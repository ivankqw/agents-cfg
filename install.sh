#!/usr/bin/env bash
# Install the agent config onto this machine. Idempotent — safe to re-run.
#
# Layers: this repo is the portable method layer. If ~/agents-cfg-private (or
# $PRIVATE_CONFIG) exists it is layered on top. At a new job, clone only this
# repo and the workflows stay identical minus the employer specifics.
set -euo pipefail

for c in git python3; do
  command -v "$c" >/dev/null || { echo "missing prerequisite: $c" >&2; exit 1; }
done
case "$(uname -s)" in Linux|Darwin) ;; *) echo "unsupported OS: $(uname -s)" >&2; exit 1;; esac
if ! command -v bun >/dev/null; then
  echo "  ! bun is missing; pstack watch-pr and orch are unavailable"
  echo "  ! install bun from https://bun.sh, then re-run this install"
fi

AC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIVATE="${PRIVATE_CONFIG:-$HOME/agents-cfg-private}"
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"
SHARED_SKILLS="$HOME/.agents/skills"
PSTACK_DIR="${PSTACK_DIR:-$HOME/.local/share/agent-plugins/pstack-claude}"
BIN="$HOME/.local/bin"
mkdir -p "$CLAUDE_DIR"/{skills,agents,hooks} "$CODEX_DIR"/{hooks,prompts} "$SHARED_SKILLS" "$BIN"

link() { # link <target> <linkname>
  [ -e "$1" ] || return 0
  if [ -L "$2" ] || [ ! -e "$2" ]; then ln -sfn "$1" "$2"
  else echo "  ! not a symlink, leaving alone: $2"; fi
}

echo "== skills"
# Third-party skills stay installer-managed in ~/.agents/skills so that
# `npx skills update` keeps them fresh. We only link them into place — vendoring
# them would freeze them at one commit and cut them off from upstream.
# The `skills` CLI reads skills-lock.json from the CURRENT directory and installs
# into ./.agents/skills — so running it from $HOME targets ~/.agents/skills.
link "$AC/skills-lock.json" "$HOME/skills-lock.json"
for d in "$AC"/skills/*/; do link "${d%/}" "$SHARED_SKILLS/$(basename "$d")"; done
[ -d "$PRIVATE/skills" ] && for d in "$PRIVATE"/skills/*/; do link "${d%/}" "$SHARED_SKILLS/$(basename "$d")"; done

PSTACK_REVISION="$(sed -n '1p' "$AC/pstack-revision.txt")"
if ! printf '%s\n' "$PSTACK_REVISION" | grep -Eq '^[0-9a-f]{40}$'; then
  echo "invalid pstack revision in $AC/pstack-revision.txt" >&2; exit 1
fi
if [ ! -d "$PSTACK_DIR/.git" ]; then
  echo "pstack checkout is missing: $PSTACK_DIR" >&2
  echo "run $AC/bootstrap.sh, or clone the pinned checkout first" >&2
  exit 1
fi
PSTACK_RESOLVED="$(cd "$PSTACK_DIR" && pwd -P)"
PSTACK_ACTUAL="$(git -C "$PSTACK_DIR" rev-parse HEAD)"
if [ "$PSTACK_ACTUAL" != "$PSTACK_REVISION" ]; then
  echo "pstack revision mismatch: expected $PSTACK_REVISION, found $PSTACK_ACTUAL" >&2
  exit 1
fi
if [ -n "$(git -C "$PSTACK_DIR" status --porcelain)" ]; then
  echo "pstack checkout has local changes; leaving it unchanged: $PSTACK_DIR" >&2
  exit 1
fi
if [ ! -d "$PSTACK_DIR/plugins/pstack/skills" ] || \
   [ ! -d "$PSTACK_DIR/plugins/pstack/.codex-plugin/prompts" ]; then
  echo "pstack checkout does not contain the expected plugin layout: $PSTACK_DIR" >&2
  exit 1
fi
PSTACK_SKILLS="$PSTACK_RESOLVED/plugins/pstack/skills"
PSTACK_PROMPTS="$PSTACK_RESOLVED/plugins/pstack/.codex-plugin/prompts"
python3 - "$SHARED_SKILLS" "$CODEX_DIR/prompts" "$PSTACK_SKILLS" "$PSTACK_PROMPTS" <<'PY'
import os, pathlib, sys

shared = pathlib.Path(sys.argv[1])
prompts = pathlib.Path(sys.argv[2])
skill_root = pathlib.Path(sys.argv[3])
prompt_root = pathlib.Path(sys.argv[4])

