"""Aftershock — event-study engine (pipeline version).
Called once per event by run_pipeline.py. Returns (record, top_fields)
instead of writing a file. Numbers are computed here; prose comes from NARRATIVE.
"""

import numpy as np
import pandas as pd
import yfinance as yf


# ---------- significance ----------
def car_tstat(basket_ar, est_start, est_end, win_start, win_end):
    """Test the cumulative abnormal return against the standard deviation of abnormal
    returns over the ESTIMATION window, not the handful of days inside the event window.

    Testing an 8-day window against its own variance has almost no statistical power:
    a genuine 12% move lands at t=1.7 simply because n=8. The standard event-study
    approach benchmarks the CAR against normal-period volatility instead, which is what
    the ~250 days of pre-event data are for.

    CAR over N days has standard error sigma_AR * sqrt(N), where sigma_AR is the daily
    abnormal-return standard deviation estimated over the clean pre-event period.
    """
    est = basket_ar.iloc[est_start:est_end].dropna()
    win = basket_ar.iloc[win_start:win_end].dropna()

    if len(win) == 0:
        return 0.0, 0.0
    if len(est) < 30:
        # not enough clean history to estimate normal volatility; fall back to the
        # in-window test rather than returning a falsely confident number
        s = win
        if len(s) < 2 or s.std(ddof=1) == 0:
            return 0.0, 0.0
        return float(s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))), 0.0

    sigma_daily = float(est.std(ddof=1))
    if sigma_daily == 0:
        return 0.0, 0.0

    car = float(win.sum())
    se_car = sigma_daily * np.sqrt(len(win))
    return float(car / se_car), sigma_daily


def significance_label(t):
    """Two tiers. |t| >= 1.96 is the conventional 5% level. |t| >= 1.65 is the 10%
    level, reported separately as directional support rather than collapsed into
    'not significant', since a large move that clears 10% but not 5% is a different
    thing from noise."""
    a = abs(t)
    if a >= 1.96:
        return "significant", True
    if a >= 1.645:
        return "directional", False
    return "not_significant", False


# ---------- helpers ----------
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


def volatility_analysis(rets, vix_series, pos, baskets, ar):
    """Measure how volatility changed after the event.
    Returns VIX move (market-wide fear) and per-sector realized-volatility ratios."""
    PRE, POST = 20, 20   # 20 trading days before vs after

    out = {"vix": None, "sectors": []}

    # --- VIX: market-wide fear ---
    if vix_series is not None:
        vix_clean = vix_series.dropna()
        if len(vix_clean) > pos + 5:
            pre_slice = vix_series.iloc[max(pos - PRE, 0):pos].dropna()
            post_slice = vix_series.iloc[pos:min(pos + POST, len(vix_series))].dropna()
            if len(pre_slice) >= 3 and len(post_slice) >= 3:
                pre_vix = float(pre_slice.mean())
                post_vix = float(post_slice.mean())
                peak_vix = float(post_slice.max())
                if pre_vix > 0:
                    pct = (post_vix / pre_vix - 1) * 100
                    out["vix"] = {
                        "before": round(pre_vix, 1),
                        "after": round(post_vix, 1),
                        "peak": round(peak_vix, 1),
                        "change_pct": f"{pct:+.0f}%",
                        "spiked": bool(pct >= 15),
                        "tone": "loss" if pct > 0 else "gain",
                        "plain": ("Market fear spiked" if pct >= 15
                                  else "Market fear rose modestly" if pct > 0
                                  else "Market fear eased"),
                    }

    # --- Realized volatility per sector: were these stocks jumpier after? ---
    for sector, members in baskets.items():
        have = [t for t in members if t in ar.columns]
        if not have:
            continue
        basket_ret = rets[have].mean(axis=1)
        pre = basket_ret.iloc[max(pos - PRE, 0):pos].dropna()
        post = basket_ret.iloc[pos:min(pos + POST, len(basket_ret))].dropna()
        if len(pre) < 5 or len(post) < 5:
            continue
        pre_vol = float(pre.std(ddof=1)) * (252 ** 0.5) * 100    # annualized %
        post_vol = float(post.std(ddof=1)) * (252 ** 0.5) * 100
        if pre_vol <= 0:
            continue
        ratio = post_vol / pre_vol
        out["sectors"].append({
            "sector": sector,
            "vol_before": f"{pre_vol:.0f}%",
            "vol_after": f"{post_vol:.0f}%",
            "ratio": round(ratio, 2),
            "more_volatile": bool(ratio >= 1.25),
            "plain": (f"{ratio:.1f}x more volatile after" if ratio >= 1.05
                      else f"{1/ratio:.1f}x calmer after" if ratio <= 0.95
                      else "volatility roughly unchanged"),
        })

    return out


