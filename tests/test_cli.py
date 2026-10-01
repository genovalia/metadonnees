import os
import json
import subprocess
import pytest
import shutil
from pathlib import Path
from catalogue_cli import (
    check_catalog, check_dataset, check_dcat, check_tracked_files, discover_datasets, find_dataset_ids,
    validate,
)
from dataset_creator import get_existing_values, create_dataset_interactive, strip_jsonc_comments

REPO_ROOT = Path(__file__).resolve().parent.parent

# Mocking directory and file structure for tests
@pytest.fixture
def temp_repo(tmp_path, monkeypatch):
    """Sets up a temporary repository structure."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    # Create templates
    templates_dir = repo_dir / "templates"
    templates_dir.mkdir()
    # Use the real templates so comment handling is exercised
    shutil.copy(REPO_ROOT / "templates" / "dcat.jsonc", templates_dir / "dcat.jsonc")
    shutil.copy(REPO_ROOT / "templates" / "mapper.jsonc", templates_dir / "mapper.jsonc")
    
    # Create a dummy dataset
    ds_dir = repo_dir / "ds1"
    ds_dir.mkdir()
    (ds_dir / "dcat.json").write_text(json.dumps({
        "dcat:keyword": ["known", "unknown"],
        "dcterms:publisher": {"foaf:name": "Existing Publisher"}
    }))

    monkeypatch.chdir(repo_dir)
    return repo_dir

def test_get_existing_values(temp_repo):
    """Test value extraction from existing datasets."""
    publishers = get_existing_values("dcterms:publisher")
    assert len(publishers) == 1
    assert publishers[0]["foaf:name"] == "Existing Publisher"

def run_create_dataset(mocker, year_end):
    """Run create_dataset_interactive with mocked questionary answers."""
    mock_text = mocker.patch("questionary.text")
    mock_select = mocker.patch("questionary.select")

    # Publisher, Contact and Creator selects all pick "[Enter new...]"
    mock_select.return_value.ask.side_effect = ["NEW", "NEW", "NEW"]

    # Text prompts, in the order create_dataset_interactive asks them
    mock_text.return_value.ask.side_effect = [
        "newds", "New Title", "New Desc", # ID, Title, Desc
        "pub_id", "Pub Name", "Pub Home", # Publisher NEW details
        "Con Name", "con@mail.com",       # Contact NEW details
        "k1, k2",                         # Keywords
        "cre_id", "Cre Name", "cre@mail.com", # Creator NEW details
        "1.0.0", "2024-05-01", "theme1", "https://sws.geonames.org/6115047/", "2021", year_end # Rest
    ]

    create_dataset_interactive()

def test_create_dataset_logic(temp_repo, mocker):
    """Test the interactive creation logic by mocking questionary."""
    run_create_dataset(mocker, year_end="2022")

    assert os.path.exists("newds/dcat.json")
    assert os.path.exists("newds/mapper.json")

    with open("newds/dcat.json") as f:
        data = json.load(f)
        assert data["@id"] == "https://sedna.apps.genovalia.ulaval.ca/datasets/newds"
        assert data["dcat:landingPage"] == "https://sedna.apps.genovalia.ulaval.ca/datasets/newds"
        assert data["dcterms:identifier"] == "newds"
        assert data["dcat:version"] == "1.0.0"
        assert "dcterms:version" not in data
        assert data["dcterms:title"] == "New Title"
        assert data["dcat:keyword"] == ["k1", "k2"]
        assert data["dcterms:issued"] == "2024-05-01"
        assert data["dcterms:temporal"]["time:hasEnd"]["time:inXSDgYear"] == "2022"

    with open("newds/mapper.json") as f:
        mapper = json.load(f)
        assert mapper["id"] == "newds"

def test_create_dataset_ongoing(temp_repo, mocker):
    """A blank end year means an ongoing dataset: time:hasEnd is omitted."""
    run_create_dataset(mocker, year_end="")

    with open("newds/dcat.json") as f:
        data = json.load(f)
        assert "time:hasEnd" not in data["dcterms:temporal"]

def test_strip_jsonc_comments():
    """Comments are removed, but "//" inside strings (URLs) is kept."""
    text = '{\n  // a comment\n  "url": "https://example.org/a", // trailing\n  "q": "say \\"//\\""\n}'
    assert json.loads(strip_jsonc_comments(text)) == {"url": "https://example.org/a", "q": 'say "//"'}

VALID_DCAT = {
    "@id": "https://sedna.apps.genovalia.ulaval.ca/datasets/ds1",
    "dcterms:identifier": "ds1",
    "dcat:landingPage": "https://sedna.apps.genovalia.ulaval.ca/datasets/ds1",
    "dcat:version": "1.0.0",
    "dcterms:issued": "2026-09-08",
    "dcterms:temporal": {"time:hasBeginning": {"time:inXSDgYear": "2023"}},
    "dcterms:spatial": "https://sws.geonames.org/6115047/",
    "dcat:qualifiedAttribution": [
        {"prov:agent": {"foaf:name": "A"}, "dcat:hadRole": ["pointOfContact", "collaborator"]}
    ],
}

def test_check_dcat_valid():
    errors, warnings = check_dcat("ds1", VALID_DCAT)
    assert errors == []
    assert warnings == ["dcterms:license is empty", "dcat:distribution is empty"]

def test_check_dcat_flags_known_problems():
    """Each problem found in the catalog before the cleanup is reported."""
    dcat = {
        **VALID_DCAT,
        "@id": "",
        "dcterms:identifier": "https://genovalia.ulaval.ca/datasets/ds1",
        "dcterms:version": "0.1",
        "dcterms:temporal": {
            "time:hasBeginning": {"time:inXSDgYear": "2023"},
            "time:hasEnd": {"time:inXSDgYear": "present"},
        },
        "dcterms:spatial": "https://www.geonames.org/6115047/quebec.html",
        "dcat:qualifiedAttribution": [
            {"prov:Agent": {"foaf:name": "A"}, "dcat:hadRole": ["pointOfcontact"]}
        ],
    }
    del dcat["dcat:version"]
    errors, _ = check_dcat("ds1", dcat)
    joined = "\n".join(errors)
    for expected in ["@id", "dcterms:identifier", "dcterms:version", "dcat:version",
                     "time:hasEnd", "dcterms:spatial", "prov:Agent", "pointOfcontact"]:
        assert expected in joined

VALID_CATALOG = {
    "@id": "https://sedna.example/catalogue",
    "@type": "dcat:Catalog",
    "dcterms:title": [{"@value": "Catalogue", "@language": "fr"}],
    "dcterms:description": "Description",
    "dcterms:publisher": {"@id": "https://genovalia.ulaval.ca/"},
}

def test_check_catalog_valid():
    assert check_catalog(VALID_CATALOG) == []

def test_check_catalog_flags_problems():
    catalog = {
        **VALID_CATALOG,
        "@type": "dcat:Dataset",
        "dcterms:title": [],
        "dcat:dataset": [],
        "dct:modified": "2026-10-01",
    }
    del catalog["@id"], catalog["dcterms:publisher"]
    joined = "\n".join(check_catalog(catalog))
    for expected in ["@id", "@type", "dcterms:title", "dcterms:publisher", "dcat:dataset", "dct:modified"]:
        assert expected in joined

def test_check_tracked_files():
    """Stray files and folders are flagged; repo and dataset files are not."""
    paths = [
        "README.md", "templates/dcat.jsonc", "tests/test_cli.py", ".github/workflows/sync.yml",
        "ds1/dcat.json", "ds1/mapper.json", "ds1/oca.json",
        "exports/ds2_DCAT.json", "ds1/README.txt", "nouveaux/ds3/dcat.json", "notes.txt",
    ]
    errors = check_tracked_files(paths, set(find_dataset_ids(paths)))
    flagged = [e.split()[0] for e in errors]
    assert flagged == ["exports/ds2_DCAT.json", "ds1/README.txt", "nouveaux/ds3/dcat.json", "notes.txt"]

def test_find_dataset_ids():
    """A dataset is a top-level folder with a dcat.json, outside templates/ and tests/."""
    paths = [
        "ds1/dcat.json", "ds1/oca.json", "ds2/dcat.json", "ds3/oca.json",
        "templates/dcat.json", "temp/ds4/dcat.json", "dcat.json",
    ]
    assert find_dataset_ids(paths) == ["ds1", "ds2"]

def test_discover_datasets_skips_ignored_folders(tmp_path, monkeypatch):
    """Untracked new folders count; folders git ignores (temp/) never do."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    (tmp_path / ".gitignore").write_text("temp/\n")
    for folder in ("ds1", "temp", "temp/ds2", "notes"):
        (tmp_path / folder).mkdir()
    (tmp_path / "ds1" / "dcat.json").write_text("{}")
    (tmp_path / "temp" / "dcat.json").write_text("{}")
    (tmp_path / "temp" / "ds2" / "dcat.json").write_text("{}")
    (tmp_path / "notes" / "todo.txt").write_text("")
    assert discover_datasets() == ["ds1"]

