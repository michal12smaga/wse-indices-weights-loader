from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
TRADING_DAYS = 252
BASE_ADV_MIN = 1_000_000.0
DELIST_MISSING_DAYS = 5
DELIST_PENALTY = -0.30
START = pd.Timestamp("2008-01-01")
END = pd.Timestamp("2024-01-24")
SPLITS = {
    "train": ("2008-01-01", "2014-12-31"),
    "validation": ("2015-01-01", "2018-12-31"),
    "oos": ("2019-01-01", "2024-01-24"),
}
MULTIPLE_TESTS = 14


def norm_symbol(x: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(x).upper())


def load_universe() -> tuple[pd.DataFrame, set[str]]:
    p = Path("datasets/historical/wse_complete_historical_20250916.csv")
    u = pd.read_csv(p)
    u = u[u["Index_Name"].astype(str).str.upper().eq("WIG")].copy()
    u["date"] = pd.to_datetime(u["Date"], format="%Y_%m_%d", errors="coerce")
    u["ticker"] = u["Company_Name"].map(norm_symbol)
    u = u.dropna(subset=["date"])
    u = u[(u["date"] <= END) & (u["date"] >= pd.Timestamp("2007-01-01"))]
    names = set(u["ticker"].dropna().astype(str))
    return u, names


