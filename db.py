import os, requests

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]

def write_event(record, top):
    row = {**top, "data": record}
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/events?on_conflict=id",
        headers={
            "apikey": SUPABASE_SECRET_KEY,
            "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        json=[row],                     # ← wrap in a list
        timeout=30,
    )
    if resp.status_code >= 300:
        print(f"  write error {resp.status_code}: {resp.text[:200]}")
    resp.raise_for_status()
    print(f"  wrote {top['event_id']} ({resp.status_code})")
