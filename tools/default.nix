# Alfredo's programs, tested on build. Each sits in its own folder; recipes and language are the modules they share.
{ pkgs, lib, facts }:
let
  inherit (facts) recipesRoot recipesUrl stateRoot cookidooCollection modelUrl model speechUrl calendarsRoot defaultCalendar syncCalendars;

  fill = import ./fill.nix { inherit lib; };
  tests = import ./tests.nix { inherit pkgs lib; };
  cook = lib.getExe pkgs.cook-cli;
  planFile = "${stateRoot}/meals-plan.json";   # meals' current plan, which drafts relinks on a rename

  shared = name: values: pkgs.python3Packages.toPythonModule
    (pkgs.writeTextDir "${pkgs.python3.sitePackages}/${name}.py" (fill name values));
  recipes = shared "recipes" { inherit cook; };
  language = shared "language" { };

  # Depending on the tests means a failing program never builds, so it never deploys.
  program = name: libraries: values: (pkgs.writers.writePython3Bin name { libraries = [ recipes language ] ++ libraries; flakeIgnore = [ "E501" ]; }
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
  agenda = program "agenda" (with pkgs.python3Packages; [ mcp icalendar recurring-ical-events tzdata ]) {
    inherit calendarsRoot defaultCalendar syncCalendars;
  };
in
{
  inherit cookidoo meals drafts agenda;
}
