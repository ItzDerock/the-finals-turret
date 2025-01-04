{
  description = "Development environment with Python and CUDA support";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    devenv.url = "github:cachix/devenv";
  };

  outputs = { self, nixpkgs, flake-utils, devenv }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
          overlays = [(final: prev: {
            python312 = prev.python312.override {
              packageOverrides = final: prevPy: {

                triton-bin = prevPy.triton-bin.overridePythonAttrs (oldAttrs: {
                  postFixup = ''
                    chmod +x "$out/${prev.python312.sitePackages}/triton/backends/nvidia/bin/ptxas"
                    substituteInPlace $out/${prev.python312.sitePackages}/triton/backends/nvidia/driver.py \
                      --replace \
                        'return [libdevice_dir, *libcuda_dirs()]' \
                        'return [libdevice_dir, "${prev.addDriverRunpath.driverLink}/lib", "${prev.cudaPackages.cuda_cudart}/lib/stubs/"]'
                  '';
                });
              };
            };
            python312Packages = final.python312.pkgs;
          })];
        };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            git pyright
            # CUDA
            git gitRepo gnupg autoconf curl
            procps gnumake util-linux m4 gperf unzip
            cudatoolkit linuxPackages.nvidia_x11
            libGLU libGL
            xorg.libXi xorg.libXmu freeglut
            xorg.libXext xorg.libX11 xorg.libXv xorg.libXrandr zlib
            ncurses5 stdenv.cc binutils
            glib
            qt5.qtwayland
            libGL
            opencv

            onnxruntime
            python310Packages.numpy
            python310Packages.pyqt5
            python310Packages.opencv4
            python310Packages.torch-bin
            python310Packages.torchvision-bin
            python310Packages.python-dotenv
            python310Packages.onnxruntime
            python310
            coreutils
          ];

          shellHook = ''
            python3 -m venv .venv
            source .venv/bin/activate
            pip install \
              websocket-client \
              ultralytics \
              PID_Py \
              "lap>=0.5.12" \
              rtmlib
          '';

          QT_PLUGIN_PATH = "${pkgs.qt5.qtwayland.bin}/lib/qt-${pkgs.qt5.qtwayland.version}/plugins";
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.libGL
            pkgs.qt5.qtwayland
            pkgs.qt5.qtbase
            pkgs.stdenv.cc.cc.lib
            pkgs.xorg.libX11
            pkgs.xorg.libXext
          ];
        };
      }
    );
}
