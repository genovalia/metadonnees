#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
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

def list_keywords(args):
    """List keywords present in dcat.json files that are not in dictionary.json."""
    dictionary = {}
    keywords = []

    if not os.path.exists("dictionary.json"):
        print("Error: dictionary.json not found.", file=sys.stderr)
        return

    # load dictionary
    with open("dictionary.json", "r") as f:
        dictionary = json.load(f)

    # find all dcat.json files
    for file in glob.glob("**/dcat.json", recursive=True):
        # Skip if it's the current directory's dcat.json (if any, though usually in subdirs)
        with open(file, "r") as f:
            try:
                data = json.load(f)
                keywords.extend(data.get("dcat:keyword", []))
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {file}", file=sys.stderr)

    # remove keywords that are in the dictionary
    untranslated = [k for k in keywords if k not in dictionary]
    
    # remove duplicates
    untranslated = list(set(untranslated))

    # print the keywords
    print("untranslated keywords:")
    print("{")
    for k in untranslated:
        print(f'  "{k}": "{k}",')
    print("}")

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

    print(f"{len(catalog['content'])} datasets checked, {total_errors} errors.")
    if total_errors:
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Genovalia Catalog Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list-keywords command
    list_keywords_parser = subparsers.add_parser("list-keywords", help="List untranslated keywords from all datasets")
    list_keywords_parser.set_defaults(func=list_keywords)

    # create-dataset command
    create_dataset_parser = subparsers.add_parser("create-dataset", help="Interactively create a new dataset entry")
    create_dataset_parser.set_defaults(func=lambda args: create_dataset_interactive())

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Check every dataset's dcat.json against the catalog conventions")
    validate_parser.add_argument("--warnings", action="store_true", help="Also list missing recommended fields (license, distribution)")
    validate_parser.set_defaults(func=validate)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
