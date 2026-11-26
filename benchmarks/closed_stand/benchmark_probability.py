#!/usr/bin/env python3
"""Compare probability estimates on a shared simulator/history sequence."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import time

os.environ.setdefault('MPLCONFIGDIR', '/tmp/auction-probability-matplotlib')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np
import polars as pl

try:
    from . import stand
    from .benchmark_reconstruction import replay
    from .generate_reconstruction_campaigns import training_counts
    from .probability_metrics import metrics, cluster_intervals, selection_over_time
    from .reconstruction import RuleReconstructor, CooldownReconstructor, ValidatedRuleReconstructor, MotifReconstructor
except ImportError:
    import stand
    from benchmark_reconstruction import replay
    from generate_reconstruction_campaigns import training_counts
    from probability_metrics import metrics, cluster_intervals, selection_over_time
    from reconstruction import RuleReconstructor, CooldownReconstructor, ValidatedRuleReconstructor, MotifReconstructor

ALGORITHMS = ('hier_beta', 'hier_user', 'rule_trie', 'single_feature', 'dnf_beam',
              'dnf_cooldown_fsm', 'dnf_validated', 'motif_noisy_or')


def historical(prep, days, sample, devices):
    pool = stand.pool_mask_of(prep, devices)
    parts, statuses = [], Counter()
    for d in range(*days):
        ts, user, combo = (np.asarray(a) for a in prep.day_arrays(d))
        path = Path(prep.root) / (prep.meta['days'][d]['name'] + '_status.npy')
        status = np.load(path, mmap_mode='r')
        if len(status) != len(ts):
            raise ValueError(f'Status alignment mismatch: {path}')
        selected = pool[combo]
        m = stand._user_mask(user, sample)
        if m is not None:
            selected &= m
        statuses.update(dict(zip(*[a.tolist() for a in np.unique(status[selected], return_counts=True)])))
        selected &= np.isin(status, [200, 204])
        parts.append((ts[selected], user[selected], combo[selected], status[selected]))
        print(f'History day {d}: {selected.sum():,} usable requests', flush=True)
    log = dict(zip(('ts', 'user', 'combo', 'status'),
                   (np.concatenate([p[i] for p in parts]) for i in range(4))))
    return log, dict(status_counts={str(k): int(v) for k, v in statuses.items()},
                     excluded_statuses=sum(v for k, v in statuses.items() if k not in (200, 204)),
                     interpretation='Historical P(status=200 | observed request), not causal routing uplift')


def predict(name, prep, log, train, args):
    tags, y, ts, user = prep.combos[log['combo']], log['status'] == 200, log['ts'], log['user']
    if name in stand.MODELS:
        constructors = dict(hier_beta=stand.HierBeta, hier_user=stand.HierBetaUser, rule_trie=stand.RuleTrie)
        model = constructors[name](prep.vocab_order, m=args.m)
        model.update(tags[train], y[train], ts[train], user[train])
        result = np.empty((~train).sum())
        indices = np.flatnonzero(~train)
        hours = ts[indices] // stand.CHUNK_S
        bounds = np.r_[0, np.flatnonzero(hours[1:] != hours[:-1]) + 1, len(indices)]
        for s, e in zip(bounds[:-1], bounds[1:]):
            ii = indices[s:e]
            result[s:e] = model.score(tags[ii], ts[ii], user[ii])
            model.update(tags[ii], y[ii], ts[ii], user[ii])
        return result
    settings = dict(max_rules=args.max_rules, min_support=args.min_support, beam_width=args.beam_width)
    if name == 'single_feature':
        model = RuleReconstructor(depth=1, **settings)
    elif name == 'dnf_beam':
        model = RuleReconstructor(depth=args.depth, merge_probability=.04, **settings)
    elif name == 'dnf_cooldown_fsm':
        model = CooldownReconstructor(depth=args.depth, merge_probability=.04, **settings)
    elif name == 'dnf_validated':
        model = ValidatedRuleReconstructor(depth=args.depth, merge_probability=.04, **settings)
    else:
        model = MotifReconstructor(depth=args.depth, **settings)
    model.fit(tags[train], y[train], ts[train], user[train])
    if isinstance(model, CooldownReconstructor):
        return model.predict(tags, ts, user, y)[~train]
    return model.predict(tags[~train])


def previous_today(ts, user):
    counts, result = {}, np.empty(len(ts), dtype=np.int32)
    for i, (t, u) in enumerate(zip(ts, user)):
        key = (int(t // stand.DAY), int(u))
        result[i] = counts.get(key, 0)
        counts[key] = result[i] + 1
    return result


def fmt(v, percent=False):
    return '—' if v is None else (f'{100*v:.2f}' if percent else f'{v:.5f}')


def plot_report(out, report):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    axes[0].plot([0, 1], [0, 1], '--', color='gray')
    for name, r in report['algorithms'].items():
        c = r['metrics']['calibration']
        line, = axes[0].plot([v['predicted'] for v in c], [v['actual'] for v in c], 'o-', label=name)
        for v in c:
            ci = r['uncertainty']['calibration'].get(str(v['bin']), {}).get('actual')
            if ci:
                axes[0].vlines(v['predicted'], ci[0], ci[1], color=line.get_color(), alpha=.45)
        axes[1].plot([(v['low']+v['high'])/2 for v in c], [v['n'] for v in c], 'o-', label=name)
        s = r['metrics']['selection']
        axes[2].plot([v['q'] for v in s], [v['sellthrough'] for v in s], 'o-', label=name)
    axes[0].set(xlabel='Mean predicted P(200)', ylabel='Observed fraction of 200 responses', title='Calibration and 95% intervals', xlim=(0, 1), ylim=(0, 1))
    axes[1].set(xlabel='Forecast interval P(200)', ylabel='Number of requests', title='Prediction distribution')
    axes[2].set(xlabel='Selected request fraction q', ylabel='Share of 200 responses among selected requests', title='Selection based on recorded outcomes')
    axes[2].axhline(report['test_rate'], color='gray', linestyle='--')
    axes[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out / 'diagnostics.png', dpi=160)
    plt.close(fig)
    import matplotlib.dates as mdates
    from matplotlib.ticker import PercentFormatter
    tz = timezone(timedelta(hours=3))
    fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=True)
    for name, r in report['algorithms'].items():
        rows = r['selection_over_time']
        dates = [datetime.fromtimestamp(report['time_series']['origin_unix'] +
                                       (v['start_s'] + v['end_s']) / 2, tz) for v in rows]
        # NaN separators prevent lines bridging hours with no observations.
        x, sellout, lift = [], [], []
        for i, (date, row) in enumerate(zip(dates, rows)):
            if i and row['start_s'] != rows[i - 1]['end_s']:
                x.append(date); sellout.append(np.nan); lift.append(np.nan)
            x.append(date); sellout.append(row['sellthrough'])
            lift.append(row['lift'] if row['lift'] is not None else np.nan)
        style = dict(linestyle='--', color='black', linewidth=2) if name == 'constant_train' else {}
        axes[0].plot(x, sellout, label=name, **style)
        axes[1].plot(x, lift, label=name, **style)
    quota = report['config']['quota']
    axes[0].set(title=f'Hourly sellout: top {quota:.0%} hourly',
                ylabel='Share of 200 responses among selected requests', ylim=(0, 1))
    axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[0].legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=8)
    axes[1].set(ylabel='Lift relative to the full-hour sale rate', xlabel='Test period, Moscow-time (UTC+3)')
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%d.%m\n%H:%M', tz=tz))
    for ax in axes:
        ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(out / 'sellout_over_time.png', dpi=160)
    plt.close(fig)


def markdown(report):
    if report['mode'] == 'simulator':
        source_text = ('Requests are taken from real logs, answers 200/204 generates simulator Seller. '
                       'The campaign composition is preserved in manager_ads.json; It’s a synthetic test.')
    else:
        counts = ', '.join(f"{k}: {v:,}" for k, v in report['source']['status_counts'].items())
        source_text = (f"Original Statuses in Selected Traffic: {counts}. "
                       f"Excluded codes outside 200/204: {report['source']['excluded_statuses']:,}. "
                       'This evaluates historical status prediction; the commercial meaning of status 200 requires confirmation.')
    models = {k: v for k, v in report['algorithms'].items() if k != 'constant_train'}
    best_probability = min(models, key=lambda k: models[k]['metrics']['brier'])
    best_calibration = min(models, key=lambda k: models[k]['metrics']['ece'])
    def operating(k):
        return next(v for v in models[k]['metrics']['selection'] if v['q'] == report['config']['quota'])
    best_selection = max(models, key=lambda k: operating(k)['sellthrough'])
    lines = ['# Sale probability quality', '',
             '**Mode:** ' + report['mode'], '',
             f"Train: {report['train_n']:,}; test: {report['test_n']:,}; test users: {report['test_users']:,}.", '',
             f"Share 200 train / test: {report['train_rate']:.2%} / {report['test_rate']:.2%}.", '',
             report['period'], '',
             source_text, '',
             '## Explanation of graphs and tables', '',
             f"1. **Traffic selection:** In the chart below, each algorithm selects the best {report['config']['quota']:.0%} "
             'requests within each test hour. Sellout (sell-through) is the fraction of 200 responses among selected requests; '
             'a higher line means better selection in that hour. The dashed constant_train line represents random selection '
             'when scores are tied; its expected sale rate equals the sale rate of the entire hour.',
             '2. **Conditions change over time:** the lower panel shows Lift relative to all traffic in '
             'the same hour. A value of 1 matches the average; 1.2 means a 20% higher sale rate among selected requests. '
             'Empty hours remain gaps; points are placed at hour midpoints. Hourly volumes are available in JSON.',
             '3. **Probability accuracy:** lower Brier and Logloss values are better. '
             'ECE measures agreement between predictions and observed frequencies. ST@q and Lift@q in the table use '
             'one selection across the entire test, which can differ from the average hourly result. '
             'Detailed definitions and examples appear in the guide at the end of the report.', '',
             'The chart uses recorded responses and hourly rankings, It’s not a separate launch Seller '
             'for each algorithm. This is a retrospective screening diagnosis; It doesn’t measure growth '
             'new routing with changes in budgets and frequencies. Confidence intervals '
             'for hourly curves were not calculated; Small differences can be noise.', '',
             '![Sellout and Lift time for each algorithm](sellout_over_time.png)', '',
             '## Consolidated comparison', '',
             f"On this test smallest Brier at **{best_probability}** "
             f"({models[best_probability]['metrics']['brier']:.5f}); "
             f"smallest ECE at **{best_calibration}** "
             f"({100*models[best_calibration]['metrics']['ece']:.2f} p.p.).", '',
             f"When selecting the top {report['config']['quota']:.0%} Maximum Observable Percentage 200 "
             f"at **{best_selection}**: {operating(best_selection)['sellthrough']:.2%} "
             f"against {report['test_rate']:.2%} everywhere test. "
             'This is a descriptive comparison on fixed outcomes, No evidence of statistically significant '
             'Excellence or increase in new routing. Different winners on metrics are permissible.', '',
             '↑ — better; ↓ — less. Calibration errors and Bias Below are shown in percentage points.', '',
             '| Model | Brier ↓ | Logloss ↓ | Brier Skill ↑ | Bias, p.p. | ECE, p.p. ↓ | RMSCE, p.p. ↓ | AUC ↑ | AP ↑ | ST@q ↑ | Lift@q ↑ |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name, r in report['algorithms'].items():
        m = r['metrics']; selected = next(v for v in m['selection'] if v['q'] == report['config']['quota'])
        values = [fmt(m[k], k in ('bias', 'ece', 'rmsce')) for k in
                  ('brier', 'logloss', 'brier_skill', 'bias', 'ece', 'rmsce', 'roc_auc', 'average_precision')]
        lines.append('| ' + ' | '.join([name] + values + [fmt(selected['sellthrough']), fmt(selected['lift'])]) + ' |')
    lines += ['', f"q={report['config']['quota']:.0%}. Baseline constant_train fixed train. All indicators are weighted by request.", '',
              '![Calibration, distribution of forecasts and quality of selection](diagnostics.png)', '',
              'Exact values for each request: `test_predictions.parquet`; row — line `observations.parquet`. All metrics and cuts: `report.json`.', '',
              '## Uncertainty intervals', '',
              '95% percentile bootstrap whole-user; Training parameters are not overestimated.', '',
              '| Model | Brier | Logloss | Bias, p.p. |', '|---|---|---|---|']
    for name, r in report['algorithms'].items():
        cells = []
        for k in ('brier', 'logloss', 'bias'):
            ci = r['uncertainty']['metrics'].get(k)
            cells.append(' … '.join(fmt(v, k == 'bias') for v in ci) if ci else '—')
        lines.append('| ' + ' | '.join([name] + cells) + ' |')
    for name, r in report['algorithms'].items():
        lines += ['', '## ' + name, '',
                  '| Interval p | n | Average forecast | Share 200 | Forecast − fact, p.p. | 95% interval 200 |',
                  '|---|---:|---:|---:|---:|---|']
        for c in r['metrics']['calibration']:
            ci = r['uncertainty']['calibration'].get(str(c['bin']), {}).get('actual')
            ci_text = ' … '.join(f'{v:.2%}' for v in ci) if ci else '—'
            lines.append(f"| {c['low']:.0%}–{c['high']:.0%} | {c['n']} | {c['predicted']:.2%} | {c['actual']:.2%} | {100*c['gap']:+.2f} | {ci_text} |")
        lines += ['', '| Quotas | Selected | Sell-through | Lift |', '|---|---:|---:|---:|']
        for s in r['metrics']['selection']:
            lines.append(f"| {s['q']:.0%} | {s['selected']} | {s['sellthrough']:.2%} | {fmt(s['lift'])} |")
        lines += ['', 'Sections with a small number of observations are not shown; intervals for cuts were not calculated.', '',
                  '| Cut | Value | n | Brier | Logloss | Bias, p.p. | ECE, p.p. |', '|---|---|---:|---:|---:|---:|---:|']
        for s in r['slices']:
            m = s['metrics']
            label = str(s['value']).replace('|', '&#124;').replace('\n', ' ')
            lines.append(f"| {s['field']} | {label} | {m['n']} | {m['brier']:.5f} | {m['logloss']:.5f} | {100*m['bias']:+.2f} | {100*m['ece']:.2f} |")
    lines += ['', Path(__file__).with_name('PROBABILITY_GUIDE.md').read_text(encoding='utf-8')]
    return '\n'.join(lines) + '\n'


def evaluate(prep, log, mode, source, out, args):
    train = log['ts'] < args.split_day * stand.DAY
    if train.sum() < 10 or not (~train).any():
        raise ValueError('Need >=10 train and >=1 test observations')
    y = (log['status'] == 200)[~train]
    baseline = float((log['status'][train] == 200).mean())
    test_tags = prep.combos[log['combo'][~train]]
    history = previous_today(log['ts'], log['user'])[~train]
    slices = {'day': (log['ts'][~train] // stand.DAY).astype(str),
              'history_today': np.where(history == 0, '0', np.where(history < 5, '1–4', '5+'))}
    for field in ('Device',):
        j = prep.vocab_order.index(field)
        slices[field] = np.asarray(prep.vocabs[field])[test_tags[:, j]]
    report = dict(mode=mode, config=vars(args), source=source,
                  prepared_signature=stand.prepared_signature(prep), train_n=int(train.sum()), test_n=len(y),
                  test_users=len(np.unique(log['user'][~train])), train_rate=baseline,
                  test_rate=float(y.mean()), algorithms={})
    t0 = datetime.fromtimestamp(prep.meta['t0'], timezone(timedelta(hours=3)))
    report['time_series'] = dict(origin_unix=prep.meta['t0'], interval_seconds=stand.CHUNK_S,
                                 quota=args.quota, selection='top quota within each hour; expected random tie breaking')
    start, end = stand.parse_range(args.days)
    date = lambda d: (t0 + timedelta(days=d)).strftime('%Y-%m-%d')
    report['period'] = (f'Train: [{date(start)}, {date(args.split_day)}); '
                        f'test: [{date(args.split_day)}, {date(end)}), Moscow-time. '
                        f'Selection {args.sample:.2%} user; device pool config. '
                        'The right boundary of the period is not included. Startup settings are set in advance; '
                        'The selection of internal parameters only uses train.')
    columns = dict(row=np.flatnonzero(~train), ts=log['ts'][~train], user=log['user'][~train],
                   actual_status=log['status'][~train], previous_observed_today=history)
    for j, field in enumerate(prep.vocab_order):
        columns[field] = np.asarray(prep.vocabs[field])[test_tags[:, j]]
    for name in ['constant_train'] + args.algorithms:
        print(f'{mode}: fit/predict {name}', flush=True)
        started = time.monotonic()
        p = np.full(len(y), baseline) if name == 'constant_train' else predict(name, prep, log, train, args)
        columns[name + '_p200'] = p
        result = dict(metrics=metrics(y, p, baseline, args.bins, args.quota),
                      selection_over_time=selection_over_time(y, p, log['ts'][~train], args.quota, stand.CHUNK_S),
                      uncertainty=cluster_intervals(y, p, log['user'][~train], args.bins, args.bootstrap, args.seed),
                      seconds=time.monotonic() - started, slices=[])
        for field, values in slices.items():
            for value in np.unique(values):
                m = values == value
                if m.sum() >= args.slice_min:
                    result['slices'].append(dict(field=field, value=str(value),
                                                metrics=metrics(y[m], p[m], baseline, args.bins, args.quota)))
        report['algorithms'][name] = result
        print(f"{mode}: {name} Brier={result['metrics']['brier']:.5f}, elapsed={result['seconds']:.1f}s", flush=True)
    out.mkdir(parents=True, exist_ok=False)
    observed = dict(ts=log['ts'], user=log['user'], status=log['status'], train=train)
    for j, field in enumerate(prep.vocab_order):
        observed[field] = np.asarray(prep.vocabs[field])[prep.combos[log['combo'], j]]
    pl.DataFrame(observed).write_parquet(out / 'observations.parquet')
    pl.DataFrame(columns).write_parquet(out / 'test_predictions.parquet')
    (out / 'report.json').write_text(json.dumps(stand.privacy.report(report), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    plot_report(out, report)
    (out / 'report.md').write_text(stand.privacy.markdown(markdown(report)), encoding='utf-8')
    return report


def run(args):
    if Path(args.name).name != args.name or args.name in ('.', '..'):
        raise ValueError('name must be a directory basename')
    prep = stand.load_prepared(args.prepared)
    days = stand.parse_range(args.days)
    if not (0 <= days[0] < args.split_day < days[1] <= prep.n_days):
        raise ValueError('Require 0 <= start < split-day < end <= prepared days')
    if not (0 < args.sample <= 1 and 0 < args.q <= 1 and 0 < args.quota <= 1):
        raise ValueError('sample, q, quota must be in (0,1]')
    if args.bins < 1 or args.bootstrap < 2 or args.slice_min < 1 or args.m <= 0:
        raise ValueError('Need bins>=1, bootstrap>=2, slice-min>=1, m>0')
    root = Path(args.output_root) / args.name
    root.mkdir(parents=True, exist_ok=False)
    reports = {}
    for mode in args.modes:
        if mode == 'historical':
            log, source = historical(prep, days, args.sample, args.pool_devices)
        else:
            ads = stand.load_ads_file(args.manager_ads)
            planning = training_counts(prep, (days[0], args.split_day), args.sample, args.pool_devices)
            log, _, _ = replay(prep, ads, days, args.sample, args.q, args.seed, args.pool_devices, planning)
            log['status'] = np.where(log.pop('winner') >= 0, 200, 204)
            source = dict(manager_ads=args.manager_ads, responses='Synthetic Seller outcomes; real request features',
                          planning='Target shares from train only; seller plan scales with full replay request count')
            (root / 'manager_ads.json').write_text(json.dumps(stand.privacy.report(ads), ensure_ascii=False, indent=2), encoding='utf-8')
        reports[mode] = evaluate(prep, log, mode, source, root / mode, args)
    lines = ['# Estimation of Probability of Sale', '', 'Two independent modes with the same metrics and built-in memo.', '']
    for mode in reports:
        lines.append(f'- [{mode}: report, chart-book]({mode}/report.md)')
    lines += ['', 'Numbers between regimes reflect different outcomes; Models are compared within the mode.']
    (root / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Report: {root / "report.md"}', flush=True)
    return reports


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', required=True)
    p.add_argument('--prepared', default=stand.PREPARED)
    p.add_argument('--output-root', default=str(Path(stand.RUNS) / 'probability'))
    p.add_argument('--modes', nargs='+', choices=['simulator', 'historical'], default=['simulator', 'historical'])
    p.add_argument('--algorithms', nargs='+', choices=ALGORITHMS, default=list(ALGORITHMS))
    p.add_argument('--manager-ads', default=str(Path(__file__).with_name('manager_target50_20261012.json')))
    p.add_argument('--days', default='0:4')
    p.add_argument('--split-day', type=int, default=3)
    p.add_argument('--sample', type=float, default=.002)
    p.add_argument('--q', type=float, default=.8, help='Random share sent to simulator; ignored for historical data')
    p.add_argument('--quota', type=float, default=.8, help='Selection quality operating quota')
    p.add_argument('--pool-devices', nargs='+', default=stand.POOL_DEVICES)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--bins', type=int, default=10)
    p.add_argument('--bootstrap', type=int, default=200)
    p.add_argument('--slice-min', type=int, default=100)
    p.add_argument('--m', type=float, default=20)
    p.add_argument('--max-rules', type=int, default=12)
    p.add_argument('--min-support', type=int, default=30)
    p.add_argument('--beam-width', type=int, default=12)
    p.add_argument('--depth', type=int, default=3)
    return p


if __name__ == '__main__':
    run(parser().parse_args())
