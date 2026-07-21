PYTHON ?= python3

.PHONY: setup analyze download-small download-all harmonize manifest validate validate-full bundle clean

setup:
	$(PYTHON) -m pip install -r requirements.txt

analyze:
	$(PYTHON) scripts/quickstart_analysis.py

download-small:
	$(PYTHON) scripts/download_datasets.py --root . --skip-large

download-all:
	$(PYTHON) scripts/download_datasets.py --root .

harmonize:
	$(PYTHON) scripts/harmonize_datasets.py --root .

manifest:
	$(PYTHON) scripts/build_manifest.py --root .

validate:
	$(PYTHON) scripts/validate_files.py --root .

validate-full:
	$(PYTHON) scripts/validate_files.py --root . --full-zip-test

bundle:
	$(PYTHON) scripts/build_release_assets.py --root . --output dist

clean:
	rm -rf dist .pytest_cache __pycache__ scripts/__pycache__
