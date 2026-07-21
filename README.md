# ME/CFS Open Dataset Workspace

A reproducible, analysis-ready collection of openly accessible ME/CFS datasets from NIH/NCBI GEO and Zenodo, with provenance, checksums, validation, conservative harmonization, citations, and access-status documentation.

## Start here

The repository is configured to generate and commit the **harmonized tabular data** under `datasets/harmonized/`. You can inspect the CSV files directly in GitHub or load them with Python/R.

```bash
git clone https://github.com/HendriVi/CFS-Dataset-.git
cd CFS-Dataset-
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-analysis.txt
python scripts/quickstart_analysis.py
```

For an interactive analysis:

```bash
jupyter lab notebooks/01_quickstart.ipynb
```

## What is included

- NIH post-infectious ME/CFS deep-phenotyping studies:
  - GSE245661 — skeletal-muscle RNA-seq
  - GSE251872 — PBMC RNA-seq
  - GSE251790 — CSF SOMAscan proteomics
  - GSE254030 — plasma SOMAscan proteomics
  - GSE251792 — aggregate SuperSeries metadata
- Cornell exercise/symptom-provocation transcriptomics: GSE214284
- Zenodo ME/CFS neuroimaging releases:
  - DTI onset phenotypes, record 12791948
  - diffusion/neuroinflammation metrics, record 16916830
  - cerebrovascular respiration-response maps, record 19078496

The Git repository contains analysis-ready tables and documentation. Multi-gigabyte original archives are downloaded from authoritative repositories by the reproducible pipeline and distributed through GitHub Releases rather than committed to Git history.

## One-command workflows

```bash
make setup
make analyze
make download-small
make download-all
make harmonize
make manifest
make validate
make bundle
```

## GitHub Releases

The workflow in `.github/workflows/build-release.yml` downloads every open original from its authoritative repository, validates it, recreates the harmonized files, commits the analysis-ready tables, and publishes:

- a compact analysis-ready ZIP;
- a complete bundle split into download-safe parts;
- SHA-256 checksums and reassembly tools.

Open the repository’s **Actions** tab and run **Build validated ME/CFS dataset release**. The resulting files appear under **Releases**.

## Data integrity and provenance

- Originals are never modified.
- Every retained original is screened for accidental HTML/access-denied responses.
- TAR, GZIP, JSON, XLSX, and ZIP containers are opened and checked.
- Zenodo MD5 checksums are verified against repository-published values.
- `documentation/manifest.csv` records title, organisation, URL, retrieval date, licence/access status, citation, format, byte size, MD5, SHA-256, validation result, and transformation.
- Restricted resources are documented but not accessed or redistributed.

## Important analytical cautions

ME/CFS cohorts are not interchangeable. Diagnostic criteria, post-infectious versus gradual onset, illness duration, sex distribution, orthostatic intolerance, comorbidities, medication use, activity level, and challenge timing differ across studies. Do not pool cohorts or use sample/cell-level rows as independent participants without explicit participant-level grouping and study-aware modelling.

These data support research and method development. They do not establish a diagnostic test and are not a substitute for clinical judgement.

## Repository map

```text
datasets/
  original/        # populated by downloader; not committed
  harmonized/      # generated analysis-ready CSV/CSV.GZ files
documentation/
  README.md
  manifest.csv
  transformation_log.csv
  validation_report.csv
  licences/
  citations.bib
scripts/
  download_datasets.py
  harmonize_datasets.py
  build_manifest.py
  validate_files.py
  build_release_assets.py
  quickstart_analysis.py
notebooks/
  01_quickstart.ipynb
```

## Licensing

The code in this repository is MIT licensed. Dataset rights remain with their respective repositories and submitters. Zenodo imaging data are CC BY 4.0; Dryad identifies its data files as CC0, although the Dryad spreadsheet was not downloaded because authoritative endpoints returned HTTP 403. GEO records do not provide a single dataset-specific Creative Commons licence. See `DATA_LICENSES.md` and `documentation/licences/`.

## Citation

Use the study-specific citations in `documentation/citations.bib` and cite this repository version when reporting derived analyses.
