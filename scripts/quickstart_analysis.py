#!/usr/bin/env python3
"""Run a small, non-inferential sanity analysis on harmonized data."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets" / "harmonized"


def main() -> int:
    print("ME/CFS harmonized dataset workspace")
    print(f"Data directory: {DATA}")
    files = sorted(DATA.glob("*.csv*")) if DATA.exists() else []
    print(f"Harmonized files: {len(files)}")
    if not files:
        print("No harmonized files found. Run the GitHub Release workflow or `make download-small && make harmonize`.")
        return 0

    metadata_files = [path for path in files if "sample_metadata" in path.name and not path.name.endswith(".gz")]
    print("\nSample metadata tables:")
    for path in metadata_files:
        frame = pd.read_csv(path)
        print(f"- {path.name}: {frame.shape[0]} rows x {frame.shape[1]} columns")

    pbmc = DATA / "GSE251872_counts_wide.csv.gz"
    if pbmc.exists():
        counts = pd.read_csv(pbmc)
        sample_cols = [column for column in counts.columns if column not in {"gene_id", "external_gene_name"}]
        numeric = counts[sample_cols].apply(pd.to_numeric, errors="coerce")
        library_sizes = numeric.sum(axis=0).sort_values(ascending=False)
        print("\nPBMC RNA-seq matrix:")
        print(f"- genes/features: {len(counts):,}")
        print(f"- sample columns: {len(sample_cols)}")
        print("- five largest library-size sums:")
        for sample, total in library_sizes.head().items():
            print(f"  {sample}: {total:,.0f}")

    print("\nNext step: open notebooks/01_quickstart.ipynb for exploratory PCA and metadata inspection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