# ---------- main ----------
def run(EVENT, BASKETS, COMPANY_INFO, NARRATIVE):
    bench = EVENT["benchmark"]
    tickers = sorted({t for ms in BASKETS.values() for t in ms})

    prices = yf.download(tickers + [bench, "^VIX"], start=EVENT["download_start"],
                         end=EVENT["download_end"], auto_adjust=True)["Close"]
    rets = prices[tickers + [bench]].pct_change().dropna()
    ar = rets[tickers].sub(rets[bench], axis=0)          # market-adjusted

    # VIX level series (the fear index itself, not its returns), aligned to trading days
    vix_series = prices["^VIX"].reindex(rets.index) if "^VIX" in prices.columns else None

    pos = int(rets.index.searchsorted(pd.Timestamp(EVENT["information_date"])))
    n = len(rets)
    s0, s1 = win_bounds(pos, *EVENT["snap_window"], n)
    f0, f1 = win_bounds(pos, *EVENT["full_window"], n)
    days = [i - pos for i in range(f0, f1)]

    # ESTIMATION WINDOW: clean pre-event period used to estimate normal volatility.
    # Ends 10 trading days before the event so any early leakage does not contaminate
    # the baseline. Runs back up to 250 trading days, roughly a year.
    est_end = max(pos - 10, 0)
    est_start = max(est_end - 250, 0)
    est_len = est_end - est_start

    reaction, timeseries, phases = [], [], []
    for sector, members in BASKETS.items():
        have = [t for t in members if t in ar.columns]
        if not have:
            continue
        basket_ar = ar[have].mean(axis=1)
        snap = basket_ar.iloc[s0:s1]
        car = float(snap.sum() * 100)

        t, sigma_daily = car_tstat(basket_ar, est_start, est_end, s0, s1)
        t = round(t, 2)
        label, is_sig = significance_label(t)

        path = (basket_ar.iloc[f0:f1].cumsum() * 100).round(2).tolist()
        reaction.append({
            "sector": sector, "tickers": ", ".join(have),
            "pct": f"{car:+.1f}%",
            "significant": is_sig,
            "significance": label,          # "significant" | "directional" | "not_significant"
            "t_stat": t,
            "normal_vol_pct": (round(sigma_daily * (252 ** 0.5) * 100, 1)
                               if sigma_daily else None),
            "tone": "gain" if car >= 0 else "loss",
        })
        timeseries.append({"sector": sector, "car_path": path})
        ph = phase_summary(days, path); ph["sector"] = sector
        phases.append(ph)

    # volatility analysis
    vol = volatility_analysis(rets, vix_series, pos, BASKETS, ar)

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
    if vol.get("vix"):
        key_metrics.append({"label": "VIX (fear index)",
                            "value": vol["vix"]["change_pct"],
                            "tone": vol["vix"]["tone"]})

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
        "volatility": vol,
        "measurement": {
            "estimation_days": est_len,
            "window_days": s1 - s0,
            "method": ("CAR tested against abnormal-return volatility estimated over the "
                       "pre-event window, ending 10 trading days before the event."),
        },
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
    print(f"  {EVENT['event_id']}: t0={rets.index[pos].date()} benchmark={bench_ret:+.1f}% "
          f"(estimation window {est_len}d)")
    for r in reaction:
        flag = {"significant": "SIG", "directional": "DIR", "not_significant": "n.s."}[r["significance"]]
        print(f"    {r['sector']:22s} {r['pct']:>7s} t={r['t_stat']:>5} {flag}")
    if vol.get("vix"):
        v = vol["vix"]
        print(f"    VIX {v['before']} -> {v['after']} ({v['change_pct']}) peak {v['peak']}")
    for s in vol.get("sectors", [])[:3]:
        print(f"    vol {s['sector']:22s} {s['ratio']}x  {s['plain']}")

    return record, top
