# LangRobot — Project Overview

## What Is It?

LangRobot is a **language-driven robot manipulation system** that lets you control a simulated robot arm using plain English commands. You type (or speak) a natural language instruction — "pick up the red cube and place it on the shelf" — and the robot executes it in a physics simulation.

It is the second flagship portfolio project, designed to target **robotics and humanoid robot companies** (Figure AI, Agility Robotics, Boston Dynamics, 1X Technologies, Apptronik).

---

## Why This Project Exists

Every major humanoid robot company right now is trying to solve the same problem: **how do you make a robot understand and act on human language?** This is the defining engineering challenge of the next decade in robotics. LangRobot is a direct demonstration that you understand and can build that pipeline — from words to robot motion.

The core skill this demonstrates to recruiters:
- ROS2 (the industry-standard robot middleware)
- Gazebo (physics simulation used in research and industry)
- Language model integration with physical systems
- Full perception → planning → action loop
- Production-grade code (not a notebook, not a demo script)

---

## Core Idea

The fundamental idea is a **three-stage pipeline** that converts language into robot motion:

```
Natural Language
      ↓
  Understand           ← LLM parses what the human wants
      ↓
  See                  ← Computer vision finds objects in the scene
      ↓
  Act                  ← Robot plans and executes the motion
      ↓
  Verify               ← Vision confirms task was completed
```

Each stage is a separate, testable module. They are wired together by ROS2 — the same architecture used in real industrial and research robots. This is important: the code structure mirrors what you would write at a real robotics company.

---

## The Pipeline in Detail

### Stage 1 — Language Understanding (`lang_node`)

The user gives a command in plain English. An LLM (running locally via Ollama, or via API) parses this into a structured action specification.

**Input:**
```
"Pick up the blue block and put it on top of the red block"
```

**Output (structured JSON):**
```json
{
  "action": "pick_and_place",
  "object": "blue_block",
  "target": "red_block",
  "relation": "on_top_of"
}
```

The LLM also handles:
- Ambiguous commands ("move that thing over there" → ask for clarification)
- Sequential tasks ("first sort by colour, then stack by size")
- Failure recovery ("that didn't work, try the other block")

This stage uses LangChain with a structured output parser and a local Llama 3.2 model via Ollama — no API key required.

---

### Stage 2 — Scene Perception (`perception_node`)

Before the robot can act, it needs to know **where things are** in the world. This stage uses computer vision on the simulated camera feed from Gazebo.

**What it detects:**
- Object identities (colour, shape, class)
- 3D positions (x, y, z coordinates in robot base frame)
- Object states (held, placed, stacked, etc.)

**How it works:**
- Gazebo publishes a simulated RGB-D camera feed as a ROS2 topic
- A YOLO model (fine-tuned on the simulation objects) detects and classifies objects
- Depth data from the camera converts 2D pixel positions to 3D world coordinates
- Results are published as a ROS2 `PoseArray` message for the planner to consume

This stage deliberately reuses YOLOv8 from InspectAI — same architecture, different training data (simulated objects instead of industrial defects).

---

### Stage 3 — Motion Planning (`planner_node`)

Given the structured action and the object poses, this stage generates a physically valid robot trajectory. It uses **MoveIt2**, the standard motion planning framework for ROS2.

**What MoveIt2 does:**
- Takes a goal pose (where the end-effector needs to reach)
- Plans a collision-free path through joint space
- Handles kinematic constraints (joint limits, singularities)
- Returns a joint trajectory the robot can execute

**The pick-and-place sequence:**
1. Move above the target object (pre-grasp pose)
2. Move down to grasp height
3. Close gripper
4. Lift up
5. Move above the destination
6. Lower to placement height
7. Open gripper
8. Retreat

Each step is a MoveIt2 planning request.

---

### Stage 4 — Execution (`controller_node`)

The planned trajectory is sent to the **Gazebo-simulated robot** via ROS2 control interfaces. Gazebo simulates the physics: the robot arm moves, gravity acts on objects, contacts are detected.

**Robot:** A UR5 or Franka Panda simulated arm — both are standard in robotics research, widely used in industry, and have excellent ROS2/MoveIt2 support.

**Gripper:** A parallel-jaw gripper that opens and closes based on controller commands.

---

### Stage 5 — Feedback & Verification (`feedback_node`)

After execution, the perception node re-analyses the scene and compares the outcome to the goal:
- Was the object picked up? ✅ / ✗
- Was it placed at the right location? ✅ / ✗
- Did anything fall over? ✅ / ✗

The result is published back as a natural language response:
```
"Done. The blue block is now on top of the red block."
"Failed — the blue block slipped. Retrying..."
```

This closes the loop and enables automatic recovery.

---

## Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│              (terminal / web UI / voice input)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Natural language command
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     lang_node (ROS2)                            │
│           LLM (Ollama/Llama 3.2) + LangChain                   │
│     Natural language → Structured action JSON                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ /task_command topic (JSON)
                           ▼
┌────────────────────────┐    ┌───────────────────────────────────┐
│   perception_node      │    │         planner_node              │
│   (ROS2)               │◄───│         (ROS2 + MoveIt2)          │
│   YOLOv8 + depth       │    │   Task JSON + Poses → Trajectory  │
│   RGB-D → Object poses │    │                                   │
└────────────────────────┘    └──────────────┬────────────────────┘
         │ /object_poses                     │ /joint_trajectory
         └──────────────►────────────────────┘
                                             ▼
                           ┌─────────────────────────────────────┐
                           │       controller_node (ROS2)        │
                           │   Trajectory → ROS2 Control         │
                           └──────────────────┬──────────────────┘
                                              │ /joint_commands
                                              ▼
                           ┌─────────────────────────────────────┐
                           │       GAZEBO SIMULATION             │
                           │   UR5 / Franka Panda robot arm      │
                           │   Physics, camera, contacts         │
                           └──────────────────┬──────────────────┘
                                              │ /camera/rgb_image
                                              ▼
                           ┌─────────────────────────────────────┐
                           │       feedback_node (ROS2)          │
                           │   Vision-based task verification    │
                           │   → Natural language result         │
                           └─────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Robot middleware | **ROS2 Humble** | Industry standard. Every major robotics company uses it. |
