#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
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

# Everything git may track besides the dataset folders. Anything else (e.g. a
# folder of incoming exports under another name than temp/) is an error.
REPO_FILES = {
    ".gitignore", "AGENTS.md", "CLAUDE.md", "README.md", "catalogue.json",
    "catalogue_cli.py", "dataset_creator.py", "poetry.lock", "pyproject.toml",
}
REPO_DIRS = {"templates", "tests"}
DATASET_FILES = {"dcat.json", "mapper.json", "oca.json"}

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

def tracked_files():
    """Files committed or staged in git, or None if this isn't a git checkout."""
    try:
        result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.splitlines()

def validate(args):
    """Check every dataset in catalogue.json. Exits with status 1 if any dataset has errors."""
    with open("catalogue.json", "r") as f:
        catalog = json.load(f)

    total_errors = 0
    for entry in catalog["content"]:
        dataset_id = entry["id"]
        errors, warnings = [], []
        for key in ("DCAT", "mapper", "OCA"):
            if not os.path.exists(entry[key]):
                errors.append(f"{key} file {entry[key]} does not exist")
        if os.path.exists(entry["DCAT"]):
            with open(entry["DCAT"], "r") as f:
                dcat_errors, warnings = check_dcat(dataset_id, json.load(f))
            errors.extend(dcat_errors)

        total_errors += len(errors)
        if errors or (warnings and args.warnings):
            print(f"{dataset_id}:")
            for message in errors:
                print(f"  error: {message}")
            if args.warnings:
                for message in warnings:
                    print(f"  warning: {message}")

    paths = tracked_files()
    if paths is not None:
        file_errors = check_tracked_files(paths, {entry["id"] for entry in catalog["content"]})
        if file_errors:
            print("repository:")
            for message in file_errors:
                print(f"  error: {message}")
        total_errors += len(file_errors)

    print(f"{len(catalog['content'])} datasets checked, {total_errors} errors.")
    if total_errors:
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Genovalia Catalog Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-dataset command
    create_dataset_parser = subparsers.add_parser("create-dataset", help="Interactively create a new dataset entry")
    create_dataset_parser.set_defaults(func=lambda args: create_dataset_interactive())

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Check every dataset's dcat.json against the catalog conventions, and that git tracks no stray files")
    validate_parser.add_argument("--warnings", action="store_true", help="Also list missing recommended fields (license, distribution)")
    validate_parser.set_defaults(func=validate)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
