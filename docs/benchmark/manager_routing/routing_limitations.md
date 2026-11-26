# Analysis of `rule_trie` and directions of improvement

The document relates to the current `closed_stand` simulation and the results retained in `recent_one`, not the real manager. Objective: When sending approximately 80% of a permitted no-mobile_device pool, you get more 200 responses than randomly sending the same share.

## What the last run showed

In [report](runs/recent_one/closed_report_20261120_1424.md) learning 2 313 097 randomly sent requests for days 0–3, parameterization `m` — day 4, test — days 5–6. In the table below, the test data; Distribution of the share of sending less 0,3 p.p., numerical 200 However, it is not at all the same number of shipments.

| Politics | Sent / pool | 200 / shipped | 200 | Total model revenue |
|---|---:|---:|---:|---:|
| random | 80,01% | 50,70% | 657 593 | 368 812 040 |
| hier_beta | 79,96% | 55,92% | 724 839 | 355 487 850 |
| hier_user | 80,11% | 56,42% | 732 713 | 365 757 950 |
| rule_trie | 79,86% | 55,25% | 715 380 | 357 577 915 |

`rule_trie` improves sell-through at **4,55 p.p.** relatively random, but is inferior to `hier_beta` at **0,67 p.p.** and `hier_user` at **1,17 p.p.** At the same time, the total model revenue of all three is lower than random: optimization of the probability of a manager's response can give him requests that are useful to our campaigns. Revenue numbers are given in booth units; the choice of the best policy depends on the business goal.

In validation, `rule_trie` showed 58,79% at all three values of `m` with two digits accuracy. This doesn't prove that anti-aliasing is useless, but it shows that in this range and on this data, it has almost no effect on the outcome. Raising `m` blindly is not the main candidate for improvement.

The result of one seed and one synthetic set of campaigns does not establish sustainable superiority; the comparison below is an analysis of implementation and hypotheses that have yet to be tested.

## How the current version works

[`RuleTrie`](../../../benchmarks/closed_stand/predictors.py) Stores nine separate sets of statistics: Each child and each child will have a child × device, device × region, device × category, device × channel. Technically, these are sorted arrays of packaged prefix and counter keys, not a machine, campaign-building.

For each path, a smoothed assessment is considered 200/Posted with parental prefix. Final `score` — **simple average of nine grades**. With a new observation, all counters are updated; `ts` and `user` model does not. [`ThresholdQuota`](../../../benchmarks/closed_stand/routers.py) Sends requests with high scores, quota-settling, Adding a random study and updating the model after an hour interval.

It's a model of predicting the response, not restoring real companies: 200/204 doesn't reveal the winner, the targeting, the budgets, or the reason for the failure. Different sets of campaigns can generate the same answers.

## Major weaknesses

### 1. Equal averaging blurs the useful signal.

Each of the nine paths has the same effect, even if he’s weak, rarer. In the report, strong segments meet simultaneously `Device=ANDROID_TV_A`, `Device=ANDROID_TV_A, Category=<none>` and `Child=<none>, Device=ANDROID_TV_A`. They’re very intersecting; Multiple related assessments can actually take into account the same feature many times over. Similarly, the strong signal of the individual channel is averaged with the estimates of the other paths.

This is an assumption about the mechanism of loss of quality, not an established cause of difference: the segment report itself is built ** after the test **, includes online updates on the traffic chosen by the policy, and describes the estimates of individual paths, rather than the contribution of each path to the final decision.

### 2 Limited set of combinations

The maximum depth is two features. `hier_beta` additionally takes into account more detailed combinations of device, region, content type and child. `rule_trie` can't express, for example, dependence on a simultaneously given device, region and channel. And even some pairs - for example, region × channel - are missing. Statistics of rare interactions are easily retrained, so adding all combinations without restrictions can worsen the result.

### 3 : No user or time information

On the same set of tags, `rule_trie` gives the same score regardless of how many times the user has already been sent to the manager and how long ago the last response was. In the simulator, user frequencies, minimum intervals, campaign limits and flutes are used. `hier_user` takes into account part of the user history. The difference between models is compatible with the benefits of these features, but does not measure it separately: the models differ in other details.

Boron statistics accumulate without fading. If the flute is out or the budget is exhausted, the old 200 continues to influence the forecast, and other models have their own adaptation limitations; they need to be compared in the same scenario.

### 4 .We only observe the requests sent.

After switching to selective routing, tags come only on sent requests. Boron statistics gradually reflect a mixture of the original random sample and the policy sample itself. Rare segments may receive little feedback; the likelihood of sending them depends on the current estimate. `ε=0,02` intelligence helps, but does not eliminate all displacement problems. Also, the initial threshold is built on sent training requests, not on all pool requests; subsequent reference samples are taken from the entire pool.

### 5 . . . There is no clear optimization of solutions near the quota boundary.

With a 80% quota, policy mainly decides which roughly 20% pool to keep, so ranking queries near a threshold may be more important than improving forecasts in very good and very bad segments. The current model averages estimates without a separate setting for this boundary. It is important to check the quota compliance by day and interval: the raw number of 200 at different fractions of sending can be misleading.

### 6: Rules are hard to interpret as campaigns

Current "rules" are frequently occurring segments that deviate from 200's total share, rather than a set of restored advertisers. Their intersections, competition, lack of feature, and time constraints can create similar effects. The `top_rules` list is sorted by `|lift| × sqrt(n)`, so often shows large, partially duplicated segments; this is not an assessment of causal contribution.

