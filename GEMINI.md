# Genovalia Catalog

## Overview
This repository manages the metadata and schemas for Genovalia datasets. It acts as a central catalog, utilizing the DCAT-AP 3.0.1 standard in JSON-LD syntax.

## Project Structure
- Each dataset is self-contained within its own directory (e.g., `bostau1`, `lymdis1`).
- Root files manage the overall catalog index and translations.

### Root Files
- `catalogue.json`: The master index of all datasets. It maps the dataset ID to its corresponding metadata files.
- `dictionary.json`: A dictionary used for keyword translations and standardization.
- `catalogue_cli.py`: A CLI tool for catalog management (keyword listing, interactive dataset creation).

### Dataset Directory Files
Every dataset directory MUST contain the following files:
1. `dcat.json`: The core metadata file describing the dataset.
   - Must validate against DCAT-AP 3.0.1 Recommendations.
   - Uses JSON-LD syntax (`@context`, `@id`, `@type`, etc.).
2. `mapper.json`: Handles the mapping between the raw `dcat.json` data and presentation/UI layers.
   - Uses JSONPath expressions (e.g., `{'type': 'jsonpath', 'path': "'dcterms:publisher'.'foaf:name'"}`) to extract values from `dcat.json`.
   - Supports internationalization (e.g., `"en"`, `"fr"` blocks).
3. `oca.json`: Overlays Capture Architecture file (can be empty `{}` if unused, but the file must exist).

## Metadata API Integration
The `metadata-api` (located in the parent directory) consumes this catalog. It supports the following mapping types in `mapper.jsonc`:
- `literal`: Direct string value.
- `jsonpath`: Extracts a single value from `dcat.json` using JSONPath.
- `jsonpath_multiple`: Extracts all matching values as a list (useful for `creators`).
- `ncbi`: Given an NCBI taxonomy URL (via `path`), it fetches the page and extracts the species name from the `ncbi_taxname` meta tag.

The API expects the mapper to provide the following fields: `theme`, `publisher_name`, `publisher_url`, `contact_name`, `contact_email`, `species`, `year_begin`, `year_end`, `spatial`, `creators`, and `creators_urls`.

## Workflows

### Setup
This repository uses **Poetry** for dependency management.
1. Install Poetry if not already present.
2. Run `poetry install` to set up the environment.

### Adding a New Dataset
The recommended way to add a new dataset is using the interactive CLI:
1. Run `poetry run python catalogue_cli.py create-dataset`.
2. Follow the prompts to enter metadata. The tool will suggest existing values for publishers, contact points, and creators to maintain consistency.
3. The tool will automatically create the directory, generate `dcat.json`, initialize other files from templates, and update `catalogue.json`.

Alternatively, you can manually:
1. Create a new directory for the dataset.
2. Copy the templates from the `templates/` folder (`dcat.jsonc`, `mapper.jsonc`, and `oca.json`) into the new directory.
3. Update the files with the specific metadata for the new dataset.
4. Update the root `catalogue.json`.

### Managing Keywords
When updating or adding keywords in `dcat.json` (`dcat:keyword` array):
1. Run `poetry run python catalogue_cli.py list-keywords` from the root directory.
2. The script will output any keywords present in the datasets that are not yet defined in `dictionary.json`.
3. Add the missing keywords to `dictionary.json` manually to ensure translation/consistency.
