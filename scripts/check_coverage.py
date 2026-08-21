"""Fail CI unless required line and branch coverage thresholds are met."""

from __future__ import annotations

import json
import sys
from pathlib import Path

LINE_THRESHOLD = 90.0
BRANCH_THRESHOLD = 85.0
CRITICAL_MODULES = {
    "src/mcp_data_agent/config.py",
    "src/mcp_data_agent/context.py",
    "src/mcp_data_agent/ledger.py",
    "src/mcp_data_agent/policy.py",
}


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) == 2 else "coverage.json")
    data = json.loads(report.read_text(encoding="utf-8"))
    totals = data["totals"]
    line_coverage = float(totals["percent_statements_covered"])
    branch_coverage = float(totals["percent_branches_covered"])
    print(f"line coverage: {line_coverage:.2f}% (required {LINE_THRESHOLD:.0f}%)")
    print(f"branch coverage: {branch_coverage:.2f}% (required {BRANCH_THRESHOLD:.0f}%)")
    failures = line_coverage < LINE_THRESHOLD or branch_coverage < BRANCH_THRESHOLD
    for path in sorted(CRITICAL_MODULES):
        summary = data["files"].get(path, {}).get("summary")
        if summary is None:
            print(f"critical module missing from coverage report: {path}")
            failures = True
            continue
        statements = float(summary["percent_covered"])
        branches = 100.0 if summary["num_branches"] == 0 else (summary["covered_branches"] / summary["num_branches"] * 100)
        print(f"critical {path}: {statements:.2f}% combined; {branches:.2f}% branches")
        if statements < 100.0 or branches < 100.0:
            failures = True
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
