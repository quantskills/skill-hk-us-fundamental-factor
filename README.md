# HK-US Fundamental Factor Skill

A reproducible PandaAI skill for building, auditing, and validating standardized
fundamental-factor panels across Hong Kong and US equities.

The skill separates three questions that are often incorrectly combined:

1. How strong is a stock's factor profile relative to its local market?
2. How complete and reliable is the supporting data?
3. Does the historically testable subfactor exhibit useful forward-return behavior?

## Features

- Hong Kong and US equity support
- Full-universe or selected-symbol execution
- Market-specific winsorization and standardization
- Quality, value, growth, momentum, and low-risk factors
- Fixed comparable composite using value, momentum, and low risk
- Explicit component and factor coverage diagnostics
- Missing values preserved rather than replaced with zero
- Point-in-time and look-ahead-bias checks
- Rank IC, ICIR, quantile-return, NAV, drawdown, and turnover analysis
- Deterministic mock mode and API-backed live mode
- Automated delivery harness
- Self-contained interactive HTML report

## Factor construction

| Factor | Example components | Direction |
|---|---|---|
| Quality | ROE, operating margin, accruals | Higher quality; lower accruals |
| Value | Earnings yield, book-to-price, sales-to-EV | Higher is cheaper |
| Growth | Revenue growth, earnings growth | Higher is stronger |
| Momentum | 26-week and 52-week relative returns | Higher is stronger |
| Low risk | Beta and volatility | Lower is stronger |

Each raw feature is winsorized at the 5th and 95th percentiles and standardized
within its own market. Hong Kong and US securities are never standardized
together.

The comparable core composite is:

```text
equal_weight(value, momentum, low_risk)
```

A stock receives a core composite only when all three factors are available.
Quality and growth remain optional diagnostics.

## Repository structure

```text
skill-hk-us-fundamental-factor/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── build_factors.py
│   ├── backtest.py
│   └── harness.py
├── references/
│   ├── api-map.md
│   └── runtime.md
├── outputs_mock_final/
├── outputs_sample_live/
├── outputs_full/
└── backtest_full/
```

## Requirements

- Python 3.10+
- `pandas`
- `numpy`
- `pyarrow`
- `panda_data>=0.0.9,<0.1` for live API execution

Install the PandaData SDK:

```bash
pip install "panda_data>=0.0.9,<0.1"
```

## Authentication

Set credentials outside the repository:

```bash
export PANDA_DATA_USERNAME="your_username"
export PANDA_DATA_PASSWORD="your_password"
```

Never commit credentials, access tokens, `.env` files, or private keys.

## Usage

### Deterministic mock run

```bash
python scripts/build_factors.py \
  --mode mock \
  --market both \
  --output-dir outputs

python scripts/harness.py --output-dir outputs
```

### Selected live symbols

```bash
python scripts/build_factors.py \
  --mode api \
  --market both \
  --symbols 0700.HK,0005.HK,AAPL,MSFT \
  --start-year 2023 \
  --end-year 2025 \
  --output-dir outputs_live

python scripts/harness.py --output-dir outputs_live
```

### Full HK-US universe

```bash
python scripts/build_factors.py \
  --mode api \
  --market both \
  --full-universe \
  --start-year 2023 \
  --end-year 2025 \
  --output-dir outputs_full

python scripts/harness.py --output-dir outputs_full
```

### Historical price-subfactor backtest

```bash
python scripts/backtest.py \
  --start-date 20240901 \
  --end-date 20260728 \
  --output-dir backtest_full
```

The historical backtest validates the price-based momentum/low-risk subfactor.
It does not backfill the latest value snapshot into earlier dates.

## Main outputs

| File | Description |
|---|---|
| `fundamental_factor_panel.csv` | Raw components, standardized factors, composite scores, and market percentiles |
| `factor_coverage.csv` | Per-stock component counts and composite eligibility |
| `quality_report.json` | Coverage, duplicates, warnings, and SDK metadata |
| `harness_report.json` | Automated acceptance-test result |
| `rank_ic_series.csv` | Monthly cross-sectional Rank IC |
| `equity_curve.csv` | Quantile returns, long-only and long-short NAV, and turnover |
| `backtest_metrics.json` | ICIR, positive-IC rate, return, drawdown, and turnover summary |
| `factor-report.html` | Self-contained interactive research report when using the packaged release |

## Full-sample reference run

The included reference run contains:

- 18,733 securities in the combined candidate panel
- 6,518 securities eligible for the fixed core composite
- 2,269 eligible Hong Kong securities
- 4,249 eligible US securities
- 5,487,555 historical daily-price observations used for the price-subfactor backtest

Counts reflect the source coverage and run date; they may change in future API
releases.

## Research safeguards

The skill requires a substantive research gate before producing conclusions:

- define universe, date, horizon, and decision context;
- verify input availability and reject future information;
- report requested, returned, eligible, and excluded samples;
- verify factor direction, scaling, components, and missing-data rules;
- evaluate IC, quantile monotonicity, NAV, drawdown, and turnover;
- test at least two reasonable alternative specifications;
- inspect whether extreme securities dominate results;
- distinguish supported findings from weak or unsupported claims.

## Limitations

- Some PandaData fields may change names across SDK versions.
- Growth or quality components may be unavailable for parts of the universe.
- Current market-financial snapshots must not be treated as historical observations.
- The documented US daily endpoint does not expose an adjusted close, so corporate
  actions require additional care in historical return analysis.
- Percentiles are market-relative and should not be compared globally.
- This project is a research and data-processing tool, not an investment
  recommendation or automated trading system.

## License

Add the repository's intended license before public distribution.
