#!/usr/bin/env python3
"""Generate provenance, checksum, validation, licence and citation documentation."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

RETRIEVAL_DATE = date.today().isoformat()

META = {
    "dryad_inflammation_2020": dict(title="The role of low-grade inflammation in ME/CFS: associations with symptoms", org="Dryad Data Repository", record="https://datadryad.org/dataset/doi%3A10.5061/dryad.f1vhhmgsb", published="Published 2020-01-02", licence="CC0 1.0", citation="Andreasson A, Jonsjö M, Olsson G, et al. Dryad. 2020. doi:10.5061/dryad.f1vhhmgsb", access="Public record; authoritative download may return HTTP 403"),
    "nih_pi_mecfs_superseries_gse251792": dict(title="Deep phenotyping of post-infectious ME/CFS (SuperSeries GSE251792)", org="NIH/NINDS via NCBI GEO", record="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE251792", published="Public 2023-12-22; updated 2024-03-06", licence="No explicit per-record CC licence; NCBI GEO policies and submitter rights apply", citation="Walitt B et al. Nature Communications. 2024;15:907. doi:10.1038/s41467-024-45107-3", access="Anonymous public download"),
    "nih_pi_mecfs_muscle_rnaseq_gse245661": dict(title="PI-ME/CFS skeletal-muscle RNA sequencing (GSE245661)", org="NIH/NINDS via NCBI GEO", record="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE245661", published="Public 2023-12-22", licence="No explicit per-record CC licence; NCBI GEO policies and submitter rights apply", citation="Walitt B et al. Nature Communications. 2024;15:907. doi:10.1038/s41467-024-45107-3", access="Anonymous public download"),
    "nih_pi_mecfs_csf_proteomics_gse251790": dict(title="PI-ME/CFS CSF SOMAscan proteomics (GSE251790)", org="NIH/NINDS via NCBI GEO", record="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE251790", published="Public 2023-12-22", licence="No explicit per-record CC licence; NCBI GEO policies and submitter rights apply", citation="Walitt B et al. Nature Communications. 2024;15:907. doi:10.1038/s41467-024-45107-3", access="Anonymous public download"),
    "nih_pi_mecfs_pbmc_rnaseq_gse251872": dict(title="PI-ME/CFS PBMC RNA sequencing (GSE251872)", org="NIH/NINDS via NCBI GEO", record="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE251872", published="Public 2023-12-22", licence="No explicit per-record CC licence; NCBI GEO policies and submitter rights apply", citation="Walitt B et al. Nature Communications. 2024;15:907. doi:10.1038/s41467-024-45107-3", access="Anonymous public download"),
    "nih_pi_mecfs_plasma_proteomics_gse254030": dict(title="PI-ME/CFS plasma SOMAscan proteomics (GSE254030)", org="NIH/NINDS via NCBI GEO", record="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE254030", published="Public 2024-01-24", licence="No explicit per-record CC licence; NCBI GEO policies and submitter rights apply", citation="Walitt B et al. Nature Communications. 2024;15:907. doi:10.1038/s41467-024-45107-3", access="Anonymous public download"),
    "cornell_exercise_provocation_gse214284": dict(title="ME/CFS exercise and symptom-provocation transcriptomics (GSE214284)", org="Cornell University via NCBI GEO", record="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE214284", published="Public 2022-10-03; updated 2024-04-12", licence="No explicit per-record CC licence; NCBI GEO policies and submitter rights apply", citation="NCBI GEO SuperSeries GSE214284 and associated SubSeries publications", access="Anonymous public download"),
    "zenodo_dti_onset_12791948": dict(title="Diffusion tensor imaging in post-infectious and gradual-onset ME/CFS", org="Zenodo", record="https://zenodo.org/records/12791948", published="Published 2024", licence="CC BY 4.0", citation="Zenodo record 12791948. doi:10.5281/zenodo.12791948", access="Anonymous public download"),
    "zenodo_nii_dti_16916830": dict(title="Diffusion-based neuroinflammation and DTI metrics in ME/CFS", org="Zenodo", record="https://zenodo.org/records/16916830", published="Published 2025", licence="CC BY 4.0", citation="Zenodo record 16916830. doi:10.5281/zenodo.16916830", access="Anonymous public download"),
    "zenodo_rrf_19078496": dict(title="Cerebrovascular respiration-response-function imaging in ME/CFS", org="Zenodo", record="https://zenodo.org/records/19078496", published="Published 2026", licence="CC BY 4.0", citation="Zenodo record 19078496. doi:10.5281/zenodo.19078496", access="Anonymous public download"),
}

URLS = {
    "Kopia_av_MEFCS_Inflammation_Shared_dataset.xlsx": "https://datadryad.org/downloads/file_stream/220948",
    "GSE251792_RAW.tar": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251792/suppl/GSE251792_RAW.tar",
    "GSE251792_family.soft.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251792/soft/GSE251792_family.soft.gz",
    "GSE245661_RAW.tar": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE245nnn/GSE245661/suppl/GSE245661_RAW.tar",
    "GSE245661_family.soft.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE245nnn/GSE245661/soft/GSE245661_family.soft.gz",
    "GSE251790_CHI-19-027.Set_001.hybNorm.plateScale.medNorm.20200106.adat.txt.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251790/suppl/GSE251790_CHI-19-027.Set_001.hybNorm.plateScale.medNorm.20200106.adat.txt.gz",
    "GSE251790_family.soft.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251790/soft/GSE251790_family.soft.gz",
    "GSE251872_RAW.tar": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251872/suppl/GSE251872_RAW.tar",
    "GSE251872_family.soft.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE251nnn/GSE251872/soft/GSE251872_family.soft.gz",
    "GSE254030_CHI-19-021.Plasma_for_CFS.adat.txt.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE254nnn/GSE254030/suppl/GSE254030_CHI-19-021.Plasma_for_CFS.adat.txt.gz",
    "GSE254030_family.soft.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE254nnn/GSE254030/soft/GSE254030_family.soft.gz",
    "GSE214284_RAW.tar": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE214nnn/GSE214284/suppl/GSE214284_RAW.tar",
    "GSE214284_family.soft.gz": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE214nnn/GSE214284/soft/GSE214284_family.soft.gz",
    "zenodo_12791948_metadata.json": "https://zenodo.org/api/records/12791948",
    "DTI_Data_sharing.zip": "https://zenodo.org/records/12791948/files/DTI_Data_sharing.zip?download=1",
    "zenodo_16916830_metadata.json": "https://zenodo.org/api/records/16916830",
    "NII_Data_sharing_MECFS.zip": "https://zenodo.org/records/16916830/files/NII_Data_sharing_MECFS.zip?download=1",
    "zenodo_19078496_metadata.json": "https://zenodo.org/api/records/19078496",
    "RRF_Data_sharing_MECFS.zip": "https://zenodo.org/records/19078496/files/RRF_Data_sharing_MECFS.zip?download=1",
}

REPO_MD5 = {"DTI_Data_sharing.zip": "be49128ebecbcf3a3eae36ae0ac92fad", "NII_Data_sharing_MECFS.zip": "38c2ad1f61f0dabe7756b891f26e56c8", "RRF_Data_sharing_MECFS.zip": "c26ee0d3c7677bb94b70ba08d0725c83"}

RESTRICTED = [
    ("nsrr_pi_mecfs_sleep", "NIH PI-ME/CFS sleep phenotypes and polysomnography", "National Sleep Research Resource", "https://sleepdata.org/datasets/pimecfs", "Registration and approved data-access request; non-commercial use"),
    ("mapmecfs", "mapMECFS integrated research portal", "RTI International / NIH-supported resources", "https://mecfs.rti.org/research/", "Registration/provider review"),
    ("searchmecfs_cfi", "searchMECFS / Chronic Fatigue Initiative", "RTI International", "https://mecfs.rti.org/research/", "Research request/application"),
    ("uk_mecfs_biobank", "UK ME/CFS Biobank", "UK ME/CFS Biobank", "https://mecfs.rti.org/research/", "Research proposal and approval"),
    ("you_me_registry", "You + ME Registry and Biobank", "Solve M.E.", "https://youandmeregistry.com/", "Application, review and data-use agreement"),
]


def digests(path: Path) -> tuple[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            md5.update(block); sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def validation(path: Path) -> str:
    lower = path.name.lower()
    with path.open("rb") as fh:
        head = fh.read(4096).lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html")) or b"access denied" in head:
        raise ValueError("HTML/access-denied response")
    if lower.endswith((".zip", ".xlsx")):
        with zipfile.ZipFile(path) as zf:
            return f"ZIP opens; {len(zf.infolist())} members"
    if lower.endswith(".tar"):
        with tarfile.open(path, "r:*") as tf:
            return f"TAR opens; {len(tf.getmembers())} members"
    if lower.endswith(".gz"):
        with gzip.open(path, "rb") as fh:
            fh.read(4096)
        return "GZIP decompresses"
    if lower.endswith(".json"):
        json.loads(path.read_text(encoding="utf-8")); return "JSON parses"
    return "File opens"


def file_format(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".soft.gz"): return "GEO SOFT.GZ"
    if name.endswith(".adat.txt.gz"): return "SOMAscan ADAT text, GZIP"
    if name.endswith(".tar"): return "TAR"
    if name.endswith(".zip"): return "ZIP"
    if name.endswith(".xlsx"): return "XLSX"
    if name.endswith(".json"): return "JSON"
    if name.endswith(".gz"): return "GZIP"
    return path.suffix.lstrip(".").upper() or "binary"


def transformation(name: str) -> str:
    if name.endswith("_RAW.tar"): return "Original preserved; archive inventory generated; RNA-seq count files merged only for designated SubSeries"
    if name.endswith("family.soft.gz"): return "Original preserved; GEO sample attributes parsed to UTF-8 CSV"
    if ".adat.txt.gz" in name: return "Original preserved; ADAT header, assay annotations, sample metadata and normalized RFU matrix parsed without renormalization"
    if name.endswith(".zip"): return "Original preserved; archive inventory generated and embedded demographic workbook sheets exported to UTF-8 CSV"
    return "Original preserved; no numerical transformation"


def write_supporting_docs(doc: Path) -> None:
    licences = doc / "licences"; licences.mkdir(parents=True, exist_ok=True)
    (licences / "CC-BY-4.0.txt").write_text("Creative Commons Attribution 4.0 International. Attribute the original creators and indicate changes. https://creativecommons.org/licenses/by/4.0/\n", encoding="utf-8")
    (licences / "CC0-1.0.txt").write_text("Creative Commons CC0 1.0 Universal public-domain dedication. https://creativecommons.org/publicdomain/zero/1.0/\n", encoding="utf-8")
    (licences / "NCBI-GEO-usage-note.txt").write_text("GEO provides public access, but these accession pages do not state a single dataset-specific Creative Commons licence. NCBI policies, submitter rights and applicable safeguards remain relevant.\n", encoding="utf-8")
    (licences / "restricted-datasets-notice.txt").write_text("Governed datasets listed in the manifest were not accessed. Registration, approval, data-use agreements and other provider controls must be respected.\n", encoding="utf-8")
    (doc / "citations.bib").write_text('''@article{walitt2024pimecfs,\n  title={Deep phenotyping of post-infectious myalgic encephalomyelitis/chronic fatigue syndrome},\n  author={Walitt, Brian and others},\n  journal={Nature Communications},\n  volume={15},\n  pages={907},\n  year={2024},\n  doi={10.1038/s41467-024-45107-3}\n}\n\n@misc{geo_gse214284, title={ME/CFS exercise and symptom-provocation transcriptomics}, howpublished={NCBI GEO GSE214284}}\n@dataset{zenodo12791948, title={ME/CFS DTI onset dataset}, year={2024}, doi={10.5281/zenodo.12791948}}\n@dataset{zenodo16916830, title={ME/CFS diffusion and neuroinflammation imaging dataset}, year={2025}, doi={10.5281/zenodo.16916830}}\n@dataset{zenodo19078496, title={ME/CFS cerebrovascular respiration-response imaging dataset}, year={2026}, doi={10.5281/zenodo.19078496}}\n''', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=Path(".")); args = parser.parse_args()
    root = args.root; original = root / "datasets" / "original"; harmonized = root / "datasets" / "harmonized"; doc = root / "documentation"; doc.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []; validation_rows: list[dict[str, str]] = []
    for path in sorted(p for p in original.rglob("*") if p.is_file() and p.name != ".gitkeep"):
        dataset_id = path.parent.name; meta = META[dataset_id]; md5, sha = digests(path); result = validation(path); repository_md5 = REPO_MD5.get(path.name, "")
        if repository_md5 and repository_md5 != md5: raise RuntimeError(f"Repository MD5 mismatch for {path}")
        rel = path.relative_to(root).as_posix()
        rows.append(dict(dataset_id=dataset_id, dataset_title=meta["title"], source_organisation=meta["org"], dataset_record_url=meta["record"], source_file_url=URLS.get(path.name, ""), retrieval_date=RETRIEVAL_DATE, version_or_publication_date=meta["published"], licence=meta["licence"], citation=meta["citation"], access_requirements=meta["access"], file_name=path.name, local_path=rel, file_format=file_format(path), status="downloaded", byte_size=str(path.stat().st_size), repository_md5=repository_md5, computed_md5=md5, computed_sha256=sha, validation=result, transformation=transformation(path.name), notes="Original repository file preserved byte-for-byte."))
        validation_rows.append(dict(local_path=rel, byte_size=str(path.stat().st_size), computed_md5=md5, computed_sha256=sha, validation_result=result, html_screen_passed="yes"))
    if not any(row["dataset_id"] == "dryad_inflammation_2020" for row in rows):
        meta = META["dryad_inflammation_2020"]
        rows.append(dict(dataset_id="dryad_inflammation_2020", dataset_title=meta["title"], source_organisation=meta["org"], dataset_record_url=meta["record"], source_file_url=URLS["Kopia_av_MEFCS_Inflammation_Shared_dataset.xlsx"], retrieval_date=RETRIEVAL_DATE, version_or_publication_date=meta["published"], licence=meta["licence"], citation=meta["citation"], access_requirements=meta["access"], file_name="Kopia_av_MEFCS_Inflammation_Shared_dataset.xlsx", local_path="", file_format="XLSX", status="not_downloaded_authoritative_endpoint_error", byte_size="", repository_md5="", computed_md5="", computed_sha256="", validation="No file retained; authoritative retrieval failed", transformation="None", notes="No HTML page or unofficial mirror was substituted."))
    for dataset_id, title, org, source, access in RESTRICTED:
        rows.append(dict(dataset_id=dataset_id, dataset_title=title, source_organisation=org, dataset_record_url=source, source_file_url="", retrieval_date=RETRIEVAL_DATE, version_or_publication_date="Current access status checked at retrieval", licence="Provider terms", citation=title, access_requirements=access, file_name="", local_path="", file_format="", status="governed_not_downloaded", byte_size="", repository_md5="", computed_md5="", computed_sha256="", validation="Not downloaded because access controls were respected", transformation="None", notes="No authentication, agreement acceptance or circumvention attempted."))
    fields = ["dataset_id","dataset_title","source_organisation","dataset_record_url","source_file_url","retrieval_date","version_or_publication_date","licence","citation","access_requirements","file_name","local_path","file_format","status","byte_size","repository_md5","computed_md5","computed_sha256","validation","transformation","notes"]
    with (doc / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    with (doc / "validation_report.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["local_path","byte_size","computed_md5","computed_sha256","validation_result","html_screen_passed"]); writer.writeheader(); writer.writerows(validation_rows)
    transforms = []
    inventory = []
    for path in sorted(p for p in harmonized.glob("*.csv*") if p.is_file()):
        rel = path.relative_to(root).as_posix(); inventory.append(dict(local_path=rel, byte_size=path.stat().st_size, format="CSV.GZ" if path.name.endswith(".gz") else "CSV"))
        kind = "archive inventory" if "inventory" in path.name else "sample/assay/measurement table"
        transforms.append(dict(harmonized_path=rel, transformation=kind, originals_modified="no", created_on=RETRIEVAL_DATE))
    with (doc / "transformation_log.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["harmonized_path","transformation","originals_modified","created_on"]); writer.writeheader(); writer.writerows(transforms)
    with (doc / "harmonized_inventory.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["local_path","byte_size","format"]); writer.writeheader(); writer.writerows(inventory)
    write_supporting_docs(doc)
    (doc / "README.md").write_text(f"# Generated dataset documentation\n\nRetrieval date: **{RETRIEVAL_DATE}**  \nDownloaded original files: **{len(validation_rows)}**  \nHarmonized files: **{len(inventory)}**\n\nSee `manifest.csv` for file-level provenance and checksums, `transformation_log.csv` for derivative documentation, `validation_report.csv` for integrity results, and `citations.bib` for citations. Restricted resources are recorded without access attempts.\n", encoding="utf-8")
    print(f"Wrote manifest for {len(validation_rows)} originals and {len(inventory)} harmonized files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
