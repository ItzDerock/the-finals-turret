# THE FINALS Turret Replica

This repo holds the machine learning code for the autonomous turret.
Uses YoloV8, ByteTrack, and YTMPose sending commands to a custom low-level firmware.

> [!NOTE]
> THIS PROJECT IS STILL WIP. More change and details to come.

- /warden -> low-level firmware for STM32 controlling the motors.
- /sentinel -> takes camera feed, passes through ML models, and feeds the results to the brigadier or warden. **for use on rpi5 + Hailo AI hat**
- /veteran -> the deprecated version of sentinel; machine learning code for use inference on cuda or cpu machines.

future:

- /brigadier -> gateway that processes the machine learning results and sends commands to the STM32.

# Development

## Warden

Contains a nix development shell that installs rust toolchain and arm cross-compilation toolchain. More details in the warden/README.md.

## Sentinel

Must have the hailo toolchain installed and python 3.11.

```sh
source setup_env.sh # Sets up the python virtual environment.
./download.sh # Downloads the model HEF files for the Hailo coprocessor.
```

It is recommended to use a remote editor like Zed editor with SSH, VSCode with Remote SSH extension, or (neo)vim/emacs, since you cannot install the hailo toolchain on your local machine.

## Veteran

A Dockerfile is provided for running the code in a containerized environment. Install nvidia-container-toolkit to use cuda acceleration.
There is also an attempt at a nix development shell, but it is incomplete due to qt dependency issues:
> Nix was having issues with conflicting QT versions on host and in the dev shell.
> So.. lets not worry about that and just run a docker container.
> This assumes you have built the local dockerfile (./Dockerfile) and named it turret_env.
> You can do this with `docker build . -t turret_env` in this folder.
> This passes through the NVIDIA GPU to the container.
> If you have the NVIDIA Container Runtime installed, you do not need to worry about drivers.
> Otherwise, please refer to the documentation and place the correct .run file into ~/.local/share/x11docker
> https://github.com/mviereck/x11docker/wiki/NVIDIA-driver-support-for-docker-container

x11docker is used to pass the display to the container, and works fine on Wayland too.

```sh
cd veteran
docker build . -t turret_env
./start_container.sh
```
