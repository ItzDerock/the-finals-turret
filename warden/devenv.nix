{ pkgs, lib, config, inputs, ... }:

{
  packages = with pkgs; [
    git
    openssl.dev
  ];

  languages.rust = {
    channel = "nightly";
    enable = true;
    targets = ["thumbv7em-none-eabihf"];
  };
}
