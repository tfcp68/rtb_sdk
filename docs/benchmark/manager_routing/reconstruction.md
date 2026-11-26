# Control experiments reconstruction

Prepared source: `prepared_20261012`; days `0:4`, split-day=3, sample=0.002.
q=0.8 , seed routing=42 , seed generation=42 , 8 campaigns.
89 464 training and 29 998 test queries. Targeting is the same in two scenarios.
All eight campaigns have been shown in train and test.
52.89%; individual coverage from 2.81% to 17.15%.
Exclusive area outside of other targeting.

Algorithms are trained by traits and 200/204; hidden composition is used in estimation.
Comparison quality is a greedy mutually unambiguous assignment with a weighted IoU ≥ 0.5.
This is a matching of areas on the observed test traffic, not an accurate recovery of JSON.

| Script | Method | Brier ↓ | Logloss ↓ | Campaigns found | Precision campaign | IoU union |
|---|---|---:|---:|---:|---:|---:|
| targeting | single_feature | 0.03201 | 0.12156 | 5/8 | 0.500 | 0.933 |
| targeting | dnf_beam | 0.03201 | 0.12157 | 3/8 | 0.750 | 0.933 |
| targeting | dnf_cooldown_fsm | 0.03201 | 0.12157 | 3/8 | 0.750 | 0.933 |
| targeting | dnf_validated | 0.03201 | 0.12157 | 3/8 | 0.750 | 0.933 |
| targeting | motif_noisy_or | 0.00096 | 0.00446 | 3/8 | 0.333 | 0.984 |
| targeting | constant train | 0.24882 | 0.69079 | — | — | — |
| dynamic | single_feature | 0.13145 | 0.43270 | 0/8 | 0.000 | 0.000 |
| dynamic | dnf_beam | 0.13145 | 0.43270 | 0/8 | 0.000 | 0.000 |
| dynamic | dnf_cooldown_fsm | 0.13145 | 0.43270 | 0/8 | 0.000 | 0.000 |
| dynamic | dnf_validated | 0.11260 | 0.37359 | 3/8 | 0.375 | 0.409 |
| dynamic | motif_noisy_or | 0.09146 | 0.28614 | 5/8 | 0.455 | 0.911 |
| dynamic | constant train | 0.13145 | 0.43270 | — | — | — |

In `targeting`, motif_noisy_or significantly improves response prognosis and overall targeting area.
But the number of individual campaigns is inferior to single_feature: several campaigns with a similar
Behavior combines, others split into motives, so low Brier can't be allowed.
This is evidence of the restoration of all campaigns.

In `dynamic`, the original DNF finds no rules: a fixed 2 penalty requires too much.
high-level 200. Selection of a fine on the inner tail train eliminate part of the problem.
Motives with EM recover 5/8 campaign areas with less prediction error.

These are two scenarios with one seed, rather than evaluating sustainability across multiple independents.
Generator parameters and a motif_noisy_or penalty were not matched by these test responses.
Training time/Forecast of each method is maintained in JSON.

Full reports with real targeting and predictions:

- [targeting](runs/reconstruction/diverse_targeting_v2_seed42/report.md)
- [dynamic](runs/reconstruction/diverse_dynamic_v2_seed42/report.md)

Repetition (you need to select new names):

```bash
python benchmarks/closed_stand/benchmark_reconstruction.py --name diverse_targeting_repeat --sample 0.002
python benchmarks/closed_stand/benchmark_reconstruction.py --name diverse_dynamic_repeat --sample 0.002 --campaign-scenario dynamic
python -m pytest tests/closed_stand -q
```

Checks: 21 test passed, including restrictions/reproducibility,
using only train days, noisy intersecting motifs with lists of values,
Punishment and a full run with separation of observations and hidden truth.
