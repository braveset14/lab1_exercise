#!/usr/bin/env python3


import math
import time

import rclpy
from action_msgs.msg import GoalStatus
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from lab_interfaces.action import DriveDistance
from my_robot_interfaces.action import Rotate


class SquareDriver(Node):

    def __init__(self):
        super().__init__("square_driver")
        self.declare_parameter("side_length", 0.5)

        self.have_odom = False
        self.create_subscription(Odometry, "odom", self.on_odom, 10)
        self.drive_client = ActionClient(self, DriveDistance, "drive_distance")
        self.rotate_client = ActionClient(self, Rotate, "rotate")

    def on_odom(self, msg):
        self.have_odom = True

    def wait_for_odom(self, timeout=30.0):
        
        start = time.monotonic()
        while not self.have_odom and rclpy.ok():
            if time.monotonic() - start > timeout:
                self.get_logger().error("Timed out waiting for /odom")
                return False
            rclpy.spin_once(self, timeout_sec=0.1)
        return self.have_odom

    def send_and_wait(self, client, goal, feedback_callback, label):
        
        client.wait_for_server()
        send_future = client.send_goal_async(goal, feedback_callback=feedback_callback)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()

        if not goal_handle.accepted:
            self.get_logger().error(f"{label}: goal rejected")
            return GoalStatus.STATUS_UNKNOWN, None

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        response = result_future.result()
        return response.status, response.result

    def on_drive_feedback(self, msg):
        self.get_logger().info(f"Travelled {msg.feedback.travelled:.2f} m")

    def on_rotate_feedback(self, msg):
        self.get_logger().info(f"Turned {msg.feedback.turned:.2f} rad")

    def run(self):
        side_length = self.get_parameter("side_length").value
        quarter_turn = math.pi / 2.0

        self.get_logger().info("Waiting for /odom...")
        if not self.wait_for_odom():
            self.get_logger().error("No odometry, giving up")
            return

        self.get_logger().info(f"Driving a square with sides of {side_length:.2f} m")

        for side in range(1, 5):
            drive_goal = DriveDistance.Goal()
            drive_goal.distance = side_length
            status, result = self.send_and_wait(
                self.drive_client, drive_goal, self.on_drive_feedback, f"side {side}"
            )
            if status != GoalStatus.STATUS_SUCCEEDED or not result.reached:
                self.get_logger().error(f"side {side}: drive failed (status {status})")
                self.stop()
                return

            rotate_goal = Rotate.Goal()
            rotate_goal.angle = quarter_turn
            status, result = self.send_and_wait(
                self.rotate_client, rotate_goal, self.on_rotate_feedback, f"turn {side}"
            )
            if status != GoalStatus.STATUS_SUCCEEDED:
                self.get_logger().error(f"side {side}: turn failed (status {status})")
                self.stop()
                return

        self.get_logger().info("Square complete")
        self.stop()

    def stop(self):
        self.get_logger().info("Done")


def main():
    rclpy.init()
    node = SquareDriver()
    try:
        node.run()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()