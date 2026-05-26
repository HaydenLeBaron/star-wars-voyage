import os
import csv
import json
import re

# Base paths
WORKSPACE_DIR = "/Users/haydenlebaron/my-repos/vibes/star-wars-voyage"
ITEMS_CSV_DIR = os.path.join(WORKSPACE_DIR, "massaged-context/items")
OUTPUT_JSON_PATH = os.path.join(WORKSPACE_DIR, "voyage/src/t2-world/s3-items/items.json")

# Category priority mapping for deduplication
CATEGORY_PRIORITY = {
    "Weapon": 5,
    "Apparel": 4,
    "Accessory": 3,
    "Tool": 2,
    "Consumable": 1,
    "Currency": 0,
    "Miscellaneous": 0
}

# Known stats and skills for bonus extraction
STATS = {'brawn', 'agility', 'intellect', 'cunning', 'willpower', 'presence', 'soak'}
SKILLS = {
    'astrogation', 'athletics', 'brawl', 'charm', 'coercion', 'computers', 'cool',
    'coordination', 'deception', 'discipline', 'gunnery', 'leadership', 'lightsaber',
    'mechanics', 'medicine', 'melee', 'negotiation', 'perception', 'piloting', 'ranged',
    'resilience', 'skulduggery', 'stealth', 'streetwise', 'survival', 'vigilance', 'xenology',
    'lore', 'warfare'
}

def resolve_category_and_slot(filepath, name):
    name_lower = name.lower()
    filename = os.path.basename(filepath).lower()
    
    # 0. Currency
    if name_lower in ["credits", "credit"]:
        return "Currency", ""
        
    # 1. Shields (should be Apparel, slot: shield)
    if "shield" in name_lower or "buckler" in name_lower:
        return "Apparel", "shield"
        
    # 2. Weapons & Lightsabers
    if "weapons" in filepath or "lightsabers" in filepath:
        return "Weapon", "Weapon"
        
    # 3. Armor (Apparel)
    if filename == "armor.csv" or any(w in name_lower for w in ["armor", "suit", "clothing", "robes", "apparel", "trenchcoat", "jacket", "cloak", "vest", "leggings", "boots", "gloves", "helmet", "doublet", "tunic", "trousers", "breeches", "greatcoat", "coveralls", "bodysuit", "regalia"]):
        # Determine slot by name
        if any(w in name_lower for w in ["helmet", "helm", "head", "visor", "hood"]):
            return "Apparel", "head"
        elif any(w in name_lower for w in ["boots", "shoes"]):
            return "Apparel", "feet"
        elif any(w in name_lower for w in ["greaves", "leggings", "pants", "trousers", "breeches"]):
            return "Apparel", "legs"
        elif any(w in name_lower for w in ["gloves", "gauntlets", "hands"]):
            return "Apparel", "hands"
        elif any(w in name_lower for w in ["coat", "cloak", "robe", "jacket", "trenchcoat"]):
            return "Apparel", "outerwear"
        else:
            return "Apparel", "body"
            
    # 4. Equipment Mods
    if "equipment-mods" in filepath or "mod" in filename:
        return "Accessory", "Accessory"
        
    # 5. Cybernetic Implants
    if "cybernetics" in filename or "implant" in name_lower:
        return "Accessory", "Accessory"
        
    # 6. Consumables
    if any(w in filename for w in ["poisons", "spice", "drugs", "toxins"]):
        return "Consumable", "Consumable"
    if any(w in name_lower for w in ["stim", "bacta", "salve", "synthskin", "synthflesh", "patch", "ration", "canteen", "water", "food", "caf", "drink", "whiskey", "wine", "delicacy", "herb", "powder", "pill", "potion"]):
        return "Consumable", "Consumable"
        
    # 7. Tools
    if any(w in filename for w in ["tools", "scanning", "security", "communications", "survival", "base-structures", "support-structures"]):
        return "Tool", ""
        
    # 8. Fallback
    return "Miscellaneous", ""

def parse_int_safe(val):
    if not val:
        return 0
    # remove comma, +, quotes, spaces
    val_clean = val.replace(",", "").replace("+", "").replace("\"", "").strip()
    if val_clean.startswith("-") and len(val_clean) > 1:
        # Check if negative number
        try:
            return int(val_clean)
        except ValueError:
            return 0
    try:
        # Extract first contiguous digits
        match = re.search(r'\d+', val_clean)
        if match:
            return int(match.group())
    except Exception:
        pass
    return 0

