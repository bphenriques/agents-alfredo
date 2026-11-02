# Alfredo's meals, cookidoo and drafts programs, tested on build.
{ pkgs, lib, facts }:
let
  inherit (facts) recipesRoot recipesUrl stateRoot cookidooCollection modelUrl model speechUrl;

  fill = import ./fill.nix { inherit lib; };
  tests = import ./tests.nix { inherit pkgs lib; };
  cook = lib.getExe pkgs.cook-cli;
  planFile = "${stateRoot}/meals-plan.json";   # meals' current plan, which drafts relinks on a rename

  recipes = pkgs.python3Packages.toPythonModule
    (pkgs.writeTextDir "${pkgs.python3.sitePackages}/recipes.py" (fill "recipes" { inherit cook; }));

  # Depending on the tests means a failing program never builds, so it never deploys.
  program = name: libraries: values: (pkgs.writers.writePython3Bin name { libraries = [ recipes ] ++ libraries; flakeIgnore = [ "E501" ]; }
    (fill name values)).overrideAttrs { inherit tests; };

  # On the state volume, writable: every refresh rotates the token.
  cookidoo = program "cookidoo" [ pkgs.python3Packages.cookidoo-api ] {
    tokenFile = "${stateRoot}/cookidoo-token.json"; library = "${recipesRoot}/library"; collection = cookidooCollection;
  };
  meals = program "meals" [ pkgs.python3Packages.mcp ] {
    library = "${recipesRoot}/library"; site = recipesUrl; cookidoo = lib.getExe cookidoo; inherit planFile cook;
  };
  # Drafts sit beside the library, so the site, plans and shopping lists never see them.
  drafts = program "drafts" [ pkgs.python3Packages.recipe-scrapers ] {
    library = "${recipesRoot}/library"; drafts = "${recipesRoot}/drafts"; inherit planFile modelUrl model speechUrl cook;
    ytDlp = lib.getExe pkgs.yt-dlp; curl = lib.getExe pkgs.curl; magick = lib.getExe' pkgs.imagemagick "magick";
  };
in
{
  inherit cookidoo meals drafts;
}
