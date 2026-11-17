# Alfredo

A personal assistant for [hermes-agent](https://github.com/NousResearch/hermes-agent), built for a local model. It speaks Portuguese.

Small local models are unreliable at composing structured output, so the code composes and the model relays. Tools return short text ready to show, and skills tell the model when to call them.

## Skills

| Skill | Does |
|---|---|
| [meal-planning](./skills/meal-planning/SKILL.md) | Plans the week's meals from the recipe library and fills Cookidoo's My week and shopping list |
| [recipe-import](./skills/recipe-import/SKILL.md) | Drafts a recipe from a web page or video into the library |
| [recipe-new](./skills/recipe-new/SKILL.md) | Drafts a recipe the user describes |
| [recipe-aisle](./skills/recipe-aisle/SKILL.md) | Completes the shopping list's sections and ingredient names |
| youtube-content, pdf | Upstream hermes-agent skills |

Without a skill, it reads and files notes in an Obsidian vault, searches the web and fetches pages.

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
    modelUrl = "http://<inference>:11434/v1";   # OpenAI-compatible base URL
    model = "<model>";
    speechUrl = "http://<whisper>/inference";
    cookidooCollection = "<collection>";
  };
};
```

Wire the result into `services.hermes-agent`: `soul` as `SOUL.md`, `workspace` as the workspace `AGENTS.md`, plus `packages`, `mcpServers` and `settings`. Append anything personal to `soul` on the host.

The tool policy steers the model but is not a boundary: `terminal` runs anything the `hermes` user can. Run it in a VM.

The programs in [tools](./tools) are tested on build, so a failing test blocks the deploy. `nix flake check` runs them alone.

## Privacy

Alfredo runs on its owner's hardware and serves only its owner. What it reads and writes stays on that host and the services the owner connects it to. It shares nothing with anyone else.
