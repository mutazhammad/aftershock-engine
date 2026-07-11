import os, re, json, requests
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic
from engine import run   # your existing engine

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
client = Anthropic()

# --- RULE: event_type -> basket name + expected sector directions ---
TYPE_CONFIG = {
    "bombing":         {"basket": "energy", "expect": {"Oil & gas producers": "up", "Defense contractors": "up"}},
    "waterway_block":  {"basket": "energy", "expect": {"Oil tanker operators": "up", "Oil & gas producers": "up"}},
    "pipeline_block":  {"basket": "energy", "expect": {"Oil & gas producers": "up"}},
    "sanctions":       {"basket": "energy", "expect": {"Oil & gas producers": "up"}},
    "sanctions_relief":{"basket": "energy", "expect": {}},
    "invasion":        {"basket": "energy", "expect": {"Defense contractors": "up", "Gold": "up"}},
    "opec_supply":     {"basket": "energy", "expect": {"Oil & gas producers": "up"}},
    "tariffs":         {"basket": "trade",  "expect": {}},
    "trade_deal":      {"basket": "trade",  "expect": {}},
    "nuclear":         {"basket": "safe_haven", "expect": {"Gold": "up"}},
    "coup_unrest":     {"basket": "safe_haven", "expect": {}},
    "cyberattack":     {"basket": "safe_haven", "expect": {}},
    "financial_crisis":{"basket": "safe_haven", "expect": {"Gold": "up"}},
}

ENERGY_BASKET = {
    "Oil tanker operators": ["STNG", "FRO", "INSW"],
    "Oil & gas producers":  ["XOM", "CVX", "COP"],
    "Defense contractors":  ["LMT", "RTX", "NOC"],
    "Gold":                 ["GLD"],
    "Airline stocks":       ["DAL", "UAL", "AAL"],
}
TRADE_BASKET = {
    "Industrials":    ["CAT", "DE", "BA"],
    "Semiconductors": ["NVDA", "AMD", "INTC"],
    "Retailers":      ["WMT", "TGT"],
    "Broad market":   ["SPY"],
}
SAFE_HAVEN_BASKET = {
    "Gold":         ["GLD"],
    "Treasuries":   ["TLT"],
    "Defense":      ["LMT", "RTX", "NOC"],
    "Broad market": ["SPY"],
}
BASKETS_BY_NAME = {
    "energy": ENERGY_BASKET,
    "trade": TRADE_BASKET,
    "safe_haven": SAFE_HAVEN_BASKET,
}

DISCLAIMER = "This tool informs your decision. It does not give investment advice."


