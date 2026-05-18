#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZSHRC="$HOME/.zshrc"
INIT_LINE='eval "$(bashmage --init)"'

echo "→ Installing bashmage..."
uv tool install --editable "$SCRIPT_DIR"

if grep -qF "$INIT_LINE" "$ZSHRC" 2>/dev/null; then
    echo "→ Shell integration already in $ZSHRC"
else
    printf '\n# BashMage shell integration\n%s\n' "$INIT_LINE" >> "$ZSHRC"
    echo "→ Shell integration added to $ZSHRC"
fi

echo "→ Reloading $ZSHRC..."
# shellcheck disable=SC1090
if source "$ZSHRC" 2>/dev/null; then
    echo "✓ Done. Ctrl+B and 'bm' are ready."
else
    echo "✓ Done. Run 'source ~/.zshrc' or open a new terminal to activate Ctrl+B and 'bm'."
fi
