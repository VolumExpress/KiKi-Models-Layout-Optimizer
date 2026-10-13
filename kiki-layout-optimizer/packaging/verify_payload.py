"""Verify a transparent portable package, using only Python stdlib (for CI/developers)."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def verify(root: Path) -> tuple[int, list[str]]:
    root = root.resolve()
    manifest_file = root / "SHA256SUMS.json"
    if not manifest_file.is_file():
        return 0, ["Missing SHA256SUMS.json"]
    manifest = json.loads(manifest_file.read_text(encoding="utf8"))
    errors = []
    if not isinstance(manifest, dict):
        return 0, ["Invalid checksums manifest"]
    for name, expected in manifest.items():
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or not isinstance(expected,str) or len(expected)!=64:
            errors.append(f"Unsafe/invalid manifest entry: {name}"); continue
        target = (root / rel).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            errors.append(f"Missing/unsafe file: {name}"); continue
        h=hashlib.sha256()
        with target.open('rb') as src:
            for block in iter(lambda:src.read(1024*1024), b''):
                h.update(block)
        if h.hexdigest() != expected.lower():
            errors.append(f"Checksum mismatch: {name}")
    # Detect unexpected payload files. Installers also verify only manifest entries;
    # CI check disallows unaccounted-for files in a release package.
    allowed = set(manifest) | {"SHA256SUMS.json", "SHA256SUMS.txt"}
    for file in root.rglob('*'):
        if file.is_file() and file.relative_to(root).as_posix() not in allowed:
            errors.append(f"Unexpected file: {file.relative_to(root)}")
    return len(manifest), errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('payload', type=Path)
    args = parser.parse_args()
    count, issues = verify(args.payload)
    for issue in issues:
        print('ERROR:', issue)
    print(f'Validated {count} files; errors: {len(issues)}')
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
