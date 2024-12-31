{ pkgs, lib, config, inputs, ... }:
{
  # https://devenv.sh/packages/
  packages = with pkgs; [
    git pyright

    # CUDA
    git gitRepo gnupg autoconf curl
    procps gnumake util-linux m4 gperf unzip
    cudatoolkit linuxPackages.nvidia_x11
    libGLU libGL
    xorg.libXi xorg.libXmu freeglut
    xorg.libXext xorg.libX11 xorg.libXv xorg.libXrandr zlib
    ncurses5 stdenv.cc binutils

    # python312Packages.torch-bin
    glib

    qt5.qtwayland
    libGL
    opencv

    python312Packages.pyqt5
    python312Packages.opencv4
    python312Packages.torch-bin
    python312Packages.torchvision-bin
  ];

  # https://devenv.sh/languages/
  languages.python.enable = true;
  languages.python.venv.enable = true;
  languages.python.venv.requirements = ''
    websocket-client
    ultralytics
    PID_Py
    lap>=0.5.12
  '';

  languages.python.package = pkgs.python312;

  env = {
    QT_PLUGIN_PATH = "${pkgs.qt5.qtwayland.bin}/lib/qt-${pkgs.qt5.qtwayland.version}/plugins";
    LD_LIBRARY_PATH = lib.makeLibraryPath [
      pkgs.libGL
      pkgs.qt5.qtwayland
      pkgs.qt5.qtbase
      pkgs.stdenv.cc.cc.lib
      pkgs.xorg.libX11
      pkgs.xorg.libXext
    ];
  };
}
