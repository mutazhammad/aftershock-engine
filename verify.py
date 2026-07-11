import os, requests, json
from datetime import datetime, timezone
from anthropic import Anthropic
from engine import run   # your existing engine

CURRENTS = "https://api.currentsapi.services/v1/search"
CURRENTS_KEY = os.environ.get("CURRENTS_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
client = Anthropic()

# --- RULE 1: event_type -> basket + expected direction ---
TYPE_CONFIG = {
    "bombing":        {"basket": "energy", "expect": {"Oil & gas producers": "up", "Defense contractors": "up"}},
    "waterway_block": {"basket": "energy", "expect": {"Oil tanker operators": "up", "Oil & gas producers": "up"}},
    "sanctions":      {"basket": "energy", "expect": {"Oil & gas producers": "up"}},
    "invasion":       {"basket": "energy", "expect": {"Defense contractors": "up", "Gold": "up"}},
    "opec_supply":    {"basket": "energy", "expect": {"Oil & gas producers": "up"}},
    "tariffs":        {"basket": "trade",  "expect": {}},
    "trade_deal":     {"basket": "trade",  "expect": {}},
    "nuclear":        {"basket": "safe_haven", "expect": {"Gold": "up"}},
}

ENERGY_BASKET = {
    "Oil tanker operators": ["STNG", "FRO", "INSW"],
    "Oil & gas producers":  ["XOM", "CVX", "COP"],
    "Defense contractors":  ["LMT", "RTX", "NOC"],
    "Gold":                 ["GLD"],
    "Airline stocks":       ["DAL", "UAL", "AAL"],
}
BASKETS_BY_NAME = {"energy": ENERGY_BASKET}  # add trade/safe_haven later


def resolve_date_with_ai(headline, why):
    """AI reads the event and returns the market-relevant information date."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=100,
        system=("You determine the INFORMATION DATE of a market event — the first trading "
                "day markets could realistically have known about it. Return ONLY that date "
                "as YYYY-MM-DD, nothing else."),
        messages=[{"role": "user", "content":
            f"Today is {today}. Event: {headline}. Context: {why}. "
            "What is the information date (YYYY-MM-DD)? Return only the date."}],
    )
    text = msg.content[0].text.strip()
    # pull the first YYYY-MM-DD pattern out of whatever the AI said
    import re
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if m:
        return m.group(0)
    return None


def plausibility_ok(record, expect):
    """RULE: did the expected sectors move in the expected direction?"""
    moves = {r["sector"]: r["tone"] for r in record.get("reaction", [])}
    if not expect:
        return True, "no directional expectation (trade-type)"
    matched = sum(1 for sec, direction in expect.items()
                  if moves.get(sec) == ("gain" if direction == "up" else "loss"))
    ok = matched >= max(1, len(expect) // 2)   # at least half the expected moves match
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


# --- run the verifier ---
for c in get_pending():
    cid, etype, headline = c["id"], c["event_type"], c["headline"]
    print(f"\nVerifying {cid}: {headline[:50]}")

    cfg = TYPE_CONFIG.get(etype)
    if not cfg:
        mark_candidate(cid, "rejected", f"no config for type {etype}")
        print(f"  REJECTED: unsupported type {etype}"); continue

    # 1. AI resolves date
    date = resolve_date_with_ai(headline, c.get("source_domains", ""))
    if not date:
        mark_candidate(cid, "held", "could not resolve date")
        print("  HELD: date unresolved"); continue
    print(f"  date resolved: {date}")

    # 2. rules pick basket; 3. engine measures
    basket = BASKETS_BY_NAME.get(cfg["basket"])
    if not basket:
        mark_candidate(cid, "held", f"no basket for {cfg['basket']}")
        print(f"  HELD: basket {cfg['basket']} not built yet"); continue

    EVENT = {"event_id": cid, "name": headline[:80], "type_label": etype,
             "information_date": date, "announcement_date": date, "benchmark": "^GSPC",
             "download_start": "2024-01-01", "download_end": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
             "snap_window": (-2, 5), "full_window": (-5, 30), "region": ""}
    NARRATIVE = {"sources": [], "status": "confirmed", "recency": "settled",
                 "summary": headline, "lasting_finding": "", "key_metrics": [],
                 "timeline": [], "markers": [], "historical": [], "historical_precedents": [],
                 "companies_in_news": [], "confidence": c.get("source_domains", "")}
    try:
        record, top = run(EVENT, basket, {}, NARRATIVE)
    except Exception as e:
        mark_candidate(cid, "held", f"measurement failed: {str(e)[:80]}")
        print(f"  HELD: measurement error {str(e)[:60]}"); continue

    # 4. plausibility gate
    ok, reason = plausibility_ok(record, cfg["expect"])
    if not ok:
        mark_candidate(cid, "held", f"implausible: {reason}")
        print(f"  HELD: {reason}"); continue

    # 5. PASS -> publish
    publish_event(record, top)
    mark_candidate(cid, "published", f"verified: {reason}")
    print(f"  PUBLISHED ✓ ({reason})")

print("\nVerification complete.")
