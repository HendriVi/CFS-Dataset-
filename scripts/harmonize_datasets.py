#!/usr/bin/env python3
"""Create conservative tabular derivatives from preserved ME/CFS originals.

Files under datasets/original are never modified. The script creates archive
inventories, GEO sample metadata, RNA-seq count matrices, SOMAscan tables, and
CSV exports of embedded imaging-demographic workbooks.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import io
from pathlib import Path
import re
import tarfile
import zipfile

import pandas as pd


def safe_name(value: str) -> str:
    value = value.strip().replace("/", "_").replace("\\", "_")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_.-")
    return value or "sheet"


def snake(value: str) -> str:
    value = value.strip().replace("/", "_")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value or "field"


def unique_columns(cols: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for raw in cols:
        base = str(raw).strip() or "unnamed"
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.append(base if n == 0 else f"{base}__{n + 1}")
    return out


def tar_inventory(tar_path: Path, output: Path) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        rows = [{"member_name": m.name, "size_bytes": m.size, "type": "file" if m.isfile() else "other"} for m in tf.getmembers()]
    pd.DataFrame(rows).to_csv(output, index=False)


def zip_inventory(zip_path: Path, output: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        rows = [{"member_name": info.filename, "size_bytes": info.file_size, "compressed_size_bytes": info.compress_size, "crc32": f"{info.CRC:08x}", "type": "directory" if info.is_dir() else "file"} for info in zf.infolist()]
    pd.DataFrame(rows).to_csv(output, index=False)


def parse_soft_samples(soft_path: Path, output: Path) -> None:
    samples: list[dict[str, str]] = []
    current: dict[str, list[str]] | None = None
    with gzip.open(soft_path, "rt", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("^SAMPLE = "):
                if current is not None:
                    samples.append({k: " | ".join(v) for k, v in current.items()})
                current = defaultdict(list)
                current["geo_accession"].append(line.split("=", 1)[1].strip())
            elif current is not None and line.startswith("!Sample_") and " = " in line:
                key, value = line[1:].split(" = ", 1)
                current[snake(key.removeprefix("Sample_"))].append(value.strip())
        if current is not None:
            samples.append({k: " | ".join(v) for k, v in current.items()})
    frame = pd.DataFrame(samples)
    if "geo_accession" in frame.columns:
        frame = frame.sort_values("geo_accession")
    frame.to_csv(output, index=False)


def read_member_table(tf: tarfile.TarFile, member: tarfile.TarInfo) -> pd.DataFrame:
    stream = tf.extractfile(member)
    if stream is None:
        raise ValueError(member.name)
    raw = stream.read()
    if member.name.lower().endswith(".gz"):
        raw = gzip.decompress(raw)
    return pd.read_csv(io.BytesIO(raw), sep="\t", dtype={0: str, 1: str})


def harmonize_rnaseq_tar(tar_path: Path, prefix: str, output_dir: Path) -> None:
    matrices: list[pd.DataFrame] = []
    duplicate_log: list[dict[str, object]] = []
    with tarfile.open(tar_path, "r:*") as tf:
        members = [m for m in tf.getmembers() if m.isfile() and m.name.lower().endswith((".txt", ".txt.gz", ".tsv", ".tsv.gz"))]
        for member in members:
            df = read_member_table(tf, member)
            if df.shape[1] < 3:
                continue
            cols = list(df.columns)
            sample_name = Path(member.name).name.split("_", 1)[0]
            df = df.rename(columns={cols[0]: "gene_id", cols[1]: "external_gene_name", cols[2]: sample_name})[["gene_id", "external_gene_name", sample_name]]
            rows_before = len(df)
            df = df.drop_duplicates()
            rows_after_exact = len(df)
            key_dups = int(df.duplicated(["gene_id", "external_gene_name"], keep=False).sum())
            if key_dups:
                df[sample_name] = pd.to_numeric(df[sample_name], errors="coerce")
                df = df.groupby(["gene_id", "external_gene_name"], dropna=False, as_index=False)[sample_name].sum(min_count=1)
            duplicate_log.append({"archive_member": member.name, "rows_before": rows_before, "exact_duplicate_rows_removed": rows_before - rows_after_exact, "nonidentical_duplicate_key_rows_aggregated": key_dups, "rows_after": len(df)})
            matrices.append(df)
    if not matrices:
        return
    merged = matrices[0]
    for frame in matrices[1:]:
        merged = merged.merge(frame, on=["gene_id", "external_gene_name"], how="outer", validate="one_to_one")
    merged = merged.sort_values(["gene_id", "external_gene_name"], na_position="last")
    merged.to_csv(output_dir / f"{prefix}_counts_wide.csv.gz", index=False, compression="gzip")
    pd.DataFrame(duplicate_log).to_csv(output_dir / f"{prefix}_duplicate_row_log.csv", index=False)


def parse_adat(path: Path, prefix: str, output_dir: Path) -> None:
    with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as fh:
        lines = [line.rstrip("\n\r").split("\t") for line in fh]
    marker = {row[0]: i for i, row in enumerate(lines) if row and row[0].startswith("^")}
    required = {"^COL_DATA", "^ROW_DATA", "^TABLE_BEGIN"}
    if not required.issubset(marker):
        raise ValueError(f"ADAT markers missing from {path.name}: {required - set(marker)}")
    col_i, row_i, table_i = marker["^COL_DATA"], marker["^ROW_DATA"], marker["^TABLE_BEGIN"]
    col_fields = [x.strip() for x in lines[col_i + 1][1:] if x.strip()]
    row_fields = [x.strip() for x in lines[row_i + 1][1:] if x.strip()]
    row_n = len(row_fields)
    data = lines[table_i + 1:]
    width = max(len(r) for r in data)
    data = [r + [""] * (width - len(r)) for r in data]
    assay_n = width - row_n
    annotation_rows = data[:len(col_fields)]
    assay_records = [{field: annotation_rows[i][row_n + j] for i, field in enumerate(col_fields)} for j in range(assay_n)]
    assay_df = pd.DataFrame(assay_records)
    seq = assay_df.get("SeqId", pd.Series([""] * assay_n)).fillna("").astype(str).tolist()
    target = assay_df.get("Target", pd.Series([""] * assay_n)).fillna("").astype(str).tolist()
    names = unique_columns([s or t or f"assay_{i + 1}" for i, (s, t) in enumerate(zip(seq, target))])
    assay_df.insert(0, "measurement_column", names)
    assay_df.to_csv(output_dir / f"{prefix}_assay_metadata.csv", index=False)
    sample_rows = data[len(col_fields) + 1:]
    sample_rows = [r for r in sample_rows if any(x.strip() for x in r[:row_n])]
    wide_cols = unique_columns(row_fields + names)
    wide = pd.DataFrame([r[:row_n + assay_n] for r in sample_rows], columns=wide_cols)
    wide.to_csv(output_dir / f"{prefix}_measurements_wide.csv.gz", index=False, compression="gzip")
    wide.iloc[:, :row_n].to_csv(output_dir / f"{prefix}_sample_metadata.csv", index=False)
    header_records = []
    for idx, row in enumerate(lines[:col_i]):
        if row and any(x.strip() for x in row):
            header_records.append({"line_number_1_based": idx + 1, "field": row[0], "value": "\t".join(row[1:])})
    pd.DataFrame(header_records).to_csv(output_dir / f"{prefix}_adat_header.csv", index=False)


def export_embedded_workbooks(zip_path: Path, prefix: str, output_dir: Path) -> int:
    exported = 0
    with zipfile.ZipFile(zip_path) as zf:
        for member in [name for name in zf.namelist() if name.lower().endswith(".xlsx")]:
            book = pd.ExcelFile(io.BytesIO(zf.read(member)), engine="openpyxl")
            member_stem = safe_name(Path(member).with_suffix("").as_posix().replace("/", "__"))
            for sheet in book.sheet_names:
                frame = pd.read_excel(book, sheet_name=sheet, dtype=object)
                frame.to_csv(output_dir / f"{prefix}__{member_stem}__{safe_name(sheet)}.csv", index=False)
                exported += 1
    return exported


def first_existing(folder: Path, pattern: str) -> Path | None:
    return next(folder.glob(pattern), None) if folder.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    original = args.root / "datasets" / "original"
    out = args.root / "datasets" / "harmonized"
    out.mkdir(parents=True, exist_ok=True)

    for dataset_dir, prefix, make_counts in [
        ("nih_pi_mecfs_muscle_rnaseq_gse245661", "GSE245661", True),
        ("nih_pi_mecfs_pbmc_rnaseq_gse251872", "GSE251872", True),
        ("nih_pi_mecfs_superseries_gse251792", "GSE251792", False),
        ("cornell_exercise_provocation_gse214284", "GSE214284", False),
    ]:
        folder = original / dataset_dir
        tar_path = first_existing(folder, "*.tar")
        soft_path = first_existing(folder, "*.soft.gz")
        if tar_path:
            tar_inventory(tar_path, out / f"{prefix}_archive_inventory.csv")
            if make_counts:
                harmonize_rnaseq_tar(tar_path, prefix, out)
        if soft_path:
            parse_soft_samples(soft_path, out / f"{prefix}_sample_metadata.csv")

    for dataset_dir, prefix in [
        ("nih_pi_mecfs_csf_proteomics_gse251790", "GSE251790_CSF_SOMAscan"),
        ("nih_pi_mecfs_plasma_proteomics_gse254030", "GSE254030_plasma_SOMAscan"),
    ]:
        folder = original / dataset_dir
        adat = first_existing(folder, "*.adat.txt.gz")
        soft = first_existing(folder, "*.soft.gz")
        if adat:
            parse_adat(adat, prefix, out)
        if soft:
            parse_soft_samples(soft, out / f"{prefix}_geo_sample_metadata.csv")

    for dataset_dir, filename, prefix in [
        ("zenodo_dti_onset_12791948", "DTI_Data_sharing.zip", "zenodo_dti_onset_12791948"),
        ("zenodo_nii_dti_16916830", "NII_Data_sharing_MECFS.zip", "zenodo_nii_dti_16916830"),
        ("zenodo_rrf_19078496", "RRF_Data_sharing_MECFS.zip", "zenodo_rrf_19078496"),
    ]:
        path = original / dataset_dir / filename
        if path.exists():
            zip_inventory(path, out / f"{prefix}__archive_inventory.csv")
            export_embedded_workbooks(path, prefix, out)

    print(f"Harmonized outputs written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
