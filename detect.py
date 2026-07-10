import os, requests, json, time
from datetime import datetime, timezone

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

# ---- TIME GUARD: stop the whole run after this many seconds ----
MAX_RUNTIME = 180          # 3 minutes hard cap
START = time.time()

# ---- ACCURACY: each type must match its own confirming words ----
# A candidate only saves if the headline contains one of these action words.
CONFIRM = {
    "waterway_block": ["clos", "block", "blockad", "seiz", "mine", "shut", "disrupt"],
    "pipeline_block": ["sabotag", "explos", "ruptur", "attack", "halt", "sever", "cut"],
    "port_disruption": ["clos", "blockad", "attack", "shut", "strike", "halt"],
    "bombing": ["strike", "airstrike", "missile", "bomb", "shell", "drone", "attack"],
    "invasion": ["invas", "invad", "offensive", "incursion", "war", "troops", "cross-border"],
    "nuclear": ["nuclear", "uranium", "enrich", "missile test", "ballistic"],
    "assassination": ["assassin", "killed", "kill "],
    "sanctions": ["sanction", "embargo", "export control", "blacklist"],
    "sanctions_relief": ["lift", "eas", "remov", "relief", "waiver", "suspend"],
    "frozen_assets": ["freez", "frozen", "seiz", "confiscat"],
    "trade_deal": ["deal", "agreement", "pact", "trade", "sign", "accord"],
    "tariffs": ["tariff", "duties", "trade war", "levy", "levies"],
    "opec_supply": ["opec", "output", "production", "supply", "cut", "quota"],
    "default_crisis": ["default", "collapse", "bailout", "crisis"],
    "coup_unrest": ["coup", "takeover", "overthrow", "insurrection", "emergency"],
    "cyberattack": ["cyber", "ransomware", "hack", "breach"],
}

WATCHLIST = {
    "waterway_block":   '("strait of hormuz" OR "suez canal" OR "red sea" OR "bab el mandeb" OR "panama canal" OR "taiwan strait" OR "black sea") (closed OR blocked OR blockade OR mined OR seized OR "shut down" OR attack)',
    "pipeline_block":   '("gas pipeline" OR "oil pipeline" OR "nord stream" OR "druzhba pipeline") (sabotage OR explosion OR attacked OR ruptured OR halted OR "cut off" OR severed)',
    "port_disruption":  '(port OR terminal OR "shipping hub") (closed OR blockaded OR attacked OR "shut down" OR strike OR halted)',
    "bombing":          '(airstrike OR airstrikes OR "military strike" OR missile OR "drone strike" OR shelling OR bombardment) (oil OR refinery OR nuclear OR military OR port OR infrastructure OR "power plant")',
    "invasion":         '(invasion OR "ground offensive" OR "military incursion" OR "cross-border attack" OR "declares war" OR "full-scale") (troops OR forces OR border OR military OR offensive)',
    "nuclear":          '("nuclear test" OR "nuclear program" OR "uranium enrichment" OR "nuclear facility" OR "ballistic missile test") (test OR strike OR expanded OR launch OR threat)',
    "assassination":    '(assassination OR "killed in strike" OR "top commander killed" OR "leader assassinated") (general OR commander OR minister OR president OR official)',
    "sanctions":        '("new sanctions" OR "sanctions package" OR "sanctions imposed" OR embargo OR "export controls" OR blacklist OR "entity list") (imposed OR announced OR expanded OR targeting)',
    "sanctions_relief": '(sanctions OR embargo OR "export controls") (lifted OR eased OR removed OR "sanctions relief" OR waiver OR suspended)',
    "frozen_assets":    '("frozen assets" OR "asset freeze" OR "seized assets" OR "asset seizure" OR "confiscated reserves") (billion OR "central bank" OR sovereign OR frozen OR seized)',
    "trade_deal":       '("trade deal" OR "trade agreement" OR "free trade" OR "tariff deal" OR "trade pact" OR "framework agreement") (signed OR announced OR reached OR agreed OR ratified)',
    "tariffs":          '(tariff OR tariffs OR "import duties" OR "trade war" OR levies) (imposed OR raised OR announced OR hiked OR escalated OR retaliatory)',
    "opec_supply":      '(OPEC OR "OPEC+" OR "output cut" OR "production cut" OR "supply cut") (cut OR reduce OR increase OR quota OR boost OR slash)',
    "default_crisis":   '("sovereign default" OR "debt default" OR "currency collapse" OR "financial crisis" OR "IMF bailout") (default OR collapse OR bailout OR crisis)',
    "coup_unrest":      '(coup OR "military takeover" OR "government overthrown" OR insurrection OR "state of emergency" OR "regime collapse") (military OR government OR president OR ousted OR seized)',
    "cyberattack":      '(cyberattack OR "cyber attack" OR ransomware OR "critical infrastructure") (pipeline OR "power grid" OR port OR bank OR government OR utility)',
}

