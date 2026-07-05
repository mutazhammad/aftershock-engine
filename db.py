import os, requests

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

def write_event(record, top):
    row = {**top, "data": record}
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/events?on_conflict=id",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        json=row, timeout=30,
    )
    resp.raise_for_status()
    print(f"  wrote {top['event_id']} ({resp.status_code})")
