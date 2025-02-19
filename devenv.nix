{ pkgs, lib, ... }:

{
  # for building optional tket2 dependency
  # see https://github.com/CQCL/tket2/blob/main/devenv.nix
  packages = [
    pkgs.just
    pkgs.llvmPackages_14.libllvm
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

  enterShell = ''
    export PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"
  '';

  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync = {
        enable = true;
        allExtras = true;
      };
    };
  };

  env.LLVM_SYS_140_PREFIX = pkgs.llvmPackages_14.libllvm.dev;

  env.LD_LIBRARY_PATH = "${lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.zlib ]}";

  languages.rust = {
    enable = true;
    channel = "stable";
  };
}
