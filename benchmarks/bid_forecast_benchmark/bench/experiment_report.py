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
    return (f'<svg viewBox="0 0 840 130" role="img" aria-label="100 значений random по min–max">{dots}{quantiles}'
            f'<line x1="70" x2="770" y1="100" y2="100" stroke="#527076"/>'
            f'<text x="70" y="122" fill="#c6d4d0" font-size="12">min {fmt(lo/1e6,3)} млн</text>'
            f'<text x="420" y="122" text-anchor="middle" fill="#fffefa" font-size="12">медиана {fmt(stats["random_p50"]/1e6,3)} млн</text>'
            f'<text x="770" y="122" text-anchor="end" fill="#c6d4d0" font-size="12">max {fmt(hi/1e6,3)} млн</text></svg>')


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
    return f'<svg viewBox="0 0 760 290" role="img" aria-label="Стратегии против среднего random в отклонении">{"".join(rows)}<line x1="410" x2="410" y1="8" y2="285" stroke="#fffefa" stroke-dasharray="4 4"/><text x="410" y="288" text-anchor="middle" fill="#c6d4d0" font-size="10">среднее random</text></svg>'


def alpha_chart(data: dict) -> str:
    scores = data["validation_alpha"]["scores"]
    points = [(float(k), v) for k, v in scores.items()]
    lo, hi = min(v for _, v in points), max(v for _, v in points)
    x = lambda a: 48 + (a - .3) / .7 * 570
    y = lambda v: 24 + (hi - v) / (hi - lo) * 180
    path = " ".join(("M" if i == 0 else "L") + f"{x(a):.1f},{y(v):.1f}" for i, (a, v) in enumerate(points))
    dots = "".join(f'<circle cx="{x(a):.1f}" cy="{y(v):.1f}" r="4" fill="#69d6c0"/>' for a,v in points)
    chosen = data["validation_alpha"]["selected_alpha"]
    return (f'<svg viewBox="0 0 700 270" role="img" aria-label="Validation ours_total по alpha">'
            f'<path d="{path}" fill="none" stroke="#69d6c0" stroke-width="3"/>{dots}'
            f'<line x1="{x(chosen):.1f}" x2="{x(chosen):.1f}" y1="15" y2="215" stroke="#f3a65b" stroke-dasharray="5 5"/>'
            f'<text x="{x(chosen):.1f}" y="15" text-anchor="middle" fill="#f3a65b">выбрано α={chosen:g}</text>'
            f'<text x="48" y="238" fill="#a8baba">α = 0,30</text><text x="618" y="238" text-anchor="end" fill="#a8baba">α = 1,00</text>'
            f'<text x="8" y="24" fill="#a8baba" font-size="10">{fmt(hi/1e6,3)} млн</text><text x="8" y="204" fill="#a8baba" font-size="10">{fmt(lo/1e6,3)} млн</text><text x="8" y="115" fill="#a8baba" font-size="10" transform="rotate(-90 8 115)">ours_total</text></svg>')


