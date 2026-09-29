# Genovalia Dataset Catalog

This repository contains the metadata and schemas for Genovalia's datasets. It serves as the central source of truth for the [Metadata API](../metadata-api).

## Overview

The catalog is organized as a collection of datasets, each residing in its own directory. We use the **DCAT-AP 3.0.1** standard (in JSON-LD syntax) to describe the metadata and a custom **Mapper** system to bridge the raw metadata with the presentation layer.

## Project Structure

- **`catalogue.json`**: The master index listing all available datasets.
- **`catalogue_cli.py`**: A CLI tool for catalog management (e.g., validating the catalog, creating new datasets).
- **`templates/`**: Standardized templates (`.jsonc`) for creating new datasets.
- **`[dataset-id]/`**: Individual dataset directories containing:
    - `dcat.json`: DCAT-AP compliant metadata.
    - `mapper.json`: UI and localization mapping logic.
    - `oca.json`: Dataset schema (Overlays Capture Architecture).

## Setup

This project uses **Poetry** for dependency management. To set up the environment:

```bash
poetry install
```

## Core Concepts

### DCAT-AP Metadata
We follow the DCAT-AP 3.0.1 recommendations. Key fields include identifiers, temporal coverage, spatial references, and themes.

### Mapping System
The `mapper.json` file determines how data is presented in the UI. It supports:
- **Literal**: Static values.
- **JSONPath**: Dynamic extraction from `dcat.json`.
- **JSONPath Multiple**: Extraction of lists (e.g., multiple creators).
- **NCBI**: Automated species name extraction from NCBI taxonomy URLs.

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

## Maintenance

This project is consumed by the **Metadata API**. Ensure that any changes to the mapper structure are compatible with the models defined in the API.
