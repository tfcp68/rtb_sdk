# Auction benchmark on real logs (full auction logic)

A version of the benchmark where the request stream defaults to `benchmarks/logs/janus_20261012_20261019.parquet`,
and the winner is selected through the same chain as `auction/simulation`:

```
active (start/end) → ad_frequency_limit (t/h/d/w/m, sliding windows)
  → user_frequency_limit (per user×ad pair) → min_interval → precise match → algorithm
```

Algorithms: all 13 classic strategies (best/random × one/price/velocity/heuristics, hybrid),
`balancer`, `a2_single_valued`, `a3_small` — one run each.

## Quick start

```bash
# 1. Once: parquet → compact .npy, split by Moscow calendar days
python benchmarks/log_benchmark/prepare_logs.py --workers 1

# 2. Campaigns: a manual set already exists (ads_manual.json); a generated one:
python benchmarks/log_benchmark/gen_ads.py --n 60 --seed 1

# 3. Benchmark
python benchmarks/log_benchmark/run_log_benchmark.py \
    --ads benchmarks/log_benchmark/ads_manual.json --period week

# 4. (optional) cross-check the fast engine against the SDK chain on a short window
python benchmarks/log_benchmark/verify_against_sdk.py --requests 20000 --n-ads 14
```

Report: `docs/benchmark/auction/log_replay/log_benchmark_<ts>.md` + `.json` with raw results.

The default output is `benchmarks/logs/prepared_20261012`; use `--prepared benchmarks/logs/prepared` to select the previous dataset. Original statuses are saved as `day_XX_status.npy`, aligned to requests, but the auction benchmark simulates outcomes. Missing client IDs have a shared identifier because the source has no IP; their count is recorded in metadata.

## What is in the logs and how it becomes tags

| Vocab | Request parameter | Note |
|---|---|---|
| Region | `location` | top-200, the rest is `<other>` |
| Device | `device_type` | case normalized |
| Child | `is_child` | present only for VOD (≈52%) |
| Category | `content_category` | VOD |
| Channel | `channel_id` | live, top-300 + `<other>` |

Category and Channel are mutually exclusive (verified: 0% overlap) — a campaign
targeting both will not receive any requests. User = `client_id` (uint32 hash).
`age_value` is not used (98.5% of values are "18"). A request without a feature gets the tag `<none>`
and does **not** match explicit targeting on that vocab.

## Period, scale, traffic

| Flag | Meaning |
|---|---|
| `--period day\|week\|month` | 1 / 7 / 30 days. The logs cover 7 days; for month the week is repeated "in a loop" **without** remapping users, but with noise: time shift ±`--jitter` s (default 120), request skip/duplicate with probability `--noise` (0.02) |
| `--sample F` / `--max-requests N` | Fraction of users (by `client_id` hash): per-user frequencies are preserved, total volume drops. By default sample is chosen so that nominal requests ≤ 5M |
| `--traffic shortage\|balanced\|excess` | Stream multiplier ×0.5 / ×1 / ×2 with campaign volume unchanged (as in the synthetic benchmark). ×0.5 — thinning, ×2 — request duplicated with a 1–300 s shift |
| `--volume-factor` | Total volume = factor × nominal (1.3). Scales automatically with sample/period |
| `--n-ads N [N ...]` | First N campaigns from the file |
| `--workers`, `--memory-gb` | Default 4 processes and 4 GB; the number of processes is lowered automatically if the memory estimate does not fit |
| `--no-adwords` | Do not run a2/a3 (10–15 times slower than the rest) |
| `--algos A [A ...]` | Explicit subset of algorithms |
| `--ref-no-limits` | Adds reference best_price/best_velocity runs without frequency limits |

### How `--max-requests` selects requests

This is **not** "the first N requests". `sample = max_requests / requests_in_period` is computed, and the stream
includes **all** requests of a random subset of users (by `client_id` hash) over the whole period.
Therefore the daily and weekly profile is preserved (in the logs the 4th day has ≈20% more than the 1st; the same
holds in the sample), and per-user frequencies are not distorted. The number of requests is approximate
(± a fraction of a percent due to uneven user activity).

## Campaign sets

| File | Campaigns | Description |
|---|---|---|
| `ads_manual.json` | 32 | base: with filler campaigns and two flights |
| `ads_manual_nofillers.json` | 29 | without `filler_*` (no campaigns with 100/62/33% match) |
| `ads_manual_trimmed.json` | 27 | without stores and flights, broad campaigns narrowed |
| `ads_generated.json` | 60 | `gen_ads.py`, synthetic profile |

## Campaign format

See the docstring of `ads.py`. Ad-level limits are set **relative to the uniform pace**
`volume / period` (profiles `none / loose / normal / tight` or explicit multipliers), so they
scale together with volume and period. User limits and `min_interval` are absolute.
`start_frac`/`end_frac` set the display window (flight) as a fraction of the period.

`gen_ads.py` takes the match rate, cpm, and priority of the first 40 archetypes of the synthetic set
(`auction_benchmark/seeds.py`) and picks targeting from the logs for each with the same match rate
(median deviation ≈0%); the rest are random with match rate log-uniform on [0.02; 0.5].

Limit calibration (manual set, 1 day, best_price; fill loss due to limits):
shortage ≈ −1 pp, balanced ≈ −4 pp, excess: ≈16–24% of requests are cut off by limits
(impressions are capped by volume, so their total changes little).

## How the speedup works

The sliding window "n-th impression from the end within the window" changes value only at the moment of an impression,
so on each impression `until` (the moment until which the pair is blocked) is recomputed, and the candidate check is
a single comparison `t < until`. The result matches the SDK `is_over_limit`
(verified by `verify_against_sdk.py`: winner sequences are identical for
best_one / best_price / best_velocity / best_heuristics / best_hybrid). Speed is ≈ 60–100k requests/s
per process for the classic ones; adwords (a2/a3) go through the SDK and are 10–15 times slower.

## Notes and limitations

- PRECISE only. Fuzzy and `parasitic_freq_limit` are not applied.
- `volume` is a hard cap on impressions (the SDK simulation has none; it only affects velocity).
- `min_interval` is read from `ad_frequency_limit` (as `get_ad_min_interval` does) and applied to the user×ad pair.
- `a2` and `a3` give identical results: with `budget = volume × cpm` and identical price initialization,
  the admission conditions (`matches < volume` and `remaining_budget > 0`) are equivalent.
- `filter_by_active` from the SDK is not used in verification: `DATE_ZERO` is naive, `DATE_INFINITY` is tz-aware,
  and comparing with any request date fails.
- Memory: user×ad pair state ≈ 200 B per impression per process; for month without sample
  (~590M requests) `--max-requests` is required.
