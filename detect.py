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

MODEL = "claude-haiku-4-5-20251001"      # everything runs on Haiku

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


def ask(system, user, max_tokens=3000):
    msg = client.messages.create(model=MODEL, max_tokens=max_tokens,
                                 system=system, messages=[{"role": "user", "content": user}])
    return msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()


def parse_event_array(text):
    """Parse a JSON array of event objects. If the response was cut off mid-array,
    recover whatever complete top-level objects came before the cutoff instead of
    discarding the whole batch."""
    try:
        return json.loads(text)
    except Exception:
        pass

    print("  response did not parse as complete JSON, attempting recovery")
    recovered = []
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    chunk = text[start:i + 1]
                    try:
                        recovered.append(json.loads(chunk))
                    except Exception:
                        pass
                    start = None

    if recovered:
        print(f"  recovered {len(recovered)} complete event(s) from a truncated response")
        return recovered

    print("  could not recover any events:", text[:150])
    return []


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
    """Identify significant events with deep analysis and named companies."""
    listing = "\n".join(f"{i}. {a['title']} — {a['description']}"
                        for i, a in enumerate(articles[:80]))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system = (
        "You are a senior geopolitical risk analyst writing for financial-markets "
        "professionals. Identify SIGNIFICANT market-moving events from recent news. "
        "Ignore sports, entertainment, local news, opinion, and speculation. Write with "
        "analytical depth: explain the mechanism by which the event transmits to markets, "
        "not just what happened. Name the specific companies exposed and explain how each "
        "is exposed. Never use em dashes or en dashes in your prose. Identify at most 6 "
        "events, prioritising the most significant, so the full response fits comfortably "
        "within the output limit."
    )
    user = (
        f"Today is {today}.\n\nHEADLINES:\n{listing}\n\n"
        "Return ONLY a JSON array of up to 6 significant events. For each:\n"
        '{"event_type":"waterway_block|pipeline_block|sanctions|sanctions_relief|bombing|'
        'invasion|trade_deal|tariffs|opec_supply|nuclear|coup_unrest|cyberattack|financial_crisis",\n'
        ' "headline":"the actual headline",\n'
        ' "event_date":"YYYY-MM-DD",\n'
        ' "date_explanation":"what the reporting says about timing and how certain the date is",\n'
        ' "what_happened":"FIVE TO EIGHT sentences. What occurred, who the actors are, the '
        'scale and severity, what is confirmed versus reported, and the immediate operational '
        'consequences. Be specific and substantive.",\n'
        ' "transmission_mechanism":"THREE TO FIVE sentences explaining the causal chain from '
        'this event to market prices. Which physical or financial channel carries the shock, '
        'which inputs get scarcer or more expensive, and which margins are squeezed or widened.",\n'
        ' "timing_note":"when it happened, or when it is expected to happen",\n'
        ' "why_significant":"one line on market relevance",\n'
        ' "companies_involved":[{"ticker":"XOM","name":"ExxonMobil","role":"How this specific '
        'company is exposed to THIS event, one or two sentences. Be concrete: which asset, '
        'which route, which contract, which input cost.","exposure":"direct|indirect|beneficiary"}],\n'
        ' "region":"the affected region",\n'
        ' "location":{"center":[longitude,latitude],"zoom":5}}\n\n'
        "companies_involved should list 4 to 6 specific listed companies, including both those "
        "hurt and those who benefit. Use real tickers. Only JSON, and make sure the array is "
        "fully closed."
    )
    text = ask(system, user, max_tokens=16000)
    return parse_event_array(text)


