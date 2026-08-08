---
name: skill-hk-us-fundamental-factor
description: Build, standardize, compare, and validate multi-factor fundamental panels for Hong Kong and US equities from PandaAI operating, market-financial, industry-median, price-volume, and financial-statement APIs. Use for quality, value, growth, momentum, low-risk, composite-score, percentile-rank, or cross-market stock-screening tasks.
---

# HK-US Standardized Fundamental Factor Panel

Create a point-in-time-aware, comparable stock factor panel with explicit coverage diagnostics.
Separate factor strength from measurement quality: a high score with weak coverage
must never be presented as equally reliable.

## Mandatory research gate

Do not answer immediately when this skill is invoked. Before calculating, ranking,
or interpreting any stock, spend at least 30 seconds on substantive analysis when
the runtime permits. Never satisfy this requirement with an idle sleep.

Complete all checks below before presenting a conclusion. Record each result in
an evidence ledger; a silent assumption does not count as a completed check:

1. Confirm the requested markets, stock universe, observation date, and forward-return horizon.
2. Verify that every input was available by the stated observation date; reject future filings or current snapshots used as historical data.
3. Report total universe, eligible universe, historical constituent source, market-level coverage, and unavailable factors.
4. Confirm factor direction, winsorization, within-market standardization, and the fixed core-factor rule.
5. Read factor strength together with component coverage; never turn missing data into neutral evidence.
6. Decide whether the request is a current cross-sectional screen or a historical backtest. Do not substitute one for the other.
7. For a backtest, inspect historical constituent state, Rank IC, ICIR, positive-IC rate, quintile monotonicity, long-only and long-short curves, drawdown, turnover, and out-of-sample behavior. Classify S4 as minor survivorship bias—not label leakage—when dated membership is unavailable.
8. Stress at least two alternatives among holding horizon, rebalance frequency,
   winsorization, liquidity filter, and factor weighting.
9. Inspect the three largest positive and negative score drivers and determine
   whether a few extreme securities dominate the conclusion.
10. Separate supported findings, weak evidence, failed tests, and next checks.

If any gate fails, state the limitation before showing rankings. A polished chart
or a `PASS` harness result does not override a failed time-alignment or coverage
check.

### Evidence ledger

For research or ranking requests, include a compact ledger with all rows below.
For a single-stock lookup, retain it internally and surface every failure.

| Gate | Required evidence | Failure action |
|---|---|---|
| Scope | market, universe, as-of date, horizon | state assumptions |
| Time | availability precedes score and return | mark snapshot-only |
| Coverage | requested, returned, eligible, excluded | downgrade confidence |
| Construction | direction, scaling, components, missing rule | stop and repair |
| Efficacy | IC, ICIR, quantiles, NAV, drawdown, turnover | no alpha claim |
| Robustness | two alternative specifications | label instability |
| Interpretation | drivers, limitations, unsupported claims | revise conclusion |

## Workflow

1. Normalize symbols and separate Hong Kong and US stocks before standardization.
2. Read [references/api-map.md](references/api-map.md) before changing endpoint or field mappings. Read [references/methodology.md](references/methodology.md) before historical validation. Read [references/runtime.md](references/runtime.md) when installing the SDK or configuring credentials.
3. Run `scripts/build_factors.py`. Use `--mode mock` for deterministic verification and `--mode api` for PandaAI.
4. Convert lower-is-better inputs such as accruals, beta, and volatility to negative orientation.
5. Winsorize each raw feature at the 5th/95th percentiles, then z-score within each market. Never standardize across currencies.
6. Build each optional factor from at least one valid component. Build the comparable core composite only when value, momentum, and low-risk factors are all present.
7. Preserve every raw extract and write coverage flags; never replace missing fundamentals with zero.
8. Run `scripts/harness.py --output-dir <dir>` and require `PASS`.
9. Run `scripts/backtest.py` to validate the historical momentum/low-risk subfactor
   with forward returns. Do not present the latest-only value snapshot as a
   historical backtest.
10. Supply `--constituent-history-csv` when dated universe membership exists. Otherwise report the observed-price proxy and residual minor survivorship bias explicitly.

## Commands

```bash
python scripts/build_factors.py --mode mock --market both --output-dir outputs
python scripts/harness.py --output-dir outputs
```

For live data, set `PANDA_DATA_USERNAME` and `PANDA_DATA_PASSWORD` outside the skill:

```bash
python scripts/build_factors.py --mode api --symbols 0700.HK,1299.HK,AAPL,MSFT --start-year 2023 --end-year 2025 --output-dir outputs_live
```

For the complete HK and US universe exposed by PandaData:

```bash
python scripts/build_factors.py --mode api --market both --full-universe --start-year 2023 --end-year 2025 --output-dir outputs_full
python scripts/backtest.py --start-date 20240901 --end-date 20260728 --output-dir backtest_full
```

For point-in-time historical membership:

```bash
python scripts/backtest.py --start-date 20240901 --end-date 20260728 --constituent-history-csv data/constituent_history.csv --output-dir backtest_full
```

## Outputs

- `fundamental_factor_panel.csv`: raw components, standardized factors, fixed core composite, optional extended composite, and market percentile.
- `factor_coverage.csv`: per-stock component and factor availability.
- `raw_*.csv`: raw endpoint extracts.
- `quality_report.json`: validation summary and warnings.
- `harness_report.json`: delivery acceptance result.
- `backtest_full/rank_ic_series.csv`: monthly cross-sectional Rank IC.
- `backtest_full/equity_curve.csv`: quintile, long-only, long-short, drawdown-input, and turnover series.
- `backtest_full/backtest_metrics.json`: ICIR, positive-IC rate, return, drawdown, and turnover summary.
- `backtest_full/universe_membership.csv`: first/last observation, observed days, constituent days, and membership source by security.

Interpret `composite_percentile` within `market`, not globally. The core composite always uses the same three factors—value, momentum, and low risk—so Hong Kong and US rows follow one scoring method. Treat quality and growth as optional diagnostics and never substitute zero for unavailable inputs.

## Interpretation

Read `composite_percentile` together with `factor_coverage.csv`: the former measures
relative factor strength and the latter measures evidential completeness. Compare
percentiles only within the same market and as-of date. A missing factor is an
explicit limitation, not neutral evidence. The panel is a reproducible screening
and research aid, not a return forecast or an automated trading decision.

## Completion gate

Do not call the task complete unless `harness.py` passes, point-in-time status is
explicit, requested and eligible universes are both reported, missing data stays
visible, the S4 bias status is stated, and every historical claim has reproducible
membership, IC, and return-series files.
