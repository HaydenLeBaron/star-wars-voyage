import os
import csv
import json
import hashlib
import re
import base64

# Base paths
WORKSPACE_DIR = "/Users/haydenlebaron/my-repos/vibes/star-wars-voyage"
CHARACTERS_JSON_PATH = os.path.join(WORKSPACE_DIR, "star-wars-raw-context/star-wars-databank-vercel-app/star-wars-character-data.json")
NPCS_DIR = os.path.join(WORKSPACE_DIR, "massaged-context/npcs")
OUTPUT_JSON_PATH = os.path.join(WORKSPACE_DIR, "voyage/src/t2-world/s5-npcs/s5-npcs.json")

def generate_embedding_id(name):
    # Generates a deterministic 8-character alphanumeric string based on the name
    digest = hashlib.sha256(name.encode('utf-8')).digest()
    b64 = base64.urlsafe_b64encode(digest).decode('utf-8')
    # Replace characters that might confuse pathing or schemas and return first 8 chars
    return b64.replace('-', 'A').replace('_', 'B')[:8]

def clean_value(val):
    if not val:
        return ""
    return val.strip().replace('"', '')

def parse_csv(filepath):
    rows = []
    if not os.path.exists(filepath):
        print(f"Warning: file not found: {filepath}")
        return rows
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            return rows
        headers = [h.strip() for h in headers]
        for row in reader:
            if not row:
                continue
            row_dict = {}
            for idx, val in enumerate(row):
                if idx < len(headers):
                    row_dict[headers[idx]] = val.strip()
            rows.append(row_dict)
    return rows

