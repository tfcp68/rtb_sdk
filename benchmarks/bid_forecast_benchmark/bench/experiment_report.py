"""Generate an offline editorial report from completed fixed-scenario JSON runs."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT.parents[1] / "docs" / "benchmark" / "bid_forecast" / "results"
OLD = RESULTS / "fixed_scenario_100" / "fixed_scenario_validation.json"
NEW = RESULTS / "fixed_scenario_probability_100" / "fixed_scenario_validation.json"
OUT = RESULTS / "experiment_report.html"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value: float, digits: int | str = 0) -> str:
    spec = digits if isinstance(digits, str) else f",.{digits}f"
    return format(value, spec).replace(",", "\u202f").replace(".", ",")


def chart_random(data: dict, old: dict, new: dict) -> str:
    randoms = [r["ours_total"] for r in data["raw_runs"] if r.get("replicate") is not None]
    stats = data["comparisons"][0]
    lo, hi = stats["random_min"], stats["random_max"]
    x = lambda v: 70 + (v - lo) / (hi - lo) * 700
    dots = "".join(f'<circle cx="{x(v):.1f}" cy="{44 + i % 7 * 5}" r="3" fill="#69d6c0" opacity=".62"/>' for i, v in enumerate(randoms))
    quantiles = "".join(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="30" y2="92" stroke="{color}" stroke-width="2"/>' for v, color in ((stats["random_p05"], "#f3a65b"), (stats["random_p50"], "#fffefa"), (stats["random_p95"], "#f3a65b")))
    return (f'<svg viewBox="0 0 840 130" role="img" aria-label="100 random runs on a min–max scale">{dots}{quantiles}'
            f'<line x1="70" x2="770" y1="100" y2="100" stroke="#527076"/>'
            f'<text x="70" y="122" fill="#c6d4d0" font-size="12">min {fmt(lo/1e6,3)} million</text>'
            f'<text x="420" y="122" text-anchor="middle" fill="#fffefa" font-size="12">median {fmt(stats["random_p50"]/1e6,3)} million</text>'
            f'<text x="770" y="122" text-anchor="end" fill="#c6d4d0" font-size="12">max {fmt(hi/1e6,3)} million</text></svg>')


def strategy_effect_chart(data: dict) -> str:
    comparisons = {r["strategy"]: r for r in data["comparisons"]}
    values = [(r["strategy"], r.get("regime", "baseline"),
               comparisons[f"{r.get('regime', 'baseline')}: {r['strategy']}"]["delta_mean"])
              for r in data["raw_runs"] if r.get("replicate") is None]
    bound = max(abs(v) for _, _, v in values)
    x = lambda v: 410 + v / bound * 330
    rows = []
    for i, (name, regime, value) in enumerate(values):
        y = 18 + i * 17
        color = "#69d6c0" if value >= 0 else "#f3a65b"
        rows.append(f'<text x="0" y="{y+4}" fill="#d2dfdc" font-size="10">{html.escape(regime)} · {html.escape(name)}</text><line x1="410" x2="{x(value):.1f}" y1="{y}" y2="{y}" stroke="{color}" stroke-width="5"/><circle cx="{x(value):.1f}" cy="{y}" r="3" fill="{color}"/>')
    return f'<svg viewBox="0 0 760 290" role="img" aria-label="Strategy differences from the random baseline mean">{"".join(rows)}<line x1="410" x2="410" y1="8" y2="285" stroke="#fffefa" stroke-dasharray="4 4"/><text x="410" y="288" text-anchor="middle" fill="#c6d4d0" font-size="10">random baseline mean</text></svg>'


def alpha_chart(data: dict) -> str:
    scores = data["validation_alpha"]["scores"]
    points = [(float(k), v) for k, v in scores.items()]
    lo, hi = min(v for _, v in points), max(v for _, v in points)
    x = lambda a: 48 + (a - .3) / .7 * 570
    y = lambda v: 24 + (hi - v) / (hi - lo) * 180
    path = " ".join(("M" if i == 0 else "L") + f"{x(a):.1f},{y(v):.1f}" for i, (a, v) in enumerate(points))
    dots = "".join(f'<circle cx="{x(a):.1f}" cy="{y(v):.1f}" r="4" fill="#69d6c0"/>' for a,v in points)
    chosen = data["validation_alpha"]["selected_alpha"]
    return (f'<svg viewBox="0 0 700 270" role="img" aria-label="Validation ours_total by alpha">'
            f'<path d="{path}" fill="none" stroke="#69d6c0" stroke-width="3"/>{dots}'
            f'<line x1="{x(chosen):.1f}" x2="{x(chosen):.1f}" y1="15" y2="215" stroke="#f3a65b" stroke-dasharray="5 5"/>'
            f'<text x="{x(chosen):.1f}" y="15" text-anchor="middle" fill="#f3a65b">selected α={chosen:g}</text>'
            f'<text x="48" y="238" fill="#a8baba">α = 0,30</text><text x="618" y="238" text-anchor="end" fill="#a8baba">α = 1,00</text>'
            f'<text x="8" y="24" fill="#a8baba" font-size="10">{fmt(hi/1e6,3)} million</text><text x="8" y="204" fill="#a8baba" font-size="10">{fmt(lo/1e6,3)} million</text><text x="8" y="115" fill="#a8baba" font-size="10" transform="rotate(-90 8 115)">ours_total</text></svg>')


def probability_sections(data: dict) -> str:
    diagnostics = data.get("provenance", {}).get("probability_diagnostics")
    if not diagnostics:
        return '<section><div class="eyebrow">Probability Metrics</div><h2>Diagnostics unavailable</h2><p>This JSON has no `provenance.probability_diagnostics` entry. These metrics were not computed.</p></section>'
    metrics = diagnostics["metrics"]
    names = ("SM (KM global)", "NM (wins-only global)", "NTM (tree, wins-only)", "STM (tree, KM)",
             "STM pruned (validation)", "Cui lognormal mixture", "Cui point-mean")
    models = [(regime, name, metrics[f"{regime}: {name}"])
              for regime in ("full", "censored") for name in names]
    rows, probe_rows, calibration, economy = [], [], [], []
    for regime, name, record in models:
        m = record.get("chosen_bid_probability", {})
        cells = (f'<td>{m["n"]:,} / {m["n_all"]:,}</td><td>{fmt(m["mean_predicted_win"]*100,1)}%</td>'
                 f'<td>{fmt(m["mean_observed_win"]*100,1)}%</td><td>{fmt(m["brier"],4)}</td>'
                 f'<td>{fmt(m["logloss"],4)}</td><td>{fmt(m["ece"],4)}</td><td>{m["confidently_wrong_count"]}</td>') if m.get("status") == "available" else '<td>—</td>' * 7
        rows.append(f'<tr><td>{regime.upper()}</td><th>{html.escape(name)}</th>{cells}</tr>')
        m = record.get("common_probe", {})
        cells = (f'<td>{fmt(m["mean_predicted_win"]*100,1)}%</td><td>{fmt(m["mean_observed_win"]*100,1)}%</td>'
                 f'<td>{fmt(m["brier"],4)}</td><td>{fmt(m["logloss"],4)}</td><td>{fmt(m["ece"],4)}</td>') if m.get("status") == "available" else '<td>—</td>' * 5
        probe_rows.append(f'<tr><td>{regime.upper()}</td><th>{html.escape(name)}</th>{cells}</tr>')
        bins = m.get("ece_bins", [])
        if bins:
            bin_rows = ''.join(f'<tr><td>{i/10:.1f}–{(i+1)/10:.1f}</td><td>{b["count"]:,}</td><td>{"—" if b["predicted_mean"] is None else fmt(b["predicted_mean"]*100,1)+"%"}</td><td>{"—" if b["observed_mean"] is None else fmt(b["observed_mean"]*100,1)+"%"}</td></tr>' for i,b in enumerate(bins))
            points = ''.join(f'<circle cx="{70+float(b["predicted_mean"])*660:.1f}" cy="{260-float(b["observed_mean"])*220:.1f}" r="4" fill="#69d6c0"><title>bin {i}: n={b["count"]}, predicted={b["predicted_mean"]:.4f}, observed={b["observed_mean"]:.4f}</title></circle>' for i,b in enumerate(bins) if b["count"])
            chart = f'<svg viewBox="0 0 780 310" role="img" aria-label="Calibration {html.escape(regime)} {html.escape(name)}"><line x1="70" y1="260" x2="730" y2="260" stroke="#527076"/><line x1="70" y1="40" x2="70" y2="260" stroke="#527076"/><line x1="70" y1="260" x2="730" y2="40" stroke="#f3a65b" stroke-dasharray="5 5"/><text x="70" y="285" fill="#c6d4d0">0%</text><text x="730" y="285" text-anchor="end" fill="#c6d4d0">100% predicted</text><text x="14" y="50" fill="#c6d4d0">100%</text><text x="14" y="260" fill="#c6d4d0">0%</text><text x="18" y="145" fill="#c6d4d0" transform="rotate(-90 18 145)">Observed win rate</text>{points}</svg>'
            calibration.append(f'<details><summary>{regime.upper()} · {html.escape(name)}</summary><div class="chart">{chart}</div><div class="table-wrap"><table><thead><tr><th>Bin P̂</th><th>n</th><th>Mean P̂</th><th>Win rate</th></tr></thead><tbody>{bin_rows}</tbody></table></div></details>')
        actual, oracle = record["actual_replay"], record["local_oracle"]
        economy.append(f'<tr><td>{regime.upper()}</td><th>{html.escape(name)}</th><td>{fmt(m["expected_market_profit"]) if m.get("status")=="available" else "—"}</td><td>{fmt(actual["market_profit"])}</td><td>{fmt(actual["eligible_win_rate"]*100,1)}%</td><td>{fmt(actual["eligible_mean_bid"],1)}</td><td>{fmt(oracle["regret_sum"])}</td></tr>')
    for name in ("shade alpha*v", "truthful b=v"):
        r = metrics[f"baseline: {name}"]
        actual, oracle = r["actual_replay"], r["local_oracle"]
        economy.append(f'<tr><td>BASELINE</td><th>{html.escape(name)}</th><td>—</td><td>{fmt(actual["market_profit"])}</td><td>{fmt(actual["eligible_win_rate"]*100,1)}%</td><td>{fmt(actual["eligible_mean_bid"],1)}</td><td>{fmt(oracle["regret_sum"])}</td></tr>')
    random_runs = [r.get("actual_decision_quality") for r in data.get("raw_runs", []) if r.get("replicate") is not None]
    random_runs = [r for r in random_runs if r and r.get("status") == "probability_not_available"]
    random_cells = (f'<td>—</td><td>{fmt(sum(r["market_profit"] if "market_profit" in r else r["eligible_actual_margin"] for r in random_runs)/len(random_runs))}</td>'
                    f'<td>{fmt(sum(r["eligible_win_rate"] for r in random_runs)/len(random_runs)*100,1)}%</td>'
                    f'<td>{fmt(sum(r["eligible_mean_bid"] for r in random_runs)/len(random_runs),1)}</td>'
                    f'<td>{fmt(sum(r["local_regret_sum"] for r in random_runs)/len(random_runs))}</td>') if random_runs else '<td>—</td>' * 5
    if random_runs:
        economy.append(f'<tr><td>RANDOM · mean of {len(random_runs)}</td><th>random bid U(R,v)</th>{random_cells}</tr>')
    probe = diagnostics["probe"]
    return f'''<section><div class="eyebrow">Probabilities and Market Economics</div><h2>Forecast and Decision Quality</h2>
<p>b* maximizes the model’s expected profit. A hindsight calculation assumes the price is known before bidding. The probabilities are forecasts for a binary outcome. The report flags wins with p=0 and losses with p=1. Log loss clips a copy of p using ε=1e-6. The tolerance at the boundaries of [0,1] is 1e-12. Scoring clips a separate copy of the probabilities and leaves the bid matrix intact.</p>
<p>Scores at the chosen bids are descriptive because models choose different bids and affect the subsequent auction state. The shared probe evaluates a static counterfactual on fixed inputs: seed {probe["seed"]}, {probe["rows"]:,} rows, SHA-256 <code>{html.escape(probe["input_sha256"])}</code>.</p>
<h3>Forecasts at Each Policy’s b* and Observed Win Rates</h3><div class="table-wrap"><table><thead><tr><th>Regime</th><th>Model</th><th>Coverage n / total</th><th>Mean P̂(win)</th><th>Observed win rate</th><th>Brier ↓</th><th>Log-loss ↓</th><th>ECE ↓</th><th>Errors at p=0/1</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h3>Shared fixed probe</h3><div class="table-wrap"><table><thead><tr><th>Regime</th><th>Model</th><th>P̂(win)</th><th>Observed win rate</th><th>Brier ↓</th><th>Log-loss ↓</th><th>ECE ↓</th></tr></thead><tbody>{''.join(probe_rows)}</tbody></table></div>
<h3>Calibration Bins (All 10 per Model)</h3><p>Expand a section to see all calibration bins, including empty bins.</p>{''.join(calibration)}
<h3>Expected and Actual Market Profit and the Local Oracle</h3><div class="table-wrap"><table><thead><tr><th>Regime</th><th>Policy</th><th>Expected market profit</th><th>Actual market profit</th><th>Win rate*</th><th>Mean bid*</th><th>Local GRID oracle regret</th></tr></thead><tbody>{''.join(economy)}</tbody></table></div>
<p>The table measures market profit only. The local oracle knows the current price and chooses the best bid on the grid for that auction. It does not optimize across budgets and cannot be deployed. Baseline policies produce no probability forecasts. The random row aggregates only the actual results for eligible requests saved in the source JSON.</p></section>'''


def render(old: dict, new: dict, paths: tuple[Path, Path]) -> str:
    old_rows = {(r.get("regime", "baseline"), r["strategy"]): r for r in old["raw_runs"] if r.get("replicate") is None}
    new_rows = {(r.get("regime", "baseline"), r["strategy"]): r for r in new["raw_runs"] if r.get("replicate") is None}
    old_cmp = {r["strategy"]: r for r in old["comparisons"]}
    new_cmp = {r["strategy"]: r for r in new["comparisons"]}
    random_old = [r["ours_total"] for r in old["raw_runs"] if r.get("replicate") is not None]
    random_new = [r["ours_total"] for r in new["raw_runs"] if r.get("replicate") is not None]
    random_old_stats = next(r for r in old["comparisons"])
    random_new_stats = next(r for r in new["comparisons"])
    pairs = [("full", name) for name in ("SM (KM global)", "NM (wins-only global)", "NTM (tree, wins-only)", "STM (tree, KM)", "STM pruned (validation)", "Cui lognormal mixture", "Cui point-mean")]
    pairs += [("censored", name) for _, name in pairs[:7]]
    strategy_rows = []
    for regime, name in pairs:
        key = regime + ": " + name
        a = old_rows[(regime, name)]
        b = new_rows[(regime, name)]
        ca, cb = old_cmp[key], new_cmp[key]
        strategy_rows.append(f'<tr><td>{html.escape(regime.upper())}</td><th>{html.escape(name)}</th><td>{fmt(a["ours_total"])}</td><td>{fmt(b["ours_total"])}</td><td>{fmt(b["ours_total"]-a["ours_total"], "+.0f")}</td><td>{fmt(ca["delta_vs_shading"], "+.0f")}</td><td>{fmt(cb["delta_vs_shading"], "+.0f")}</td><td>{fmt(ca["delta_mean"], "+.0f")}</td><td>{fmt(cb["delta_mean"], "+.0f")}</td><td>{int(cb["fraction_random_runs_beaten"]*len(random_new))}/100</td></tr>')
    baselines=[]
    for name in ("shade alpha*v", "truthful b=v"):
        a,b=old_rows[("baseline", name)],new_rows[("baseline", name)]
        baselines.append(f'<tr><td>BASELINE</td><th>{html.escape(name)}</th><td>{fmt(a["ours_total"])}</td><td>{fmt(b["ours_total"])}</td><td>{fmt(b["ours_total"]-a["ours_total"], "+.0f")}</td><td>{fmt(old_cmp["baseline: " + name]["delta_vs_shading"], "+.0f")}</td><td>{fmt(new_cmp["baseline: " + name]["delta_vs_shading"], "+.0f")}</td><td>{fmt(old_cmp["baseline: " + name]["delta_mean"], "+.0f")}</td><td>{fmt(new_cmp["baseline: " + name]["delta_mean"], "+.0f")}</td><td>{int(new_cmp["baseline: " + name]["fraction_random_runs_beaten"]*len(random_new))}/100</td></tr>')
    random_delta = sum(random_new)/len(random_new)-sum(random_old)/len(random_old)
    lo, hi = random_new_stats["random_min"], random_new_stats["random_max"]
    val = new["provenance"]["request_counts"]
    old_counts=old["provenance"]["request_counts"]
    cp=new["provenance"]["campaign_planning"]
    source_rows=[]
    for p in paths:
        payload=old if p==paths[0] else new
        source_rows.append(f'<tr><td><a href="{html.escape(p.parent.name)}/{html.escape(p.name)}">{html.escape(p.parent.name)}/{html.escape(p.name)}</a></td><td><code>{sha256(p)}</code></td></tr>')
    source_hash_rows=''.join(f'<tr><td>{html.escape(k)}</td><td><code>{html.escape(v)}</code></td></tr>' for k,v in new["provenance"]["source_hashes"].items())
    code_hash_rows=''.join(f'<tr><td>{html.escape(k)}</td><td><code>{html.escape(v)}</code></td></tr>' for k,v in new["provenance"]["code_sha256"].items())
    phase_table=''.join(f'<tr><th>{name}</th><td>{fmt(sum(plans["ours"]))}</td><td>{fmt(sum(map(sum,plans["competitors"])))}</td></tr>' for name,plans in cp["plans"].items())
    old_mean=sum(random_old)/len(random_old); new_mean=sum(random_new)/len(random_new)
    leaders = {regime: max((r for r in new["raw_runs"] if r.get("regime") == regime and r.get("replicate") is None), key=lambda r: r["ours_total"])
               for regime in ("full", "censored")}
    data=new
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Bidding and Information: Experiment Report</title>
<style>
:root{{--ink:var(--foreground,#122b35);--navy:var(--primary,#102a35);--navy2:#173d47;--paper:var(--background,#f4f2eb);--white:var(--card,#fffefa);--teal:var(--accent,#087d78);--mint:#69d6c0;--amber:#f3a65b;--line:var(--border,#d9ded8);--muted:var(--muted-foreground,#587078);--serif:Georgia,'Times New Roman',serif;--sans:'Segoe UI',Tahoma,Arial,sans-serif;}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:transparent;color:var(--ink);font:16px/1.65 var(--sans)}}.report{{background:var(--paper)}}a{{color:var(--teal)}}.wrap{{max-width:1160px;margin:auto;padding:0 28px}}.hero{{background:radial-gradient(ellipse at 83% 9%,#28606a 0,transparent 36%),linear-gradient(132deg,var(--navy),#142f3a 68%,#0d4b50);color:#f4f2eb;padding:68px 0 56px;border-bottom:5px solid var(--mint)}}.kicker,.eyebrow{{font-size:.76rem;letter-spacing:.16em;text-transform:uppercase;font-weight:700;color:var(--mint)}}h1,h2,h3{{font-family:var(--serif);line-height:1.12;font-weight:500}}h1{{font-size:clamp(2.6rem,6vw,5.4rem);max-width:880px;margin:20px 0}}.hero p{{max-width:760px;color:#d2dfdc;font-size:1.12rem}}.flag{{display:inline-block;border:1px solid #6aa8a1;border-radius:99px;padding:5px 12px;font-size:.78rem;letter-spacing:.07em}}main{{padding:36px 0 80px}}section{{margin:58px 0}}h2{{font-size:clamp(2rem,4vw,3rem);margin:0 0 18px;color:var(--navy)}}h3{{font-size:1.45rem;margin:0 0 12px}}.lead{{font:1.2rem/1.7 var(--serif);max-width:850px;color:#29434a}}.intro-grid{{display:grid;grid-template-columns:1.5fr 1fr;gap:20px;margin-top:28px}}.note,.card{{background:var(--white);border:1px solid var(--line);padding:22px 24px;box-shadow:0 8px 22px #18333b0b}}.note{{border-left:4px solid var(--amber)}}.note strong{{color:var(--navy)}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0}}.metric{{background:var(--navy);color:white;padding:18px 20px;min-height:120px}}.metric b{{font:1.8rem var(--serif);display:block;color:var(--mint)}}.metric span{{font-size:.8rem;color:#c6d4d0}}.chart{{padding:18px 20px;background:var(--navy);color:white;overflow:hidden}}svg{{display:block;width:100%;height:auto}}.chart p,.caption{{color:var(--muted);font-size:.9rem}}.chart p{{color:#c6d4d0}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);background:var(--white)}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;min-width:780px}}td,th{{padding:11px 13px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}}thead th{{background:var(--navy);color:white;font-size:.78rem;letter-spacing:.04em}}td:first-child,th:first-child,tbody th{{text-align:left}}tbody tr:nth-child(even){{background:#f5f7f2}}tbody tr:hover{{background:#e9f3ef}}.delta-pos{{color:#087d78}}.split{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.phases{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}}.phase{{padding:18px;background:#e7eeea;border-top:3px solid var(--teal)}}.phase b{{font:1.4rem var(--serif);display:block}}.method-list{{counter-reset:m}}.method-list li{{margin:10px 0;padding-left:6px}}code{{font: .82rem/1.5 Consolas,monospace;overflow-wrap:anywhere}}.small{{font-size:.88rem;color:var(--muted)}}details{{background:var(--white);border:1px solid var(--line);margin:12px 0;padding:14px 18px}}summary{{font-weight:700;color:var(--navy);cursor:pointer}}.hash-table td:first-child{{text-align:left}}.warning{{background:#fff4e6;border:1px solid #e5c49d;padding:18px 22px}}footer{{background:var(--navy);color:#c6d4d0;padding:28px 0}}.rule{{height:1px;background:var(--line);margin:28px 0}}.pill{{display:inline-block;padding:2px 8px;background:#dcebe6;color:#155d58;border-radius:3px;font-size:.75rem}}@media(max-width:760px){{.wrap{{padding:0 17px}}.hero{{padding:45px 0 40px}}.intro-grid,.split{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(2,1fr)}}.phases{{grid-template-columns:1fr}}section{{margin:42px 0}}}}@media print{{body{{background:#fff;font-size:11pt}}.hero{{background:#fff;color:var(--ink);padding:20px 0;border-bottom:2px solid var(--teal)}}.hero p{{color:var(--ink)}}.kicker{{color:var(--teal)}}.flag{{border-color:#777}}.wrap{{max-width:none;padding:0}}section{{margin:28px 0;break-inside:avoid}}.chart,.metric{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}details{{break-inside:avoid}}details:not([open])>*:not(summary){{display:block}}a{{color:inherit;text-decoration:none}}}}
</style></head><body>
<!-- Values, labels, and charts below are rendered from the completed source JSON files. -->
<div class="report"><header class="hero"><div class="wrap"><span class="kicker">Research Note · Auction Pricing</span><h1>When Simpler Models Win</h1><p>A review of a fixed seven-day scenario with 16 policies, two observation regimes, and 100 random-bid runs on the same test stream.</p><span class="flag">Results from completed runs · Reproducible comparisons</span></div></header>
<main class="wrap">
<section><div class="eyebrow">Summary</div><h2>Campaign Planning Changes the Market</h2><p class="lead">Estimating campaign volumes from training data alone prevents validation and test data from informing future campaign plans. The change also alters the market faced by the policies, so the revenue difference between runs cannot isolate the effect of the algorithm.</p>
<div class="intro-grid"><div class="note"><strong>Methodological limitation.</strong> Both runs share the same SHA-256 hashes for the prepared data and ad files, the same split, and the same environment seed. The old campaign plan used the full week. The new plan uses only sampled requests from training days 0–2. Campaign budgets and volumes affect auction outcomes, so the difference in total revenue includes the effect of the change in the environment.</div><div class="card"><h3>Train-Only Test Leaders by Regime</h3><p>FULL leader: {html.escape(leaders['full']['strategy'])} — <b>{fmt(leaders['full']['ours_total'])}</b>. CENSORED leader: {html.escape(leaders['censored']['strategy'])} — <b>{fmt(leaders['censored']['ours_total'])}</b>. These results describe the two observation regimes in this scenario.</p></div></div>
<div class="metrics"><div class="metric"><b>{len(new["comparisons"])}</b><span>policies in each comparison table</span></div><div class="metric"><b>{len(random_new)}</b><span>random bid seeds per test setup</span></div><div class="metric"><b>{fmt(random_delta, "+.0f")}</b><span>change in mean random total from the old plan to the new plan</span></div><div class="metric"><b>1900</b><span>shared environment seed</span></div></div>
</section>
<section><div class="eyebrow">01 / Protocol</div><h2>Time Split and Environment State</h2><p>The seven source days are split chronologically. Each phase starts the simulator from a fresh campaign state with a fixed environment, making the request stream and competitors reproducible.</p><div class="phases"><div class="phase"><span class="pill">Training</span><b>Days 0–2</b><span>indices [0, 3), sampled market requests: {fmt(val['train'])}</span></div><div class="phase"><span class="pill">Validation</span><b>Days 3–4</b><span>indices [3, 5), sampled market requests: {fmt(val['validation'])}</span></div><div class="phase"><span class="pill">Test</span><b>Days 5–6</b><span>indices [5, 7), sampled market requests: {fmt(val['test'])}</span></div></div><div class="warning"><b>Two uses of validation.</b> Validation ours_total selects the shading alpha while the campaign plan and parameters stay fixed. The selected policy is then evaluated on the test set. Models fit on the training set, and pruned STM uses validation to prune the tree. Random bid seeds vary while the environment seed stays at 1900.</div>
<h3 style="margin-top:28px">Campaign Planning Change</h3><p>The old JSON has no campaign_planning entry. That plan used the full week’s traffic mix and the observed phase volumes. The new plan uses request combinations from training days 0–2 and applies the daily forecast derived from training to every phase. Validation and test traffic are used only for replay and reporting.</p><p><code>{html.escape(cp['formula'])}</code></p><div class="table-wrap"><table><thead><tr><th>Phase</th><th>Own campaigns: total planned volume</th><th>Three competitors: total planned volume</th></tr></thead><tbody>{phase_table}</tbody></table></div><p class="small">The totals sum planned volumes from campaign_planning.plans in the new JSON.</p>
</section>
<section><div class="eyebrow">02 / Random Baseline</div><h2>Random Outcomes and Strategy Differences</h2><p>The random policy draws a uniform bid between the reserve and the request value. All 100 runs share the test stream and use separate bid seeds (1000–1099). The upper chart spans the random minimum to maximum. The lower chart uses a separate scale for differences from the random mean so the full range of baseline results remains visible.</p><div class="chart">{chart_random(data, old, new)}<p>Each dot is one random run. The colored lines mark p05, the median, and p95. The endpoints show the minimum and maximum.</p></div><div class="chart">{strategy_effect_chart(data)}<p>Each bar shows the strategy and regime from the test JSON and its difference from the random mean. Zero is centered. Green indicates a higher result and amber a lower result. The table contains the original totals and paired differences.</p></div><div class="metrics"><div class="metric"><b>{fmt(random_new_stats['random_p05']/1e6,3)} million</b><span>random p05</span></div><div class="metric"><b>{fmt(random_new_stats['random_p50']/1e6,3)} million</b><span>random median</span></div><div class="metric"><b>{fmt(random_new_stats['random_p95']/1e6,3)} million</b><span>random p95</span></div><div class="metric"><b>{fmt(lo/1e6,3)}–{fmt(hi/1e6,3)} million</b><span>random min–max</span></div></div><p class="small">The percentiles and differences describe variation within one fixed environment. All bid seeds reuse the same traffic period.</p></section>
<section><div class="eyebrow">03 / Results</div><h2>All 16 Policies Under Both Plans</h2><p>ours_total combines market profit and external revenue from our campaigns. The change between plans is the arithmetic difference in totals and includes the effect of the planning change. The delta versus random is the paired mean difference against the 100 random runs in the same JSON. The delta versus shading also uses results from the same JSON.</p><div class="table-wrap"><table><thead><tr><th>Regime</th><th>Policy</th><th>Old total</th><th>Train-only total</th><th>Δ plan</th><th>Δ shade old</th><th>Δ shade new</th><th>Δ random old</th><th>Δ random new</th><th>Random runs beaten (new)</th></tr></thead><tbody>{''.join(strategy_rows)}{''.join(baselines)}</tbody></table></div><p class="caption">The count compares each strategy against the ours_total from all 100 random runs in the new JSON. It counts only strictly higher results.</p><div class="split"><div class="card"><h3>Full Observation</h3><p>SM and NM use global price distributions. NTM and STM add trees, and pruned STM prunes on validation. Cui mixture estimates a campaign’s lognormal mixture, and point-mean reduces it to its mean. SM and NM beat the more complex trees in this scenario. Cui mixture and especially point-mean score lower on total revenue.</p></div><div class="card"><h3>Censored Observation</h3><p>A loss reveals only a lower bound on the price. NM fits on wins, SM uses Kaplan–Meier for censored observations, and NTM and STM add features and a tree. The lead of SM and NM over nearby alternatives depends on this fixed market.</p></div></div></section>
<section><div class="eyebrow">04 / Baseline Selection</div><h2>Validation Selects the Shading Coefficient</h2><p>Validation scores the bid α·v over a grid of α values. The selected value stays fixed for the test. The chart plots the recorded validation_alpha.scores directly.</p><div class="chart">{alpha_chart(new)}<p>The vertical axis shows validation ours_total. Dots mark the α values, and the orange line identifies the selected maximum.</p></div><p class="lead">Grid optimum α = {new['validation_alpha']['selected_alpha']:g}. Validation score: {fmt(new['validation_alpha']['scores'][str(new['validation_alpha']['selected_alpha'])])}.</p></section>
<section><div class="eyebrow">05 / Model Families</div><h2>How the Models Estimate Prices</h2><div class="table-wrap"><table><thead><tr><th>Family</th><th>Observation regime and structure</th><th>Key idea</th></tr></thead><tbody><tr><th>SM</th><td>Full or censored, global</td><td>Global price estimate using Kaplan–Meier under censoring.</td></tr><tr><th>NM</th><td>Wins only, global</td><td>Baseline fitted to observed wins.</td></tr><tr><th>NTM</th><td>Tree, wins only</td><td>Normal price model fitted in each feature-based tree leaf.</td></tr><tr><th>STM</th><td>Tree with Kaplan–Meier</td><td>Leaf-level survival estimate that accounts for censoring.</td></tr><tr><th>STM pruned</th><td>STM pruned on validation</td><td>Validation negative log likelihood guides pruning before the test.</td></tr><tr><th>Cui mixture</th><td>Full or censored, lognormal mixture</td><td>Estimates the campaign distribution as a mixture of lognormal components.</td></tr><tr><th>Cui point-mean</th><td>Mean of the mixture</td><td>Control that discards variation in the distribution.</td></tr></tbody></table></div><p class="lead">A more complex model may add little signal at this sample size or in this scenario. The comparison measures the profit of the policy, which is distinct from how well the model estimates the distribution.</p></section>
 {probability_sections(new)}
 <section><div class="eyebrow">06 / Interpretation and Limitations</div><h2>Limits of the Evidence</h2><div class="warning"><ol class="method-list"><li><b>Campaign plan changed.</b> Differences in raw totals combine changes to the plan and market with changes to the model.</li><li><b>One synthetic campaign setup and one seven-day source.</b> The simulation uses prepared data with a sampling fraction of 0.002 and environment seed 1900. It covers one setup.</li><li><b>Campaign state resets between phases.</b> Every phase starts with a clean slate, which limits how directly the planning results transfer to campaigns that run continuously.</li><li><b>Training forecast error.</b> The new plan extrapolates daily traffic and the target match mix from three training days. The report makes the plan’s source explicit.</li><li><b>Variation across traffic seeds remains unmeasured.</b> The 100 bid seeds vary the bid under a fixed environment. They cannot provide independent seven-day samples, standard errors, or population estimates.</li><li><b>Choose strategies before testing.</b> The table is descriptive. Shading alpha and tree pruning use validation as described above.</li></ol></div><p class="lead">To estimate an algorithm’s effect, compare models on identical streams with identical campaign budgets. To generalize, repeat the experiment across independent environment seeds or scenarios with a metric chosen in advance.</p></section>
<section><div class="eyebrow">07 / Reproducibility</div><h2>Sources, Hashes, and Commands</h2><p>The HTML is self-contained for viewing and printing. The links open the source JSON files stored alongside it. To reproduce the train-only experiment from the repository root, use a fresh output directory because the runner preserves existing results.</p><pre class="card"><code>python -m articles_prorotypes.bench.fixed_scenario_validation --prepared benchmarks/logs/prepared_20261012_retry --manager-ads benchmarks/closed_stand/manager_target50_20261012.json --our-ads benchmarks/log_benchmark/ads_manual.json --output-dir docs/benchmark/bid_forecast/results/fixed_scenario_probability_reproduced</code></pre><p>To regenerate only the HTML, run the report generator.</p><pre class="card"><code>python -m articles_prorotypes.bench.experiment_report</code></pre><p class="small">The report generator uses only the standard library and runs offline.</p><div class="table-wrap"><table class="hash-table"><thead><tr><th>JSON</th><th>File SHA-256 (computed at render time)</th></tr></thead><tbody>{''.join(source_rows)}</tbody></table></div>
<details><summary>Input Array Hashes from the New JSON</summary><div class="table-wrap"><table class="hash-table"><tbody>{source_hash_rows}</tbody></table></div></details><details><summary>Experiment Code Hashes from the New JSON</summary><div class="table-wrap"><table class="hash-table"><tbody>{code_hash_rows}</tbody></table></div></details><details><summary>Runtime and Settings</summary><p>Python {html.escape(new['provenance']['python'])}, NumPy {html.escape(new['provenance']['numpy'])}, sampling fraction {fmt(new['configuration']['sample'],3)}, q={fmt(new['configuration']['q'],1)}, reserve={fmt(new['configuration']['reserve'])}, competitors={new['configuration']['competitors']}, random bid seeds {new['configuration']['bid_seed']}–{new['configuration']['bid_seed']+new['configuration']['random_replicates']-1}, environment seed {new['provenance']['environment_seed']}. Sampled market requests: training {fmt(val['train'])}, validation {fmt(val['validation'])}, test {fmt(val['test'])}.</p><p>The source JSON contains all validation alpha scores, all 100 random records, the 16 original strategy results, and all comparisons.</p></details></section>
</main><footer><div class="wrap">Offline report · The tables and charts use numerical results from the listed source JSON files.</div></footer></div></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, default=OLD)
    parser.add_argument("--new", type=Path, default=NEW)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    old_path, new_path = args.old.resolve(), args.new.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(load(old_path), load(new_path), (old_path, new_path)), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
