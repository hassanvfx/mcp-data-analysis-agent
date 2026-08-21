"""Fail CI unless required line and branch coverage thresholds are met."""

from __future__ import annotations

import json
import sys
from pathlib import Path

LINE_THRESHOLD = 90.0
BRANCH_THRESHOLD = 85.0


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) == 2 else "coverage.json")
    totals = json.loads(report.read_text(encoding="utf-8"))["totals"]
    line_coverage = float(totals["percent_statements_covered"])
    branch_coverage = float(totals["percent_branches_covered"])
    print(f"line coverage: {line_coverage:.2f}% (required {LINE_THRESHOLD:.0f}%)")
    print(f"branch coverage: {branch_coverage:.2f}% (required {BRANCH_THRESHOLD:.0f}%)")
    return 0 if line_coverage >= LINE_THRESHOLD and branch_coverage >= BRANCH_THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
