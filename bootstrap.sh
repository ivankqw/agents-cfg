#!/usr/bin/env bash
# One-command bootstrap from a bare machine (Linux or macOS).
#   curl -fsSL https://raw.githubusercontent.com/ivankqw/agents-cfg/main/bootstrap.sh | bash
set -euo pipefail

DEST="${AGENTS_CFG_DIR:-$HOME/agents-cfg}"
REPO="${AGENTS_CFG_REPO:-https://github.com/ivankqw/agents-cfg.git}"

case "$(uname -s)" in Linux|Darwin) ;; *) echo "unsupported OS: $(uname -s)" >&2; exit 1;; esac
for c in git python3; do command -v "$c" >/dev/null || { echo "missing prerequisite: $c" >&2; exit 1; }; done

if [ -d "$DEST/.git" ]; then echo "== updating $DEST"; git -C "$DEST" pull --ff-only
else echo "== cloning into $DEST"; git clone --depth 1 "$REPO" "$DEST"; fi

if command -v npx >/dev/null; then "$DEST/bootstrap-skills.sh"
else echo "!! node/npx not found — skipping third-party skills; run ./bootstrap-skills.sh later"; fi

"$DEST/install.sh"

case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  echo; echo "!! add this to your shell profile:"; echo '   export PATH="$HOME/.local/bin:$PATH"';;
esac
echo; echo "== done. Verify with the check in $DEST/AGENTS.md"
