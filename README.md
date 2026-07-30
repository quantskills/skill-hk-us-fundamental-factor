# 港美股基本面因子技能 / HK-US Fundamental Factor Skill

一个可复现的 PandaAI 技能，用于构建、审计及验证港股与美股的标准化基本面因子面板。  
A reproducible PandaAI skill for building, auditing, and validating standardized fundamental-factor panels across Hong Kong and US equities.

本技能明确区分三个问题：股票相对本地市场的因子表现、底层数据的完整性与可靠性，以及具备历史可检验条件的子因子能否预测未来收益。  
The skill separates factor strength relative to the local market, supporting-data quality, and the forward-return behavior of historically testable subfactors.

## 核心功能 / Features

- 支持港股、美股、指定股票及全样本运行 / HK, US, selected-symbol, and full-universe support
- 分市场缩尾与标准化 / Market-specific winsorization and standardization
- 质量、价值、成长、动量及低风险因子 / Quality, value, growth, momentum, and low-risk factors
- 固定可比核心复合因子 / Fixed comparable core composite
- 成分与因子覆盖率诊断 / Component and factor coverage diagnostics
- 保留缺失值，不以零替代 / Missing values remain missing rather than being replaced with zero
- 时点与前视偏差检查 / Point-in-time and look-ahead-bias checks
- Rank IC、ICIR、分组收益、净值、回撤及换手率分析 / Rank IC, ICIR, quantile return, NAV, drawdown, and turnover analysis
- 确定性模拟模式与 API 实盘数据模式 / Deterministic mock mode and API-backed live mode
- 自动验收及独立交互式 HTML 报告 / Automated acceptance testing and self-contained interactive HTML reporting

## 因子构建 / Factor Construction

| 因子 / Factor | 示例成分 / Example components | 方向 / Direction |
|---|---|---|
| 质量 / Quality | ROE、营业利润率、应计项 / ROE, operating margin, accruals | 质量越高越好，应计项越低越好 / Higher quality; lower accruals |
| 价值 / Value | 盈利收益率、账面市值比、销售额企业价值比 / Earnings yield, book-to-price, sales-to-EV | 越高代表越便宜 / Higher is cheaper |
| 成长 / Growth | 营收增长、盈利增长 / Revenue and earnings growth | 越高越强 / Higher is stronger |
| 动量 / Momentum | 26周及52周相对收益 / 26-week and 52-week relative returns | 越高越强 / Higher is stronger |
| 低风险 / Low risk | Beta、波动率 / Beta and volatility | 越低越强 / Lower is stronger |

原始特征在各自市场内按第 5/95 百分位缩尾并标准化，港股和美股不会混合标准化。  
Raw features are winsorized at the 5th/95th percentiles and standardized within each market; HK and US securities are never standardized together.

核心复合因子为：

```text
equal_weight(value, momentum, low_risk)
```

只有三个核心因子均可用时才计算复合分；质量与成长因子作为补充诊断。  
The core composite is assigned only when all three factors are available; quality and growth remain optional diagnostics.

## 目录结构 / Repository Structure

```text
skill-hk-us-fundamental-factor/
├── SKILL.md
├── README.md
├── agents/openai.yaml
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

## 环境要求 / Requirements

- Python 3.10+
- `pandas`
- `numpy`
- `pyarrow`
- 实盘 API 模式需要 / Live API mode requires `panda_data>=0.0.9,<0.1`

```bash
pip install "panda_data>=0.0.9,<0.1"
```

## 身份认证与安全 / Authentication & Security

请在仓库外配置环境变量；切勿提交真实凭据、访问令牌、`.env` 文件或私钥。  
Set credentials outside the repository. Never commit credentials, access tokens, `.env` files, or private keys.

```bash
export PANDA_DATA_USERNAME="your_username"
export PANDA_DATA_PASSWORD="your_password"
```

## 使用方法 / Usage

### 模拟数据 / Deterministic Mock Run

```bash
python scripts/build_factors.py --mode mock --market both --output-dir outputs
python scripts/harness.py --output-dir outputs
```

### 指定股票实盘数据 / Selected Live Symbols

```bash
python scripts/build_factors.py \
  --mode api --market both \
  --symbols 0700.HK,0005.HK,AAPL,MSFT \
  --start-year 2023 --end-year 2025 \
  --output-dir outputs_live

