import os, re, requests, json, time
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic
from engine import run

CURRENTS = "https://api.currentsapi.services/v1/search"
CURRENTS_KEY = os.environ.get("CURRENTS_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
AUTH = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
client = Anthropic()

DISCLAIMER = "This tool informs your decision. It does not give investment advice."
TOPICS = ["geopolitical conflict", "sanctions", "military strike", "oil energy crisis",
          "trade war tariffs", "invasion war", "OPEC oil", "nuclear missile"]

# ---------- baskets ----------
ENERGY = {"Oil tanker operators": ["STNG", "FRO", "INSW"],
          "Oil & gas producers": ["XOM", "CVX", "COP"],
          "Defense contractors": ["LMT", "RTX", "NOC"],
          "Gold": ["GLD"], "Airline stocks": ["DAL", "UAL", "AAL"]}
SHIPPING = {"Container liners": ["ZIM", "MATX"], "Air freight": ["FDX", "UPS"],
            "Oil & gas producers": ["XOM", "CVX"], "Retailers": ["WMT", "TGT"]}
TRADE = {"Industrials": ["CAT", "DE", "BA"], "Semiconductors": ["NVDA", "AMD", "INTC"],
         "Retailers": ["WMT", "TGT"], "Broad market": ["SPY"]}
SAFE = {"Gold": ["GLD"], "Treasuries": ["TLT"], "Defense": ["LMT", "RTX", "NOC"],
        "Broad market": ["SPY"]}
BANKS = {"Regional banks": ["KRE"], "Large banks": ["JPM", "BAC"],
         "Gold": ["GLD"], "Broad market": ["SPY"]}

TYPE_CONFIG = {
    "waterway_block":   {"basket": SHIPPING, "expect": {"Container liners": "up"}},
    "pipeline_block":   {"basket": ENERGY,   "expect": {"Oil & gas producers": "up"}},
    "bombing":          {"basket": ENERGY,   "expect": {"Defense contractors": "up"}},
    "invasion":         {"basket": ENERGY,   "expect": {"Defense contractors": "up"}},
    "sanctions":        {"basket": ENERGY,   "expect": {}},
    "sanctions_relief": {"basket": ENERGY,   "expect": {}},
    "opec_supply":      {"basket": ENERGY,   "expect": {"Oil & gas producers": "up"}},
    "tariffs":          {"basket": TRADE,    "expect": {}},
    "trade_deal":       {"basket": TRADE,    "expect": {}},
    "nuclear":          {"basket": SAFE,     "expect": {"Gold": "up"}},
    "coup_unrest":      {"basket": SAFE,     "expect": {}},
    "cyberattack":      {"basket": SAFE,     "expect": {}},
    "financial_crisis": {"basket": BANKS,    "expect": {}},
}

TICKER_START = {"STNG": 2010, "FRO": 2001, "INSW": 2017, "XOM": 1990, "CVX": 1990,
    "COP": 2002, "LMT": 1995, "RTX": 1990, "NOC": 1990, "GLD": 2005, "DAL": 2007,
    "UAL": 2006, "AAL": 2013, "ZIM": 2021, "MATX": 2012, "FDX": 1990, "UPS": 1999,
    "WMT": 1990, "TGT": 1990, "CAT": 1990, "DE": 1990, "BA": 1990, "NVDA": 1999,
    "AMD": 1990, "INTC": 1990, "SPY": 1993, "TLT": 2002, "KRE": 2006, "JPM": 1990,
    "BAC": 1990}


# ---------- cache ----------
def cache_get(pid):
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/curated_precedents",
            params={"id": f"eq.{pid}", "select": "id,name,information_date,data"},
            headers=AUTH, timeout=30)
        rows = r.json() if r.status_code == 200 else []
        return rows[0] if rows else None
    except Exception:
        return None