def resolve_date_with_ai(headline, why):
    """Fallback: AI resolves the information date if detection didn't supply one."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=100,
            system=("You determine the INFORMATION DATE of a market event — the first trading "
                    "day markets could realistically have known about it. Return ONLY that date "
                    "as YYYY-MM-DD."),
            messages=[{"role": "user", "content":
                f"Today is {today}. Event: {headline}. Context: {why}. "
                "What is the information date (YYYY-MM-DD)? Return only the date."}],
        )
        text = msg.content[0].text.strip()
    except Exception as e:
        print(f"    (AI date call failed: {str(e)[:50]})")
        return None
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return m.group(0) if m else None


def plausibility_ok(record, expect):
    """RULE: did the expected sectors move in the expected direction?"""
    moves = {r["sector"]: r["tone"] for r in record.get("reaction", [])}
    if not expect:
        return True, "no directional expectation"
    matched = sum(1 for sec, direction in expect.items()
                  if moves.get(sec) == ("gain" if direction == "up" else "loss"))
    ok = matched >= max(1, len(expect) // 2)
    return ok, f"{matched}/{len(expect)} expected moves matched"


def get_pending():
    r = requests.get(f"{SUPABASE_URL}/rest/v1/candidates",
        params={"status": "eq.pending", "select": "*"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}, timeout=30)
    return r.json() if r.status_code == 200 else []


def mark_candidate(cid, status, note=""):
    requests.patch(f"{SUPABASE_URL}/rest/v1/candidates",
        params={"id": f"eq.{cid}"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json"},
        data=json.dumps({"status": status, "source_domains": note[:200]}), timeout=30)


def publish_event(record, top):
    row = {**top, "data": record}
    row["id"] = row.pop("event_id")
    requests.post(f"{SUPABASE_URL}/rest/v1/events", params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([row]), timeout=30)


def publish_breaking(cid, headline, etype, date, why, days_since):
    """Publish a recent event as 'breaking' — all context, no measured reaction yet."""
    record = {
        "event": {"name": headline[:80], "type_label": etype,
                  "information_date": date, "announcement_date": date, "key_metrics": []},
        "location": {}, "sources": [], "status": "confirmed", "recency": "breaking",
        "summary": headline,
        "timeline": [], "reaction": [], "lasting_finding": "",
        "timeseries": {"days": [], "series": [], "markers": []},
        "phases": [], "historical": [], "historical_precedents": [],
        "companies_affected": [], "companies_in_news": [],
        "confidence": why, "disclaimer": DISCLAIMER,
    }
    top = {"event_id": cid, "name": headline[:80], "type_label": etype,
           "information_date": date, "status": "confirmed", "recency": "breaking", "region": ""}
    publish_event(record, top)
    mark_candidate(cid, "published", f"breaking — {days_since}d old, reaction pending")
    print(f"  PUBLISHED (breaking, {days_since}d old — no reaction yet)")


# --- run the verifier ---
for c in get_pending():
    cid, etype, headline = c["id"], c["event_type"], c["headline"]
    why = c.get("source_domains", "")
    print(f"\nVerifying {cid}: {headline[:50]}")

    cfg = TYPE_CONFIG.get(etype)
    if not cfg:
        mark_candidate(cid, "rejected", f"no config for type {etype}")
        print(f"  REJECTED: unsupported type {etype}"); continue

    # 1. use detection's date first; only ask AI if missing/invalid
    date = c.get("detected_date")
    if not date or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        date = resolve_date_with_ai(headline, why)
    if not date:
        mark_candidate(cid, "held", "could not resolve date")
        print("  HELD: date unresolved"); continue
    date = str(date)[:10]
    print(f"  date: {date}")

    # timezone-aware date math
    try:
        ev_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        mark_candidate(cid, "held", "date parse failed")
        print("  HELD: bad date format"); continue
    today_dt = datetime.now(timezone.utc)
    days_since = (today_dt - ev_date).days

    # 2. TOO RECENT (< 10 days) -> publish as breaking, no measured reaction
    if days_since < 10:
        publish_breaking(cid, headline, etype, date, why, days_since)
        continue

    # 3. old enough to measure -> pick basket
    basket = BASKETS_BY_NAME.get(cfg["basket"])
    if not basket:
        mark_candidate(cid, "held", f"no basket for {cfg['basket']}")
        print(f"  HELD: basket {cfg['basket']} not built"); continue

    # download window relative to the event date
    dl_start = (ev_date - timedelta(days=250)).strftime("%Y-%m-%d")
    dl_end_dt = ev_date + timedelta(days=45)
    if dl_end_dt > today_dt:
        dl_end_dt = today_dt
    dl_end = dl_end_dt.strftime("%Y-%m-%d")

    # partial (10-30 days) = developing; full window elapsed = settled
    recency = "developing" if days_since < 35 else "settled"

    EVENT = {"event_id": cid, "name": headline[:80], "type_label": etype,
             "information_date": date, "announcement_date": date, "benchmark": "^GSPC",
             "download_start": dl_start, "download_end": dl_end,
             "snap_window": (-2, 5), "full_window": (-5, 30), "region": ""}
    NARRATIVE = {"sources": [], "status": "confirmed", "recency": recency,
                 "summary": headline, "lasting_finding": "", "key_metrics": [],
                 "timeline": [], "markers": [], "historical": [], "historical_precedents": [],
                 "companies_in_news": [], "confidence": why}

    # 4. measure
    try:
        record, top = run(EVENT, basket, {}, NARRATIVE)
    except Exception as e:
        # measurement failed (often too little post-event data) -> fall back to breaking
        print(f"  measurement failed ({str(e)[:50]}) — publishing as breaking")
        publish_breaking(cid, headline, etype, date, why, days_since)
        continue

    # 5. plausibility gate
    ok, reason = plausibility_ok(record, cfg["expect"])
    if not ok:
        mark_candidate(cid, "held", f"implausible: {reason}")
        print(f"  HELD: {reason}"); continue

    # 6. PASS -> publish (developing or settled)
    publish_event(record, top)
    mark_candidate(cid, "published", f"{recency} — verified: {reason}")
    print(f"  PUBLISHED ✓ ({recency}, {reason})")

print("\nVerification complete.")
