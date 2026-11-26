"""
Generator of a Markdown report from the benchmark results.

Report structure:
  - Header with the date, parameters, simplifications
  - Summary table of all scenarios (impressions / fill_rate / revenue)
  - Detailed sections for each scenario
    - Conditions (companies, volumes, match_rate)
    - Table of classic strategies (1 run)
    - Tables A2 and A3 (min/max/median/mean over N runs)
    - Text conclusion on the applicability limits
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from .seeds import CLASSIC_STRATEGIES, VOCABS, BASE_COMPANIES
from benchmarks import report_privacy as privacy

for _values in VOCABS.values():
    privacy.register(_values)
for _company in BASE_COMPANIES:
    privacy.register([_company["name"]])

BALANCER_STRATEGY = "balancer"  # the same name as in engine.BALANCER_STRATEGY

if TYPE_CHECKING:
    from .engine import SingleRunResult, MultiRunStats


# ─── Number formatting ──────────────────────────────────────────────────

def _fmt_int(n: int | float) -> str:
    return f"{int(n):,}".replace(",", " ")

def _fmt_float(v: float, decimals: int = 1) -> str:
    return f"{v:,.{decimals}f}".replace(",", " ")

def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"

def _fmt_cpm(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


# ─── Table utilities ────────────────────────────────────────────────────

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(h), max((len(r[i]) for r in rows), default=0))
              for i, h in enumerate(headers)]
    sep  = "| " + " | ".join("-" * w for w in widths) + " |"
    head = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    body = "\n".join(
        "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)) + " |"
        for row in rows
    )
    return privacy.markdown("\n".join([head, sep, body]))


# ─── Sections ───────────────────────────────────────────────────────────────

def _scenario_header(
    n_companies: int,
    n_requests: int,
    traffic_type: str,
    ad_data: dict,
) -> str:
    traffic_label = {
        "balanced": "Balanced",
        "shortage":  "Lack of traffic",
        "excess":    "Excess traffic",
    }[traffic_type]

    total_volume = sum(d["volume"] for d in ad_data.values())
    total_budget = sum(d["budget"] for d in ad_data.values())
    avg_cpm = sum(d["cpm"] for d in ad_data.values()) / len(ad_data) if ad_data else 0

    lines = [f"### Scenario conditions\n"]
    params_rows = [
        ["Campaigns",              str(n_companies)],
        ["Requests",              _fmt_int(n_requests)],
        ["Type of traffic",           traffic_label],
        ["Total volume (A2)", f"{_fmt_int(total_volume)} impressions"],
        ["Total budget (A3)", f"{_fmt_cpm(total_budget)} units."],
        ["e-CPM",                 _fmt_float(avg_cpm)],
    ]
    lines.append(_md_table(["Parameter", "Value"], params_rows))
    lines.append("")
    lines.append("#### Companies-participant\n")

    comp_rows = [
        [data["name"], f"{data['match_rate']*100:.1f}%",
         f"{data['cpm']:.0f}", f"{data['priority']:.1f}",
         _fmt_int(data["volume"]), _fmt_cpm(data["budget"])]
        for ad_id, data in ad_data.items()
    ]
    lines.append(
        _md_table(
            ["Campaign", "Match rate", "CPM", "Priority", "Volume (A2)", "Budget (A3)"],
            comp_rows,
        )
    )
    return "\n".join(lines)


def _classic_table(classic_results: dict) -> str:
    headers = [
        "Strategy", "Impressions", "Fill rate", "Miss rate",
        "Revenue", "Avg.CPM/display",
    ]
    rows = []
    for strategy, res in classic_results.items():
        rows.append([
            strategy,
            _fmt_int(res.total_impressions),
            _fmt_pct(res.fill_rate),
            _fmt_pct(res.miss_rate),
            _fmt_cpm(res.total_revenue),
            _fmt_float(res.avg_cpm_per_hit, 1),
        ])
    return "#### Classic strategies (1 run)\n\n" + _md_table(headers, rows)


def _adwords_stats_table(stats) -> str:
    """Min/max/median/mean table for one algorithm."""
    algo_label = {
        "a2_single_valued": "A2 (Single-Valued, Vazirani)",
        "a3_small":         "A3 (Small Budget, Vazirani)",
    }.get(stats.algorithm, stats.algorithm)

    lines = [f"#### {algo_label} — {stats.n_runs} runs\n"]

    headers = ["Metric", "Min", "Max", "Median", "Mean"]
    rows = [
        ["Impressions",
         _fmt_int(stats.impressions_min),
         _fmt_int(stats.impressions_max),
         _fmt_int(stats.impressions_median),
         _fmt_float(stats.impressions_mean, 0)],
        ["Fill rate",
         _fmt_pct(stats.fill_rate_min),
         _fmt_pct(stats.fill_rate_max),
         _fmt_pct(stats.fill_rate_median),
         _fmt_pct(stats.fill_rate_mean)],
        ["Revenue",
         _fmt_cpm(stats.revenue_min),
         _fmt_cpm(stats.revenue_max),
         _fmt_cpm(stats.revenue_median),
         _fmt_cpm(stats.revenue_mean)],
    ]
    lines.append(_md_table(headers, rows))

    # Variation of impressions
    spread = stats.impressions_max - stats.impressions_min
    spread_pct = spread / stats.impressions_mean * 100 if stats.impressions_mean else 0
    lines.append(f"\n> Impression spread: {_fmt_int(spread)} ({spread_pct:.1f}% of the mean)")

    return "\n".join(lines)


def _applicability_note(
    n_companies: int,
    n_requests: int,
    traffic_type: str,
    classic_results: dict,
    adwords_results: dict,
) -> str:
    """Automatic text conclusion on the applicability limits."""
    lines = ["\n#### Applicability assessment\n"]

    # Compare best_price (greedy) with a2/a3
    ref = classic_results.get("best_price")
    a2  = adwords_results.get("a2_single_valued")
    a3  = adwords_results.get("a3_small")

    if ref and a2:
        a2_vs_ref = (a2.impressions_mean - ref.total_impressions) / ref.total_impressions * 100
        rev_vs_ref = (a2.revenue_mean - ref.total_revenue) / ref.total_revenue * 100 if ref.total_revenue else 0
        lines.append(
            f"- **A2 vs best_price**: impressions {'+'if a2_vs_ref>=0 else ''}{a2_vs_ref:.1f}%, "
            f"revenue {'+'if rev_vs_ref>=0 else ''}{rev_vs_ref:.1f}%"
        )

    if ref and a3:
        a3_vs_ref = (a3.impressions_mean - ref.total_impressions) / ref.total_impressions * 100
        rev3_vs_ref = (a3.revenue_mean - ref.total_revenue) / ref.total_revenue * 100 if ref.total_revenue else 0
        lines.append(
            f"- **A3 vs best_price**: impressions {'+'if a3_vs_ref>=0 else ''}{a3_vs_ref:.1f}%, "
            f"revenue {'+'if rev3_vs_ref>=0 else ''}{rev3_vs_ref:.1f}%"
        )

    bal = classic_results.get(BALANCER_STRATEGY)
    if ref and bal:
        imp_vs = (bal.total_impressions - ref.total_impressions) / ref.total_impressions * 100 if ref.total_impressions else 0
        rev_vs = (bal.total_revenue - ref.total_revenue) / ref.total_revenue * 100 if ref.total_revenue else 0
        lines.append(
            f"- **balancer vs best_price**: impressions {'+'if imp_vs>=0 else ''}{imp_vs:.1f}%, "
            f"revenue {'+'if rev_vs>=0 else ''}{rev_vs:.1f}%"
        )

    # Stability of A2/A3 (spread)
    if a2:
        spread_pct = (a2.impressions_max - a2.impressions_min) / a2.impressions_mean * 100 if a2.impressions_mean else 0
        stability = "high" if spread_pct < 5 else ("moderate" if spread_pct < 15 else "lowly")
        lines.append(f"- **A2 stability**: {stability} (spread {spread_pct:.1f}%)")

    if a3:
        spread_pct = (a3.impressions_max - a3.impressions_min) / a3.impressions_mean * 100 if a3.impressions_mean else 0
        stability = "high" if spread_pct < 5 else ("moderate" if spread_pct < 15 else "lowly")
        lines.append(f"- **A3 stability**: {stability} (spread {spread_pct:.1f}%)")

    # Traffic specifics
    if traffic_type == "shortage":
        lines.append(
            "- **Lack of traffic**: Requests less than the total number of ads; "
            "volume is not a limitation; algorithmic differences — Only in the distribution of revenue by company."
        )
    elif traffic_type == "excess":
        lines.append(
            "- **Excess traffic**: More than the total number of ads; "
            "All algorithms are limited by the number of impressions available; "
            "adwords They may show a little less of the-randomly."
        )

    return "\n".join(lines)


def _per_ad_breakdown(
    classic_results: dict,
    adwords_results: dict,
    ad_data: dict,
) -> str:
    """Table of impressions per ad for each algorithm."""
    ad_ids = list(ad_data.keys())
    ad_names = [ad_data[aid]["name"] for aid in ad_ids]
    volumes = [ad_data[aid]["volume"] for aid in ad_ids]

    col_headers = ["Ad", "Volume"] + \
                  list(classic_results.keys()) + \
                  [f"{k} (Wed.)" for k in adwords_results.keys()]

    rows = []
    for i, (aid, name, vol) in enumerate(zip(ad_ids, ad_names, volumes)):
        row = [privacy.tag_label(name), _fmt_int(vol)]
        for res in classic_results.values():
            imp = res.per_ad_impressions.get(aid, 0)
            util = imp / vol * 100 if vol > 0 else 0
            row.append(f"{_fmt_int(imp)} ({util:.0f}%)")
        for stats in adwords_results.values():
            mean_imp = sum(r.per_ad_impressions.get(aid, 0)
                           for r in stats.per_run_results) / stats.n_runs if stats.n_runs else 0
            util = mean_imp / vol * 100 if vol > 0 else 0
            row.append(f"{_fmt_int(mean_imp)} ({util:.0f}%)")
        rows.append(row)

    return "#### Advertising displays (impressions (disposal volume))\n\n" + _md_table(col_headers, rows)


# ─── Public interface ──────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """GitHub-style anchor for a heading: lower-case, no punctuation, spaces → hyphens."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def scenario_title(
    n_companies: int,
    n_requests: int,
    traffic_type: str,
    scenario_index: int = 0,
) -> str:
    """Text of the scenario section heading (without the leading '## ').

    n_requests — the actual number of requests sent (not the nominal value
    of the scenario matrix, which depends on traffic_type).
    """
    traffic_label = {
        "balanced": "balanced",
        "shortage":  "lack of",
        "excess":    "excess",
    }[traffic_type]

    return (f"Script {scenario_index}: "
            f"{n_companies} campaigns, {_fmt_int(n_requests)} requests, {traffic_label}")


