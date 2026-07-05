"""Aftershock — event-study engine (pipeline version).
Called once per event by run_pipeline.py. Returns (record, top_fields)
instead of writing a file. Numbers are computed here; prose comes from NARRATIVE.
"""

import numpy as np
import pandas as pd
import yfinance as yf


# ---------- helpers ----------
def tstat(series):
    s = series.dropna()
    if len(s) < 2 or s.std(ddof=1) == 0:
        return 0.0
    return float(s.mean() / (s.std(ddof=1) / np.sqrt(len(s))))


def win_bounds(pos, start, end, n):
    return max(pos + start, 0), min(pos + end + 1, n)


def phase_summary(days, path):
    if not path:
        return {"peak_pct": None, "peak_day": None, "reverted_by_day": None}
    peak_i = max(range(len(path)), key=lambda i: abs(path[i]))
    peak_val = path[peak_i]
    reverted = next((days[i] for i in range(peak_i, len(path))
                     if abs(path[i]) < abs(peak_val) / 2), None)
    return {"peak_pct": f"{peak_val:+.1f}%", "peak_day": days[peak_i],
            "reverted_by_day": reverted}


# ---------- main ----------
def run(EVENT, BASKETS, COMPANY_INFO, NARRATIVE):
    bench = EVENT["benchmark"]
    tickers = sorted({t for ms in BASKETS.values() for t in ms})

    prices = yf.download(tickers + [bench], start=EVENT["download_start"],
                         end=EVENT["download_end"], auto_adjust=True)["Close"]
    rets = prices.pct_change().dropna()
    ar = rets[tickers].sub(rets[bench], axis=0)          # market-adjusted

    pos = int(rets.index.searchsorted(pd.Timestamp(EVENT["information_date"])))
    n = len(rets)
    s0, s1 = win_bounds(pos, *EVENT["snap_window"], n)
    f0, f1 = win_bounds(pos, *EVENT["full_window"], n)
    days = [i - pos for i in range(f0, f1)]

    reaction, timeseries, phases = [], [], []
    for sector, members in BASKETS.items():
        have = [t for t in members if t in ar.columns]
        if not have:
            continue
        basket_ar = ar[have].mean(axis=1)
        snap = basket_ar.iloc[s0:s1]
        car = float(snap.sum() * 100)
        t = round(tstat(snap), 2)
        path = (basket_ar.iloc[f0:f1].cumsum() * 100).round(2).tolist()
        reaction.append({
            "sector": sector, "tickers": ", ".join(have),
            "pct": f"{car:+.1f}%", "significant": abs(t) >= 2.0,
            "t_stat": t, "tone": "gain" if car >= 0 else "loss",
        })
        timeseries.append({"sector": sector, "car_path": path})
        ph = phase_summary(days, path); ph["sector"] = sector
        phases.append(ph)

    companies_affected = []
    for sector, members in BASKETS.items():
        for tk in members:
            if tk not in ar.columns:
                continue
            cmove = float(ar[tk].iloc[s0:s1].sum() * 100)
            name, role = COMPANY_INFO.get(tk, (tk, ""))
            companies_affected.append({
                "ticker": tk, "name": name, "sector": sector, "role": role,
                "move_pct": f"{cmove:+.1f}%",
                "tone": "gain" if cmove >= 0 else "loss",
            })

    bench_ret = float((rets[bench].iloc[f0:f1] + 1).prod() - 1) * 100
    key_metrics = list(NARRATIVE.get("key_metrics", [])) + [
        {"label": "S&P 500", "value": f"{bench_ret:+.1f}%",
         "tone": "loss" if bench_ret < 0 else "gain"}
    ]

    record = {
        "event": {
            "name": EVENT["name"], "type_label": EVENT["type_label"],
            "information_date": EVENT["information_date"],
            "announcement_date": EVENT.get("announcement_date", ""),
            "key_metrics": key_metrics,
        },
        "location": EVENT.get("location", {}),
        "sources": NARRATIVE.get("sources", []),
        "status": NARRATIVE.get("status", "confirmed"),
        "recency": NARRATIVE.get("recency", "settled"),
        "summary": NARRATIVE.get("summary", ""),
        "timeline": NARRATIVE.get("timeline", []),
        "reaction": reaction,
        "lasting_finding": NARRATIVE.get("lasting_finding", ""),
        "timeseries": {"days": days, "series": timeseries,
                       "markers": NARRATIVE.get("markers", [])},
        "phases": phases,
        "historical": NARRATIVE.get("historical", []),
        "historical_precedents": NARRATIVE.get("historical_precedents", []),
        "companies_affected": companies_affected,
        "companies_in_news": NARRATIVE.get("companies_in_news", []),
        "confidence": NARRATIVE.get("confidence", ""),
        "disclaimer": "This tool informs your decision. It does not give investment advice.",
    }

    top = {
        "event_id": EVENT["event_id"], "name": EVENT["name"],
        "type_label": EVENT["type_label"],
        "information_date": EVENT["information_date"],
        "status": record["status"], "recency": record["recency"],
        "region": EVENT.get("region", ""),
    }

    # smell test — shows up in the GitHub Actions log so you can verify a run
    print(f"  {EVENT['event_id']}: t0={rets.index[pos].date()} benchmark={bench_ret:+.1f}%")
    for r in reaction:
        flag = "SIG" if r["significant"] else "n.s."
        print(f"    {r['sector']:22s} {r['pct']:>7s} t={r['t_stat']:>5} {flag}")

    return record, top
