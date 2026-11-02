# The checksum is the one cook-mcp's npm installer verifies.
{ lib, stdenv, fetchurl, autoPatchelfHook }:
stdenv.mkDerivation rec {
  pname = "cook-mcp";
  version = "0.2.3";

  src = fetchurl {
    url = "https://github.com/cook-md/cook-mcp/releases/download/v${version}/cook-mcp-x86_64-unknown-linux-gnu.tar.gz";
    sha256 = "fa7e9425b1cddcbda8bb09f55d1371d15a340d9513e44d194ac89e4c1dea2378";
  };

  sourceRoot = ".";
  nativeBuildInputs = [ autoPatchelfHook ];
  buildInputs = [ stdenv.cc.cc.lib ];
  installPhase = "install -Dm755 cook-mcp $out/bin/cook-mcp";

  meta = {
    description = "MCP server for Cooklang recipes";
    homepage = "https://github.com/cook-md/cook-mcp";
    platforms = [ "x86_64-linux" ];
    mainProgram = "cook-mcp";
  };
}