# ---------- per-event precedent research ----------
def ai_research_precedents(event):
    system = (
        "You are a financial-markets historian. Given a current event, identify the closest "
        "HISTORICAL PRECEDENTS, meaning past events with the same market transmission "
        "mechanism. ACCURACY IS PARAMOUNT. For each, give the INFORMATION DATE, the first "
        "trading day markets could realistically have known, and rate your confidence "
        "honestly. Use 'high' only if you are certain of the specific day. Only propose "
        "events from 2005 onward. Do not guess dates. Match the event's actual mechanism, "
        "not just its surface category. A policy action and a physical blockade are not "
        "interchangeable precedents even if both involve the same region."
    )
    user = (
        f"CURRENT EVENT:\nHeadline: {event.get('headline','')}\n"
        f"Type: {event.get('event_type','')}\n"
        f"What happened: {event.get('what_happened','')}\n"
        f"Mechanism: {event.get('transmission_mechanism','')}\n\n"
        "Identify up to 5 of the closest historical precedents. Return ONLY JSON:\n"
        '[{"id":"snake_case_id_with_year","name":"Event name",'
        ' "information_date":"YYYY-MM-DD","date_confidence":"high|medium|low",'
        ' "date_reasoning":"why this is the information date",'
        ' "why_relevant":"two to three sentences on why this is a precedent for the current '
        'event, focusing on the shared transmission mechanism",'
        ' "region":"region"}]  Only JSON.'
    )
    text = ask(system, user, max_tokens=2500)
    try:
        return json.loads(text)
    except Exception:
        return []


# ---------- IMPORTANT NOTES, consolidated ----------
def ai_important_notes(event, prec_rows):
    """What differs between the precedents and today. Consolidated: at most 3 notes,
    a verdict up front, no restating the same argument multiple ways."""
    if not prec_rows:
        return None

    prec_desc = "\n".join(
        f"- {p['id']} | {p.get('name','')} | {str(p.get('information_date',''))[:10]}"
        for p in prec_rows)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system = (
        "You are a markets strategist. Identify why a historical precedent may not "
        "translate cleanly to a current event. Before writing anything, identify the "
        "genuinely DISTINCT arguments, not the number of facts you could cite. If several "
        "facts support the same underlying reason, for example structural capacity moving "
        "away from a single region, that is ONE note with several supporting details, not "
        "several notes. Write at most 3 notes. If there is truly only one real reason the "
        "precedents apply or fail to apply, write one note and stop. Padding with restated "
        "arguments is worse than a short section. Be specific and concrete. Never use em "
        "dashes or en dashes."
    )
    user = (
        f"Today is {today}.\n\n"
        f"CURRENT EVENT:\n{event.get('headline','')}\n"
        f"Type: {event.get('event_type','')}\n"
        f"Region: {event.get('region','')}\n"
        f"What happened: {event.get('what_happened','')}\n\n"
        f"PRECEDENTS BEING USED:\n{prec_desc}\n\n"
        "Return ONLY JSON:\n"
        '{"verdict":"ONE SENTENCE stating plainly whether this precedent set is a strong, '
        'moderate, or weak basis for comparison, and why in the fewest words possible.",\n'
        ' "overall_applicability":"TWO TO THREE sentences, no more. State where the '
        'comparison holds and where it breaks down.",\n'
        ' "notes":[{"title":"Short title",'
        ' "category":"structural|regime|market_structure|confounding|scale|regional",'
        ' "detail":"TWO TO THREE sentences. State the change and its directional effect. '
        'If this note would restate a point already made in another note, do not include '
        'it, fold the detail into the existing note instead.",'
        ' "affects":["precedent_id", ...],'
        ' "direction":"amplifies|dampens|uncertain"}]}\n\n'
        "Maximum 3 notes. Fewer is better if fewer are genuinely distinct. Only JSON."
    )
    text = ask(system, user, max_tokens=1800)
    try:
        return json.loads(text)
    except Exception as e:
        print(f"    (important notes failed: {str(e)[:50]})")
        return None


# ---------- measurement and validation ----------
def era_safe(basket, year):
    out = {}
    for sector, tickers in basket.items():
        keep = [t for t in tickers if TICKER_START.get(t, 1990) <= year]
        if keep:
            out[sector] = keep
    return out


