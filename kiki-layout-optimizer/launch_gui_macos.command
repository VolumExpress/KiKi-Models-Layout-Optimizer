#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  osascript -e 'display alert "KiKi Models" message "Run install_macos.command once to install Python packages."' 2>/dev/null || true
  exit 1
fi
.venv/bin/python -m kiki_layout.gui
