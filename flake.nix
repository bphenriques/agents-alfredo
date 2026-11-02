{
  description = "Alfredo: a household assistant for hermes-agent on a local model";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    hermes-agent.url = "github:NousResearch/hermes-agent/v0.22.0";
    hermes-agent.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, hermes-agent, ... }:
    let
      system = "x86_64-linux";   # cook-mcp ships no other build
      pkgs = nixpkgs.legacyPackages.${system};
      example = {
        vaultRoot = "/var/lib/vault"; recipesRoot = "/var/lib/recipes"; stateRoot = "/var/lib/hermes";
        recipesUrl = "https://recipes.test"; modelUrl = "http://model.test"; model = "test";
        speechUrl = "http://speech.test"; cookidooCollection = "test";
      };
    in
    {
      # The host passes its facts (paths, endpoints, model) and runs the result under hermes-agent's NixOS module.
      lib.alfredo = { pkgs, facts }: import ./. { inherit pkgs facts hermes-agent; inherit (pkgs) lib; };

      packages.${system}.cook-mcp = pkgs.callPackage ./packages/cook-mcp.nix { };

      checks.${system} = {
        tools = import ./tools/tests.nix { inherit pkgs; inherit (pkgs) lib; };
        definition = pkgs.writeText "alfredo.json" (builtins.toJSON { inherit (self.lib.alfredo { inherit pkgs; facts = example; }) settings mcpServers; });
      };
    };
}
