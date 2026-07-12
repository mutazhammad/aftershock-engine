import os, re, json, requests
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic
from engine import run

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
AUTH = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
client = Anthropic()

# ---------- BASKETS (era-aware: some ETFs didn't exist before certain years) ----------
ENERGY = {
    "Oil tanker operators": ["STNG", "FRO", "INSW"],
    "Oil & gas producers":  ["XOM", "CVX", "COP"],
    "Defense contractors":  ["LMT", "RTX", "NOC"],
    "Gold":                 ["GLD"],
    "Airline stocks":       ["DAL", "UAL", "AAL"],
}
SHIPPING = {
    "Container liners":    ["ZIM", "MATX"],
    "Air freight":         ["FDX", "UPS"],
    "Oil & gas producers": ["XOM", "CVX"],
    "Retailers":           ["WMT", "TGT"],
}
TRADE = {
    "Industrials":    ["CAT", "DE", "BA"],
    "Semiconductors": ["NVDA", "AMD", "INTC"],
    "Retailers":      ["WMT", "TGT"],
    "Broad market":   ["SPY"],
}
SAFE = {
    "Gold":         ["GLD"],
    "Treasuries":   ["TLT"],
    "Defense":      ["LMT", "RTX", "NOC"],
    "Broad market": ["SPY"],
}
BANKS = {
    "Regional banks": ["KRE"],
    "Large banks":    ["JPM", "BAC"],
    "Gold":           ["GLD"],
    "Broad market":   ["SPY"],
}

# ticker -> first year it reliably has data (accuracy guard)
TICKER_START = {
    "STNG": 2010, "FRO": 2001, "INSW": 2017, "XOM": 1990, "CVX": 1990, "COP": 2002,
    "LMT": 1995, "RTX": 1990, "NOC": 1990, "GLD": 2005, "DAL": 2007, "UAL": 2006,
    "AAL": 2013, "ZIM": 2021, "MATX": 2012, "FDX": 1990, "UPS": 1999, "WMT": 1990,
    "TGT": 1990, "CAT": 1990, "DE": 1990, "BA": 1990, "NVDA": 1999, "AMD": 1990,
    "INTC": 1990, "SPY": 1993, "TLT": 2002, "KRE": 2006, "JPM": 1990, "BAC": 1990,
}

TYPE_CONFIG = {
    "energy_shock":    {"basket": ENERGY,   "expect": {"Oil & gas producers": "up"}},
    "shipping":        {"basket": SHIPPING, "expect": {"Container liners": "up"}},
    "sanctions":       {"basket": ENERGY,   "expect": {}},
    "military":        {"basket": ENERGY,   "expect": {"Defense contractors": "up"}},
    "tariffs":         {"basket": TRADE,    "expect": {}},
    "nuclear":         {"basket": SAFE,     "expect": {"Gold": "up"}},
    "financial_crisis":{"basket": BANKS,    "expect": {"Gold": "up"}},
    "political_shock": {"basket": SAFE,     "expect": {}},
}

MIN_CONFIDENCE = "high"     # only measure events the AI is confident about


def existing_ids():
    ids = set()
    for table in ("curated_precedents", "events"):
        try:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}",
                             params={"select": "id"}, headers=AUTH, timeout=30)
            if r.status_code == 200:
                ids |= {row["id"] for row in r.json()}
        except Exception:
            pass
    return ids


def ai_propose_events(existing):
    """AI proposes historical events with dates AND a confidence rating."""
    known = ", ".join(sorted(existing)[:40])
    system = (
        "You are a financial-markets historian. Propose SIGNIFICANT historical "
        "geopolitical/market events suitable for event-study analysis. ACCURACY IS "
        "PARAMOUNT. For each event you must give the INFORMATION DATE — the first "
        "trading day on which markets could realistically have known about it (not the "
        "official announcement if news broke earlier). Rate your confidence in that date "
        "honestly: 'high' only if you are certain of the specific day; 'medium' if you "
        "know the week; 'low' if you are unsure. Do NOT guess dates you are unsure of — "
        "mark them low. Only propose events from 2005 onward (earlier data is unreliable)."
    )
    user = (
        f"Already in the library (do not repeat): {known}\n\n"
        "Propose up to 25 NEW significant events. Return ONLY a JSON array:\n"
        '{"id":"short_snake_case_id_with_year",'
        ' "name":"Event name",'
        ' "event_type":"energy_shock|shipping|sanctions|military|tariffs|nuclear|'
        'financial_crisis|political_shock",'
        ' "information_date":"YYYY-MM-DD",'
        ' "date_confidence":"high|medium|low",'
        ' "date_reasoning":"why this is the information date",'
        ' "summary":"2-3 sentences on what happened and the market mechanism",'
        ' "region":"region name"}\n'
        "Prioritise events with clear, well-documented dates. Only JSON."
    )
    msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=6000,
                                 system=system, messages=[{"role": "user", "content": user}])
    text = msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        print("  AI returned non-JSON:", text[:150])
        return []


