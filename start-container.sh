#!/usr/bin/env bash
# Nix was having issues with conflicting QT versions on host and in the dev shell.
# So.. lets not worry about that and just run a docker container.
# This assumes you have built the local dockerfile (./Dockerfile) and named it turret_env.
# You can do this with `docker build . -t turret_env` in this folder.
# This passes through the NVIDIA GPU to the container.
# If you have the NVIDIA Container Runtime installed, you do not need to worry about drivers.
# Otherwise, please refer to the documentation and place the correct .run file into ~/.local/share/x11docker
# https://github.com/mviereck/x11docker/wiki/NVIDIA-driver-support-for-docker-container

x11docker -g -I --sudouser -it --share "$(pwd)" --hostdisplay --runtime=nvidia --webcam turret_env
