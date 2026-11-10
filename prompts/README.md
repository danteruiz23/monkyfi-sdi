# prompts

Stable system prompt, tool definitions and output modes (SPEC 7.3). Every file starts with a `prompt_version` tag; the version is stored with every extraction run. Changing a prompt requires re-running the evals.

- `system.md` — stable system prompt: guardrails that apply to every call.
- `extract_fields.md` — Phase 2 task: list the catalog values one document prints, verbatim, with page and location. The catalog is built from `rules/fields.*.json`; the answer schema from the same list.

Output modes (full intake, incremental update, communications only) come in later phases.