def era_safe_basket(basket, year):
    """ACCURACY LAYER 2: drop tickers that didn't exist in that era."""
    out = {}
    for sector, tickers in basket.items():
        keep = [t for t in tickers if TICKER_START.get(t, 1990) <= year]
        if keep:
            out[sector] = keep
    return out


def plausible(record, expect):
    """ACCURACY LAYER 3: did the expected sectors move the expected way?"""
    moves = {r["sector"]: r["tone"] for r in record.get("reaction", [])}
    if not expect:
        return True, "no directional expectation"
    matched = sum(1 for sec, d in expect.items()
                  if moves.get(sec) == ("gain" if d == "up" else "loss"))
    return matched >= 1, f"{matched}/{len(expect)} expected moves matched"


def has_signal(record):
    """ACCURACY LAYER 4: reject non-events — nothing moved meaningfully."""
    moves = []
    for r in record.get("reaction", []):
        try:
            moves.append(abs(float(str(r["pct"]).replace("%", "").replace("+", ""))))
        except Exception:
            pass
    if not moves:
        return False, "no measurable reaction"
    biggest = max(moves)
    if biggest < 2.0:
        return False, f"largest move only {biggest:.1f}% — likely a non-event"
    return True, f"largest move {biggest:.1f}%"


def save_precedent(record, top):
    row = {**top, "data": record}
    row["id"] = row.pop("event_id")
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/curated_precedents",
        params={"on_conflict": "id"},
        headers={**AUTH, "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([row]), timeout=30)
    return resp.status_code < 300, resp.text[:120]


# ---------------- run ----------------
existing = existing_ids()
print(f"Library currently has {len(existing)} events.")

print("AI proposing new historical events...")
proposals = ai_propose_events(existing)
print(f"  AI proposed {len(proposals)} events\n")

added, rejected = 0, 0
for p in proposals:
    eid = p.get("id", "").strip()
    name = p.get("name", "")
    etype = p.get("event_type", "")
    date = p.get("information_date", "")
    conf = p.get("date_confidence", "low")

    print(f"{eid}: {name[:45]}")

    if not eid or eid in existing:
        print("  SKIP: duplicate or missing id"); continue

    # LAYER 1 — confidence gate
    if conf != MIN_CONFIDENCE:
        print(f"  REJECT: date confidence '{conf}' (need '{MIN_CONFIDENCE}')")
        rejected += 1; continue

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        print("  REJECT: bad date format"); rejected += 1; continue

    cfg = TYPE_CONFIG.get(etype)
    if not cfg:
        print(f"  REJECT: unknown type {etype}"); rejected += 1; continue

    ev_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    year = ev_date.year
    if year < 2005:
        print(f"  REJECT: {year} — pre-2005 data unreliable"); rejected += 1; continue
    if (datetime.now(timezone.utc) - ev_date).days < 60:
        print("  REJECT: too recent to have a full window"); rejected += 1; continue

    # LAYER 2 — era-safe basket
    basket = era_safe_basket(cfg["basket"], year)
    if len(basket) < 2:
        print(f"  REJECT: too few tickers existed in {year}"); rejected += 1; continue

    EVENT = {
        "event_id": eid, "name": name, "type_label": etype,
        "information_date": date, "announcement_date": date, "benchmark": "^GSPC",
        "download_start": (ev_date - timedelta(days=280)).strftime("%Y-%m-%d"),
        "download_end": (ev_date + timedelta(days=60)).strftime("%Y-%m-%d"),
        "snap_window": (-2, 5), "full_window": (-5, 30),
        "region": p.get("region", ""),
    }
    NARRATIVE = {
        "sources": [], "status": "confirmed", "recency": "settled",
        "summary": p.get("summary", ""), "key_metrics": [], "timeline": [],
        "markers": [], "historical": [], "historical_precedents": [],
        "companies_in_news": [], "lasting_finding": "",
        "confidence": (f"Date: {p.get('date_reasoning','')} "
                       f"(AI-proposed, high confidence; validated by plausibility check)."),
    }

    try:
        record, top = run(EVENT, basket, {}, NARRATIVE)
    except Exception as e:
        print(f"  REJECT: measurement failed ({str(e)[:50]})"); rejected += 1; continue

    # LAYER 3 — plausibility
    ok, why = plausible(record, cfg["expect"])
    if not ok:
        print(f"  REJECT: implausible — {why}"); rejected += 1; continue

    # LAYER 4 — signal check
    sig_ok, sig_why = has_signal(record)
    if not sig_ok:
        print(f"  REJECT: {sig_why}"); rejected += 1; continue

    record["date_reasoning"] = p.get("date_reasoning", "")
    record["validation"] = {"plausibility": why, "signal": sig_why,
                            "date_confidence": conf, "auto_added": True}

    saved, err = save_precedent(record, top)
    if saved:
        vix = (record.get("volatility") or {}).get("vix")
        vtxt = f", VIX {vix['change_pct']}" if vix else ""
        print(f"  ADDED ({why}{vtxt})")
        added += 1
        existing.add(eid)
    else:
        print(f"  write failed: {err}"); rejected += 1

print(f"\nLibrary expansion complete: {added} added, {rejected} rejected.")
print(f"Library now has ~{len(existing)} events.")