def target_of(link):
    target = pathlib.Path(os.readlink(str(link)))
    if not target.is_absolute():
        target = link.parent / target
    return target.resolve(strict=False)

def is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

def prune(link, root):
    if not link.is_symlink():
        return
    target = target_of(link)
    if is_within(target, root) and not target.exists():
        link.unlink()
        print(f"  remove stale pstack link: {link}")

for entry in shared.iterdir():
    prune(entry, skill_root)
    if entry.is_dir() and not entry.is_symlink():
        prune(entry / entry.name, skill_root)
for entry in prompts.iterdir():
    prune(entry, prompt_root)
PY
for d in "$PSTACK_RESOLVED"/plugins/pstack/skills/*/; do
  name="$(basename "$d")"
  destination="$SHARED_SKILLS/$name"
  if [ -d "$destination" ] && [ ! -L "$destination" ]; then
    link "${d%/}" "$destination/$name"
  else
    link "${d%/}" "$destination"
  fi
done
for f in "$PSTACK_PROMPTS"/*.md; do
  link "$f" "$CODEX_DIR/prompts/$(basename "$f")"
done

for d in "$SHARED_SKILLS"/*/; do link "${d%/}" "$CLAUDE_DIR/skills/$(basename "$d")"; done

echo "== unlocking skills listed in skills-unlock.txt"
if [ -f "$AC/skills-unlock.txt" ]; then
  python3 - "$AC/skills-unlock.txt" "$HOME/.agents/skills" <<'PYEOF'
import pathlib, re, sys
names = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
root = pathlib.Path(sys.argv[2])
for n in names:
    f = root / n / "SKILL.md"
    if not f.exists():
        print(f"  skip {n}: not installed"); continue
    s = f.read_text()
    s2 = re.sub(r"^disable-model-invocation:[ \t]*true[ \t]*\n", "", s, count=1, flags=re.M)
    if s == s2:
        print(f"  {n}: already unlocked")
    else:
        f.write_text(s2); print(f"  {n}: unlocked")
PYEOF
fi