def write_dataset(root, dataset_id, **docs):
    folder = root / dataset_id
    folder.mkdir()
    for name, content in docs.items():
        (folder / f"{name}.json").write_text(content if isinstance(content, str) else json.dumps(content))

def test_check_dataset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dcat = {**VALID_DCAT}
    write_dataset(tmp_path, "ds1", dcat=dcat, oca={}, mapper={"id": "ds1"})
    write_dataset(tmp_path, "ds2", dcat={**dcat, "dcterms:identifier": "ds2"}, oca="{not json", mapper={"id": "ds1"})
    write_dataset(tmp_path, "Ds_3", mapper={"id": "Ds_3"})

    assert check_dataset("ds1")[1] == []
    errors = "\n".join(check_dataset("ds2")[1])
    assert "oca.json is not valid JSON" in errors
    assert 'mapper.json "id" should be "ds2"' in errors
    errors = "\n".join(check_dataset("Ds_3")[1])
    assert "dcat.json is missing" in errors and "oca.json is missing" in errors
    assert "not a dataset ID" in errors

def test_repository_catalog_is_valid(monkeypatch):
    """The real catalog in this repository passes validation."""
    monkeypatch.chdir(REPO_ROOT)

    class Args:
        warnings = False

    validate(Args())  # exits with status 1 on any error
