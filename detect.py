import os, requests, json, time
from datetime import datetime, timezone, timedelta

CURRENTS = "https://api.currentsapi.services/v1/search"
API_KEY = os.environ.get("CURRENTS_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

WATCHLIST = {
    "waterway_block":  "strait closed OR canal blocked OR shipping blockade",
    "pipeline_block":  "pipeline sabotage OR pipeline explosion OR pipeline attacked",
    "sanctions":       "new sanctions OR sanctions package OR export controls",
    "bombing":         "airstrike OR military strike OR missile attack",
    "invasion":        "invasion OR military offensive OR declares war",
    "trade_deal":      "trade deal signed OR trade agreement reached",
    "tariffs":         "new tariffs OR tariff hike OR trade war",
    "opec_supply":     "OPEC production cut OR OPEC output",
    "nuclear":         "nuclear test OR uranium enrichment OR ballistic missile",
    "coup_unrest":     "military coup OR government overthrown OR state of emergency",
}

CONFIRM = {
    "waterway_block": ["clos", "block", "blockad", "seiz", "shut"],
    "pipeline_block": ["sabotag", "explos", "ruptur", "attack", "sever"],
    "sanctions": ["sanction", "embargo", "export control", "blacklist"],
    "bombing": ["strike", "airstrike", "missile", "bomb", "attack"],
    "invasion": ["invas", "invad", "offensive", "war", "troops"],
    "trade_deal": ["deal", "agreement", "sign", "pact", "accord"],
    "tariffs": ["tariff", "duties", "trade war", "levy"],
    "opec_supply": ["opec", "output", "production", "cut"],
    "nuclear": ["nuclear", "uranium", "missile", "enrich"],
    "coup_unrest": ["coup", "overthrow", "takeover", "emergency"],
}

BLOCK_PATTERNS = ["links", "roundup", "daily digest", "newsletter", "opinion"]


def currents_get(keywords):
    start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
    try:
        r = requests.get(CURRENTS, params={
            "keywords": keywords,
            "language": "en",
            "start_date": start,
        }, headers={"Authorization": API_KEY}, timeout=20)
        if r.status_code != 200:
            print(f"    (Currents error {r.status_code})")
            return []
        return r.json().get("news", [])
    except Exception as e:
        print(f"    (fetch failed: {str(e)[:50]})")
        return []


def is_accurate(event_type, articles):
    words = CONFIRM.get(event_type, [])
    hits = sum(1 for a in articles[:20]
               if any(w in (a.get("title", "") or "").lower() for w in words))
    return hits, hits >= 3


def save_candidate(c):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/candidates",
        params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([c]), timeout=30,
    )
    print(f"  {'SAVED' if resp.status_code < 300 else 'error ' + str(resp.status_code)}: {c['id']}")


for event_type, keywords in WATCHLIST.items():
    articles = currents_get(keywords)
    articles = [a for a in articles
                if not any(p in (a.get("title", "") or "").lower() for p in BLOCK_PATTERNS)]

    if len(articles) < 5:
        print(f"  {event_type}: {len(articles)} articles, not significant")
        time.sleep(1)
        continue

    hits, ok = is_accurate(event_type, articles)
    if not ok:
        print(f"  {event_type}: {len(articles)} articles, only {hits} confirm — skipped")
        time.sleep(1)
        continue

    words = CONFIRM.get(event_type, [])
    best = next((a for a in articles if any(w in (a.get("title", "") or "").lower() for w in words)),
                articles[0])
    sources = []
    for a in articles[:8]:
        url = a.get("url", "")
        if url and "/" in url:
            parts = url.split("/")
            if len(parts) > 2:
                sources.append(parts[2])
    wk = datetime.now(timezone.utc).strftime("%Y%W")
    save_candidate({
        "id": f"{event_type}_{wk}",
        "headline": best.get("title", "").strip(),
        "event_type": event_type,
        "detected_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "coverage_count": len(articles),
        "source_domains": ", ".join(sorted(set(sources))[:8]),
        "status": "pending",
    })
    time.sleep(1)

print("Detection complete.")
