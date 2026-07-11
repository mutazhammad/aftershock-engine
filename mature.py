import os, json, requests
from datetime import datetime, timezone, timedelta
from engine import run

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
           "Content-Type": "application/json"}

# event_type -> basket
ENERGY = {"Oil tanker operators": ["STNG", "FRO", "INSW"],
          "Oil & gas producers": ["XOM", "CVX", "COP"],
          "Defense contractors": ["LMT", "RTX", "NOC"],
          "Gold": ["GLD"], "Airline stocks": ["DAL", "UAL", "AAL"]}
TRADE = {"Industrials": ["CAT", "DE", "BA"], "Semiconductors": ["NVDA", "AMD", "INTC"],
         "Retailers": ["WMT", "TGT"], "Broad market": ["SPY"]}
SAFE = {"Gold": ["GLD"], "Treasuries": ["TLT"], "Defense": ["LMT", "RTX", "NOC"],
        "Broad market": ["SPY"]}

TYPE_BASKET = {
    "bombing": ENERGY, "waterway_block": ENERGY, "pipeline_block": ENERGY,
    "sanctions": ENERGY, "sanctions_relief": ENERGY, "invasion": ENERGY,
    "opec_supply": ENERGY, "tariffs": TRADE, "trade_deal": TRADE,
    "nuclear": SAFE, "coup_unrest": SAFE, "cyberattack": SAFE, "financial_crisis": SAFE,
}


def get_feed_events():
    r = requests.get(f"{SUPABASE_URL}/rest/v1/events",
        params={"select": "id,name,type_label,information_date,recency,data"},
        headers=HEADERS, timeout=30)
    return r.json() if r.status_code == 200 else []


def upgrade_event(ev, record, top):
    row = {**top, "data": record}
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/events", params={"on_conflict": "id"},
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([row]), timeout=30)
    return resp.status_code < 300


today = datetime.now(timezone.utc)

for ev in get_feed_events():
    eid = ev["id"]
    data = ev.get("data") or {}
    etype = ev.get("type_label", "")
    date = ev.get("information_date")

    if not date:
        print(f"  {eid}: no date, skipped"); continue

    ev_date = datetime.strptime(str(date)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    days_since = (today - ev_date).days

    if days_since < 10:
        print(f"  {eid}: {days_since}d — still breaking"); continue

    target = "developing" if days_since < 35 else "settled"
    if ev.get("recency") == target and data.get("reaction"):
        print(f"  {eid}: already {target}"); continue      # nothing to do

    basket = TYPE_BASKET.get(etype)
    if not basket:
        print(f"  {eid}: no basket for type {etype}"); continue

    dl_start = (ev_date - timedelta(days=250)).strftime("%Y-%m-%d")
    dl_end_dt = min(ev_date + timedelta(days=45), today)
    EVENT = {"event_id": eid, "name": ev.get("name", "")[:120], "type_label": etype,
             "information_date": str(date)[:10], "announcement_date": str(date)[:10],
             "benchmark": "^GSPC", "download_start": dl_start,
             "download_end": dl_end_dt.strftime("%Y-%m-%d"),
             "snap_window": (-2, 5), "full_window": (-5, 30),
             "region": ev.get("region", "")}

    # PRESERVE all the original context written at detection
    NARRATIVE = {
        "sources": data.get("sources", []), "status": "confirmed", "recency": target,
        "summary": data.get("summary", ""), "key_metrics": [],
        "timeline": data.get("timeline", []), "markers": data.get("markers", []),
        "historical": data.get("historical", []),
        "historical_precedents": data.get("historical_precedents", []),
        "companies_in_news": data.get("companies_in_news", []),
        "lasting_finding": "",
        "confidence": (f"Measured {days_since} days after the event. "
                       + ("Full window complete." if target == "settled"
                          else "Reaction still developing; the full window is not yet complete.")),
    }

    try:
        record, top = run(EVENT, basket, {}, NARRATIVE)
    except Exception as e:
        print(f"  {eid}: measurement failed ({str(e)[:50]}) — staying breaking"); continue

    # carry forward the detection-time context that the engine doesn't produce
    record["date_explanation"] = data.get("date_explanation", "")
    record["timing_note"] = data.get("timing_note", "")
    record["why_significant"] = data.get("why_significant", "")
    record["db_date"] = data.get("db_date", "")
    record["matched_precedents"] = data.get("matched_precedents", [])
    record["precedent_expectation"] = data.get("precedent_expectation")

    top["id"] = top.pop("event_id")
    if upgrade_event(ev, record, top):
        vix = (record.get("volatility") or {}).get("vix")
        vtxt = f" VIX {vix['change_pct']}" if vix else ""
        print(f"  {eid}: UPGRADED to {target} ({days_since}d){vtxt}")
    else:
        print(f"  {eid}: upgrade write failed")

print("Maturation complete.")
