{ pkgs, lib, config, inputs, ... }:

{
  packages = with pkgs; [
    git
    openssl.dev # development requirement
    gcc-arm-embedded # for -objdump and other utils
    probe-rs # for flashing and debugging
  ];

  languages.rust = {
    channel = "nightly";
    enable = true;
    targets = [
      # "thumbv7em-none-eabihf"
      "thumbv6m-none-eabi"
      # "x86_64-unknown-linux-gnu"
    ];

    components = [
      "rustc"
      "cargo"
      "clippy"
      "rustfmt"
      "rust-analyzer"
      "llvm-tools"
    ];
  };
}
