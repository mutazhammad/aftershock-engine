"""Aftershock — event configs. One dict per event in EVENTS.
run_pipeline.py passes EVENT / BASKETS / COMPANY_INFO / NARRATIVE to the engine.
Numbers are computed by the engine; the text below is authored.

download_start is set roughly fourteen months before the information date so the
engine has enough clean pre-event history for its estimation window, which runs up
to 250 trading days ending ten trading days before the event.
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
            "download_start": "2025-01-01",
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
                "fell, the textbook reaction to an energy-supply shock. The moves pointed the right "
                "way but over the first week most were within normal market swings. The one clear, "
                "lasting effect was a drop in airline stocks that held for weeks. Energy and gold "
                "gains faded after the 8 April ceasefire."
            ),
            "lasting_finding": (
                "Over the following weeks airline stocks fell and stayed down, the move large and "
                "consistent enough to be statistically reliable."
            ),
            "timeline": [
                {"datetime": "28 Feb 2026", "headline": "US-Israel strikes on Iran begin",
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
            "download_start": "2018-07-01",
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
            "download_start": "2020-12-01",
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
                "months. Energy and defense stocks rose while broad markets fell, and unlike a "
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

    # ========== IRAN-ISRAEL 2024 ==========
    {
        "event_id": "iran_israel_2024_04",
        "EVENT": {
            "event_id": "iran_israel_2024_04",
            "name": "Iran-Israel strikes, April 2024",
            "type_label": "energy supply shock",
            "information_date": "2024-04-12",   # Fri before the Apr 13 attack
            "announcement_date": "2024-04-13",
            "benchmark": "^GSPC",
            "download_start": "2023-02-01",
            "download_end": "2024-06-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Middle East",
            "location": {"region": "Middle East", "center": [44.0, 33.0], "zoom": 4},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Reuters", "AP", "Bloomberg"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$90", "tone": "neutral"}],
            "summary": "Iran's direct strike on Israel raised fears of a wider regional war and disruption to Gulf oil. Energy and defense reacted, but with no actual supply cut and a measured response, the spike was contained and faded quickly.",
            "lasting_finding": "The reaction was brief; without a real supply disruption, energy and safe-haven gains reverted within days.",
            "timeline": [
                {"datetime": "13 Apr 2024", "headline": "Iran launches drones and missiles at Israel", "detail": "First direct Iranian strike on Israeli territory; markets brace for escalation.", "source": "Reuters"},
                {"datetime": "19 Apr 2024", "headline": "Israel's limited response", "detail": "A contained retaliation eases fears of all-out war; risk premium fades.", "source": "AP"},
            ],
            "markers": [{"day": 0, "label": "Iran strike"}, {"day": 5, "label": "Contained response"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Rises (supply fear)", "this_event": "Rose", "match": True},
                {"sector": "Defense", "usual": "Rises (conflict)", "this_event": "Rose", "match": True},
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A serious escalation but no actual supply cut; the market reaction was real but short-lived.",
        },
    },

    # ========== OPEC+ CUT 2022 ==========
    {
        "event_id": "opec_cut_2022_10",
        "EVENT": {
            "event_id": "opec_cut_2022_10",
            "name": "OPEC+ production cut, October 2022",
            "type_label": "energy supply shock",
            "information_date": "2022-10-05",   # the cut announcement
            "announcement_date": "2022-10-05",
            "benchmark": "^GSPC",
            "download_start": "2021-08-01",
            "download_end": "2022-12-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Middle East",
            "location": {"region": "Middle East", "center": [46.0, 25.0], "zoom": 4},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "OPEC"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$93", "tone": "neutral"}],
            "summary": "OPEC+ announced a large output cut, deliberately tightening global oil supply. Unlike a conflict shock, this was a policy decision: energy producers gained on higher prices, while the broader market weighed the inflation implications.",
            "lasting_finding": "Oil producers gained on the deliberate supply tightening; the effect was policy-driven and more durable than a conflict scare.",
            "timeline": [
                {"datetime": "5 Oct 2022", "headline": "OPEC+ agrees to cut output by 2 million bpd", "detail": "The largest cut since the pandemic tightens global supply.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "OPEC+ cut"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Rises (supply tightening)", "this_event": "Rose", "match": True},
                {"sector": "Airlines", "usual": "Falls (fuel cost)", "this_event": "Fell", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A deliberate policy cut rather than a disruption; the energy reaction was clear and supply-driven.",
        },
    },

    # ========== LIBYA 2011 ==========
    {
        "event_id": "libya_2011_02",
        "EVENT": {
            "event_id": "libya_2011_02",
            "name": "Libya civil war oil disruption, 2011",
            "type_label": "energy supply shock",
            "information_date": "2011-02-17",   # start of the uprising
            "announcement_date": "2011-02-17",
            "benchmark": "^GSPC",
            "download_start": "2009-12-01",
            "download_end": "2011-05-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "North Africa",
            "location": {"region": "Libya", "center": [17.0, 27.0], "zoom": 4},
        },
        "BASKETS": {   # airlines removed — JETS didn't exist in 2011
            "Oil tanker operators": ["FRO"],
            "Oil & gas producers":  ["XOM", "CVX", "COP"],
            "Defense contractors":  ["LMT", "RTX", "NOC"],
            "Gold":                 ["GLD"],
        },
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Reuters", "AP", "EIA"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$111", "tone": "neutral"}],
            "summary": "Libya's civil war removed a significant chunk of high-quality crude from global markets, driving oil sharply higher during the broader Arab Spring. Energy producers gained as supply fears mounted.",
            "lasting_finding": "The prolonged loss of Libyan output kept oil elevated, benefiting producers over an extended period.",
            "timeline": [
                {"datetime": "17 Feb 2011", "headline": "Libyan uprising begins", "detail": "Unrest threatens the country's oil exports amid the wider Arab Spring.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "Uprising begins"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Rises (supply fear)", "this_event": "Rose", "match": True},
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A prolonged real supply loss; older data means a slightly reduced basket, but the energy signal is clear.",
        },
    },

    # ========== EVER GIVEN 2021 ==========
    {
        "event_id": "ever_given_2021_03",
        "EVENT": {
            "event_id": "ever_given_2021_03",
            "name": "Ever Given blocks the Suez Canal, 2021",
            "type_label": "shipping disruption",
            "information_date": "2021-03-23",   # grounding date
            "announcement_date": "2021-03-23",
            "benchmark": "^GSPC",
            "download_start": "2020-01-01",
            "download_end": "2021-06-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Suez",
            "location": {"region": "Suez Canal", "center": [32.3, 30.4], "zoom": 5},
        },
        "BASKETS": {   # CONTAINER basket — matches the cargo, not crude
            "Container liners":    ["ZIM", "MATX"],
            "Air freight":         ["FDX", "UPS"],
            "Oil & gas producers": ["XOM", "CVX"],
            "Retailers":           ["WMT", "TGT"],
        },
        "COMPANY_INFO": {
            "ZIM":  ("ZIM Integrated Shipping", "Container liner that benefits when freight rates spike from disruption."),
            "MATX": ("Matson", "Container shipping operator exposed to global freight rates."),
            "FDX":  ("FedEx", "Air-freight operator that can gain when sea routes are blocked and cargo reroutes to air."),
            "UPS":  ("UPS", "Logistics and air-freight firm exposed to shipping disruptions."),
            "XOM":  ("ExxonMobil", "Oil major; Suez carries crude, so a blockage can lift oil modestly."),
            "CVX":  ("Chevron", "Oil major with sensitivity to shipping-driven oil moves."),
            "WMT":  ("Walmart", "Import-dependent retailer exposed to supply-chain delays and higher freight costs."),
            "TGT":  ("Target", "Retailer reliant on imported goods, squeezed by shipping disruptions."),
        },
        "NARRATIVE": {
            "sources": ["Suez Canal Authority", "Reuters", "Lloyd's List"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Days blocked", "value": "6", "tone": "neutral"}],
            "summary": "The Ever Given grounded and blocked the Suez Canal for six days, halting a major share of global container traffic. Because it was an accident expected to resolve quickly, markets treated it as a transient logistics event rather than a structural shock.",
            "lasting_finding": "The reaction was muted and short-lived; markets correctly priced a temporary blockage that was cleared within a week.",
            "timeline": [
                {"datetime": "23 Mar 2021", "headline": "Ever Given runs aground", "detail": "The container ship blocks the Suez Canal, halting traffic in both directions.", "source": "Reuters"},
                {"datetime": "29 Mar 2021", "headline": "Ship refloated", "detail": "The Ever Given is freed and traffic resumes; the disruption ends.", "source": "Suez Canal Authority"},
            ],
            "markers": [{"day": 0, "label": "Grounding"}, {"day": 4, "label": "Refloated"}],
            "historical": [
                {"sector": "Container liners", "usual": "Rises (freight rates)", "this_event": "Mixed", "match": False},
                {"sector": "Air freight", "usual": "Rises (reroute)", "this_event": "Mixed", "match": False},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A transient accident, not a structural shock, so expect small, short-lived reactions. ZIM listed only in January 2021, so the pre-event history available for this event is unusually short and the significance test is correspondingly weaker.",
        },
    },

    # ========== RED SEA 2023 ==========
    {
        "event_id": "red_sea_2023_12",
        "EVENT": {
            "event_id": "red_sea_2023_12",
            "name": "Red Sea shipping crisis, 2023",
            "type_label": "shipping disruption",
            "information_date": "2023-12-18",   # major carriers suspend Red Sea transit
            "announcement_date": "2023-12-18",
            "benchmark": "^GSPC",
            "download_start": "2022-10-01",
            "download_end": "2024-03-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Red Sea",
            "location": {"region": "Bab el-Mandeb", "center": [43.3, 12.6], "zoom": 5},
        },
        "BASKETS": {
            "Container liners":    ["ZIM", "MATX"],
            "Air freight":         ["FDX", "UPS"],
            "Oil & gas producers": ["XOM", "CVX"],
            "Retailers":           ["WMT", "TGT"],
        },
        "COMPANY_INFO": {
            "ZIM":  ("ZIM Integrated Shipping", "Container liner that gains when freight rates spike from rerouting."),
            "MATX": ("Matson", "Container shipping operator exposed to global freight rates."),
            "FDX":  ("FedEx", "Air-freight operator that can gain as blocked sea routes push cargo to air."),
            "UPS":  ("UPS", "Logistics and air-freight firm exposed to shipping disruptions."),
            "XOM":  ("ExxonMobil", "Oil major; Red Sea carries energy cargo, so disruption can lift oil."),
            "CVX":  ("Chevron", "Oil major sensitive to shipping-driven oil moves."),
            "WMT":  ("Walmart", "Import-dependent retailer exposed to longer shipping times and higher freight costs."),
            "TGT":  ("Target", "Retailer reliant on imported goods, squeezed by rerouting delays."),
        },
        "NARRATIVE": {
            "sources": ["Reuters", "Maersk", "Lloyd's List"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Suez transit drop", "value": "~90%", "tone": "neutral"}],
            "summary": "Houthi attacks forced major shipping lines to suspend Red Sea transit and reroute around the Cape of Good Hope, adding weeks to Asia-Europe voyages. Unlike a single-facility shock, this was a prolonged disruption that pushed freight rates sharply higher over months.",
            "lasting_finding": "Because the disruption was sustained, container-freight strength persisted rather than reverting within weeks, a slow-burn shipping shock.",
            "timeline": [
                {"datetime": "19 Nov 2023", "headline": "Houthis begin attacking commercial vessels", "detail": "Attacks on Red Sea shipping start, targeting vessels linked to Israel.", "source": "Reuters"},
                {"datetime": "18 Dec 2023", "headline": "Major carriers suspend Red Sea transit", "detail": "Maersk, MSC, BP and others reroute around the Cape of Good Hope.", "source": "Maersk"},
                {"datetime": "Jan 2024", "headline": "Freight rates surge", "detail": "Asia-Europe spot container rates rise sharply on rerouting costs.", "source": "Lloyd's List"},
            ],
            "markers": [{"day": 0, "label": "Carriers reroute"}, {"day": 15, "label": "Rates surge"}],
            "historical": [
                {"sector": "Container liners", "usual": "Rises (freight rates)", "this_event": "Rose", "match": True},
                {"sector": "Retailers", "usual": "Falls (import costs)", "this_event": "Fell", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A prolonged, well-documented shipping disruption; the freight-rate signal was strong and sustained.",
        },
    },

    # ========== CHIP CONTROLS 2022 ==========
    {
        "event_id": "chip_controls_2022_10",
        "EVENT": {
            "event_id": "chip_controls_2022_10",
            "name": "US semiconductor export controls on China, 2022",
            "type_label": "sanctions",
            "information_date": "2022-10-07",   # BIS rules announced
            "announcement_date": "2022-10-07",
            "benchmark": "^GSPC",
            "download_start": "2021-08-01",
            "download_end": "2022-12-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "US-China",
            "location": {"region": "China", "center": [104.0, 35.0], "zoom": 3},
        },
        "BASKETS": {
            "Chipmakers":        ["NVDA", "AMD", "INTC"],
            "Chip equipment":    ["AMAT", "LRCX", "KLAC"],
            "Broad tech":        ["QQQ"],
        },
        "COMPANY_INFO": {
            "NVDA": ("Nvidia", "Leading AI-chip designer with major China revenue exposure hit by export limits."),
            "AMD":  ("AMD", "Chip designer exposed to restricted China sales."),
            "INTC": ("Intel", "Chipmaker affected by China market restrictions."),
            "AMAT": ("Applied Materials", "Chip-equipment maker directly restricted from selling to China."),
            "LRCX": ("Lam Research", "Semiconductor equipment firm heavily exposed to China revenue."),
            "KLAC": ("KLA Corp", "Chip-equipment supplier hit by the China export ban."),
            "QQQ":  ("Nasdaq-100 ETF", "Broad tech index reflecting the sector-wide reaction."),
        },
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "US Commerce Dept"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Sector", "value": "Semiconductors", "tone": "neutral"}],
            "summary": "The US imposed sweeping controls blocking China's access to advanced chips and chipmaking equipment. This targeted a specific sector rather than energy: chip-equipment makers with heavy China revenue were hit hardest as investors priced in lost sales.",
            "lasting_finding": "Chip-equipment firms with the largest China exposure saw the sharpest reaction; the impact was sector-specific, not market-wide.",
            "timeline": [
                {"datetime": "7 Oct 2022", "headline": "US announces sweeping chip export controls", "detail": "New rules block China's access to advanced semiconductors and equipment.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "Controls announced"}],
            "historical": [
                {"sector": "Chip equipment", "usual": "Falls (lost China sales)", "this_event": "Fell", "match": True},
                {"sector": "Chipmakers", "usual": "Falls (revenue hit)", "this_event": "Fell", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A targeted sector shock; the reaction was concentrated in China-exposed chip names, as expected.",
        },
    },

    # ========== ISRAEL-HAMAS 2023 ==========
    {
        "event_id": "israel_hamas_2023_10",
        "EVENT": {
            "event_id": "israel_hamas_2023_10",
            "name": "Israel-Hamas war onset, October 2023",
            "type_label": "military conflict",
            "information_date": "2023-10-06",   # Fri before the Oct 7 attack
            "announcement_date": "2023-10-07",
            "benchmark": "^GSPC",
            "download_start": "2022-08-01",
            "download_end": "2023-12-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Middle East",
            "location": {"region": "Israel", "center": [35.0, 31.5], "zoom": 5},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Reuters", "AP", "Bloomberg"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$88", "tone": "neutral"}],
            "summary": "The October 7 Hamas attack and Israel's response raised fears of a wider Middle East conflict. Defense and oil rose on escalation risk, but with no direct hit to oil supply, the energy reaction was more about risk premium than an actual shortage.",
            "lasting_finding": "Defense stocks showed the clearest gain; oil's rise reflected regional risk premium rather than a real supply cut, and faded as containment held.",
            "timeline": [
                {"datetime": "7 Oct 2023", "headline": "Hamas launches attack on Israel", "detail": "The assault triggers war and fears of regional escalation.", "source": "Reuters"},
                {"datetime": "Mid-Oct 2023", "headline": "Israel's ground response", "detail": "Markets weigh the risk of a wider conflict drawing in oil producers.", "source": "AP"},
            ],
            "markers": [{"day": 0, "label": "Attack"}],
            "historical": [
                {"sector": "Defense", "usual": "Rises (conflict)", "this_event": "Rose", "match": True},
                {"sector": "Oil & gas", "usual": "Rises (risk premium)", "this_event": "Rose", "match": True},
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A major conflict but no direct oil-supply disruption; defense reacted clearly, energy more modestly.",
        },
    },

    # ========== IRAN SANCTIONS 2018 ==========
    {
        "event_id": "iran_sanctions_2018_11",
        "EVENT": {
            "event_id": "iran_sanctions_2018_11",
            "name": "Iran oil sanctions (maximum pressure), 2018",
            "type_label": "sanctions",
            "information_date": "2018-11-05",   # sanctions take effect
            "announcement_date": "2018-11-05",
            "benchmark": "^GSPC",
            "download_start": "2017-09-01",
            "download_end": "2019-01-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Iran",
            "location": {"region": "Iran", "center": [53.0, 32.0], "zoom": 4},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "US Treasury"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "$73", "tone": "neutral"}],
            "summary": "The US reimposed sanctions targeting Iran's oil exports, aiming to cut a major supplier off from world markets. Because waivers softened the blow and supply fears were partly priced in, the reaction was more muted than a sudden physical disruption.",
            "lasting_finding": "Waivers blunted the supply impact, so the oil reaction was contained rather than a sharp spike, a slower-burn sanctions effect.",
            "timeline": [
                {"datetime": "5 Nov 2018", "headline": "US reimposes Iran oil sanctions", "detail": "Sanctions target Iran's oil exports, with temporary waivers for some buyers.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "Sanctions effective"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Rises (supply cut)", "this_event": "Mixed", "match": False},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "Waivers meant the supply cut was partial; the market reaction was muted, showing sanctions are often slow-burn.",
        },
    },

    # ========== TRADE WAR 2019 ==========
    {
        "event_id": "trade_war_2019_05",
        "EVENT": {
            "event_id": "trade_war_2019_05",
            "name": "US-China trade war escalation, May 2019",
            "type_label": "tariffs",
            "information_date": "2019-05-05",   # Trump tariff-hike tweet, Sunday
            "announcement_date": "2019-05-10",
            "benchmark": "^GSPC",
            "download_start": "2018-03-01",
            "download_end": "2019-07-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "US-China",
            "location": {"region": "China", "center": [104.0, 35.0], "zoom": 3},
        },
        "BASKETS": {
            "Industrials":       ["CAT", "DE", "BA"],
            "Semiconductors":    ["NVDA", "AMD", "INTC"],
            "Broad market":      ["SPY"],
            "Gold":              ["GLD"],
        },
        "COMPANY_INFO": {
            "CAT":  ("Caterpillar", "Industrial bellwether exposed to China demand and tariff costs."),
            "DE":   ("Deere", "Farm-equipment maker hit by retaliatory agricultural tariffs."),
            "BA":   ("Boeing", "Exporter exposed to China trade tensions."),
            "NVDA": ("Nvidia", "Chipmaker with China revenue exposure sensitive to trade escalation."),
            "AMD":  ("AMD", "Chip designer exposed to China demand."),
            "INTC": ("Intel", "Chipmaker affected by trade uncertainty."),
            "SPY":  ("S&P 500 ETF", "Broad market reflecting risk-off on trade escalation."),
            "GLD":  ("SPDR Gold Shares", "Safe-haven asset that rises on trade-war uncertainty."),
        },
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "WSJ"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Tariff rate", "value": "10% to 25%", "tone": "neutral"}],
            "summary": "The US sharply escalated tariffs on Chinese goods, reigniting the trade war. Trade-exposed industrials and chipmakers fell on higher costs and demand fears, while gold rose as a safe haven amid the uncertainty.",
            "lasting_finding": "Trade-sensitive industrials and semiconductors led the decline; the effect was broad risk-off with safe havens gaining.",
            "timeline": [
                {"datetime": "5 May 2019", "headline": "US threatens to raise tariffs to 25%", "detail": "A surprise escalation reignites trade-war fears.", "source": "Reuters"},
                {"datetime": "10 May 2019", "headline": "Tariff hike takes effect", "detail": "Tariffs on $200bn of Chinese goods rise to 25%.", "source": "WSJ"},
            ],
            "markers": [{"day": 0, "label": "Escalation"}, {"day": 4, "label": "Tariffs effective"}],
            "historical": [
                {"sector": "Industrials", "usual": "Falls (trade costs)", "this_event": "Fell", "match": True},
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A clear trade-escalation shock; trade-exposed sectors fell and safe havens rose, as expected.",
        },
    },

    # ========== NORTH KOREA 2017 ==========
    {
        "event_id": "nkorea_2017_08",
        "EVENT": {
            "event_id": "nkorea_2017_08",
            "name": "North Korea nuclear escalation, 2017",
            "type_label": "nuclear escalation",
            "information_date": "2017-08-08",   # "fire and fury" remarks
            "announcement_date": "2017-08-08",
            "benchmark": "^GSPC",
            "download_start": "2016-06-01",
            "download_end": "2017-10-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Korea",
            "location": {"region": "Korean Peninsula", "center": [127.5, 39.0], "zoom": 4},
        },
        "BASKETS": {
            "Gold":            ["GLD"],
            "Treasuries":      ["TLT"],
            "Defense":         ["LMT", "RTX", "NOC"],
            "Broad market":    ["SPY"],
        },
        "COMPANY_INFO": {
            "GLD":  ("SPDR Gold Shares", "Safe-haven asset that rises when geopolitical fear spikes."),
            "TLT":  ("20+ Year Treasury ETF", "Long-term US bonds; a flight-to-safety asset in a crisis."),
            "LMT":  ("Lockheed Martin", "Defense prime that benefits from missile-defense demand."),
            "RTX":  ("RTX (Raytheon)", "Defense prime with missile-defense exposure."),
            "NOC":  ("Northrop Grumman", "Defense prime tied to elevated defense spending."),
            "SPY":  ("S&P 500 ETF", "Broad market reflecting risk-off on nuclear escalation."),
        },
        "NARRATIVE": {
            "sources": ["Reuters", "AP", "Bloomberg"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "VIX", "value": "spiked", "tone": "neutral"}],
            "summary": "A sharp escalation in US-North Korea rhetoric over nuclear weapons triggered a classic flight to safety. With no economic supply channel involved, the reaction was pure risk-off: gold and Treasuries rose, defense gained, and broad equities dipped before recovering.",
            "lasting_finding": "The move was a short-lived risk-off episode; safe havens rose then gave back gains as tensions eased, with no lasting economic damage.",
            "timeline": [
                {"datetime": "8 Aug 2017", "headline": "Escalation in nuclear rhetoric", "detail": "Heightened US-North Korea tensions spark a flight to safety.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "Escalation"}],
            "historical": [
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
                {"sector": "Broad market", "usual": "Falls (risk-off)", "this_event": "Fell", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A pure risk-off scare with no economic supply channel; the safe-haven reaction was clear but temporary.",
        },
    },

    # ========== SVB 2023 ==========
    {
        "event_id": "svb_2023_03",
        "EVENT": {
            "event_id": "svb_2023_03",
            "name": "Banking crisis (SVB collapse), 2023",
            "type_label": "financial crisis",
            "information_date": "2023-03-09",   # SVB deposit run begins
            "announcement_date": "2023-03-10",
            "benchmark": "^GSPC",
            "download_start": "2022-01-01",
            "download_end": "2023-06-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "United States",
            "location": {"region": "United States", "center": [-98.0, 39.0], "zoom": 3},
        },
        "BASKETS": {
            "Regional banks":  ["KRE"],
            "Large banks":     ["JPM", "BAC"],
            "Gold":            ["GLD"],
            "Broad market":    ["SPY"],
        },
        "COMPANY_INFO": {
            "KRE":  ("Regional Banking ETF", "Regional banks at the center of the deposit-flight contagion."),
            "JPM":  ("JPMorgan", "Large bank seen as a safe haven within the sector during the crisis."),
            "BAC":  ("Bank of America", "Major bank exposed to sector-wide stress."),
            "GLD":  ("SPDR Gold Shares", "Safe haven that rose as banking fears spread."),
            "SPY":  ("S&P 500 ETF", "Broad market reflecting the systemic-risk scare."),
        },
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "WSJ"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Sector", "value": "Regional banks", "tone": "neutral"}],
            "summary": "The sudden collapse of Silicon Valley Bank triggered fears of wider banking contagion. Regional banks fell sharply on deposit-flight fears, while gold rose as a safe haven and large banks held up better than smaller peers.",
            "lasting_finding": "Regional banks bore the brunt and stayed depressed; the crisis was concentrated in the banking sector rather than broad-market.",
            "timeline": [
                {"datetime": "9 Mar 2023", "headline": "Run on Silicon Valley Bank", "detail": "A deposit run forces SVB toward collapse, sparking contagion fears.", "source": "Reuters"},
                {"datetime": "12 Mar 2023", "headline": "Regulators backstop deposits", "detail": "Emergency measures aim to contain the spread.", "source": "WSJ"},
            ],
            "markers": [{"day": 0, "label": "SVB run"}, {"day": 3, "label": "Backstop"}],
            "historical": [
                {"sector": "Regional banks", "usual": "Falls (contagion)", "this_event": "Fell", "match": True},
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A sharp, sector-specific banking shock; regional banks fell hard while contagion was contained.",
        },
    },

    # ========== OPEC PRICE WAR 2020 ==========
    {
        "event_id": "opec_pricewar_2020_03",
        "EVENT": {
            "event_id": "opec_pricewar_2020_03",
            "name": "OPEC price war / oil crash, 2020",
            "type_label": "energy supply shock",
            "information_date": "2020-03-06",   # OPEC+ talks collapse, Fri
            "announcement_date": "2020-03-09",
            "benchmark": "^GSPC",
            "download_start": "2019-01-01",
            "download_end": "2020-06-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Middle East",
            "location": {"region": "Middle East", "center": [46.0, 25.0], "zoom": 4},
        },
        "BASKETS": BASKETS,
        "COMPANY_INFO": COMPANY_INFO,
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "OPEC"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Brent oil", "value": "crashed", "tone": "loss"}],
            "summary": "When OPEC+ talks collapsed, Saudi Arabia launched a price war and flooded the market with oil, sending crude into one of its steepest crashes ever. This was an oversupply shock, the mirror image of a supply cut, hammering oil producers rather than lifting them.",
            "lasting_finding": "Oil producers fell hard on the deliberate oversupply, showing the same energy-shock type can push producers down when supply floods rather than tightens.",
            "timeline": [
                {"datetime": "6 Mar 2020", "headline": "OPEC+ talks collapse", "detail": "Russia and Saudi Arabia fail to agree on cuts; a price war begins.", "source": "Reuters"},
                {"datetime": "9 Mar 2020", "headline": "Oil crashes", "detail": "Crude posts one of its largest single-day drops as Saudi Arabia floods the market.", "source": "Bloomberg"},
            ],
            "markers": [{"day": 0, "label": "Talks collapse"}],
            "historical": [
                {"sector": "Oil & gas", "usual": "Falls (oversupply)", "this_event": "Fell", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "Overlaps the COVID crash, so the market-adjusted model is doing real work here; the oil-specific oversupply signal is the key read.",
        },
    },

    # ========== TURKEY 2018 ==========
    {
        "event_id": "turkey_2018_08",
        "EVENT": {
            "event_id": "turkey_2018_08",
            "name": "Turkey currency crisis, 2018",
            "type_label": "financial crisis",
            "information_date": "2018-08-10",   # lira crash accelerates
            "announcement_date": "2018-08-10",
            "benchmark": "^GSPC",
            "download_start": "2017-06-01",
            "download_end": "2018-11-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "Turkey",
            "location": {"region": "Turkey", "center": [35.0, 39.0], "zoom": 4},
        },
        "BASKETS": {
            "Emerging markets":  ["EEM"],
            "European banks":    ["EUFN"],
            "Gold":              ["GLD"],
            "US dollar":         ["UUP"],
            "Broad market":      ["SPY"],
        },
        "COMPANY_INFO": {
            "EEM":  ("Emerging Markets ETF", "EM equities hit by contagion fears from Turkey's crisis."),
            "EUFN": ("European Financials ETF", "European banks with exposure to Turkish debt."),
            "GLD":  ("SPDR Gold Shares", "Safe haven amid the currency turmoil."),
            "UUP":  ("US Dollar Index ETF", "The dollar strengthens as capital flees emerging markets."),
            "SPY":  ("S&P 500 ETF", "Broad US market, relatively insulated from the EM shock."),
        },
        "NARRATIVE": {
            "sources": ["Reuters", "Bloomberg", "FT"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "Lira", "value": "crashed", "tone": "loss"}],
            "summary": "Turkey's lira collapsed amid a debt and confidence crisis, raising fears of contagion to other emerging markets and European banks exposed to Turkish debt. Capital fled to the dollar and gold, while EM assets and exposed banks fell.",
            "lasting_finding": "The dollar and gold gained on the flight to safety while EM assets fell; contagion stayed largely contained to emerging markets.",
            "timeline": [
                {"datetime": "10 Aug 2018", "headline": "Lira crash accelerates", "detail": "Turkey's currency plunges, sparking emerging-market contagion fears.", "source": "Reuters"},
            ],
            "markers": [{"day": 0, "label": "Lira crash"}],
            "historical": [
                {"sector": "Emerging markets", "usual": "Falls (contagion)", "this_event": "Fell", "match": True},
                {"sector": "US dollar", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A currency crisis with contained contagion; the flight-to-dollar and EM weakness were the clear signals.",
        },
    },

    # ========== BREXIT 2016 ==========
    {
        "event_id": "brexit_2016_06",
        "EVENT": {
            "event_id": "brexit_2016_06",
            "name": "Brexit referendum, 2016",
            "type_label": "political shock",
            "information_date": "2016-06-24",   # result announced
            "announcement_date": "2016-06-24",
            "benchmark": "^GSPC",
            "download_start": "2015-04-01",
            "download_end": "2016-09-01",
            "snap_window": (-2, 5),
            "full_window": (-5, 30),
            "region": "United Kingdom",
            "location": {"region": "United Kingdom", "center": [-2.0, 54.0], "zoom": 4},
        },
        "BASKETS": {
            "UK equities":     ["EWU"],
            "British pound":   ["FXB"],
            "Gold":            ["GLD"],
            "Broad market":    ["SPY"],
        },
        "COMPANY_INFO": {
            "EWU":  ("UK Equity ETF", "UK stocks hit by the shock Leave vote and growth fears."),
            "FXB":  ("British Pound ETF", "The pound plunged to multi-decade lows on the result."),
            "GLD":  ("SPDR Gold Shares", "Safe haven that surged on the surprise outcome."),
            "SPY":  ("S&P 500 ETF", "Broad US market, which fell then recovered quickly."),
        },
        "NARRATIVE": {
            "sources": ["Reuters", "BBC", "FT"],
            "status": "confirmed", "recency": "settled",
            "key_metrics": [{"label": "GBP/USD", "value": "-8%", "tone": "loss"}],
            "summary": "Britain's surprise vote to leave the EU shocked markets. The pound crashed to multi-decade lows and UK equities and global stocks dropped on the uncertainty, while gold surged as a safe haven, before broad markets recovered within weeks.",
            "lasting_finding": "The pound's fall was the durable effect; equity markets dropped sharply then recovered, showing a political shock without a direct economic supply channel.",
            "timeline": [
                {"datetime": "24 Jun 2016", "headline": "UK votes to leave the EU", "detail": "The surprise result sends the pound and global equities sharply lower.", "source": "BBC"},
            ],
            "markers": [{"day": 0, "label": "Result"}],
            "historical": [
                {"sector": "British pound", "usual": "Falls (uncertainty)", "this_event": "Fell", "match": True},
                {"sector": "Gold", "usual": "Rises (safe haven)", "this_event": "Rose", "match": True},
            ],
            "historical_precedents": [], "companies_in_news": [],
            "confidence": "A clean political-shock case; the currency reaction was lasting while equities recovered quickly.",
        },
    },

]
