#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import date
import api_sync
from dataset_creator import create_dataset_interactive, dataset_url

# ISO 19115-1 CI_RoleCode values, used for dcat:hadRole.
ISO_19115_ROLES = {
    "resourceProvider", "custodian", "owner", "user", "distributor", "originator",
    "pointOfContact", "principalInvestigator", "processor", "publisher", "author",
    "sponsor", "coAuthor", "collaborator", "editor", "mediator", "rightsHolder",
    "contributor", "funder", "stakeholder",
}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
GYEAR = re.compile(r"^\d{4}$")
GEONAMES = re.compile(r"^https://sws\.geonames\.org/\d+/$")
DATASET_ID = re.compile(r"^[a-z]+[0-9]+$")

# Everything git may track besides the dataset folders. Anything else (e.g. a
# folder of incoming exports under another name than temp/) is an error.
REPO_FILES = {
    ".gitignore", "AGENTS.md", "CLAUDE.md", "README.md", "api_sync.py",
    "catalog.json", "catalogue_cli.py", "dataset_creator.py", "poetry.lock", "pyproject.toml",
}
REPO_DIRS = {".github", "templates", "tests"}
DATASET_FILES = {"dcat.json", "mapper.json", "oca.json"}

# catalog.json holds only the catalog-level fields no dataset provides. The
# API requires these, and generates the others itself from the datasets.
CATALOG_FILE = "catalog.json"
CATALOG_REQUIRED = ("dcterms:title", "dcterms:description", "dcterms:publisher")
CATALOG_GENERATED = ("dcat:dataset", "dcterms:language", "dcterms:modified")

def check_dcat(dataset_id, dcat):
    """Return (errors, warnings) for one dataset's dcat.json."""
    errors, warnings = [], []
    url = dataset_url(dataset_id)

    if dcat.get("@id") != url:
        errors.append(f'@id should be "{url}", got {dcat.get("@id")!r}')
    if dcat.get("dcat:landingPage") != url:
        errors.append(f'dcat:landingPage should be "{url}", got {dcat.get("dcat:landingPage")!r}')
    if dcat.get("dcterms:identifier") != dataset_id:
        errors.append(f'dcterms:identifier should be "{dataset_id}", got {dcat.get("dcterms:identifier")!r}')

    if "dcterms:version" in dcat:
        errors.append("dcterms:version is not a Dublin Core term; use dcat:version")
    if not SEMVER.match(str(dcat.get("dcat:version", ""))):
        errors.append(f'dcat:version should be MAJOR.MINOR.PATCH, got {dcat.get("dcat:version")!r}')

    try:
        date.fromisoformat(dcat.get("dcterms:issued", ""))
    except (TypeError, ValueError):
        errors.append(f'dcterms:issued should be YYYY-MM-DD, got {dcat.get("dcterms:issued")!r}')

    temporal = dcat.get("dcterms:temporal", {})
    for bound in ("time:hasBeginning", "time:hasEnd"):
        if bound in temporal:
            year = temporal[bound].get("time:inXSDgYear")
            if not GYEAR.match(str(year)):
                errors.append(f"{bound} year should be YYYY (omit time:hasEnd if ongoing), got {year!r}")

    spatial = dcat.get("dcterms:spatial", "")
    if not GEONAMES.match(spatial):
        errors.append(f'dcterms:spatial should look like https://sws.geonames.org/<id>/, got {spatial!r}')

    for attribution in dcat.get("dcat:qualifiedAttribution", []):
        if "prov:Agent" in attribution:
            errors.append("qualifiedAttribution uses prov:Agent (the class); use prov:agent")
        for role in attribution.get("dcat:hadRole", []):
            if role not in ISO_19115_ROLES:
                errors.append(f"unknown role {role!r} (not an ISO 19115 CI_RoleCode)")

    if not dcat.get("dcterms:license"):
        warnings.append("dcterms:license is empty")
    if not dcat.get("dcat:distribution"):
        warnings.append("dcat:distribution is empty")

    return errors, warnings

def check_catalog(catalog):
    """Return the errors in catalog.json, the same checks the API makes."""
    errors = []
    if not catalog.get("@id"):
        errors.append("@id is missing")
    if catalog.get("@type") != "dcat:Catalog":
        errors.append(f'@type should be "dcat:Catalog", got {catalog.get("@type")!r}')
    for key in CATALOG_REQUIRED:
        if not catalog.get(key):
            errors.append(f"{key} is missing")
    for key in CATALOG_GENERATED:
        for spelling in (key, key.replace("dcterms:", "dct:")):
            if spelling in catalog:
                errors.append(f"{spelling} is filled in by the API from the datasets; remove it")
    return errors

def load_catalog():
    """Return (catalog, errors) for catalog.json."""
    try:
        with open(CATALOG_FILE, encoding="utf-8") as f:
            catalog = json.load(f)
    except FileNotFoundError:
        return None, [f"{CATALOG_FILE} is missing"]
    except ValueError as exc:
        return None, [f"{CATALOG_FILE} is not valid JSON: {exc}"]
    return catalog, check_catalog(catalog)

def check_tracked_files(paths, dataset_ids):
    """Return errors for tracked files that are neither repo files nor dataset files."""
    errors = []
    for path in paths:
        parts = path.split("/")
        if len(parts) == 1:
            ok = path in REPO_FILES
        elif parts[0] in REPO_DIRS:
            ok = True
        else:
            ok = len(parts) == 2 and parts[0] in dataset_ids and parts[1] in DATASET_FILES
        if not ok:
            errors.append(f"{path} should not be committed (incoming files go in temp/)")
    return errors