def cache_put(record, top):
    row = {**top, "data": record}
    row["id"] = row.pop("event_id")
    requests.post(f"{SUPABASE_URL}/rest/v1/curated_precedents",
        params={"on_conflict": "id"},
        headers={**AUTH, "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([row]), timeout=30)


# ---------- news ----------
def gather_articles():
    seen, pool = set(), []
    for topic in TOPICS:
        try:
            r = requests.get(CURRENTS, params={"keywords": topic, "language": "en"},
                             headers={"Authorization": CURRENTS_KEY}, timeout=20)
            if r.status_code == 200:
                for a in r.json().get("news", []):
                    t = (a.get("title") or "").strip()
                    if t and t not in seen:
                        seen.add(t)
                        pool.append({"title": t, "description": (a.get("description") or "")[:250]})
        except Exception as e:
            print(f"  gather failed for {topic}: {str(e)[:40]}")
        time.sleep(1)
    return pool


def ai_find_events(articles):
    listing = "\n".join(f"{i}. {a['title']} — {a['description']}"
                        for i, a in enumerate(articles[:80]))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system = ("You are a financial-markets analyst. Identify SIGNIFICANT market-moving "
              "geopolitical events from recent news. Ignore sports, entertainment, local "
              "news, opinion, and speculation. Be transparent about date uncertainty.")
    user = (f"Today is {today}.\n\nHEADLINES:\n{listing}\n\n"
        "Return ONLY a JSON array of significant events:\n"
        '{"event_type":"waterway_block|pipeline_block|sanctions|sanctions_relief|bombing|'
        'invasion|trade_deal|tariffs|opec_supply|nuclear|coup_unrest|cyberattack|financial_crisis",'
        ' "headline":"actual headline", "event_date":"YYYY-MM-DD",'
        ' "date_explanation":"what the article says about timing and how certain",'
        ' "what_happened":"2-3 sentences on what is reported",'
        ' "timing_note":"when it happened or is expected",'
        ' "why_significant":"one line on market relevance"}  Only JSON.')
    msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=4000,
                                 system=system, messages=[{"role": "user", "content": user}])
    text = msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        print("  AI returned non-JSON:", text[:150]); return []


# ---------- per-event precedent research ----------
def ai_research_precedents(event):
    """For THIS specific breaking event, find the closest historical precedents."""
    system = (
        "You are a financial-markets historian. Given a current event, identify the "
        "closest HISTORICAL PRECEDENTS — past events with the same market mechanism. "
        "ACCURACY IS PARAMOUNT. For each, give the INFORMATION DATE (the first trading "
        "day markets could have known) and rate your confidence honestly: 'high' only if "
        "certain of the specific day. Only propose events from 2005 onward. Do not guess."
    )
    user = (
        f"CURRENT EVENT:\n"
        f"Headline: {event.get('headline','')}\n"
        f"Type: {event.get('event_type','')}\n"
        f"What happened: {event.get('what_happened','')}\n\n"
        "Identify up to 5 of the closest historical precedents. Return ONLY JSON:\n"
        '[{"id":"snake_case_id_with_year", "name":"Event name",'
        ' "information_date":"YYYY-MM-DD", "date_confidence":"high|medium|low",'
        ' "date_reasoning":"why this is the information date",'
        ' "why_relevant":"why this is a precedent for the current event",'
        ' "region":"region"}]  Only JSON.'
    )
    msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=2000,
                                 system=system, messages=[{"role": "user", "content": user}])
    text = msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        return []


def era_safe(basket, year):
    out = {}
    for sector, tickers in basket.items():
        keep = [t for t in tickers if TICKER_START.get(t, 1990) <= year]
        if keep:
            out[sector] = keep
    return out


def plausible(record, expect):
    moves = {r["sector"]: r["tone"] for r in record.get("reaction", [])}
    if not expect:
        return True, "no directional expectation"
    m = sum(1 for s, d in expect.items()
            if moves.get(s) == ("gain" if d == "up" else "loss"))
    return m >= 1, f"{m}/{len(expect)} expected moves matched"


