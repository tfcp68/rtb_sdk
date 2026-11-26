#!/usr/bin/env python3
"""
Unified script for running the auction + optimizer tests with a live reporter.

Usage (from the project root):
    python tests/run_report.py [pytest-args...]

Examples:
    python tests/run_report.py                     # all tests
    python tests/run_report.py tests/auction/      # auction only
    python tests/run_report.py tests/optimizer/    # optimizer only
    python tests/run_report.py -k "optimize"       # filter by name

After running it creates:
    tests/reports/report.json           — combined report
    tests/auction/reports/report.json   — auction only
    tests/optimizer/reports/report.json — optimizer only
"""

import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
COMBINED_REPORT = TESTS_DIR / "reports" / "report.json"

_LIVE_OPTS = [
    "--live-describe",
    "-p", "no:terminal",
    "-p", "no:rich",
    "-p", "no:sugar",
    "-p", "no:spec",
]


def main():
    extra_args = sys.argv[1:]

    # If the path is not given explicitly — run both modules
    test_paths = [a for a in extra_args if not a.startswith("-")]
    if not test_paths:
        extra_args = [
          str(TESTS_DIR / "auction"),
          str(TESTS_DIR / "optimizer"),
          str(TESTS_DIR / "predictor"),
          str(TESTS_DIR / "simulation")
        ] + extra_args

    cmd = [
        sys.executable, "-m", "pytest",
        *_LIVE_OPTS,
        *extra_args,
    ]

    print("=" * 60)
    print(f"Launch: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if COMBINED_REPORT.exists():
        data = json.loads(COMBINED_REPORT.read_text(encoding="utf-8"))
        s = data["summary"]
        print()
        print("=" * 60)
        print(f"JSON-report: {COMBINED_REPORT}")
        print(
            f"Totally: {s['total']}  |  "
            f"passed: {s['passed']}  |  "
            f"failed: {s['failed']}  |  "
            f"error: {s['error']}  |  "
            f"skipped: {s['skipped']}"
        )
        for module, mod_data in data.get("modules", {}).items():
            ms = mod_data["summary"]
            print(
                f"  [{module}] total={ms['total']}  "
                f"passed={ms['passed']}  failed={ms['failed']}"
            )
        print("=" * 60)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
