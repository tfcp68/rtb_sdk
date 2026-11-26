# Closed-manager routing experiments

[All benchmark results](../README.md) · [Stand and CLI](../../../benchmarks/closed_stand/README.md)

The routing stand observes request features and manager 200/204 feedback. It
compares policies at a target fraction of the eligible pool and reports manager
sell-through, house-campaign delivery and total simulated revenue. Most runs
use a synthetic manager on prepared request traffic; historical probability
evaluation is identified separately below.

## Main findings

| Study | Question and saved finding |
| --- | --- |
| [Three-seed XGBoost/CatBoost study](tree_models.md) · [run tables](runs/seeds_43_45_q60_q80/report.md) | Do response-history features help at 60%/80% quotas? `xgb_fb` raises mean simulated sell-through over matched random routing by 13.923/5.653 percentage points. Total-revenue gains are much smaller; plain XGBoost has slightly higher mean total revenue at 80%. Three seeds on one prepared period do not establish production superiority. |
| [Hierarchical and RuleTrie analysis](routing_limitations.md) · [full evaluation](runs/recent_one/closed_report_20261120_1424.md) | Does better manager selection improve the whole system? RuleTrie improves manager sell-through in the analyzed run, but total model revenue remains below random. This motivates evaluating the value of retained house traffic, not only P(200). |
| [Reconstruction controls](reconstruction.md) | Can hidden campaign structure be recovered? Motif models improve response prediction and union-of-targeting recovery; individual campaign recovery remains incomplete, especially with dynamic limits. |

## Probability quality

[Method and metric definitions](../../../benchmarks/closed_stand/PROBABILITY_GUIDE.md).
These are retrospective predictions and top-quota rankings on fixed outcomes;
they do not replay a different stateful seller separately for each policy.

| Mode | Report | Saved observation |
| --- | --- | --- |
| Historical responses | [Report](runs/probability/probability_large_02_report_v2/historical/report.md) | `hier_beta` has the lowest Brier score (0.13984). `hier_user` reaches 49.41% observed 200 among the top 80%, versus 40.15% in the full test. The business meaning of the historical status code needs separate confirmation. |
| Synthetic seller | [Report](runs/probability/probability_large_02_report_v2/simulator/report.md) | `hier_beta` has the lowest Brier score (0.16120). `hier_user` reaches 53.75% observed 200 among the top 80%, versus 43.73% in the full test. These are simulated outcomes. |

The [combined entry](runs/probability/probability_large_02_report_v2/report.md)
links both modes; adjacent JSON and plots retain their detailed diagnostics.

## Reconstruction runs

| Run | What was checked |
| --- | --- |
| [Diverse targeting, seed 42](runs/reconstruction/diverse_targeting_v2_seed42/report.md) | Eight overlapping campaigns without dynamic frequency effects. Motif models recover the combined targeting area well, but do not identify all campaigns separately. |
| [Diverse dynamic, seed 42](runs/reconstruction/diverse_dynamic_v2_seed42/report.md) | The same targeting with dynamic limits and response state. Motif models recover 5/8 campaigns in the summary's matching evaluation; basic DNF methods struggle. |
| [Grouped reconstruction](runs/reconstruction/reconstruction_grouped_20261103/report.md) | Earlier control comparing response models and recovered targeting on the saved grouped setup. |
| [Week reconstruction](runs/reconstruction/reconstruction_week/report.md) | Larger replay: 620,276 training and 487,867 test observations. It checks response prediction and targeting recovery at a larger sample size. |

## Earlier runs and smoke checks

These are development checkpoints with differing samples, splits and campaign
calibrations. They establish that particular configurations run and expose
policy trade-offs; they are not independent evidence of a universal ranking.
Each folder also retains the open-run report and configuration when available.

| Run | Purpose | Closed report |
| --- | --- | --- |
| `demo` | Initial open/train/validation/test routing comparison. | [October 26](runs/demo/closed_report_20261026_1317.md) |
| `new_source_smoke` | Short-split check after changing the prepared traffic source. | [October 29](runs/new_source_smoke/closed_report_20261029_1954.md) |
| `new_week` | Week-based comparison with validation and held-out test days. | [October 29](runs/new_week/closed_report_20261029_2001.md) |
| `calibrated_smoke` | Compare routing against a calibrated synthetic manager. | [October 29](runs/calibrated_smoke/closed_report_20261029_2011.md) |
| `baseline50_check` | Baseline calibration check around the intended manager sell-through setup. | [October 29](runs/baseline50_check/closed_report_20261029_2019.md) |
| `frequency_smoke` | Compare policies with calibrated frequency constraints. | [October 29](runs/frequency_smoke/closed_report_20261029_2106.md) |
| `trie_smoke` | Small split for hierarchical/RuleTrie development checks. | [First run](runs/trie_smoke/closed_report_20261029_1918.md) · [follow-up](runs/trie_smoke/closed_report_20261029_2111.md) |
| `recent_one` | Larger hierarchical/user-history/RuleTrie comparison used by the limitations analysis. | [November 20](runs/recent_one/closed_report_20261120_1424.md) |