python scripts/harness.py --output-dir outputs_live
```

### 港美股全样本 / Full HK-US Universe

```bash
python scripts/build_factors.py \
  --mode api --market both --full-universe \
  --start-year 2023 --end-year 2025 \
  --output-dir outputs_full

python scripts/harness.py --output-dir outputs_full
```

### 历史价格子因子回测 / Historical Price-Subfactor Backtest

```bash
python scripts/backtest.py \
  --start-date 20240901 --end-date 20260728 \
  --output-dir backtest_full
```

该回测只验证价格型动量/低风险子因子，不会把当前价值快照回填至历史日期。  
This backtest validates only the price-based momentum/low-risk subfactor; it never backfills the latest value snapshot into earlier dates.

## 主要产出 / Main Outputs

| 文件 / File | 说明 / Description |
|---|---|
| `fundamental_factor_panel.csv` | 原始成分、标准化因子、复合分及市场百分位 / Raw components, standardized factors, composites, and market percentiles |
| `factor_coverage.csv` | 个股成分数量与复合因子资格 / Component counts and composite eligibility |
| `quality_report.json` | 覆盖率、重复值、警告及 SDK 信息 / Coverage, duplicates, warnings, and SDK metadata |
| `harness_report.json` | 自动验收结果 / Automated acceptance-test result |
| `rank_ic_series.csv` | 月度横截面 Rank IC / Monthly cross-sectional Rank IC |
| `equity_curve.csv` | 分组收益、多头及多空净值、换手率 / Quantile returns, NAV, and turnover |
| `backtest_metrics.json` | ICIR、正 IC 比率、收益、回撤及换手率 / ICIR, positive-IC rate, return, drawdown, and turnover |
| `factor-report.html` | 独立交互式研究报告 / Self-contained interactive research report |

## 全样本参考结果 / Full-Sample Reference Run

- 港美股候选证券 18,733 只 / 18,733 candidate securities
- 核心复合因子合格证券 6,518 只 / 6,518 core-composite-eligible securities
- 其中港股 2,269 只，美股 4,249 只 / 2,269 HK and 4,249 US securities
- 历史价格子因子回测使用 5,487,555 条日行情 / 5,487,555 daily-price observations

数量取决于数据源覆盖范围和运行日期，未来可能变化。  
Counts depend on source coverage and run date and may change in future releases.

## GitHub 上传说明 / GitHub Upload Notes

仓库中的 `.gitignore` 会排除全样本原始数据、完整因子面板及历史日行情缓存，以避免提交体积过大的文件；本地文件不会被删除。小型模拟/实盘示例、质量报告、Rank IC、收益曲线及回测指标仍可正常上传。全样本数据可通过上述命令重新生成。  
The included `.gitignore` excludes full-universe raw extracts, the complete factor panel, and the historical daily-price cache without deleting local files. Small examples, quality reports, Rank IC, equity curves, and backtest metrics remain uploadable. Full-sample data can be regenerated with the commands above.

## 研究规范 / Research Safeguards

- 明确股票池、日期、预测周期与决策场景 / Define universe, date, horizon, and decision context
- 检查输入可得性并排除未来信息 / Verify data availability and reject future information
- 报告请求、返回、合格与排除样本数 / Report requested, returned, eligible, and excluded samples
- 核查因子方向、尺度、成分及缺失值规则 / Verify direction, scaling, components, and missing-data rules
- 评估 IC、分组单调性、净值、回撤及换手率 / Evaluate IC, monotonicity, NAV, drawdown, and turnover
- 至少测试两种合理替代设定 / Test at least two reasonable alternative specifications
- 检查极端股票是否主导结果 / Inspect extreme-security dominance
- 区分有证据、弱证据及不受支持的结论 / Separate supported, weak, and unsupported claims

## 局限性 / Limitations

- PandaData SDK 不同版本可能调整字段名 / Field names may change across SDK versions
- 部分股票可能缺少成长或质量数据 / Growth or quality components may be unavailable
- 当前财务快照不得视为历史观测 / Current financial snapshots are not historical observations
- 美股日行情接口不提供复权收盘价，历史收益分析需谨慎处理公司行动 / The documented US daily endpoint lacks adjusted close, so corporate actions need care
- 百分位为市场内相对值，不应直接进行全球比较 / Percentiles are market-relative
- 本项目仅用于研究与数据处理，不构成投资建议或自动交易系统 / This project is for research and data processing, not investment advice or an automated trading system

## 许可 / License

公开发布前请添加适用的开源许可证。  
Add the intended open-source license before public distribution.