TRUSTED = ("(domainis:reuters.com OR domainis:apnews.com OR domainis:bloomberg.com "
           "OR domainis:wsj.com OR domainis:ft.com OR domainis:aljazeera.com "
           "OR domainis:bbc.com OR domainis:cnbc.com OR domainis:theguardian.com "
           "OR domainis:nytimes.com OR domainis:washingtonpost.com OR domainis:economist.com)")

import time

LAST_CALL = [0]     # tracks when we last hit GDELT

def gdelt_get(query):
    # enforce >=6 seconds since the last call, always
    wait = 6 - (time.time() - LAST_CALL[0])
    if wait > 0:
        time.sleep(wait)
    LAST_CALL[0] = time.time()

    full_query = f"{query} {TRUSTED}"
    try:
        r = requests.get(GDELT, params={"query": full_query, "mode": "artlist",
            "format": "json", "maxrecords": 50, "timespan": "1month",
            "sort": "datedesc"}, timeout=30)
        if r.status_code == 429:
            print("    (rate limited — waiting 15s)")
            time.sleep(15)
            return gdelt_get(query)         # retry once after cooldown
        return r.json().get("articles", [])
    except Exception as e:
        print(f"    (fetch failed: {str(e)[:50]})")
        return []

def is_accurate(event_type, articles):
    """ACCURACY CHECK: of the top articles, how many actually confirm the event
    by containing a confirming action-word in the headline? Requires several."""
    words = CONFIRM.get(event_type, [])
    hits = 0
    for a in articles[:20]:
        title = (a.get("title", "") or "").lower()
        if any(w in title for w in words):
            hits += 1
    return hits, hits >= 4     # need >=4 confirming headlines to count as real


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


for event_type, query in WATCHLIST.items():
    # TIME GUARD — bail out if we've run too long
    if time.time() - START > MAX_RUNTIME:
        print(f"  time cap reached ({MAX_RUNTIME}s) — stopping early")
        break

    articles = gdelt_get(query)

    # SIGNIFICANCE — enough trusted coverage?
    if len(articles) < 10:
        print(f"  {event_type}: {len(articles)} articles, not significant")
        continue

    # ACCURACY — do the headlines actually confirm this event?
    hits, ok = is_accurate(event_type, articles)
    if not ok:
        print(f"  {event_type}: {len(articles)} articles but only {hits} confirm — likely noise, skipped")
        continue

    # pick the best confirming headline as the display headline
    words = CONFIRM.get(event_type, [])
    best = next((a for a in articles if any(w in (a.get("title","") or "").lower() for w in words)),
                articles[0])
    domains = sorted({a.get("domain") for a in articles if a.get("domain")})
    wk = datetime.now(timezone.utc).strftime("%Y%W")
    save_candidate({
        "id": f"{event_type}_{wk}",
        "headline": best.get("title", "").strip(),
        "event_type": event_type,
        "detected_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "coverage_count": len(articles),
        "source_domains": ", ".join(domains[:8]),
        "status": "pending",
    })

print("Detection complete.")
