{ pkgs, lib, config, ... }: let
  cfg = config.llvm;
  libllvm = pkgs."llvmPackages_${cfg.llvmVersion}".libllvm.dev;
in {
  # for building optional tket2 dependency
  # see https://github.com/CQCL/tket2/blob/main/devenv.nix
  options.llvm = {
    llvmVersion = lib.mkOption {
      type = lib.types.str;
      default = "14";
    };
  };
  config = {
    packages = [
      pkgs.just
      libllvm
      # these are required by libllvm
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

    env = {
      "LLVM_SYS_${cfg.llvmVersion}0_PREFIX" = "${libllvm}";
    };

    languages.python = {
      enable = true;
      poetry = {
        enable = true;
        activate.enable = true;
      };
    };

    languages.rust = {
      enable = true;
      channel = "stable";
    };
  };
}
