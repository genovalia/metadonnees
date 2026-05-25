import json
import os
import glob
import shutil
import questionary
from typing import List, Dict, Any

def get_existing_values(field_path: str) -> List[Dict[str, Any]]:
    """Extract unique values for a specific field from all dcat.json files."""
    values = []
    seen = set()

    for dcat_file in glob.glob("**/dcat.json", recursive=True):
        if "templates" in dcat_file:
            continue
        try:
            with open(dcat_file, "r") as f:
                data = json.load(f)
                
            # Basic path traversal (e.g., "dcterms:publisher")
            parts = field_path.split('.')
            current = data
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = None
                    break
            
            if current:
                # Use a string representation to detect duplicates
                str_val = json.dumps(current, sort_keys=True)
                if str_val not in seen:
                    values.append(current)
                    seen.add(str_val)
        except Exception:
            continue
    return values

def prompt_complex_field(field_name: str, field_path: str, display_attr: str) -> Dict[str, Any]:
    """Prompt for a complex field, offering existing values or a new entry."""
    existing = get_existing_values(field_path)
    
    choices = []
    for val in existing:
        label = val.get(display_attr, str(val))
        choices.append(questionary.Choice(title=label, value=val))
    
    choices.append(questionary.Choice(title="[Enter new...]", value="NEW"))
    
    result = questionary.select(
        f"Select {field_name}:",
        choices=choices
    ).ask()
    
    if result == "NEW":
        # This part should be customized based on the field structure
        # For simplicity in this helper, we'll handle the common ones here or specialize
        return None 
    return result

def create_dataset_interactive():
    # 1. Dataset ID
    dataset_id = questionary.text("Dataset ID (e.g., bostau2):").ask()
    if not dataset_id:
        print("Dataset ID is required.")
        return

    if os.path.exists(dataset_id):
        print(f"Directory {dataset_id} already exists.")
        return

    # 2. Metadata Collection
    title = questionary.text("Title:").ask()
    description = questionary.text("Description:").ask()
    
    # Publisher
    publishers = get_existing_values("dcterms:publisher")
    pub_choices = [questionary.Choice(title=p.get("foaf:name", str(p)), value=p) for p in publishers]
    pub_choices.append(questionary.Choice(title="[Enter new...]", value="NEW"))
    publisher = questionary.select("Publisher:", choices=pub_choices).ask()
    if publisher == "NEW":
        publisher = {
            "@id": questionary.text("Publisher ID (URL):", default="https://genovalia.ulaval.ca/").ask(),
            "@type": "foaf:Organization",
            "foaf:name": questionary.text("Publisher Name:", default="Genovalia").ask(),
            "foaf:homepage": questionary.text("Publisher Homepage:", default="https://genovalia.ulaval.ca/").ask()
        }

    # Contact Point
    contacts = get_existing_values("dcat:contactPoint")
    con_choices = [questionary.Choice(title=c.get("vcard:fn", str(c)), value=c) for c in contacts]
    con_choices.append(questionary.Choice(title="[Enter new...]", value="NEW"))
    contact = questionary.select("Contact Point:", choices=con_choices).ask()
    if contact == "NEW":
        contact = {
            "@type": "vcard:Kind",
            "vcard:fn": questionary.text("Contact Name:", default="Genovalia").ask(),
            "vcard:hasEmail": {
                "@id": f"mailto:{questionary.text('Contact Email:', default='genovalia@ulaval.ca').ask()}"
            }
        }

    # Keywords
    keywords_raw = questionary.text("Keywords (comma separated):").ask()
    keywords = [k.strip() for k in keywords_raw.split(",")] if keywords_raw else []

    # Creator
    creators_list = get_existing_values("dcterms:creator")
    # Handle both single and multiple creators if they exist
    creators_flat = []
    seen_creators = set()
    for c in creators_list:
        if isinstance(c, list):
            for sub_c in c:
                s = json.dumps(sub_c, sort_keys=True)
                if s not in seen_creators:
                    creators_flat.append(sub_c)
                    seen_creators.add(s)
        else:
            s = json.dumps(c, sort_keys=True)
            if s not in seen_creators:
                creators_flat.append(c)
                seen_creators.add(s)

    cre_choices = [questionary.Choice(title=c.get("foaf:name", str(c)), value=c) for c in creators_flat]
    cre_choices.append(questionary.Choice(title="[Enter new...]", value="NEW"))
    creator = questionary.select("Creator:", choices=cre_choices).ask()
    if creator == "NEW":
        creator = {
            "@id": questionary.text("Creator ID (e.g. ORCID):").ask(),
            "@type": "foaf:Person",
            "foaf:name": questionary.text("Creator Name:").ask(),
            "foaf:mbox": f"mailto:{questionary.text('Creator Email:').ask()}"
        }

    # 3. Create Files
    os.makedirs(dataset_id)
    
    # Load template dcat
    with open("templates/dcat.jsonc", "r") as f:
        # Simple removal of comments for json loading if needed, 
        # but we'll just construct the dict
        template_lines = f.readlines()
        clean_lines = [line for line in template_lines if not line.strip().startswith("//")]
        dcat = json.loads("".join(clean_lines))

    # Update template with values
    dcat["dcterms:title"] = title
    dcat["dcterms:description"] = description
    dcat["dcterms:publisher"] = publisher
    dcat["dcat:contactPoint"] = contact
    dcat["dcat:keyword"] = keywords
    dcat["dcterms:creator"] = creator
    
    # Optional fields with defaults or prompts
    dcat["dcterms:identifier"] = questionary.text("Identifier (e.g. DOI):").ask() or ""
    dcat["dcat:theme"] = questionary.text("Theme (URL):").ask() or ""
    dcat["dcterms:spatial"] = questionary.text("Spatial (GeoNames URL):").ask() or ""
    
    year_start = questionary.text("Year Start:").ask()
    year_end = questionary.text("Year End:").ask()
    dcat["dcterms:temporal"]["time:hasBeginning"]["time:inXSDgYear"] = year_start
    dcat["dcterms:temporal"]["time:hasEnd"]["time:inXSDgYear"] = year_end

    # Write dcat.json
    with open(os.path.join(dataset_id, "dcat.json"), "w") as f:
        json.dump(dcat, f, indent=2)

    # Copy mapper and oca
    shutil.copy("templates/mapper.jsonc", os.path.join(dataset_id, "mapper.json"))
    shutil.copy("templates/oca.json", os.path.join(dataset_id, "oca.json"))
    
    # Update mapper ID
    with open(os.path.join(dataset_id, "mapper.json"), "r") as f:
        mapper_content = f.read()
    mapper_content = mapper_content.replace("TEMPLATE_ID", dataset_id)
    with open(os.path.join(dataset_id, "mapper.json"), "w") as f:
        f.write(mapper_content)

    # 4. Update catalogue.json
    with open("catalogue.json", "r") as f:
        catalog = json.load(f)
    
    catalog["content"].append({
        "id": dataset_id,
        "mapper": f"{dataset_id}/mapper.json",
        "OCA": f"{dataset_id}/oca.json",
        "DCAT": f"{dataset_id}/dcat.json"
    })
    
    with open("catalogue.json", "w") as f:
        json.dump(catalog, f, indent=2)

    print(f"\nSuccessfully created dataset '{dataset_id}'!")
