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

# --- Your 17 curated events: the AI matches detected events against these ---
CURATED = [
    ("hormuz_2026_03", "Strait of Hormuz closure", "energy supply shock"),
    ("abqaiq_2019", "Abqaiq oil-facility attack", "energy supply shock"),
    ("russia_energy_2022", "Russia energy shock", "energy supply shock"),
    ("iran_israel_2024_04", "Iran-Israel strikes 2024", "energy supply shock"),
    ("opec_cut_2022_10", "OPEC+ production cut 2022", "energy supply shock"),
    ("libya_2011_02", "Libya civil war oil disruption 2011", "energy supply shock"),
    ("ever_given_2021_03", "Ever Given blocks Suez Canal 2021", "shipping disruption"),
    ("red_sea_2023_12", "Red Sea shipping crisis 2023", "shipping disruption"),
    ("chip_controls_2022_10", "US chip export controls on China 2022", "sanctions"),
    ("israel_hamas_2023_10", "Israel-Hamas war onset 2023", "military conflict"),
    ("iran_sanctions_2018_11", "Iran oil sanctions 2018", "sanctions"),
    ("trade_war_2019_05", "US-China trade war escalation 2019", "tariffs"),
    ("nkorea_2017_08", "North Korea nuclear escalation 2017", "nuclear escalation"),
    ("svb_2023_03", "SVB banking crisis 2023", "financial crisis"),
    ("opec_pricewar_2020_03", "OPEC price war / oil crash 2020", "energy supply shock"),
    ("turkey_2018_08", "Turkey currency crisis 2018", "financial crisis"),
    ("brexit_2016_06", "Brexit referendum 2016", "political shock"),
]


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
                                     "description": (a.get("description") or "")[:250]})
            else:
                print(f"  {topic}: Currents error {r.status_code}")
        except Exception as e:
            print(f"  gather failed for {topic}: {str(e)[:40]}")
        time.sleep(1)
    return pool


def ai_analyze(articles):
    listing = "\n".join(f"{i}. {a['title']} — {a['description']}"
                        for i, a in enumerate(articles[:80]))
    curated_list = "\n".join(f"- {cid} | {name} | {etype}" for cid, name, etype in CURATED)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system = (
        "You are a financial-markets analyst building a library of geopolitical precedents. "
        "From recent news, identify SIGNIFICANT market-moving events (wars, strikes on "
        "infrastructure, sanctions, blockades, major trade deals, OPEC decisions, nuclear "
        "escalation, coups, financial crises). Ignore sports, entertainment, local news, "
        "and pure speculation. For each, write transparent analysis and match it to any of "
        "the analyst's existing measured events that it is a meaningful PRECEDENT for "
        "(same mechanism/sector/region). Be honest about date uncertainty."
    )
    user = (
        f"Today is {today}.\n\nRECENT HEADLINES:\n{listing}\n\n"
        f"THE ANALYST'S 17 MEASURED EVENTS (id | name | type):\n{curated_list}\n\n"
        "Return ONLY a JSON array. For each significant event:\n"
        '{"event_type":"waterway_block|pipeline_block|sanctions|sanctions_relief|bombing|'
        'invasion|trade_deal|tariffs|opec_supply|nuclear|coup_unrest|cyberattack|'
        'financial_crisis",'
        ' "headline":"the actual headline",'
        ' "event_date":"YYYY-MM-DD or best estimate",'
        ' "date_explanation":"what the article says about timing and how certain the date '
        'is — be transparent (e.g. explicit date given, inferred from \'last week\', or a '
        'future/expected event)",'
        ' "what_happened":"2-3 sentences on what the article specifically reports",'
        ' "timing_note":"when it happened, or when it is expected to happen",'
        ' "why_significant":"one line on market relevance",'
        ' "matched_events":["curated_id", ...]}  '
        "matched_events = the ids of measured events this is a genuine precedent for "
        "(empty array if none fit). Return only the JSON."
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=4000,
        system=system, messages=[{"role": "user", "content": user}],
    )
    text = msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        print("  AI returned non-JSON:", text[:150])
        return []


def save_pool(p):
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/precedent_pool",
        params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([p]), timeout=30)
    print(f"  {'SAVED' if resp.status_code < 300 else 'error '+str(resp.status_code)}: "
          f"{p['id']} -> {p['matched_events'] or '(no match)'}")


# --- run ---
print("Gathering articles...")
pool = gather_articles()
print(f"  {len(pool)} unique articles")

print("AI analyzing + matching to curated events...")
events = ai_analyze(pool)
print(f"  AI produced {len(events)} events")

wk = datetime.now(timezone.utc).strftime("%Y%W")
for i, e in enumerate(events):
    etype = e.get("event_type", "other")
    matches = e.get("matched_events", [])
    # only keep valid curated ids
    valid_ids = {cid for cid, _, _ in CURATED}
    matches = [m for m in matches if m in valid_ids]
    save_pool({
        "id": f"{etype}_{i}_{wk}",
        "headline": e.get("headline", "").strip(),
        "event_type": etype,
        "event_date": e.get("event_date", ""),
        "date_explanation": e.get("date_explanation", "")[:500],
        "what_happened": e.get("what_happened", "")[:600],
        "timing_note": e.get("timing_note", "")[:300],
        "why_significant": e.get("why_significant", "")[:300],
        "matched_events": ", ".join(matches),
    })

print("Detection complete.")