| Physics simulation | **Gazebo Ignition** | Standard simulator paired with ROS2. |
| Motion planning | **MoveIt2** | Standard for arm manipulation planning. |
| Language model | **Ollama + Llama 3.2** | Local, no API key, no cost. Same stack as InspectAI. |
| LLM framework | **LangChain** | Structured output parsing, prompt management. |
| Object detection | **YOLOv8** | Reused from InspectAI — same architecture, different weights. |
| Language | **Python 3.11** | Primary ROS2 language for research-grade nodes. |
| Visualisation | **RViz2** | Standard ROS2 visualisation tool. |

---

## Project Structure (Planned)

```
LangRobot/
├── langrobot/              ← ROS2 package
│   ├── lang_node.py        ← LLM command parser
│   ├── perception_node.py  ← YOLOv8 + depth → object poses
│   ├── planner_node.py     ← MoveIt2 motion planning
│   ├── controller_node.py  ← Trajectory execution
│   └── feedback_node.py    ← Task verification
├── config/
│   ├── robot.urdf          ← Robot description
│   ├── scene.sdf           ← Gazebo scene (table, objects)
│   └── moveit.yaml         ← MoveIt2 planning config
├── launch/
│   └── langrobot.launch.py ← Single command to start everything
├── models/
│   └── sim_objects.pt      ← YOLOv8 weights for sim objects
├── tests/
│   ├── test_lang_node.py
│   ├── test_perception.py
│   └── test_planner.py
├── scripts/
│   └── train_perception.py ← Train YOLOv8 on sim objects
├── docker-compose.yml      ← Containerised: ROS2 + Gazebo + Ollama
├── requirements.txt
└── README.md
```

---

## Demonstration Scenario

The goal is one clean, impressive end-to-end demo:

**Scene:** A table with 5 coloured blocks (red, blue, green, yellow, white) in random positions. A simulated UR5 arm.

**Commands the system handles:**

```
User: "Stack all the blocks by colour, lightest on top"
Robot: sorts, plans, picks, places — stacks in order

User: "Move the red block to the left side of the table"
Robot: perceives, plans, executes

User: "Pick up the block closest to you"
Robot: measures distances, picks nearest

User: "Undo that last action"
Robot: remembers state, reverses
```

This covers: perception, spatial reasoning, sequential planning, memory, and error recovery — all the capabilities robotics companies care about.

---

## Key Design Decisions

### Why ROS2 and not a simpler approach?
ROS2 is used in every serious robotics company. Knowing it signals you can work in a real robotics engineering team. A Python script talking to a simulated arm would not be credible.

### Why local LLM (Ollama)?
Same reason as InspectAI — no API key, no cloud cost, runs on the same machine as the rest of the stack. Also demonstrates the ability to deploy models to edge devices (a real constraint in robotics).

### Why reuse YOLOv8 from InspectAI?
It shows deliberate architecture thinking — same perception backbone, retrained for a different domain. This is how real ML systems are built: transferable components with task-specific fine-tuning.

### Why Gazebo and not a real robot?
Simulation is how robotics software is actually developed. Every company develops in simulation first, then transfers to hardware. Sim-to-real is a core competency this project demonstrates.

### Why keep it one clean scenario?
Depth beats breadth. One perfectly working, well-documented demo is more impressive than five half-working ones.

---

## What This Proves to Recruiters

| Company Type | What They See |
|-------------|---------------|
| **Figure AI, Agility, 1X** | Language-conditioned manipulation — exactly what they're building |
| **Boston Dynamics, Unitree** | ROS2 + MoveIt2 + Gazebo — the tools they use daily |
| **AI startups (robot-adjacent)** | Full LLM → physical action pipeline |
| **Automation / Industry** | Simulation, planning, computer vision combined |

---

## Prerequisites Before Starting

- InspectAI fully trained and deployed (learn YOLOv8 deeply first)
- ROS2 Humble installed on Ubuntu (your Linux PC is ready)
- Basic familiarity with ROS2 concepts (nodes, topics, services, launch files)
- Gazebo Ignition installed

---

## Estimated Timeline

| Phase | Task | Time |
|-------|------|------|
| 1 | ROS2 + Gazebo setup, basic arm control | 3–4 days |
| 2 | Scene setup (table, blocks, camera) | 2–3 days |
| 3 | lang_node (LLM → structured command) | 2–3 days |
| 4 | perception_node (YOLOv8 on sim objects) | 3–4 days |
| 5 | planner_node (MoveIt2 pick-and-place) | 4–5 days |
| 6 | feedback_node + full pipeline integration | 3–4 days |
| 7 | Testing, polishing, README, demo video | 3–4 days |
| **Total** | | **~3–4 weeks** |

---

## First Steps When Ready to Start

1. Install ROS2 Humble on your Linux PC
2. Install Gazebo Ignition
3. Get a simulated UR5 or Franka arm running in Gazebo (there are open-source packages for both)
4. Verify you can send a joint command from Python and see the arm move in Gazebo
5. Then build each node one at a time in the order above

That first "arm moves when I run a Python script" moment is the foundation everything builds on.
