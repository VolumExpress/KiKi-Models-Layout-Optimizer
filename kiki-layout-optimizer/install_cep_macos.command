#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then echo 'Run install_macos.command first'; read -r; exit 1; fi
printf 'Enable unsigned CEP developer mode (only for your account)? [y/N] '
read -r answer
case "$answer" in
  y|Y) .venv/bin/python -m kiki_layout.cep_install --enable-unsigned-dev ;;
  *) .venv/bin/python -m kiki_layout.cep_install ;;
esac
printf '\nRestart Illustrator. Press Enter to close.'
read -r