def git_files(*flags):
    """`git ls-files` with these flags, or None if this isn't a git checkout."""
    try:
        result = subprocess.run(["git", "ls-files", *flags], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.splitlines()

def tracked_files():
    """Files committed or staged in git, or None if this isn't a git checkout."""
    return git_files()

def find_dataset_ids(paths):
    """Dataset IDs: the top-level folders holding a dcat.json."""
    return sorted({
        parts[0] for parts in (path.split("/") for path in paths)
        if len(parts) == 2 and parts[1] == "dcat.json" and parts[0] not in REPO_DIRS
    })

def discover_datasets():
    """Every dataset folder git tracks or would add.

    Folders git ignores (temp/) are left out, so incoming files there are never
    picked up. A new folder counts before it is added to git.
    """
    paths = git_files("--cached", "--others", "--exclude-standard")
    if paths is None:
        paths = [p for p in glob.glob("*/dcat.json") if not p.startswith("temp/")]
    return find_dataset_ids(paths)

def load_dataset(dataset_id):
    """Return ({name: parsed document}, errors) for one dataset folder."""
    docs, errors = {}, []
    for name in sorted(DATASET_FILES):
        path = os.path.join(dataset_id, name)
        if not os.path.exists(path):
            errors.append(f"{path} is missing")
            continue
        try:
            with open(path, encoding="utf-8") as f:
                docs[name] = json.load(f)
        except ValueError as exc:
            errors.append(f"{path} is not valid JSON: {exc}")
    return docs, errors

def check_dataset(dataset_id):
    """Return (docs, errors, warnings) for one dataset folder."""
    docs, errors = load_dataset(dataset_id)
    warnings = []
    if not DATASET_ID.match(dataset_id):
        errors.append(f"folder name {dataset_id!r} is not a dataset ID (letters then a number, e.g. salnam1)")
    if "dcat.json" in docs:
        dcat_errors, warnings = check_dcat(dataset_id, docs["dcat.json"])
        errors.extend(dcat_errors)
    if "mapper.json" in docs and docs["mapper.json"].get("id") != dataset_id:
        errors.append(f'mapper.json "id" should be "{dataset_id}", got {docs["mapper.json"].get("id")!r}')
    return docs, errors, warnings

def validate(args):
    """Check every dataset folder. Exits with status 1 if any dataset has errors."""
    dataset_ids = discover_datasets()
    total_errors = 0
    for dataset_id in dataset_ids:
        _, errors, warnings = check_dataset(dataset_id)
        total_errors += len(errors)
        if errors or (warnings and args.warnings):
            print(f"{dataset_id}:")
            for message in errors:
                print(f"  error: {message}")
            if args.warnings:
                for message in warnings:
                    print(f"  warning: {message}")

    _, catalog_errors = load_catalog()
    if catalog_errors:
        print(f"{CATALOG_FILE}:")
        for message in catalog_errors:
            print(f"  error: {message}")
    total_errors += len(catalog_errors)

    paths = tracked_files()
    if paths is not None:
        file_errors = check_tracked_files(paths, set(dataset_ids))
        if file_errors:
            print("repository:")
            for message in file_errors:
                print(f"  error: {message}")
        total_errors += len(file_errors)

    print(f"{len(dataset_ids)} datasets checked, {total_errors} errors.")
    if total_errors:
        sys.exit(1)

def sync(args):
    """Bring the API at --base-url in line with the dataset folders."""
    api_key = os.environ.get("METADATA_API_KEY")
    if not args.dry_run and not api_key:
        sys.exit("METADATA_API_KEY must be set (or use --dry-run, which needs no key).")
    if not args.base_url:
        sys.exit("Pass --base-url or set METADATA_API_URL.")

    datasets = {}
    for dataset_id in discover_datasets():
        docs, errors, _ = check_dataset(dataset_id)
        if errors:
            sys.exit(f"{dataset_id} doesn't validate; run `validate` first.")
        datasets[dataset_id] = (docs["dcat.json"], docs["oca.json"], docs["mapper.json"])
    catalog, errors = load_catalog()
    if errors:
        sys.exit(f"{CATALOG_FILE} doesn't validate; run `validate` first.")

    if not api_sync.run(datasets, catalog, args.base_url.rstrip("/"), api_key, args.dry_run):
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Genovalia Catalog Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-dataset command
    create_dataset_parser = subparsers.add_parser("create-dataset", help="Interactively create a new dataset entry")
    create_dataset_parser.set_defaults(func=lambda args: create_dataset_interactive())

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Check every dataset's dcat.json and catalog.json against the catalog conventions, and that git tracks no stray files")
    validate_parser.add_argument("--warnings", action="store_true", help="Also list missing recommended fields (license, distribution)")
    validate_parser.set_defaults(func=validate)

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Create or update the datasets and the catalog in a Metadata API (admin key in METADATA_API_KEY)")
    sync_parser.add_argument("--base-url", default=os.environ.get("METADATA_API_URL"), help="API to sync, e.g. https://metadata-api-dev.apps.genovalia.ulaval.ca (default: $METADATA_API_URL)")
    sync_parser.add_argument("--dry-run", action="store_true", help="Only report what would change; needs no API key")
    sync_parser.set_defaults(func=sync)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
