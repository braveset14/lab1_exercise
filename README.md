# Lab 1 Exercise: Program diffdrive_bot

**Program:** BSc in Software Engineering  
**Course:** Introduction to Robotics and Intelligent Systems  
**Name:** Yeabsera  Zewdu

This repository contains the completed exercise for Lab 1. It includes the modified `diffdrive_bot` package (with a newly added depth camera and IMU), along with two new packages created for this exercise: `my_robot_interfaces` and `my_robot_nodes`. 

The project builds on ROS 2 Jazzy and Gazebo Harmonic (Ubuntu 24.04).


## How to Build

Because this folder contains four packages (`diffdrive_bot`, `lab_interfaces`, `my_robot_interfaces`, `my_robot_nodes`), it can be dropped into the `src` folder of any ROS 2 workspace and built.

```bash
# 1. Source your ROS 2 installation
source /opt/ros/jazzy/setup.bash

# 2. Build the packages
cd ~/your_workspace
colcon build --symlink-install

# 3. Source the workspace
source install/setup.bash

2. How to Run Each Step
Important: Open a new terminal for every new command block below, and make sure it is sourced:

bash
source /opt/ros/jazzy/setup.bash
source ~/diffdrive_ws/install/setup.bash
Step 1: Sensors (Depth Camera and IMU)
Verify the new URDF in RViz (check the TF tree and the joints):

bash
ros2 launch diffdrive_bot display.launch.py
Verify the transform of the depth camera (expect x = -0.215, yaw = 3.14159):

bash
ros2 run tf2_ros tf2_echo base_link depth_camera_link
Run the simulation to see the sensors in RViz (add Image on /depth_camera/image and PointCloud2 on /depth_camera/points):

bash
ros2 launch diffdrive_bot gazebo.launch.py
Verify the IMU is publishing at 50 Hz:

bash
ros2 topic hz /imu
Steps 2-5: The turn_away Node
This covers the node that reacts to obstacles, reads parameters, publishes RobotStatus, and uses services.

bash
# Terminal 1: Start the simulation
ros2 launch diffdrive_bot control.launch.py

# Terminal 2: Run your node (starts switched off)
ros2 run my_robot_nodes turn_away
Check Step 3 (Parameters):

bash
ros2 param list /turn_away
ros2 param set /turn_away forward_speed 0.4
Check Step 4 (Custom Message):

bash
# Run this after enabling the node to see "forward" or "turning"
ros2 topic echo /robot_status
Check Step 5 (Services):

bash
# Enable the node
ros2 service call /turn_away_enable std_srvs/srv/SetBool "{data: true}"

# Set speed (Accepted)
ros2 service call /set_turn_speed my_robot_interfaces/srv/SetTurnSpeed "{turn_speed: 1.0}"

# Set speed (Rejected, exceeds max_turn_speed of 1.5)
ros2 service call /set_turn_speed my_robot_interfaces/srv/SetTurnSpeed "{turn_speed: 3.0}"

# Disable the node
ros2 service call /turn_away_enable std_srvs/srv/SetBool "{data: false}"
Step 6: The rotate Action Server
This server turns the robot on the spot by accumulating yaw changes from /odom.

bash
# Terminal 1: Start the simulation
ros2 launch diffdrive_bot control.launch.py

# Terminal 2: Run the server
ros2 run my_robot_nodes rotate_server

# Terminal 3: Send a goal (quarter turn left)
ros2 action send_goal --feedback /rotate my_robot_interfaces/action/Rotate "{angle: 1.57}"

# Test rejection (angle of zero)
ros2 action send_goal /rotate my_robot_interfaces/action/Rotate "{angle: 0.0}"
Step 7: The square_driver and Launch File
This client calls /drive_distance and /rotate in a loop to drive a square. It waits for /odom before sending the first goal.

bash
# Start the simulation, the rotate server, and the square driver all at once
ros2 launch my_robot_nodes square.launch.py side_length:=0.8
To see the action connections, open a new terminal while the robot is driving and run:

bash
rqt_graph


         
         What did not work for me 
-- During the development of this exercise, I hit several bugs and environment quirks. Here is what went wrong and how I fixed it:

           1)Goal rejected on startup (Status 0):
  When square_driver launched, it sent its first goal immediately. However, drive_distance_server rejected it because self.position was still None (it had not yet received the first /odom message from the Gazebo bridge).
Fix: I modified square_driver to subscribe to /odom and spin until self.have_odom becomes True before sending the first goal. This ensures the action server is fully loaded and ready.

           2) The robot blinking and disappearing in Gazebo:
  Occasionally, relaunching the simulation caused the robot to spawn and then immediately vanish. This was caused by stale gz sim background processes from a previous run interfering with the new instance.
Fix: Running pkill -f "gz sim" before relaunching kills any zombie processes and guarantees a clean simulation start.

           3)TF_OLD_DATA warnings in RViz:
  RViz printed a flood of warnings saying it was ignoring data from the past for the base_footprint frame. This happens because RViz processes TF data before Gazebo simulation clock (/clock) has fully started, causing a mismatch between wall-clock time and sim-time.
Fix: The gazebo.launch.py file already sets use_sim_time: True for RViz and robot_state_publisher. The warnings only appear during the first 2 seconds of startup and then clear up once the clock catches up. This is harmless.

