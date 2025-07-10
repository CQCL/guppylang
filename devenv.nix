{ pkgs, lib, ... }:

{
  # for building optional tket2 dependency
  # see https://github.com/CQCL/tket2/blob/main/devenv.nix
  packages = [
    pkgs.just
    pkgs.graphviz

  ]
  ++ lib.optionals pkgs.stdenv.isDarwin (
    [ pkgs.zlib ]
  );


  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
    venv.enable = true;
  };

  languages.rust = {
    channel = "stable";
    enable = true;
    components = [ "rustc" "cargo" "clippy" "rustfmt" "rust-analyzer" ];
  };
}
