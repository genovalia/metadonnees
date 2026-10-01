"""Bring a running Metadata API in line with the datasets in this repository.

Each dataset folder is compared with what the API holds:

- a dataset the API doesn't have is created;
- a changed dcat.json or oca.json is PATCHed, and a changed dcat:version is
  snapshotted as a new version. The OCA has no version of its own: a changed
  oca.json is snapshotted under the dataset's dcat:version, which therefore
  has to be bumped whenever oca.json changes;
- a changed mapper.json value is PUT as that language's translation.

catalog.json is PUT to /catalog when it differs from the API's.

Datasets in the API with no folder here are reported, never deleted.

Reads are public, so a dry run needs no API key; writes need an admin key.
"""
import os
from dataclasses import dataclass, field

import httpx

LANGUAGES = [
    {"code": "en", "label": "English", "is_default": True},
    {"code": "fr", "label": "Français", "is_default": False},
]
TRANSLATION_FIELDS = ("theme", "spatial", "title", "description", "species")
# The fields GET /catalog adds to catalog.json, from the datasets.
CATALOG_GENERATED = ("dcat:dataset", "dcterms:language", "dcterms:modified")


@dataclass
class Action:
    label: str
    method: str
    path: str
    body: dict


@dataclass
class DatasetPlan:
    id: str
    actions: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    created: bool = False


def translations_from_mapper(mapper):
    """The translation payload for each language in mapper.json.

    Only the `value` of theme, spatial and species, and of title and
    description where present, is used; every other mapper entry is ignored.
    """
    result = {}
    for lang, section in mapper.items():
        if lang == "id":
            continue
        fields = {}
        for name in TRANSLATION_FIELDS:
            entry = section.get(name)
            fields[name] = entry.get("value") if isinstance(entry, dict) else entry
        result[lang] = fields
    return result


def semver(version):
    try:
        return tuple(int(part) for part in str(version).split("."))
    except ValueError:
        return (0,)


def translation_differs(expected, dcat, shown):
    """Whether the API's view of one language differs from mapper.json.

    The API shows the dcat.json title and description for a language that has
    none of its own, so that is what an empty mapper value is compared with.
    """
    for name in TRANSLATION_FIELDS:
        want = expected[name]
        if want is None and name in ("title", "description"):
            want = dcat.get(f"dcterms:{name}")
        if shown.get(name) != want:
            return True
    return False


def plan_dataset(client, dataset_id, dcat, oca, mapper):
    """Work out the API calls that bring one dataset up to date."""
    plan = DatasetPlan(dataset_id)
    version = dcat["dcat:version"]
    translations = translations_from_mapper(mapper)

    resp = client.get(f"/datasets/{dataset_id}/dcat")
    if resp.status_code == 404:
        plan.created = True
        plan.actions.append(Action("create", "POST", "/datasets", {
            "id": dataset_id,
            "dcat": dcat,
            "dcat_version": version,
            "oca": oca,
            "oca_version": version,
            "translations": translations,
        }))
        return plan
    resp.raise_for_status()

    # The detailed view per language holds the current versions, the raw
    # documents and what is shown in that language. 404 = no translation yet.
    shown = {}
    for lang in translations:
        resp = client.get(f"/datasets/{dataset_id}", params={"lang": lang})
        if resp.status_code != 404:
            resp.raise_for_status()
            shown[lang] = resp.json()
    if not shown:
        plan.errors.append("the API has no translation for this dataset; fix it in the API by hand")
        return plan
    current = next(iter(shown.values()))

    dcat_changed = current["dcat"] != dcat
    oca_changed = (current["oca"] or {}) != oca
    api_version = current["dcat_version"]
    bumped = version != api_version

    if bumped and semver(version) < semver(api_version):
        plan.errors.append(f"dcat:version {version} is lower than the API's {api_version}")
    if oca_changed and not bumped:
        plan.errors.append(f"oca.json changed, so dcat:version has to be bumped (the API has {api_version})")
    if bumped:
        for doc_type, needed in (("dcat", True), ("oca", oca_changed)):
            if not needed:
                continue
            resp = client.get(f"/datasets/{dataset_id}/{doc_type}/versions")
            resp.raise_for_status()
            if version in {v["version"] for v in resp.json()}:
                plan.errors.append(f"the API already has a {doc_type} version {version}; bump dcat:version")
    if plan.errors:
        return plan

    if dcat_changed:
        plan.actions.append(Action("dcat", "PATCH", f"/datasets/{dataset_id}/dcat", {"dcat": dcat}))
    if oca_changed:
        plan.actions.append(Action("oca", "PATCH", f"/datasets/{dataset_id}/oca", {"oca": oca}))
    if bumped:
        plan.actions.append(Action(f"dcat version {api_version} → {version}", "POST",
                                   f"/datasets/{dataset_id}/dcat/version", {"version": version}))
    if oca_changed:
        plan.actions.append(Action(f"oca version {current['oca_version']} → {version}", "POST",
                                   f"/datasets/{dataset_id}/oca/version", {"version": version}))
    for lang, fields in translations.items():
        if lang not in shown or translation_differs(fields, dcat, shown[lang]):
            plan.actions.append(Action(f"{lang} translation", "PUT",
                                       f"/datasets/{dataset_id}/translations/{lang}", fields))
    return plan


