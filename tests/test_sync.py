import copy
import json
import re

import httpx
import pytest

from api_sync import DatasetPlan, report, sync, translations_from_mapper

DCAT = {
    "dcterms:identifier": "ds1",
    "dcterms:title": "Title",
    "dcterms:description": "Description",
    "dcat:version": "1.0.0",
}
OCA = {"d": "E1", "oca_bundle": {}}
MAPPER = {
    "id": "ds1",
    "en": {
        "theme": {"type": "literal", "value": "Salmo salar"},
        "spatial": {"type": "literal", "value": "Quebec"},
        "species": {"type": "literal", "value": "Salmo salar"},
        "access_request_url": {"type": "literal", "value": "https://example.org"},
    },
    "fr": {
        "theme": {"type": "literal", "value": "Salmo salar"},
        "spatial": {"type": "literal", "value": "Québec"},
        "species": {"type": "literal", "value": "Salmo salar"},
        "title": {"type": "literal", "value": "Titre"},
        "description": {"type": "literal", "value": "Description FR"},
    },
}


CATALOG = {
    "@context": {"dcat": "http://www.w3.org/ns/dcat#", "dcterms": "http://purl.org/dc/terms/"},
    "@id": "https://sedna.example/catalogue",
    "@type": "dcat:Catalog",
    "dcterms:title": "Catalogue",
    "dcterms:description": "Description",
    "dcterms:publisher": {"@id": "https://genovalia.ulaval.ca/"},
}


def served(catalog):
    """catalog.json as GET /catalog returns it: with the generated fields, and
    the API's context after its own."""
    return {
        **catalog,
        "@context": [catalog["@context"], {"dcat": "http://www.w3.org/ns/dcat#"}],
        "dcterms:language": [{"@id": "http://id.loc.gov/vocabulary/iso639-1/en"}],
        "dcterms:modified": {"@value": "2026-10-01T00:00:00+00:00", "@type": "xsd:dateTime"},
        "dcat:dataset": [{"@id": "https://sedna.example/datasets/ds1", "@type": "dcat:Dataset"}],
    }


class FakeApi:
    """Just enough of the Metadata API: datasets, translations, versions, languages, catalog."""

    def __init__(self):
        self.catalog = served(CATALOG)
        self.datasets = {}
        self.languages = [{"code": "en"}, {"code": "fr"}]
        self.writes = []

    def add(self, dataset_id, dcat, oca, mapper, oca_version="0.1"):
        self.datasets[dataset_id] = {
            "dcat": copy.deepcopy(dcat), "oca": copy.deepcopy(oca),
            "dcat_version": dcat["dcat:version"], "oca_version": oca_version,
            "translations": translations_from_mapper(mapper),
            "versions": {"dcat": {dcat["dcat:version"]}, "oca": {oca_version}},
        }

    def shown(self, ds, lang):
        t = ds["translations"][lang]
        return {
            **{k: t[k] for k in ("theme", "spatial", "species")},
            "title": t["title"] or ds["dcat"].get("dcterms:title"),
            "description": t["description"] or ds["dcat"].get("dcterms:description"),
            "dcat": ds["dcat"], "oca": ds["oca"],
            "dcat_version": ds["dcat_version"], "oca_version": ds["oca_version"],
        }

    def handler(self, request):
        method, path = request.method, request.url.path
        body = json.loads(request.content) if request.content else None
        if method != "GET":
            assert request.headers.get("X-API-Key") == "key"
            self.writes.append((method, path))

        if path == "/languages":
            if method == "POST":
                self.languages.append(body)
                return httpx.Response(201, json=body)
            return httpx.Response(200, json=self.languages)
        if path == "/catalog":
            if method == "PUT":
                self.catalog = served(body)
            if self.catalog is None:
                return httpx.Response(404, json={"detail": "No catalog has been set for this deployment"})
            return httpx.Response(200, json=self.catalog)
        if path == "/datasets" and method == "GET":
            ids = sorted(self.datasets)
            return httpx.Response(200, json={
                "content": [{"id": i} for i in ids], "total": len(ids), "page": 1, "page_size": 200,
            })
        if path == "/datasets" and method == "POST":
            self.add(body["id"], body["dcat"], body["oca"], {}, oca_version=body["oca_version"])
            self.datasets[body["id"]]["translations"] = body["translations"]
            return httpx.Response(201, json={})

        m = re.fullmatch(r"/datasets/([^/]+)(?:/(.*))?", path)
        ds = self.datasets.get(m.group(1))
        if ds is None:
            return httpx.Response(404, json={"detail": "Dataset not found"})
        rest = m.group(2)
        if rest is None:
            lang = request.url.params["lang"]
            if lang not in ds["translations"]:
                return httpx.Response(404, json={"detail": "Dataset not found"})
            return httpx.Response(200, json=self.shown(ds, lang))
        if rest in ("dcat", "oca"):
            if method == "PATCH":
                ds[rest] = body[rest]
            return httpx.Response(200, json=ds[rest])
        if rest in ("dcat/versions", "oca/versions"):
            return httpx.Response(200, json=[{"version": v} for v in ds["versions"][rest[:-9]]])
        if rest in ("dcat/version", "oca/version"):
            doc = rest[:-8]
            if body["version"] in ds["versions"][doc]:
                return httpx.Response(409, json={"detail": "Version already exists"})
            ds["versions"][doc].add(body["version"])
            ds[f"{doc}_version"] = body["version"]
            return httpx.Response(200, json={})
        if rest.startswith("translations/"):
            ds["translations"][rest.split("/")[1]] = body
            return httpx.Response(200, json={})
        raise AssertionError(f"unexpected {method} {path}")


