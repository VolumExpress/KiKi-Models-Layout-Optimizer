#!/bin/bash
# Safe uninstall of KiKi. Workspace and presets are kept by default.
set -euo pipefail
DEST="$HOME/Library/Application Support/KiKiModels/LayoutOptimizer"
CEP="$HOME/Library/Application Support/Adobe/CEP/extensions/com.kikimodels.layoutoptimizer"
CONFIG="$CEP/config.js"
if [[ -f "$CONFIG" ]] && grep -Fq "$DEST" "$CONFIG"; then
  rm -rf "$CEP"
  echo 'KiKi CEP extension removed'
elif [[ -f "$CONFIG" ]]; then
  echo 'CEP points elsewhere; leaving it untouched'
fi
for name in runtime cep illustrator assets installers docs; do
  [[ ! -e "$DEST/$name" ]] || rm -rf "$DEST/$name"
done
for file in LICENSE VERSION README.md README_RU.md README_EN.md CHANGELOG.md SHA256SUMS.json SHA256SUMS.txt; do
  [[ ! -e "$DEST/$file" ]] || rm "$DEST/$file"
done
if [[ "${1:-}" == '--delete-user-data' ]]; then
  rm -rf "$DEST/workspace" "$DEST/presets"
  echo 'User data removed by explicit request'
else
  echo "User data preserved at $DEST/workspace and $DEST/presets"
fi
echo 'Adobe unsigned CEP developer-mode settings were NOT modified.'
