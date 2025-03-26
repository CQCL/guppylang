{ pkgs, lib, ... }:

{
  # for building optional tket2 dependency
  # see https://github.com/CQCL/tket2/blob/main/devenv.nix
  packages = [
    pkgs.just
    pkgs.graphviz

    # These are required for hugr-llvm to be able to link to llvm.
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
      pkgs.zlib
      pkgs.ncurses
    ]
  );

  enterShell = ''
    export LD_LIBRARY_PATH="${lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}";
  '';

  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
    venv.enable = true;
  };

  env.LLVM_SYS_140_PREFIX = pkgs.llvmPackages_14.libllvm.dev;

  languages.rust = {
    enable = true;
    channel = "stable";
    components = [ "rustc" "cargo" "clippy" "rustfmt" "rust-analyzer" ];
  };
}
