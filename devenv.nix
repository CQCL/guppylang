{ ... }:

{
  languages.python = {
    enable = true;
    venv.enable = true;
  };

  languages.rust = {
    enable = true;
    channel = "stable";
  };
}
