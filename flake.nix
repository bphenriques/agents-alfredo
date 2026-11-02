{
  description = "Alfredo: a household assistant for hermes-agent on a local model";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    hermes-agent.url = "github:NousResearch/hermes-agent/v0.22.0";
    hermes-agent.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { nixpkgs, hermes-agent, ... }:
    let
      system = "x86_64-linux";   # cook-mcp ships no other build
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      # The host passes its facts (paths, endpoints, model) and runs the result under hermes-agent's NixOS module.
      lib.alfredo = { pkgs, facts }: import ./. { inherit pkgs facts hermes-agent; inherit (pkgs) lib; };

      packages.${system}.cook-mcp = pkgs.callPackage ./packages/cook-mcp.nix { };

      checks.${system}.tools = (import ./tools { inherit pkgs; inherit (pkgs) lib; facts = { }; }).tests;
    };
}
