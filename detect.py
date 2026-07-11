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
VALID_IDS = {cid for cid, _, _ in CURATED}
DISCLAIMER = "This tool informs your decision. It does not give investment advice."


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
                        pool.append({"title": title, "description": (a.get("description") or "")[:250]})
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
        "You are a financial-markets analyst. From recent news, identify SIGNIFICANT "
        "market-moving geopolitical events. Ignore sports, entertainment, local news, and "
        "pure speculation. For each, write transparent analysis and match it to the "
        "analyst's existing measured events it is a meaningful PRECEDENT for (same "
        "mechanism/sector/region). Be honest about date uncertainty."
    )
    user = (
        f"Today is {today}.\n\nRECENT HEADLINES:\n{listing}\n\n"
        f"THE ANALYST'S 17 MEASURED PRECEDENTS (id | name | type):\n{curated_list}\n\n"
        "Return ONLY a JSON array. Each significant event:\n"
        '{"event_type":"waterway_block|pipeline_block|sanctions|sanctions_relief|bombing|'
        'invasion|trade_deal|tariffs|opec_supply|nuclear|coup_unrest|cyberattack|financial_crisis",'
        ' "headline":"actual headline",'
        ' "event_date":"YYYY-MM-DD or best estimate",'
        ' "date_explanation":"what the article says about timing and how certain — be transparent",'
        ' "what_happened":"2-3 sentences on what the article specifically reports",'
        ' "timing_note":"when it happened or is expected",'
        ' "why_significant":"one line on market relevance",'
        ' "matched_precedents":["curated_id", ...]}  '
        "matched_precedents = ids of measured events this is a genuine precedent for "
        "(empty if none). Return only JSON."
    )
    msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=4000,
        system=system, messages=[{"role": "user", "content": user}])
    text = msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        print("  AI returned non-JSON:", text[:150]); return []


def fetch_precedent_data(ids):
    """Pull the measured records for the matched curated precedents."""
    if not ids:
        return []
    id_list = ",".join(f'"{i}"' for i in ids)
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/curated_precedents",
            params={"id": f"in.({id_list})", "select": "id,name,information_date,data"},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=30)
        return r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"    (precedent fetch failed: {str(e)[:50]})")
        return []


def build_expectation(matched_ids):
    """From the matched precedents' REAL measured data, compute honest historical averages.
    These are what ACTUALLY happened in comparable events — not a forecast."""
    precedents = fetch_precedent_data(matched_ids)
    if not precedents:
        return None

    sector_moves = {}       # sector -> list of (pct, significant)
    vix_changes = []
    vol_ratios = []
    used = []

    for p in precedents:
        d = p.get("data") or {}
        used.append({"id": p.get("id", ""), "name": p.get("name", ""),
                     "date": str(p.get("information_date", ""))[:10]})

        for r in d.get("reaction", []):
            try:
                pct = float(str(r.get("pct", "0")).replace("%", "").replace("+", ""))
            except Exception:
                continue
            sector_moves.setdefault(r.get("sector", "?"), []).append((pct, bool(r.get("significant"))))

        vol = d.get("volatility") or {}
        vix = vol.get("vix")
        if vix and vix.get("change_pct"):
            try:
                vix_changes.append(float(str(vix["change_pct"]).replace("%", "").replace("+", "")))
            except Exception:
                pass
        for s in vol.get("sectors", []):
            if s.get("ratio"):
                try:
                    vol_ratios.append(float(s["ratio"]))
                except Exception:
                    pass

    sector_averages = []
    for sector, entries in sector_moves.items():
        pcts = [e[0] for e in entries]
        n_sig = sum(1 for e in entries if e[1])
        avg = sum(pcts) / len(pcts)
        sector_averages.append({
            "sector": sector,
            "avg_move": f"{avg:+.1f}%",
            "n_events": len(entries),
            "n_significant": n_sig,
            "direction": "gain" if avg >= 0 else "loss",
            "consistency": f"{n_sig} of {len(entries)} were statistically significant",
        })
    sector_averages.sort(key=lambda x: abs(float(x["avg_move"].replace("%", ""))), reverse=True)

    return {
        "based_on": used,
        "sector_averages": sector_averages,
        "avg_vix_change": (f"{sum(vix_changes)/len(vix_changes):+.0f}%" if vix_changes else None),
        "avg_volatility_ratio": (round(sum(vol_ratios) / len(vol_ratios), 2) if vol_ratios else None),
        "caveat": ("These figures are what actually happened in comparable historical events, "
                   "measured from market data. They are NOT a forecast of what will happen now. "
                   "This event is too recent to measure."),
    }


def publish_feed_event(cid, e, matches):
    """Write a detected event to the FEED as breaking, with precedents + historical expectation."""
    expectation = build_expectation(matches)

    record = {
        "event": {"name": e.get("headline", "")[:120], "type_label": e.get("event_type", ""),
                  "information_date": e.get("event_date", ""), "announcement_date": "",
                  "key_metrics": []},
        "location": {}, "sources": [], "status": "confirmed", "recency": "breaking",
        "summary": e.get("what_happened", ""),
        "date_explanation": e.get("date_explanation", ""),
        "timing_note": e.get("timing_note", ""),
        "why_significant": e.get("why_significant", ""),
        "timeline": [], "reaction": [], "lasting_finding": "",
        "timeseries": {"days": [], "series": [], "markers": []}, "phases": [],
        "volatility": None,                          # not measurable yet — honest
        "historical": [], "historical_precedents": [],
        "matched_precedents": matches,
        "precedent_expectation": expectation,        # ← the analytical depth
        "companies_affected": [], "companies_in_news": [],
        "confidence": ("Breaking event — the market reaction has not happened yet and cannot be "
                       "measured. The historical precedents below show what actually occurred in "
                       "comparable past events."),
        "disclaimer": DISCLAIMER,
    }
    top = {"id": cid, "name": e.get("headline", "")[:120], "type_label": e.get("event_type", ""),
           "information_date": e.get("event_date", "") or None, "status": "confirmed",
           "recency": "breaking", "region": ""}
    row = {**top, "data": record}

    resp = requests.post(f"{SUPABASE_URL}/rest/v1/events", params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([row]), timeout=30)

    n_prec = len(expectation["based_on"]) if expectation else 0
    status = "SAVED" if resp.status_code < 300 else f"error {resp.status_code}"
    print(f"  {status}: {cid} -> {n_prec} precedents, "
          f"expectation {'✓' if expectation else '✗'}")
    if resp.status_code >= 300:
        print(f"    {resp.text[:150]}")


# --- run ---
print("Gathering articles...")
pool = gather_articles()
print(f"  {len(pool)} unique articles")

print("AI analyzing + matching precedents...")
events = ai_analyze(pool)
print(f"  AI produced {len(events)} events")

wk = datetime.now(timezone.utc).strftime("%Y%W")
for i, e in enumerate(events):
    etype = e.get("event_type", "other")
    matches = [m for m in e.get("matched_precedents", []) if m in VALID_IDS]
    publish_feed_event(f"{etype}_{i}_{wk}", e, matches)

print("Detection complete.")