@pytest.fixture
def api():
    return FakeApi()


def run_sync(api, datasets, dry_run=False, catalog=CATALOG):
    transport = httpx.MockTransport(api.handler)
    with httpx.Client(base_url="http://api", headers={"X-API-Key": "key"}, transport=transport) as client:
        return sync(client, datasets, copy.deepcopy(catalog), dry_run)


def local(dcat=DCAT, oca=OCA, mapper=MAPPER):
    return {"ds1": (copy.deepcopy(dcat), copy.deepcopy(oca), copy.deepcopy(mapper))}


def results(plans):
    return {p.id: (p.created, [a.label for a in p.actions], p.errors) for p in plans}


def test_translations_from_mapper_keeps_only_values():
    t = translations_from_mapper(MAPPER)
    assert set(t) == {"en", "fr"}
    assert t["en"] == {"theme": "Salmo salar", "spatial": "Quebec", "title": None,
                       "description": None, "species": "Salmo salar"}
    assert t["fr"]["title"] == "Titre"


def test_creates_missing_dataset(api):
    plans, _, _, _ = run_sync(api, local())
    assert results(plans) == {"ds1": (True, ["create"], [])}
    created = api.datasets["ds1"]
    assert created["dcat_version"] == created["oca_version"] == "1.0.0"
    assert created["translations"]["fr"]["spatial"] == "Québec"


