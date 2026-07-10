import os, requests, json, time
from datetime import datetime, timezone
from anthropic import Anthropic

CURRENTS = "https://api.currentsapi.services/v1/search"
CURRENTS_KEY = os.environ.get("CURRENTS_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
client = Anthropic()

TOPICS = ["geopolitical conflict", "sanctions", "military strike", "oil energy crisis",
          "trade war tariffs", "invasion war", "OPEC oil", "nuclear missile"]


def gather_articles():
    seen, pool = set(), []
    for topic in TOPICS:
        try:
            r = requests.get(CURRENTS, params={"keywords": topic, "language": "en"},
                             headers={"Authorization": CURRENTS_KEY}, timeout=20)
            if r.status_code == 200:
                for a in r.json().get("news", []):
                    title = (a.get("title") or "").strip()
                    if title and title not in seen:
                        seen.add(title)
                        pool.append({"title": title,
                                     "description": (a.get("description") or "")[:200]})
        except Exception as e:
            print(f"  gather failed for {topic}: {str(e)[:40]}")
        time.sleep(1)
    return pool


def ai_pick_events(articles):
    listing = "\n".join(f"{i}. {a['title']} — {a['description']}"
                        for i, a in enumerate(articles[:80]))
    system = (
        "You are a financial-markets analyst. From news headlines, identify the most "
        "SIGNIFICANT geopolitical events likely to move financial markets (wars, strikes "
        "on infrastructure, sanctions, blockades, major trade deals, OPEC decisions, "
        "nuclear escalation, coups). IGNORE sports, entertainment, local news, opinion, "
        "and non-market news. Only REAL events that actually happened."
    )
    user = (
        f"Recent headlines:\n\n{listing}\n\n"
        "Return ONLY a JSON array of up to 6 most significant market-moving events, each: "
        '{"event_type":"one of: waterway_block, pipeline_block, sanctions, sanctions_relief, '
        'bombing, invasion, trade_deal, tariffs, opec_supply, nuclear, coup_unrest, '
        'cyberattack, financial_crisis", "headline":"actual headline", '
        '"why_significant":"one line"}. If none qualify, return []. Only the JSON.'
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1500,
        system=system, messages=[{"role": "user", "content": user}],
    )
    text = msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        print("  AI returned non-JSON:", text[:150])
        return []


def save_candidate(c):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/candidates",
        params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([c]), timeout=30,
    )
    print(f"  {'SAVED' if resp.status_code < 300 else 'error '+str(resp.status_code)}: {c['id']}")


print("Gathering articles...")
pool = gather_articles()
print(f"  {len(pool)} unique articles")

print("AI selecting significant events...")
events = ai_pick_events(pool)
print(f"  AI identified {len(events)} events")

wk = datetime.now(timezone.utc).strftime("%Y%W")
for i, e in enumerate(events):
    etype = e.get("event_type", "other")
    save_candidate({
        "id": f"{etype}_{i}_{wk}",
        "headline": e.get("headline", "").strip(),
        "event_type": etype,
        "detected_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "coverage_count": 0,
        "source_domains": e.get("why_significant", "")[:200],
        "status": "pending",
    })

print("Detection complete.")
