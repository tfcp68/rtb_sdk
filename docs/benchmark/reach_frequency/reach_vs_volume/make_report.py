"""
Generator of the weekly reach-vs-volume report from an EXECUTED notebook
check_reach_vs_volume.ipynb.

Does not require access to the parquet logs: reads only the saved outputs of the notebook
(the export cell printing JSON between REPORT_JSON_BEGIN/END, and the images from
the chart cells) and assembles `reports/<week>.md` + `reports/<week>/img/*.png`.

Workflow for a new week:

    1. In check_reach_vs_volume.ipynb change PARQUET_FILE to the needed week,
       run Run All (the last metrics export cell is mandatory).
    2. Save the notebook (with outputs).
    3. python make_report.py            # or --notebook / --reports-dir

The script takes the week name from the parquet file name (e.g. report-20260601)
and writes the report under the corresponding `report-YYYYMMDD` name.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

# Signatures (substrings in the cell source) -> image file name + caption.
# We match by the text of the chart title, not by cell id -- robust to
# cell recreation.
FIGURES = [
    ("w_h vs reach_share_h clockwise", "01_wh_vs_reach_share.png"),
    ("freq_h clockwise", "02_freq_and_hist.png"),
    ("Coverage by user segments", "03_segment_composition.png"),
    ("Correlation freq_h / diff", "04_correlation.png"),
    ("reach_h by (weekday, hour)", "05_dow_hour_heatmap.png"),
]

SEGMENTS = ["casual", "active", "superactive", "bot"]


# --------------------------------------------------------------------------- #
# Reading the notebook
# --------------------------------------------------------------------------- #
def load_notebook(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cell_source(cell: dict) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else src


def iter_stream_text(cell: dict):
    for out in cell.get("outputs", []):
        if out.get("output_type") == "stream":
            txt = out.get("text", "")
            yield "".join(txt) if isinstance(txt, list) else txt


def extract_report_json(nb: dict) -> dict:
    """Looks for the REPORT_JSON_BEGIN/END block in the outputs and parses the JSON."""
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        for text in iter_stream_text(cell):
            if "REPORT_JSON_BEGIN" not in text:
                continue
            body = text.split("REPORT_JSON_BEGIN", 1)[1]
            body = body.split("REPORT_JSON_END", 1)[0].strip()
            return json.loads(body)
    raise SystemExit(
        "No block found REPORT_JSON_BEGIN/END notebook.\n"
        "Do it Run All, including the latest export metrics, and save the notebook."
    )


def first_png(cell: dict) -> bytes | None:
    for out in cell.get("outputs", []):
        data = out.get("data", {})
        if "image/png" in data:
            png = data["image/png"]
            if isinstance(png, list):
                png = "".join(png)
            return base64.b64decode(png)
    return None


def extract_figures(nb: dict, img_dir: Path) -> list[str]:
    """Saves PNGs from the chart cells; returns a list of missing signatures."""
    img_dir.mkdir(parents=True, exist_ok=True)
    missing = []
    for signature, fname in FIGURES:
        found = False
        for cell in nb["cells"]:
            if cell.get("cell_type") != "code":
                continue
            if signature in cell_source(cell):
                png = first_png(cell)
                if png is not None:
                    (img_dir / fname).write_bytes(png)
                    found = True
                break
        if not found:
            missing.append((signature, fname))
    return missing


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def thous(x) -> str:
    return f"{int(round(x)):,}".replace(",", " ")  # narrow no-break space


def f4(x) -> str:
    return f"{x:.4f}"


def pct(x) -> str:
    return f"{x * 100:.2f}%"


def verdict_text(h1: bool) -> str:
    return "H1 (decomposition is needed)" if h1 else "H0 (current `w_h` sufficient)"


# --------------------------------------------------------------------------- #
# Rendering markdown
# --------------------------------------------------------------------------- #
def render_md(R: dict) -> str:
    week = R["week"].removeprefix("report-").removeprefix("janus-")
    report_name = f"report-{week}"
    has_daily = "tv_daily" in R
    has_corr = "corr_freq" in R
    has_dow = "cov_freq_weekday" in R

    L = []  # report lines
    L.append(f"# Reach vs Volume — weekly report `{week}`\n")
    L.append(
        "Testing a hypothesis from [`../hypothesis.md`](../hypothesis.md): mix up "
        "hour-weight `w_h` (share **volume**, used `build_seasonal_context`) "
        "coverage (`reach_h` — number of users) frequency (`freq_h` — impressions "
        "user-on), and whether the composition of user segments varies by hour.\n"
    )

    daily_clause = (
        f" (or {pct(R['tv_daily'])} daytime reach)" if has_daily else ""
    )
    L.append(
        f"> **Verdict (primary hypothesis.md, step 5): "
        f"{'H1' if R['h1_primary'] else 'H0'}** — `w_h` "
        f"{'lacking' if R['h1_primary'] else 'sufficient as a proxy coverage'}. "
        f"Cumulative Systematic Shift Transfers **{pct(R['tv_weekly'])}**"
        f"{daily_clause} campaign screenings between morning and evening — check "
        f"persistence in other weeks, beforehand.\n"
    )
    L.append("---\n")

    # 1. Conditions
    L.append("## 1. Experiment conditions\n")
    L.append("| Parameter | Value |")
    L.append("|---|---|")
    source = R["parquet_file"].replace("janus-", "report-")
    L.append(f"| Source | `{source}` |")
    L.append(f"| Period (after `AT TIME ZONE`) | `{R['date_start']}` — `{R['date_end']}` |")
    L.append(f"| `MODE` | `{R['mode']}` |")
    L.append(f"| `TIMEZONE` | `{R['timezone']}` |")
    L.append(f"| Total events | **{thous(R['total_records'])}** |")
    L.append(f"| Hour buckets with data | {R['n_buckets']} |")
    empty_pct = R["empty_user_frac"] * 100
    empty_note = (
        "negligible, does **not** distort reach/segments"
        if R["empty_user_frac"] < 0.02 else
        "substantial — check reach/frequency"
    )
    L.append(
        f"| `EmptyUser` (no `client_id`) | {thous(R['empty_user_events'])} events = "
        f"{empty_pct:.4f}% → segment `{R['empty_user_segment']}` ({empty_note}) |"
    )
    L.append(
        f"| Threshold | `COV_THRESHOLD = {R['cov_threshold']}`, "
        f"`DIFF_THRESHOLD = {R['diff_threshold']}` |"
    )
    L.append(f"| `CAMPAIGN_VOLUME` | {thous(R['campaign_volume'])} impressions |")
    L.append(
        "| Segments (percentile) | casual 0–60% · active 60–90% · "
        "superactive 90–98% · bot 98–100% |\n"
    )
    L.append(
        "**Method (briefly).** In one pass, we materialize `(h, uid, ts)` and compute "
        "`counts[h]`, `reach[h] = COUNT(DISTINCT uid)`, and `freq[h] = counts/reach`. "
        "We compare `w_h = normalize(counts)` (the current model) with "
        "`reach_share_h = normalize(reach)` (needed for user-capped campaigns). "
        "Hour bucketing uses the same `_get_h_type` logic as production.\n"
    )
    L.append("---\n")

    # 2. Results
    L.append("## 2. Key results\n")
    L.append("### 2.1 Primary verdict (prearranged)\n")
    L.append("| Metric | Value | Thread | Outcome |")
    L.append("|---|---|---|---|")
    cov_ok = "H1" if R["cov_freq"] > R["cov_threshold"] else "H0"
    diff_ok = "H1" if R["max_diff"] > R["diff_threshold"] else "H0"
    L.append(f"| `CoV(freq_h)` | **{f4(R['cov_freq'])}** | {R['cov_threshold']} | {cov_ok} |")
    L.append(
        f"| `max\\|w_h − reach_share_h\\|` | **{f4(R['max_diff'])}** | "
        f"{R['diff_threshold']} | {diff_ok} |"
    )
    L.append(f"| `Pearson(w_h, reach_share_h)` | {R['pearson']:.3f} | — | — |")
    L.append(f"| `Spearman(w_h, reach_share_h)` | {R['spearman']:.3f} | — | — |")
    L.append(f"| **Verdict** | | | **{verdict_text(R['h1_primary'])}** |\n")

    L.append("### 2.2 Magnitude of the divergence in impressions\n")
    L.append(
        "> **TV (Total Variation distance)** = `½·Σ_h |w_h − reach_share_h|` — a single "
        "number from 0 to 1: **the share of a campaign's impressions that lie in the "
        "wrong hour** if weights are switched from volume-based (`w_h`) to reach-based "
        "(`reach_share_h`). 0 means the distributions coincide. The factor ½ avoids "
        "counting each moved impression twice (once leaving and once arriving).\n"
    )
    L.append(
        "The bias is **systematic and monotone** (morning reach is underrepresented, "
        "evening reach overrepresented), so hourly errors add up rather than cancel. "
        "Therefore, the meaningful scale is TV (total divergence), not the worst "
        "single hour (`max|diff|`):\n"
    )
    L.append("| Reach denominator | `max\\|diff\\|` | TV | Impressions per "
             + thous(R["campaign_volume"]) + " campaign | For which limit |")
    L.append("|---|---|---|---|---|")
    L.append(
        f"| Weekly-unique (`reach_share_h`) | {f4(R['max_diff'])} | "
        f"**{f4(R['tv_weekly'])} ({pct(R['tv_weekly'])})** | "
        f"{thous(R['misallocated_weekly'])} | weekly `'w'` |"
    )
    if has_daily:
        L.append(
            f"| Daytime-averaged (`reach_share_daily`) | {f4(R['max_diff_daily'])} | "
            f"**{f4(R['tv_daily'])} ({pct(R['tv_daily'])})** | "
            f"{thous(R['misallocated_daily'])} | **daytime `'d'`** |"
        )
        artifact = (R["tv_weekly"] - R["tv_daily"]) / R["tv_weekly"] * 100
        L.append(
            f"\n→ ~{artifact:.0f}% weekly divergence — denominator "
            "(weekly-unique reach It understates coverage in the evening "
            "regular visitors). For the daytime `user_frequency_limit` real "
            f"displacement **{pct(R['tv_daily'])}**, weekly **{pct(R['tv_weekly'])}**.\n"
        )
    else:
        L.append("")

    L.append("### 2.3 Hourly peaks\n")
    L.append("| Metric | Peak | Trough |")
    L.append("|---|---|---|")
    p = R["peaks"]
    L.append(f"| counts (volume) | hour {p['counts']['peak_h']} — {thous(p['counts']['peak'])} | "
             f"hour {p['counts']['low_h']} — {thous(p['counts']['low'])} |")
    L.append(f"| reach (unique users) | hour {p['reach']['peak_h']} — {thous(p['reach']['peak'])} | "
             f"hour {p['reach']['low_h']} — {thous(p['reach']['low'])} |")
    L.append(f"| freq (per user) | hour {p['freq']['peak_h']} — {p['freq']['peak']:.2f} | "
             f"hour {p['freq']['low_h']} — {p['freq']['low']:.2f} |\n")
    L.append("---\n")

    # 3. Charts
    L.append("## 3. Charts\n")
    L.append("### 3.1 `w_h` (volume) vs `reach_share_h` (reach) by hour\n")
    L.append(f"![w_h vs reach_share_h]({report_name}/img/01_wh_vs_reach_share.png)\n")
    L.append(f"Pearson {R['pearson']:.2f} — the divergence is small in every hour, but "
             "systematic: morning reach is slightly higher than volume, evening reach lower.\n")

    L.append("### 3.2 `freq_h` by hour + distribution\n")
    L.append(f"![freq_h]({report_name}/img/02_freq_and_hist.png)\n")
    L.append(f"`CoV(freq_h) = {f4(R['cov_freq'])}` "
             f"({'higher' if R['cov_freq'] > R['cov_threshold'] else 'below'} "
             f"threshold {R['cov_threshold']}).\n")

    L.append("### 3.3 Composition of reach by segment, by hour\n")
    L.append(f"![segments]({report_name}/img/03_segment_composition.png)\n")
    sp = R["segment_peaks"]
    sa, bt = sp["superactive"], sp["bot"]
    sa_ratio = sa["peak"] / sa["low"] if sa["low"] else float("nan")
    bt_ratio = bt["peak"] / bt["low"] if bt["low"] else float("nan")
    L.append(
        f"Share `superactive` growing {sa['low']:.3f} (hour {sa['low_h']}) → "
        f"{sa['peak']:.3f} (hour {sa['peak_h']}), ×{sa_ratio:.1f}; "
        f"`bot` {bt['low']:.3f} → {bt['peak']:.3f}, ×{bt_ratio:.1f}.\n"
    )

    if has_corr:
        L.append("### 3.4 Correlation of `freq_h`/`diff` with segment shares\n")
        L.append(f"![correlation]({report_name}/img/04_correlation.png)\n")
        cf, cd = R["corr_freq"], R["corr_diff"]
        diff_key = "diff (w_h - reach_share_h)"
        L.append("Rising frequency explained **shifting**:\n")
        L.append("| | `freq_h` | `diff` |")
        L.append("|---|---|---|")
        L.append(f"| `share_superactive` | **{cf['share_superactive']:+.2f}** | {cd['share_superactive']:+.2f} |")
        L.append(f"| `share_bot` | {cf['share_bot']:+.2f} | {cd['share_bot']:+.2f} |")
        L.append(f"| `share_casual` | {cf['share_casual']:+.2f} | {cd['share_casual']:+.2f} |")
        L.append(f"| `freq_h ↔ diff` | {cf[diff_key]:+.2f} | — |\n")

    if has_dow:
        L.append("### 3.5 Weekdays vs weekends (day of week × hour)\n")
        L.append(f"![heatmap]({report_name}/img/05_dow_hour_heatmap.png)\n")
        L.append(
            f"Within a fixed day of the week, the frequency is more stable: "
            f"`CoV(freq_h)` = {f4(R['cov_freq_weekday'])} (weekday) / "
            f"{f4(R['cov_freq_weekend'])} (weekend) against {f4(R['cov_freq'])} "
            f"in `hour_of_day` — scatter `hour_of_day` mixing "
            "weekday and weekend profiles.\n"
        )
    L.append("---\n")

    # 4. Conclusions
    L.append("## 4. Conclusions\n")
    tv_range = (f"{pct(R['tv_daily'])}–{pct(R['tv_weekly'])}"
                if has_daily else pct(R["tv_weekly"]))
    if R["h1_primary"]:
        L.append(
            "1. **The primary rule gave H1** — at least one metric "
            f"(`CoV(freq)={f4(R['cov_freq'])}`, `max|diff|={f4(R['max_diff'])}`) is above "
            "its threshold. Check which metric triggered it and whether it holds in other weeks.\n"
        )
    else:
        L.append(
            f"1. **Formally H0.** `max|diff| = {f4(R['max_diff'])}` (threshold "
            f"{R['diff_threshold']}), `CoV(freq) = {f4(R['cov_freq'])}` (threshold "
            f"{R['cov_threshold']}), Pearson {R['pearson']:.2f}.\n"
        )
    L.append(
        f"2. **Cumulative bias {tv_range} — assess separately.** It accumulates "
        "systematically (morning −, evening +); the relevant scale is TV, not max.\n"
    )
    covs = R["segment_covs"]
    hot = [s for s in SEGMENTS if covs.get(s, 0) > R["cov_threshold"]]
    hot_txt = (", ".join(f"CoV({s})={f4(covs[s])}" for s in hot)
               if hot else "below-threshold")
    empty_txt = ("artifact (`EmptyUser` ≈ 0%)"
                 if R["empty_user_frac"] < 0.02
                 else f"cautiously: `EmptyUser` = {R['empty_user_frac']*100:.2f}%")
    L.append(
        f"3. **Audience composition by hour ({hot_txt}).** Exploration signal ({empty_txt}); "
        "was not part of the stated rule, threshold 0.15 not calibrated for small segments.\n"
    )
    if has_daily:
        L.append(
            "4. **For the daily limit — `reach_share_daily`, weekly reach** "
            "(weekly overstates evening skew).\n"
        )
    L.append(
        f"**Next steps:** check whether `TV ≈ {tv_range}` holds on 1–2 other "
        "weeks; compare the daily denominator and monitor `EmptyUser`; if stable, "
        "weigh the cost of `reach`/`freq` decomposition (by analogy with `HourShares` in "
        "[`../../../frequency_accounting_improvements.md`](../../../frequency_accounting_improvements.md), "
        "section 0) against the accuracy gain for user-capped campaigns.\n"
    )
    L.append("---\n")

    # 5. Reproduction
    L.append("## 5. How to update for another week\n")
    L.append(
        "1. In [`../check_reach_vs_volume.ipynb`](../check_reach_vs_volume.ipynb) "
        "change `PARQUET_FILE`, run **Run All** (including the metrics export cell), "
        "and save the notebook.\n"
        "2. `python make_report.py` — generate `reports/<week>.md` and "
        "`reports/<week>/img/` automatically.\n"
        "3. Compare it to this report: whether the sign and magnitude are stable `TV`, share "
        "`EmptyUser`, segmentation.\n"
    )
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--notebook", type=Path, default=here / "check_reach_vs_volume.ipynb")
    ap.add_argument("--reports-dir", type=Path, default=here / "reports")
    args = ap.parse_args()

    if not args.notebook.exists():
        raise SystemExit(f"Laptop not found: {args.notebook}")

    nb = load_notebook(args.notebook)
    R = extract_report_json(nb)
    week = R["week"].removeprefix("report-").removeprefix("janus-")
    report_name = f"report-{week}"

    img_dir = args.reports_dir / report_name / "img"
    missing = extract_figures(nb, img_dir)
    for sig, fname in missing:
        print(f"[WARNING] no picture for '{sig}' -> {fname} "
              "(cell not completed or without schedule)", file=sys.stderr)

    md_path = args.reports_dir / f"{report_name}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_md(R), encoding="utf-8")

    n_img = len(FIGURES) - len(missing)
    print(f"Report: {md_path}")
    print(f"Picture saved: {n_img}/{len(FIGURES)} in {img_dir}")
    print(f"Verdict: {'H1' if R['h1_primary'] else 'H0'}  "
          f"TV_nerd={R['tv_weekly']:.4f}"
          + (f"  TV_bottom={R['tv_daily']:.4f}" if 'tv_daily' in R else ""))


if __name__ == "__main__":
    main()
