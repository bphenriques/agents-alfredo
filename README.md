# Alfredo

A household assistant for [hermes-agent](https://github.com/NousResearch/hermes-agent), built for a local model. It plans the week's meals, keeps a [Cooklang](https://cooklang.org) recipe library, and reads and files notes in an Obsidian vault. It speaks Portuguese.

Small local models are unreliable at composing structured output, so the code composes and the model relays. Tools return short text ready to show, and skills tell the model when to call them.

## Use

This repo is the agent's definition: persona, skills, tools and tool policy. The host runs it and owns the model, network, mounts and state.

```nix
alfredo = inputs.agents-alfredo.lib.alfredo {
  inherit pkgs;
  facts = {
    vaultRoot = "/var/lib/vault";
    recipesRoot = "/var/lib/recipes";
    stateRoot = "/var/lib/hermes";
    recipesUrl = "https://recipes.example.com";
    modelUrl = "http://<ollama>:11434";
    model = "<model>";
    speechUrl = "http://<whisper>/inference";
    cookidooCollection = "<collection>";
  };
};
```

Wire the result into `services.hermes-agent`: `soul` as `SOUL.md`, `workspace` as the workspace `AGENTS.md`, plus `packages`, `mcpServers` and `settings`. Append anything personal to `soul` on the host.

The tool policy steers the model but is not a boundary: `terminal` runs anything the `hermes` user can. Run it in a VM.

## Meals ("Cozinha")

- [meals](./tools/meals/meals.py): MCP server that plans the week from the library and saves plans to `plans/<date>.menu`. Saving also fills Cookidoo's My week and shopping list.
- [cookidoo](./tools/cookidoo/cookidoo.py): the only Cookidoo client. Syncs a collection into the library, and writes My week and the shopping list without touching your own entries.
- [drafts](./tools/drafts/drafts.py): drafts recipes from pages ([recipe-scrapers](https://github.com/hhursev/recipe-scrapers)), videos (yt-dlp, then whisper) or text, plus `aisle.conf` entries, into `drafts/<folder>/`. `promote` moves a reviewed draft into the library.
- [cook-mcp](https://github.com/cook-md/cook-mcp): reads recipe files. Search is `find_recipes` in meals, which takes food names in any form `aisle.conf` knows.

The tools' tests run on build, so a failing test blocks the deploy. `nix flake check` runs them alone.

| to | do |
|---|---|
| sign in to Cookidoo | `sudo -u hermes cookidoo login` |
| check planning | `sudo -u hermes meals propose` |
| draft an import by hand | `sudo -u hermes drafts new <url>` |
| replace a library recipe | copy it into `drafts/<folder>/`, edit it, then `sudo -u hermes drafts promote "<new name>" --replace "<name>"` |
| complete aisle.conf | `sudo -u hermes drafts aisle`, then `drafts promote aisle.conf` |