def load_prices(keep: set[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    files = sorted(Path("research_data/gpw_ohlcv").glob("*.csv"))
    frames = []
    for f in files:
        try:
            year = int(f.stem)
        except ValueError:
            continue
        if year < 2006 or year > 2024:
            continue
        df = pd.read_csv(
            f,
            dtype={"ticker": "string", "open": "float64", "high": "float64",
                   "low": "float64", "close": "float64", "volume": "float64"},
            parse_dates=["date"],
        )
        df["ticker"] = df["ticker"].map(norm_symbol)
        df = df[df["ticker"].isin(keep | {"WIG20", "WIG", "MWIG40", "SWIG80"})]
        frames.append(df[["ticker", "date", "open", "high", "low", "close", "volume"]])

    raw = pd.concat(frames, ignore_index=True)
    raw = raw.sort_values(["date", "ticker"])
    duplicates = int(raw.duplicated(["date", "ticker"]).sum())
    raw = raw.drop_duplicates(["date", "ticker"], keep="last")
    raw = raw[(raw["date"] >= pd.Timestamp("2006-01-01")) & (raw["date"] <= END)]

    bad_price_rows = int(((raw["close"] <= 0) | ~np.isfinite(raw["close"])).sum())
    zero_volume_rows = int((raw["volume"].fillna(0) <= 0).sum())

    close = raw.pivot(index="date", columns="ticker", values="close").sort_index()
    open_ = raw.pivot(index="date", columns="ticker", values="open").reindex(close.index)
    volume = raw.pivot(index="date", columns="ticker", values="volume").reindex(close.index)

    rets = close.pct_change(fill_method=None)
    outlier_returns = int((rets.abs() > 1.0).sum().sum())
    stacked = rets.stack().dropna()
    largest_abs = stacked.abs().nlargest(20)
    largest_abs_details = []
    for (dt, ticker), _ in largest_abs.items():
        largest_abs_details.append({
            "date": str(pd.Timestamp(dt).date()),
            "ticker": str(ticker),
            "return": float(stacked.loc[(dt, ticker)]),
        })

    audit = {
        "rows_loaded": int(len(raw)),
        "unique_tickers_loaded": int(raw["ticker"].nunique()),
        "first_date": str(raw["date"].min().date()),
        "last_date": str(raw["date"].max().date()),
        "duplicate_date_ticker_rows": duplicates,
        "bad_price_rows": bad_price_rows,
        "zero_or_missing_volume_rows": zero_volume_rows,
        "abs_daily_return_gt_100pct": outlier_returns,
        "largest_abs_daily_returns": largest_abs_details,
        "note": "OHLCV has no explicit adjusted-close or dividend field; results are price-return based. WIG20 is used as price-index benchmark.",
    }
    return close, open_, volume, audit


def latest_snapshot_members(universe: pd.DataFrame, signal_date: pd.Timestamp) -> set[str]:
    dates = universe.loc[universe["date"] <= signal_date, "date"]
    if dates.empty:
        return set()
    d = dates.max()
    # use membership only after its effective date; signals are at close and execute next close
    return set(universe.loc[universe["date"].eq(d), "ticker"].astype(str))


def month_ends(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(idx, index=idx)
    return list(s.groupby(idx.to_period("M")).last().values)


def week_ends(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(idx, index=idx)
    return list(s.groupby(idx.to_period("W-FRI")).last().values)


def cost_rate_from_adv(adv: pd.Series) -> pd.Series:
    # one-way all-in friction: brokerage + half-spread + slippage/impact proxy
    out = pd.Series(np.nan, index=adv.index, dtype=float)
    out.loc[adv >= 50_000_000] = 0.0025
    out.loc[(adv >= 10_000_000) & (adv < 50_000_000)] = 0.0035
    out.loc[(adv >= 3_000_000) & (adv < 10_000_000)] = 0.0050
    out.loc[(adv >= 1_000_000) & (adv < 3_000_000)] = 0.0075
    return out


@dataclass
class Target:
    weights: dict[str, float]
    cost_rates: dict[str, float]


def build_targets(
    kind: str,
    close: pd.DataFrame,
    volume: pd.DataFrame,
    universe: pd.DataFrame,
    *,
    mom_lb: int = 252,
    skip: int = 21,
    sma: int = 200,
    rev_lb: int = 5,
    vol_win: int = 120,
) -> dict[pd.Timestamp, Target]:
    dates = month_ends(close.loc[START:END].index)
    if kind == "reversal":
        dates = week_ends(close.loc[START:END].index)

    execution_targets: dict[pd.Timestamp, Target] = {}
    all_dates = close.index

    for sig in dates:
        pos = all_dates.get_indexer([sig])[0]
        if pos < 0 or pos + 1 >= len(all_dates):
            continue
        exec_date = all_dates[pos + 1]
        members = latest_snapshot_members(universe, sig)
        if not members:
            continue
        cols = [c for c in members if c in close.columns]
        if not cols:
            continue

        hist = close.loc[:sig, cols]
        vol_hist = volume.loc[:sig, cols]
        if len(hist) < 260:
            continue

        px = hist.iloc[-1]
        adv = (hist.tail(60) * vol_hist.tail(60)).median(axis=0, skipna=True)
        rates = cost_rate_from_adv(adv)
        eligible = (
            px.notna()
            & (adv >= BASE_ADV_MIN)
            & rates.notna()
            & (hist.tail(60).notna().mean(axis=0) >= 0.90)
        )
        cols_e = list(eligible[eligible].index)
        if len(cols_e) < 10:
            continue

        chosen: list[str] = []
        if kind in {"momentum", "market_filtered_momentum", "mom_lowvol"}:
            if len(hist) <= mom_lb:
                continue
            mom = hist.iloc[-1 - skip] / hist.iloc[-1 - mom_lb] - 1.0
            mom = mom[cols_e].replace([np.inf, -np.inf], np.nan).dropna()
            if kind == "market_filtered_momentum":
                if "WIG20" not in close.columns or len(close.loc[:sig, "WIG20"].dropna()) < sma:
                    continue
                w = close.loc[:sig, "WIG20"].dropna()
                if not (w.iloc[-1] > w.tail(sma).mean()):
                    chosen = []
                else:
                    n = max(5, math.ceil(0.20 * len(mom)))
                    chosen = list(mom.nlargest(n).index)
            elif kind == "mom_lowvol":
                n = max(10, math.ceil(0.30 * len(mom)))
                pre = list(mom.nlargest(n).index)
                rv = hist[pre].pct_change(fill_method=None).tail(vol_win).std()
                n2 = max(5, math.ceil(0.50 * len(rv.dropna())))
                chosen = list(rv.nsmallest(n2).index)
            else:
                n = max(5, math.ceil(0.20 * len(mom)))
                chosen = list(mom.nlargest(n).index)

        elif kind == "trend":
            if len(hist) < max(sma, mom_lb) + 2:
                continue
            ma = hist[cols_e].tail(sma).mean()
            mom = hist[cols_e].iloc[-1] / hist[cols_e].iloc[-1 - mom_lb] - 1.0
            mask = (hist[cols_e].iloc[-1] > ma) & (mom > 0)
            chosen = list(mask[mask].index)

        elif kind == "lowvol":
            rv = hist[cols_e].pct_change(fill_method=None).tail(vol_win).std()
            rv = rv.dropna()
            n = max(5, math.ceil(0.20 * len(rv)))
            chosen = list(rv.nsmallest(n).index)

        elif kind == "reversal":
            if len(hist) <= rev_lb + 1:
                continue
            rr = hist[cols_e].iloc[-1] / hist[cols_e].iloc[-1 - rev_lb] - 1.0
            rr = rr.dropna()
            n = max(5, math.ceil(0.20 * len(rr)))
            chosen = list(rr.nsmallest(n).index)

        elif kind == "equal_weight_universe":
            chosen = cols_e
        else:
            raise ValueError(kind)

        if chosen:
            w = 1.0 / len(chosen)
            weights = {c: w for c in chosen}
        else:
            weights = {}

        cr = {c: float(rates.get(c, np.nan)) for c in (set(chosen) | set(cols_e)) if np.isfinite(rates.get(c, np.nan))}
        execution_targets[pd.Timestamp(exec_date)] = Target(weights, cr)

    return execution_targets


def simulate(
    close: pd.DataFrame,
    targets: dict[pd.Timestamp, Target],
    cost_mult: float = 1.0,
) -> tuple[pd.Series, dict]:
    idx = close.loc[START:END].index
    rets = close.pct_change(fill_method=None).reindex(idx)

    current: dict[str, float] = {}
    miss = defaultdict(int)
    daily = []
    turnover_events = []
    trade_count = 0
    cost_paid = 0.0
    exposure_obs = []

    for d in idx:
        port_r = 0.0
        penalty = 0.0
        if current:
            dayret = rets.loc[d]
            for a, w in list(current.items()):
                r = dayret.get(a, np.nan)
                if pd.notna(r) and np.isfinite(r):
                    miss[a] = 0
                    port_r += w * float(r)
                else:
                    miss[a] += 1
                    if miss[a] == DELIST_MISSING_DAYS:
                        penalty += w * DELIST_PENALTY
                        current[a] = 0.0

            port_r += penalty
            # drift weights after returns; missing assets carried unless penalized
            denom = max(1e-12, 1.0 + port_r)
            for a in list(current):
                if current[a] <= 0:
                    del current[a]
                    continue
                r = dayret.get(a, np.nan)
                rr = float(r) if pd.notna(r) and np.isfinite(r) else 0.0
                current[a] = current[a] * (1.0 + rr) / denom

        # execute target at this day's close; new target earns from next session onward
        if d in targets:
            t = targets[d]
            assets = set(current) | set(t.weights)
            turnover = 0.0
            c = 0.0
            for a in assets:
                old = current.get(a, 0.0)
                new = t.weights.get(a, 0.0)
                delta = abs(new - old)
                turnover += delta
                if delta > 1e-8:
                    trade_count += 1
                rate = t.cost_rates.get(a, 0.0050)
                c += delta * rate * cost_mult
            port_r -= c
            cost_paid += c
            turnover_events.append(turnover)
            current = dict(t.weights)
            miss = defaultdict(int)

        daily.append(port_r)
        exposure_obs.append(sum(current.values()))

    s = pd.Series(daily, index=idx, name="return")
    stats = {
        "annualized_turnover": float(np.mean(turnover_events) * len(turnover_events) / max(1, len(idx)) * TRADING_DAYS) if turnover_events else 0.0,
        "mean_rebalance_turnover": float(np.mean(turnover_events)) if turnover_events else 0.0,
        "rebalances": len(turnover_events),
        "trade_legs": int(trade_count),
        "total_cost_fraction_of_initial_capital": float(cost_paid),
        "average_exposure": float(np.mean(exposure_obs)) if exposure_obs else 0.0,
    }
    return s, stats


def max_drawdown_stats(r: pd.Series) -> tuple[float, float, int]:
    eq = (1 + r.fillna(0)).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1
    maxdd = float(dd.min()) if len(dd) else np.nan
    avgdd = float(dd[dd < 0].mean()) if (dd < 0).any() else 0.0
    cur = longest = 0
    for x in (dd < 0).values:
        if x:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return maxdd, avgdd, int(longest)


def metrics(r: pd.Series, bench: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) == 0:
        return {}
    total = float((1 + r).prod() - 1)
    years = len(r) / TRADING_DAYS
    cagr = float((1 + total) ** (1 / years) - 1) if total > -1 and years > 0 else -1.0
    vol = float(r.std(ddof=1) * math.sqrt(TRADING_DAYS))
    mean_ann = float(r.mean() * TRADING_DAYS)
    sharpe = mean_ann / vol if vol > 0 else np.nan
    downside = float(np.sqrt((np.minimum(r, 0) ** 2).mean()) * math.sqrt(TRADING_DAYS))
    sortino = mean_ann / downside if downside > 0 else np.nan
    maxdd, avgdd, dd_dur = max_drawdown_stats(r)
    calmar = cagr / abs(maxdd) if maxdd < 0 else np.nan
    pos = r[r > 0].sum()
    neg = r[r < 0].sum()
    profit_factor = float(pos / abs(neg)) if neg < 0 else np.nan

    monthly = (1 + r).resample("ME").prod() - 1
    annual = (1 + r).resample("YE").prod() - 1
    var5 = float(r.quantile(0.05))
    es5 = float(r[r <= var5].mean()) if (r <= var5).any() else np.nan

    out = {
        "n_days": int(len(r)),
        "total_return": total,
        "cagr": cagr,
        "ann_vol": vol,
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "profit_factor_daily": profit_factor,
        "win_rate_daily": float((r > 0).mean()),
        "avg_daily_return": float(r.mean()),
        "median_daily_return": float(r.median()),
        "max_drawdown": maxdd,
        "average_drawdown": avgdd,
        "max_drawdown_duration_sessions": dd_dur,
        "worst_month": float(monthly.min()) if len(monthly) else np.nan,
        "worst_year": float(annual.min()) if len(annual) else np.nan,
        "downside_deviation_ann": downside,
        "var_95_daily": var5,
        "expected_shortfall_95_daily": es5,
        "skew": float(r.skew()),
        "kurtosis_excess": float(r.kurt()),
    }
    if bench is not None:
        b = bench.reindex(r.index).fillna(0)
        if b.var() > 0:
            beta = float(np.cov(r, b, ddof=1)[0, 1] / np.var(b, ddof=1))
        else:
            beta = np.nan
        active = r - b
        irden = active.std(ddof=1) * math.sqrt(TRADING_DAYS)
        out["beta_vs_wig20"] = beta
        out["alpha_ann_vs_wig20"] = float((r.mean() - beta * b.mean()) * TRADING_DAYS) if np.isfinite(beta) else np.nan
        out["information_ratio_vs_wig20"] = float(active.mean() * TRADING_DAYS / irden) if irden > 0 else np.nan
    return out


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def psr_dsr(r: pd.Series, trials: int = MULTIPLE_TESTS) -> dict:
    r = r.dropna()
    n = len(r)
    if n < 50:
        return {"psr_gt_0": np.nan, "dsr_approx": np.nan}
    sr = r.mean() / r.std(ddof=1)
    sk = float(r.skew())
    ku = float(r.kurt() + 3.0)
    denom = math.sqrt(max(1e-12, 1 - sk * sr + ((ku - 1) / 4.0) * sr * sr))
    z0 = sr * math.sqrt(n - 1) / denom
    psr = normal_cdf(z0)

    # Bailey/Lopez de Prado style expected maximum Sharpe under multiple trials.
    gamma = 0.5772156649
    if trials > 1:
        a = math.sqrt(2 * math.log(trials))
        z_exp = (1 - gamma) * a + gamma * (a - (math.log(math.log(trials)) + math.log(4 * math.pi)) / (2 * a))
    else:
        z_exp = 0.0
    sr_std = 1.0 / math.sqrt(max(1, n - 1))
    sr0 = z_exp * sr_std
    z_d = (sr - sr0) * math.sqrt(n - 1) / denom
    return {"psr_gt_0": float(psr), "dsr_approx": float(normal_cdf(z_d)), "trials_assumed": trials}


def segment(r: pd.Series, name: str) -> pd.Series:
    a, b = SPLITS[name]
    return r.loc[a:b]


def yearly_walkforward(r: pd.Series, start_year: int = 2015) -> dict:
    vals = []
    for y, x in r[r.index.year >= start_year].groupby(r[r.index.year >= start_year].index.year):
        m = metrics(x)
        vals.append({"year": int(y), "return": m.get("total_return"), "sharpe": m.get("sharpe"), "max_drawdown": m.get("max_drawdown")})
    sharps = [x["sharpe"] for x in vals if x["sharpe"] is not None and np.isfinite(x["sharpe"])]
    rets = [x["return"] for x in vals if x["return"] is not None and np.isfinite(x["return"])]
    return {
        "windows": vals,
        "median_year_sharpe": float(np.median(sharps)) if sharps else np.nan,
        "positive_year_fraction": float(np.mean(np.array(rets) > 0)) if rets else np.nan,
        "worst_year_return": float(np.min(rets)) if rets else np.nan,
    }


def concentration_stress(r: pd.Series) -> dict:
    r = r.dropna()
    yearly = {}
    for y, x in r.groupby(r.index.year):
        yearly[str(int(y))] = float((1 + x).prod() - 1)

    ex2020 = r[r.index.year != 2020]
    recent_2021_2023 = r[(r.index >= pd.Timestamp("2021-01-01")) & (r.index <= pd.Timestamp("2023-12-31"))]
    post_2020 = r[r.index >= pd.Timestamp("2021-01-01")]

    top_year = None
    if yearly:
        top_year = max(yearly.items(), key=lambda kv: kv[1])

    return {
        "yearly_returns": yearly,
        "best_year": {"year": top_year[0], "return": top_year[1]} if top_year else None,
        "excluding_2020": metrics(ex2020),
        "recent_2021_2023": metrics(recent_2021_2023),
        "post_2020_through_end": metrics(post_2020),
    }


def block_bootstrap_mc(r: pd.Series, n_sims: int = 2000, block: int = 20) -> dict:
    x = r.dropna().values.astype(float)
    n = len(x)
    if n < 100:
        return {}
    rng = np.random.default_rng(SEED)
    cagr, sr, mdd, loss, streaks = [], [], [], [], []
    years = n / TRADING_DAYS
    for _ in range(n_sims):
        arr = []
        while len(arr) < n:
            s = int(rng.integers(0, max(1, n - block + 1)))
            arr.extend(x[s:s + block])
        a = np.asarray(arr[:n])
        eq = np.cumprod(1 + a)
        tot = eq[-1] - 1
        cg = (1 + tot) ** (1 / years) - 1 if tot > -1 else -1
        vv = np.std(a, ddof=1) * math.sqrt(TRADING_DAYS)
        sh = (np.mean(a) * TRADING_DAYS) / vv if vv > 0 else np.nan
        peak = np.maximum.accumulate(eq)
        dd = eq / peak - 1
        run = mx = 0
        for z in a < 0:
            if z:
                run += 1
                mx = max(mx, run)
            else:
                run = 0
        cagr.append(cg); sr.append(sh); mdd.append(float(dd.min())); loss.append(tot < 0); streaks.append(mx)

    def q(a, p): return float(np.nanquantile(np.asarray(a, dtype=float), p))
    return {
        "simulations": n_sims,
        "block_sessions": block,
        "cagr_p05": q(cagr, .05),
        "cagr_median": q(cagr, .50),
        "cagr_p95": q(cagr, .95),
        "sharpe_p05": q(sr, .05),
        "sharpe_median": q(sr, .50),
        "sharpe_p95": q(sr, .95),
        "max_drawdown_p05": q(mdd, .05),
        "max_drawdown_median": q(mdd, .50),
        "max_drawdown_p95": q(mdd, .95),
        "losing_streak_median_sessions": q(streaks, .50),
        "losing_streak_p95_sessions": q(streaks, .95),
        "probability_terminal_loss": float(np.mean(loss)),
    }


def run_strategy(name: str, kind: str, close, volume, universe, **kwargs):
    targets = build_targets(kind, close, volume, universe, **kwargs)
    runs = {}
    execstats = {}
    for cm in [1.0, 1.5, 2.0, 3.0]:
        r, es = simulate(close, targets, cost_mult=cm)
        runs[cm] = r
        execstats[cm] = es
    return targets, runs, execstats


def main():
    outdir = Path("research_results")
    outdir.mkdir(exist_ok=True)

    universe, universe_names = load_universe()
    close, open_, volume, data_audit = load_prices(universe_names)

    if "WIG20" not in close.columns:
        raise RuntimeError("WIG20 benchmark missing from archive")
    benchmark = close["WIG20"].pct_change(fill_method=None).loc[START:END].fillna(0)

    specs = {
        "momentum_12_1": ("momentum", {"mom_lb": 252, "skip": 21}),
        "trend_sma200": ("trend", {"mom_lb": 252, "sma": 200}),
        "reversal_5d": ("reversal", {"rev_lb": 5}),
        "lowvol_120d": ("lowvol", {"vol_win": 120}),
        "momentum_market_filter": ("market_filtered_momentum", {"mom_lb": 252, "skip": 21, "sma": 200}),
        "momentum_lowvol": ("mom_lowvol", {"mom_lb": 252, "skip": 21, "vol_win": 120}),
        "equal_weight_wig": ("equal_weight_universe", {}),
    }

    all_returns = {}
    report = {
        "research_design": {
            "sample": [str(START.date()), str(END.date())],
            "splits": SPLITS,
            "execution": "signal at close t; rebalance at close t+1; new holdings earn returns from t+2 close-to-close",
            "liquidity_filter": f"60-session median PLN turnover >= {BASE_ADV_MIN:,.0f}",
            "cost_model": {
                ">=50m_ADV": "25 bps one-way",
                "10-50m_ADV": "35 bps",
                "3-10m_ADV": "50 bps",
                "1-3m_ADV": "75 bps",
                "stress_multipliers": [1.0, 1.5, 2.0, 3.0],
            },
            "missing_quote_rule": f"after {DELIST_MISSING_DAYS} consecutive missing sessions while held, realize {DELIST_PENALTY:.0%} penalty and move weight to cash",
            "multiple_testing_variants_counted": MULTIPLE_TESTS,
        },
        "data_integrity": data_audit,
        "universe": {
            "wig_snapshot_rows": int(len(universe)),
            "snapshot_dates": int(universe["date"].nunique()),
            "unique_snapshot_company_names": int(universe["ticker"].nunique()),
            "snapshot_first": str(universe["date"].min().date()),
            "snapshot_last": str(universe["date"].max().date()),
            "price_tickers_matching_any_wig_name": int(len(set(close.columns) & universe_names)),
        },
        "benchmark": {},
        "strategies": {},
        "parameter_robustness": {},
    }

    report["benchmark"]["full"] = metrics(benchmark)
    for seg in SPLITS:
        report["benchmark"][seg] = metrics(segment(benchmark, seg))

    for name, (kind, kw) in specs.items():
        targets, runs, ex = run_strategy(name, kind, close, volume, universe, **kw)
        base = runs[1.0]
        all_returns[name] = base
        st = {
            "target_rebalances": len(targets),
            "execution_stats": ex[1.0],
            "full": metrics(base, benchmark),
            "train": metrics(segment(base, "train"), segment(benchmark, "train")),
            "validation": metrics(segment(base, "validation"), segment(benchmark, "validation")),
            "oos": metrics(segment(base, "oos"), segment(benchmark, "oos")),
            "walk_forward_years": yearly_walkforward(base),
            "statistical_validation_oos": psr_dsr(segment(base, "oos")),
            "monte_carlo_oos": block_bootstrap_mc(segment(base, "oos")),
            "concentration_stress_oos": concentration_stress(segment(base, "oos")),
            "cost_stress_oos": {},
        }
        for cm, rr in runs.items():
            st["cost_stress_oos"][str(cm)] = metrics(segment(rr, "oos"), segment(benchmark, "oos"))
        report["strategies"][name] = st

    robustness = {
        "momentum_lookback": [
            ("mom_6_1", "momentum", {"mom_lb": 126, "skip": 21}),
            ("mom_9_1", "momentum", {"mom_lb": 189, "skip": 21}),
            ("mom_12_1", "momentum", {"mom_lb": 252, "skip": 21}),
        ],
        "trend_sma": [
            ("trend_150", "trend", {"mom_lb": 252, "sma": 150}),
            ("trend_200", "trend", {"mom_lb": 252, "sma": 200}),
            ("trend_250", "trend", {"mom_lb": 252, "sma": 250}),
        ],
        "reversal_lookback": [
            ("rev_3", "reversal", {"rev_lb": 3}),
            ("rev_5", "reversal", {"rev_lb": 5}),
            ("rev_10", "reversal", {"rev_lb": 10}),
        ],
        "lowvol_window": [
            ("lv_60", "lowvol", {"vol_win": 60}),
            ("lv_120", "lowvol", {"vol_win": 120}),
            ("lv_180", "lowvol", {"vol_win": 180}),
        ],
    }
    for family, variants in robustness.items():
        arr = []
        for vname, kind, kw in variants:
            _, runs, _ = run_strategy(vname, kind, close, volume, universe, **kw)
            m = metrics(segment(runs[1.0], "oos"), segment(benchmark, "oos"))
            arr.append({"variant": vname, **m})
        report["parameter_robustness"][family] = arr

    # Correlations, drawdown correlations, and equal-weight strategy portfolio for non-benchmark strategies.
    strat_names = [x for x in specs if x != "equal_weight_wig"]
    ret_df = pd.concat([all_returns[n].rename(n) for n in strat_names], axis=1).fillna(0)
    oos_ret = ret_df.loc[SPLITS["oos"][0]:SPLITS["oos"][1]]
    report["portfolio_analysis"] = {
        "oos_return_correlation": oos_ret.corr().round(6).to_dict(),
    }
    dd_df = pd.DataFrame(index=oos_ret.index)
    for c in oos_ret:
        eq = (1 + oos_ret[c]).cumprod()
        dd_df[c] = eq / eq.cummax() - 1
    report["portfolio_analysis"]["oos_drawdown_correlation"] = dd_df.corr().round(6).to_dict()

    combo = oos_ret.mean(axis=1)
    report["portfolio_analysis"]["equal_weight_all_6_oos"] = metrics(combo, segment(benchmark, "oos"))

    # Classification based on falsification evidence, intentionally conservative.
    for name, st in report["strategies"].items():
        if name == "equal_weight_wig":
            st["status"] = "BENCHMARK_CONTROL"
            continue
        o = st["oos"]
        c2 = st["cost_stress_oos"]["2.0"]
        wf = st["walk_forward_years"]
        # family parameter stability
        family = None
        if name.startswith("momentum_12"): family = "momentum_lookback"
        elif name.startswith("trend_"): family = "trend_sma"
        elif name.startswith("reversal_"): family = "reversal_lookback"
        elif name.startswith("lowvol_"): family = "lowvol_window"
        robust_positive = None
        if family:
            vals = report["parameter_robustness"][family]
            robust_positive = sum(v.get("cagr", -1) > 0 for v in vals) >= 2

        reject = (
            o.get("cagr", -1) <= 0
            or c2.get("cagr", -1) <= 0
            or (robust_positive is False)
        )
        strong = (
            not reject
            and o.get("sharpe", -9) > 0.8
            and o.get("max_drawdown", -1) > -0.40
            and wf.get("positive_year_fraction", 0) >= 0.60
            and st["statistical_validation_oos"].get("dsr_approx", 0) >= 0.90
        )
        st["status"] = "PASS" if strong else ("REJECTED" if reject else "WATCH")
        st["classification_inputs"] = {
            "parameter_family_2_of_3_positive_oos_cagr": robust_positive,
            "oos_sharpe_gt_0_8": o.get("sharpe", -9) > 0.8,
            "oos_maxdd_better_than_minus_40pct": o.get("max_drawdown", -1) > -0.40,
            "2x_cost_oos_cagr_positive": c2.get("cagr", -1) > 0,
            "positive_year_fraction_ge_60pct": wf.get("positive_year_fraction", 0) >= 0.60,
            "dsr_approx_ge_90pct": st["statistical_validation_oos"].get("dsr_approx", 0) >= 0.90,
        }

    with open(outdir / "gpw_quant_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=True)

    # Compact comparison CSV
    rows = []
    for name, st in report["strategies"].items():
        for seg in ["train", "validation", "oos"]:
            m = st[seg]
            rows.append({
                "strategy": name, "segment": seg, "status": st.get("status"),
                "cagr": m.get("cagr"), "sharpe": m.get("sharpe"), "sortino": m.get("sortino"),
                "max_drawdown": m.get("max_drawdown"), "ann_vol": m.get("ann_vol"),
                "calmar": m.get("calmar"), "beta_vs_wig20": m.get("beta_vs_wig20"),
            })
    pd.DataFrame(rows).to_csv(outdir / "strategy_metrics.csv", index=False)

    # Equity curves (base costs)
    eq = pd.DataFrame({n: (1 + r.loc[START:END].fillna(0)).cumprod() for n, r in all_returns.items()})
    eq["WIG20"] = (1 + benchmark).cumprod()
    eq.to_csv(outdir / "equity_curves.csv")

    # Human-readable concise report.
    lines = [
        "# GPW Quant Research — automated baseline",
        "",
        f"Sample: {START.date()} to {END.date()}",
        f"Final OOS: {SPLITS['oos'][0]} to {SPLITS['oos'][1]}",
        "",
        "| Strategy | Status | OOS CAGR | OOS Sharpe | OOS MaxDD | 2x cost CAGR | OOS DSR approx |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for name, st in report["strategies"].items():
        if name == "equal_weight_wig":
            continue
        o = st["oos"]; c2 = st["cost_stress_oos"]["2.0"]; d = st["statistical_validation_oos"]
        lines.append(
            f"| {name} | {st['status']} | {o.get('cagr', np.nan):.2%} | "
            f"{o.get('sharpe', np.nan):.2f} | {o.get('max_drawdown', np.nan):.2%} | "
            f"{c2.get('cagr', np.nan):.2%} | {d.get('dsr_approx', np.nan):.3f} |"
        )
    lines += [
        "",
        "## Key limitations",
        "- Historical WIG membership is point-in-time by available GPW Benchmark snapshots, but snapshots are not daily.",
        "- OHLCV archive has no explicit adjusted-close/dividend field; strategy returns are price-return based.",
        "- Delisting terminal returns are unavailable; a conservative -30% penalty is applied after 5 consecutive missing sessions while held.",
        "- Execution is next-close, not same-close. Spread/slippage uses ADV buckets and is stress-tested at 1x/1.5x/2x/3x.",
        "- Results end on 2024-01-24 because that is the terminal date of the mirrored Bossa archive used here.",
    ]
    (outdir / "README.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
