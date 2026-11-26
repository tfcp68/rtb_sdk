"""Markdown/JSON report of the log benchmark."""
from __future__ import annotations

import sys as _privacy_sys
from pathlib import Path as _PrivacyPath
_privacy_sys.path.insert(0, str(_PrivacyPath(__file__).resolve().parents[2]))
from benchmarks import report_privacy as privacy

import json
import os
from datetime import datetime

from engine_full import AdPack, RunResult, CLASSIC_STRATEGIES, BALANCER, BALANCER_TEMPORAL, ADWORDS


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _int(v) -> str:
    return f"{int(round(v)):,}".replace(",", " ")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def scenario_title(sc: dict) -> str:
    return (f"{sc['period']} · {sc['traffic']} · {sc['n_ads']} company · "
            f"{_int(sc['requests'])} requests")


def scenario_section(idx: int, sc: dict, pack: AdPack, results: dict[str, RunResult]) -> str:
    total_vol = sum(pack.volume)
    L = [f"## {idx}. {scenario_title(sc)}\n"]
    L.append(_table(["Parameter", "Value"], [
        ["Period", f"{sc['days']} days. ({sc['period']})"],
        ["Type of traffic", f"{sc['traffic']} (×{sc['traffic_factor']})"],
        ["Percentage of users (sample)", f"{sc['sample']:.4f}"],
        ["Nominal requests", _int(sc["nominal"])],
        ["Running requests", _int(sc["requests"])],
        ["Total volume company", f"{_int(total_vol)} (×{sc['volume_factor']} nominally)"],
        ["Requests / volume", f"{sc['requests'] / total_vol:.2f}"],
    ]))

    # ── main table ──
    base_rev = None
    rows = []
    order = [a for a in CLASSIC_STRATEGIES + [BALANCER, BALANCER_TEMPORAL] + ADWORDS if a in results]
    order += [a for a in results if a not in order]
    for a in order:
        r = results[a]
        imp = r.total_impressions
        if a == "best_price":
            base_rev = r.revenue
        rows.append([a, _int(imp), _pct(r.fill_rate), _int(r.revenue),
                     f"{r.revenue / imp:.1f}" if imp else "—",
                     _pct(imp / total_vol),
                     _pct(r.miss_nomatch / r.requests),
                     _pct(r.miss_filtered / r.requests),
                     _pct(r.miss_algo / r.requests) if r.miss_algo else "—",
                     _pct(r.miss_by_limits / r.requests),
                     f"{r.seconds:.0f}"])
    if base_rev:
        for row, a in zip(rows, order):
            row.insert(4, f"{results[a].revenue / base_rev * 100:.1f}%")
        hdr = ["Algorithm", "Impressions", "Fill", "Revenue", "Revenue/best_price", "Avg. CPM", "Sellout",
               "No targeting", "Filters cut off", "Algorithm failure", "Lost from-limitless", "Time, s"]
    else:
        hdr = ["Algorithm", "Impressions", "Fill", "Revenue", "Avg. CPM", "Sellout",
               "No targeting", "Filters cut off", "Algorithm failure", "Lost from-limitless", "Time, s"]
    L.append("### Algorithm results\n")
    L.append(_table(hdr, rows))
    L.append("> Fill = impressions / request; Sellout = impressions / summative volume; «No targeting» — requesting "
             "single-company; «Filters cut off» — fitting, but they’re all exhausted volume "
             "or bound by limits/window; «Lost from-limitless» — share of requests without display, pool "
             "The candidates were emptied and among those eliminated were cut off by frequency limits/min_interval "
             "(subset «Filters cut off»).\n")

    # ── candidate rejections ──
    rows = []
    for a in order:
        r = results[a]
        tot = r.rej_volume + r.rej_ad_limit + r.rej_user_limit + r.rej_min_interval + r.rej_inactive
        rows.append([a, _int(r.rej_volume), _int(r.rej_ad_limit), _int(r.rej_user_limit),
                     _int(r.rej_min_interval), _int(r.rej_inactive), _int(tot)])
    L.append("### Cut-off of candidates (query × company)\n")
    L.append(_table(["Algorithm", "volume exhausted", "ad_frequency_limit", "user_frequency_limit",
                     "min_interval", "outside start/end", "Total"], rows))

    # ── by day ──
    if sc["days"] > 1:
        L.append("### Shows by day\n")
        L.append(_table(["Algorithm"] + [f"d{d + 1}" for d in range(sc["days"])],
                        [[a] + [_int(x) for x in results[a].day_impressions] for a in order]))

    # ── by company ──
    L.append("### Implementation volume company (% from volume)\n")
    show = [a for a in ("best_one", "best_price", "best_velocity", "best_heuristics", "best_hybrid_0.2",
                        "random_hybrid_0.5", BALANCER, BALANCER_TEMPORAL, "a2_single_valued", "a3_small") if a in results]
    rows = []
    for i in range(pack.n):
        rows.append([pack.ids[i], pack.names[i], f"{pack.cpm[i]:.0f}", _pct(pack.match_rate[i]),
                     _int(pack.volume[i])] +
                    [_pct(results[a].impressions[i] / pack.volume[i]) for a in show])
    L.append(_table(["id", "Name", "CPM", "Match", "Volume"] + show, rows))
    return "\n".join(L) + "\n"


def write_report(path: str, header: dict, sections: list[str], summary_rows: list[list[str]], notes: list[str]) -> None:
    L = [f"# Benchmark Auctions on Real Logs\n",
         f"_Formed: {datetime.now():%Y-%m-%d %H:%M}_\n",
         "## Launch parameters\n",
         _table(["Parameter", "Value"], [[k, str(v)] for k, v in header.items()]),
         "## Simplifications and features\n"]
    L += [f"- {n}" for n in notes]
    L.append("")
    if summary_rows:
        L.append("## Summary (impressions / revenue % from best_price)\n")
        L.append(_table(summary_rows[0], summary_rows[1:]))
    L += sections
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(privacy.markdown("\n".join(L)))


def dump_json(path: str, scenarios: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(privacy.report(scenarios), f, ensure_ascii=False)
