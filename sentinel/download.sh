#!/usr/bin/env bash

mkdir -p model
curl -o model/yolov8s_pose.hef "https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.13.0/hailo8/yolov8s_pose.hef"
