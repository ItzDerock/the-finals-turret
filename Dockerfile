FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04

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
  torch torchvision --index-url https://download.pytorch.org/whl/cu126 && \
  /opt/venv/bin/pip install --no-cache-dir \
  pyqt5 \
  opencv-python \
  ultralytics \
  websocket-client \
  PID_Py \
  python-dotenv \
  "lap>=0.5.12"

# Activate the virtual environment in future layers
ENV PATH="/opt/venv/bin:$PATH"

# Verify OpenCV installation with Qt support
RUN python3 -c "import cv2; print(cv2.getBuildInformation())" | grep -i qt

# Work in the development directory
WORKDIR /workspace

# Drop into a bash shell
CMD ["/bin/bash"]
