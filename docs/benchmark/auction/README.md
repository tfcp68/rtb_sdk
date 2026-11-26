# Auction comparisons

[All benchmark results](../README.md) · [Runner instructions](../../../benchmarks/README.md)

## Synthetic auctions

These runs compare classic selection, hybrid scoring, balancer-based allocation
and AdWords A2/A3 on controlled campaign targeting and traffic volumes. They
measure delivered impressions, revenue in simulation units, campaign sellout
and runtime. Their simplified engine uses precise matching and does not apply
per-user frequency limits or minimum intervals; see each report's assumptions.

| Saved run | Role |
| --- | --- |
| [September 6](synthetic/benchmark_20260906_1859.md) | Initial comparative scenario matrix. |
| [September 7, quick](synthetic/benchmark_quick_20260907_0104.md) | Reduced-volume comparison for faster iteration. |
| [September 10](synthetic/benchmark_20260910_0218.md) | Follow-up synthetic allocation comparison. |
| [September 11](synthetic/benchmark_20260911_0413.md) | Additional scenario matrix retained for historical comparison. |
| [October 6](synthetic/benchmark_20261006_1608.md) | Comparison including hybrid strategies and balancer allocation across 3, 10 and 20 campaigns under shortage, balanced supply and excess. |

The comparisons show how traffic supply, targeting overlap and capacity change
which strategy performs well. Use the tables within a run for rankings; the
files are historical configurations rather than a controlled sequence of
improvements.

## Log replay

[Method and CLI](../../../benchmarks/log_benchmark/README.md).
The replay engine adds active dates, sliding campaign and user frequency caps,
minimum intervals and realistic combinations of request tags.

| Saved run | What it shows |
| --- | --- |
| [October 14 summary](log_replay/log_benchmark_20261014_1330_summary.md) | Thirty-day replay with 32 campaigns and three traffic levels. `best_price` leads with shortage; pace-aware methods gain about 0.3% with excess. A2/A3 coincide in this setup and take substantially longer. |
| [October 14 full report](log_replay/log_benchmark_20261014_1330.md) · [JSON](log_replay/log_benchmark_20261014_1330.json) | Per-strategy delivery, revenue, filtering losses, timing and campaign details behind the summary. |
| [Balancer-fix run](log_replay/log_benchmark_balancer_fix.md) · [JSON](log_replay/log_benchmark_balancer_fix.json) | Separate saved replay after the balancer correction; inspect its configuration before comparing it with the earlier run. |

Revenue is a simulator quantity. Replay uses precise matching; fuzzy and
parasitic limits are outside these comparisons.
