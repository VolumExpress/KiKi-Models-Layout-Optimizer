#!/bin/bash
# Transparent per-user installer; uses only macOS built-in utilities.
set -euo pipefail
SCRIPT="$(cd -- "$(dirname -- "$0")" && pwd)"
SRC="$(cd -- "$SCRIPT/../.." && pwd)"
DEST="$HOME/Library/Application Support/KiKiModels/LayoutOptimizer"
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions/com.kikimodels.layoutoptimizer"
if [[ ! -f "$SRC/runtime/kiki-worker" ]]; then
  echo 'macOS runtime missing. Use a native-built portable release.' >&2; exit 1
fi
if [[ ! -f "$SRC/SHA256SUMS.txt" ]]; then echo 'No SHA256SUMS.txt' >&2; exit 1; fi
( cd "$SRC" && shasum -a 256 -c SHA256SUMS.txt ) || { echo 'Integrity check failed' >&2; exit 1; }
mkdir -p "$DEST" "$CEP"
for item in runtime cep illustrator assets installers docs third_party_licenses; do
  [[ ! -e "$SRC/$item" ]] || ditto "$SRC/$item" "$DEST/$item"
done
for file in LICENSE VERSION README.md README_RU.md README_EN.md CHANGELOG.md THIRD_PARTY_NOTICES.md SHA256SUMS.json SHA256SUMS.txt; do
  [[ ! -e "$SRC/$file" ]] || cp "$SRC/$file" "$DEST/$file"
done
ditto "$DEST/cep/com.kikimodels.layoutoptimizer" "$CEP"
# macOS paths can contain backslashes/quotes; escape for JavaScript string literal.
Q="$(printf '%s' "$DEST" | sed 's/\\/\\\\/g;s/"/\\"/g')"
printf 'window.KIKI_PROJECT_ROOT = "%s";\n' "$Q" > "$CEP/config.js"
chmod +x "$DEST/runtime/kiki-worker"
echo "Installed: $DEST"
if [[ "${1:-}" != '--noninteractive' ]]; then
  read -r -p 'Enable unsigned Adobe CEP developer mode? (y/N) ' yn
  if [[ "$yn" == y || "$yn" == Y ]]; then
    defaults write com.adobe.CSXS.11 PlayerDebugMode -int 1
    defaults write com.adobe.CSXS.12 PlayerDebugMode -int 1
    echo 'Unsigned CEP developer mode enabled for this user.'
  fi
else
  echo 'Noninteractive mode: unsigned developer mode was NOT enabled.'
fi
echo 'Restart Illustrator.'
