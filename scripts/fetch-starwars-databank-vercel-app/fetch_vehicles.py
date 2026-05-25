#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import time
import sys
import os

def fetch_page(page, limit=100):
    url = f"https://starwars-databank-server.onrender.com/api/v1/vehicles?page={page}&limit={limit}"
    print(f"Fetching: {url}")
    
    retries = 5
    backoff = 3
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            )
            # 60s timeout in case Render service is spinning up
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                else:
                    print(f"Error status: {response.status}")
        except (urllib.error.URLError, Exception) as e:
            print(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                print(f"Waiting {backoff} seconds before retrying...")
                time.sleep(backoff)
                backoff *= 2
            else:
                raise e
    raise Exception("Failed to fetch page after retries")

def main():
    all_vehicles = []
    page = 1
    limit = 100
    
    while True:
        try:
            result = fetch_page(page, limit)
        except Exception as e:
            print(f"Fatal error fetching page {page}: {e}")
            sys.exit(1)
            
        data = result.get("data", [])
        info = result.get("info", {})
        
        all_vehicles.extend(data)
        total_expected = info.get("total", "unknown")
        print(f"Page {page} fetched: got {len(data)} vehicles. Total so far: {len(all_vehicles)} / {total_expected}")
        
        # Check if we have reached the end
        next_page = info.get("next")
        if not next_page or len(data) == 0:
            break
            
        page += 1
        time.sleep(0.5) # Polite delay
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "star-wars-raw-context", "star-wars-databank-vercel-app", "star-wars-vehicles-data.json")
    
    # Ensure directory exists just in case
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_vehicles, f, indent=2, ensure_ascii=False)
        
    print(f"\nSuccessfully saved {len(all_vehicles)} vehicles to {output_path}")

if __name__ == "__main__":
    main()
