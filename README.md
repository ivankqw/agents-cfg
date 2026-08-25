# agents-cfg

My agent setup for [Claude Code](https://code.claude.com) and
[Codex](https://developers.openai.com/codex): working conventions, a few skills I wrote, an
adversarial code reviewer, an advisory pre-push hook, and a script that routes review work.

Runs on Linux and macOS. Everything installs by symlink, so `git pull` takes effect at once.

## Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/ivankqw/agents-cfg/main/bootstrap.sh | bash
```

Step by step:

```bash
git clone git@github.com:ivankqw/agents-cfg.git ~/agents-cfg
~/agents-cfg/install.sh
cd ~ && npx skills experimental_install
export PATH="$HOME/.local/bin:$PATH"   # add to your shell profile
```

Pointing an agent at this repo? Give it the URL and tell it to read [`AGENTS.md`](./AGENTS.md).
That file holds the install steps, what the install touches, and how to check it worked.

## How it is put together

**One place for my setup.** What lives here is method: how I want an agent to verify a claim, when
a change gets reviewed and by whom, how findings get written down. Nothing in this repo names an
employer, a host, or a person.

Employer conventions and domain memory sit in a separate private repo. `install.sh` layers that on
top when it finds one at `~/agents-cfg-private`, or wherever `$PRIVATE_CONFIG` points.

**One source, two harnesses.** Claude Code reads `CLAUDE.md` and expands `@imports`, so
`install.sh` writes `~/.claude/CLAUDE.md` with one import per layer. Codex reads `AGENTS.md`, where
import support is not documented, so the layers get concatenated into `~/AGENTS.md`. Re-run
`install.sh` after you edit a convention, or Codex keeps reading a stale copy.

**Third-party skills stay upstream.** Most of my skills come from other people's repos and are
managed by [`npx skills`](https://www.npmjs.com/package/skills), which keeps them in
`~/.agents/skills` with a lockfile. Copying them in here would pin them to one commit and cut them
off from `npx skills update`. This repo carries `skills-lock.json` instead, and
`npx skills experimental_install` restores each skill at its recorded commit. Only skills I wrote
live in `skills/`.

**Nothing secret.** The install writes no credential. MCP servers are declared by name and URL in
`mcp/servers.json`; keys come from the environment, and a server whose key is missing gets skipped.

## Layout

See the table in [`AGENTS.md`](./AGENTS.md).

## License

MIT. See [LICENSE](./LICENSE).

`agents/reviewer.md` adapts the adversarial stance, attack-surface list, and calibration rules from
the Codex plugin for Claude Code, Copyright 2026 OpenAI, under the Apache License 2.0. See
[NOTICE](./NOTICE).