def has_signal(record):
    moves = []
    for r in record.get("reaction", []):
        try:
            moves.append(abs(float(str(r["pct"]).replace("%", "").replace("+", ""))))
        except Exception:
            pass
    if not moves:
        return False, "no measurable reaction"
    b = max(moves)
    return (b >= 2.0), (f"largest move {b:.1f}%" if b >= 2.0
                        else f"largest move only {b:.1f}% — likely a non-event")


def measure_precedent(p, etype):
    """Measure one AI-proposed precedent. Returns the stored row, or None if rejected."""
    pid = p.get("id", "").strip()
    date = p.get("information_date", "")
    conf = p.get("date_confidence", "low")

    if not pid or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        return None, "bad id/date"
    if conf != "high":
        return None, f"date confidence '{conf}'"

    cached = cache_get(pid)
    if cached and (cached.get("data") or {}).get("reaction"):
        return cached, "cached"

    ev = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if ev.year < 2005:
        return None, f"{ev.year} — pre-2005 unreliable"
    if (datetime.now(timezone.utc) - ev).days < 60:
        return None, "too recent for a full window"

    cfg = TYPE_CONFIG.get(etype, {"basket": ENERGY, "expect": {}})
    basket = era_safe(cfg["basket"], ev.year)
    if len(basket) < 2:
        return None, f"too few tickers existed in {ev.year}"

    EVENT = {"event_id": pid, "name": p.get("name", ""), "type_label": etype,
             "information_date": date, "announcement_date": date, "benchmark": "^GSPC",
             "download_start": (ev - timedelta(days=280)).strftime("%Y-%m-%d"),
             "download_end": (ev + timedelta(days=60)).strftime("%Y-%m-%d"),
             "snap_window": (-2, 5), "full_window": (-5, 30), "region": p.get("region", "")}
    NARRATIVE = {"sources": [], "status": "confirmed", "recency": "settled",
                 "summary": p.get("why_relevant", ""), "key_metrics": [], "timeline": [],
                 "markers": [], "historical": [], "historical_precedents": [],
                 "companies_in_news": [], "lasting_finding": "",
                 "confidence": f"Date: {p.get('date_reasoning','')}"}
    try:
        record, top = run(EVENT, basket, {}, NARRATIVE)
    except Exception as e:
        return None, f"measurement failed ({str(e)[:40]})"

    ok, why = plausible(record, cfg["expect"])
    if not ok:
        return None, f"implausible — {why}"
    sig_ok, sig_why = has_signal(record)
    if not sig_ok:
        return None, sig_why

    record["why_relevant"] = p.get("why_relevant", "")
    record["date_reasoning"] = p.get("date_reasoning", "")
    record["validation"] = {"plausibility": why, "signal": sig_why, "date_confidence": conf}
    cache_put(record, dict(top))
    return {"id": pid, "name": p.get("name", ""), "information_date": date,
            "data": record}, f"measured ({why})"


