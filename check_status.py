"""
check_status.py

Checks the current business_status of every store in the store list
against the last known status in the state file, using Places API (New)
Place Details. Posts a message to a Slack or Discord webhook whenever a
status changes (e.g. OPERATIONAL -> CLOSED_PERMANENTLY).

Cost note: business_status is a Pro-tier field ($17 per 1,000 calls past
the free 5,000/month allowance). Checking ~600 London stores WEEKLY stays
comfortably inside that free allowance. Checking daily would cost roughly
$150-220/month - the GitHub Actions schedule in this repo is set to
weekly on purpose. Don't change it to daily without expecting a bill.

Env vars required:
    GOOGLE_API_KEY   - your Google Places API key
    WEBHOOK_URL      - a Slack or Discord incoming webhook URL
    STORES_FILE      - e.g. "stores_starbucks.json" or "stores_costa.json"
    STATE_FILE       - e.g. "state_starbucks.json" or "state_costa.json"
"""

import json
import os
import time
import requests

API_KEY = os.environ["GOOGLE_API_KEY"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

STORES_FILE = os.environ.get("STORES_FILE", "stores.json")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")

DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = "businessStatus,displayName,formattedAddress,googleMapsUri"

STATUS_EMOJI = {
    "OPERATIONAL": "🟢",
    "CLOSED_TEMPORARILY": "🟡",
    "CLOSED_PERMANENTLY": "🔴",
}


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_status(place_id):
    headers = {
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    resp = requests.get(DETAILS_URL.format(place_id=place_id), headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"  ! Error fetching {place_id}: {resp.status_code} {resp.text[:200]}")
        return None
    result = resp.json()
    return {
        "business_status": result.get("businessStatus", "OPERATIONAL"),
        "name": result.get("displayName", {}).get("text"),
        "address": result.get("formattedAddress"),
        "maps_url": result.get("googleMapsUri"),
    }


def send_webhook(message):
    is_discord = "discord.com" in WEBHOOK_URL or "discordapp.com" in WEBHOOK_URL
    payload = {"content": message} if is_discord else {"text": message}
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    if resp.status_code >= 300:
        print(f"  ! Webhook post failed: {resp.status_code} {resp.text}")


def main():
    stores = load_json(STORES_FILE, [])
    if not stores:
        print(f"{STORES_FILE} is empty or missing. Run discover_stores.py first.")
        return

    state = load_json(STATE_FILE, {})
    changes = []

    for store in stores:
        pid = store["place_id"]
        current = get_status(pid)
        if current is None:
            continue

        prev_status = state.get(pid, {}).get("business_status", "OPERATIONAL")
        new_status = current["business_status"]

        if new_status != prev_status:
            changes.append({
                "name": current["name"] or store.get("name"),
                "address": current["address"] or store.get("address"),
                "from": prev_status,
                "to": new_status,
                "maps_url": current.get("maps_url"),
            })

        state[pid] = current
        time.sleep(0.1)  # be polite to the API

    save_json(STATE_FILE, state)

    if not changes:
        print("No status changes detected.")
        return

    print(f"Detected {len(changes)} status change(s). Posting to webhook...")
    for c in changes:
        emoji = STATUS_EMOJI.get(c["to"], "⚪")
        msg = (
            f"{emoji} **Status change**: {c['name']}\n"
            f"{c['address']}\n"
            f"{c['from']} → {c['to']}"
        )
        if c.get("maps_url"):
            msg += f"\n{c['maps_url']}"
        send_webhook(msg)
        time.sleep(0.5)

    print("Done.")


if __name__ == "__main__":
    main()
