# Aftershock

Aftershock measures how geopolitical events move financial markets. It detects significant events from live news, researches historical precedents for each one, measures those precedents with a real event-study engine, and rejects any measurement that fails statistical validation before it reaches the site. The system runs unattended on a schedule.

**Live site:** (https://aftershock-site-five.vercel.app/)
**Frontend repo:** https://github.com/mutazhammad/aftershock_site

This repo is the backend: the event-study engine, the detection and precedent-research pipeline, the diagnostics layer, and the scheduled jobs that keep the database current.

## What it does

A geopolitical event breaks. There is no market reaction to measure yet, because the reaction has not happened. Rather than guess, the system researches historical events with the same market transmission mechanism, measures each one with the same engine used everywhere else, and keeps only those whose measurements are statistically defensible. The event publishes immediately as **breaking**, carrying that validated historical context. As trading days pass, a separate job re-measures the event itself, upgrading it to **developing** at ten days and **settled** at thirty-five, once the full reaction window closes. Settled events then become available as precedents for the next breaking event. The archive builds itself.

## The core methodological decision

Every measurement is anchored to the **information date**, the first trading day markets could plausibly have known about an event, rather than the date of an official announcement. These are often different days and the gap matters.

An early build anchored a Strait of Hormuz closure to its announcement date. The results looked clean. They were wrong. Markets had already repriced days earlier, when the news first broke. Moving the anchor changed which sectors showed a significant reaction and which did not.

This is not a quirk of one event. An abnormal return is a descriptive figure: it says how prices moved relative to a statistical benchmark around a window. Reading it as something the event *caused* requires the event date to be known precisely and the event to have been unanticipated. Get the date wrong and the number is still a number, it just no longer means what it appears to mean.

## Validation, not just detection

Finding a plausible-sounding historical parallel is easy. Most of the engineering here went into rejecting bad ones. A candidate precedent survives only if:

- The research pass is confident, not approximate, about its information date
- The event postdates 2005 and has a complete post-event trading window
- At least one sector reaction is **statistically significant**, not merely large
- That significant reaction moves in the direction the event type would predict

An earlier version of this gate was too permissive. It asked only that the reaction point the expected way and that some sector move more than two percent. That admitted precedents where every sector result was statistically insignificant, so a report could show a confident-looking sector average built entirely on noise. The bar was raised and validated precedent counts fell, which was the right outcome. A short list that cleared a real bar is better evidence than a long list that cleared a low one.

When everything proposed fails, the report says so plainly instead of filling the section with weak evidence.

## Diagnostics before interpretation

Passing validation means a measurement is statistically real. It does not mean it can be read as caused by the event. Three checks run before any interpretation is offered:

**Date basis.** Was the precedent precisely dated and unanticipated, the precondition for a causal reading at all.

**Concentration.** Each sector figure is an average across a basket of named stocks. When one constituent dominates the movement, the figure describes that company rather than the sector. Any significant sector where a single ticker accounts for 60 percent or more of total basket movement is flagged, computed directly from per-ticker returns.

**Confounding windows.** A window runs from five days before an event to thirty days after. If another major development landed inside it, the reaction cannot be attributed to the event alone. Each precedent's window is checked individually rather than covered by a blanket caveat.

Separating this from interpretation was a deliberate fix. One section originally tried to do both jobs, judge whether the numbers could be trusted and explain what they meant. Given a quota to fill and two jobs to do, it produced five notes on a single event that all restated the same underlying point. With the trust question handled by computed diagnostics, the interpretation section shrank to its real job: what has materially changed between the precedent conditions and today.

## Architecture

```
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
Supabase (PostgreSQL)
        │
        ▼
React frontend, reading directly from Supabase, no backend server
```

Two tables carry the system. `events` is the live feed: detected events, breaking on arrival, maturing over time. `curated_precedents` is the validated historical library, populated automatically as precedents pass validation and as feed events themselves mature into settled records. Cached precedents are re-validated against the current bar on reuse, so tightening the gate retroactively excludes entries measured under looser rules.

Three scheduled GitHub Actions jobs run this unattended:

| Job | What it does |
|---|---|
| `detect.py` | Finds significant current events, researches and validates their precedents, runs diagnostics, publishes to the feed |
| `mature.py` | Re-measures aging feed events, upgrading breaking to developing to settled |
| `run_pipeline.py` | Maintains the hand-curated event set that seeded the precedent library |

## What each report contains

Measured figures with a significance test on every reported move. The specific companies exposed and how each is exposed. Historical precedents, each independently measured and validated rather than merely cited. What those precedents' sector reactions averaged, and how consistent that pattern actually was. Market fear (VIX) and realized volatility before and after. Diagnostics on whether those figures can be read causally. And an assessment of what has changed since the precedents that would alter the response now.

## Stack

Python, pandas, numpy, yfinance for the engine. Supabase (PostgreSQL) for storage. GitHub Actions for scheduling. Anthropic's API for detection, precedent research, and analysis. React reading directly from Supabase, deployed on Vercel.

## Cost

Everything runs on Haiku. A full run, including precedent research, diagnostics, and analysis for every detected event, costs roughly a cent. With twice-daily detection and the daily maturation job, the whole system runs for well under a dollar a month.

## What this is not

Aftershock does not predict markets and does not give investment advice, a disclaimer that appears on every report it produces. It measures what happened in comparable past events, checks whether those measurements can be trusted, and states plainly when the comparison is weak. It is a demonstration of event-study methodology, automated precedent research, and validation discipline, not a trading signal.
