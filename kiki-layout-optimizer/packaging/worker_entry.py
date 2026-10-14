"""Executable entrypoint for PyInstaller; keep Python engine unchanged."""
from kiki_layout.cep_worker import main
if __name__ == '__main__':
    raise SystemExit(main())
