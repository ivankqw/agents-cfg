#!/usr/bin/env bash
# One-command bootstrap from a bare machine (Linux or macOS).
#   curl -fsSL https://raw.githubusercontent.com/ivankqw/agents-cfg/main/bootstrap.sh | bash
set -euo pipefail

DEST="${AGENTS_CFG_DIR:-$HOME/agents-cfg}"
REPO="${AGENTS_CFG_REPO:-https://github.com/ivankqw/agents-cfg.git}"
PSTACK_DIR="${PSTACK_DIR:-$HOME/.local/share/agent-plugins/pstack-claude}"
PSTACK_REPO="${PSTACK_REPO:-https://github.com/michael-denyer/pstack-claude.git}"

case "$(uname -s)" in Linux|Darwin) ;; *) echo "unsupported OS: $(uname -s)" >&2; exit 1;; esac
for c in git python3; do command -v "$c" >/dev/null || { echo "missing prerequisite: $c" >&2; exit 1; }; done

resolve_for_compare() { # resolve_for_compare <path>
  python3 - "$1" <<'PY'
import pathlib
import sys

print(pathlib.Path(sys.argv[1]).resolve(strict=False))
PY
}

preflight_skills_lock() { # preflight_skills_lock <repo-lock> <home-lock>
  repo_lock="$(resolve_for_compare "$1")"
  home_lock="$2"
  if [ -L "$home_lock" ]; then
    target="$(readlink "$home_lock")"
    case "$target" in
      /*) target_path="$target" ;;
      *) target_path="$(dirname "$home_lock")/$target" ;;
    esac
    current_lock="$(resolve_for_compare "$target_path")"
    if [ "$current_lock" != "$repo_lock" ]; then
      echo "refusing to retarget skills lock symlink: $home_lock -> $target" >&2
      exit 1
    fi
  elif [ -e "$home_lock" ]; then
    echo "refusing to replace non-symlink skills lock: $home_lock" >&2
    exit 1
  fi
}

preflight_skills_lock "$DEST/skills-lock.json" "$HOME/skills-lock.json"

if [ -d "$DEST/.git" ]; then echo "== updating $DEST"; git -C "$DEST" pull --ff-only
else echo "== cloning into $DEST"; git clone --depth 1 "$REPO" "$DEST"; fi

PSTACK_REVISION="$(sed -n '1p' "$DEST/pstack-revision.txt")"
if ! printf '%s\n' "$PSTACK_REVISION" | grep -Eq '^[0-9a-f]{40}$'; then
  echo "invalid pstack revision in $DEST/pstack-revision.txt" >&2
  exit 1
fi
if [ -e "$PSTACK_DIR" ] && [ ! -d "$PSTACK_DIR/.git" ]; then
  echo "pstack path exists but is not a git checkout: $PSTACK_DIR" >&2
  exit 1
fi
if [ -d "$PSTACK_DIR/.git" ]; then
  if [ -n "$(git -C "$PSTACK_DIR" status --porcelain)" ]; then
    echo "pstack checkout has local changes; leaving it unchanged: $PSTACK_DIR" >&2
    exit 1
  fi
  echo "== fetching pinned pstack revision"
  git -C "$PSTACK_DIR" fetch origin "$PSTACK_REVISION"
else
  echo "== cloning pstack into $PSTACK_DIR"
  mkdir -p "$(dirname "$PSTACK_DIR")"
  git clone "$PSTACK_REPO" "$PSTACK_DIR"
fi
if ! git -C "$PSTACK_DIR" cat-file -e "$PSTACK_REVISION^{commit}" 2>/dev/null; then
  echo "pstack revision is missing after fetch: $PSTACK_REVISION" >&2
  exit 1
fi
git -C "$PSTACK_DIR" checkout --detach "$PSTACK_REVISION"

if command -v npx >/dev/null; then
  echo "== restoring third-party skills from the lockfile"
  python3 "$DEST/scripts/skill_metadata.py" install-lock "$DEST/skills-lock.json" "$HOME/skills-lock.json"
  ( cd "$HOME" && npx --yes skills@latest experimental_install )
else
  echo "!! node/npx not found — skipping third-party skills. Later run:"
  echo "   cd ~ && npx skills experimental_install"
fi

"$DEST/install.sh"

case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  echo; echo "!! add this to your shell profile:"; echo '   export PATH="$HOME/.local/bin:$PATH"';;
esac
echo; echo "== done. Verify with the check in $DEST/AGENTS.md"
