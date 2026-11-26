"""
Root pytest plugin: collects the results of the auction, optimizer and simulation tests,
generates reports after each run.

Output files:
  tests/reports/report.json              — combined report
  tests/auction/reports/report.json      — auction only
  tests/optimizer/reports/report.json    — optimizer only
  tests/simulation/reports/report.json   — simulation only
"""

import io
import json
import re
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest

_RichLive: Any = None
_RichText: Any = None
_RichConsole: Any = None
_RICH_AVAILABLE = False

try:
    from rich.live import Live as _RichLive
    from rich.text import Text as _RichText
    from rich.console import Console as _RichConsole
    _RICH_AVAILABLE = True
except ImportError:
    pass


TESTS_DIR = Path(__file__).parent
TMP_PATH_ROOT = TESTS_DIR.parent / ".pytest_tmp_local"

_MODULE_DIRS: dict[str, Path] = {
    "auction":    TESTS_DIR / "auction",
    "adwords":    TESTS_DIR / "adwords",
    "optimizer":  TESTS_DIR / "optimizer",
    "predictor":  TESTS_DIR / "predictor",
    "simulation": TESTS_DIR / "simulation",
    "balancer":   TESTS_DIR / "balancer",
}

_MODULE_REPORTS: dict[str, Path] = {
    "auction":    TESTS_DIR / "auction"   / "reports" / "report.json",
    "adwords":    TESTS_DIR / "adwords"   / "reports" / "report.json",
    "optimizer":  TESTS_DIR / "optimizer" / "reports" / "report.json",
    "predictor":  TESTS_DIR / "predictor" / "reports" / "report.json",
    "simulation": TESTS_DIR / "simulation"/ "reports" / "report.json",
    "balancer":   TESTS_DIR / "balancer"  / "reports" / "report.json",
}

COMBINED_REPORT = TESTS_DIR / "reports" / "report.json"

_KNOWN_MODULES = tuple(_MODULE_DIRS.keys())


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _decode_pytest_id(s: str) -> str:
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)


def _detect_module(nodeid: str) -> str:
    for name in _KNOWN_MODULES:
        if f"test_{name}" in nodeid or f"/{name}/" in nodeid:
            return name
    return "unknown"


def _parse_nodeid(nodeid: str) -> tuple[str, str | None, str | None]:
    """Returns (module, func_name, case_desc)."""
    module = _detect_module(nodeid)

    m = re.match(r".*::describe_(\w+)::test_it\[(.+)\]$", nodeid)
    if m:
        return module, m.group(1), m.group(2)

    m = re.match(r".*::test_(\w+)\[(.+)\]$", nodeid)
    if m:
        return module, m.group(1), m.group(2)

    m = re.match(r".*::test_(\w+)$", nodeid)
    if m:
        return module, m.group(1), m.group(1)

    return module, None, None


def _load_tests_meta(module: str) -> dict:
    tests_json = _MODULE_DIRS.get(module, TESTS_DIR) / "tests.json"
    try:
        with open(tests_json, encoding="utf-8") as f:
            data = json.load(f)
        return {
            name: {
                "description": meta.get("description", ""),
                "signature": meta.get("signature", ""),
            }
            for name, meta in data.items()
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Live display (Rich)
# ---------------------------------------------------------------------------

_MARK  = {"passed": "✔", "failed": "✗", "error": "!", "skipped": "~"}
_COLOR = {"passed": "\033[32m", "failed": "\033[31m", "error": "\033[31m", "skipped": "\033[33m"}
_BOLD, _RESET = "\033[1m", "\033[0m"


class _LiveDisplay:
    _MARKS = {
        "passed":  ("✔", "green"),
        "failed":  ("✗", "red"),
        "error":   ("!", "bold red"),
        "skipped": ("~", "yellow"),
    }
    _SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, total: int, func_totals: dict[str, int]):
        self._total = total
        self._func_totals = func_totals
        self._done = 0
        self._func_marks: dict[str, list[tuple[str, str]]] = {}
        self._frame = 0

        self._console = _RichConsole(highlight=False, stderr=False)
        self._live = _RichLive(
            _RichText(),
            console=self._console,
            refresh_per_second=15,
            transient=False,
        )
        self._live.start()

    def _spin(self) -> str:
        s = self._SPINNER[self._frame % len(self._SPINNER)]
        self._frame += 1
        return s

    def update(self, func_name: str, status: str) -> None:
        self._done += 1
        self._func_marks.setdefault(func_name, []).append(
            self._MARKS.get(status, ("?", "white"))
        )
        self._live.update(self._render())

    def _render(self) -> Any:
        pct = int(self._done / self._total * 100) if self._total else 0
        spin = self._spin()

        t = _RichText()
        t.append(f"{spin} ", style="bold cyan")
        t.append(f"[{pct:3d}%]  ", style="bold white")
        for marks in self._func_marks.values():
            for mark, style in marks:
                t.append(mark, style=style)
        t.append("\n")

        for fname, marks in self._func_marks.items():
            total_f = self._func_totals.get(fname, 0)
            done_f = len(marks)
            pct_f = int(done_f / total_f * 100) if total_f else 100
            t.append(f"  {spin} ", style="bold cyan")
            t.append(f"[{pct_f:3d}%] ", style="dim")
            t.append(f"{fname}  ", style="cyan")
            for mark, style in marks:
                t.append(mark, style=style)
            t.append("\n")

        return t

    def stop(self) -> None:
        self._live.update(self._render())
        self._live.stop()


