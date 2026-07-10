import os, requests, json, time
from datetime import datetime, timezone

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

WATCHLIST = {
    "waterway_block":   '("strait of hormuz" OR "suez canal" OR "bab el mandeb" OR "panama canal" OR "red sea" OR "taiwan strait" OR "black sea" OR "kerch strait" OR "malacca strait" OR "dardanelles" OR "bosphorus") (closed OR blocked OR blockade OR mined OR "shut down" OR disrupted OR seized OR attack OR rerouted OR suspended)',
    "pipeline_block":   '("gas pipeline" OR "oil pipeline" OR "nord stream" OR "druzhba pipeline" OR "energy pipeline" OR "power line" OR "transit pipeline") (sabotage OR explosion OR blast OR ruptured OR attacked OR "cut off" OR shutdown OR leak OR halted OR severed OR damaged)',
    "sanctions":        '("new sanctions" OR "sanctions package" OR "sanctions imposed" OR embargo OR "export controls" OR "asset freeze" OR "trade restrictions" OR blacklist OR "entity list") (imposed OR announced OR expanded OR targeting OR "cracks down" OR tightened)',
    "sanctions_relief": '(sanctions OR embargo OR "export controls" OR restrictions) (lifted OR eased OR removed OR "sanctions relief" OR waiver OR suspended OR relaxed)',
    "bombing":          '(airstrike OR airstrikes OR "military strike" OR missile OR shelling OR bombardment OR "drone strike" OR "rocket attack" OR raid) (oil OR refinery OR "power plant" OR nuclear OR military OR port OR infrastructure OR facility OR base OR depot)',
    "invasion":         '(invasion OR "ground offensive" OR "military incursion" OR "cross-border attack" OR "declares war" OR mobilization OR "troop buildup") (troops OR forces OR border OR military OR advance OR offensive)',
    "trade_deal":       '("trade deal" OR "trade agreement" OR "free trade" OR "tariff deal" OR "trade pact" OR "framework agreement" OR "trade accord" OR "economic partnership") (signed OR announced OR reached OR agreed OR ratified OR finalized)',
    "tariffs":          '(tariff OR tariffs OR "import duties" OR "trade barriers" OR "trade war" OR levies OR duties) (imposed OR raised OR announced OR "new tariffs" OR hiked OR escalated OR retaliatory)',
    "opec_supply":      '(OPEC OR "OPEC+" OR "oil production" OR "output cut" OR "supply cut" OR "crude output") (cut OR reduce OR increase OR quota OR "production target" OR boost OR slash)',
    "coup_unrest":      '(coup OR "military takeover" OR "government overthrown" OR "civil unrest" OR "mass protests" OR insurrection OR uprising OR "state of emergency") (military OR government OR president OR capital OR ousted OR seized)',
    "cyberattack":      '(cyberattack OR "cyber attack" OR ransomware OR "data breach" OR "cyber operation") (infrastructure OR bank OR "power grid" OR pipeline OR port OR government OR utility OR financial)',
    "nuclear":          '("nuclear test" OR "nuclear program" OR "uranium enrichment" OR "nuclear facility" OR "ballistic missile") (test OR strike OR expanded OR "missile launch" OR threat OR escalation)',
    "energy_shock":     '("energy crisis" OR "power outage" OR "gas supply" OR "oil supply" OR "electricity shortage" OR "fuel shortage") (cut OR halted OR disrupted OR shortage OR crisis OR surge OR spike)',
}
def save_candidate(c):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/candidates",
        params={"on_conflict": "id"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps([c]), timeout=30,
    )
    print(f"  {'saved' if resp.status_code < 300 else 'error '+str(resp.status_code)}: {c['id']}")


def gdelt_get(query, tries=3):
    for i in range(tries):
        try:
            r = requests.get(GDELT, params={"query": query, "mode": "artlist",
                "format": "json", "maxrecords": 75, "timespan": "7d",
                "sort": "datedesc"}, timeout=20)
            return r.json().get("articles", [])
        except Exception:
            time.sleep(10)          # wait, then retry
    return []


for event_type, query in WATCHLIST.items():
    articles = gdelt_get(query)                     # ← uses the retry helper

    if len(articles) < 5:
        print(f"  {event_type}: {len(articles)} articles, below threshold")
        time.sleep(5)
        continue

    domains = sorted({a.get("domain") for a in articles if a.get("domain")})
    wk = datetime.now(timezone.utc).strftime("%Y%W")
    save_candidate({
        "id": f"{event_type}_{wk}",
        "headline": articles[0].get("title", "").strip(),
        "event_type": event_type,
        "detected_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "coverage_count": len(articles),
        "source_domains": ", ".join(domains[:8]),
        "status": "pending",
    })
    time.sleep(5)

print("Detection complete.")