def load_databank_characters():
    characters = []
    if not os.path.exists(CHARACTERS_JSON_PATH):
        print(f"Warning: {CHARACTERS_JSON_PATH} not found.")
        return characters
    with open(CHARACTERS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        for char in data:
            name = clean_value(char.get("name", ""))
            if not name:
                continue
            desc = clean_value(char.get("description", ""))
            image = clean_value(char.get("image", ""))
            
            npc = {
                "name": name,
                "type": "",
                "currentLocation": "",
                "currentArea": "",
                "gender": "",
                "basicInfo": desc or f"A known Star Wars character.",
                "hiddenInfo": "",
                "personality": [],
                "abilities": [],
                "tier": "strong",
                "detailType": "basic",
                "portraitUrl": image,
                "embeddingId": generate_embedding_id(name)
            }
            characters.append(npc)
    return characters

def map_droids():
    droids = []
    filepath = os.path.join(NPCS_DIR, "droids.csv")
    rows = parse_csv(filepath)
    for row in rows:
        name = row.get("Model", "").strip()
        if not name:
            name = row.get("NPC", "").strip()
        if not name or name.lower() in ["npc", "model", ""]:
            continue
        
        npc_tier = row.get("NPC", "").strip()
        tier = "strong"
        if npc_tier.lower() == "minion":
            tier = "basic"
        elif npc_tier.lower() == "rival":
            tier = "strong"
        elif npc_tier.lower() == "nemesis":
            tier = "elite"
            
        category = row.get("Category", "").strip()
        soak = row.get("Soak", "").strip()
        wt = row.get("WT", "").strip()
        st = row.get("ST", "").strip()
        def_val = row.get("M/R Def.", "").strip()
        skills = row.get("Skills", "").strip()
        restricted = row.get("(Restricted)", "").strip()
        price = row.get("Price", "").strip()
        rarity = row.get("Rarity0to10", "").strip()
        stats = row.get("Br/Ag/Int/Cun/Wil/Pr", "").strip()
        
        basic_info = f"A droid model of type {category}. Model: {name}."
        if price:
            basic_info += f" Base Price: {price} credits."
        if rarity:
            basic_info += f" Rarity: {rarity}/10."
            
        abilities = []
        if stats:
            parts = stats.split("/")
            if len(parts) == 6:
                abilities.append(f"Stats: Brawn {parts[0]}, Agility {parts[1]}, Intellect {parts[2]}, Cunning {parts[3]}, Willpower {parts[4]}, Presence {parts[5]}")
        if soak:
            abilities.append(f"Soak: {soak}")
        if wt:
            abilities.append(f"Wound Threshold: {wt}")
        if st and st != "-":
            abilities.append(f"Strain Threshold: {st}")
        if def_val:
            abilities.append(f"Defense (M/R): {def_val}")
        if skills:
            for s in [x.strip() for x in skills.split(",") if x.strip()]:
                abilities.append(f"Skill: {s}")
        if restricted:
            abilities.append("Restricted Droid Model")
            
        npc = {
            "name": name,
            "type": "",
            "currentLocation": "",
            "currentArea": "",
            "gender": "",
            "basicInfo": basic_info,
            "hiddenInfo": "",
            "personality": [],
            "abilities": abilities,
            "tier": tier,
            "detailType": "detailed",
            "portraitUrl": "",
            "embeddingId": generate_embedding_id(name)
        }
        droids.append(npc)
    return droids

def map_riding_beasts():
    beasts = []
    filepath = os.path.join(NPCS_DIR, "riding-beasts.csv")
    rows = parse_csv(filepath)
    for row in rows:
        name = row.get("Model", "").strip()
        if not name or name.lower() in ["model", ""]:
            continue
        
        npc_tier = row.get("NPC", "").strip()
        tier = "strong"
        if npc_tier.lower() == "minion":
            tier = "basic"
        elif npc_tier.lower() == "rival":
            tier = "strong"
        elif npc_tier.lower() == "nemesis":
            tier = "elite"
            
        soak = row.get("Soak", "").strip()
        wt = row.get("WT", "").strip()
        st = row.get("ST", "").strip()
        def_val = row.get("M/R Def.", "").strip()
        skills = row.get("Skills", "").strip()
        talents = row.get("Talents", "").strip()
        spec_abilities = row.get("Abilities", "").strip()
        equipment = row.get("Equipment", "").strip()
        price = row.get("Price", "").strip()
        rarity = row.get("Rarity0to10", "").strip()
        stats = row.get("Br/Ag/Int/Cun/Wil/Pr", "").strip()
        
        basic_info = f"A native riding beast. Model: {name}."
        if equipment and equipment.lower() != "none":
            basic_info += f" Natural Equipment: {equipment}"
        if price:
            basic_info += f" Price: {price} credits."
        if rarity:
            basic_info += f" Rarity: {rarity}/10."
            
        abilities = []
        if stats:
            parts = stats.split("/")
            if len(parts) == 6:
                abilities.append(f"Stats: Brawn {parts[0]}, Agility {parts[1]}, Intellect {parts[2]}, Cunning {parts[3]}, Willpower {parts[4]}, Presence {parts[5]}")
        if soak:
            abilities.append(f"Soak: {soak}")
        if wt:
            abilities.append(f"Wound Threshold: {wt}")
        if st and st != "-":
            abilities.append(f"Strain Threshold: {st}")
        if def_val:
            abilities.append(f"Defense (M/R): {def_val}")
        if skills:
            for s in [x.strip() for x in skills.split(",") if x.strip()]:
                abilities.append(f"Skill: {s}")
        if talents and talents.lower() != "none":
            abilities.append(f"Talents: {talents}")
        if spec_abilities and spec_abilities.lower() != "none":
            # Split abilities carefully, sometimes they are comma separated with text in parentheses
            parts = []
            current = []
            paren_depth = 0
            for char in spec_abilities:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                if char == ',' and paren_depth == 0:
                    parts.append("".join(current).strip())
                    current = []
                else:
                    current.append(char)
            if current:
                parts.append("".join(current).strip())
            for part in parts:
                if part:
                    abilities.append(f"Ability: {part}")
                    
        npc = {
            "name": name,
            "type": "",
            "currentLocation": "",
            "currentArea": "",
            "gender": "",
            "basicInfo": basic_info,
            "hiddenInfo": "",
            "personality": [],
            "abilities": abilities,
            "tier": tier,
            "detailType": "detailed",
            "portraitUrl": "",
            "embeddingId": generate_embedding_id(name)
        }
        beasts.append(npc)
    return beasts

def map_vehicular_droids():
    vessels = []
    filepath = os.path.join(NPCS_DIR, "starfighter-and-vehicular-droids.csv")
    rows = parse_csv(filepath)
    for row in rows:
        name = row.get("Name", "").strip()
        if not name or name.lower() in ["name", ""]:
            continue
            
        silh = row.get("Silh.", "").strip()
        speed = row.get("Speed", "").strip()
        hand = row.get("Hand.", "").strip()
        def_val = row.get("Def.", "").strip()
        armor = row.get("Armor", "").strip()
        ht = row.get("HT", "").strip()
        ss = row.get("SS", "").strip()
        restricted = row.get("(Restricted)", "").strip()
        price = row.get("Price", "").strip()
        rarity = row.get("Rarity0to10", "").strip()
        
        basic_info = f"An automated starfighter / vehicular droid. Model: {name}."
        if price:
            basic_info += f" Price: {price} credits."
        if rarity:
            basic_info += f" Rarity: {rarity}/10."
            
        abilities = []
        if silh:
            abilities.append(f"Silhouette: {silh}")
        if speed:
            abilities.append(f"Speed: {speed}")
        if hand:
            abilities.append(f"Handling: {hand}")
        if def_val:
            abilities.append(f"Defense (F/A): {def_val}")
        if armor:
            abilities.append(f"Armor: {armor}")
        if ht:
            abilities.append(f"Hull Trauma Threshold: {ht}")
        if ss:
            abilities.append(f"System Strain Threshold: {ss}")
        if restricted:
            abilities.append("Restricted Model")
            
        npc = {
            "name": name,
            "type": "",
            "currentLocation": "",
            "currentArea": "",
            "gender": "",
            "basicInfo": basic_info,
            "hiddenInfo": "",
            "personality": [],
            "abilities": abilities,
            "tier": "strong",
            "detailType": "detailed",
            "portraitUrl": "",
            "embeddingId": generate_embedding_id(name)
        }
        vessels.append(npc)
    return vessels

def map_planetside_vehicles():
    vehicles = []
    folder = os.path.join(NPCS_DIR, "planetside-vehicles")
    if not os.path.exists(folder):
        print(f"Warning: Planetside vehicles directory not found: {folder}")
        return vehicles
    for file in os.listdir(folder):
        if file.endswith(".csv"):
            filepath = os.path.join(folder, file)
            category_name = file.replace(".csv", "").replace("-", " ").title()
            rows = parse_csv(filepath)
            for row in rows:
                name = row.get("Model", "").strip()
                if not name:
                    name = row.get("Name", "").strip()
                if not name or name.lower() in ["model", "name", ""]:
                    continue
                
                silh = row.get("Silhouette", "").strip()
                speed = row.get("Speed", "").strip()
                hp = row.get("HP", "").strip()
                restricted = row.get("(Restricted)", "").strip()
                price = row.get("Price", "").strip()
                rarity = row.get("Rarity0to10", "").strip()
                weapons = row.get("Weapons?", "").strip()
                cat = row.get("Category", category_name).strip()
                
                hand = row.get("Handling", "").strip()
                hull = row.get("Hull", "").strip()
                system = row.get("System", "").strip()
                
                basic_info = f"A planetside vehicle of category {cat}. Model: {name}."
                if price:
                    basic_info += f" Price: {price} credits."
                if rarity:
                    basic_info += f" Rarity: {rarity}/10."
                    
                abilities = []
                if silh:
                    abilities.append(f"Silhouette: {silh}")
                if speed:
                    abilities.append(f"Speed: {speed}")
                if hand:
                    abilities.append(f"Handling: {hand}")
                if hp:
                    abilities.append(f"Hardpoints: {hp}")
                if hull:
                    abilities.append(f"Hull Trauma Threshold: {hull}")
                if system:
                    abilities.append(f"System Strain Threshold: {system}")
                if weapons and weapons.lower() != "no":
                    abilities.append(f"Weapons: {weapons}")
                if restricted:
                    abilities.append("Restricted Vehicle Model")
                    
                npc = {
                    "name": name,
                    "type": "",
                    "currentLocation": "",
                    "currentArea": "",
                    "gender": "",
                    "basicInfo": basic_info,
                    "hiddenInfo": "",
                    "personality": [],
                    "abilities": abilities,
                    "tier": "strong",
                    "detailType": "detailed",
                    "portraitUrl": "",
                    "embeddingId": generate_embedding_id(name)
                }
                vehicles.append(npc)
    return vehicles

def map_starships():
    starships = []
    folder = os.path.join(NPCS_DIR, "starships")
    if not os.path.exists(folder):
        print(f"Warning: Starships directory not found: {folder}")
        return starships
    for file in os.listdir(folder):
        if file.endswith(".csv"):
            filepath = os.path.join(folder, file)
            category_name = file.replace(".csv", "").replace("-", " ").title()
            rows = parse_csv(filepath)
            for row in rows:
                name = row.get("Model", "").strip()
                if not name or name.lower() in ["model", ""]:
                    continue
                    
                silh = row.get("Silhouette", "").strip()
                speed = row.get("Speed", "").strip()
                hp = row.get("HP", "").strip()
                price = row.get("Price", "").strip()
                rarity = row.get("Rarity0to10", "").strip()
                hyperdrive = row.get("Hyperdrive", "").strip() or row.get("Hyperdrive?", "").strip()
                crew = row.get("Crew Complement", "").strip()
                weapons = row.get("Weapons?", "").strip() or row.get("# of Weapons", "").strip() or row.get("No of Weapon Batteries", "").strip()
                special = row.get("Special Features", "").strip() or row.get("Special;", "").strip()
                passengers = row.get("Passengers", "").strip() or row.get("Encumbrance / Passengers", "").strip()
                encumbrance = row.get("Encumbrance", "").strip()
                cat = row.get("Category", category_name).strip()
                
                basic_info = f"A starship of category {cat}. Model: {name}."
                if price:
                    basic_info += f" Price: {price} credits."
                if rarity:
                    basic_info += f" Rarity: {rarity}/10."
                if special and special.lower() != "-":
                    basic_info += f" Special Features: {special}"
                    
                abilities = []
                if silh:
                    abilities.append(f"Silhouette: {silh}")
                if speed:
                    abilities.append(f"Speed: {speed}")
                if hp:
                    abilities.append(f"Hardpoints: {hp}")
                if hyperdrive and hyperdrive.lower() != "-":
                    abilities.append(f"Hyperdrive: {hyperdrive}")
                if crew:
                    abilities.append(f"Crew Complement: {crew}")
                if weapons and weapons.lower() not in ["-", "no"]:
                    abilities.append(f"Weapons: {weapons}")
                if passengers and passengers.lower() != "-":
                    abilities.append(f"Passengers: {passengers}")
                if encumbrance:
                    abilities.append(f"Encumbrance: {encumbrance}")
                    
                npc = {
                    "name": name,
                    "type": "",
                    "currentLocation": "",
                    "currentArea": "",
                    "gender": "",
                    "basicInfo": basic_info,
                    "hiddenInfo": "",
                    "personality": [],
                    "abilities": abilities,
                    "tier": "strong",
                    "detailType": "detailed",
                    "portraitUrl": "",
                    "embeddingId": generate_embedding_id(name)
                }
                starships.append(npc)
    return starships

def main():
    print("Porting characters and NPCs...")
    
    # Dict to store unique NPCs. Key is name.
    npcs_map = {}
    lower_to_orig = {}
    
    def add_or_merge_npc(npc):
        name = npc["name"]
        name_lower = name.lower()
        if name_lower in lower_to_orig:
            orig_name = lower_to_orig[name_lower]
            existing = npcs_map[orig_name]
            
            # Merge!
            if len(npc["basicInfo"]) > len(existing["basicInfo"]):
                existing["basicInfo"] = npc["basicInfo"]
            if npc["portraitUrl"] and not existing["portraitUrl"]:
                existing["portraitUrl"] = npc["portraitUrl"]
            for ability in npc["abilities"]:
                if ability not in existing["abilities"]:
                    existing["abilities"].append(ability)
            if npc["detailType"] == "detailed" or existing["detailType"] == "detailed":
                existing["detailType"] = "detailed"
            tier_order = {"basic": 0, "strong": 1, "elite": 2, "boss": 3}
            if tier_order.get(npc["tier"], 0) > tier_order.get(existing["tier"], 0):
                existing["tier"] = npc["tier"]
        else:
            lower_to_orig[name_lower] = name
            npcs_map[name] = npc

    # 1. Load characters
    print("Loading databank characters...")
    chars = load_databank_characters()
    print(f"  Found {len(chars)} characters.")
    for c in chars:
        add_or_merge_npc(c)
        
    # 2. Load droids
    print("Loading droids...")
    droids = map_droids()
    print(f"  Found {len(droids)} droids.")
    for d in droids:
        add_or_merge_npc(d)
        
    # 3. Load riding beasts
    print("Loading riding beasts...")
    beasts = map_riding_beasts()
    print(f"  Found {len(beasts)} riding beasts.")
    for b in beasts:
        add_or_merge_npc(b)
        
    # 4. Load vehicle droids
    print("Loading vehicular droids...")
    vehicular_droids = map_vehicular_droids()
    print(f"  Found {len(vehicular_droids)} vehicular droids.")
    for vd in vehicular_droids:
        add_or_merge_npc(vd)
        
    # 5. Load planetside vehicles
    print("Loading planetside vehicles...")
    vehicles = map_planetside_vehicles()
    print(f"  Found {len(vehicles)} planetside vehicles.")
    for v in vehicles:
        add_or_merge_npc(v)
        
    # 6. Load starships
    print("Loading starships...")
    starships = map_starships()
    print(f"  Found {len(starships)} starships.")
    for s in starships:
        add_or_merge_npc(s)
        
    print(f"Total unique NPCs after merge: {len(npcs_map)}")
    
    # Save output
    output_data = {
        "npcs": npcs_map
    }
    
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully wrote {len(npcs_map)} NPCs to {OUTPUT_JSON_PATH}!")

if __name__ == "__main__":
    main()
