# Traffic Routing with XGBoost and CatBoost: A Three-Seed Simulation Study

## Abstract

This note reports a completed CPU experiment comparing six XGBoost and CatBoost routing policies with a matched random baseline at manager-pool quotas of 60% and 80%. Each policy and quota was evaluated with seeds 43, 44, and 45 on the same prepared traffic sample and test days. Adding past manager-response features (`*_fb`) raised simulated manager sell-through substantially over random routing. For `xgb_fb`, the mean increase was 13.923 percentage points at the 60% quota and 5.653 points at the 80% quota. The system-wide revenue result was much smaller: the mean was 221,280 report units above random at 60% and 768,270 units above random at 80%. At 80%, however, plain `xgboost` had slightly higher mean total revenue than `xgb_fb`, while using less elapsed evaluation time. These are historical results from a simulated auction on one prepared traffic period, not observed HTTP outcomes, currency-denominated revenue, evidence of statistical significance, or production performance.

## Research questions

1. At matched traffic-pool quotas, do learned XGBoost and CatBoost policies increase the proportion of manager submissions returning a simulated `200` compared with random routing?
2. Do response-history features improve routing outcomes, and do the gains translate into higher total simulated revenue after accounting for the traffic left to the house campaigns?
3. What trade-offs in total revenue and full evaluation time accompany the differences in sell-through?

## Experiment scope and design

The selected experiment is the completed CPU series `seeds_43_45_q60_q80` together with the separately saved, matched `random_43_45_q60_q80` control. It contains 42 completed evaluations: six model policies at two quotas across three seeds, plus random at the same two quotas and three seeds. No new runs were performed for this note.

| Design element | Evidence-backed setting |
|---|---|
| Seeds | 43, 44, 45; the seed varies the closed-run sample/training randomness and router choices as described in the source report |
| Quota | 0.60 or 0.80 of the eligible manager pool |
| Test split | Days 5:7, corresponding to 6-7 October 2026 in the prepared traffic description |
| Training observations | Shared open-run training log from days 0:4; 1,542,430 labeled submitted requests |
| Test sample | 2,279,395 requests, including 1,417,561 eligible pool requests |
| User sample | Sampling fraction 0.05834053566692987, held constant across the series and random controls |
| Routing exploration | Model policies use `epsilon=0.02`; random uses `RandomShare` and has no separate epsilon or learned threshold |
| Return behavior | `fallback_204` is disabled |
| Evaluation timing | Full per-evaluation elapsed time includes initial fitting, simulator preparation, and test simulation; shared imports and initial data loading are excluded. No profiler was used. |
| Runtime versions in saved configuration | Python 3.12.10, XGBoost 3.4.1, CatBoost 1.2.10 |

The manager pool contains eligible TV/STB device categories. Web and mobile requests are outside this pool. The test stream comes from prepared traffic logs dated 1-7 October 2026. The selected sample and simulation use the same campaigns, manager price, traffic, and test window across the compared policies. Random shares each eligible pool request independently with probability equal to the target quota. The model policies use a learned probability threshold, quota correction, and 2% random exploration. Equal seed values do not imply that different policies route identical requests.

## Models and input features

All six learned policies predict the probability that the simulated manager returns `200`. The training target is `1` for `status == 200` and `0` otherwise; the negative response in this run is `204`. Model families use the same feature groups, but the learning algorithms differ.

| Policy family | Feature count | Feature groups |
|---|---:|---|
| `xgboost`, `catboost` | 6 | Five request tags and hour of day |
| `xgb_fb`, `catboost_fb` | 10 | Base six plus four response-history features |
| `xgb_user`, `catboost_user` | 13 | Base six, four response-history features, and three pool-activity features |

The five request tags are region, device, child, category, and channel. In the source data their column labels are `Region`, `Device`, `Child`, `Category`, and `Channel` (translated from the original labels), respectively. These are categorical values encoded as dictionary indices, not ordinal measurements. The sixth feature is hour of day, computed as `(ts % 86400) // 3600`.

The response-history features are `n200_24h`, `nsent_24h`, `n200_all`, and `last_status`. They describe the current user's manager responses up to the start of the current hour, excluding the current hour. The three additional pool-history features are `npool_1h`, `npool_24h`, and `dt_prev_pool`; they describe the user's eligible-pool activity, including requests not sent to the manager. They are computed over windows ending strictly before the current request timestamp. The user identifier and timestamp are history lookup keys and are not passed as independent model features. Current response, target quota, epsilon, threshold, and quota error are not model features.

## Metrics and aggregation

For evaluation `i`, let `S_i` be the number of requests sent to the manager, `Y_i` the number returning simulated `200`, `P_i` the number of eligible pool requests, and `R_i` the total revenue reported by the simulator.

