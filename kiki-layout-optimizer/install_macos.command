#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv || { echo 'Install Python 3.10+ from python.org'; read x; exit 1; }
fi
.venv/bin/python -m pip install -e .
echo 'KiKi installed. Open launch_gui_macos.command.'
read x
