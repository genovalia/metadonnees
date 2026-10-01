# Genovalia Dataset Catalog

This repository contains the metadata and schemas for Genovalia's datasets. A GitHub Action syncs it into the [Metadata API](../metadata-api): merges into `dev` go to the test site, merges into `main` to the public site (Sedna). See [Branches](./AGENTS.md#branches) and [How the catalog reaches the API](./AGENTS.md#how-the-catalog-reaches-the-api).

## Overview

The catalog is organized as a collection of datasets, each residing in its own directory. We use the **DCAT-AP 3.0.1** standard (in JSON-LD syntax) to describe the metadata, and a small `mapper.json` per dataset for the English and French display text.

## Project Structure

- **`catalogue_cli.py`**: A CLI tool for catalog management (validating the catalog, creating new datasets, syncing to the API).
- **`api_sync.py`**: The sync to the Metadata API, used by `catalogue_cli.py sync`.
- **`.github/workflows/`**: `validate.yml` (PR checks and a dry-run sync), `sync.yml` (sync on merge), `restrict-main-source.yml` (PRs into `main` come from `dev`).
- **`templates/`**: Standardized templates (`.jsonc`) for creating new datasets.
- **`[dataset-id]/`**: Individual dataset directories. Any top-level folder with a `dcat.json` is a dataset; each contains:
    - `dcat.json`: DCAT-AP compliant metadata.
    - `mapper.json`: English and French display labels (theme, species, spatial) and the French title and description.
    - `oca.json`: Dataset schema (Overlays Capture Architecture).

## Setup

This project uses **Poetry** for dependency management. To set up the environment:

```bash
poetry install
```

## Core Concepts

### DCAT-AP Metadata
We follow the DCAT-AP 3.0.1 recommendations. Key fields include identifiers, temporal coverage, spatial references, and themes.

### Mapper
The API reads publisher, contact, years, creators and the other language-independent facts straight from `dcat.json`. From `mapper.json` it takes only the `value` of `theme`, `spatial` and `species` in each language, and of `title` and `description` in `fr`; English title and description come from `dcat.json`. The older entries in the file (`jsonpath`, `jsonpath_multiple`, `ncbi`, `access_request_url`) are no longer read by the API.

## Workflows

For detailed instructions on adding datasets, please refer to [AGENTS.md](./AGENTS.md).

### Quick Start: Adding a Dataset

The easiest way to add a dataset is to use the interactive CLI:

```bash
poetry run python catalogue_cli.py create-dataset
```

This will guide you through the metadata collection, allowing you to reuse existing publishers, contact points, and creators.

### Validating the Catalog
Check every dataset's `dcat.json` against the catalog conventions (`@id`/landing page on Sedna, `dcterms:identifier` = dataset id, `dcat:version` as `MAJOR.MINOR.PATCH`, valid dates and years, canonical GeoNames URIs, `prov:agent`, ISO 19115 roles), and that git doesn't track stray files (e.g. incoming exports outside `temp/`). It exits with status 1 on any error, and the test suite runs it too:
```bash
poetry run python catalogue_cli.py validate
```
Add `--warnings` to also list missing recommended fields (license, distribution).

### Syncing to the API
The **Sync** action runs `catalogue_cli.py sync` on every push to `dev` (dev API) and `main` (prod API), with the admin key from the GitHub Environment of the same name. It creates missing datasets, updates changed ones, and lists datasets the API has but the repo doesn't, without deleting them. To preview it locally (reads need no key):
```bash
poetry run python catalogue_cli.py sync --dry-run --base-url https://metadata-api-dev.apps.genovalia.ulaval.ca
```
For a real run, set `METADATA_API_KEY` to an admin key. See [AGENTS.md](./AGENTS.md#how-the-catalog-reaches-the-api) for what is synced and which fields the API uses.
