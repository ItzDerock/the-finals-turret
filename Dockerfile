# From nvidia/cuda -- need to modify to support cuDNN 8
FROM nvidia/cuda:12.6.3-devel-ubuntu22.04 as base

# FROM base as base-amd64

# ENV NV_CUDNN_VERSION 8.9.7.29_1.0-1
# ENV NV_CUDNN_PACKAGE_NAME libcudnn8-cuda-12
# ENV NV_CUDNN_PACKAGE libcudnn8-cuda-12=${NV_CUDNN_VERSION}
# ENV NV_CUDNN_PACKAGE_DEV libcudnn8-dev-cuda-12=${NV_CUDNN_VERSION}

# FROM base as base-arm64

# ENV NV_CUDNN_VERSION 9.5.1.17-1
# ENV NV_CUDNN_PACKAGE_NAME libcudnn9-cuda-12
# ENV NV_CUDNN_PACKAGE libcudnn9-cuda-12=${NV_CUDNN_VERSION}
# ENV NV_CUDNN_PACKAGE_DEV libcudnn9-dev-cuda-12=${NV_CUDNN_VERSION}
# FROM base-${TARGETARCH}

# ARG TARGETARCH

# LABEL maintainer "NVIDIA CORPORATION <cudatools@nvidia.com>"
# LABEL com.nvidia.cudnn.version="${NV_CUDNN_VERSION}"

RUN apt-get update && apt-get install -y --no-install-recommends \
  libcudnn8 libcudnn8-dev

# FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04

# Set environment variables for CUDA and DEBIAN_FRONTEND
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Update and install basic utilities and dependencies
RUN apt-get update && apt-get install -y \
  vim \
  sudo \
  bash \
  wget \
  curl \
  git \
  build-essential \
  cmake \
  libopencv-dev \
  qtbase5-dev \
  python3 \
  python3-pip \
  python3-venv \
  x11-apps \
  libcanberra-gtk-module \
  libcanberra-gtk3-module && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up a passwordless sudo environment for development
RUN echo 'root ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# Create a Python virtual environment and install packages
RUN python3 -m venv /opt/venv && \
  /opt/venv/bin/pip install --no-cache-dir \
  juxtapose \
  websocket-client \
  PID_Py \
  python-dotenv \
  rel wsaccel \
  "numpy<2" && \
  /opt/venv/bin/pip install --no-cache-dir \
  "onnxruntime-gpu==1.17.1" \
  --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/
# torch torchvision \
# pyqt5 \
# opencv-python \
# ultralytics \
# websocket-client \
# PID_Py \
# python-dotenv \
# rtmlib \
# onnxruntime \
# "lap==0.5.12"

# Activate the virtual environment in future layers
ENV PATH="/opt/venv/bin:$PATH"

# Verify OpenCV installation with Qt support
RUN python3 -c "import cv2; print(cv2.getBuildInformation())" | grep -i qt

# Work in the development directory
WORKDIR /workspace

# Drop into a bash shell
CMD ["/bin/bash"]
