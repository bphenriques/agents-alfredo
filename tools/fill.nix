# A tool's source with its @placeholders@ filled; one left unfilled fails the build.
{ lib }:
name: values:
let
  text = builtins.replaceStrings (map (k: "@${k}@") (builtins.attrNames values)) (builtins.attrValues values)
    (builtins.readFile (./. + "/${name}/${name}.py"));
  left = builtins.filter builtins.isList (builtins.split "@([A-Za-z]+)@" text);
in
lib.throwIf (left != [ ]) "${name}.py: no value for ${lib.concatMapStringsSep ", " (m: "@${builtins.head m}@") left}" text
