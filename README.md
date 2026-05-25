# Genovalia Dataset Catalog

This repository contains the metadata and schemas for Genovalia's datasets. It serves as the central source of truth for the [Metadata API](../metadata-api).

## Overview

The catalog is organized as a collection of datasets, each residing in its own directory. We use the **DCAT-AP 3.0.1** standard (in JSON-LD syntax) to describe the metadata and a custom **Mapper** system to bridge the raw metadata with the presentation layer.

## Project Structure

- **`catalogue.json`**: The master index listing all available datasets.
- **`dictionary.json`**: Centralized translations and standardized terms for keywords.
- **`catalogue_cli.py`**: A CLI tool for catalog management (e.g., checking for untranslated keywords, creating new datasets).
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

For detailed instructions on adding datasets or managing keywords, please refer to the [GEMINI.md](./GEMINI.md) file.

### Quick Start: Adding a Dataset

The easiest way to add a dataset is to use the interactive CLI:

```bash
poetry run python catalogue_cli.py create-dataset
```

This will guide you through the metadata collection, allowing you to reuse existing publishers, contact points, and creators.

### Managing Keywords
Run the CLI tool to find keywords that need translation in `dictionary.json`:
```bash
poetry run python catalogue_cli.py list-keywords
```

## Maintenance

This project is consumed by the **Metadata API**. Ensure that any changes to the mapper structure are compatible with the models defined in the API.