### 7 Data and Computation Limitations

`<none>` and `<other>` are real codes for missing and aggregated rare values. They can't be automatically treated as normal independent features: for example, the lack of a category is related to the type of content and can duplicate other signals. Packaging uses 9 bits per category and assumes less than 512 values in each dictionary. Now prepared dictionaries fit into this limitation, but changing the source requires verification.

More paths and states means more memory and work on each `score` update and call, including recalculating the router reference sample. Check quality along with speed and memory; a compact structure alone does not guarantee a better forecast.

## Improvement options

### A. To learn how to combine path assessments - first candidate

Instead of an equal average, use a small, regulated model, such as logistic regression over path estimates, their support, and no-observation indicators. You can train weights from predictions from earlier data with a chronological out-of-fold or prequential approach: you can't train the second layer on estimates calculated using the same line's response. A simple leave-one-out on the sheet is not enough if the parental score also contains this label.

This will allow the model to reduce the weight of duplicate and marginal paths: check: gain to the original `rule_trie`, calibration and quality near the threshold; use regularization and rollback to the baseline estimate with little support; consider non-negative weights or other restrictions only as separate options, and not consider them automatically correct.

### B. Adaptive interactions and sparse branches

Add pairs and triples, improve the prognosis in the earlier training window: Check out the region first × channel, region × category and device × region × channel/category. Creating Branches with Minimum Support, smooth over to a more common parent, limit the depth and number of nodes, Remove the ineffective according to the results of a separate inspection.

You can use a compact boron by category or combine common subtrees into DAG/memory-storage. Selection of order for small categories → It saves space in some distributions, It does not in itself guarantee quality or minimum size. Individual paths or masks are also needed for rules, rootless. Compare memory and speed with current packed arrays before complication of structure.

### C. Add custom features over boron

Compare with `hier_user`: on top of the boron scores, use the same features of the user's send and response history, the time from the previous send and the user's correction. The model should build the features strictly from the state of the **to** next answer. Check the effect as a separate ablation: `rule_trie` → `rule_trie + user`, without changing the router and other parameters.

Now, responses are transmitted to models after the hour-long buck; within an hour, the user's state is not updated. This is a limitation of both stateful variants and a potentially important source of error for frequencies. More frequent buckets or sequential updates should be measured separately, taking into account the cost and realistic delay of response.

### D. Account for change over time

Check the exponential attenuation of counters, Sliding windows or a combination of long-term and recent assessment; add on/The day as signs and measures the effect. Comparison over consecutive periods, appearance-scenario/End of Flights and Exhaustion of Plans. Memory that is too short will impair scores of rare segments, Therefore, periods of attenuation should be selected for validation.

### E. Correct the Selective Traffic Assessment

Logicate for each decision the probability of sending and the sign of a random study. Start with estimates trained on a random subset and compare with the use of all shipments; then check the weighting by the reverse probability of sending with a restriction of large weights. Requires non-zero probability of selection and correct accounting of actual policies, including the threshold, quota and allowed pool. This reduces some types of bias, but does not restore counterfactual responses automatically and can increase variance.

### F. Threshold ranking and quota

Check the quality of sorting on a random delayed sample: how well the model separates the lower ~20% pool, along with log loss, Brier score and calibration. Compare the number 200 and sell-through ** at the closest actual quota**; additionally measure quota errors by day and hour. If necessary, investigate the selection of threshold, quota and `ε`, without selecting them on the final test.

### G. Explicit Campaign Hypotheses – Separate Research Stage

Form a limited list of interpreted rules with multiple tags, support, and uncertainty; allow intersections. You can compare a sparse logistic model to a rule-setting pattern or a latent model to a time state. Verify prospective targeting of known campaigns only as a simulator diagnostic, never pass hidden campaigns to a predictor. Accurate recovery of campaigns, budgets, and winners from binary responses is generally unidentifiable.

## The order of experiments

1. **Secret baseline.**Save configuration, seed, q, ε, campaign period and scenario; compare multiple seeds on the same sample and multiple non-intersecting time tests. All politicians should see the same queries and have their own independent simulator states. Show scatter, not just better run.
2. **Diagnostics of predictions.** On a random sample not used in model training and parameter selection, calibrate and error by device, content type, region, user history and proximity to the threshold. Separately measure the contribution of each path and their correlations. Do not use test `top_rules` to select options.
3. **One hypothesis is:** path weights (A), user history (C), then interactions (B) and time (D). First ablations individually, then combinations. For the second layer, use chronological out-of-fold estimates; hyperparameters to choose only for validation.
4. **Test on other managers:** Repeat on multiple synthetic sets with different targeting, frequency, overlap, and flute structure, as well as on different source baseline. One scenario specifically calibrated around 50% should not define the model architecture.
5. **Report:** sell-through, 200 / pool 200 quota-free, intervals of uncertainty seed/period, revenue-sharing, loss of our campaigns, memory, duration of training and processing. Purpose of the first experiments — sustainably `rule_trie` comparable; shifting-Revenue targets require separate discussion.

For an independent historical assessment of real-world answers, you need to prepare a correct set with a known sending policy and non-overlapping periods. The stand is now simulating the manager's answers; the original statuses of the new parquet do not by themselves give an answer to what would have happened with another routing. In addition, the calculation of campaign plans in the current booth uses tag frequencies for the entire prepared week, including future days. For a strict temporal experiment, you need to count these frequencies only in the period available at the time of setting.
