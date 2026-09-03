# agents-cfg agent entry

This repository installs one portable layer for Claude Code and Codex.

If the user asks you to install it, read `docs/INSTALL.md` and complete each verification step.

If the user asks how it works, read these files:

- `docs/HOW-IT-WORKS.md`
- `docs/GLOSSARY.md`
- `docs/THESIS.md`
- `docs/SYNC.md`

If the user asks you to change it, read `MAINTAINING.md` and `conventions/AGENTS.md` first. Preserve
upstream source links. Keep employer, host, person, and credential data in the private layer.

Use `python3 -m unittest discover -s tests` as the canonical test command. Run `git diff --check`
before you commit.
