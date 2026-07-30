from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd


FEATURES = {
    "quality": [("roe", 1), ("operating_margin", 1), ("accruals", -1)],
    "value": [("earnings_yield", 1), ("book_to_price", 1), ("sales_to_ev", 1)],
    "growth": [("revenue_growth", 1), ("earnings_growth", 1)],
    "momentum": [("relative_return_26w", 1), ("relative_return_52w", 1)],
    "low_risk": [("beta_5y", -1), ("volatility_1y", -1)],
}
CORE_FACTORS = ["value", "momentum", "low_risk"]

ALIASES = {
    "roe": ["roe", "return_on_equity", "return on equity"],
    "operating_margin": ["operating_margin", "oper_margin", "operating margin"],
    "accruals": ["accruals", "asset_accruals", "bs_asset_accruals"],
    "earnings_yield": ["earnings_yield", "curr_earn_yld_basic_excl_ratio_ttm",
                       "curr_earn_yld_basic_incl_ratio_ttm", "ep", "earnings yield"],
    "book_to_price": ["book_to_price", "bp", "book to price"],
    "sales_to_ev": ["sales_to_ev", "curr_rev_to_ev_ratio_ttm", "curr_rev_to_ev_ratio",
                    "revenue_to_ev", "sales to ev"],
    "revenue_growth": ["revenue_growth", "sales_growth", "revenue growth"],
    "earnings_growth": ["earnings_growth", "net_income_growth", "earnings growth"],
    "relative_return_26w": ["relative_return_26w", "pv_rel_return_26w"],
    "relative_return_52w": ["relative_return_52w", "pv_rel_return_52w"],
    "beta_5y": ["beta_5y", "pv_beta_5y"],
    "volatility_1y": ["volatility_1y", "pv_volatility_1y", "volatility"],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build standardized HK-US fundamental factors.")
    p.add_argument("--mode", choices=["mock", "api"], default="mock")
    p.add_argument("--market", choices=["hk", "us", "both"], default="both")
    p.add_argument("--symbols", default="")
    p.add_argument("--full-universe", action="store_true",
                   help="Query every stock exposed by the selected market APIs.")
    p.add_argument("--start-year", default="2023")
    p.add_argument("--end-year", default="2025")
    p.add_argument("--as-of-date", default="")
    p.add_argument("--output-dir", default="outputs")
    return p.parse_args()


def symbols_for(raw: str, market: str) -> list[str]:
    supplied = [x.strip().upper() for x in raw.split(",") if x.strip()]
    defaults = {"hk": ["0700.HK", "0005.HK", "1299.HK", "2318.HK", "0388.HK", "0941.HK"],
                "us": ["AAPL", "MSFT", "JPM", "NVDA", "KO", "XOM"]}
    values = supplied or defaults[market]
    return [x for x in values if (x.endswith(".HK") if market == "hk" else not x.endswith(".HK"))]


def mock_frame(market: str, symbols: list[str]) -> pd.DataFrame:
    rows = []
    for i, symbol in enumerate(symbols):
        j = i + (0 if market == "hk" else 2)
        rows.append({
            "market": market, "symbol": symbol, "as_of_date": "20251231",
            "roe": 8 + j * 2.3, "operating_margin": 12 + j * 1.8,
            "accruals": -0.02 + j * 0.008, "earnings_yield": 0.035 + j * 0.007,
            "book_to_price": 0.18 + j * 0.045, "sales_to_ev": 0.20 + j * 0.03,
            "revenue_growth": 0.03 + j * 0.018, "earnings_growth": 0.02 + j * 0.022,
            "relative_return_26w": -0.05 + j * 0.055, "relative_return_52w": -0.08 + j * 0.07,
            "beta_5y": 0.72 + j * 0.09, "volatility_1y": 0.16 + j * 0.025,
        })
    return pd.DataFrame(rows)


def as_frame(value) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    if isinstance(value, dict):
        for key in ("data", "result", "rows"):
            if key in value:
                return pd.DataFrame(value[key])
    return pd.DataFrame(value)


def init_api():
    try:
        import panda_data
    except ImportError as exc:
        raise RuntimeError("panda_data is unavailable; configure it or use --mode mock") from exc
    username = os.getenv("PANDA_DATA_USERNAME") or os.getenv("PANDA_USERNAME")
    password = os.getenv("PANDA_DATA_PASSWORD") or os.getenv("PANDA_PASSWORD")
    if username and password:
        kwargs = {"username": username, "password": password}
        base_url = os.getenv("PANDA_DATA_BASE_URL") or os.getenv("PANDA_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        panda_data.init_token(**kwargs)
    elif hasattr(panda_data, "init"):
        panda_data.init()
    else:
        raise RuntimeError("Set PANDA_DATA_USERNAME and PANDA_DATA_PASSWORD for PandaData authentication")
    return panda_data


def normalize_symbols(df: pd.DataFrame, market: str) -> pd.DataFrame:
    if df.empty:
        return df
    symbol = next((c for c in df.columns if str(c).lower() in {"symbol", "ticker", "stock_code"}), None)
    if symbol is None:
        return df
    df = df.copy()
    df["symbol"] = df[symbol].astype(str).str.upper()
    if market == "us":
        df["symbol"] = df["symbol"].str.replace(r"\.(NB|N|OQ|P)$", "", regex=True)
    return df


def collapse_latest(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "symbol" not in df:
        return df
    date_cols = [c for c in df.columns if str(c).lower() in {"date", "report_date", "trade_date", "end_date"}]
    if date_cols:
        df = df.sort_values(date_cols[0])
    rows = []
    for symbol, group in df.groupby("symbol", sort=False):
        row = {"symbol": symbol}
        for col in group.columns:
            if col == "symbol":
                continue
            values = group[col].dropna()
            row[col] = values.iloc[-1] if not values.empty else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def canonicalize(frames: list[pd.DataFrame], market: str, symbols: list[str]) -> pd.DataFrame:
    if symbols:
        universe = symbols
    else:
        universe = sorted({
            str(symbol).upper()
            for frame in frames
            if not frame.empty
            for col in frame.columns
            if str(col).lower() in {"symbol", "ticker", "stock_code"}
            for symbol in frame[col].dropna()
        })
    base = pd.DataFrame({"symbol": universe})
    base["market"] = market
    for df in frames:
        if df.empty:
            continue
        df = normalize_symbols(df, market)
        item_col = next((c for c in df.columns if str(c).lower() in {"item_desc", "item_name", "indicator_name"}), None)
        value_col = next((c for c in df.columns if str(c).lower() in {"item_num", "item_value", "value"}), None)
        if item_col and value_col and "symbol" in df:
            temp = df.assign(_item=df[item_col].astype(str).str.lower().map(
                lambda x: re.sub(r"[^a-z0-9]+", "_", x).strip("_")))
            date_cols = [c for c in temp.columns if str(c).lower() in {
                "date", "report_date", "trade_date", "end_date", "financial_period_end_date"}]
            if date_cols:
                temp = temp.sort_values(date_cols[0]).drop_duplicates(["symbol", "_item"], keep="last")
            df = temp.pivot_table(index="symbol", columns="_item", values=value_col, aggfunc="last").reset_index()
        else:
            df = collapse_latest(df)
        if "symbol" not in df:
            continue
        # Several PandaData endpoints expose overlapping columns.  Keep the
        # first non-null observation across endpoints instead of discarding a
        # later endpoint merely because an earlier frame created the column
        # with only null values.
        incoming = [c for c in df.columns if c != "symbol"]
        overlap = [c for c in incoming if c in base.columns]
        base = base.merge(df[["symbol", *incoming]], on="symbol", how="left",
                          suffixes=("", "__incoming"))
        for col in overlap:
            other = f"{col}__incoming"
            base[col] = base[col].combine_first(base[other])
            base = base.drop(columns=other)
    out = base[["market", "symbol"]].copy()
    out["as_of_date"] = pd.NA
    lowered = {str(c).lower(): c for c in base.columns}
    for canonical, aliases in ALIASES.items():
        candidates = [lowered[a.lower()] for a in aliases if a.lower() in lowered]
        source = next((c for c in candidates
                       if pd.to_numeric(base[c], errors="coerce").notna().any()), None)
        if source is None:
            candidates = [c for c in base.columns
                          if any(a.lower() in str(c).lower() for a in aliases)]
            source = next((c for c in candidates
                           if pd.to_numeric(base[c], errors="coerce").notna().any()), None)
        out[canonical] = pd.to_numeric(base[source], errors="coerce") if source else np.nan
    if out["book_to_price"].isna().all():
        pb_candidates = [lowered[x] for x in ("curr_pb", "curr_pb_issue") if x in lowered]
        pb_source = next((c for c in pb_candidates
                          if pd.to_numeric(base[c], errors="coerce").notna().any()), None)
        if pb_source:
            pb = pd.to_numeric(base[pb_source], errors="coerce")
            out["book_to_price"] = 1 / pb.where(pb > 0)
    return out


def api_frame(api, market: str, symbols: list[str], start_year: str, end_year: str) -> tuple[pd.DataFrame, list[pd.DataFrame]]:
    query = symbols if symbols else ""
    if market == "hk":
        calls = [
            ("operating", api.get_stock_operating_indicator, {"symbol": query, "fields": [""], "start_year": start_year, "end_year": end_year}),
            ("mktfin", api.get_stock_mktfin_indicator, {"symbol": query, "fields": [
                "curr_earn_yld_basic_excl_ratio_ttm", "curr_earn_yld_basic_incl_ratio_ttm",
                "curr_pb", "curr_pb_issue", "curr_rev_to_ev_ratio", "curr_rev_to_ev_ratio_ttm"]}),
            ("median", api.get_stock_industry_median, {"symbol": query, "fields": [
                "imed_pretax_roa_ratio_ttm", "imed_net_trade_cycle_days_ttm"]}),
            ("pv", api.get_stock_pv_indicator, {"symbol": query, "fields": [
                "pv_beta_5y", "pv_rel_return_26w", "pv_rel_return_52w"]}),
            ("statement", api.get_fina_statement, {
                "symbol": query, "fields": ["symbol", "date", "bs_asset_accruals"],
                "start_quarter": f"{start_year}q1",
                "end_quarter": f"{end_year}q4", "is_latest": True}),
        ]
    else:
        calls = [
            ("operating", api.get_stock_operating_metric, {"symbol": query, "fields": [""], "start_year": start_year, "end_year": end_year}),
            ("mktfin", api.get_stock_mktfin_metric, {"symbol": query, "fields": [
                "curr_earn_yld_basic_excl_ratio_ttm", "curr_earn_yld_basic_incl_ratio_ttm",
                "curr_pb", "curr_pb_issue", "curr_rev_to_ev_ratio", "curr_rev_to_ev_ratio_ttm"]}),
            ("median", api.get_stock_sector_median, {"symbol": query, "fields": [
                "imed_pretax_roa_ratio_ttm", "imed_net_trade_cycle_days_ttm"]}),
            ("pv", api.get_stock_pv_metric, {"symbol": query, "fields": [
                "pv_beta_5y", "pv_rel_return_26w", "pv_rel_return_52w"]}),
            ("statement", api.get_fina_ex, {
                "symbol": query, "fields": ["symbol", "date", "bs_asset_accruals"],
                "start_quarter": f"{start_year}q1",
                "end_quarter": f"{end_year}q4", "is_latest": True}),
        ]
    raw = []
    for _, func, kwargs in calls:
        raw.append(as_frame(func(**kwargs)))
    return canonicalize(raw, market, symbols), raw


def zscore(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    if x.notna().sum() < 2:
        return pd.Series(np.nan, index=x.index)
    lo, hi = x.quantile([0.05, 0.95])
    clipped = x.clip(lo, hi)
    sd = clipped.std(ddof=0)
    return (clipped - clipped.mean()) / sd if sd and np.isfinite(sd) else pd.Series(0.0, index=x.index)


def score_factors(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = panel.copy()
    coverage = panel[["market", "symbol"]].copy()
    factor_cols = []
    for factor, specs in FEATURES.items():
        oriented = []
        for feature, direction in specs:
            col = f"z_{feature}"
            panel[col] = panel.groupby("market", group_keys=False)[feature].transform(zscore) * direction
            oriented.append(col)
        available = panel[oriented].notna().sum(axis=1)
        minimum = 1
        panel[factor] = panel[oriented].mean(axis=1).where(available >= minimum)
        coverage[f"{factor}_components"] = available
        factor_cols.append(factor)
    panel["factor_count"] = panel[factor_cols].notna().sum(axis=1)
    panel["core_factor_count"] = panel[CORE_FACTORS].notna().sum(axis=1)
    panel["eligible_for_composite"] = panel["core_factor_count"] == len(CORE_FACTORS)
    panel["composite_z"] = panel[CORE_FACTORS].mean(axis=1).where(
        panel["eligible_for_composite"])
    panel["extended_composite_z"] = panel[factor_cols].mean(axis=1).where(panel["factor_count"] >= 3)
    panel["composite_percentile"] = panel.groupby("market")["composite_z"].rank(pct=True) * 100
    panel["composite_method"] = "equal_weight(value,momentum,low_risk)"
    coverage["factor_count"] = panel["factor_count"]
    coverage["core_factor_count"] = panel["core_factor_count"]
    coverage["eligible_for_composite"] = panel["eligible_for_composite"]
    coverage["component_count"] = panel[list(ALIASES)].notna().sum(axis=1)
    return panel, coverage


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    markets = ["hk", "us"] if args.market == "both" else [args.market]
    api = init_api() if args.mode == "api" else None
    panels, warnings = [], []
    for market in markets:
        symbols = [] if args.full_universe else symbols_for(args.symbols, market)
        if not symbols and not args.full_universe:
            warnings.append(f"No {market.upper()} symbols selected")
            continue
        if api:
            panel, raw = api_frame(api, market, symbols, args.start_year, args.end_year)
            for name, frame in zip(("operating", "mktfin", "median", "pv", "statement"), raw):
                frame.to_csv(out / f"raw_{market}_{name}.csv", index=False, encoding="utf-8-sig")
        else:
            panel = mock_frame(market, symbols)
            panel.to_csv(out / f"raw_{market}_mock.csv", index=False, encoding="utf-8-sig")
        panels.append(panel)
    combined = pd.concat(panels, ignore_index=True) if panels else pd.DataFrame()
    scored, coverage = score_factors(combined) if not combined.empty else (combined, pd.DataFrame())
    scored.to_csv(out / "fundamental_factor_panel.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(out / "factor_coverage.csv", index=False, encoding="utf-8-sig")
    missing = {x: int(scored[x].isna().sum()) for x in FEATURES} if not scored.empty else {}
    unavailable = [name for name, count in missing.items() if count == len(scored)]
    warnings.extend(f"Factor unavailable for all selected stocks: {name}" for name in unavailable)
    quality = {
        "status": "PASS" if (
            not scored.empty
            and not scored.duplicated(["market", "symbol"]).any()
            and scored["eligible_for_composite"].any()
            and scored.loc[
                scored["eligible_for_composite"], "composite_z"
            ].notna().all()
        ) else "FAIL",
        "mode": args.mode, "rows": len(scored),
        "duplicate_keys": int(scored.duplicated(["market", "symbol"]).sum()) if not scored.empty else 0,
        "missing_factor_counts": missing, "warnings": warnings,
        "sdk_version": importlib.metadata.version("panda_data") if args.mode == "api" else None,
        "core_factors": CORE_FACTORS,
        "markets": markets,
        "symbol_count": int(scored["symbol"].nunique()) if not scored.empty else 0,
        "eligible_symbol_count": int(scored["eligible_for_composite"].sum()) if not scored.empty else 0,
        "eligible_by_market": (
            scored.groupby("market")["eligible_for_composite"].sum().astype(int).to_dict()
            if not scored.empty else {}
        ),
        "symbols_preview": scored["symbol"].head(20).tolist() if not scored.empty else [],
    }
    (out / "quality_report.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    main()
