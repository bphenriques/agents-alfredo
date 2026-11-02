# The tools' tests, against ./fixtures.
{ pkgs, lib }:
let
  fill = import ./fill.nix { inherit lib; };
  fixture = { tokenFile = "token.json"; planFile = "plan.json"; library = "${./fixtures}"; site = "https://recipes.test";
              collection = "test"; cookidoo = "cookidoo"; drafts = "drafts"; modelUrl = "http://model.test";
              model = "test"; speechUrl = "http://speech.test"; ytDlp = "yt-dlp"; curl = "curl"; magick = "magick";
              cook = lib.getExe pkgs.cook-cli; };
  copy = name: "cp ${pkgs.writeText "${name}.py" (fill name fixture)} ${name}.py";
in
pkgs.runCommand "alfredo-tools-tests" {
  nativeBuildInputs = [ (pkgs.python3.withPackages (ps: with ps; [ cookidoo-api mcp recipe-scrapers pytest ])) ];
} ''
  ${lib.concatMapStringsSep "\n" copy [ "recipes" "cookidoo" "meals" "drafts" ]}
  cp ${./cookidoo/test_cookidoo.py} test_cookidoo.py
  cp ${./meals/test_meals.py} test_meals.py
  cp ${./drafts/test_drafts.py} test_drafts.py
  python -m pytest -q -p no:cacheprovider
  touch $out
''