def scenario_anchor(
    n_companies: int,
    n_requests: int,
    traffic_type: str,
    scenario_index: int = 0,
) -> str:
    """Anchor ('#...') matching the scenario heading."""
    return _slugify(scenario_title(n_companies, n_requests, traffic_type, scenario_index))


def write_toc(f, toc_entries: list[tuple[int, int, int, str]]) -> None:
    """Writes a table of contents with links to all scenario sections.

    toc_entries: list of (scenario_index, n_companies, n_requests, traffic_type).
    """
    f.write("## Table of contents\n\n")
    for sc_idx, n_companies, n_requests, traffic_type in toc_entries:
        title = scenario_title(n_companies, n_requests, traffic_type, sc_idx)
        anchor = _slugify(title)
        f.write(f"- [{title}](#{anchor})\n")
    f.write("\n---\n\n")


def format_scenario_section(
    n_companies: int,
    n_requests: int,
    traffic_type: str,
    ad_data: dict,
    classic_results: dict,
    adwords_results: dict,
    scenario_index: int = 0,
) -> str:
    """Builds the full Markdown section for one scenario."""
    privacy.register(data["name"] for data in ad_data.values())
    parts = [
        f"## {scenario_title(n_companies, n_requests, traffic_type, scenario_index)}\n",
        _scenario_header(n_companies, n_requests, traffic_type, ad_data),
        "",
        _classic_table(classic_results),
        "",
    ]

    for stats in adwords_results.values():
        parts.append(_adwords_stats_table(stats))
        parts.append("")

    if len(ad_data) <= 20:
        # Full per-ad table only for small scenarios
        parts.append(_per_ad_breakdown(classic_results, adwords_results, ad_data))
        parts.append("")

    parts.append(
        _applicability_note(
            n_companies, n_requests, traffic_type,
            classic_results, adwords_results,
        )
    )
    parts.append("\n---\n")
    return privacy.markdown("\n".join(parts))


