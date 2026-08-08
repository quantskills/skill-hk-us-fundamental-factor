# Historical-universe and bias methodology

## S4 assessment

Classify the default historical price backtest as having **minor survivorship bias**, not label leakage. Prices and forward returns are aligned within each security and no future return is used to construct the score. The residual issue is universe construction: without a dated constituent file, the observed-price universe may omit securities that disappeared before the extraction window or may not reproduce historical index membership.

## Historical constituent state

Preferred input is a daily point-in-time CSV supplied through `--constituent-history-csv` with:

| Column | Meaning |
|---|---|
| `market` | `hk` or `us` |
| `symbol` | normalized security identifier |
| `date` | date on which the membership state applies |
| `is_constituent` | whether the security belongs to the research universe on that date |

The backtest joins membership on `market + symbol + date`, filters the rebalance cross-section to contemporaneous constituents and tradeable securities, and writes `universe_membership.csv` for audit.

When the file is absent, use the observed-price/trade-status history only as an explicit proxy. Mark `bias_assessment.s4_status = minor_survivorship_bias`, keep `label_leakage = false`, and do not describe the result as fully survivorship-bias-free.

