#!/usr/bin/env python3
"""Build compact and complete release assets with checksums and reassembly tools."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def zip_tree(source_root: Path, output: Path, include_originals: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        for path in sorted(source_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source_root)
            if relative.parts[0] in {".git", ".venv", "dist"}:
                continue
            if not include_originals and relative.parts[:2] == ("datasets", "original") and path.name != ".gitkeep":
                continue
            already_compressed = path.suffix.lower() in {".zip", ".gz", ".tar", ".xlsx"}
            archive.write(path, relative.as_posix(), compress_type=zipfile.ZIP_STORED if already_compressed else zipfile.ZIP_DEFLATED)


def split_file(path: Path, part_size: int) -> list[Path]:
    parts: list[Path] = []
    with path.open("rb") as source:
        index = 0
        while True:
            block = source.read(part_size)
            if not block:
                break
            part = path.with_name(f"{path.name}.part-{index:02d}")
            part.write_bytes(block)
            parts.append(part)
            index += 1
    return parts


def write_reassembly_tools(output_dir: Path, expected_sha: str) -> None:
    (output_dir / "reassemble_full_bundle.py").write_text(
        f'''#!/usr/bin/env python3\nfrom pathlib import Path\nimport hashlib\nparts = sorted(Path('.').glob('mecfs_full_bundle.zip.part-*'))\nif not parts:\n    raise SystemExit('No parts found')\nout = Path('mecfs_full_bundle.zip')\nwith out.open('wb') as destination:\n    for part in parts:\n        print('Appending', part.name)\n        with part.open('rb') as source:\n            while chunk := source.read(8 * 1024 * 1024):\n                destination.write(chunk)\ndigest = hashlib.sha256()\nwith out.open('rb') as source:\n    while chunk := source.read(8 * 1024 * 1024):\n        digest.update(chunk)\nactual = digest.hexdigest()\nprint('SHA-256', actual)\nif actual != '{expected_sha}':\n    raise SystemExit('Checksum mismatch')\nprint('Verified', out)\n''',
        encoding="utf-8",
    )
    (output_dir / "reassemble_full_bundle.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\ncat mecfs_full_bundle.zip.part-* > mecfs_full_bundle.zip\nsha256sum mecfs_full_bundle.zip\n",
        encoding="utf-8",
    )
    (output_dir / "reassemble_full_bundle.bat").write_text(
        "@echo off\ncopy /b mecfs_full_bundle.zip.part-* mecfs_full_bundle.zip\ncertutil -hashfile mecfs_full_bundle.zip SHA256\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--split-size-mib", type=int, default=1500)
    args = parser.parse_args()
    root = args.root.resolve(); output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    compact = output / "mecfs_analysis_ready.zip"
    full = output / "mecfs_full_bundle.zip"
    zip_tree(root, compact, include_originals=False)
    zip_tree(root, full, include_originals=True)
    full_sha = sha256(full)
    parts = split_file(full, args.split_size_mib * 1024 * 1024)
    full.unlink()
    write_reassembly_tools(output, full_sha)

    assets = [compact, *parts, output / "reassemble_full_bundle.py", output / "reassemble_full_bundle.sh", output / "reassemble_full_bundle.bat"]
    with (output / "SHA256SUMS.txt").open("w", encoding="utf-8") as fh:
        for asset in assets:
            fh.write(f"{sha256(asset)}  {asset.name}\n")
        fh.write(f"{full_sha}  mecfs_full_bundle.zip (after reassembly)\n")
    print(f"Built {len(assets)} assets in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
