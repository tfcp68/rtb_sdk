# Benchmark and research results

Start here to find an experiment by the question it answers. Reports, JSON
results, tables, plots and companion research notebooks are grouped below.
Runnable auction and routing benchmarks remain in [benchmarks/](../../benchmarks/README.md).

| Question | What was checked | What the saved results show | Reports |
| --- | --- | --- | --- |
| Which auction strategy works under scarce or excess traffic? | Synthetic campaigns and request streams; classic strategies, hybrid scoring, balancer allocation and AdWords A2/A3. | Results depend on targeting, campaign capacity and traffic supply. These runs isolate allocation behavior; they do not apply the full production filter chain. | [Synthetic auction runs](auction/README.md#synthetic-auctions) |
| Does the result change with realistic request patterns and frequency limits? | Replay of prepared traffic with active dates, campaign limits, per-user frequency limits and minimum intervals. | In the October 14 run, price selection leads under shortage; pace-aware strategies narrowly lead with excess traffic. A2/A3 produce identical outcomes in that configuration and take longer. | [Log replay comparison](auction/README.md#log-replay) |
| Can selective routing improve a closed manager's sell-through? | Random routing versus hierarchical and tree models at a controlled pool quota. | Higher manager sell-through can reduce revenue from house campaigns. The three-seed study separates response-history models from tag-only models and reports both sell-through and total simulated revenue. | [Routing experiments](manager_routing/README.md) |
| Can a response predictor recover hidden campaigns? | Synthetic sellers; only request features and 200/204 feedback are visible to reconstruction methods. | Motif models improve response prediction and targeting-union recovery, but low prediction error does not establish recovery of every campaign. | [Reconstruction controls](manager_routing/reconstruction.md) |
| Are predicted probabilities calibrated and useful for ranking? | Brier score, log loss, calibration and top-quota selection, separately on historical responses and a simulator. | Hierarchical models improve the saved diagnostics; probability accuracy, calibration and ranking have different winners. Retrospective ranking is not a live routing experiment. | [Probability evaluation](manager_routing/README.md#probability-quality) |
| What does the incoming manager traffic look like? | Device mix, seasonality, users, tag coverage and tag dependencies; theoretical routing ceilings. | The selected TV pool is about 61.9% of valid traffic. The EDA source lacks manager response labels, so it cannot establish sales probability. Oracle gains are modeled bounds. | [Traffic EDA and oracle](manager_traffic/README.md) |
| Which forecasting models and horizons deserve further work? | Rolling-origin comparisons of the SDK Prophet baseline with statistical, neural and tree-based alternatives. | Several alternatives outperform the baseline on the saved aggregate accuracy measure; their ranking and training cost vary by series and forecast horizon. | [Predictor comparison](predictor/README.md) |
| How well do bid-landscape models estimate market prices and win probability? | Cui (2011) and Wang (2016) prototypes on synthetic data and closed-stand logs, with full and censored observations. | The methods address different observation models. | [Bid forecast benchmark](bid_forecast/README.md) |
| Do reach and user-frequency effects justify changing the balancer? | Weekly reach-versus-volume comparisons, profile backtesting, frequency conversion and cumulative-frequency corrections. | Reach decomposition is mostly within the measured noise scale; frequency conversion is a correctness fix. Cumulative-frequency gains concentrate on tight user caps. | [Frequency research](reach_frequency/README.md) |

## Reading order

For auction selection, start with the [log replay summary](auction/log_replay/log_benchmark_20261014_1330_summary.md),
then compare its assumptions with the [synthetic runs](auction/README.md#synthetic-auctions).
For routing, start with the [three-seed study](manager_routing/tree_models.md)
and the [limitations analysis](manager_routing/routing_limitations.md).
For balancing changes, start with the [frequency research summary](reach_frequency/README.md).

## Artifacts and interpretation

A Markdown report explains a run; the adjacent JSON retains its numerical
results, where available. Plot and table directories belong to their report.
Dates and run identifiers are retained so different historical experiments are
not mistaken for repetitions of the same configuration. The [routing index](manager_routing/README.md)
identifies the small smoke checks separately from the larger evaluations.

These are saved experimental results, not a fresh rerun or a production
performance guarantee. Compare metrics within matching configurations; source
periods, sampling, campaign sets and available response labels differ.
Private source adapters, raw logs, prepared arrays and caches remain excluded
from Git; see [local sources](../local_sources.md).