echo "== agents / hooks"
for f in "$AC"/agents/*.md;  do link "$f" "$CLAUDE_DIR/agents/$(basename "$f")"; done
STALE_HOOK="$CLAUDE_DIR/hooks/codex_review_reminder.py"
if [ -L "$STALE_HOOK" ]; then
  rm -f "$STALE_HOOK"
elif [ -e "$STALE_HOOK" ]; then
  echo "  ! not a symlink, leaving alone: $STALE_HOOK"
fi
for f in "$AC"/hooks/*;      do link "$f" "$CLAUDE_DIR/hooks/$(basename "$f")"; done
for f in "$AC"/hooks/*;      do link "$f" "$CODEX_DIR/hooks/$(basename "$f")"; done

echo "== bin"
for f in "$AC"/bin/*;        do link "$f" "$BIN/$(basename "$f")"; done
[ -d "$PRIVATE/bin" ] && for f in "$PRIVATE"/bin/*; do link "$f" "$BIN/$(basename "$f")"; done

echo "== instruction files"
# Claude reads CLAUDE.md and expands @imports natively, so edits are live.
link "$AC/conventions/AGENTS.md" "$CLAUDE_DIR/AGENTS.portable.md"
: > "$CLAUDE_DIR/CLAUDE.md.tmp"
echo "@AGENTS.portable.md" >> "$CLAUDE_DIR/CLAUDE.md.tmp"
if [ -f "$PRIVATE/AGENTS.md" ]; then
  link "$PRIVATE/AGENTS.md" "$CLAUDE_DIR/AGENTS.private.md"
  echo "@AGENTS.private.md" >> "$CLAUDE_DIR/CLAUDE.md.tmp"
fi
mv -f "$CLAUDE_DIR/CLAUDE.md.tmp" "$CLAUDE_DIR/CLAUDE.md"

# Codex reads AGENTS.md. Concatenate rather than rely on @import support.
{ echo "<!-- GENERATED by agent-config/install.sh — edit the source repos, then re-run -->"; echo
  cat "$AC/conventions/AGENTS.md"
  [ -f "$PRIVATE/AGENTS.md" ] && { echo; cat "$PRIVATE/AGENTS.md"; }
  echo; cat "$AC/configs/pstack-codex.md"
} > "$HOME/AGENTS.md"
link "$HOME/AGENTS.md" "$CODEX_DIR/AGENTS.md"
link "$AC/configs/pstack-codex.md" "$CODEX_DIR/pstack-models.md"

echo "== mcp servers (keys from env; nothing secret is stored in this repo)"
if command -v claude >/dev/null && [ -f "$AC/mcp/servers.json" ]; then
  python3 - "$AC/mcp/servers.json" <<'PY'
import json,os,subprocess,sys
for s in json.load(open(sys.argv[1]))["servers"]:
    name,url = s["name"], s["url"]
    env = s.get("header_env")
    if env and not os.environ.get(env):
        print(f"  skip {name}: ${env} not set"); continue
    cmd=["claude","mcp","add","--scope","user","--transport","http",name,url]
    if env: cmd += ["--header", f"{s['header_name']}: {os.environ[env]}"]
    r=subprocess.run(cmd,capture_output=True,text=True)
    print(f"  {'ok' if r.returncode==0 else 'exists/failed'} {name}")
PY
fi

echo "== Codex settings"
CODEX_CONFIG="$CODEX_DIR/config.toml"
missing="$(python3 - "$CODEX_CONFIG" "$HOME" "$PSTACK_RESOLVED" <<'PY'
import pathlib, re, sys

path = pathlib.Path(sys.argv[1])
home = sys.argv[2]
pstack_dir = sys.argv[3]
sections = {}
arrays = {}
section = None
hook_parents = {}

def strip_comment(line):
    quote = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if char in ("'", '"'):
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == "#" and quote is None:
            return line[:index]
    return line

if path.is_file():
    for raw in path.read_text().splitlines():
        line = strip_comment(raw).strip()
        if not line:
            continue
        match = re.fullmatch(r"\[\[([^]]+)\]\]", line)
        if match:
            section = match.group(1)
            values = {}
            if section in ("hooks.PreToolUse", "hooks.PostToolUse"):
                hook_parents[section] = values
            elif section == "hooks.PreToolUse.hooks":
                values["_parent"] = hook_parents.get("hooks.PreToolUse", {})
            elif section == "hooks.PostToolUse.hooks":
                values["_parent"] = hook_parents.get("hooks.PostToolUse", {})
            arrays.setdefault(section, []).append(values)
            continue
        match = re.fullmatch(r"\[([^]]+)\]", line)
        if match:
            section = match.group(1)
            values = sections.setdefault(section, {})
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)\s*=\s*(.+)", line)
        if section is not None and match:
            values[match.group(1)] = match.group(2).strip()

missing = []
features = sections.get("features", {})
if features.get("hooks") != "true":
    missing.append("hooks")
if features.get("multi_agent") != "true":
    missing.append("multi_agent")

plugin = sections.get('plugins."pstack@pstack-claude"', {})
if plugin.get("enabled") != "true":
    missing.append("pstack-plugin")

marketplace = sections.get("marketplaces.pstack-claude", {})
source = marketplace.get("source", "")
if len(source) >= 2 and source[0] == source[-1] and source[0] in ("'", '"'):
    source = source[1:-1]
try:
    source_matches = pathlib.Path(source).expanduser().resolve() == pathlib.Path(pstack_dir)
except (OSError, RuntimeError):
    source_matches = False
if marketplace.get("source_type") != '"local"' or not source_matches:
    missing.append("pstack-marketplace")

hook_ok = False
for values in arrays.get("hooks.PreToolUse.hooks", []):
    command = values.get("command", "")
    parent = values.get("_parent", {})
    if (parent.get("matcher") == '"^Bash$"' and values.get("type") == '"command"'
            and home + "/.codex/hooks/review_reminder.py" in command):
        hook_ok = True
if not hook_ok:
    missing.append("review-hook")

cleanup_hook_ok = False
for values in arrays.get("hooks.PostToolUse.hooks", []):
    command = values.get("command", "")
    parent = values.get("_parent", {})
    if (parent.get("matcher") == '"^Bash$"' and values.get("type") == '"command"'
            and home + "/.codex/hooks/cleanup_crew_after_pr.py" in command):
        cleanup_hook_ok = True
if not cleanup_hook_ok:
    missing.append("cleanup-hook")
print(" ".join(missing))
PY
)"
if [ -n "$missing" ]; then
  echo "  ! missing Codex settings: $missing"
  echo "  ! merge $AC/settings/codex.config.template.toml into $CODEX_CONFIG"
  echo "  ! replace HOME_PATH in the template with $HOME"
fi

echo "== done. Merge the settings templates by hand."
