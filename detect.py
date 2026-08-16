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

MODEL = "claude-haiku-4-5-20251001"

DISCLAIMER = "This tool informs your decision. It does not give investment advice."
TOPICS = ["geopolitical conflict", "sanctions", "military strike", "oil energy crisis",
          "trade war tariffs", "invasion war", "OPEC oil", "nuclear missile"]

# Calendar days of price history to download before an event. The engine wants up to
# 250 TRADING days for its estimation window, ending 10 trading days before the event.
LOOKBACK_DAYS = 430

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

# Date confidence accepted into the precedent set. 'high' means the specific trading
# day is known. 'medium' means the week is known but not the exact day, which is
# weaker evidence but still usable when the measurement itself holds up. Anything
# lower is rejected outright.
ACCEPTED_DATE_CONFIDENCE = {"high", "medium"}


def ask(system, user, max_tokens=3000):
    msg = client.messages.create(model=MODEL, max_tokens=max_tokens,
                                 system=system, messages=[{"role": "user", "content": user}])
    return msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()


def parse_event_array(text):
    """Parse a JSON array. If the response was cut off mid-array, recover the complete
    objects that came before the cutoff rather than discarding the whole batch."""
    try:
        return json.loads(text)
    except Exception:
        pass
    print("  response did not parse as complete JSON, attempting recovery")
    recovered, depth, start = [], 0, None
    in_string = escape = False
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
                    try:
                        recovered.append(json.loads(text[start:i + 1]))
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


def is_current_measurement(data):
    """Records measured before the estimation-window significance test lack the
    'measurement' block and the per-sector 'significance' label. Their t-statistics
    came from the old underpowered in-window test, so they must be re-measured."""
    if not data.get("measurement"):
        return False
    reaction = data.get("reaction") or []
    return bool(reaction) and all("significance" in r for r in reaction)


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
                        pool.append({"title": t,
                                     "description": (a.get("description") or "")[:250]})
        except Exception as e:
            print(f"  gather failed for {topic}: {str(e)[:40]}")
        time.sleep(1)
    return pool


def ai_find_events(articles):
    """Identify significant events. No fixed quotas: length and company count follow
    what the evidence actually supports."""
    listing = "\n".join(f"{i}. {a['title']} — {a['description']}"
                        for i, a in enumerate(articles[:80]))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system = (
        "You are a senior geopolitical risk analyst writing for financial-markets "
        "professionals who already read the news. Identify SIGNIFICANT market-moving "
        "events. Ignore sports, entertainment, local news, opinion, and speculation. "
        "Write only as much as the evidence supports. Do not pad a simple event or a "
        "simple mechanism to sound thorough. A tight three sentence explanation of a "
        "straightforward causal chain is better than five sentences restating it. "
        "Never use em dashes or en dashes."
    )
    user = (
        f"Today is {today}.\n\nHEADLINES:\n{listing}\n\n"
        "Return ONLY a JSON array of up to 6 significant events, fewer if fewer qualify. "
        "For each:\n"
        '{"event_type":"waterway_block|pipeline_block|sanctions|sanctions_relief|bombing|'
        'invasion|trade_deal|tariffs|opec_supply|nuclear|coup_unrest|cyberattack|financial_crisis",\n'
        ' "headline":"the actual headline",\n'
        ' "event_date":"YYYY-MM-DD",\n'
        ' "date_explanation":"what the reporting says about timing, and whether the event '
        'was anticipated before this date. State plainly if the market may already have '
        'priced it in.",\n'
        ' "what_happened":"What occurred, who the actors are, the scale, and what is '
        'confirmed versus reported. As many sentences as this genuinely requires and no '
        'more. Three tight sentences beat eight padded ones.",\n'
        ' "transmission_mechanism":"The causal chain from this event to market prices. One '
        'sentence per genuine causal step, no more. If the chain is short, say so briefly '
        'rather than elaborating.",\n'
        ' "timing_note":"when it happened, or when it is expected",\n'
        ' "why_significant":"one line on market relevance",\n'
        ' "companies_involved":[{"ticker":"XOM","name":"ExxonMobil","role":"How this company '
        'is specifically exposed to THIS event. Name the asset, route, contract, or input '
        'cost.","exposure":"direct|indirect|beneficiary"}],\n'
        ' "region":"the affected region",\n'
        ' "location":{"center":[longitude,latitude],"zoom":5}}\n\n'
        "companies_involved: include a company only if its exposure is specific and "
        "material. Three sharp entries are better than six padded ones. Maximum six. "
        "Use real tickers. Only JSON, fully closed array."
    )
    return parse_event_array(ask(system, user, max_tokens=16000))