# ---------------------------------------------------------------------------
# Report plugin
# ---------------------------------------------------------------------------

class _ReportPlugin:
    def __init__(self, config):
        # results[module][func_name] = [case_entry, ...]
        self._results: dict[str, dict[str, list[dict]]] = {}
        self._live: bool = config.getoption("--live-describe", default=False)
        self._live_current_func: str | None = None
        self._live_display: _LiveDisplay | None = None

    # ------------------------------------------------------------------
    # Collection: build totals for rich display
    # ------------------------------------------------------------------

    def pytest_collection_finish(self, session) -> None:
        if not self._live or not _RICH_AVAILABLE:
            return
        func_totals: dict[str, int] = {}
        for item in session.items:
            _, func, _ = _parse_nodeid(item.nodeid)
            if func:
                func_totals[func] = func_totals.get(func, 0) + 1
        self._live_display = _LiveDisplay(
            total=session.testscollected,
            func_totals=func_totals,
        )

    # ------------------------------------------------------------------
    # Live progress
    # ------------------------------------------------------------------

    def _live_update(self, func_name: str, status: str) -> None:
        if self._live_display is not None:
            self._live_display.update(func_name, status)
            return

        # Fallback: plain ANSI
        use_color = sys.stdout.isatty()
        if func_name != self._live_current_func:
            if self._live_current_func is not None:
                sys.stdout.write("\n")
            label = (_BOLD + func_name + _RESET) if use_color else func_name
            sys.stdout.write(f"\n{label}  ")
            sys.stdout.flush()
            self._live_current_func = func_name

        mark = _MARK.get(status, "?")
        if use_color:
            mark = _COLOR.get(status, "") + mark + _RESET
        sys.stdout.write(mark + " ")
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Result collection
    # ------------------------------------------------------------------

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            if report.passed:
                status = "passed"
            elif report.failed:
                status = "failed"
            else:
                status = "skipped"
        elif report.when == "setup" and report.failed:
            status = "error"
        else:
            return

        module, func_name, case_desc = _parse_nodeid(report.nodeid)
        if func_name is None:
            return

        entry = {
            "description": _decode_pytest_id(case_desc) if case_desc else case_desc,
            "status": status,
            "duration": round(report.duration, 6),
        }
        self._results.setdefault(module, {}).setdefault(func_name, []).append(entry)

        if self._live:
            self._live_update(func_name, status)
            if self._live_display is None and status in ("failed", "error") and report.longrepr:
                sys.stdout.write("\n")
                for line in str(report.longrepr).splitlines():
                    sys.stdout.write("    " + line + "\n")
                sys.stdout.flush()
                self._live_current_func = None

    # ------------------------------------------------------------------
    # Report building
    # ------------------------------------------------------------------

    def _build_module_report(self, module: str, func_results: dict[str, list[dict]]):
        meta = _load_tests_meta(module)
        summary = {"total": 0, "passed": 0, "failed": 0, "error": 0, "skipped": 0}
        functions = {}

        for func_name, case_list in func_results.items():
            func_stat = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
            for c in case_list:
                s = c["status"]
                summary["total"] += 1
                summary[s] = summary.get(s, 0) + 1
                func_stat[s] = func_stat.get(s, 0) + 1

            m = meta.get(func_name, {})
            functions[func_name] = {
                "description": m.get("description", ""),
                "signature": m.get("signature", ""),
                "total": len(case_list),
                **func_stat,
                "cases": case_list,
            }

        return summary, functions

    def _build_combined_report(self):
        combined_summary = {"total": 0, "passed": 0, "failed": 0, "error": 0, "skipped": 0}
        modules_data = {}

        for module, func_results in self._results.items():
            mod_summary, mod_functions = self._build_module_report(module, func_results)
            modules_data[module] = {
                "summary": mod_summary,
                "functions": mod_functions,
            }
            for k in combined_summary:
                combined_summary[k] += mod_summary.get(k, 0)

        return combined_summary, modules_data

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------

    def _print_console_summary(self):
        if hasattr(sys.stdout, "reconfigure"):
            try:
                cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        use_color = sys.stdout.isatty()
        stdout_encoding = sys.stdout.encoding or "utf-8"

        def c(text, *codes):
            return ("".join(codes) + text + _RESET) if use_color else text

        def safe(text):
            return str(text).encode(stdout_encoding, errors="replace").decode(
                stdout_encoding,
                errors="replace",
            )

        for module, func_results in self._results.items():
            sep = "=" * 25
            label = module.capitalize()
            print(f"\n{sep} {label} Test Cases {sep}")
            for func_name, case_list in func_results.items():
                total = len(case_list)
                n_passed = sum(1 for case in case_list if case["status"] == "passed")
                all_ok = n_passed == total
                counter_color = "\033[32m" if all_ok else "\033[31m"
                print(f"\n{c(func_name, _BOLD)}  {c(f'[{n_passed}/{total} passed]', counter_color)}")
                for case in case_list:
                    st = case["status"]
                    mark = _MARK.get(st, "?")
                    color = _COLOR.get(st, "")
                    print(f"  {c(mark, color)} {safe(case['description'])}  ({case['duration']}s)")

    # ------------------------------------------------------------------
    # Session finish
    # ------------------------------------------------------------------

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        if self._live_display is not None:
            self._live_display.stop()
            self._live_display = None
        elif self._live and self._live_current_func is not None:
            sys.stdout.write("\n")
            sys.stdout.flush()

        combined_summary, modules_data = self._build_combined_report()
        now = datetime.now().isoformat(timespec="seconds")

        # Combined report
        combined_report = {
            "generated_at": now,
            "summary": combined_summary,
            "modules": modules_data,
        }
        COMBINED_REPORT.parent.mkdir(parents=True, exist_ok=True)
        with open(COMBINED_REPORT, "w", encoding="utf-8") as f:
            json.dump(combined_report, f, ensure_ascii=False, indent=2)

        # Separate reports for each module
        for module, mod_data in modules_data.items():
            mod_report_path = _MODULE_REPORTS.get(module)
            if mod_report_path:
                mod_report = {
                    "generated_at": now,
                    "summary": mod_data["summary"],
                    "functions": mod_data["functions"],
                }
                mod_report_path.parent.mkdir(parents=True, exist_ok=True)
                with open(mod_report_path, "w", encoding="utf-8") as f:
                    json.dump(mod_report, f, ensure_ascii=False, indent=2)

        self._print_console_summary()


# ---------------------------------------------------------------------------
# Pytest hooks
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    try:
        parser.addoption(
            "--live-describe",
            action="store_true",
            default=False,
            help="Live per-describe-block progress with checkmarks",
        )
    except ValueError:
        pass  # already registered (several conftest.py)


def pytest_configure(config):
    config.pluginmanager.register(_ReportPlugin(config), "unified_report_plugin")


@pytest.fixture
def tmp_path(request):
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)
    path = TMP_PATH_ROOT / f"{safe_name}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
