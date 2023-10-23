{ pkgs, config, ... }:

{
  # https://devenv.sh/packages/
  packages = [ pkgs.git pkgs.maturin pkgs.graphviz];

  enterShell = ''
    pip install -e '.[dev]'
    (cd validator && maturin develop)
  '';

  # https://devenv.sh/languages/
  # languages.nix.enable = true;
  languages.python = {
    enable = true;
    version = "3.12";
    venv.enable = true;
    venv.requirements = "-r ${config.env.DEVENV_ROOT}/requirements.txt";
  };
  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # https://devenv.sh/processes/
  # processes.ping.exec = "ping example.com";

  # See full reference at https://devenv.sh/reference/options/
}
