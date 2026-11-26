# Incoming traffic and routing bounds

[All benchmark results](../README.md) · [EDA implementation](../../../benchmarks/manager_eda/)

| Study | What was checked | What it shows |
| --- | --- | --- |
| [EDA findings](analysis/eda_findings.md) · [full report](reports/eda_report.md) | Device pool composition, hourly and weekly profiles, tag coverage and user repetition on seven days of incoming requests. | About 145 million valid requests; the configured TV pool is 61.9%. Traffic composition and seasonality support modeling, but this source has no manager response codes. |
| [Tag-dependency findings](analysis/relations_findings.md) · [full report](reports/relations_report.md) | Dependencies between device, time, region, channel and content categories. | Features are dependent; category and channel describe different content types. Independent marginals alone lose some targeting structure. |
| [Oracle bounds](analysis/oracle.md) · [table](analysis/oracle_table.csv) · [plot](analysis/figs/oracle_bounds.png) | Selection gains under modeled heterogeneity of request success probabilities. | Sending the whole pool leaves no selection gain; smaller quotas and more heterogeneous success probabilities raise the theoretical ceiling. These are modeled bounds, not observed response rates. |
| [Manager strategy](analysis/strategy.md) | How a routing model could use incoming traffic and later response feedback. | A design and evaluation plan informed by the EDA, rather than a measured production effect. |

The full EDA reports own the [plots](reports/figs/) and [CSV tables](reports/tables/).
Prepared source data and intermediate aggregation caches remain local and ignored.