def plausible(record, expect):
    """A directional expectation must be met by a SIGNIFICANT sector, not any sector
    regardless of significance. Raises the bar from 'moved the right way' to 'moved
    the right way and the move was real'."""
    sig_moves = {r["sector"]: r["tone"] for r in record.get("reaction", [])
                if r.get("significant")}
    if not expect:
        return True, "no directional expectation"
    m = sum(1 for s, d in expect.items()
            if sig_moves.get(s) == ("gain" if d == "up" else "loss"))
    return m >= 1, f"{m}/{len(expect)} expected moves matched with significance"


def has_signal(record):
    """At least one sector must be statistically significant, not just large. A big
    but noisy move is not evidence."""
    moves = []
    sig_count = 0
    for r in record.get("reaction", []):
        try:
            pct = abs(float(str(r["pct"]).replace("%", "").replace("+", "")))
        except Exception:
            continue
        moves.append(pct)
        if r.get("significant"):
            sig_count += 1
    if not moves:
        return False, "no measurable reaction"
    if sig_count == 0:
        return False, f"largest move {max(moves):.1f}% but nothing statistically significant"
    return True, f"largest move {max(moves):.1f}%, {sig_count} sector(s) significant"


def measure_precedent(p, etype):
    pid = p.get("id", "").strip()
    date = p.get("information_date", "")
    conf = p.get("date_confidence", "low")

    if not pid or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        return None, "bad id or date"
    if conf != "high":
        return None, f"date confidence '{conf}'"

    cached = cache_get(pid)
    if cached and (cached.get("data") or {}).get("reaction"):
        d = cached["data"]
        # cached precedents measured under the OLD looser gate may not meet the new bar,
        # so re-validate them against the current standard before reusing
        cfg = TYPE_CONFIG.get(etype, {"basket": ENERGY, "expect": {}})
        sig_ok, sig_why = has_signal(d)
        if not sig_ok:
            return None, f"cached but fails current bar, {sig_why}"
        ok, why = plausible(d, cfg["expect"])
        if not ok:
            return None, f"cached but fails current bar, implausible, {why}"
        d["why_relevant"] = p.get("why_relevant", d.get("why_relevant", ""))
        return cached, "cached, re-validated"

    ev = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if ev.year < 2005:
        return None, f"{ev.year}, pre-2005 data unreliable"
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
                 "confidence": f"Date basis: {p.get('date_reasoning','')}"}
    try:
        record, top = run(EVENT, basket, {}, NARRATIVE)
    except Exception as e:
        return None, f"measurement failed ({str(e)[:40]})"

    sig_ok, sig_why = has_signal(record)
    if not sig_ok:
        return None, sig_why
    ok, why = plausible(record, cfg["expect"])
    if not ok:
        return None, f"implausible, {why}"

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
    per_precedent = []

    for p in prec_rows:
        d = p.get("data") or {}
        used.append({"id": p["id"], "name": p.get("name", ""),
                     "date": str(p.get("information_date", ""))[:10],
                     "why_relevant": d.get("why_relevant", "")})
        rows = []
        for r in d.get("reaction", []):
            try:
                pct = float(str(r["pct"]).replace("%", "").replace("+", ""))
            except Exception:
                continue
            sector_moves.setdefault(r["sector"], []).append((pct, bool(r.get("significant"))))
            rows.append({"sector": r["sector"], "pct": r["pct"], "value": pct,
                         "significant": bool(r.get("significant")), "t_stat": r.get("t_stat")})
        vol = d.get("volatility") or {}
        vix = vol.get("vix")
        per_precedent.append({"id": p["id"], "name": p.get("name", ""),
                              "date": str(p.get("information_date", ""))[:10],
                              "moves": rows,
                              "vix_change": (vix or {}).get("change_pct")})
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
        sig_pcts = [e[0] for e in entries if e[1]]
        avg_sig = (sum(sig_pcts) / len(sig_pcts)) if sig_pcts else None
        averages.append({"sector": sector, "avg_move": f"{avg:+.1f}%", "avg_value": round(avg, 2),
                         "avg_move_significant_only": (f"{avg_sig:+.1f}%" if avg_sig is not None else None),
                         "n_events": len(entries), "n_significant": n_sig,
                         "range_low": f"{min(pcts):+.1f}%", "range_high": f"{max(pcts):+.1f}%",
                         "spread": round(max(pcts) - min(pcts), 1) if len(pcts) > 1 else 0,
                         "direction": "gain" if avg >= 0 else "loss",
                         "consistency": f"{n_sig} of {len(entries)} were statistically significant"})
    averages.sort(key=lambda x: abs(x["avg_value"]), reverse=True)

    return {"based_on": used, "sector_averages": averages, "per_precedent": per_precedent,
            "avg_vix_change": (f"{sum(vix_changes)/len(vix_changes):+.0f}%" if vix_changes else None),
            "avg_volatility_ratio": (round(sum(vol_ratios)/len(vol_ratios), 2) if vol_ratios else None),
            "caveat": ("These figures are what actually happened in comparable historical events, "
                       "measured from market data. They are not a forecast of what will happen now. "
                       "This event is too recent to measure.")}


