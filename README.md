# Aftershock

Aftershock measures how geopolitical events move financial markets.

It detects significant events from live news, researches historical precedents for each event, measures those precedents with a real event-study engine, and rejects any measurement that fails statistical validation before it reaches the site. The system runs unattended on a schedule.

An early build anchored a Strait of Hormuz closure to its announcement date and got the wrong answer, because markets had already repriced days earlier. Most of the engineering here exists to stop that class of mistake from reaching a reader.

**Live site:** https://aftershock-site-five.vercel.app/
**Frontend repo:** https://github.com/mutazhammad/aftershock_site

This repository contains the backend: the event-study engine, event-detection and precedent-research pipeline, diagnostics layer, and scheduled jobs that keep the database current.

## What it does

When a geopolitical event breaks, there is no market reaction to measure yet. The reaction has not happened.

Rather than guess, Aftershock researches historical events with the same market transmission mechanism, measures each one with the same event-study engine used everywhere else, and keeps only those whose measurements are statistically defensible.

The event is published immediately, then re-measured as trading days pass:

- **Breaking:** published immediately with validated historical context
- **Developing:** upgraded after ten trading days, as the market reaction becomes observable
- **Settled:** upgraded after thirty-five trading days, once the full reaction window closes

Settled events then become available as precedents for future breaking events. The archive builds itself over time.

## The core methodological decision

Every measurement is anchored to the **information date**: the first trading day on which markets could plausibly have known about an event, rather than the date of an official announcement.

These dates are often different, and the gap matters.

An early build anchored a Strait of Hormuz closure to its announcement date. The results looked clean. **They were wrong.** Markets had already repriced days earlier, when the news first broke. Moving the anchor changed which sectors showed a significant reaction and which did not.

This is not a quirk of one event.

An abnormal return is a descriptive figure. It tells us how prices moved relative to a statistical benchmark around a particular window. Reading it as something the event *caused* requires the event date to be known precisely and the event to have been unanticipated.

Get the date wrong and the number is still a number. It simply no longer means what it appears to mean.

## Validation, not just detection

Finding a plausible-sounding historical parallel is easy. Most of the engineering here went into **rejecting bad ones**.

A candidate precedent survives only if:

- The research pass is confident, rather than approximate, about its information date
- The event postdates 2005 and has a complete post-event trading window
- At least one sector reaction is **statistically significant**, rather than merely large
- That significant reaction moves in the direction the event type would predict

### Why the validation bar changed

An earlier version of this gate was too permissive. It required only that the reaction point in the expected direction and that some sector move more than two percent.

That admitted precedents where every sector result was statistically insignificant. A report could therefore show a confident-looking sector average built entirely on noise.

The bar was raised, and validated precedent counts fell. That was the right outcome.

A short list that clears a real statistical bar is better evidence than a long list that clears a low one.

When everything proposed fails, the report says so plainly instead of filling the section with weak evidence.

## Diagnostics before interpretation

Passing validation means a measurement is statistically real. It does **not** mean it can automatically be interpreted as having been caused by the event.

Three checks run before any interpretation is offered.

### 1. Date basis

Was the precedent precisely dated and unanticipated?

This is a precondition for making a causal reading at all.

### 2. Concentration

Each sector figure is an average across a basket of named stocks.

When one constituent dominates the movement, the figure describes that company rather than the sector. Any significant sector where a single ticker accounts for **60% or more of total basket movement** is flagged.

The concentration measure is computed directly from per-ticker returns.

### 3. Confounding windows

Each event uses a window running from **five days before the event to thirty days after**.

If another major development landed inside that window, the reaction cannot necessarily be attributed to the event being studied.

Each precedent's window is checked individually rather than being covered by a blanket caveat.

### Separating diagnostics from interpretation

Separating diagnostics from interpretation was a deliberate fix.

One section originally tried to do two jobs at once:

1. Judge whether the numbers could be trusted
2. Explain what those numbers meant

Given a quota to fill and two jobs to do, it produced five notes on a single event that all restated the same underlying point.

With the trust question handled by computed diagnostics, the interpretation section could shrink to its actual job:

**What has materially changed between the precedent conditions and today?**

## Architecture

```text
Live news (Currents API)
        │
        ▼
Event detection (Anthropic, Haiku)
        │
        ▼
Per-event precedent research
        │
        ▼
Event-study engine (pandas, yfinance)
        │
        ▼
Validation gates
  significance, plausibility, date confidence
        │
        ▼
Diagnostics layer
  concentration, confounding, anticipation
        │
        ▼
Supabase (PostgreSQL)  ◀──────┐
        │                     │
        ▼                     │
React frontend                │
                              │
mature.py re-measures aging   │
events and writes them back ──┘
Settled events then serve as
precedents for future events
```

Two tables carry the system.

### `events`

The live feed containing detected events. Events arrive as breaking and mature over time.

### `curated_precedents`

The validated historical library. It is populated automatically as:

- Historical precedents pass validation
- Feed events themselves mature into settled records

Cached precedents are re-validated against the current validation bar whenever they are reused. Tightening the validation gate can therefore retroactively exclude entries that were measured under looser rules.

### Automated jobs

Three scheduled GitHub Actions jobs run the system unattended:

| Job | What it does |
|---|---|
| `detect.py` | Finds significant current events, researches and validates their precedents, runs diagnostics, and publishes to the feed |
| `mature.py` | Re-measures aging feed events, upgrading them from breaking to developing to settled |
| `run_pipeline.py` | Maintains the hand-curated event set that seeded the precedent library |

## What each report contains

- Measured figures with a significance test on every reported move
- Specific companies exposed, and how each is exposed
- Historical precedents, each independently measured and validated rather than merely cited
- Average sector reactions across those precedents
- Consistency of the precedent pattern, rather than just its average
- Market fear (VIX) before and after
- Realized volatility before and after
- Diagnostics assessing whether the figures can be interpreted causally
- An assessment of what has changed since the precedents that could alter the response now

## Stack

- **Python, pandas, NumPy, yfinance:** event-study engine
- **Supabase (PostgreSQL):** data storage
- **GitHub Actions:** scheduled automation
- **Anthropic API:** event detection, precedent research, and analysis
- **React:** frontend
- **Vercel:** frontend deployment

The React frontend reads directly from Supabase. There is no backend server between the frontend and the database.

## Cost

Everything runs on Haiku.

A full run, including precedent research, diagnostics, and analysis for every detected event, costs roughly one cent.

With twice-daily detection and the daily maturation job, the entire system runs for well under a dollar per month.

## What this is not

Aftershock does not predict markets and does not give investment advice. A disclaimer appears on every report it produces.

It measures what happened in comparable past events, checks whether those measurements can be trusted, and states plainly when the comparison is weak. It is not a trading signal.
