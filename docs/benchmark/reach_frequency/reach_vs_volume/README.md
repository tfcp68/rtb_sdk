# Reach vs Volume — Hypothesis A (weekly summary report)

Local README for this folder. This is branch **A** of the general report
[`../README.md`](../README.md) — here there are more details on the hypothesis itself, and all
weekly runs are combined into one table.

## What was tested (in plain words)

For each hour the balancer stores a single parameter — the hour weight `w_h` (the share of all daily
impressions that falls on that hour). But the impression volume in an hour is made up of two different
things: **how many distinct people** showed up (`reach`) and **how many times on average each of them**
was shown an ad (`freq`, frequency). `w_h` does not distinguish between them — yet for campaigns with a **per-user
impression limit** (`user_frequency_limit`) the real ceiling of an hour is set by reach
(`reach[h] × limit`), not by raw volume.

**Question:** how much do `w_h` (volume weight, what the model uses now) and `reach_share` (reach weight, what
would have to be used for user-capped campaigns) diverge on real logs? If the divergence is small, nothing needs to
change; if it is large, the model needs a separate `reach_share`.

The full statement of the hypothesis (H0/H1) and the verification plan are in [`hypothesis.md`](hypothesis.md).

## What was done (methodology, briefly)

1. For each week of logs (`E:/Logs/report-YYYYMMDD.parquet`), in a single pass we compute for
   each hour: `counts[h]` (volume), `reach[h] = COUNT(DISTINCT uid)`, `freq[h] = counts/reach`.
2. We compare `w_h = normalize(counts)` (the current model) with `reach_share_h = normalize(reach)`
   (needed for user-capped campaigns) — using the same hour bucketing logic (`_get_h_type`)
   as in production.
3. **Verdict rule declared in advance** (before running on real weeks, step 5 of
   `hypothesis.md`): `CoV(freq_h) > 0.15` **or** `max|w_h − reach_share_h| > 0.05` → H1
   (decomposition is needed); otherwise H0 (the current `w_h` is sufficient).
4. Separately we compute `TV` (Total Variation distance) between `w_h` and `reach_share_h` — the share
   of a campaign's impressions that "lies in the wrong hour" if the weights are switched from volume-based to
   reach-based. Unlike the threshold-based H0/H1, this is a continuous measure of the effect.
5. Additionally (exploratory, not part of the declared rule) — we break down `reach[h]`
   by user segments (casual/active/superactive/bot by activity percentiles)
   and see whether the audience composition changes across hours.

Implementation notebook: [`check_reach_vs_volume.ipynb`](check_reach_vs_volume.ipynb).
Weekly report generator: [`make_report.py`](make_report.py).

## Results by week

| Week | Period | Events | `CoV(freq)` (threshold 0.15) | `max\|diff\|` (threshold 0.05) | Verdict | TV wk. | TV day | EmptyUser | Report |
|---|---|---:|---:|---:|:---:|---:|---:|---:|---|
| 601 | 01.06–08.06 | 104.0M | 0.1408 | 0.0090 | **H0** | 5.78% | 4.05% | 0.0019% | [details](reports/report-20260601.md) |
| 608 | 08.06–15.06 | 237.9M | 2.5380 | 0.4712 | **H1** ⚠️ corrupt data | 47.12% | 47.11% | 0.0011% | [details](reports/report-20260608.md) |
| 615 | 15.06–22.06 | 154.4M | 0.1559 | 0.0175 | **H1** (by a hair) | 6.23% | 4.41% | 0.0012% | [details](reports/report-20260615.md) |
| 622 | 22.06–29.06 | 172.6M | 0.0919 | 0.0091 | **H0** | 3.26% | 3.25% | 0.0010% | [details](reports/report-20260622.md) |

**Week 608 is an artifact — disregard it.** ~51% of the weekly traffic is dumped into a single hour
(12:00) — a backfill/duplicate load in the logs (independently confirmed by branch B as well). Its
formal H1 and TV=47% say nothing about the hypothesis; they only reflect corrupted
data. More details — ["Data: week 608 is corrupted"](../README.md#data-week-608-is-corrupted)
in the general report.

### Audience composition by hour (exploratory, not part of the declared rule)

In all **clean** weeks the share of `superactive`/`bot` in reach grows toward the evening (by a factor of 1.5–2.7
from the morning minimum to the evening peak), while `casual` falls symmetrically. This
means that not only *how many* people show up but also *who exactly* shows up depends on the
hour — the signal is real (`EmptyUser` is negligible everywhere, ~0.001%), but the 0.15 threshold is not
calibrated for it, so it does not participate in H0/H1.

| Week | Hourly spread of `superactive`/`bot`/`casual` (CoV) |
|---|---|
| 601 | superactive 0.2604 · bot 0.2495 |
| 608 ⚠️ | superactive 0.2160 · bot 0.2971 |
| 615 | casual 0.1791 · superactive 0.2599 · bot 0.2417 |
| 622 | casual 0.2084 · active 0.2713 |

## Conclusions

1. **The H0/H1 verdict jumps from week to week, but this is noise at the 0.15 threshold, not a regime
   change.** CoV(freq) values in clean weeks: 0.14 → 0.16 → 0.09 — the label
   flips literally one step from the boundary (615: 0.156 vs 0.15).
2. **The stable signal is not the H0/H1 label but the TV magnitude: ~3–6% per week** (3.25%/3.26%
   for 622, 4.05%/5.78% for 601, 4.41%/6.23% for 615), consistently across all three clean
   weeks. The direction of the bias is always the same: `w_h` underestimates morning reach and
   overestimates evening reach.
3. **For the daily `user_frequency_limit`, `reach_share_daily` is needed, not the weekly
   `reach_share`.** The weekly denominator underestimates evening reach (regular
   visitors have already been "counted" earlier in the week), so TV_wk is higher than TV_day (601:
   5.78% vs 4.05%; 615: 6.23% vs 4.41% — a difference of 1.7–1.8 pp). For 608 and 622 the difference is
   ~0 — the pattern is unclear, but the practical conclusion does not change: for the daily limit,
   compute `reach_share_daily`.
4. **Decomposition does not pay off.** The effect of ~3–6% is of the same order as the model's own
   weekly error of `w_h` vs reality (branch B of the main report, ~5%
   out-of-sample). Introducing a separate `reach_share` into the model for a gain within
   its own noise makes no sense.
5. **Data:** week 608 is unusable for conclusions (log pipeline, spike at 12:00) —
   a ticket for the log source is needed, separate from this hypothesis.

To update/add a week, see section 5 in any of the weekly reports (replace
`PARQUET_FILE` in the notebook → `python make_report.py`).

## Folder files

- [`hypothesis.md`](hypothesis.md) — statement of the hypothesis (H0/H1) and verification plan
- [`check_reach_vs_volume.ipynb`](check_reach_vs_volume.ipynb) — verification notebook (DuckDB)
- [`make_report.py`](make_report.py) — weekly report generator from the notebook
- [`reports/`](reports) — detailed reports for each week (601/608/615/622) + charts
- [`check_reach_vs_volume.py`](check_reach_vs_volume.py) early CLI versions of the check
