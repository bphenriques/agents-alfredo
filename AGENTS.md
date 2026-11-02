# Agent Instructions

Alfredo, a household assistant for hermes-agent. Overview in [README.md](./README.md).

## Privacy

- Public repo. Nothing household-specific: no names, addresses, credentials, collection ids or URLs of real hosts. The host supplies those through `facts` or appends them to `soul`.
- Tests and fixtures use made-up data (`recipes.test`, generic dishes).

## Design

- The model relays, the code composes. A tool returns short text ready to show, never structured data for the model to format.
- Skills say when to call a tool and to relay its reply verbatim. Rules live in the tools.
- The definition is a plain function of `pkgs` and `facts`. It never names a host, network or secret backend.

## Tools

- Python under `tools/<name>/<name>.py`. `@placeholders@` are filled by Nix, and an unfilled one fails the build.
- Every tool has a pytest file beside it, run on build against `tools/fixtures`. Add a test with every behaviour change.
- `nix flake check` runs the tests.

## Code style

- Simple and idiomatic. Match neighbouring files.
- YAGNI. No option or parameter without a second use.

## Comments

- Default to none. Comment only what the code can't say: the why, a non-obvious constraint.
- One line, succinct.

## Writing

- Plain declaratives, point first. No em-dashes, no semicolons.
- No LLM cadence: no "not just X but Y", no padded threes, no restating a point.
- Say it once. Cut every word the sentence survives without.
