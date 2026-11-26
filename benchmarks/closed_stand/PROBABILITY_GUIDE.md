## Guide: interpreting probability quality

**Quick review.** Start with `sellout_over_time.png`. Each line represents an algorithm.
The X axis shows the test period in Moscow time. The upper panel shows sellout:
the fraction of 200 responses among the requests ranked highest within each hour.
All algorithms use the same quota (80% by default). A higher line means better
selection during that hour. The lower panel shows Lift: selected sellout divided
by the fraction of 200 responses across the entire hour. The dashed `constant_train`
line represents expected random selection. At a tie on the quota boundary, the
expected outcome of random selection is used; responses never affect ranking.
Empty hours remain gaps. Exact counts and values are stored in JSON under
`time_series` and `algorithms.<name>.selection_over_time`. Lift is undefined when
there are no sales.

Each hour selects `ceil(q * N_hour)` requests from fixed, recorded responses.
Seller budgets and frequencies are not recalculated for each algorithm. These
curves describe retrospective selection rather than independent live routing.
Uncertainty intervals are not calculated for hourly curves. ST@q in the summary
uses one selection across the entire test and can differ from the chart average.
Regional slices are omitted from the report. Original features remain in local
Parquet files and campaign inputs for replay; published report labels are pseudonyms.

**Task.** For each request, the model returns `p = P(status 200)`, between 0 and 1.
A prediction of 0.7 means an expected 70% sale rate in similar situations.
The observed outcome `y` is 1 for status 200 and 0 for status 204. In historical
mode this predicts a status; treating 200 as a commercial impression requires
confirmation of the log's meaning. One rejection at p=0.9 does not establish a
model error: rejections should occur in about 10% of such cases. Evaluate many
requests together.

**Train / test / baseline.** Models train on earlier days and are evaluated on
later days. The baseline assigns every request the fraction of 200 responses in
train; it does not know the future sale rate. Models within a mode share the same
requests. Outcomes differ between modes, so their error magnitudes cannot directly
determine a winner across modes.

| Metric | Calculation | Interpretation |
|---|---|---|
| n | Number of test requests | Fewer observations make results less stable |
| Actual / Predicted | Mean y / mean p | Observed sale rate / mean prediction |
| Brier ↓ | mean((p−y)²), range 0…1 | Lower is better. Random outcomes produce nonzero error even with correct probabilities |
| Logloss ↓ | −mean(y·ln(p)+(1−y)·ln(1−p)) | Lower is better; confidently wrong predictions receive a large penalty. Uses natural logarithms; only this calculation clips p to [10⁻¹⁵,1−10⁻¹⁵] to avoid ln(0) |
| Brier Skill ↑ | 1−Brier/Brier_baseline on the same test | 0 matches baseline; 0.2 means 20% less error; negative is worse. Undefined if baseline error is zero |
| Bias, pp | 100·(mean(p)−mean(y)) | +10 pp means average overprediction by 10 percentage points; opposite errors can cancel |
| ECE, pp ↓ | 100·Σ(n_b/N)·abs(mean(p_b)−mean(y_b)) | Mean calibration error across probability bins |
| RMSCE, pp ↓ | 100·sqrt(Σ(n_b/N)·(mean(p_b)−mean(y_b))²) | Calibration error with greater weight on large deviations |
| ROC-AUC ↑ | Fraction of 200/204 pairs where 200 ranks higher; ties count as 0.5 | 1 is perfect ranking; 0.5 is random. Undefined for a single class |
| AP ↑ | Σ increase in recall · precision as the threshold decreases | Average Precision measures concentration of sales near the top. Tied scores enter together. Compare against the test sale rate; undefined without sales |
| Sell-through@q ↑ | Sales among the top q fraction / number selected | Quality of traffic selection at the given quota; q=0.8 selects the best 80% |
| Lift@q ↑ | Sell-through@q / overall test sale rate | 1 matches the average; 1.1 means a 10% relative increase, not 10 percentage points. Undefined without sales |

**Why several metrics?** Brier and Logloss assess overall probability quality,
including calibration and discrimination. ECE and RMSCE compare predictions with
observed frequencies. AUC and AP assess ranking rather than the numerical accuracy
of p. Predicting the correct overall rate for everyone can be well calibrated yet
useless for selection. Accuracy/F1 at a 0.5 threshold are secondary here.

**Charts and tables.** In the calibration chart, X is the bin's mean prediction
and Y is its actual fraction of 200 responses. The diagonal indicates agreement;
a point below it indicates overprediction. Equal probability bins are used
(10 by default), with 1 included in the final bin. Empty bins are omitted.
ECE/RMSCE depend on binning and are noisy with small samples; use identical bins
when comparing models. The histogram shows request counts per bin. The selection
curve shows sale rates at different quotas. Each quota selects `ceil(q * N)`
requests; boundary ties use expected random selection without consulting outcomes.

**Example.** Predicting 70% for everyone when 60% sell gives Bias=+10 pp and
ECE=RMSCE=10 pp. A rejection at p=0.9 contributes 0.81 to Brier and approximately
2.303 to Logloss. Brier=0.1 does not mean a 10% probability error or 90% accuracy.

**Uncertainty.** The 95% intervals for Brier, Logloss, Bias and calibration points
use a user bootstrap: sample whole users with replacement, retaining all their
test requests. This accounts for dependence within a user, but not shared time
drift or dependence between users. Intervals describe this test period, not a
guarantee for next week. Other metrics have no intervals; intervals are undefined
for groups containing one user. Compare models on shared requests. Overlapping
individual intervals are not themselves a statistical test.

**Protocol and limitations.** `hier_beta`, `hier_user` and `rule_trie` train on
train, then receive a completed hour's responses only after predicting that entire
hour, as in the main stand. New responses are unavailable within the hour.
Reconstruction models are static; the FSM sees each response only after predicting
that request. Baseline remains fixed. Models share one observed history rather
than seeing outcomes from different routers. The history slice counts the user's
previous observed requests that day; activity outside the sample is unknown.
Zero feature codes represent missing values.

Simulator mode combines real requests with synthetic Seller responses. Historical
mode retains only original 200/204 responses within the configured pool; other
codes are counted and excluded. It does not recover failure causes, routing to a
specific manager or missing outcomes. Previous routing policies may have selected
the logged traffic. A good historical status forecast does not establish higher
sales under a new policy, because budgets and frequencies can change. That requires
a separate simulation or live experiment.

Metric references: [calibration and probabilistic losses](https://scikit-learn.org/stable/modules/calibration),
[ROC-AUC](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html),
[Average Precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).
