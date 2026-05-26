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
    
    # Find any of these text columns
    for col in ["features", "effect", "special"]:
        if col in row and row[col]:
            val = row[col].strip()
            if val:
                combined_text += " " + val

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

    return bonuses, ""

# Suffixes representing source books or technical/database duplicate annotations to be stripped
STRIP_SUFFIXES = {
    'CaM', 'CotR', 'DC', 'DoH', 'EotE', 'EtU', 'FC', 'FO', 'FiB', 'GaG', 
    'GaG, AoR', 'GaG, CaM', 'KoF', 'KtP', 'LoNH', 'ND', 'RotS', 'SM', 'SS', 
    'SS Errata', 'SS, DC', 'SoF', 'table', 'table entry', 'entry'
}

def normalize_name(name):
    # Strip quotes
    name = name.strip('"\'')
    
    # Check if there is a trailing parenthetical suffix to strip
    match = re.search(r'\(([^)]+)\)\s*$', name)
    if match:
        suffix = match.group(1).strip()
        if suffix in STRIP_SUFFIXES:
            name = re.sub(r'\s*\([^)]+\)\s*$', '', name)
            
    return name.strip()

def merge_bonuses(bonuses1, bonuses2):
    # Merge two lists of bonus dictionaries
    merged = list(bonuses1)
    for b in bonuses2:
        if b not in merged:
            # Check if there's an existing bonus of same type and variable
            existing = next((x for x in merged if x['type'] == b['type'] and x['variable'] == b['variable']), None)
            if existing:
                # Keep the one with higher absolute value
                if abs(b.get('value', 0)) > abs(existing.get('value', 0)):
                    existing['value'] = b['value']
            else:
                merged.append(b)
    return merged

def main():
    print(f"Reading CSV files from {ITEMS_CSV_DIR}...")
    
    raw_items = []
    
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
                            "description": description if description else "",
                            "bonuses": bonuses
                        }
                        if slot:
                            item_data["slot"] = slot
                        else:
                            item_data["slot"] = ""
                        
                        raw_items.append(item_data)
                            
    # Group items by normalized name
    grouped_items = {}
    for item in raw_items:
        norm = normalize_name(item["name"])
        if norm not in grouped_items:
            grouped_items[norm] = []
        grouped_items[norm].append(item)
        
    items_map = {}
    merges_count = 0
    
    for norm, group in grouped_items.items():
        if len(group) == 1:
            # Single item - just rename to clean normalized name and keep it
            item = group[0]
            item["name"] = norm
            items_map[norm] = item
        else:
            # Multiple items - group by category/slot to keep functional variants separate
            subgroups = {}
            for item in group:
                sub_key = (item["category"], item["slot"])
                if sub_key not in subgroups:
                    subgroups[sub_key] = []
                subgroups[sub_key].append(item)
                
            for (cat, slot), sub_items in subgroups.items():
                merged_item = {
                    "name": norm,
                    "category": cat,
                    "slot": slot,
                    "description": "",
                    "bonuses": []
                }
                
                # Seed with first item
                merged_item["description"] = sub_items[0]["description"]
                merged_item["bonuses"] = list(sub_items[0]["bonuses"])
                
                for item in sub_items[1:]:
                    # Keep richer description
                    desc = item["description"]
                    if desc and (not merged_item["description"] or len(desc) > len(merged_item["description"])):
                        merged_item["description"] = desc
                    # Merge bonuses
                    merged_item["bonuses"] = merge_bonuses(merged_item["bonuses"], item["bonuses"])
                
                if len(subgroups) > 1:
                    # If there are multiple functional variants, preserve names to distinguish them
                    for item in sub_items:
                        orig_name = item["name"]
                        clean_name = normalize_name(orig_name)
                        if clean_name == norm:
                            final_name = orig_name if orig_name != norm else f"{norm} ({cat})"
                        else:
                            final_name = orig_name
                        item_copy = dict(item)
                        item_copy["name"] = final_name
                        items_map[final_name] = item_copy
                else:
                    items_map[norm] = merged_item
                    if len(sub_items) > 1:
                        merges_count += 1
                        
    # Dump to output file
    output_data = {
        "items": items_map
    }
    
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
        
    print(f"\nSuccessfully wrote {len(items_map)} items to {OUTPUT_JSON_PATH}!")
    print(f"Total merged duplicate item groups: {merges_count}")

if __name__ == "__main__":
    main()