def publish(cid, e, prec_rows, expectation, notes):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    record = {
        "event": {"name": e.get("headline", "")[:120], "type_label": e.get("event_type", ""),
                  "information_date": e.get("event_date", ""), "announcement_date": "",
                  "key_metrics": []},
        "location": e.get("location", {}),
        "sources": [], "status": "confirmed", "recency": "breaking",
        "summary": e.get("what_happened", ""),
        "transmission_mechanism": e.get("transmission_mechanism", ""),
        "date_explanation": e.get("date_explanation", ""),
        "timing_note": e.get("timing_note", ""),
        "why_significant": e.get("why_significant", ""),
        "companies_involved": e.get("companies_involved", []),
        "important_notes": notes,
        "db_date": now,
        "timeline": [], "reaction": [], "lasting_finding": "",
        "timeseries": {"days": [], "series": [], "markers": []}, "phases": [],
        "volatility": None,
        "historical": [], "historical_precedents": [],
        "matched_precedents": [p["id"] for p in prec_rows],
        "precedent_expectation": expectation,
        "companies_affected": [], "companies_in_news": [],
        "confidence": ("Breaking event. The market reaction has not happened yet and cannot be "
                       "measured. The precedents below were researched for this specific event, "
                       "measured from real market data, and validated against a strict "
                       "statistical significance bar. This analysis deepens automatically as "
                       "market data accumulates."),
        "disclaimer": DISCLAIMER,
    }
    top = {"id": cid, "name": e.get("headline", "")[:120], "type_label": e.get("event_type", ""),
           "information_date": e.get("event_date", "") or None, "status": "confirmed",
           "recency": "breaking", "region": e.get("region", "")}
    resp = requests.post(f"{SUPABASE_URL}/rest/v1/events", params={"on_conflict": "id"},
        headers={**AUTH, "Content-Type": "application/json",
                 "Prefer": "resolution=ignore-duplicates,return=minimal"},
        data=json.dumps([{**top, "data": record}]), timeout=30)
    n_notes = len(notes.get("notes", [])) if notes else 0
    verdict = (notes or {}).get("verdict", "") if notes else ""
    print(f"  {'SAVED' if resp.status_code < 300 else 'error '+str(resp.status_code)}: {cid}"
          f" ({len(prec_rows)} precedents, {len(record['companies_involved'])} companies, "
          f"{n_notes} notes)")
    if verdict:
        print(f"    verdict: {verdict}")


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
    prec_rows = []
    for p in ai_research_precedents(e):
        row, why = measure_precedent(p, etype)
        print(f"    {'OK' if row else 'REJECT'} {p.get('id','?')}: {why}")
        if row:
            prec_rows.append(row)

    expectation = build_expectation(prec_rows)

    print("  analysing what makes this event different...")
    notes = ai_important_notes(e, prec_rows)

    publish(cid, e, prec_rows, expectation, notes)

print("\nDetection complete.")
