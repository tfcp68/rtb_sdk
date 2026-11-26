#!/usr/bin/env python3
"""
Script for running the simulation filter tests with report generation.

Usage (from the project root):
    python tests/simulation/run_report.py [pytest-args...]

After running it creates tests/simulation/reports/report.json.
"""

import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent.parent
REPORT_JSON = TESTS_DIR / "reports" / "report.json"

_LIVE_OPTS = [
    "--live-describe",
    "-p", "no:terminal",
    "-p", "no:rich",
    "-p", "no:sugar",
    "-p", "no:spec",
]


def main():
    extra_args = sys.argv[1:]

    cmd = [
        sys.executable, "-m", "pytest",
        str(TESTS_DIR),
        *_LIVE_OPTS,
        *extra_args,
    ]

    print("=" * 60)
    print(f"Launch: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if REPORT_JSON.exists():
        data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        s = data["summary"]
        print()
        print("=" * 60)
        print(f"JSON-report: {REPORT_JSON}")
        print(
            f"Totally: {s['total']}  |  "
            f"passed: {s['passed']}  |  "
            f"failed: {s['failed']}  |  "
            f"error: {s['error']}  |  "
            f"skipped: {s['skipped']}"
        )
        print("=" * 60)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
