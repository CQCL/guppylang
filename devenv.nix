{ ... }:

{
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
}
