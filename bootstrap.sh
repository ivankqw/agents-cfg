#!/usr/bin/env bash
# One-command bootstrap from a bare machine (Linux or macOS).
#   curl -fsSL https://raw.githubusercontent.com/ivankqw/agents-cfg/main/bootstrap.sh | bash
set -euo pipefail

DEST="${AGENTS_CFG_DIR:-$HOME/agents-cfg}"
REPO="${AGENTS_CFG_REPO:-https://github.com/ivankqw/agents-cfg.git}"
PSTACK_DIR="${PSTACK_DIR:-$HOME/.local/share/agent-plugins/pstack-claude}"
PSTACK_REPO="${PSTACK_REPO:-https://github.com/michael-denyer/pstack-claude.git}"
PRIVATE="${PRIVATE_CONFIG:-$HOME/agents-cfg-private}"

case "$(uname -s)" in Linux|Darwin) ;; *) echo "unsupported OS: $(uname -s)" >&2; exit 1;; esac
for c in git python3; do command -v "$c" >/dev/null || { echo "missing prerequisite: $c" >&2; exit 1; }; done

preflight_operator_state() {
  python3 "$DEST/scripts/skill_metadata.py" preflight-ponytail \
    "$DEST/skills/ponytail" "$HOME/.agents/skills"
  python3 "$DEST/scripts/skill_metadata.py" preflight-private-ponytail "$PRIVATE"
}

if [ -e "$DEST/.git" ]; then
  echo "== updating $DEST"
  git -C "$DEST" pull --ff-only
else
  echo "== cloning into $DEST"
  git clone --depth 1 "$REPO" "$DEST"
fi

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
  preflight_operator_state
  echo "== fetching pinned pstack revision"
  git -C "$PSTACK_DIR" fetch origin "$PSTACK_REVISION"
else
  preflight_operator_state
  echo "== cloning pstack into $PSTACK_DIR"
  mkdir -p "$(dirname "$PSTACK_DIR")"
  git clone "$PSTACK_REPO" "$PSTACK_DIR"
fi
if ! git -C "$PSTACK_DIR" cat-file -e "$PSTACK_REVISION^{commit}" 2>/dev/null; then
  echo "pstack revision is missing after fetch: $PSTACK_REVISION" >&2
  exit 1
fi
preflight_operator_state
git -C "$PSTACK_DIR" checkout --detach "$PSTACK_REVISION"

python3 "$DEST/scripts/skill_metadata.py" preflight-pstack \
  "$PSTACK_DIR" "$DEST/pstack-revision.txt"
preflight_operator_state

set +e
"$DEST/install.sh"
install_rc=$?
set -e

if [ "$install_rc" -ne 0 ]; then
  exit "$install_rc"
fi

case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  echo; echo "!! add this to your shell profile:"; echo '   export PATH="$HOME/.local/bin:$PATH"';;
esac
echo; echo "== done. Verify with the check in $DEST/AGENTS.md"
