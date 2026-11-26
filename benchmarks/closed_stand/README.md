# "Closed manager" stand

A test bench for the new log format: part of the requests goes to an unknown company (the "manager"), which answers **200** (sold) or **204**.
The goal is to send the manager a given share of requests and maximize the share of 200s among the sent ones.

## Scheme

```
open   (run 1)  manager is VISIBLE (manager_ads.json) ─ a policy picks what goes to it ─► train_log.parquet
                                                                                           │ request features + 200/204 only
closed (run 2)  manager is HIDDEN ─ the algorithm learns from the log, routes by p̂(x) ◄────┘
```

* **Pool** — requests that may be sent to the manager (by default all set-top boxes / smart TVs, ≈61% of traffic).
* **Manager** — synthetic campaigns (`manager_target50_20261012.json` by default), calibrated for approximately 50% random sell-through at q=0.8, with their own auction (the same filters as in `log_benchmark`:
  sliding frequency windows, min_interval, volume, flights; best_price). A request is 200 if the inner auction picked a company, otherwise 204.
  Company volumes are derived from the expected number of sent requests and from match rates **inside the pool**.
* **Our companies** (`../log_benchmark/ads_manual.json`) get everything that did not go to the manager (`--fallback-204` also gives them the 204s).
* The price of a 200 is fixed (`--manager-price`, default 150, in the engine's cpm units).
* The log contains no targeting, frequencies or winners of the manager. The default request stream is `logs/prepared_20261012`, prepared from `janus_20261012_20261019.parquet`. The stand simulates 200/204 responses; original statuses are preserved separately, not treated as counterfactual outcomes.

## Running

```bash
# run 1: random 50% of the pool (or --policy all: the whole pool, no selection), days 0..3 — training
python benchmarks/closed_stand/stand.py open --name demo --policy random --q 0.5 --days 0:4

# run 2: test on days 4..6
python benchmarks/closed_stand/stand.py closed --name demo --days 4:7 --policies random hier_beta all

# train / validation / test: m is tuned on validation, the test stays clean
python benchmarks/closed_stand/stand.py closed --name demo --val-days 4:5 --days 5:7 --tune-m 5 20 80
```

`--q` in closed is the target share of the eligible pool (default: 0.8, independently of open). The default pool is the listed set-top-box and smart TV devices; requests outside it stay with our companies. Artifacts: `docs/benchmark/manager_routing/runs/<name>/`
(`train_log.parquet`, `meta.json`, `open_report.md`, `closed_report_*.md/json`). A run on 2M requests takes seconds.

## Report metrics

* **Sent / pool** (and / all traffic) — quota fulfilment; **Sell-through** = 200 / sent; 200 / pool; number of 200s.
* Manager revenue (200 × price), revenue of our companies, total. Per day.
* Whole run: impressions, sell-out and revenue of each of our companies; losses due to missing targeting / filters.
* "Hidden manager companies" — simulator diagnostics, not visible to the algorithm.

## Algorithms

`rule_trie` averages smoothed probabilities from sparse tries over individual features and selected pairs. Its reported segments describe observed outcomes, not identified campaigns; it does not yet model time or user history separately.

`calibrate_manager.py --out <new.json>` adjusts plan weights and tests frequency multipliers. By default it selects the candidate closest to 50% random-policy sell-through; `--objective campaign` selects by campaign sell-out deviation. `calibrate_targeting.py` additionally searches bounded additions to synthetic target lists. Both evaluate on later days, preserve the input, and do not guarantee the target or optimize revenue. Match rates are based on all prepared days, including the evaluation period. Pass the generated file to `stand.py open --manager-ads <new.json>`.

An algorithm = a `Predictor` (`predictors.py`): `update(tags, y, ts, user)` and `score(tags, ts, user) -> p̂`.
Currently: `HierBeta` — a hierarchical Beta with shrinkage to the parent (§4.1 of strategy.md; levels: device → +region →
+category/channel → full profile; `m` is the prior strength). Routing (`routers.py`): `ThresholdQuota` — threshold τ as a
quantile of p̂ over the recent pool for the share q, ε of random exploration (§5), quota correction by the accumulated error,
online retraining on the manager's answers every hour. Baselines: `random` (same quota), `all`.
Models from `log_eda/models` (EDA of the labeled janus log):
* `catboost` (`CatBoostPredictor`) — model B: CatBoost on the 5 tags (categorical) + hour; refit from scratch
  on all answers every 24 updates (once a day), up to 500k rows, trees by early stopping on a 10% holdout.
* `catboost_fb` (`UserCatBoost(stream=False)`) — the same + the manager's answers to this user known before the start
  of the current hour: 200s and sends over 24h, 200s overall, the last answer. Only `update`/`score`.
* `catboost_user` (`UserCatBoost(stream=True)`) — plus our own pool traffic of the user: requests over 1h and 24h
  before t, time since the previous request. The router passes the chunk's pool requests via `observe_pool`; `open`
  writes `pool_log.parquet` for training (the whole pool, sent or not).

  Both are fit once on the log and start the closed run with an empty history (fresh manager, another ts scale).
  `check_user_features.py` checks that the features use only data already available.
* `xgboost`, `xgb_fb`, `xgb_user` (`XGBPredictor`, `UserXGB`) — the same three models on XGBoost (hist, categorical tags,
  lr 0.1, depth 8, min_child_weight 50, λ 5, max_cat_threshold 16). Train 4.5–5.6× faster than CatBoost with the same
  sell-through (±0.2 pp); with CatBoost's params (lr 0.2, depth 6) they overfit. Requires `pip install xgboost`.

A new algorithm = a new predictor class plus a line in `MODELS` (`stand.py`). Without `fork` (Windows) the policies run one by one.

## Verification

`verify_seller.py` — the stand's auction gives the same impressions as `run_algorithm(best_price)` from `log_benchmark`.

## Calibration of manager's plans

`calibrate_manager.py` creates a separate configuration for the same campaigns by adjusting planned volume weights (`volume_weight`) and frequency limits:

```bash
python benchmarks/closed_stand/calibrate_manager.py \
  --out benchmarks/closed_stand/manager_calibrated_new.json \
  --days 0:3 --eval-days 3:4 --sample 0.003 --target 0.6 --iterations 5

python benchmarks/closed_stand/stand.py open --name balanced \
  --manager-ads benchmarks/closed_stand/manager_calibrated_new.json --q 0.8 --days 0:4
python benchmarks/closed_stand/stand.py closed --name balanced \
  --val-days 4:5 --days 5:7 --policies random hier_beta hier_user rule_trie --tune-m 5 20 80
```

At each step, the tool simulates random routing with the same quota and reduces plan weights for campaigns that underdeliver. The total planned volume remains approximately constant, and relative frequency limits scale with each plan. After selecting plans, it independently tries common ad-limit and user-limit multipliers (1, 1.25, 1.5). Multipliers apply to the input JSON, with integer limits rounded down. Windows, absent limits, and `min_interval` remain unchanged. Set the multipliers with `--ad-frequency-factors` and `--frequency-factors`; applying calibration to an already calibrated file can relax limits further.

By default, calibration selects random-routing sell-through closest to 50% (`--objective sellthrough --target-sellthrough 0.5`). `--objective campaign` selects the previous objective: weighted deviation of campaign sellout from `--target`. The selected configuration is then evaluated on `--eval-days`. The original JSON remains unchanged, and an existing output file is never overwritten. History and diagnostics are stored in the new file's `meta`. This heuristic does not guarantee the target or optimize algorithm uplift or revenue. Targeting shares use frequencies from all days of the prepared traffic, so evaluation is not fully isolated from future data.

`calibrate_targeting.py` further tunes synthetic targeting. Each step considers expanding one existing tag list and selects the candidate that brings random-routing sell-through closer to the target on calibration days. The search is restricted to these candidates and does not reconstruct real campaigns. Run `--help` for parameters.

## Separate reconstruction benchmark

[Campaign reconstruction](RECONSTRUCTION.md) includes a dedicated diverse
targeting generator, validation-tuned DNF and motif discovery with EM/noisy-OR.
Generated campaigns are the default only for `benchmark_reconstruction.py`; the
regular closed-manager stand keeps its existing campaign configuration.

## Probability quality on simulator and historical responses

```bash
python -m benchmarks.closed_stand.benchmark_probability \
  --name probability_week --days 0:7 --split-day 4 --sample 0.002
```

Both `simulator` and `historical` modes run by default. Historical mode retains
original 200/204 statuses and reports excluded codes. Models share one observed
sequence per mode; predictor updates happen after each completed hour, while
reconstruction methods retain their static/FSM protocol. This assesses forecast
quality, not causal uplift under a different routing policy.

Outputs under `docs/benchmark/manager_routing/runs/probability/<name>/`: an index and, per mode,
Markdown/JSON reports, a PNG diagnostic figure, observations and per-request
predictions in Parquet. Each report embeds a beginner-oriented English
[metrics guide](PROBABILITY_GUIDE.md). Prediction `row` indexes `observations.parquet`.
`sellout_over_time.png` compares hourly sell-through and Lift for the best
`--quota` fraction of each hour's requests, with one curve per algorithm.
Exact points are stored in `algorithms.<name>.selection_over_time` in JSON.
This is retrospective selection on fixed outcomes, without resimulating budgets
or frequency caps. Regional slices are omitted from Markdown and JSON reports;
the original features remain in the local Parquet artifacts.
Existing runs are never overwritten. Figures require `matplotlib`.
Use `--modes historical` or `--algorithms hier_beta hier_user rule_trie` to restrict
execution. `--q` controls only simulator sending; `--quota` controls the selection
metric operating point. `--bootstrap` defaults to 200 whole-user resamples for
Brier, Logloss, bias and calibration-bin confidence intervals.
