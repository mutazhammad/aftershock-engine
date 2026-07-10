import os, requests, json, time
from datetime import datetime, timezone

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

WATCHLIST = {
    "waterway_block": '("strait of hormuz" OR "suez canal" OR "bab el mandeb") (closed OR blocked OR blockade)',
    "pipeline_block": '("gas pipeline" OR "oil pipeline") (sabotage OR explosion OR ruptured OR attacked)',
    "sanctions":      '("new sanctions" OR "sanctions package" OR embargo) (imposed OR announced)',
    "bombing":        '(airstrike OR airstrikes OR "military strike") (oil OR refinery OR nuclear OR military)',
}

def save_candidate(c):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/candidates",
        params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([c]), timeout=30,
    )
    print(f"  {'saved' if resp.status_code < 300 else 'error '+str(resp.status_code)}: {c['id']}")

for event_type, query in WATCHLIST.items():
    try:
        r = requests.get(GDELT, params={"query": query, "mode": "artlist",
            "format": "json", "maxrecords": 250, "timespan": "2months", "sort": "datedesc"}, timeout=30)
        articles = r.json().get("articles", [])
    except Exception as e:
        print(f"  {event_type}: fetch failed ({e})"); time.sleep(8); continue

    if len(articles) < 5:
        print(f"  {event_type}: {len(articles)} articles, below threshold"); time.sleep(8); continue

    domains = sorted({a.get("domain") for a in articles if a.get("domain")})
    wk = datetime.now(timezone.utc).strftime("%Y%W")
    save_candidate({
        "id": f"{event_type}_{wk}",
        "headline": articles[0].get("title", "").strip(),
        "event_type": event_type,
        "detected_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "coverage_count": len(articles),
        "source_domains": ", ".join(domains[:8]),
        "status": "pending",
    })
    time.sleep(8)

print("Detection complete.")
