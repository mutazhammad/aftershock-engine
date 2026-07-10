"""Aftershock — event configs. One dict per event in EVENTS.
run_pipeline.py passes EVENT / BASKETS / COMPANY_INFO / NARRATIVE to the engine.
Numbers are computed by the engine; the text below is authored.
"""

# ---------- shared across all energy-shock events ----------
BASKETS = {
    "Oil tanker operators": ["STNG", "FRO", "INSW"],
    "Oil & gas producers":  ["XOM", "CVX", "COP"],
    "Defense contractors":  ["LMT", "RTX", "NOC"],
    "Gold":                 ["GLD"],
    "Airline stocks":       ["DAL", "UAL", "AAL"],
}

COMPANY_INFO = {
    "STNG": ("Scorpio Tankers", "Operates tankers through the Gulf; a supply shock can lift freight rates."),
    "FRO":  ("Frontline", "Large crude-tanker operator that gains when shipping is disrupted."),
    "INSW": ("International Seaways", "Crude and product tanker operator exposed to key routes."),
    "XOM":  ("ExxonMobil", "Integrated oil major; higher crude prices raise its revenues."),
    "CVX":  ("Chevron", "Integrated oil major that gains from rising oil prices."),
    "COP":  ("ConocoPhillips", "US oil & gas producer leveraged to crude-price spikes."),
    "LMT":  ("Lockheed Martin", "Defense prime; conflict raises demand and contract flow."),
    "RTX":  ("RTX (Raytheon)", "Defense prime with missile-defense exposure."),
    "NOC":  ("Northrop Grumman", "Defense prime that benefits from elevated defense spending."),
    "GLD":  ("SPDR Gold Shares", "Tracks gold; a safe-haven asset that tends to rise on geopolitical risk."),
    "DAL":  ("Delta Air Lines", "Major airline; fuel-cost spikes squeeze margins."),
    "UAL":  ("United Airlines", "Major airline exposed to higher fuel costs."),
    "AAL":  ("American Airlines", "Fuel-cost-sensitive airline with high oil leverage."),
}

