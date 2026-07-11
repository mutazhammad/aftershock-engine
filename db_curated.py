import os, requests, json

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

def write_event(record, top):
    row = {**top, "data": record}
    row["id"] = row.pop("event_id")
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/curated_precedents",   # ← curated table
        params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=[row], timeout=30,
    )
    if resp.status_code >= 300:
        print(f"  write error {resp.status_code}: {resp.text[:150]}")
    else:
        print(f"  wrote {row['id']} ({resp.status_code})")