def write_report_header(
    f,
    total_scenarios: int,
    adwords_runs_map: dict,
    simplifications: list[str],
) -> None:
    """Writes the report header."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    f.write(f"# Comparative benchmark of auction algorithms\n\n")
    f.write(f"_Generated: {ts}_\n\n")
    f.write(f"## Launch parameters\n\n")
    f.write(f"- All scenarios: {total_scenarios}\n")
    f.write("- Runaways A2/A3 number of requests:\n")
    for n, r in sorted(adwords_runs_map.items()):
        label = {10_000:"10k",100_000:"100k",1_000_000:"1M",10_000_000:"10M"}.get(n,str(n))
        f.write(f"  - {label} requests → {r} runs\n")
    f.write("\n## Assumption and simplification\n\n")
    for s in simplifications:
        f.write(f"- {s}\n")
    f.write("\n---\n\n")


HYBRID_STRATEGIES = [s for s in CLASSIC_STRATEGIES if "hybrid" in s]


def hybrid_summary_cells(classic_results: dict) -> list[str]:
    """Cells of the summary table for the hybrid strategies: impressions and revenue of each."""
    cells = []
    for strat in HYBRID_STRATEGIES:
        res = classic_results.get(strat)
        cells.append(_fmt_int(res.total_impressions) if res else "—")
        cells.append(_fmt_cpm(res.total_revenue) if res else "—")
    return cells


def balancer_summary_cells(classic_results: dict) -> list[str]:
    """Cells of the summary table for the balancer: impressions and revenue."""
    res = classic_results.get(BALANCER_STRATEGY)
    if not res:
        return ["—", "—"]
    return [_fmt_int(res.total_impressions), _fmt_cpm(res.total_revenue)]


SUMMARY_METRICS = [
    "Campaigns", "Requests", "Traffic", "Common volume company",
    "best_price impressions", "A2 impressions (Wed.)", "A3 impressions (Wed.)",
    "best_price revenue", "A2 revenue (Wed.)", "A3 revenue (Wed.)",
    "Sellout",
]


def build_summary_row(
    scenario_index: int,
    n_companies: int,
    n_requests_label: str,
    traffic_type: str,
    total_volume: int,
    bp_impressions, a2_impressions, a3_impressions,
    bp_revenue, a2_revenue, a3_revenue,
    sellout: str,
    hybrid_cells: list[str],
) -> list[str]:
    """Collects one row of summary data (not yet transposed)."""
    return [
        str(scenario_index),
        str(n_companies),
        n_requests_label,
        traffic_type,
        _fmt_int(total_volume),
        _fmt_int(bp_impressions) if bp_impressions is not None else "—",
        _fmt_int(a2_impressions) if a2_impressions is not None else "—",
        _fmt_int(a3_impressions) if a3_impressions is not None else "—",
        _fmt_cpm(bp_revenue) if bp_revenue is not None else "—",
        _fmt_cpm(a2_revenue) if a2_revenue is not None else "—",
        _fmt_cpm(a3_revenue) if a3_revenue is not None else "—",
        sellout,
        *hybrid_cells,
    ]


def write_summary_table(f, summary_rows: list[list[str]]) -> None:
    """Writes the summary table of all scenarios — transposed: scenarios in columns,
    metrics in rows (with a large number of strategies the usual orientation becomes too wide)."""
    f.write("## Summary table\n\n")

    metric_names = list(SUMMARY_METRICS)
    for strat in HYBRID_STRATEGIES:
        metric_names += [f"{strat} impressions", f"{strat} revenue"]
    metric_names += [f"{BALANCER_STRATEGY} impressions", f"{BALANCER_STRATEGY} revenue"]

    col_headers = ["Metric"] + [f"№{row[0]}" for row in summary_rows]
    rows = [
        [metric] + [row[i] for row in summary_rows]
        for i, metric in enumerate(metric_names, start=1)
    ]
    f.write(_md_table(col_headers, rows))
    f.write("\n\n---\n\n")


REPORT_SIMPLIFICATIONS = [
    "Balancer (`balancer`): `balance_traffic` (objective=maximize_money,"
    " total_traffic_volume = number of script requests) + balancer."
    " Weights of the auction are precalculated according to the formula SDK tagging; pronouncement,"
    " exhausted volume, pop out; zero-weight request — flop.",
    "Filtration: only precise match predefined vocab-restraint.",
    "Frequency limits of users (user_frequency_limit) and min_interval not applied.",
    "For classic strategies velocity/heuristics monthly counter = total"
    " run-in (the whole run is considered one «month-long»).",
    "Volume-The limitation for classical strategies is applied at the level of the benchmark engine,"
    " not through SDK-filter.",
    "Classical strategies implemented directly (calllessly `auction()` of SDK) for"
    " productivity; logic is identical SDK-implementation.",
    "For A2 and A3 The flow of requests is the same in all N runaway; change"
    " price-initiation `pj = exp(wj - 1)`.",
    "Budget for A3 = volume × CPM pronouncement (money-equivalent volume).",
    "Volume Companies do not depend on traffic_type: capacitance"
    " ≈ 115% script-nominal (stockpile, if balanced saturated volume"
    " on its own) It is divided between companies proportionally match_rate."
    " Traffic_type Regulates the number of actually sent requests:"
    " shortage ×0.5, balanced ×1, excess ×2 nominally — report everywhere"
    " the actual number of requests.",
]