def extract_bonuses_and_description(row, category, filename, name):
    bonuses = []
    
    # 1. Base category bonuses
    if category == "Apparel":
        soak_val = parse_int_safe(row.get("soak", ""))
        def_val = parse_int_safe(row.get("defense", ""))
        armor_val = soak_val * 50 + def_val * 25
        if armor_val > 0:
            bonuses.append({
                "type": "stat",
                "variable": "armor",
                "value": armor_val
            })
            
    elif category == "Weapon":
        dam_val = parse_int_safe(row.get("dam", ""))
        if dam_val > 0:
            bonuses.append({
                "type": "stat",
                "variable": "damage",
                "value": dam_val
            })
            
    # 2. Text-based bonuses from Features, Effect, or Special
    combined_text = ""
    desc_val = ""
    
    # Find any of these text columns
    for col in ["features", "effect", "special"]:
        if col in row and row[col]:
            val = row[col].strip()
            if val:
                combined_text += " " + val
                if not desc_val:
                    desc_val = val
                elif val not in desc_val:
                    desc_val += " | " + val

    # If no text column has a value, construct a default description
    if not desc_val:
        if category == "Weapon":
            desc_val = f"A combat-ready Star Wars weapon. Skill: {row.get('skill', 'Combat')}, Damage: {row.get('dam', '0')}, Crit: {row.get('crit', '-')}, Range: {row.get('range', 'Engaged')}."
        elif category == "Apparel":
            desc_val = f"Protective wear. Soak: {row.get('soak', '0')}, Defense: {row.get('defense', '0')}, HP: {row.get('hp', '0')}."
        elif category == "Accessory":
            desc_val = f"An accessory modification for gear, weapons, or armor."
        elif category == "Consumable":
            desc_val = f"A consumable item. Price: {row.get('price', '0')}, Rarity: {row.get('rarity0to10', '0')}."
        else:
            desc_val = f"A useful Star Wars item."

    # Search for +1, +2, etc. stat/skill bonuses in text
    if combined_text:
        # Match pattern: "+1 Brawn" or "Add +2 to Athletics"
        # We can look for +[digits] followed by words, or words followed by +[digits]
        pattern1 = r'\+\s*([1-9])\s*(?:to\s*)?([a-zA-Z\s\-]+)'
        pattern2 = r'([a-zA-Z\s\-]+)\s*\+\s*([1-9])'
        
        extracted = []
        for match in re.finditer(pattern1, combined_text):
            val = int(match.group(1))
            var_name = match.group(2).strip().lower()
            extracted.append((var_name, val))
            
        for match in re.finditer(pattern2, combined_text):
            var_name = match.group(1).strip().lower()
            val = int(match.group(2))
            extracted.append((var_name, val))
            
        for var_name, val in extracted:
            # Clean var_name (remove words like "to", "add")
            var_clean = re.sub(r'^(?:add|to|a|an)\s+', '', var_name).strip()
            # If multiple skills listed, split them (e.g. "vigilance & perception" or "vigilance and perception")
            parts = re.split(r'\s+(?:and|&)\s+', var_clean)
            for part in parts:
                part = part.strip()
                if part in STATS:
                    # Avoid duplicates
                    if not any(b["type"] == "stat" and b["variable"] == part for b in bonuses):
                        bonuses.append({
                            "type": "stat",
                            "variable": part,
                            "value": val
                        })
                elif part in SKILLS:
                    if not any(b["type"] == "skill" and b["variable"] == part for b in bonuses):
                        bonuses.append({
                            "type": "skill",
                            "variable": part,
                            "value": val
                        })

    return bonuses, desc_val

def main():
    print(f"Reading CSV files from {ITEMS_CSV_DIR}...")
    
    items_map = {}
    
    for root, dirs, files in os.walk(ITEMS_CSV_DIR):
        for file in files:
            if file.endswith(".csv"):
                filepath = os.path.join(root, file)
                filename = os.path.basename(filepath)
                
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    if not headers:
                        continue
                    
                    # Convert headers to lowercase for easy lookup
                    headers_lower = [h.lower() for h in headers]
                    
                    # Determine Name column index
                    name_idx = -1
                    for idx, h in enumerate(headers_lower):
                        if h in ["name", "type", "gear", "modification", "drug", "poison", "equipment"]:
                            name_idx = idx
                            break
                    if name_idx == -1:
                        print(f"  Warning: No name column found in {file} headers: {headers}")
                        continue
                    
                    for row in reader:
                        if not row or len(row) <= name_idx:
                            continue
                        name = row[name_idx].strip()
                        if not name:
                            continue
                        
                        # Map row to dictionary
                        row_dict = {}
                        for idx, val in enumerate(row):
                            if idx < len(headers_lower):
                                row_dict[headers_lower[idx]] = val.strip()
                        
                        # Resolve Category and Slot
                        category, slot = resolve_category_and_slot(filepath, name)
                        
                        # Extract bonuses and description
                        bonuses, description = extract_bonuses_and_description(row_dict, category, filename, name)
                        
                        item_data = {
                            "name": name,
                            "category": category,
                            "description": description,
                            "bonuses": bonuses
                        }
                        if slot:
                            item_data["slot"] = slot
                        else:
                            item_data["slot"] = ""
                            
                        # Deduplication logic
                        if name in items_map:
                            prev_category = items_map[name]["category"]
                            if CATEGORY_PRIORITY[category] > CATEGORY_PRIORITY[prev_category]:
                                print(f"  Updating '{name}': {prev_category} -> {category}")
                                items_map[name] = item_data
                            else:
                                # Merge description or bonuses if they are richer
                                if len(item_data["description"]) > len(items_map[name]["description"]):
                                    items_map[name]["description"] = item_data["description"]
                                for bonus in item_data["bonuses"]:
                                    if bonus not in items_map[name]["bonuses"]:
                                        items_map[name]["bonuses"].append(bonus)
                        else:
                            items_map[name] = item_data
                            
    # Dump to output file
    output_data = {
        "items": items_map
    }
    
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
        
    print(f"\nSuccessfully wrote {len(items_map)} unique items to {OUTPUT_JSON_PATH}!")

if __name__ == "__main__":
    main()
