# THE FINALS Turret Replica

This repo holds the machine learning code for the autonomous turret. 
Uses YoloV8, ByteTrack, and YTMPose sending commands to Klipper.

> [!NOTE]
> THIS PROJECT IS STILL WIP. More change and details to come.

In the future,
- /warden -> low-level firmware for STM32 controlling the motors.
- /brigadier -> gateway that processes the machine learning results and sends commands to the STM32.
- /sentinel -> the current code in the repo. Forwards ML output to brigadier.
