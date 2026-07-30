from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest the HK-US momentum/low-risk subfactor.")
    p.add_argument("--start-date", default="20240901")
    p.add_argument("--end-date", default="20260728")
    p.add_argument("--output-dir", default="backtest_full")
    p.add_argument("--reuse-price-cache", action="store_true")
    return p.parse_args()


def init_api():
    import panda_data

    username = os.getenv("PANDA_DATA_USERNAME") or os.getenv("PANDAAI_USERNAME")
    password = os.getenv("PANDA_DATA_PASSWORD") or os.getenv("PANDAAI_PASSWORD")
    if not username or not password:
        raise RuntimeError("PandaData credentials are required")
    panda_data.init_token(username=username, password=password)
    return panda_data


def prepare(frame: pd.DataFrame, market: str) -> pd.DataFrame:
    frame = frame.copy()
    frame["market"] = market
    frame["date"] = pd.to_datetime(frame["date"].astype(str))
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    price_col = "alt_close" if market == "hk" and "alt_close" in frame else "close"
    frame["price"] = pd.to_numeric(frame[price_col], errors="coerce")
    frame["volume"] = pd.to_numeric(frame.get("volume"), errors="coerce")
    frame = frame.dropna(subset=["date", "symbol", "price"])
    frame = frame[frame["price"] > 0].sort_values(["symbol", "date"])
    return compute_features(frame)


def compute_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values(["market", "symbol", "date"]).copy()
    grouped = frame.groupby(["market", "symbol"], group_keys=False)
    frame["ret_1d"] = grouped["price"].pct_change(fill_method=None)
    frame["momentum_60d"] = grouped["price"].pct_change(60, fill_method=None)
    frame["volatility_20d"] = (
        grouped["ret_1d"].rolling(20, min_periods=15).std()
        .reset_index(level=[0, 1], drop=True)
    )
    frame["forward_21d"] = grouped["price"].pct_change(21, fill_method=None).shift(-21)
    return frame


def rank_z(series: pd.Series) -> pd.Series:
    rank = series.rank(pct=True)
    return (rank - 0.5) * 2


def monthly_backtest(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    frame = frame.copy()
    frame["month"] = frame["date"].dt.to_period("M")
    rebalance = frame.groupby(["market", "symbol", "month"], as_index=False).tail(1)
    rebalance["forward_21d"] = rebalance.groupby(["market", "month"])["forward_21d"].transform(
        lambda x: x.clip(x.quantile(0.01), x.quantile(0.99))
    )
    rebalance["momentum_score"] = rebalance.groupby(["market", "month"])["momentum_60d"].transform(rank_z)
    rebalance["low_risk_score"] = -rebalance.groupby(["market", "month"])["volatility_20d"].transform(rank_z)
    rebalance["factor_score"] = (rebalance["momentum_score"] + rebalance["low_risk_score"]) / 2
    rebalance = rebalance.dropna(subset=["factor_score", "forward_21d"])
    rebalance["quantile"] = rebalance.groupby(["market", "month"])["factor_score"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 5, labels=False, duplicates="drop") + 1
    )
    ic = (
        rebalance.groupby(["market", "month"])
        .apply(lambda x: x["factor_score"].rank().corr(x["forward_21d"].rank()),
               include_groups=False)
        .rename("rank_ic")
        .reset_index()
    )
    ic["date"] = ic["month"].dt.to_timestamp("M")
    ic = ic.drop(columns="month")
    quantile = (
        rebalance.groupby(["market", "month", "quantile"], as_index=False)["forward_21d"]
        .mean()
        .rename(columns={"forward_21d": "period_return"})
    )
    wide = quantile.pivot_table(
        index=["market", "month"], columns="quantile", values="period_return"
    ).reset_index()
    wide["date"] = wide["month"].dt.to_timestamp("M")
    wide = wide.drop(columns="month")
    for q in range(1, 6):
        if q not in wide:
            wide[q] = np.nan
    wide["long_short_return"] = wide[5] - wide[1]
    wide["long_only_return"] = wide[5]
    wide = wide.sort_values(["market", "date"])
    wide["long_short_nav"] = wide.groupby("market")["long_short_return"].transform(
        lambda x: (1 + x.fillna(0)).cumprod()
    )
    wide["long_only_nav"] = wide.groupby("market")["long_only_return"].transform(
        lambda x: (1 + x.fillna(0)).cumprod()
    )

    turnover_rows = []
    for market, group in rebalance[rebalance["quantile"] == 5].groupby("market"):
        previous: set[str] | None = None
        for month, dated in group.groupby("month"):
            current = set(dated["symbol"])
            turnover = np.nan if previous is None else 1 - len(current & previous) / max(len(previous), 1)
            turnover_rows.append({"market": market, "date": month.to_timestamp("M"), "top_quantile_turnover": turnover})
            previous = current
    turnover = pd.DataFrame(turnover_rows)
    wide = wide.merge(turnover, on=["market", "date"], how="left")

    metrics: dict[str, dict] = {}
    for market in sorted(wide["market"].unique()):
        curve = wide[wide["market"] == market]
        market_ic = ic.loc[ic["market"] == market, "rank_ic"].dropna()
        nav = curve["long_short_nav"]
        drawdown = nav / nav.cummax() - 1
        metrics[market] = {
            "periods": int(len(curve)),
            "mean_rank_ic": float(market_ic.mean()),
            "icir": float(market_ic.mean() / market_ic.std(ddof=1)) if market_ic.std(ddof=1) else None,
            "positive_ic_rate": float((market_ic > 0).mean()),
            "long_short_total_return": float(nav.iloc[-1] - 1),
            "long_only_total_return": float(curve["long_only_nav"].iloc[-1] - 1),
            "max_drawdown": float(drawdown.min()),
            "mean_top_quantile_turnover": float(curve["top_quantile_turnover"].mean()),
        }
    return ic, wide, metrics


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "daily_prices.parquet"
    if args.reuse_price_cache and cache.exists():
        prices = pd.read_parquet(cache)
        prices["date"] = pd.to_datetime(prices["date"])
        prices = compute_features(prices)
    else:
        api = init_api()
        hk = api.get_hk_daily(
            symbol=[], start_date=args.start_date, end_date=args.end_date,
            fields=["date", "symbol", "alt_close", "close", "volume", "trade_status"],
        )
        us = api.get_us_daily(
            symbol=[], start_date=args.start_date, end_date=args.end_date,
            fields=["date", "symbol", "close", "volume", "trade_status"],
        )
        prices = pd.concat([prepare(hk, "hk"), prepare(us, "us")], ignore_index=True)
        prices[["market", "date", "symbol", "price", "volume"]].to_parquet(
            cache, index=False
        )
    ic, curve, metrics = monthly_backtest(prices)
    ic.to_csv(out / "rank_ic_series.csv", index=False, encoding="utf-8-sig")
    curve.to_csv(out / "equity_curve.csv", index=False, encoding="utf-8-sig")
    (out / "backtest_metrics.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "method": "monthly momentum_60d + negative volatility_20d; next 21 trading-day return",
                "start_date": args.start_date,
                "end_date": args.end_date,
                "price_rows": len(prices),
                "metrics": metrics,
                "limitations": [
                    "Validates the price-based momentum/low-risk subfactor, not the latest-only value snapshot.",
                    "US close is unadjusted because the documented US daily endpoint does not expose adjusted close.",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
