# agents-cfg

Portable agent configuration for [Claude Code](https://code.claude.com) and
[Codex](https://developers.openai.com/codex). Conventions, a few hand-written skills, an adversarial
code-review agent, an advisory pre-push hook, and a review-routing script.

Works on Linux and macOS. Installs by symlink, so `git pull` takes effect immediately.

## Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/ivankqw/agents-cfg/main/bootstrap.sh | bash
```

Or step by step:

```bash
git clone git@github.com:ivankqw/agents-cfg.git ~/agents-cfg
~/agents-cfg/install.sh
cd ~ && npx skills experimental_install
export PATH="$HOME/.local/bin:$PATH"   # add to your shell profile
```

**Pointing an agent at this repo?** Give it the URL and tell it to read
[`AGENTS.md`](./AGENTS.md) — that file is written for an agent and carries the install steps, what
the install touches, and how to verify it worked.

## Design

**This is my personal agent setup, kept in one place.** A new laptop, or a new job, should be a
clone away rather than a week of rebuilding from memory. What lives here is method: how I want an
agent to verify a claim, when a change gets reviewed and by whom, how findings get written down.
None of it names an employer, a host, or a person, so all of it travels.

Anything that would stop being true at a different company lives in a second, private repo, which
`install.sh` layers on top when it finds one — at `~/agents-cfg-private`, or wherever
`$PRIVATE_CONFIG` points. Employer conventions, private skills and accumulated domain memory belong
there. At a new job I clone this repo, skip the other one, and the way I work is unchanged.

**One source, two harnesses.** Claude Code reads `CLAUDE.md` and expands `@imports`, so `install.sh`
writes `~/.claude/CLAUDE.md` with one import per layer. Codex reads `AGENTS.md`, where import support
is not guaranteed, so the layers are concatenated into `~/AGENTS.md`. Re-run `install.sh` after
editing conventions, or Codex reads a stale copy.

**Third-party skills are declared, not vendored.** Most skills come from upstream repos managed by
[`npx skills`](https://www.npmjs.com/package/skills), which keeps them in `~/.agents/skills` with a
lockfile. Copying them in would freeze them at one commit and stop `npx skills update` from reaching
them. Instead this repo carries `skills-lock.json`, and the CLI's own
`npx skills experimental_install` restores every skill at its pinned commit. `install.sh` links them
into `~/.claude/skills`. Only skills written here live in `skills/`.

**Nothing secret.** No credential is stored or written. MCP servers are declared by name and URL in
`mcp/servers.json`; keys are read from the environment at install time, and a server whose key is
unset is skipped.

## Layout

See the table in [`AGENTS.md`](./AGENTS.md).

## License

MIT — see [LICENSE](./LICENSE).