# ---------- event list ----------
EVENTS = [

    # ========== HORMUZ 2026 ==========
    {
        "event_id": "hormuz_2026_03",
        "EVENT": {
            "event_id": "hormuz_2026_03",
            "name": "Strait of Hormuz closure",
            "type_label": "energy supply shock",
            "information_date": "2026-02-27",
            "announcement_date": "2026-03-04",
            "benchmark": "^GSPC",
            "download_start": "2025-06-01",
            "download_end": "2026-05-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Persian Gulf",
            "location": {"region": "Persian Gulf", "center": [56.3, 26.6], "zoom": 5},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["IRGC", "Reuters", "vessel-tracking"],
            "status": "confirmed",
            "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$126", "tone": "neutral"}],
            "summary": (
                "When the Strait closed, oil, shipping, defense and gold stocks rose and airlines "
                "fell — the textbook reaction to an energy-supply shock. The moves pointed the right "
                "way but over the first week most were within normal market swings. The one clear, "
                "lasting effect was a drop in airline stocks that held for weeks. Energy and gold "
                "gains faded after the 8 April ceasefire."
            ),
            "lasting_finding": (
                "Over the following weeks airline stocks fell and stayed down — the move large and "
                "consistent enough to be statistically reliable."
            ),
            "timeline": [
                {"datetime": "28 Feb 2026", "headline": "US–Israel strikes on Iran begin",
                 "detail": "Markets first learn of the conflict; risk assets start repricing.", "source": "Reuters"},
                {"datetime": "4 Mar 2026", "headline": "Iran declares the Strait closed",
                 "detail": "IRGC announces closure of the Strait of Hormuz to shipping.", "source": "IRGC"},
                {"datetime": "8 Apr 2026", "headline": "Ceasefire announced",
                 "detail": "A ceasefire eases the supply fear; the spike begins to unwind.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "Conflict begins"}, {"day": 28, "label": "Ceasefire, 8 Apr"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Rises (supply fear)", "this_event": "Rose", "match": True},
                {"sector": "Defense", "usual": "Rises (conflict)", "this_event": "Rose", "match": True},
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
                {"sector": "Airlines", "usual": "Falls (fuel cost)", "this_event": "Fell", "match": True},
                {"sector": "Tankers", "usual": "Mixed (route-dependent)", "this_event": "Rose", "match": False},
            ],
            "historical_precedents": [
                {"event_id": "abqaiq_2019", "name": "Abqaiq oil-facility attack", "date": "2019-09-16",
                 "similarity": "energy supply shock, sudden", "measured": True,
                 "mini": {"summary": "Oil jumped sharply then largely reverted within weeks.", "moves": []}},
                {"event_id": "russia_energy_2022", "name": "Russia energy shock", "date": "2022-02-24",
                 "similarity": "energy supply shock, prolonged", "measured": True,
                 "mini": {"summary": "Energy prices surged for months; not transient.", "moves": []}},
            ],
            "companies_in_news": [],
            "confidence": (
                "Few directly comparable past events; figures strip out the market's own move; the "
                "short one-week window limits how reliably small moves can be judged."
            ),
        },
    },

    # ========== ABQAIQ 2019 ==========
    {
        "event_id": "abqaiq_2019",
        "EVENT": {
            "event_id": "abqaiq_2019",
            "name": "Abqaiq oil-facility attack",
            "type_label": "energy supply shock",
            "information_date": "2019-09-16",
            "announcement_date": "2019-09-14",
            "benchmark": "^GSPC",
            "download_start": "2019-04-01",
            "download_end": "2019-12-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Saudi Arabia",
            "location": {"region": "Saudi Arabia", "center": [45.0, 24.0], "zoom": 5},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Saudi Aramco", "Reuters", "EIA"],
            "status": "confirmed",
            "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$69", "tone": "neutral"}],
            "summary": (
                "A drone and missile attack knocked out roughly 5% of global oil supply overnight, "
                "triggering the largest single-day jump in oil prices on record. Energy and safe-haven "
                "assets reacted, but because Saudi Aramco restored output within weeks, the market "
                "treated it as a sharp but temporary shock rather than a lasting supply change."
            ),
            "lasting_finding": (
                "The oil-price spike faded quickly as production was restored, so most equity reactions "
                "were short-lived."
            ),
            "timeline": [
                {"datetime": "14 Sep 2019", "headline": "Attack hits Abqaiq and Khurais facilities",
                 "detail": "Drones and missiles strike the world's largest oil-processing site.", "source": "Reuters"},
                {"datetime": "16 Sep 2019", "headline": "Markets open to a record oil spike",
                 "detail": "Oil posts its largest single-day gain on record as supply fears hit.", "source": "Reuters"},
                {"datetime": "Late Sep 2019", "headline": "Output restored",
                 "detail": "Saudi Aramco restores production faster than expected; prices ease.", "source": "Saudi Aramco"},
            ],
            "markers": [{"day": 0, "label": "Attack hits market"}, {"day": 10, "label": "Output restored"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Rises (supply fear)", "this_event": "Rose", "match": True},
                {"sector": "Airlines", "usual": "Falls (fuel cost)", "this_event": "Fell", "match": True},
            ],
            "historical_precedents": [],
            "companies_in_news": [],
            "confidence": (
                "A single-facility attack that was quickly reversed; the reaction was real but brief, "
                "limiting how much it reprices markets."
            ),
        },
    },

    # ========== RUSSIA 2022 ==========
    {
        "event_id": "russia_energy_2022",
        "EVENT": {
            "event_id": "russia_energy_2022",
            "name": "Russia energy shock",
            "type_label": "energy supply shock",
            "information_date": "2022-02-24",
            "announcement_date": "2022-02-24",
            "benchmark": "^GSPC",
            "download_start": "2021-08-01",
            "download_end": "2022-06-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Eastern Europe",
            "location": {"region": "Eastern Europe", "center": [32.0, 49.0], "zoom": 4},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "EIA"],
            "status": "confirmed",
            "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$105", "tone": "neutral"}],
            "summary": (
                "Russia's invasion of Ukraine triggered a prolonged energy shock. Sanctions and "
                "supply fears sent oil and gas prices sharply higher and kept them elevated for "
                "months. Energy and defense stocks rose while broad markets fell — and unlike a "
                "single-facility attack, the disruption was sustained rather than transient."
            ),
            "lasting_finding": (
                "Because the disruption was prolonged, energy and defense strength persisted rather "
                "than reverting within weeks."
            ),
            "timeline": [
                {"datetime": "24 Feb 2022", "headline": "Russia invades Ukraine",
                 "detail": "Markets reprice sharply on energy-supply and sanctions risk.", "source": "Reuters"},
                {"datetime": "Early Mar 2022", "headline": "Sanctions escalate",
                 "detail": "Western sanctions tighten; oil and gas prices surge further.", "source": "Bloomberg"},
                {"datetime": "Mar 2022", "headline": "Oil peaks near multi-year highs",
                 "detail": "Brent spikes toward its highest levels since 2008.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "Invasion"}, {"day": 8, "label": "Sanctions escalate"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Rises (supply fear)", "this_event": "Rose", "match": True},
                {"sector": "Defense", "usual": "Rises (conflict)", "this_event": "Rose", "match": True},
                {"sector": "Airlines", "usual": "Falls (fuel cost)", "this_event": "Fell", "match": True},
            ],
            "historical_precedents": [],
            "companies_in_news": [],
            "confidence": (
                "A prolonged, well-documented shock with strong reactions, though a single event study "
                "window captures only the initial move, not the months-long aftermath."
            ),
        },
    },
]
