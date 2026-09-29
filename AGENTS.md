# Genovalia Catalog — Agent Guide

This repository holds the metadata for Genovalia's datasets. The [Metadata API](../metadata-api) reads it, and each dataset appears on Sedna at `https://sedna.apps.genovalia.ulaval.ca/datasets/<id>`. Anything merged into `main` ends up on the public site, so mistakes are visible.

## Who you are working with

Some of the people using this repo are **not developers**. They mostly add new datasets from DCAT and OCA files they made themselves, outside this repo. With them:

- Explain what you are about to do in plain words before you do it, especially git steps. Don't assume they know what a branch, commit or PR is. Give a one-line explanation the first time one comes up.
- Do the git and terminal work yourself rather than asking them to type commands.
- Show them a short summary of every change you made to their files, and ask before changing their wording, dates, people or keywords. It's their data. You fix the format; they decide the content.
- When something is ambiguous (which OCA file goes with which dataset, a year that doesn't match, an unknown place), **ask**. Don't guess.
- Never run destructive git commands (`push --force`, `reset --hard`, `branch -D`, `checkout -- .`, `clean`) or delete files you didn't create in this session. If git gets into a confusing state, stop, explain what you see, and ask.

## Repository layout

- `catalogue.json`: the list of all datasets. A dataset that isn't listed here doesn't exist for the API.
- `<id>/`: one folder per dataset, always holding these three files:
  - `dcat.json`: the dataset's metadata, DCAT-AP 3.0.1 in JSON-LD.
  - `oca.json`: the dataset's schema (an OCA package).
  - `mapper.json`: tells the API what to show in English and French.
- `catalogue_cli.py` and `dataset_creator.py`: the CLI (`validate`, `create-dataset`).
- `templates/`: templates used by `create-dataset`. `templates/dcat.jsonc` has a comment on every field and is the best reference for what a field means.
- `tests/`: pytest suite. It also runs `validate` on the real catalog.
- `temp/`: git ignores this folder. Put incoming files here (see below). **Never commit it.**

  Only `temp/` is ignored. A folder with any other name (`exports/`, `Temp/`, `nouveaux datasets/`, …) is **not** ignored and could be committed by mistake. If the user's files are anywhere else in the repo, move them into `temp/` first, after asking. `validate` fails if git tracks or has staged any file that isn't a dataset file (`<id>/dcat.json`, `mapper.json`, `oca.json` for an ID in `catalogue.json`), in `templates/` or `tests/`, or one of the known root files (`REPO_FILES` in `catalogue_cli.py`).

### Dataset IDs

An ID is the first 3 letters of the genus, the first 3 letters of the species, and a number: `salnam1` = *Salvelinus namaycush*, `anogla1` = *Anoplophora glabripennis*. Use `spp` for several species (`corspp1`, `ednaspp1`). A second dataset on the same species gets the next number (`salnam2`). The ID is the folder name and appears in `dcat.json`, `mapper.json` and `catalogue.json`. It must be the same in all of them.

## Setup

```bash
poetry install
```

Run commands with `poetry run ...` from the repository root.

## Git workflow (always follow this)

`main` isn't protected on GitHub, so nothing stops a direct push. You have to do the checking yourself.

1. **Start from an up-to-date `main`:**
   ```bash
   git switch main
   git pull
   git status
   ```
   If `git status` shows modified files, stop and ask the user what they are before going on. `git status` doesn't show `temp/`, because git ignores it. Any **untracked** folder or file it lists (other than the datasets you are about to add) is probably incoming files under another name: ask the user, and move it into `temp/`.
2. **Create a new branch for each piece of work.** Never commit to `main`.
   - Adding datasets: ask the user for the IDs of the datasets they are adding (see [Dataset IDs](#dataset-ids)), then name the branch `add-<id>` after them, e.g. `add-anogla1` or `add-salnam1-salnam2`. Don't guess the IDs from file names. If the user isn't sure, suggest IDs that follow the convention and have them confirm.
   - Fixing one dataset: `fix-<id>-<what>` (e.g. `fix-oviari1-typo`).
   - If a branch with that name already exists, ask before reusing it. It may hold someone else's unfinished work.
3. **Commit** only files that belong to the change. Add them by name (`git add anogla1 catalogue.json`), never with `git add -A` or `git add .`, because that would pick up `temp/` or stray files. Run `git status` and `validate` before committing to check. If a file you don't recognize is staged, unstage it with `git restore --staged <path>`; this doesn't delete the file.
   - Commit message: a short summary line, a blank line, then a body listing the datasets added and **every correction you made to the user's files** (see the log of `e1a1749` for an example).
4. **Push and open a pull request:**
   ```bash
   git push -u origin <branch>
   gh pr create --base main --title "..." --body "..."
   ```
   The PR body repeats the dataset list and the corrections. Give the user the PR link.
5. **Don't merge the PR** unless the user explicitly asks. Someone reviews it first.
6. After it's merged, switch back to `main` and pull (step 1) before starting anything new.

## Adding datasets from the user's own files (the usual case)

The user usually brings files they made themselves instead of running `create-dataset`. A typical batch (e.g. the 2026-09-25 export) contains:

- one DCAT file per dataset, e.g. `anogla1_DCAT.json`, already mostly in the final format
- one OCA package per dataset, e.g. `salvelinus_namaycush_2_OCA_package.json`, often minified and **named after the species, not the ID**, along with a `..._README.txt`, which is not committed
- two mapper spreadsheets saved as CSV, separated by `;` and starting with a byte-order mark:
  - English: `dataset_id;title;description;theme;species;temp_beg;temp_end;spatial`
  - French: `dataset_id;titre;description;thème;espèce;temp_début;temp_fin;spatial`

Ask the user to put them in a subfolder of `temp/` (e.g. `temp/salnam1/`), never in a folder with another name. Ignore `*:Zone.Identifier` files, which Windows creates on download.

Then, for each dataset:

1. **Match the files.** Pair each DCAT file with its OCA package and CSV rows. Use the species and description, since the OCA file name doesn't contain the ID. If two datasets share a species (`salnam1` and `salnam2`), confirm the pairing with the user.
2. **`<id>/dcat.json`:** start from the user's DCAT file and keep its content. Check it against the rules in [DCAT rules](#dcat-rules) and fix only the format, telling the user about each fix. In particular:
   - `dcterms:issued` is the date the dataset is published in the catalog. Set it to the day the PR is opened (or merged) and tell the user. The export often carries an older date.
   - Keep `dcterms:accessRights` as the user gave it (OpenAccess or RestrictedAccess). It differs between datasets on purpose.
   - Keep `dcterms:license` and `dcat:distribution` empty unless the user provides them (see [Deliberately left for later](#deliberately-left-for-later)).
3. **`<id>/oca.json`:** the OCA package, pretty-printed. Don't change its content: the `d` values are hashes of it, and any edit breaks them.
   ```bash
   python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1])), indent=2, ensure_ascii=False))" temp/.../X_OCA_package.json > <id>/oca.json
   ```
4. **`<id>/mapper.json`:** copy the `mapper.json` of a recent dataset (e.g. `anogla1/mapper.json`) and change only these values:
   - `"id"`: the dataset ID
   - `en.theme.value`, `en.species.value`, `fr.theme.value`, `fr.species.value`: the Latin species name (the CSV `species`/`espèce` column)
   - `en.spatial.value`: the English CSV `spatial`; `fr.spatial.value`: the French CSV `spatial`
   - `fr.title.value`, `fr.description.value`: the French CSV `titre` and `description`. English title and description come from `dcat.json`, so the `en` block has no `title`/`description`.
   - Keep everything else (the JSONPath entries and `access_request_url`) exactly as in the copied file. The API depends on this structure.
   - Write it with 2-space indentation, UTF-8 (keep accents as they are, not `é`), and a final newline.
5. **Cross-check the CSVs against `dcat.json`.** The English title and description, the theme URL, and the start and end years should match. If they don't, show the user the difference and ask which one is right. Watch for stray spaces at the start or end of a value, and for typos in French text. Point these out and fix them only if the user agrees.
6. **`catalogue.json`:** add an entry at the end of `content`:
   ```json
   { "id": "<id>", "mapper": "<id>/mapper.json", "OCA": "<id>/oca.json", "DCAT": "<id>/dcat.json" }
   ```
   (use the same multi-line format as the existing entries).
7. **Keywords:** compare the new `dcat:keyword` values with the keywords the other datasets already use. Look for near-duplicates (different case, singular vs plural, hyphen vs space). If you find one, ask the user whether to use the existing spelling instead. Generic terms are lowercase (`genotyping-by-sequencing`, `invasive species`); species and proper names keep their capitals (`Picea glauca`, `North America`).

Then run the [checks](#checks-before-committing), show the user a summary, and follow the [git workflow](#git-workflow-always-follow-this).

## Adding a dataset with the script

If the user has no DCAT file, the interactive script creates the folder, `dcat.json`, `mapper.json` and the `catalogue.json` entry:

```bash
poetry run python catalogue_cli.py create-dataset
```

It's interactive, so the **user** has to run it in their own terminal. It doesn't create `oca.json` (add the user's OCA package as in step 3 above), and it leaves the mapper's `theme`, `species`, `spatial` and French title/description empty. Fill those as in step 4.

## DCAT rules

`validate` enforces these:

- `@id` and `dcat:landingPage` are both `https://sedna.apps.genovalia.ulaval.ca/datasets/<id>`.
- `dcterms:identifier` is the plain ID (`"anogla1"`), not a URL.
- `dcat:version` is `MAJOR.MINOR.PATCH` (new datasets: `"1.0.0"`). Never use `dcterms:version`.
- `dcterms:issued` is `YYYY-MM-DD`.
- The years in `dcterms:temporal` are `"YYYY"` strings. For an ongoing dataset, **remove `time:hasEnd` entirely**. Never write `"present"` or leave it empty.
- `dcterms:spatial` is a GeoNames URI in exactly this form: `https://sws.geonames.org/<number>/` (https, `sws.`, trailing slash).
- Each `dcat:qualifiedAttribution` entry uses `prov:agent` (lowercase *a*; `prov:Agent` is wrong). Its `dcat:hadRole` values are ISO 19115 role codes, spelled exactly: `pointOfContact`, `principalInvestigator`, `collaborator`, `author`, `custodian`, `funder`, etc. (see `ISO_19115_ROLES` in `catalogue_cli.py`).

Conventions `validate` doesn't check:

- `dcat:theme` is the NCBI taxonomy URL of the species: `https://www.ncbi.nlm.nih.gov/datasets/taxonomy/<taxid>/`.
- People have an ORCID URL as `@id`, when they have one.
- The publisher and contact point are Genovalia (`genovalia@ulaval.ca`) unless the user says otherwise.

## Checks before committing

Run both from the repo root. Both must pass:

```bash
poetry run python catalogue_cli.py validate
poetry run pytest -q
```

- `validate` must end with `0 errors.` A `repository:` error means a stray file is staged or committed. Unstage it and move it into `temp/`; never "fix" it by adding the path to `REPO_FILES`.
- `pytest` must pass. It includes validation of the real catalog.

Also check that `git status` lists only the files you meant to change. Every new dataset folder must hold exactly `dcat.json`, `mapper.json` and `oca.json`.

## Fixing an existing dataset

Keep fixes small and limited to what the user asked. Use a `fix-<id>-<what>` branch. Bump `dcat:version` only when the data itself changes, not for metadata typos.

## Deliberately left for later

Don't "fix" these on your own. The maintainer has deferred them:

- `dcterms:license` and `dcat:distribution` are empty on every dataset (`validate --warnings` lists them).
- `dcterms:accessRights` uses the eprints vocabulary and `dcterms:language` is `"en"`. Both are planned to move to EU vocabularies later, and access rights will need a matching mapper change.
- `lymdis1`'s spatial is the whole Earth, and `ednaspp1`'s theme is an EDAM topic instead of an NCBI taxonomy URL.
- `mapper.json` files use `"jsonpath"` for `creators` (only `lymdis1` uses `"jsonpath_multiple"`), while the template uses `"jsonpath_multiple"`. Copy an existing dataset's mapper as described above.

## Metadata API reference

The API supports these mapper types:

- `literal`: a fixed string (`value`).
- `jsonpath`: one value from `dcat.json` (`path`, e.g. `'dcterms:publisher'.'foaf:name'`).
- `jsonpath_multiple`: every matching value, as a list.
- `ncbi`: fetches an NCBI taxonomy URL (`path`) and reads the species name from it.

It expects `theme`, `publisher` (name, url), `contact` (name, email), `species`, `temporal` (year_begin, year_end), `spatial`, `creators`, `creators_urls` and `access_request_url` in each language block, plus `title` and `description` in `fr`. Any change to the mapper structure must also be made in the API.
