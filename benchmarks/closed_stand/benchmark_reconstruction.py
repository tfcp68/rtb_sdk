#!/usr/bin/env python3
"""Replay a hidden seller, reconstruct campaigns from public responses, audit truth.

python benchmarks/closed_stand/benchmark_reconstruction.py --name reconstruction_small
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
import time

import numpy as np
import polars as pl

try:
    from . import stand
    from .reconstruction import RuleReconstructor, CooldownReconstructor, ValidatedRuleReconstructor, MotifReconstructor, response_metrics, compare_targeting
    from .generate_reconstruction_campaigns import from_prepared, training_counts, add_generation_arguments, generation_settings
except ImportError:
    import stand
    from reconstruction import RuleReconstructor, CooldownReconstructor, ValidatedRuleReconstructor, MotifReconstructor, response_metrics, compare_targeting
    from generate_reconstruction_campaigns import from_prepared, training_counts, add_generation_arguments, generation_settings


def replay(prep, ads, days, sample, q, seed, pool_devices, planning_counts=None):
    """One continuous seller lifetime, including across the train/test boundary."""
    pool = stand.pool_mask_of(prep, pool_devices)
    _, count = stand.count_requests(prep, days, sample, pool)
    pool_prep = dataclasses.replace(prep, combo_counts=(prep.combo_counts if planning_counts is None else planning_counts) * pool)
    pack = stand.build_pack(pool_prep, ads, max(1, round(q * count)), days[1] - days[0], 1.3, True)
    seller = stand.Seller(pack, stand.build_match_lists(prep, pack.targets))
    rng = np.random.default_rng(seed)
    parts = []
    for day, ts, user, combo in stand.iter_chunks(prep, days, sample):
        sent = pool[combo] & (rng.random(len(combo)) < q)
        ts, user, combo = ts[sent], user[sent], combo[sent]
        winner = np.array([seller.serve(int(t), int(u), int(c)) for t, u, c in zip(ts, user, combo)], dtype=np.int32)
        parts.append((ts + days[0] * stand.DAY, user, combo, winner))
        if len(parts) % 24 == 0:
            print(f"Replay: day {days[0] + day}, sent {sum(len(p[0]) for p in parts):,}", flush=True)
    log = dict(zip(("ts", "user", "combo", "winner"), (np.concatenate([p[i] for p in parts]) for i in range(4))))
    return log, pack, seller


def truth_masks(prep, pack, profiles):
    masks = []
    for target in pack.targets:
        mask = np.ones(len(profiles), dtype=bool)
        for field, name in enumerate(prep.vocab_order):
            if name in target:
                values = [prep.vocabs[name].index(label) for label in target[name]]
                mask &= (profiles[:, field] != 0) & np.isin(profiles[:, field], values)
        masks.append(mask)
    return masks


def write_markdown(report):
    def cell(value):
        return str(value).replace("&", "&amp;").replace("|", "&#124;").replace("`", "&#96;").replace("\n", "<br>")

    def target_cell(targets):
        return f"`{cell(json.dumps(targets, ensure_ascii=False))}`" if targets else "Unrestricted"

    lines = ["# Rebuilding Hidden Campaigns", "",
             "Algorithms enter: query, time, user, 200/204. "
             "Winners and Seller Configuration are used only in the evaluation.", "",
             f"Train: {report['train_n']:,}; test: {report['test_n']:,}. "
             "Time breakdown; The auction is not dropped at the border.", "",
             "IoU Targeting is weighted by profile frequencies **Only sent test requests**. "
             "Comparison of campaigns: mutually explicit IoU ≥ 0.5. "
             "In recall There are also campaigns without screenings; Outside of test traffic, targeting is not checked.", "",
             "Campaigns with the same observed behavior are not identifiable. "
             "The rules found — hypotheses: names, CPM, budget, Accurate frequencies and flutes are not restored. "
             "Cooldown — hypothetical, not measured min_interval real-life.", "",
             "motif_noisy_or: P(200)=1−(1−background)∏(1−activation) coincidentally. "
             "In his table P(200) indicates the probability of activation of a particular motif, "
             "Not the full probability of a response when crossing the rules.", "",
             "## Comparison of algorithms", "",
             "| Algorithm | Hypotheses | Brier ↓ | Logloss ↓ | Accuracy | Precision campaign | Recall campaign | IoU union |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, result in report["algorithms"].items():
        r, t = result["response"], result["targeting"]
        lines.append(f"| {name} | {len(result['hypotheses'])} | {r['brier']:.4f} | {r['logloss']:.4f} | "
                     f"{r['accuracy']:.3f} | {t['campaign_precision']:.3f} | {t['campaign_recall']:.3f} | {t['union_iou']:.3f} |")
    base = report["constant_baseline"]
    lines.extend(["", f"constant (share 200 in train): Brier={base['brier']:.4f}, Logloss={base['logloss']:.4f}.", "",
                  "Static models don’t use answers test. FSM preview, then receives "
                  "factual 200/204 for the next request. Parameters FSM chosen on the inner tail train; "
                  "starting-state test history-warmed train.", "",
                  "## Real and Restored Targeting", "",
                  "In every line — real-life, near — The closest hypotheses of each algorithm "
                  "with numbers from the prediction sections and IoU. Each hypothesis is shown at its nearest "
                  "real-life, including IoU < 0.5; That doesn’t mean it, that the campaign has been re-established. "
                  "«No nearby hypotheses» signifier, No hypothesis has chosen this campaign for the nearest future. "
                  "Empty targeting is shown as «Unrestricted».", "",
                  "| A real campaign | Real-life targeting | "
                  + " | ".join(cell(name) for name in report["algorithms"]) + " |",
                  "|---|---|" + "---|" * len(report["algorithms"])])
    for ad in report["truth"]:
        columns = [cell(ad["id"]), target_cell(ad["targets"])]
        for result in report["algorithms"].values():
            hypotheses = [
                f"№ {match['hypothesis']}: {target_cell(rule['targets'])} (IoU={match['iou']:.3f})"
                for rule, match in zip(result["hypotheses"], result["targeting"]["best_matches"])
                if match["closest_truth"] == ad["id"]
            ]
            columns.append("<br>".join(hypotheses) or "No nearby hypotheses")
        lines.append("| " + " | ".join(columns) + " |")
    lines.extend(["", "## What was inside", ""])
    for ad in report["truth"]:
        lines.append(f"- **{ad['id']}**: targeting `{json.dumps(ad['targets'], ensure_ascii=False)}`; "
                     f"impressions train/test={ad['train_impressions']}/{ad['test_impressions']}; plan={ad['volume']}; "
                     f"min_interval={ad['min_interval']}; user limits={ad['user_lims']}; "
                     f"ad limits={ad['ad_lims']}; flight={ad['start_s']}…{ad['end_s']} s.")
    for name, result in report["algorithms"].items():
        lines.extend(["", f"## Predictions {name}", "",
                      "| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |",
                      "|---|---|---:|---:|---:|---|---:|"])
        for i, (rule, match) in enumerate(zip(result["hypotheses"], result["targeting"]["best_matches"]), 1):
            target = json.dumps(rule["targets"], ensure_ascii=False)
            lines.append(f"| {i} | `{target}` | {rule['probability']:.3f} | {rule['support']} / {rule['successes']} | "
                         f"{rule['cooldown_seconds']} | {match['closest_truth']} | {match['iou']:.3f} |")
        if not result["hypotheses"]:
            lines.append("| — | There are no rules with sufficient support | | | | | |")
    return "\n".join(lines) + "\n"


def run(args):
    prep = stand.load_prepared(args.prepared)
    start, end = stand.parse_range(args.days)
    if not (0 <= start < args.split_day < end <= prep.n_days):
        raise ValueError("Require 0 <= start < split-day < end <= prepared days")
    if not (0 < args.sample <= 1 and 0 < args.q <= 1):
        raise ValueError("sample and q must be in (0, 1]")
    if Path(args.name).name != args.name or args.name in (".", ".."):
        raise ValueError("name must be a directory basename")
    out = Path(args.output_root) / args.name
    # Refuse to overwrite earlier experiments.
    out.mkdir(parents=True, exist_ok=False)
    planning_counts = None
    if args.manager_ads:
        ads = stand.load_ads_file(args.manager_ads)
        campaign_config = dict(meta=dict(source=args.manager_ads), ads=ads)
        planning_counts = training_counts(prep, (start, args.split_day), args.sample, args.pool_devices)
    else:
        print("Generate reconstruction-only campaigns from training traffic", flush=True)
        campaign_config, planning_counts = from_prepared(
            prep, (start, args.split_day), args.sample, args.pool_devices, **generation_settings(args))
        ads = campaign_config["ads"]
    (out / "manager_ads.json").write_text(json.dumps(stand.privacy.report(campaign_config), ensure_ascii=False, indent=2), encoding="utf-8")
    print("Replay hidden seller", flush=True)
    log, pack, seller = replay(prep, ads, (start, end), args.sample, args.q, args.seed, args.pool_devices, planning_counts)
    train = log["ts"] < args.split_day * stand.DAY
    test = ~train
    if train.sum() < 10 or not test.any():
        raise ValueError("Need >=10 training and >=1 test observations; increase sample or day ranges")
    tags = prep.combos[log["combo"]]
    y = log["winner"] >= 0
    # Observable log and simulator-only audit data are separate artifacts.
    columns = {"ts": log["ts"], "user": log["user"], "status": np.where(y, 200, 204), "train": train}
    for i, field in enumerate(prep.vocab_order):
        columns[field] = np.asarray(prep.vocabs[field], dtype=object)[tags[:, i]]
    pl.DataFrame(columns).write_parquet(out / "observations.parquet")
    pl.DataFrame({"row": np.arange(len(y)), "winner_index": log["winner"]}).write_parquet(out / "truth_winners.parquet")
    profiles, weights = np.unique(tags[test], axis=0, return_counts=True)
    actual_masks = truth_masks(prep, pack, profiles)
    truth = [dict(id=pack.ids[a], name=pack.names[a], targets=pack.targets[a], volume=pack.volume[a],
                  cpm=pack.cpm[a], min_interval=pack.min_interval[a], ad_lims=pack.ad_lims[a],
                  user_lims=pack.user_lims[a], start_s=pack.start_s[a], end_s=pack.end_s[a],
                  train_impressions=int(np.sum(log["winner"][train] == a)),
                  test_impressions=int(np.sum(log["winner"][test] == a))) for a in range(pack.n)]
    report = dict(config=vars(args), campaign_generation=campaign_config["meta"],
                  prepared_signature=stand.prepared_signature(prep),
                  train_n=int(train.sum()), test_n=int(test.sum()), truth=truth, algorithms={},
                  constant_baseline=response_metrics(y[test], np.full(test.sum(), y[train].mean())),
                  evaluation_domain="sent test requests; traffic-weighted targeting IoU",
                  matching="greedy one-to-one IoU >= 0.5")
    predictions = {"row": np.flatnonzero(test), "actual_status": np.where(y[test], 200, 204),
                   "actual_winner_index": log["winner"][test]}
    settings = dict(max_rules=args.max_rules, min_support=args.min_support, beam_width=args.beam_width)
    for name, model in (("single_feature", RuleReconstructor(depth=1, **settings)),
                        ("dnf_beam", RuleReconstructor(depth=args.depth, merge_probability=0.04, **settings)),
                        ("dnf_cooldown_fsm", CooldownReconstructor(depth=args.depth, merge_probability=0.04, **settings)),
                        ("dnf_validated", ValidatedRuleReconstructor(depth=args.depth, merge_probability=0.04, **settings)),
                        ("motif_noisy_or", MotifReconstructor(depth=args.depth, **settings))):
        print(f"Fit {name}", flush=True)
        begun = time.monotonic()
        # This API gets only the observable columns. No pack, ids, targets, budgets or winner labels.
        model.fit(tags[train], y[train], log["ts"][train], log["user"][train])
        if isinstance(model, CooldownReconstructor):
            # Replay training history to warm user state; each test response is revealed AFTER scoring.
            probability = model.predict(tags, log["ts"], log["user"], y)[test]
        else:
            probability = model.predict(tags[test])
        predictions[name + "_p200"] = probability
        report["algorithms"][name] = dict(
            hypotheses=[rule.export(prep.vocab_order, prep.vocabs) for rule in model.rules],
            response=response_metrics(y[test], probability),
            targeting=compare_targeting(model.rules, profiles, weights, actual_masks, pack.ids),
            selected_negative_penalty=getattr(model, "selected_negative_penalty", None),
            seconds=time.monotonic() - begun)
    pl.DataFrame(predictions).write_parquet(out / "test_predictions.parquet")
    (out / "report.json").write_text(json.dumps(stand.privacy.report(report), ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "report.md").write_text(stand.privacy.markdown(write_markdown(report)), encoding="utf-8")
    print(f"Report: {out / 'report.md'}", flush=True)
    return report


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", required=True)
    p.add_argument("--prepared", default=stand.PREPARED)
    p.add_argument("--manager-ads", help="Use an existing JSON instead of generating reconstruction-only campaigns")
    p.add_argument("--output-root", default=str(Path(stand.RUNS) / "reconstruction"))
    p.add_argument("--days", default="0:4")
    p.add_argument("--split-day", type=int, default=3)
    p.add_argument("--sample", type=float, default=0.002)
    p.add_argument("--q", type=float, default=0.8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--pool-devices", nargs="+", default=stand.POOL_DEVICES)
    p.add_argument("--max-rules", type=int, default=12)
    p.add_argument("--depth", type=int, default=3)
    p.add_argument("--min-support", type=int, default=30)
    p.add_argument("--beam-width", type=int, default=12)
    add_generation_arguments(p)
    return p


if __name__ == "__main__":
    run(parser().parse_args())