# ---------- precedent research ----------
def ai_research_precedents(event):
    system = (
        "You are a financial-markets historian. Identify HISTORICAL PRECEDENTS for a "
        "current event, meaning past events with the same market transmission mechanism. "
        "ACCURACY IS PARAMOUNT. Propose an event only if it is a genuine mechanism match. "
        "A policy action and a physical blockade are not interchangeable even in the same "
        "region. Two strong precedents are worth more than five loose ones, so propose "
        "fewer rather than padding the list. Only events from 2005 onward.\n\n"
        "For the INFORMATION DATE, give the first trading day markets could realistically "
        "have known, and rate your confidence honestly using this scale:\n"
        "  high: you are certain of the specific trading day\n"
        "  medium: you know the week or the few-day span but not the exact day\n"
        "  low: you are unsure even of the week\n"
        "Medium is a legitimate and useful answer. Do not inflate to high, and do not "
        "deflate a date you genuinely know to the week down to low."
    )
    user = (
        f"CURRENT EVENT:\nHeadline: {event.get('headline','')}\n"
        f"Type: {event.get('event_type','')}\n"
        f"What happened: {event.get('what_happened','')}\n"
        f"Mechanism: {event.get('transmission_mechanism','')}\n\n"
        "Return ONLY JSON, up to 5 precedents, fewer if fewer genuinely match:\n"
        '[{"id":"snake_case_id_with_year","name":"Event name",'
        ' "information_date":"YYYY-MM-DD","date_confidence":"high|medium|low",'
        ' "date_reasoning":"why this is the information date, and if confidence is medium, '
        'what specifically is uncertain about the exact day",'
        ' "anticipated":"was this event anticipated before the information date, and did '
        'markets likely price it in early. One sentence.",'
        ' "why_relevant":"why this is a precedent, focused on the shared transmission '
        'mechanism. Two sentences maximum.",'
        ' "region":"region"}]  Only JSON.'
    )
    try:
        return json.loads(ask(system, user, max_tokens=2500))
    except Exception:
        return []


# ---------- validation ----------
def era_safe(basket, year):
    out = {}
    for sector, tickers in basket.items():
        keep = [t for t in tickers if TICKER_START.get(t, 1990) <= year]
        if keep:
            out[sector] = keep
    return out


def sector_tiers(record):
    """Split sectors by evidence tier. 'significant' clears the conventional 5 percent
    level; 'directional' clears 10 percent, which many published event studies report
    and which is meaningfully different from noise."""
    strong, directional = [], []
    for r in record.get("reaction", []):
        tier = r.get("significance")
        if tier == "significant":
            strong.append(r)
        elif tier == "directional":
            directional.append(r)
    return strong, directional


def plausible(record, expect):
    """A directional expectation must be met by a sector that clears at least the
    10 percent level. Noise does not count as confirmation."""
    strong, directional = sector_tiers(record)
    moves = {r["sector"]: r["tone"] for r in strong + directional}
    if not expect:
        return True, "no directional expectation"
    m = sum(1 for s, d in expect.items()
            if moves.get(s) == ("gain" if d == "up" else "loss"))
    return m >= 1, f"{m}/{len(expect)} expected moves matched"


def has_signal(record):
    """At least one sector must clear the 10 percent level. Returns the evidence tier
    so the precedent can be labelled by strength rather than treated as binary."""
    strong, directional = sector_tiers(record)
    moves = []
    for r in record.get("reaction", []):
        try:
            moves.append(abs(float(str(r["pct"]).replace("%", "").replace("+", ""))))
        except Exception:
            continue
    if not moves:
        return False, "strong", "no measurable reaction"
    if strong:
        return True, "strong", (f"{len(strong)} sector(s) significant at the 5% level, "
                                f"largest move {max(moves):.1f}%")
    if directional:
        return True, "directional", (f"{len(directional)} sector(s) significant at the 10% "
                                     f"level only, largest move {max(moves):.1f}%")
    return False, "none", f"largest move {max(moves):.1f}% but nothing clears the 10% level"