- **Sell-through:** `Y_i / S_i`. The reported summary is the arithmetic mean of per-run rates, multiplied by 100. This is not classifier accuracy: it is the success fraction among routed manager requests.
- **Sent share of pool:** `S_i / P_i`. The quota is a target share, not a guaranteed count; small differences in realized shares remain.
- **Total revenue:** manager revenue plus revenue from the house campaigns on requests not sent to the manager. It is reported in the simulator's internal report units. It is not documented as a real-world currency amount.
- **Full elapsed time:** per-evaluation wall-clock seconds for initial model fitting, simulator preparation, and test simulation, excluding common imports and initial source-data loading.
- **Across-seed SD:** sample standard deviation (`n-1` denominator) of the three per-run sell-through percentages. It describes dispersion across these three seeds on the same underlying period. It is not a confidence interval, standard error, or estimate of future-period uncertainty.
- **Paired xgb_fb contrast to random:** within each quota, pair the model and random evaluation by seed. The reported sell-through difference is `100 * mean(xgb_fb.sellthrough_i - random.sellthrough_i)` in percentage points. Revenue difference is `mean(xgb_fb.total_revenue_i - random.total_revenue_i)` in report units. Revenue percentage change is `100 * (mean model revenue / mean random revenue - 1)`.

All means and SDs below were independently recalculated from the per-evaluation JSON files. Percentages and time are rounded for display. Total revenue is rounded to the nearest report unit. There are three evaluations in every row.

## Results: full 14-row summary

| Target pool quota | Policy | Evaluations | Sell-through, mean +/- sample SD (%) | Sent / pool, mean (%) | Total revenue, mean (report units) | Full time, mean (s) |
|---:|---|---:|---:|---:|---:|---:|
| 60% | `random` | 3 | 44.863 +/- 0.041 | 59.974 | 334,313,810 | 25.4 |
| 60% | `xgboost` | 3 | 55.878 +/- 0.048 | 59.956 | 328,676,208 | 200.6 |
| 60% | `xgb_fb` | 3 | 58.786 +/- 0.009 | 60.035 | 334,535,090 | 296.3 |
| 60% | `xgb_user` | 3 | 58.793 +/- 0.017 | 60.113 | 330,756,300 | 369.6 |
| 60% | `catboost` | 3 | 55.751 +/- 0.053 | 59.926 | 328,010,157 | 524.9 |
| 60% | `catboost_fb` | 3 | 58.785 +/- 0.011 | 60.039 | 334,281,902 | 431.2 |
| 60% | `catboost_user` | 3 | 58.779 +/- 0.018 | 60.108 | 330,119,950 | 476.2 |
| 80% | `random` | 3 | 40.905 +/- 0.006 | 79.977 | 305,075,572 | 17.0 |
| 80% | `xgboost` | 3 | 46.287 +/- 0.007 | 79.961 | 305,884,463 | 205.9 |
| 80% | `xgb_fb` | 3 | 46.557 +/- 0.012 | 79.982 | 305,843,842 | 303.9 |
| 80% | `xgb_user` | 3 | 46.493 +/- 0.011 | 80.043 | 304,444,310 | 366.5 |
| 80% | `catboost` | 3 | 46.277 +/- 0.005 | 79.905 | 305,838,258 | 537.7 |
| 80% | `catboost_fb` | 3 | 46.575 +/- 0.015 | 79.949 | 304,969,333 | 465.9 |
| 80% | `catboost_user` | 3 | 46.486 +/- 0.009 | 80.046 | 303,649,058 | 485.8 |

## Primary contrasts: `xgb_fb` versus random

| Target pool quota | xgb_fb sell-through (%) | Random sell-through (%) | Difference (percentage points) | xgb_fb total revenue | Random total revenue | Difference (report units) | Relative revenue change |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 60% | 58.786 | 44.863 | +13.923 | 334,535,090 | 334,313,810 | +221,280 | +0.066% |
| 80% | 46.557 | 40.905 | +5.653 | 305,843,842 | 305,075,572 | +768,270 | +0.252% |

At 60%, the per-seed sell-through gains were +13.886, +13.920, and +13.964 percentage points for seeds 43, 44, and 45. Total revenue exceeded its matched random result in all three runs by 264,515, 172,765, and 226,560 report units, respectively. At 80%, the corresponding sell-through gains were +5.650, +5.661, and +5.648 points; total-revenue differences were +768,475, +759,730, and +776,605 units.

The paired contrasts are descriptive. The same test period and open-training log are shared by all seeds, and three seed pairs do not establish statistical significance or generalization to other periods. The apparent revenue gains are small in relative terms, especially at 60%. Sell-through measures success among manager submissions, while total revenue also reflects the value of traffic remaining for house campaigns. Thus the large change in sell-through must not be read as a similar increase in system revenue.