def catalog_differs(shown, catalog):
    """Whether the API's catalog holds something other than catalog.json.

    GET /catalog returns catalog.json's fields plus the generated ones, and
    its @context is catalog.json's followed by the API's own.
    """
    context = shown.get("@context")
    stored = {k: v for k, v in shown.items() if k not in CATALOG_GENERATED and k != "@context"}
    local = {k: v for k, v in catalog.items() if k != "@context"}
    stored_context = context[0] if isinstance(context, list) else None
    return stored != local or stored_context != catalog.get("@context")


def plan_catalog(client, catalog):
    """The PUT that brings the API's catalog up to date, as a one-action plan."""
    plan = DatasetPlan("catalog.json")
    resp = client.get("/catalog")
    if resp.status_code == 404:
        plan.created = True
    else:
        resp.raise_for_status()
        if not catalog_differs(resp.json(), catalog):
            return plan
    plan.actions.append(Action("catalog", "PUT", "/catalog", catalog))
    return plan


def plan_languages(client):
    resp = client.get("/languages")
    resp.raise_for_status()
    existing = {lang["code"] for lang in resp.json()}
    return [Action(f"language {lang['code']}", "POST", "/languages", lang)
            for lang in LANGUAGES if lang["code"] not in existing]


def api_dataset_ids(client):
    ids, page = set(), 1
    while True:
        resp = client.get("/datasets", params={"page": page, "page_size": 200})
        resp.raise_for_status()
        body = resp.json()
        ids.update(item["id"] for item in body["content"])
        if not body["content"] or page * body["page_size"] >= body["total"]:
            return ids
        page += 1


def run_actions(client, plan):
    for action in plan.actions:
        resp = client.request(action.method, action.path, json=action.body)
        if resp.is_error:
            plan.errors.append(f"{action.method} {action.path}: {resp.status_code} {resp.text[:300]}")
            return


def sync(client, datasets, catalog, dry_run):
    """Plan, and unless dry_run, apply the changes for every dataset and the
    catalog.

    `datasets` maps each dataset ID to its (dcat, oca, mapper) documents.
    Returns (plans, catalog_plan, orphans, language_actions).
    """
    language_actions = plan_languages(client)
    if not dry_run:
        for action in language_actions:
            client.request(action.method, action.path, json=action.body).raise_for_status()

    plans = []
    for dataset_id, (dcat, oca, mapper) in datasets.items():
        try:
            plan = plan_dataset(client, dataset_id, dcat, oca, mapper)
        except httpx.HTTPError as exc:
            plan = DatasetPlan(dataset_id, errors=[f"reading from the API failed: {exc}"])
        if not dry_run and not plan.errors:
            run_actions(client, plan)
        plans.append(plan)

    try:
        catalog_plan = plan_catalog(client, catalog)
    except httpx.HTTPError as exc:
        catalog_plan = DatasetPlan("catalog.json", errors=[f"reading from the API failed: {exc}"])
    if not dry_run and not catalog_plan.errors:
        run_actions(client, catalog_plan)

    orphans = sorted(api_dataset_ids(client) - set(datasets))
    return plans, catalog_plan, orphans, language_actions


def report(plans, catalog_plan, orphans, language_actions, base_url, dry_run):
    """The sync result as Markdown, for the terminal and the GitHub job summary."""
    verb = "Would" if dry_run else "Did"
    lines = [f"## {'Dry run against' if dry_run else 'Sync to'} {base_url}", ""]
    if language_actions:
        lines.append(f"{verb} create: {', '.join(a.label for a in language_actions)}")
        lines.append("")
    lines += ["| Dataset | Result |", "|---|---|"]
    for plan in [*plans, catalog_plan]:
        if plan.errors:
            result = "**error**: " + "; ".join(plan.errors)
        elif plan.created:
            result = f"{verb.lower()} create"
        elif plan.actions:
            result = f"{verb.lower()} update " + ", ".join(a.label for a in plan.actions)
        else:
            result = "unchanged"
        lines.append(f"| `{plan.id}` | {result} |")
    if orphans:
        lines += ["", "In the API but not in this repository (left alone): "
                  + ", ".join(f"`{i}`" for i in orphans)]
    return "\n".join(lines) + "\n"


def run(datasets, catalog, base_url, api_key, dry_run):
    """Sync and print the report. Returns True if every dataset and the
    catalog succeeded."""
    headers = {"X-API-Key": api_key} if api_key else {}
    with httpx.Client(base_url=base_url, headers=headers, timeout=30) as client:
        plans, catalog_plan, orphans, language_actions = sync(client, datasets, catalog, dry_run)

    text = report(plans, catalog_plan, orphans, language_actions, base_url, dry_run)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(text)
    return not any(plan.errors for plan in [*plans, catalog_plan])
