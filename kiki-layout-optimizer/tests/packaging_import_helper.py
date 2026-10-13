import importlib.util
from pathlib import Path


def load_packaging_build():
    p=Path(__file__).resolve().parents[1]/'packaging'/'build_portable.py'
    spec=importlib.util.spec_from_file_location('kiki_build_portable',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m
