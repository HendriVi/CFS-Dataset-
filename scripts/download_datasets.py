#!/usr/bin/env python3
"""Download authoritative public ME/CFS files without bypassing access controls."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import time
import zipfile

import requests

UA = "ME-CFS-open-data-workspace/1.0 (research reproducibility)"

FILES = [
    dict(dataset_id="dryad_inflammation_2020", name="Kopia_av_MEFCS_Inflammation_Shared_dataset.xlsx", url="https://datadryad.org/downloads/file_stream/220948", fmt="xlsx", large=False, required=False),
    dict(dataset_id="nih_pi_mecfs_superseries_gse251792", name="GSE251792_RAW.tar", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251792/suppl/GSE251792_RAW.tar", fmt="tar", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_superseries_gse251792", name="GSE251792_family.soft.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251792/soft/GSE251792_family.soft.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_muscle_rnaseq_gse245661", name="GSE245661_RAW.tar", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE245nnn/GSE245661/suppl/GSE245661_RAW.tar", fmt="tar", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_muscle_rnaseq_gse245661", name="GSE245661_family.soft.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE245nnn/GSE245661/soft/GSE245661_family.soft.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_csf_proteomics_gse251790", name="GSE251790_CHI-19-027.Set_001.hybNorm.plateScale.medNorm.20200106.adat.txt.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251790/suppl/GSE251790_CHI-19-027.Set_001.hybNorm.plateScale.medNorm.20200106.adat.txt.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_csf_proteomics_gse251790", name="GSE251790_family.soft.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251790/soft/GSE251790_family.soft.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_pbmc_rnaseq_gse251872", name="GSE251872_RAW.tar", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251872/suppl/GSE251872_RAW.tar", fmt="tar", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_pbmc_rnaseq_gse251872", name="GSE251872_family.soft.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251872/soft/GSE251872_family.soft.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_plasma_proteomics_gse254030", name="GSE254030_CHI-19-021.Plasma_for_CFS.adat.txt.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE254nnn/GSE254030/suppl/GSE254030_CHI-19-021.Plasma_for_CFS.adat.txt.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="nih_pi_mecfs_plasma_proteomics_gse254030", name="GSE254030_family.soft.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE254nnn/GSE254030/soft/GSE254030_family.soft.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="cornell_exercise_provocation_gse214284", name="GSE214284_RAW.tar", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE214nnn/GSE214284/suppl/GSE214284_RAW.tar", fmt="tar", large=True, required=True),
    dict(dataset_id="cornell_exercise_provocation_gse214284", name="GSE214284_family.soft.gz", url="https://ftp.ncbi.nlm.nih.gov/geo/series/GSE214nnn/GSE214284/soft/GSE214284_family.soft.gz", fmt="gz", large=False, required=True),
    dict(dataset_id="zenodo_dti_onset_12791948", name="zenodo_12791948_metadata.json", url="https://zenodo.org/api/records/12791948", fmt="json", large=False, required=True),
    dict(dataset_id="zenodo_dti_onset_12791948", name="DTI_Data_sharing.zip", url="https://zenodo.org/records/12791948/files/DTI_Data_sharing.zip?download=1", fmt="zip", large=True, required=True, md5="be49128ebecbcf3a3eae36ae0ac92fad"),
    dict(dataset_id="zenodo_nii_dti_16916830", name="zenodo_16916830_metadata.json", url="https://zenodo.org/api/records/16916830", fmt="json", large=False, required=True),
    dict(dataset_id="zenodo_nii_dti_16916830", name="NII_Data_sharing_MECFS.zip", url="https://zenodo.org/records/16916830/files/NII_Data_sharing_MECFS.zip?download=1", fmt="zip", large=True, required=True, md5="38c2ad1f61f0dabe7756b891f26e56c8"),
    dict(dataset_id="zenodo_rrf_19078496", name="zenodo_19078496_metadata.json", url="https://zenodo.org/api/records/19078496", fmt="json", large=False, required=True),
    dict(dataset_id="zenodo_rrf_19078496", name="RRF_Data_sharing_MECFS.zip", url="https://zenodo.org/records/19078496/files/RRF_Data_sharing_MECFS.zip?download=1", fmt="zip", large=True, required=True, md5="c26ee0d3c7677bb94b70ba08d0725c83"),
]


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
        raise ValueError("HTML/access-denied response saved instead of data")


def validate(path: Path, fmt: str, full_zip_test: bool = False) -> str:
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError("missing or empty file")
    reject_html(path)
    if fmt in {"xlsx", "zip"}:
        if not zipfile.is_zipfile(path):
            raise ValueError("not a ZIP/XLSX container")
        with zipfile.ZipFile(path) as zf:
            members = len(zf.infolist())
            if full_zip_test:
                bad = zf.testzip()
                if bad:
                    raise ValueError(f"corrupt member: {bad}")
        return f"ZIP opens; {members} members"
    if fmt == "tar":
        with tarfile.open(path, "r:*") as tf:
            members = len(tf.getmembers())
            if not members:
                raise ValueError("empty TAR")
        return f"TAR opens; {members} members"
    if fmt == "gz":
        with gzip.open(path, "rb") as fh:
            fh.read(4096)
        return "GZIP decompresses"
    if fmt == "json":
        json.loads(path.read_text(encoding="utf-8"))
        return "JSON parses"
    raise ValueError(f"unsupported format: {fmt}")


def retrieve(url: str, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    last: Exception | None = None
    for attempt in range(5):
        partial.unlink(missing_ok=True)
        try:
            with requests.get(url, stream=True, allow_redirects=True, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=(30, 900)) as response:
                response.raise_for_status()
                with partial.open("wb") as out:
                    for chunk in response.iter_content(8 * 1024 * 1024):
                        if chunk:
                            out.write(chunk)
                partial.replace(target)
                reject_html(target)
                return response.url
        except Exception as exc:
            last = exc
            partial.unlink(missing_ok=True); target.unlink(missing_ok=True)
            time.sleep(2 ** attempt)
    raise RuntimeError(str(last))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--skip-large", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--full-zip-test", action="store_true")
    args = parser.parse_args()
    failures: list[tuple[dict, str]] = []
    for item in FILES:
        if args.skip_large and item["large"]:
            print(f"SKIP large: {item['name']}")
            continue
        target = args.root / "datasets" / "original" / item["dataset_id"] / item["name"]
        try:
            if args.overwrite or not target.exists():
                final_url = retrieve(item["url"], target)
                print(f"DOWNLOADED {target} <- {final_url}")
            result = validate(target, item["fmt"], args.full_zip_test)
            md5, sha = digests(target)
            if item.get("md5") and md5.lower() != item["md5"].lower():
                raise ValueError(f"repository MD5 mismatch: {md5}")
            print(f"VALID {target} md5={md5} sha256={sha} ({result})")
        except Exception as exc:
            target.unlink(missing_ok=True)
            failures.append((item, str(exc)))
            print(f"FAILED {item['dataset_id']}/{item['name']}: {exc}", file=sys.stderr)
    required = [failure for failure in failures if failure[0]["required"]]
    if failures:
        print("\nDownload exceptions:", file=sys.stderr)
        for item, message in failures:
            level = "REQUIRED" if item["required"] else "OPTIONAL"
            print(f"- {level} {item['dataset_id']}/{item['name']}: {message}", file=sys.stderr)
    return 1 if required else 0


if __name__ == "__main__":
    raise SystemExit(main())