def test_unchanged_dataset_makes_no_writes(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    plans, _, orphans, languages = run_sync(api, local())
    assert results(plans) == {"ds1": (False, [], [])}
    assert orphans == [] and languages == []
    assert api.writes == []


def test_dry_run_makes_no_writes(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    plans, _, _, _ = run_sync(api, local(dcat={**DCAT, "dcterms:title": "Fixed"}), dry_run=True)
    assert results(plans)["ds1"][1] == ["dcat", "en translation"]
    assert api.writes == []


def test_dcat_typo_fix_patches_without_new_version(api):
    """The English title falls back to dcat.json, so its translation is refreshed too."""
    api.add("ds1", DCAT, OCA, MAPPER)
    plans, _, _, _ = run_sync(api, local(dcat={**DCAT, "dcterms:title": "Fixed"}))
    assert results(plans)["ds1"] == (False, ["dcat", "en translation"], [])
    assert api.datasets["ds1"]["dcat"]["dcterms:title"] == "Fixed"
    assert api.datasets["ds1"]["dcat_version"] == "1.0.0"


def test_oca_change_snapshots_under_dcat_version(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    plans, _, _, _ = run_sync(api, local(dcat={**DCAT, "dcat:version": "1.1.0"}, oca={**OCA, "d": "E2"}))
    assert results(plans)["ds1"] == (
        False, ["dcat", "oca", "dcat version 1.0.0 → 1.1.0", "oca version 0.1 → 1.1.0"], [])
    ds = api.datasets["ds1"]
    assert ds["oca"]["d"] == "E2"
    assert ds["dcat_version"] == ds["oca_version"] == "1.1.0"


def test_oca_change_without_version_bump_is_refused(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    plans, _, _, _ = run_sync(api, local(oca={**OCA, "d": "E2"}))
    assert "bumped" in results(plans)["ds1"][2][0]
    assert api.writes == []


def test_lower_or_reused_version_is_refused(api):
    api.add("ds1", {**DCAT, "dcat:version": "1.2.0"}, OCA, MAPPER)
    plans, _, _, _ = run_sync(api, local())
    assert "lower" in results(plans)["ds1"][2][0]

    api.datasets["ds1"]["versions"]["dcat"].add("1.3.0")
    plans, _, _, _ = run_sync(api, local(dcat={**DCAT, "dcat:version": "1.3.0"}))
    assert "already has a dcat version 1.3.0" in results(plans)["ds1"][2][0]
    assert api.writes == []


def test_mapper_change_puts_translation(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    mapper = copy.deepcopy(MAPPER)
    mapper["fr"]["title"]["value"] = "Nouveau titre"
    plans, _, _, _ = run_sync(api, local(mapper=mapper))
    assert results(plans)["ds1"] == (False, ["fr translation"], [])
    assert api.datasets["ds1"]["translations"]["fr"]["title"] == "Nouveau titre"


def test_missing_translation_is_added(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    del api.datasets["ds1"]["translations"]["fr"]
    plans, _, _, _ = run_sync(api, local())
    assert results(plans)["ds1"] == (False, ["fr translation"], [])


def test_orphans_are_reported_not_deleted(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    api.add("old1", {**DCAT, "dcterms:identifier": "old1"}, OCA, MAPPER)
    plans, _, orphans, _ = run_sync(api, local())
    assert orphans == ["old1"]
    assert "old1" in api.datasets
    assert "`old1`" in report(plans, DatasetPlan("catalog.json"), orphans, [], "http://api", dry_run=False)


def test_missing_languages_are_created(api):
    api.languages = []
    _, _, _, languages = run_sync(api, local())
    assert [a.label for a in languages] == ["language en", "language fr"]
    assert [lang["code"] for lang in api.languages] == ["en", "fr"]


def test_failed_write_is_reported(api):
    api.add("ds1", DCAT, OCA, MAPPER)
    api.handler, real = (lambda request: httpx.Response(500, text="boom")
                         if request.method == "PATCH" else real(request)), api.handler
    plans, _, _, _ = run_sync(api, local(dcat={**DCAT, "dcterms:title": "Fixed"}))
    assert "500 boom" in results(plans)["ds1"][2][0]
    assert "**error**" in report(plans, DatasetPlan("catalog.json"), [], [], "http://api", dry_run=False)


def catalog_result(plan):
    return (plan.created, [a.label for a in plan.actions], plan.errors)


def test_unchanged_catalog_makes_no_writes(api):
    _, catalog_plan, _, _ = run_sync(api, {})
    assert catalog_result(catalog_plan) == (False, [], [])
    assert api.writes == []


def test_missing_catalog_is_created(api):
    api.catalog = None
    _, catalog_plan, _, _ = run_sync(api, {})
    assert catalog_result(catalog_plan) == (True, ["catalog"], [])
    assert api.catalog["dcterms:title"] == "Catalogue"


@pytest.mark.parametrize("change", [
    {"dcterms:title": "New title"},
    {"@context": {**CATALOG["@context"], "foaf": "http://xmlns.com/foaf/0.1/"}},
])
def test_changed_catalog_is_put(api, change):
    _, catalog_plan, _, _ = run_sync(api, {}, catalog={**CATALOG, **change})
    assert catalog_result(catalog_plan) == (False, ["catalog"], [])
    assert api.writes == [("PUT", "/catalog")]


def test_removed_catalog_field_is_put(api):
    catalog = {k: v for k, v in CATALOG.items() if k != "dcterms:description"}
    _, catalog_plan, _, _ = run_sync(api, {}, catalog=catalog)
    assert catalog_result(catalog_plan)[1] == ["catalog"]


def test_catalog_dry_run_makes_no_writes(api):
    _, catalog_plan, _, _ = run_sync(api, {}, dry_run=True, catalog={**CATALOG, "dcterms:title": "New"})
    assert catalog_result(catalog_plan)[1] == ["catalog"]
    assert api.writes == []


def test_failed_catalog_write_is_reported(api):
    api.handler, real = (lambda request: httpx.Response(400, text="bad catalog")
                         if request.method == "PUT" else real(request)), api.handler
    plans, catalog_plan, orphans, languages = run_sync(api, {}, catalog={**CATALOG, "dcterms:title": "New"})
    assert "400 bad catalog" in catalog_plan.errors[0]
    assert "| `catalog.json` | **error**" in report(plans, catalog_plan, orphans, languages, "http://api", dry_run=False)
