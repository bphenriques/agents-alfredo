# The tools' tests, against ./fixtures.
{ pkgs, lib }:
let
  fill = import ./fill.nix { inherit lib; };
  fixture = { tokenFile = "token.json"; planFile = "plan.json"; library = "${./fixtures}"; site = "https://recipes.test";
              collection = "test"; cookidoo = "cookidoo"; drafts = "drafts"; modelUrl = "http://model.test";
              model = "test"; speechUrl = "http://speech.test"; ytDlp = "yt-dlp"; curl = "curl"; magick = "magick";
              cook = lib.getExe pkgs.cook-cli; calendarsRoot = "calendars"; defaultCalendar = "personal"; };
  programs = [ "cookidoo" "meals" "drafts" "agenda" ];
  copy = name: "cp ${pkgs.writeText "${name}.py" (fill name fixture)} ${name}.py";
in
pkgs.runCommand "alfredo-tools-tests" {
  nativeBuildInputs = [ (pkgs.python3.withPackages (ps: with ps; [ cookidoo-api mcp recipe-scrapers icalendar recurring-ical-events tzdata pytest ])) ];
  TZ = "Europe/Lisbon";   # the agenda's local time, which a build has none of
} ''
  ${lib.concatMapStringsSep "\n" copy ([ "recipes" "language" ] ++ programs)}
  ${lib.concatMapStringsSep "\n" (name: "cp ${./. + "/${name}/test_${name}.py"} test_${name}.py") ([ "language" ] ++ programs)}
  python -m pytest -q -p no:cacheprovider
  touch $out
''
