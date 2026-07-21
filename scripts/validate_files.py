#!/usr/bin/env python3
"""Validate originals, harmonized derivatives and manifest checksums."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile


def digests(path: Path) -> tuple[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            md5.update(block); sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def reject_html(path: Path) -> None:
    with path.open("rb") as fh:
        head = fh.read(4096).lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html")) or b"access denied" in head:
        raise ValueError("HTML/access-denied content")


def validate_original(path: Path, full_zip_test: bool) -> str:
    if path.stat().st_size == 0:
        raise ValueError("empty file")
    reject_html(path)
    lower = path.name.lower()
    if lower.endswith((".zip", ".xlsx")):
        if not zipfile.is_zipfile(path):
            raise ValueError("not a ZIP container")
        with zipfile.ZipFile(path) as zf:
            count = len(zf.infolist())
            if full_zip_test:
                bad = zf.testzip()
                if bad:
                    raise ValueError(f"corrupt member: {bad}")
        return f"ZIP opens; {count} members"
    if lower.endswith(".tar"):
        with tarfile.open(path, "r:*") as tf:
            count = len(tf.getmembers())
            if not count:
                raise ValueError("empty TAR")
        return f"TAR opens; {count} members"
    if lower.endswith(".gz"):
        with gzip.open(path, "rb") as fh:
            fh.read(4096)
        return "GZIP decompresses"
    if lower.endswith(".json"):
        json.loads(path.read_text(encoding="utf-8"))
        return "JSON parses"
    with path.open("rb") as fh:
        fh.read(4096)
    return "binary file opens"


def validate_harmonized(path: Path) -> str:
    opener = gzip.open if path.name.lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="strict", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if not header:
            raise ValueError("empty CSV header")
        next(reader, None)
    return f"CSV parses; {len(header)} columns"


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        return {row["local_path"]: row for row in csv.DictReader(fh) if row.get("local_path") and row.get("status") == "downloaded"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--full-zip-test", action="store_true", help="CRC-test every ZIP member; slow for GB-scale imaging archives")
    args = parser.parse_args()
    manifest = read_manifest(args.root / "documentation" / "manifest.csv")
    failures = 0
    original_root = args.root / "datasets" / "original"
    if original_root.exists():
        for path in sorted(p for p in original_root.rglob("*") if p.is_file() and p.name != ".gitkeep"):
            rel = path.relative_to(args.root).as_posix()
            try:
                result = validate_original(path, args.full_zip_test)
                md5, sha = digests(path)
                if manifest:
                    row = manifest.get(rel)
                    if not row:
                        raise ValueError("downloaded file absent from manifest")
                    if row.get("computed_md5") and md5 != row["computed_md5"]:
                        raise ValueError("MD5 differs from manifest")
                    if row.get("computed_sha256") and sha != row["computed_sha256"]:
                        raise ValueError("SHA-256 differs from manifest")
                print(f"OK\t{rel}\t{result}\t{sha}")
            except Exception as exc:
                failures += 1
                print(f"FAIL\t{rel}\t{exc}")
    harmonized_root = args.root / "datasets" / "harmonized"
    if harmonized_root.exists():
        for path in sorted(harmonized_root.rglob("*.csv*")):
            rel = path.relative_to(args.root).as_posix()
            try:
                print(f"OK\t{rel}\t{validate_harmonized(path)}")
            except Exception as exc:
                failures += 1
                print(f"FAIL\t{rel}\t{exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
