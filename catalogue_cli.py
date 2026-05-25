#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys
from dataset_creator import create_dataset_interactive

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

def main():
    parser = argparse.ArgumentParser(description="Genovalia Catalog Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list-keywords command
    list_keywords_parser = subparsers.add_parser("list-keywords", help="List untranslated keywords from all datasets")
    list_keywords_parser.set_defaults(func=list_keywords)

    # create-dataset command
    create_dataset_parser = subparsers.add_parser("create-dataset", help="Interactively create a new dataset entry")
    create_dataset_parser.set_defaults(func=lambda args: create_dataset_interactive())

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
