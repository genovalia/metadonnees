import os
import json
import pytest
import shutil
from catalogue_cli import list_keywords
from dataset_creator import get_existing_values, create_dataset_interactive

# Mocking directory and file structure for tests
@pytest.fixture
def temp_repo(tmp_path, monkeypatch):
    """Sets up a temporary repository structure."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    # Create templates
    templates_dir = repo_dir / "templates"
    templates_dir.mkdir()
    templates_dir.joinpath("dcat.jsonc").write_text(json.dumps({
        "@context": {},
        "dcterms:title": "",
        "dcterms:publisher": {},
        "dcterms:temporal": {
            "time:hasBeginning": {"time:inXSDgYear": ""},
            "time:hasEnd": {"time:inXSDgYear": ""}
        }
    }))
    (templates_dir / "mapper.jsonc").write_text('{"id": "TEMPLATE_ID"}')
    (templates_dir / "oca.json").write_text('{}')
    
    # Create dictionary
    (repo_dir / "dictionary.json").write_text(json.dumps({"known": "connu"}))
    
    # Create a dummy dataset
    ds_dir = repo_dir / "ds1"
    ds_dir.mkdir()
    (ds_dir / "dcat.json").write_text(json.dumps({
        "dcat:keyword": ["known", "unknown"],
        "dcterms:publisher": {"foaf:name": "Existing Publisher"}
    }))
    
    # Create catalogue.json
    (repo_dir / "catalogue.json").write_text(json.dumps({"content": []}))
    
    monkeypatch.chdir(repo_dir)
    return repo_dir

def test_list_keywords(temp_repo, capsys):
    """Test the list-keywords functionality."""
    class Args:
        pass
    
    list_keywords(Args())
    captured = capsys.readouterr()
    assert '"unknown": "unknown"' in captured.out
    assert '"known"' not in captured.out

def test_get_existing_values(temp_repo):
    """Test value extraction from existing datasets."""
    publishers = get_existing_values("dcterms:publisher")
    assert len(publishers) == 1
    assert publishers[0]["foaf:name"] == "Existing Publisher"

def test_create_dataset_logic(temp_repo, mocker):
    """Test the interactive creation logic by mocking questionary."""
    # Mock questionary prompts
    mock_text = mocker.patch("questionary.text")
    mock_select = mocker.patch("questionary.select")
    
    # Define sequence of inputs
    mock_text.return_value.ask.side_effect = [
        "newds",      # dataset_id
        "New Title",   # title
        "New Desc",    # description
        "k1, k2",     # keywords
        "ident1",     # identifier
        "theme1",     # theme
        "spatial1",   # spatial
        "2021",       # year_start
        "2022"        # year_end
    ]
    
    # Mock selects (Publisher, Contact, Creator)
    # 1. Publisher select (return "NEW" first)
    # 2. Contact select
    # 3. Creator select
    mock_select.return_value.ask.side_effect = ["NEW", "NEW", "NEW"]
    
    # Sub-prompts for "NEW" selections
    # This matches the order in create_dataset_interactive
    # (Publisher details, Contact details, Creator details)
    mock_text.return_value.ask.side_effect = [
        "newds", "New Title", "New Desc", # ID, Title, Desc
        "pub_id", "Pub Name", "Pub Home", # Publisher NEW details
        "Con Name", "con@mail.com",       # Contact NEW details
        "k1, k2",                         # Keywords
        "cre_id", "Cre Name", "cre@mail.com", # Creator NEW details
        "ident1", "theme1", "spatial1", "2021", "2022" # Rest
    ]

    create_dataset_interactive()
    
    assert os.path.exists("newds/dcat.json")
    assert os.path.exists("newds/mapper.json")
    
    with open("newds/dcat.json") as f:
        data = json.load(f)
        assert data["dcterms:title"] == "New Title"
        assert data["dcat:keyword"] == ["k1", "k2"]
    
    with open("catalogue.json") as f:
        catalog = json.load(f)
        assert any(item["id"] == "newds" for item in catalog["content"])
