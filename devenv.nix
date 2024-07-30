{ pkgs, lib, ... }:

{
  # for building optional tket2 dependency
  # see https://github.com/CQCL/tket2/blob/main/devenv.nix
  packages = [
    pkgs.libffi
    pkgs.libxml2
  ]
  ++ lib.optionals pkgs.stdenv.isLinux [
    pkgs.stdenv.cc.cc.lib
  ]
  ++ lib.optionals pkgs.stdenv.isDarwin (
    with pkgs.darwin.apple_sdk; [
      frameworks.CoreServices
      frameworks.CoreFoundation
    ]
  );

  languages.python = {
    enable = true;
    poetry = {
      enable = true;
      install = {
        enable = true;
        groups = ["validation" "pytket"];
      };

      activate.enable = true;
    };
  };

  languages.rust = {
    enable = true;
    channel = "stable";
  };
}
