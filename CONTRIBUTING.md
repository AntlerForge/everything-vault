# Contributing

Thanks for considering a contribution to Everything Vault. The project is small and opinionated, so a few notes on what tends to fit.

## Principles

- **Local-first stays local.** No cloud sync, telemetry, or third-party API keys in core. Optional integrations (e.g. an MCP server for a specific LLM platform) are fine if they're clearly opt-in.
- **Plain markdown + YAML.** The vault format is the contract. Don't propose binary formats, proprietary file types, or schemas that can only be read by special tools.
- **Read-mostly by default.** Tools that surface findings and propose actions are preferred over tools that auto-merge, auto-delete, or auto-rewrite. The user is always in the loop.
- **Small over feature-rich.** EV is meant to be one thing well, not a personal-knowledge cathedral. Features that overlap with what users can already do in markdown are usually not worth adding.

## What to contribute

Good fits:

- Bug fixes (especially in the dashboard build script, board parser, or query tool)
- New scheduled-task examples
- New skill prompts for capabilities not covered yet
- New `PLATFORM-<NAME>.md` files for LLM hosts that don't have one yet (e.g. Codex CLI, VS Code with MCP, ChatGPT custom GPTs, local-model setups). The two bundled files — `PLATFORM-CURSOR.md` and `PLATFORM-CLAUDE.md` — show the shape; new platforms slot in without changing the core.
- Documentation improvements
- Accessibility improvements to the dashboard
- Performance improvements (the indexer and dashboard build are linear scans of the vault — there's room to do better at large scale)
- New example articles for the example vault, especially in domains that are currently sparse

Less good fits:

- Cloud sync, account systems, payment integration
- Anything that requires a server you don't control
- Schema changes that break backwards compatibility (without a clear migration story)
- LLM-specific features that only work with one provider

## How to contribute

1. Open an issue first if it's a substantial change. Sketch the idea before writing code.
2. Fork, branch, work.
3. Run the existing tools against `example-vault/` to make sure they still pass.
4. Update docs that describe the area you changed.
5. Open a pull request with a clear description of what changed and why.

## Code style

- Python: follow PEP 8 broadly. The existing tools deliberately avoid external dependencies; please match that unless you have a strong reason. PyYAML is optional — fall back to the lightweight parsers if it's not installed.
- Markdown: keep lines under ~100 chars. Use descriptive headings. Don't add bold to entire sentences.
- Shell scripts: target bash 3.2+ (default on macOS). Quote variables. `set -e` when appropriate.

## Testing

There's no test suite — yet. If you add one, prefer simple Python unittest in a `tests/` folder using the example vault as a fixture. Tests that hit the live filesystem are fine; tests that hit external services are not.

## License

By contributing, you agree your work is licensed under the MIT license (the same as the rest of the project).
