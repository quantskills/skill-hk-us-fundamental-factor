from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="outputs")
    args = p.parse_args()
    root = Path(args.output_dir)
    required = ["fundamental_factor_panel.csv", "factor_coverage.csv", "quality_report.json"]
    checks = {"required_files": all((root / x).is_file() for x in required)}
    if checks["required_files"]:
        panel = pd.read_csv(root / required[0])
        expected = {"market", "symbol", "quality", "value", "growth", "momentum",
                    "low_risk", "composite_z", "composite_percentile", "factor_count",
                    "core_factor_count", "eligible_for_composite",
                    "extended_composite_z", "composite_method"}
        quality = json.loads((root / "quality_report.json").read_text(encoding="utf-8"))
        checks.update({
            "nonempty_panel": not panel.empty,
            "required_columns": expected.issubset(panel.columns),
            "unique_keys": bool(not panel.duplicated(["market", "symbol"]).any()),
            "valid_markets": set(panel["market"]).issubset({"hk", "us"}),
            "eligible_sample_nonempty": bool(panel["eligible_for_composite"].sum() > 0),
            "eligible_composite_complete": bool(
                panel.loc[panel["eligible_for_composite"], "composite_z"].notna().all()),
            "ineligible_composite_empty": bool(
                panel.loc[~panel["eligible_for_composite"], "composite_z"].isna().all()),
            "percentile_range": bool(panel["composite_percentile"].dropna().between(0, 100).all()),
            "fixed_core_factor_rule": bool(
                panel["eligible_for_composite"].eq(panel["core_factor_count"].eq(3)).all()),
            "fixed_composite_method": set(panel["composite_method"]) == {
                "equal_weight(value,momentum,low_risk)"},
            "quality_report_pass": quality.get("status") == "PASS",
        })
    status = "PASS" if checks and all(checks.values()) else "FAIL"
    result = {"status": status, "checks": checks}
    (root / "harness_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
