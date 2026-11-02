#!/usr/bin/env python3

import math
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node

from my_robot_interfaces.action import Rotate


def yaw_from_quaternion(q):
    
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angle_difference(target, current):
    return math.atan2(math.sin(target - current), math.cos(target - current))


class RotateServer(Node):

    def __init__(self):
        super().__init__("rotate_server")
        self.declare_parameter("turn_speed", 0.5)

        self.yaw = None

        # The goal runs in a loop, so the odometry callback needs its own thread
        group = ReentrantCallbackGroup()
        self.cmd_vel = self.create_publisher(Twist, "cmd_vel", 10)
        self.create_subscription(Odometry, "odom", self.on_odom, 10, callback_group=group)
        self.action_server = ActionServer(
            self, Rotate, "rotate",
            execute_callback=self.execute,
            goal_callback=self.on_goal,
            cancel_callback=lambda goal_handle: CancelResponse.ACCEPT,
            callback_group=group,
        )

    def on_odom(self, msg):
        self.yaw = yaw_from_quaternion(msg.pose.pose.orientation)

    def on_goal(self, goal):
        if goal.angle == 0.0 or self.yaw is None:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def execute(self, goal_handle):
        goal = goal_handle.request.angle
        self.get_logger().info(f"Turning {goal:.2f} rad")

        turn_speed = self.get_parameter("turn_speed").value
        direction = 1.0 if goal > 0.0 else -1.0
        twist = Twist()
        twist.angular.z = direction * turn_speed

        feedback = Rotate.Feedback()
        result = Rotate.Result()

        # Sum the change between consecutive odometry messages, so the jump from pi
        # to -pi does not corrupt the total
        prev_yaw = self.yaw
        turned = 0.0

        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                self.cmd_vel.publish(Twist())
                goal_handle.canceled()
                result.turned = turned
                self.get_logger().info(f"Canceled after {turned:.2f} rad")
                return result

            turned += angle_difference(self.yaw, prev_yaw)
            prev_yaw = self.yaw
            result.turned = turned

            if abs(turned) >= abs(goal):
                break

            self.cmd_vel.publish(twist)
            feedback.turned = turned
            goal_handle.publish_feedback(feedback)
            time.sleep(0.05)

        self.cmd_vel.publish(Twist())
        goal_handle.succeed()
        self.get_logger().info(f"Reached, turned {result.turned:.2f} rad")
        return result


def main():
    rclpy.init()
    node = RotateServer()
    try:
        rclpy.spin(node, executor=MultiThreadedExecutor())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()