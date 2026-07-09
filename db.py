import os, requests, json

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

print(f"DEBUG key length: {len(SUPABASE_KEY) if SUPABASE_KEY else 'EMPTY'}")

def write_event(record, top):
    row = {**top, "data": record}
    url = f"{SUPABASE_URL}/rest/v1/events"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    resp = requests.post(
        url, params={"on_conflict": "id"},
        headers=headers, data=json.dumps([row]), timeout=30,
    )
    if resp.status_code >= 300:
        print(f"  write error {resp.status_code}: {resp.text[:300]}")
    else:
        print(f"  wrote {top['event_id']} ({resp.status_code})")
