"""
discover_stores.py

One-off (or occasional) script to build/refresh the list of coffee shop
locations across Greater London using the Places API (New) - Text Search.

Uses only Essentials-tier fields (id, displayName, formattedAddress,
location), which are free/cheap - the paid field (business_status) is only
requested later in check_status.py, on a weekly schedule, to stay inside
Google's free monthly allowance.

Run this manually whenever you want to rescan for NEW stores that have
opened (it won't remove stores from the store list automatically -
closures are tracked separately by check_status.py).

Usage:
    export GOOGLE_API_KEY="your-key-here"
    export BRAND="Starbucks"                      # or "Costa Coffee"
    export OUTPUT_FILE="stores_starbucks.json"     # or stores_costa.json
    python discover_stores.py

Output:
    <OUTPUT_FILE> - list of {place_id, name, address, lat, lng}
"""

import json
import os
import time
import requests

API_KEY = os.environ["GOOGLE_API_KEY"]
BRAND = os.environ.get("BRAND", "Starbucks")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "stores.json")

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Essentials-tier fields only - cheapest possible discovery pass.
FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,nextPageToken"

# Bounding box roughly covering Greater London (with a bit of buffer)
LAT_MIN, LAT_MAX = 51.28, 51.70
LNG_MIN, LNG_MAX = -0.52, 0.34

# Grid spacing - smaller = more thorough but more API calls.
GRID_SPACING_DEG_LAT = 0.045   # ~5km
GRID_SPACING_DEG_LNG = 0.072   # ~5km at London's latitude
SEARCH_RADIUS_M = 4000


def frange(start, stop, step):
    vals = []
    v = start
    while v <= stop:
        vals.append(round(v, 6))
        v += step
    return vals


def search_point(lat, lng):
    """Return all matching places near (lat, lng), following pagination."""
    results = []
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "textQuery": BRAND,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": SEARCH_RADIUS_M,
            }
        },
    }

    page_token = None
    while True:
        if page_token:
            body["pageToken"] = page_token
        resp = requests.post(SEARCH_URL, headers=headers, json=body, timeout=15)
        if resp.status_code != 200:
            print(f"  ! API error at {lat},{lng}: {resp.status_code} {resp.text[:200]}")
            break

        data = resp.json()
        for place in data.get("places", []):
            name = place.get("displayName", {}).get("text", "")
            brand_key = BRAND.split()[0].lower()  # e.g. "costa" from "Costa Coffee"
            if brand_key in name.lower():
                results.append(place)

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(2)  # token needs a moment to become valid

    return results


def main():
    lat_points = frange(LAT_MIN, LAT_MAX, GRID_SPACING_DEG_LAT)
    lng_points = frange(LNG_MIN, LNG_MAX, GRID_SPACING_DEG_LNG)
    total_points = len(lat_points) * len(lng_points)
    print(f"Scanning {total_points} grid points across Greater London for '{BRAND}'...")

    seen = {}
    count = 0
    for lat in lat_points:
        for lng in lng_points:
            count += 1
            print(f"[{count}/{total_points}] {lat},{lng}")
            for place in search_point(lat, lng):
                pid = place["id"]
                if pid not in seen:
                    loc = place.get("location", {})
                    seen[pid] = {
                        "place_id": pid,
                        "name": place.get("displayName", {}).get("text"),
                        "address": place.get("formattedAddress"),
                        "lat": loc.get("latitude"),
                        "lng": loc.get("longitude"),
                    }
            time.sleep(0.2)  # be polite to the API

    stores = list(seen.values())
    with open(OUTPUT_FILE, "w") as f:
        json.dump(stores, f, indent=2)

    print(f"\nDone. Found {len(stores)} unique {BRAND} locations.")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
