# PandaAI API and factor map

## Endpoints

| Market | Operating | Market/financial | Industry median | Price/volume | Quarterly statement |
|---|---|---|---|---|---|
| Hong Kong | `get_stock_operating_indicator` | `get_stock_mktfin_indicator` | `get_stock_industry_median` | `get_stock_pv_indicator` | `get_fina_statement` |
| United States | `get_stock_operating_metric` | `get_stock_mktfin_metric` | `get_stock_sector_median` | `get_stock_pv_metric` | `get_fina_ex` |

Operating endpoints return long-form rows with fields such as `symbol`, fiscal year, `item_desc`, and `item_num`. Pivot the latest usable observation by symbol and item description before mapping factors.

## Canonical components

- Quality: `roe`, `operating_margin`, negative `accruals`.
- Value: `earnings_yield`, `book_to_price`, `sales_to_ev`.
- Growth: `revenue_growth`, `earnings_growth`.
- Momentum: `relative_return_26w`, `relative_return_52w`.
- Low risk: negative `beta_5y`, negative `volatility_1y`.

The builder accepts canonical names directly and resolves common PandaAI aliases. API releases may expose different field names; retain raw extracts and record missing mappings in `quality_report.json`.

## Point-in-time rules

Use the latest record available as of the requested cutoff. Do not join future filings to earlier market dates. Do not compare raw currency-valued fields across HKD and USD. Standardize by market and use ratios or growth rates whenever possible.
