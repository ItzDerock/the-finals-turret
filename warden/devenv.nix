{ pkgs, lib, config, inputs, ... }:

{
  packages = with pkgs; [
    git
    openssl.dev # development requirement
    gcc-arm-embedded # for -objdump and other utils
  ];

  languages.rust = {
    channel = "nightly";
    enable = true;
    targets = [
      "thumbv7em-none-eabihf"
      "x86_64-unknown-linux-gnu"
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