def probability_sections(data: dict) -> str:
    diagnostics = data.get("provenance", {}).get("probability_diagnostics")
    if not diagnostics:
        return '<section><div class="eyebrow">Вероятностные метрики</div><h2>Диагностика отсутствует</h2><p>В этом JSON нет `provenance.probability_diagnostics`; эти метрики не вычислялись.</p></section>'
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
            points = ''.join(f'<circle cx="{70+float(b["predicted_mean"])*660:.1f}" cy="{260-float(b["observed_mean"])*220:.1f}" r="4" fill="#69d6c0"><title>bin {i}: n={b["count"]}, прогноз={b["predicted_mean"]:.4f}, наблюдение={b["observed_mean"]:.4f}</title></circle>' for i,b in enumerate(bins) if b["count"])
            chart = f'<svg viewBox="0 0 780 310" role="img" aria-label="Calibration {html.escape(regime)} {html.escape(name)}"><line x1="70" y1="260" x2="730" y2="260" stroke="#527076"/><line x1="70" y1="40" x2="70" y2="260" stroke="#527076"/><line x1="70" y1="260" x2="730" y2="40" stroke="#f3a65b" stroke-dasharray="5 5"/><text x="70" y="285" fill="#c6d4d0">0%</text><text x="730" y="285" text-anchor="end" fill="#c6d4d0">100% прогноз</text><text x="14" y="50" fill="#c6d4d0">100%</text><text x="14" y="260" fill="#c6d4d0">0%</text><text x="18" y="145" fill="#c6d4d0" transform="rotate(-90 18 145)">факт. доля побед</text>{points}</svg>'
            calibration.append(f'<details><summary>{regime.upper()} · {html.escape(name)}</summary><div class="chart">{chart}</div><div class="table-wrap"><table><thead><tr><th>Bin P̂</th><th>n</th><th>Средняя P̂</th><th>Доля побед</th></tr></thead><tbody>{bin_rows}</tbody></table></div></details>')
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
        economy.append(f'<tr><td>RANDOM · среднее {len(random_runs)}</td><th>random bid U(R,v)</th>{random_cells}</tr>')
    probe = diagnostics["probe"]
    return f'''<section><div class="eyebrow">Вероятности и market-only экономика</div><h2>Качество прогноза и решений</h2>
<p>b* максимизирует ожидаемую прибыль по модели, а не hindsight-прибыль при заранее известной цене. Вероятности — прогнозы, не классификационные метки 0/1. Отмечены уверенно ошибочные p=0 при победе и p=1 при проигрыше; log-loss клиппирует копию p к ε=1e-6. Допуск у границ вероятности [0,1] — 1e-12; для scoring ограничивается отдельная копия, матрица ставки не меняется.</p>
<p>Across-model chosen-bid scores не являются честным leaderboard: ставки/траектории эндогенны и различаются. Общий probe — фиксированный статический контрфактический тест, а не своя траектория: seed {probe["seed"]}, {probe["rows"]:,} строк, SHA-256 <code>{html.escape(probe["input_sha256"])}</code>.</p>
<h3>Прогноз на собственных b* и фактическая доля побед</h3><div class="table-wrap"><table><thead><tr><th>Режим</th><th>Модель</th><th>Покрытие n / все</th><th>Средняя P̂(win)</th><th>Факт. win rate</th><th>Brier ↓</th><th>Log-loss ↓</th><th>ECE ↓</th><th>Ошибки p=0/1</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h3>Одинаковый фиксированный probe</h3><div class="table-wrap"><table><thead><tr><th>Режим</th><th>Модель</th><th>P̂(win)</th><th>Факт. win rate</th><th>Brier ↓</th><th>Log-loss ↓</th><th>ECE ↓</th></tr></thead><tbody>{''.join(probe_rows)}</tbody></table></div>
<h3>Calibration bins (все 10 на модель)</h3><p>Детали свернуты для читаемости; каждая таблица показывает полную шкалу bins, включая пустые.</p>{''.join(calibration)}
<h3>Expected vs actual MARKET profit и local oracle</h3><div class="table-wrap"><table><thead><tr><th>Режим</th><th>Политика</th><th>Ожидаемая market profit</th><th>Фактическая market profit</th><th>Win rate*</th><th>Средняя ставка*</th><th>Local GRID oracle regret</th></tr></thead><tbody>{''.join(economy)}</tbody></table></div>
<p>Используется только market profit, не `ours_total`. Local oracle — мгновенный GRID oracle по текущей цене, не оптимум с глобальными бюджетами и не deployable. Baseline-политики не имеют прогнозных вероятностей. Random-строка агрегирует только сохранённые actual-only eligible summaries; метрик вероятности/знаменателей сверх JSON не выводим.</p></section>'''


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
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Ставка и информация — отчёт эксперимента</title>
<style>
:root{{--ink:var(--foreground,#122b35);--navy:var(--primary,#102a35);--navy2:#173d47;--paper:var(--background,#f4f2eb);--white:var(--card,#fffefa);--teal:var(--accent,#087d78);--mint:#69d6c0;--amber:#f3a65b;--line:var(--border,#d9ded8);--muted:var(--muted-foreground,#587078);--serif:Georgia,'Times New Roman',serif;--sans:'Segoe UI',Tahoma,Arial,sans-serif;}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:transparent;color:var(--ink);font:16px/1.65 var(--sans)}}.report{{background:var(--paper)}}a{{color:var(--teal)}}.wrap{{max-width:1160px;margin:auto;padding:0 28px}}.hero{{background:radial-gradient(ellipse at 83% 9%,#28606a 0,transparent 36%),linear-gradient(132deg,var(--navy),#142f3a 68%,#0d4b50);color:#f4f2eb;padding:68px 0 56px;border-bottom:5px solid var(--mint)}}.kicker,.eyebrow{{font-size:.76rem;letter-spacing:.16em;text-transform:uppercase;font-weight:700;color:var(--mint)}}h1,h2,h3{{font-family:var(--serif);line-height:1.12;font-weight:500}}h1{{font-size:clamp(2.6rem,6vw,5.4rem);max-width:880px;margin:20px 0}}.hero p{{max-width:760px;color:#d2dfdc;font-size:1.12rem}}.flag{{display:inline-block;border:1px solid #6aa8a1;border-radius:99px;padding:5px 12px;font-size:.78rem;letter-spacing:.07em}}main{{padding:36px 0 80px}}section{{margin:58px 0}}h2{{font-size:clamp(2rem,4vw,3rem);margin:0 0 18px;color:var(--navy)}}h3{{font-size:1.45rem;margin:0 0 12px}}.lead{{font:1.2rem/1.7 var(--serif);max-width:850px;color:#29434a}}.intro-grid{{display:grid;grid-template-columns:1.5fr 1fr;gap:20px;margin-top:28px}}.note,.card{{background:var(--white);border:1px solid var(--line);padding:22px 24px;box-shadow:0 8px 22px #18333b0b}}.note{{border-left:4px solid var(--amber)}}.note strong{{color:var(--navy)}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0}}.metric{{background:var(--navy);color:white;padding:18px 20px;min-height:120px}}.metric b{{font:1.8rem var(--serif);display:block;color:var(--mint)}}.metric span{{font-size:.8rem;color:#c6d4d0}}.chart{{padding:18px 20px;background:var(--navy);color:white;overflow:hidden}}svg{{display:block;width:100%;height:auto}}.chart p,.caption{{color:var(--muted);font-size:.9rem}}.chart p{{color:#c6d4d0}}.table-wrap{{overflow-x:auto;border:1px solid var(--line);background:var(--white)}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;min-width:780px}}td,th{{padding:11px 13px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}}thead th{{background:var(--navy);color:white;font-size:.78rem;letter-spacing:.04em}}td:first-child,th:first-child,tbody th{{text-align:left}}tbody tr:nth-child(even){{background:#f5f7f2}}tbody tr:hover{{background:#e9f3ef}}.delta-pos{{color:#087d78}}.split{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.phases{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}}.phase{{padding:18px;background:#e7eeea;border-top:3px solid var(--teal)}}.phase b{{font:1.4rem var(--serif);display:block}}.method-list{{counter-reset:m}}.method-list li{{margin:10px 0;padding-left:6px}}code{{font: .82rem/1.5 Consolas,monospace;overflow-wrap:anywhere}}.small{{font-size:.88rem;color:var(--muted)}}details{{background:var(--white);border:1px solid var(--line);margin:12px 0;padding:14px 18px}}summary{{font-weight:700;color:var(--navy);cursor:pointer}}.hash-table td:first-child{{text-align:left}}.warning{{background:#fff4e6;border:1px solid #e5c49d;padding:18px 22px}}footer{{background:var(--navy);color:#c6d4d0;padding:28px 0}}.rule{{height:1px;background:var(--line);margin:28px 0}}.pill{{display:inline-block;padding:2px 8px;background:#dcebe6;color:#155d58;border-radius:3px;font-size:.75rem}}@media(max-width:760px){{.wrap{{padding:0 17px}}.hero{{padding:45px 0 40px}}.intro-grid,.split{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(2,1fr)}}.phases{{grid-template-columns:1fr}}section{{margin:42px 0}}}}@media print{{body{{background:#fff;font-size:11pt}}.hero{{background:#fff;color:var(--ink);padding:20px 0;border-bottom:2px solid var(--teal)}}.hero p{{color:var(--ink)}}.kicker{{color:var(--teal)}}.flag{{border-color:#777}}.wrap{{max-width:none;padding:0}}section{{margin:28px 0;break-inside:avoid}}.chart,.metric{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}details{{break-inside:avoid}}details:not([open])>*:not(summary){{display:block}}a{{color:inherit;text-decoration:none}}}}
</style></head><body>
<!-- Values, labels, and charts below are rendered from the completed source JSON files. -->
<div class="report"><header class="hero"><div class="wrap"><span class="kicker">Исследовательская записка · аукционное ценообразование</span><h1>Когда простая модель выигрывает у сложности</h1><p>Повторный разбор фиксированного семидневного сценария: 16 политик, два режима наблюдаемости, по 100 случайных ставок на одной и той же тестовой ленте.</p><span class="flag">Результаты из завершённых JSON · воспроизводимая сверка</span></div></header>
<main class="wrap">
<section><div class="eyebrow">Короткий вывод</div><h2>Смена плана меняет уровень; сравнение моделей — отдельный вопрос</h2><p class="lead">Train-only планирование делает разделение честнее: сведения validation/test больше не подсказывают объём будущих кампаний. Но результаты до и после этого изменения нельзя трактовать как чистый прирост алгоритма — изменился сам рынок, против которого политики разыгрывались.</p>
<div class="intro-grid"><div class="note"><strong>Главное методическое ограничение.</strong> В обоих прогонах совпадают SHA-256 подготовленного источника и файлов объявлений, split и environment seed. Однако старый план кампаний рассчитывался по полной композиции недели; новый — только по sampled train дням 0:3. Кампанийные бюджеты/объёмы влияют на исходы, поэтому разность суммарных доходов включает изменение среды. Это не доказательство улучшения алгоритма.</div><div class="card"><h3>Лидеры по режимам, train-only test</h3><p>FULL лидирует: {html.escape(leaders['full']['strategy'])} — <b>{fmt(leaders['full']['ours_total'])}</b>. CENSORED лидирует: {html.escape(leaders['censored']['strategy'])} — <b>{fmt(leaders['censored']['ours_total'])}</b>. Это описательное сравнение лишь в данном сценарии; в частности, полные/цензурированные результаты не взаимозаменяемы.</p></div></div>
<div class="metrics"><div class="metric"><b>{len(new["comparisons"])}</b><span>политик в каждой таблице сравнения</span></div><div class="metric"><b>{len(random_new)}</b><span>bid-seed повторов random на режим теста</span></div><div class="metric"><b>{fmt(random_delta, "+.0f")}</b><span>изменение среднего random total, старый → новый план</span></div><div class="metric"><b>1900</b><span>одна environment seed в обоих прогонах</span></div></div>
</section>
<section><div class="eyebrow">01 / Протокол</div><h2>Временной split и состояние среды</h2><p>Семь исходных дней разделены хронологически. Для каждой фазы стенд заново запускается с фиксированной средой — поток и конкуренты воспроизводимы; состояния кампаний между фазами не переносятся.</p><div class="phases"><div class="phase"><span class="pill">обучение</span><b>Дни 0–2</b><span>индексы [0, 3), sampled market requests: {fmt(val['train'])}</span></div><div class="phase"><span class="pill">валидация</span><b>Дни 3–4</b><span>индексы [3, 5), sampled market requests: {fmt(val['validation'])}</span></div><div class="phase"><span class="pill">тест</span><b>Дни 5–6</b><span>индексы [5, 7), sampled market requests: {fmt(val['test'])}</span></div></div><div class="warning"><b>Два применения validation.</b> Alpha для shading выбирается по validation `ours_total`, а параметры/план кампаний остаются заморожены; затем политика оценивается на test. Модели обучаются на train, pruned STM использует validation для pruning. Random bid seed меняется, environment seed остаётся 1900.</div>
<h3 style="margin-top:28px">Смена планирования кампаний</h3><p>В старом JSON нет записи `campaign_planning`: плановый состав опирался на все недельные данные и реальные фазовые объёмы. В новом JSON в план попадают только комбинации запросов из train дней 0:3, а train-derived daily forecast используется и для train, validation и test. Фактический поток validation/test используется для проигрывания/отчётности, но не для формирования плана.</p><p><code>{html.escape(cp['formula'])}</code></p><div class="table-wrap"><table><thead><tr><th>Фаза</th><th>Наши кампании: сумма плановых объёмов</th><th>Три конкурента: сумма плановых объёмов</th></tr></thead><tbody>{phase_table}</tbody></table></div><p class="small">Суммы вычислены из массива `campaign_planning.plans` в новом JSON; это плановые значения, не фактические показы.</p>
</section>
<section><div class="eyebrow">02 / Случайный эталон</div><h2>Распределение случайных результатов и эффекты стратегий</h2><p>Случайная политика выбирает ставку равномерно между reserve и ценностью запроса; все 100 повторов используют один и тот же поток test, но отдельные bid-seed (1000–1099). Верхний график использует исключительно min–max random. Ниже показан отдельный масштаб delta стратегий к среднему random, чтобы не спутать позиции моделей с квантилями и не обрезать низкие baseline.</p><div class="chart">{chart_random(data, old, new)}<p>Сто точек random; цветные вертикали отмечают random p05 / медиану / p95, подписи по краям — random min и max.</p></div><div class="chart">{strategy_effect_chart(data)}<p>Каждая полоса — точно стратегия и regime из тестового JSON; значение смещения относительно среднего random (общий ноль по центру). Зелёный — выше, янтарный — ниже. Исходные totals и парные дельты находятся в таблице.</p></div><div class="metrics"><div class="metric"><b>{fmt(random_new_stats['random_p05']/1e6,3)} млн</b><span>random p05</span></div><div class="metric"><b>{fmt(random_new_stats['random_p50']/1e6,3)} млн</b><span>random медиана</span></div><div class="metric"><b>{fmt(random_new_stats['random_p95']/1e6,3)} млн</b><span>random p95</span></div><div class="metric"><b>{fmt(lo/1e6,3)}–{fmt(hi/1e6,3)} млн</b><span>random min–max</span></div></div><p class="small">Процентили и delta — описательный разброс при одной фиксированной среде, а не доверительный интервал. Повторные bid seeds не являются независимыми периодами трафика.</p></section>
<section><div class="eyebrow">03 / Результаты</div><h2>Все 16 политик — старый и train-only планы</h2><p>`ours_total` = прибыль на рынке + внешняя выручка наших кампаний. Delta старый→новый — арифметическая разность сумм: вследствие смены планов она не является эффектом изменения модели. Δ vs random — парная средняя разность к 100 random результатам этого же JSON; сравнивайте её внутри режима планирования. Δ vs shading также считается внутри одного JSON.</p><div class="table-wrap"><table><thead><tr><th>Режим</th><th>Политика</th><th>Старый total</th><th>Train-only total</th><th>Δ план</th><th>Δ shade old</th><th>Δ shade new</th><th>Δ random old</th><th>Δ random new</th><th>Random побито new</th></tr></thead><tbody>{''.join(strategy_rows)}{''.join(baselines)}</tbody></table></div><p class="caption">Beat count сравнивает стратегию со всеми 100 random `ours_total` в новом JSON. Точное равенство считается tie и не включается в strictly beaten.</p><div class="split"><div class="card"><h3>Полное наблюдение</h3><p>SM/NM используют глобальные распределения цен; NTM и STM добавляют деревья; STM pruned использует validation для pruning. Cui mixture строит логнормальную смесь кампании, point-mean сводит её к среднему. В этом сценарии SM/NM выигрывают у более сложных деревьев; Cui mixture и особенно point-mean слабее по суммарной цели.</p></div><div class="card"><h3>Цензурированное наблюдение</h3><p>При проигрыше известен лишь нижний предел цены, а не точная цена. NM здесь — оценка только по победам; SM использует Kaplan–Meier с цензурированием; NTM/STM добавляют признаки и дерево. Вывод по лидеру скромный: разница между SM/NM и соседними вариантами остаётся зависимой от этого фиксированного рынка.</p></div></div></section>
<section><div class="eyebrow">04 / Подбор baseline</div><h2>Validation выбирает коэффициент shading</h2><p>На validation перебирались значения α для ставки α·v. Выбранное значение замораживается до test; линия показывает scores именно из `validation_alpha.scores`, без пересчёта/сглаживания.</p><div class="chart">{alpha_chart(new)}<p>По вертикали `ours_total` на validation; точки — значения α, оранжевая линия — выбранный максимум.</p></div><p class="lead">Оптимум по сетке: α = {new['validation_alpha']['selected_alpha']:g}; validation score: {fmt(new['validation_alpha']['scores'][str(new['validation_alpha']['selected_alpha'])])}.</p></section>
<section><div class="eyebrow">05 / Таксономия</div><h2>Модели отвечают на разные вопросы</h2><div class="table-wrap"><table><thead><tr><th>Семейство</th><th>Режим информации / структура</th><th>Ключевая идея</th></tr></thead><tbody><tr><th>SM</th><td>Полная цена / цензурирование; глобально</td><td>Глобальная оценка цены; при цензуре — Kaplan–Meier.</td></tr><tr><th>NM</th><td>Только выигрышные наблюдения, глобально</td><td>Базовая оценка по наблюдаемым победам; проигрыши не используют как точные цены.</td></tr><tr><th>NTM</th><td>Дерево, wins-only</td><td>Нормальная модель цены в листе дерева; условные подгруппы по признакам.</td></tr><tr><th>STM</th><td>Дерево + Kaplan–Meier</td><td>Локальная survival-оценка в дереве с учётом цензуры.</td></tr><tr><th>STM pruned</th><td>STM, pruning по validation</td><td>Упрощение структуры по validation NLL; не независимая test-настройка.</td></tr><tr><th>Cui mixture</th><td>Полное / цензурированное; lognormal mixture</td><td>Оценка распределения кампаний как смеси логнормальных компонентов.</td></tr><tr><th>Cui point-mean</th><td>Среднее вместо распределения смеси</td><td>Контроль, теряющий информацию о вариативности распределения.</td></tr></tbody></table></div><p class="lead">Простая модель может выигрывать не вопреки своей простоте, а потому что сложная структура на конкретном объёме/сценарии не добавила полезного сигнала. Здесь сравнивается прибыль политики, а не чистое качество оценки распределения; это разные критерии.</p></section>
 {probability_sections(new)}
 <section><div class="eyebrow">06 / Интерпретация и ограничения</div><h2>Что эти цифры не доказывают</h2><div class="warning"><ol class="method-list"><li><b>Не причинный эффект алгоритма.</b> Между прогонами изменился план кампаний. Прямое вычитание raw totals смешивает изменение плана/рынка и изменение выбранной модели.</li><li><b>Одна synthetic campaign setup и один семидневный источник.</b> Сценарий построен симулятором на подготовленных данных, sampled fraction 0,002, environment seed 1900; не оценка разнородных реальных кампаний.</li><li><b>Сброс состояния между фазами.</b> Нет непрерывной кампании, переносимой из train в validation и test. Каждый период разыгрывается с чистым состоянием; это ограничивает практическую переносимость планирования.</li><li><b>Ошибка train-only прогноза.</b> Новый план переносит оценку дневного потока/target-match состава из трёх train-дней на будущие периоды. Report не устраняет ошибку такого прогноза, а делает источник плана явным.</li><li><b>Нет интервалов по traffic seed.</b> 100 random seed измеряют лишь условную вариативность ставки при неизменной среде. Они не дают независимых семидневных реализаций, стандартных ошибок или обобщения на популяцию.</li><li><b>Выбор стратегии по тесту запрещён.</b> Таблица сравнительная; test лидера нельзя выдавать за заранее выбранного победителя. Alpha и pruning имеют указанное использование validation.</li></ol></div><p class="lead">Для вывода об улучшении алгоритма нужен парный дизайн: одинаковые потоки и бюджеты кампаний, меняется только модель; для обобщения — повторения по независимым environment seeds/сценариям и заранее определённая метрика.</p></section>
<section><div class="eyebrow">07 / Воспроизводимость</div><h2>Источники, хэши и запуск</h2><p>HTML самодостаточен для отображения и печати; ссылки рядом открывают локальные исходные JSON рядом с отчётом. Полный повтор train-only эксперимента из корня репозитория (используйте новый output-dir, поскольку runner не перезаписывает результаты):</p><pre class="card"><code>python -m articles_prorotypes.bench.fixed_scenario_validation --prepared benchmarks/logs/prepared_20261012_retry --manager-ads benchmarks/closed_stand/manager_target50_20261012.json --our-ads benchmarks/log_benchmark/ads_manual.json --output-dir docs/benchmark/bid_forecast/results/fixed_scenario_probability_reproduced</code></pre><p>Для обновления только HTML:</p><pre class="card"><code>python -m articles_prorotypes.bench.experiment_report</code></pre><p class="small">Генератор отчёта использует только стандартную библиотеку; сеть и сервер не нужны.</p><div class="table-wrap"><table class="hash-table"><thead><tr><th>JSON</th><th>SHA-256 файла (сгенерирован при рендере)</th></tr></thead><tbody>{''.join(source_rows)}</tbody></table></div>
<details><summary>Хэши исходных массивов (из provenance нового JSON)</summary><div class="table-wrap"><table class="hash-table"><tbody>{source_hash_rows}</tbody></table></div></details><details><summary>Хэши исходного кода эксперимента (из provenance нового JSON)</summary><div class="table-wrap"><table class="hash-table"><tbody>{code_hash_rows}</tbody></table></div></details><details><summary>Среда выполнения и настройки</summary><p>Python {html.escape(new['provenance']['python'])}; NumPy {html.escape(new['provenance']['numpy'])}; семплирование {fmt(new['configuration']['sample'],3)}; q={fmt(new['configuration']['q'],1)}; reserve={fmt(new['configuration']['reserve'])}; конкурентов={new['configuration']['competitors']}; random bid seeds {new['configuration']['bid_seed']}–{new['configuration']['bid_seed']+new['configuration']['random_replicates']-1}; environment seed {new['provenance']['environment_seed']}; train sampled market requests {fmt(val['train'])}; validation {fmt(val['validation'])}; test {fmt(val['test'])}.</p><p>Полные validation-alpha scores, все 100 random записей, 16 сырых стратегий и все сравнения сохранены в исходных JSON.</p></details></section>
</main><footer><div class="wrap">Офлайн-отчёт · Все численные значения в таблицах и графиках получены из указанных завершённых JSON-файлов. Генератор не меняет исходные результаты.</div></footer></div></body></html>'''


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
