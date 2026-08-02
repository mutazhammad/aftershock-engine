# Aftershock

Aftershock measures how geopolitical events move financial markets. It detects significant events from live news, researches historical precedents for each one, measures those precedents with a real event-study engine, and rejects any measurement that fails statistical validation before it reaches the site. The system runs unattended on a schedule.

**Live site:** [add your Vercel URL here]
**Frontend repo:** [add your aftershock_site link here]

This repo is the backend: the event-study engine, the detection and precedent-research pipeline, and the scheduled jobs that keep the database current.

## What it does

A geopolitical event breaks. The system has no market reaction to measure yet, since the reaction has not happened. Instead of guessing, it researches historical events with the same market transmission mechanism, measures each one with the same engine used for everything else, and keeps only the ones whose measurements are statistically defensible. The event publishes immediately as **breaking**, carrying that validated historical context. As real trading days pass, a separate job re-measures the event itself, upgrading it to **developing** at ten days and **settled** at thirty-five, once the full reaction window is complete. Settled events then become available as precedents for the next breaking event. The archive builds itself.

Every report includes:

- What happened, and the specific mechanism by which it reaches market prices
- Named companies exposed to the event, and how each is exposed
- Historical precedents, each independently measured and validated, not just cited
- What those precedents' sector reactions looked like on average, and how consistent that pattern actually was
- A written assessment of where the historical comparison holds and where it breaks down
- Market fear (VIX) and realized volatility, before and after
- A significance test on every reported move

## The core methodological decision

The engine anchors every measurement to the **information date** — the first trading day markets could plausibly have known about an event — rather than the date of an official announcement. These are often different days, and the gap matters. Early builds of this engine anchored to the announcement date for a Strait of Hormuz closure. The results looked clean. They were wrong: markets had already repriced days earlier, when the news first broke. Moving the anchor to the information date changed which sectors showed a significant reaction and which did not. In event-study work, the hardest question is rarely what to measure. It is when to start measuring.

## Architecture

```
Live news (Currents API)
        │
        ▼
AI event detection (Anthropic, Haiku)
        │
        ▼
Per-event precedent research ──▶ Event-study engine ──▶ Validation gates
        │                         (pandas, yfinance)      (significance,
        ▼                                                  plausibility,
Supabase (PostgreSQL)                                       date confidence)
        │
        ▼
React frontend (reads directly from Supabase, no backend server)
```

Two tables carry the system. `events` is the live feed: detected events, breaking on arrival, maturing over time. `curated_precedents` is the validated historical library, populated automatically as precedents pass validation and as feed events themselves mature into settled, measured records.

Three scheduled GitHub Actions jobs run this unattended:

| Job | Job it does |
|---|---|
| `detect.py` | Finds significant current events, researches and validates their precedents, publishes to the feed |
| `mature.py` | Re-measures aging feed events, upgrading breaking to developing to settled |
| `run_pipeline.py` | Maintains the original hand-curated event set that seeded the precedent library |

## Validation, not just detection

Finding a plausible-sounding historical parallel is easy. Most of the engineering effort here went into making sure a bad parallel gets rejected rather than published. A candidate precedent only survives if:

- The AI is confident, not merely approximate, about its information date
- The event postdates 2005 and has a complete post-event trading window
- At least one sector's reaction is statistically significant, not just large
- The significant reaction moves in the direction the event type would predict

A precedent that fails any of these is discarded. On some events, everything proposed fails, and the report says so plainly rather than filling the section with weak evidence. This is the same discipline applied to the AI's language: when there is only one genuine reason a precedent set is strong or weak, the system says that once, instead of writing several notes that restate it.

## Stack

Python, pandas, numpy, yfinance for the engine. Supabase (PostgreSQL) for storage. GitHub Actions for scheduling. Anthropic's API for event detection, precedent research, and analysis. React, reading directly from Supabase, for the frontend, deployed on Vercel.

## Cost

Detection runs on Haiku throughout. A full run, including precedent research and analysis for every detected event, costs roughly a cent. At twice-daily detection plus the daily maturation job, the entire system runs for well under a dollar a month.

## What this is not

Aftershock does not predict markets and does not give investment advice, a disclaimer that appears on every report it produces. It measures what happened in comparable past events and states plainly when the comparison is weak. It is a demonstration of event-study methodology, automated precedent research, and validation discipline, not a trading signal.