### Interpretation across policy variants

At 60%, `xgb_fb` and `catboost_fb` had nearly identical mean sell-through. For XGBoost, adding pool-activity history (`xgb_user` rather than `xgb_fb`) changed mean sell-through by only about +0.007 percentage points, while mean total revenue was lower by 3,778,790 report units and mean elapsed time was about 73.3 seconds longer. At 80%, `xgb_user` was lower than `xgb_fb` in both mean sell-through and mean total revenue. The added pool-history group therefore showed no clear system-level benefit in this series; this comparison evaluates feature groups, not individual feature ablations.

At 80%, `xgb_fb` exceeded plain `xgboost` in sell-through by about 0.270 percentage points, but plain `xgboost` mean revenue was 40,622 report units higher and mean time was 97.9 seconds lower. This is a small revenue difference, not evidence of a reliable advantage. The model choice depends on whether the priority is manager sell-through, system-wide simulator revenue, or evaluation cost.

## Limitations and interpretation boundaries

1. **Simulated responses, not observed HTTP outcomes.** The `200` and `204` response labels are generated by the benchmark's auction simulator for a hidden synthetic manager. The results do not measure live network responses or an external manager's actual behavior.
2. **Synthetic campaign setup and internal units.** Manager and house campaigns, constraints, and manager price are benchmark inputs. Total revenue is the sum of manager and house-campaign revenue in simulator report units. Although a manager price of 150 is present in the saved configuration, no currency unit or validated real-world revenue mapping is established here.
3. **One sampled traffic period.** The prepared source covers 1-7 October 2026, with model training on days 0:4 and evaluation on days 5:7. The test includes two days, and both it and the open-training log are shared across seeds. The user sample is approximately 5.83% of the prepared user population. Results do not establish performance on other dates, traffic mixes, devices, or campaign configurations.
4. **Seed variation is not independent-period uncertainty.** Three seeds capture only a narrow slice of run variability. Sample SD is not a confidence interval, and no inferential test or claim of statistical significance is made.
5. **Quota and policy differences.** Realized sent shares vary slightly around target quota. Random routing independently samples submissions, while model policies include thresholding, quota correction, and epsilon exploration. Same seed does not create identical per-request treatment, so observed differences describe whole-policy outcomes rather than a fully request-matched causal effect.
6. **`xgb_user` temporal caveat.** The source comparison notes that during initial threshold calculation, training-sample and test-stream time coordinates differ. Some initial sample rows can therefore incorporate pool requests from later in the current test hour. Treat `*_user` results as subject to this initial-threshold timing caveat, not as a clean test of strictly sequential online routing.
7. **Timing is environment-specific.** Full time is simulation/evaluation runtime, not per-request latency or service throughput. It excludes common imports and initial data loading. Hardware details for the selected CPU series are not recorded in the cited configuration and are not asserted here.
8. **Not a probability-model benchmark.** This report evaluates routing outcomes, not fixed-sample calibration or classification metrics such as accuracy, log loss, or ROC AUC. Sell-through is not classifier accuracy.

## Related experiment inventory, not pooled

The repository contains other completed but distinct work. GPU routing runs are recorded separately in `gpu_seeds_43_45_q60_q80`; that report identifies an NVIDIA RTX 2060 SUPER, but uses XGBoost 2.0.3 rather than 3.4.1 in the CPU series. The version mismatch confounds a direct attribution of time or quality changes to hardware alone, so GPU measurements are not combined with this CPU summary. A separate profiling run uses seed 42 and a 50% quota with `cProfile`; its timing has different quota and profiler overhead. XGBoost parameter/performance optimization experiments evaluate fit and prediction settings using offline metrics and different protocols. They are not pooled with closed-routing outcomes here.

## Reproducibility and provenance

The claims in this note are grounded in saved per-evaluation results, experiment configurations, execution logs, and model-feature documentation. The summary statistics and paired contrasts were recalculated from the saved model and random-control results.

The saved configuration records seeds, quotas, policy list, split, training-row count, sample fraction, epsilon, open seed, and library/Python versions. The runner source documents how the historical evaluations were performed. Reproducing the run requires access to the prepared traffic, open-run training and pool logs, manager and house campaign definitions, and a compatible environment. These inputs are local data and are not supplied as a portable public dataset with this report.

The recorded evidence does not fully specify hardware or capture every dependency and operating-system detail, so byte-for-byte or timing reproduction cannot be promised. No portable launch command is prescribed because the historical runners depend on local data and configuration paths. This report contains no new experiment results.