def build_expectation(prec_rows):
    if not prec_rows:
        return None
    sector_moves, vix_changes, vol_ratios, used = {}, [], [], []
    for p in prec_rows:
        d = p.get("data") or {}
        used.append({"id": p["id"], "name": p.get("name", ""),
                     "date": str(p.get("information_date", ""))[:10],
                     "why_relevant": d.get("why_relevant", "")})
        for r in d.get("reaction", []):
            try:
                pct = float(str(r["pct"]).replace("%", "").replace("+", ""))
            except Exception:
                continue
            sector_moves.setdefault(r["sector"], []).append((pct, bool(r.get("significant"))))
        vol = d.get("volatility") or {}
        vix = vol.get("vix")
        if vix and vix.get("change_pct"):
            try:
                vix_changes.append(float(str(vix["change_pct"]).replace("%", "").replace("+", "")))
            except Exception:
                pass
        for s in vol.get("sectors", []):
            try:
                vol_ratios.append(float(s["ratio"]))
            except Exception:
                pass

    averages = []
    for sector, entries in sector_moves.items():
        pcts = [e[0] for e in entries]
        n_sig = sum(1 for e in entries if e[1])
        avg = sum(pcts) / len(pcts)
        averages.append({"sector": sector, "avg_move": f"{avg:+.1f}%",
                         "n_events": len(entries), "n_significant": n_sig,
                         "direction": "gain" if avg >= 0 else "loss",
                         "consistency": f"{n_sig} of {len(entries)} were statistically significant"})
    averages.sort(key=lambda x: abs(float(x["avg_move"].replace("%", ""))), reverse=True)

    return {"based_on": used, "sector_averages": averages,
            "avg_vix_change": (f"{sum(vix_changes)/len(vix_changes):+.0f}%" if vix_changes else None),
            "avg_volatility_ratio": (round(sum(vol_ratios)/len(vol_ratios), 2) if vol_ratios else None),
            "caveat": ("These figures are what actually happened in comparable historical events, "
                       "measured from market data. They are NOT a forecast. This event is too "
                       "recent to measure.")}


def publish(cid, e, prec_rows, expectation):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    record = {
        "event": {"name": e.get("headline", "")[:120], "type_label": e.get("event_type", ""),
                  "information_date": e.get("event_date", ""), "announcement_date": "",
                  "key_metrics": []},
        "location": {}, "sources": [], "status": "confirmed", "recency": "breaking",
        "summary": e.get("what_happened", ""),
        "date_explanation": e.get("date_explanation", ""),
        "timing_note": e.get("timing_note", ""),
        "why_significant": e.get("why_significant", ""),
        "db_date": now,
        "timeline": [], "reaction": [], "lasting_finding": "",
        "timeseries": {"days": [], "series": [], "markers": []}, "phases": [],
        "volatility": None,
        "historical": [], "historical_precedents": [],
        "matched_precedents": [p["id"] for p in prec_rows],
        "precedent_expectation": expectation,
        "companies_affected": [], "companies_in_news": [],
        "confidence": ("Breaking event — the market reaction has not happened yet and cannot "
                       "be measured. The precedents below were researched for this specific "
                       "event, measured from real market data, and validated. This analysis "
                       "deepens automatically as data accumulates."),
        "disclaimer": DISCLAIMER,
    }
    top = {"id": cid, "name": e.get("headline", "")[:120], "type_label": e.get("event_type", ""),
           "information_date": e.get("event_date", "") or None, "status": "confirmed",
           "recency": "breaking", "region": ""}
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/events", params={"on_conflict": "id"},
        headers={**AUTH, "Content-Type": "application/json",
                 "Prefer": "resolution=ignore-duplicates,return=minimal"},
        data=json.dumps([{**top, "data": record}]), timeout=30)
    print(f"  {'SAVED' if resp.status_code < 300 else 'error '+str(resp.status_code)}: {cid}"
          f" ({len(prec_rows)} validated precedents)")


# ---------------- run ----------------
print("Gathering articles...")
pool = gather_articles()
print(f"  {len(pool)} unique articles")

print("AI identifying significant events...")
events = ai_find_events(pool)
print(f"  {len(events)} events found\n")

wk = datetime.now(timezone.utc).strftime("%Y%W")
for i, e in enumerate(events):
    etype = e.get("event_type", "other")
    cid = f"{etype}_{i}_{wk}"
    print(f"{cid}: {e.get('headline','')[:55]}")

    print("  researching precedents...")
    proposals = ai_research_precedents(e)
    prec_rows = []
    for p in proposals:
        row, why = measure_precedent(p, etype)
        tag = "OK" if row else "REJECT"
        print(f"    {tag} {p.get('id','?')}: {why}")
        if row:
            prec_rows.append(row)

    expectation = build_expectation(prec_rows)
    publish(cid, e, prec_rows, expectation)

print("\nDetection complete.")