def evidence_tier(signal_tier, date_conf):
    """Combine measurement strength and date certainty into one label the site can show."""
    if signal_tier == "strong" and date_conf == "high":
        return "strong", "Significant at the 5% level, with a precisely dated event."
    if signal_tier == "strong":
        return "moderate", ("Significant at the 5% level, but the exact information date "
                            "is known only to within a few days.")
    if date_conf == "high":
        return "moderate", ("Significant at the 10% level only, with a precisely dated "
                            "event. A weaker statistical result.")
    return "weak", ("Significant at the 10% level only, and the exact information date is "
                    "known only to within a few days. Read with caution.")


def measure_precedent(p, etype):
    pid = p.get("id", "").strip()
    date = p.get("information_date", "")
    conf = p.get("date_confidence", "low")

    if not pid or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        return None, "bad id or date"
    if conf not in ACCEPTED_DATE_CONFIDENCE:
        return None, f"date confidence '{conf}'"

    # Reuse the cache only if the stored record was measured under the CURRENT
    # methodology. Anything older gets re-measured rather than judged on stale numbers.
    cached = cache_get(pid)
    if cached and is_current_measurement(cached.get("data") or {}):
        d = cached["data"]
        cfg = TYPE_CONFIG.get(etype, {"basket": ENERGY, "expect": {}})
        sig_ok, sig_tier, sig_why = has_signal(d)
        if not sig_ok:
            return None, f"cached, {sig_why}"
        ok, why = plausible(d, cfg["expect"])
        if not ok:
            return None, f"cached, implausible, {why}"
        tier, tier_note = evidence_tier(sig_tier, conf)
        d["why_relevant"] = p.get("why_relevant", d.get("why_relevant", ""))
        d["anticipated"] = p.get("anticipated", d.get("anticipated", ""))
        d["evidence_tier"] = tier
        d["evidence_note"] = tier_note
        d["date_confidence"] = conf
        return cached, f"cached, {tier} ({sig_tier} signal, {conf} date)"

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
             "download_start": (ev - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d"),
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

    sig_ok, sig_tier, sig_why = has_signal(record)
    if not sig_ok:
        return None, sig_why
    ok, why = plausible(record, cfg["expect"])
    if not ok:
        return None, f"implausible, {why}"

    tier, tier_note = evidence_tier(sig_tier, conf)
    record["why_relevant"] = p.get("why_relevant", "")
    record["date_reasoning"] = p.get("date_reasoning", "")
    record["anticipated"] = p.get("anticipated", "")
    record["date_confidence"] = conf
    record["evidence_tier"] = tier
    record["evidence_note"] = tier_note
    record["validation"] = {"plausibility": why, "signal": sig_why,
                            "signal_tier": sig_tier, "date_confidence": conf,
                            "evidence_tier": tier}
    cache_put(record, dict(top))
    est = (record.get("measurement") or {}).get("estimation_days")
    return ({"id": pid, "name": p.get("name", ""), "information_date": date,
             "data": record},
            f"{tier} ({sig_tier} signal, {conf} date, est {est}d)")


# ---------- DIAGNOSTICS ----------
def concentration_check(prec_rows):
    """A sector result driven by one constituent is weaker evidence than a basket-wide
    move. Flags any significant sector where a single ticker dominates the reaction."""
    flags = []
    for p in prec_rows:
        d = p.get("data") or {}
        sig_sectors = {r["sector"] for r in d.get("reaction", [])
                       if r.get("significance") in ("significant", "directional")}
        by_sector = {}
        for c in d.get("companies_affected", []):
            if c.get("sector") not in sig_sectors:
                continue
            try:
                mv = abs(float(str(c.get("move_pct", "0")).replace("%", "").replace("+", "")))
            except Exception:
                continue
            by_sector.setdefault(c["sector"], []).append((c.get("ticker", "?"), mv))
        for sector, entries in by_sector.items():
            if len(entries) < 3:
                continue
            total = sum(m for _, m in entries)
            if total <= 0:
                continue
            ticker, largest = max(entries, key=lambda x: x[1])
            share = largest / total
            if share >= 0.6:
                flags.append({
                    "precedent": p.get("name", p["id"]),
                    "sector": sector,
                    "ticker": ticker,
                    "share": f"{share*100:.0f}%",
                    "detail": (f"In {p.get('name', p['id'])}, the {sector} reaction was "
                               f"largely one name: {ticker} accounted for {share*100:.0f}% "
                               f"of the basket's total movement. Read that sector's figure "
                               f"as a single-company result rather than a sector-wide one."),
                })
    return flags


def date_certainty_check(prec_rows):
    """Precedents admitted on a medium-confidence date are weaker evidence, since the
    measurement window may be anchored a day or two off. Surface that per precedent."""
    out = []
    for p in prec_rows:
        d = p.get("data") or {}
        if d.get("date_confidence") == "medium":
            out.append({
                "precedent": p.get("name", p["id"]),
                "detail": (f"The information date for this precedent is known to within a "
                           f"few days rather than exactly. {d.get('date_reasoning','')} "
                           f"A window anchored slightly off can understate the measured "
                           f"reaction.").strip(),
            })
    return out


def anticipation_check(prec_rows):
    """The causal reading of an abnormal return requires the event to have been
    unanticipated. Surfaces what the research pass said about each precedent."""
    out = []
    for p in prec_rows:
        d = p.get("data") or {}
        note = (d.get("anticipated") or "").strip()
        if note:
            out.append({"precedent": p.get("name", p["id"]), "detail": note})
    return out


def ai_confounding_check(event, prec_rows):
    """Was anything else moving markets in each precedent's window? A contaminated
    window means the measured reaction cannot be attributed to the event alone."""
    if not prec_rows:
        return []
    listing = "\n".join(
        f"- {p['id']} | {p.get('name','')} | window centred on "
        f"{str(p.get('information_date',''))[:10]}"
        for p in prec_rows)
    system = (
        "You identify confounding events. Given a historical event and its measurement "
        "window of roughly five days before to thirty days after, state whether any OTHER "
        "major market-moving development occurred in that window that would contaminate "
        "the measurement. Be specific and factual. If the window was clean, say so "
        "plainly. Do not speculate. Never use em dashes or en dashes."
    )
    user = (
        f"PRECEDENT WINDOWS TO CHECK:\n{listing}\n\n"
        "Return ONLY JSON, one entry per precedent:\n"
        '[{"precedent_id":"the id","clean":true or false,'
        ' "detail":"If not clean, name the confounding development in one sentence. If '
        'clean, state briefly that no major concurrent development was identified."}]  '
        "Only JSON."
    )
    try:
        return json.loads(ask(system, user, max_tokens=1500))
    except Exception:
        return []


def build_diagnostics(event, prec_rows):
    """The trust layer. Answers whether these measurements can be read causally,
    before any interpretation is offered."""
    if not prec_rows:
        return None
    concentration = concentration_check(prec_rows)
    anticipation = anticipation_check(prec_rows)
    date_certainty = date_certainty_check(prec_rows)
    confounding = ai_confounding_check(event, prec_rows)

    tiers = [(p.get("data") or {}).get("evidence_tier", "weak") for p in prec_rows]
    n_strong = sum(1 for t in tiers if t == "strong")
    n_moderate = sum(1 for t in tiers if t == "moderate")
    n_weak = sum(1 for t in tiers if t == "weak")

    contaminated = [c for c in confounding if not c.get("clean", True)]
    n = len(prec_rows)
    parts = [f"{n} precedent{'s' if n != 1 else ''} cleared validation"]
    strength_bits = []
    if n_strong:
        strength_bits.append(f"{n_strong} strong")
    if n_moderate:
        strength_bits.append(f"{n_moderate} moderate")
    if n_weak:
        strength_bits.append(f"{n_weak} weak")
    if strength_bits:
        parts.append("evidence strength: " + ", ".join(strength_bits))
    if concentration:
        parts.append(f"{len(concentration)} sector result{'s' if len(concentration) != 1 else ''} "
                     f"driven by a single constituent")
    if date_certainty:
        parts.append(f"{len(date_certainty)} precedent{'s' if len(date_certainty) != 1 else ''} "
                     f"dated only to within a few days")
    if contaminated:
        parts.append(f"{len(contaminated)} measurement window{'s' if len(contaminated) != 1 else ''} "
                     f"contained a confounding development")
    summary = ". ".join(parts) + "."

    est_days = [(p.get("data") or {}).get("measurement", {}).get("estimation_days")
                for p in prec_rows]
    est_days = [d for d in est_days if d]
    date_basis = ("Each precedent is anchored to its information date, the first trading "
                  "day markets could plausibly have known.")
    if est_days:
        date_basis += (f" Each reaction was tested against normal volatility estimated "
                       f"over roughly {int(sum(est_days)/len(est_days))} trading days of "
                       f"clean pre-event history.")

    return {
        "summary": summary,
        "date_basis": date_basis,
        "evidence_strength": {"strong": n_strong, "moderate": n_moderate, "weak": n_weak},
        "concentration": concentration,
        "date_certainty": date_certainty,
        "anticipation": anticipation,
        "confounding": confounding,
    }


# ---------- IMPORTANT NOTES ----------
def ai_important_notes(event, prec_rows, diagnostics):
    """Interpretation only. The diagnostics layer already handles whether the
    measurements are trustworthy, so this answers only what the comparison supports."""
    if not prec_rows:
        return None
    prec_desc = "\n".join(
        f"- {p['id']} | {p.get('name','')} | {str(p.get('information_date',''))[:10]}"
        for p in prec_rows)
    diag_summary = (diagnostics or {}).get("summary", "")

    system = (
        "You are a markets strategist. The measurement quality of these precedents has "
        "already been assessed separately, so do NOT discuss data reliability, sample "
        "size, or statistical caveats. Your only job is substantive: what has materially "
        "changed between the precedent conditions and today that would alter the market "
        "response. Before writing, identify the genuinely DISTINCT arguments. If several "
        "facts support the same underlying reason, that is ONE note with several details, "
        "not several notes. Write at most 3 notes, and one is fine if there is only one "
        "real reason. Padding with restated arguments is worse than a short section. "
        "Never use em dashes or en dashes."
    )
    user = (
        f"CURRENT EVENT:\n{event.get('headline','')}\n"
        f"Type: {event.get('event_type','')}\n"
        f"Region: {event.get('region','')}\n"
        f"What happened: {event.get('what_happened','')}\n\n"
        f"PRECEDENTS USED:\n{prec_desc}\n\n"
        f"MEASUREMENT DIAGNOSTICS ALREADY ESTABLISHED: {diag_summary}\n\n"
        "Return ONLY JSON:\n"
        '{"verdict":"ONE SENTENCE stating whether this precedent set is a strong, '
        'moderate, or weak basis for comparison, and why, in the fewest words possible.",\n'
        ' "overall_applicability":"Two to three sentences on where the comparison holds '
        'and where it breaks down. No more.",\n'
        ' "notes":[{"title":"Short title",'
        ' "category":"structural|regime|market_structure|scale|regional",'
        ' "detail":"Two to three sentences. The change and its directional effect. If this '
        'would restate another note, fold it in rather than adding it.",'
        ' "affects":["precedent_id", ...],'
        ' "direction":"amplifies|dampens|uncertain"}]}\n\n'
        "Maximum 3 notes, fewer if fewer are distinct. Only JSON."
    )
    try:
        return json.loads(ask(system, user, max_tokens=1800))
    except Exception as e:
        print(f"    (important notes failed: {str(e)[:50]})")
        return None


# ---------- expectation ----------
def build_expectation(prec_rows):
    if not prec_rows:
        return None
    sector_moves, vix_changes, vol_ratios, used, per_precedent = {}, [], [], [], []

    for p in prec_rows:
        d = p.get("data") or {}
        used.append({"id": p["id"], "name": p.get("name", ""),
                     "date": str(p.get("information_date", ""))[:10],
                     "why_relevant": d.get("why_relevant", ""),
                     "evidence_tier": d.get("evidence_tier", ""),
                     "evidence_note": d.get("evidence_note", "")})
        rows = []
        for r in d.get("reaction", []):
            try:
                pct = float(str(r["pct"]).replace("%", "").replace("+", ""))
            except Exception:
                continue
            sector_moves.setdefault(r["sector"], []).append(
                (pct, r.get("significance", "not_significant")))
            rows.append({"sector": r["sector"], "pct": r["pct"], "value": pct,
                         "significant": bool(r.get("significant")),
                         "significance": r.get("significance", ""),
                         "t_stat": r.get("t_stat")})
        vol = d.get("volatility") or {}
        vix = vol.get("vix")
        per_precedent.append({"id": p["id"], "name": p.get("name", ""),
                              "date": str(p.get("information_date", ""))[:10],
                              "evidence_tier": d.get("evidence_tier", ""),
                              "moves": rows, "vix_change": (vix or {}).get("change_pct")})
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
        n_sig = sum(1 for e in entries if e[1] == "significant")
        n_dir = sum(1 for e in entries if e[1] == "directional")
        avg = sum(pcts) / len(pcts)
        sig_pcts = [e[0] for e in entries if e[1] in ("significant", "directional")]
        avg_sig = (sum(sig_pcts) / len(sig_pcts)) if sig_pcts else None

        if n_sig:
            consistency = (f"{n_sig} of {len(entries)} significant at the 5% level"
                           + (f", {n_dir} more at the 10% level" if n_dir else ""))
        elif n_dir:
            consistency = f"{n_dir} of {len(entries)} significant at the 10% level only"
        else:
            consistency = f"0 of {len(entries)} reached statistical significance"

        averages.append({
            "sector": sector, "avg_move": f"{avg:+.1f}%", "avg_value": round(avg, 2),
            "avg_move_significant_only": (f"{avg_sig:+.1f}%" if avg_sig is not None else None),
            "n_events": len(entries), "n_significant": n_sig, "n_directional": n_dir,
            "range_low": f"{min(pcts):+.1f}%", "range_high": f"{max(pcts):+.1f}%",
            "spread": round(max(pcts) - min(pcts), 1) if len(pcts) > 1 else 0,
            "direction": "gain" if avg >= 0 else "loss",
            "consistency": consistency})
    averages.sort(key=lambda x: abs(x["avg_value"]), reverse=True)

    return {"based_on": used, "sector_averages": averages, "per_precedent": per_precedent,
            "avg_vix_change": (f"{sum(vix_changes)/len(vix_changes):+.0f}%" if vix_changes else None),
            "avg_volatility_ratio": (round(sum(vol_ratios)/len(vol_ratios), 2) if vol_ratios else None),
            "caveat": ("These figures are what actually happened in comparable historical "
                       "events, measured from market data. They are not a forecast. This "
                       "event is too recent to measure.")}


def publish(cid, e, prec_rows, expectation, diagnostics, notes):
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
        "diagnostics": diagnostics,
        "important_notes": notes,
        "db_date": now,
        "timeline": [], "reaction": [], "lasting_finding": "",
        "timeseries": {"days": [], "series": [], "markers": []}, "phases": [],
        "volatility": None,
        "historical": [], "historical_precedents": [],
        "matched_precedents": [p["id"] for p in prec_rows],
        "precedent_expectation": expectation,
        "companies_affected": [], "companies_in_news": [],
        "confidence": ("Breaking event. The market reaction has not happened yet and cannot "
                       "be measured. The precedents below were researched for this event, "
                       "measured from real market data, and labelled by evidence strength. "
                       "This analysis deepens as market data accumulates."),
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
    n_flags = len((diagnostics or {}).get("concentration", []))
    strength = (diagnostics or {}).get("evidence_strength", {})
    strength_txt = ("/".join(f"{v}{k[0]}" for k, v in strength.items() if v)
                    if strength else "")
    print(f"  {'SAVED' if resp.status_code < 300 else 'error '+str(resp.status_code)}: {cid}"
          f" ({len(prec_rows)} precedents{' ' + strength_txt if strength_txt else ''}, "
          f"{len(record['companies_involved'])} companies, "
          f"{n_flags} concentration flag(s), {n_notes} note(s))")
    if notes and notes.get("verdict"):
        print(f"    verdict: {notes['verdict']}")


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

    print("  running diagnostics...")
    diagnostics = build_diagnostics(e, prec_rows)
    if diagnostics:
        print(f"    {diagnostics['summary']}")

    print("  assessing what differs from the precedents...")
    notes = ai_important_notes(e, prec_rows, diagnostics)

    publish(cid, e, prec_rows, expectation, diagnostics, notes)

print("\nDetection complete.")
