# Phase 4 Test Log

**Date:** 2026-04-12
**Machine:** GhostMachine — AMD RX 7700 XT, Ubuntu 24.04
**Branch/commit:**

---

## Test Results

### Test 1 — Unit tests (33 tests)
- [x] All 33 PASSED  [ ] Some FAILED

**Output (last 5 lines):**
tests/test_scene.py::test_table_top_height PASSED                                                 [ 78%]
tests/test_scene.py::test_table_within_arm_reach PASSED                                           [ 81%]
tests/test_scene.py::test_all_blocks_on_table_surface PASSED                                      [ 84%]
tests/test_scene.py::test_all_blocks_within_table_bounds PASSED                                   [ 87%]
tests/test_scene.py::test_five_blocks PASSED                                                      [ 90%]
tests/test_scene.py::test_block_names PASSED                                                      [ 93%]
tests/test_scene.py::test_camera_above_everything PASSED                                          [ 96%]
tests/test_scene.py::test_blocks_no_overlap PASSED                                                [100%]

========================================== 33 passed in 0.21s ===========================================
ghost@GhostMachine:~/Desktop/Projects/LangRobot$ 


---

### Test 2 — perception_node starts
- [x] `perception_node ready` appears
- [x] `Camera intrinsics cached` appears (with values)

**Intrinsics logged:**
ghost@GhostMachine:~/Desktop/Projects/LangRobot$ ros2 launch langrobot langrobot.launch.py
[INFO] [launch]: All log files can be found below /home/ghost/.ros/log/2026-04-12-11-26-56-843616-GhostMachine-6687
[INFO] [launch]: Default logging verbosity is set to INFO
[INFO] [robot_state_publisher-1]: process started with pid [6691]
[INFO] [gz-2]: process started with pid [6692]
[INFO] [parameter_bridge-3]: process started with pid [6693]
[INFO] [controller_node-4]: process started with pid [6694]
[INFO] [rviz2-5]: process started with pid [6695]
[INFO] [lang_node-6]: process started with pid [6696]
[INFO] [perception_node-7]: process started with pid [6697]
[robot_state_publisher-1] [INFO] [1775957217.090699316] [robot_state_publisher]: Robot initialized
[parameter_bridge-3] [INFO] [1775957217.111485236] [clock_bridge]: Creating GZ->ROS Bridge: [/clock (gz.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
[rviz2-5] [INFO] [1775957217.334463243] [rviz2]: Stereo is NOT SUPPORTED
[rviz2-5] [INFO] [1775957217.334590442] [rviz2]: OpenGl version: 4.6 (GLSL 4.6)
[rviz2-5] [INFO] [1775957217.354931308] [rviz2]: Stereo is NOT SUPPORTED
[controller_node-4] [INFO] [1775957217.392601032] [controller_node]: Controller node started for FrankaRobot
[controller_node-4] [INFO] [1775957217.393775705] [controller_node]: Joints: ['panda_joint1', 'panda_joint2', 'panda_joint3', 'panda_joint4', 'panda_joint5', 'panda_joint6', 'panda_joint7']
[lang_node-6] [INFO] [1775957217.437189812] [lang_node]: lang_node ready — publish to /task_input to send a command
[rviz2-5] [INFO] [1775957217.443332738] [rviz2]: Stereo is NOT SUPPORTED
[perception_node-7] [INFO] [1775957217.495455892] [perception_node]: perception_node ready — waiting for camera frames
[INFO] [parameter_bridge-8]: process started with pid [7069]
[INFO] [create-9]: process started with pid [7070]
[create-9] [INFO] [1775957220.103563134] [ros_gz_sim]: Requesting list of world names.
[parameter_bridge-8] [INFO] [1775957220.118851791] [camera_bridge]: Creating GZ->ROS Bridge: [/camera/image (gz.msgs.Image) -> /camera/image (sensor_msgs/msg/Image)] (Lazy 0)
[parameter_bridge-8] [INFO] [1775957220.120849970] [camera_bridge]: Creating GZ->ROS Bridge: [/camera/depth_image (gz.msgs.Image) -> /camera/depth_image (sensor_msgs/msg/Image)] (Lazy 0)
[parameter_bridge-8] [INFO] [1775957220.121351427] [camera_bridge]: Creating GZ->ROS Bridge: [/camera/camera_info (gz.msgs.CameraInfo) -> /camera/camera_info (sensor_msgs/msg/CameraInfo)] (Lazy 0)
[create-9] [INFO] [1775957220.541177794] [ros_gz_sim]: Waiting messages on topic [/robot_description].
[perception_node-7] [INFO] [1775957220.541546721] [perception_node]: Camera intrinsics cached: {'fx': 554.3827128226441, 'fy': 554.3827128226441, 'cx': 320.0, 'cy': 240.0}
[perception_node-7] [WARN] [1775957220.547590288] [perception_node]: No depth frame yet — skipping
[create-9] [INFO] [1775957220.553445974] [ros_gz_sim]: Entity creation successful.
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint1"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint2"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint3"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint4"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint5"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint6"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint7"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_finger_joint1"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_finger_joint2"]/physics/ode/provide_feedback:<urdf-string>:L0]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] [Err] [Physics.cc:1801] Attempting to create a mimic constraint for joint [fr3_finger_joint2] but the chosen physics engine does not support mimic constraints, so no constraint will be created.
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint1"]/physics/ode/provide_feedback:<data-string>:L65]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint2"]/physics/ode/provide_feedback:<data-string>:L128]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint3"]/physics/ode/provide_feedback:<data-string>:L191]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[INFO] [create-9]: process has finished cleanly [pid 7070]
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint4"]/physics/ode/provide_feedback:<data-string>:L254]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint5"]/physics/ode/provide_feedback:<data-string>:L317]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint6"]/physics/ode/provide_feedback:<data-string>:L380]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_joint7"]/physics/ode/provide_feedback:<data-string>:L443]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_finger_joint1"]/physics/ode/provide_feedback:<data-string>:L525]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].
[gz-2] Warning [Utils.cc:132] [/sdf/model[@name="fr3"]/joint[@name="fr3_finger_joint2"]/physics/ode/provide_feedback:<data-string>:L680]: XML Element[provide_feedback], child of element[ode], not defined in SDF. Copying[provide_feedback] as children of [ode].


---

### Test 3 — /object_poses output
- [x] JSON array of 5 dicts updating at framerate
- [x] Visible blocks have non-null coordinates

**Sample output:**
data: '[{"colour": "red", "x": 0.748, "y": 0.049, "z": 0.45, "visible": true}, {"colour": "blue", "x": 0.254, "y": 0.047, "z": 0.45, "v...'

**Notes:** full line doesnt get priunted in the terminal.


---

### Test 4 — Position accuracy
- [x] Positions within ~5 cm of Gazebo block locations
- [ yes, but i changed it] y-axis correction needed: yes / no

**Notes:**
made y axis change already inside perceptio.py

---

### Test 5 — Active nodes
- [x] `/perception_node` in `ros2 node list`

**Output of `ros2 node list`:**
/camera_bridge
/clock_bridge
/controller_node
/lang_node
/perception_node
/robot_state_publisher
/rviz2
/transform_listener_impl_62da0c0128b0

---

## Overall Phase 4 Result

- [x] **PASSED**
- [x] **PASSED WITH ISSUES** — see notes
- [ ] **FAILED**

**Issues:**
conficts beween dependensies or libraries, or packages, numpy was a problem had o downgrade.

---

## What to do next

```bash
git add logs/phase4-test-log.md
git commit -m "test: Phase 4 verification results"
git push origin main
```
