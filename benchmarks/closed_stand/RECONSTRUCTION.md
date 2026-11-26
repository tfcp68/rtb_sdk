# Recovery of campaigns from closed spinner responses

Start from the root of the project (with established dependencies SDK):

```bash
python benchmarks/closed_stand/benchmark_reconstruction.py --name reconstruction_small
```

Default: Prepared `prepared_20261012` traffic, **Separately generated
8 campaigns for reconstruction**, days of `0:4`, training up to day of 3, test on day of 3.
Sampling 0.2% users, sending random 80% requests from a pool of devices.
Synthetic companies, requests from prepared project logs.
200/204 answers generate a true `Seller` booth with all its filters.
The user sample saves repeated user requests.

Bigger experiment:

```bash
python benchmarks/closed_stand/benchmark_reconstruction.py \
  --name reconstruction_week --days 0:7 --split-day 4 --sample 0.01 \
  --max-rules 16 --depth 3 --min-support 100 --beam-width 16
```

The name of the run should be new: existing results are not overwritten.
`--manager-ads` allows you to repeat the experiment on another JSON campaign.
`--seed` controls random sending, `--q` controls its share.
`--max-rules` is the same upper limit of hypotheses.

## Targeting Generator for Reconstruction Only

Regular `stand.py`, its JSON and calibrations do not change. Reconstruction by default
Creates its `manager_ads.json` from profile frequencies **only training days**.
Choosing targeting and plan shares does not use future-day `combo_counts`.
Feature dictionaries remain common to the prepared source.
sent requests for the entire period is known to the simulator to scale plans;
Recovery algorithms don't get the plans or the statistics.

Within the field, values are connected through OR, fields through OR.
The generator alternates the 1/2/3 field, uses up to three values in the field, and discards:

- Campaigns that cover less than 2.5% or more than 20% training pools.
- Targeting pairs with weighted IoU > 0.60 and shared coverage sets > 85%.
- Sets where any campaign has less than 10% of its own coverage
  This protects against complete cover-up by competing targeting.

All restrictions are checked on the observed train traffic.
Impressions on test, structural identifiability or field independence
The generator gives an error in impossible restrictions, a universal campaign is not created.

`--campaign-seed` (default 42) manages generation independently of `--seed`
Settings: `--campaign-count`, `--campaign-min-coverage`.
`--campaign-max-coverage`, `--campaign-max-iou`, `--campaign-max-union`.
Two modes with the same targeting with the same seed:

- `--campaign-scenario targeting` (default): no frequency restrictions
  The budget is still finite; the goal is to study targeting separately.
- `--campaign-scenario dynamic` : additionally different min_interval, custom
  Daily limits and ad-limit profiles; the goal is to check for noise from campaign availability.

Self-generated and run with existing JSON:

```bash
python benchmarks/closed_stand/generate_reconstruction_campaigns.py \
  --out /tmp/reconstruction_ads.json --train-days 0:3 --campaign-seed 43
python benchmarks/closed_stand/benchmark_reconstruction.py \
  --name reconstruction_custom --manager-ads /tmp/reconstruction_ads.json
# Former management team:
python benchmarks/closed_stand/benchmark_reconstruction.py \
  --name reconstruction_old --manager-ads benchmarks/closed_stand/manager_target50_20261012.json
```

## The algorithms.

The implementation is in [reconstruction.py](reconstruction.py), training
evaluations — in [benchmark_reconstruction.py](benchmark_reconstruction.py).
All methods solve two related problems: construct interpreted areas.
Predict the probability of 200 responding to the next query.
Hypothesis - the alleged area of work of a hidden campaign; the correspondence of one
Hypotheses one advertising account from observations does not follow.

### What data is available to the algorithm

Each row of the log contains the categorical features `x`, time `t`, user.
`u` and the answer `y`: 1 for 200, 0 for 204. The algorithm does not receive the winner ID.
the number of campaigns, their targeting, budgets, prices and restrictions. Time and user
A temporary automaton is needed; static models use signs and answers.

200 means that the seller has been able to select the ad. 204 can mean how
Lack of suitable targeting and temporary inaccessibility of suitable
Campaigns: Exhaustion of volume, frequency limit, or time limit.
Therefore, algorithms look for a statistical relationship of traits to a response, rather than counting.
Every 204 is proof of no campaign.

For static search, the same feature vectors are combined into profiles.
For the `i` profile, `n_i` is the number of requests, `s_i` is the number of 200.
`f_i = n_i − s_i` is the number of 204 . The weight of the profile is equal to the number of original queries:
One profile with a thousand appeals affects learning more than a profile with one.
Aggregation reduces search volume and preserves static model statistics.
For the automaton, the initial sequence of events is additionally reproduced.

### As the rule is presented

A rule is a conjunction of field constraints.

```text
Region ∈ {Moscow, Kazan} And the device = Phone
```

Inside the list of values is OR, between the fields - I. Absent in the rule
The field is free: any of its values, i.e. wildcard, are suitable.
The 0 code in dictionaries means missing value.
Search does not create a field = 0 condition, because Seller cannot target that way.
Wildcard also allows for missing values.

Several rules form DNF - disjunction of conjunctions:

```text
(Region = Moscow and the Device = Phone)
or (Channel = Video)
```

Such a set can be represented by a boron or an automaton on tokens of features.
In the current code, matches are calculated by NumPy Boolean masks; separate boron
Or regular expression doesn't make sense. Categorical comparisons make sense.
fields without converting the request into a line.

### Common Covering Search: `single_feature` and `dnf_beam`

These methods use `RuleReconstructor`. They consistently choose the rules.
which explain a lot of uncoated 200 and capture little of 204.
For each profile, a `r_i` residue is entered: first, `r_i = s_i`.
Candidate score `R` :

```text
gain(R) = Σ r_i − λ × Σ f_i,  profile-wise i, coincidental R.
```

In organic search, `λ = 2` . . Positive responses already explained by the selected ones
The rules no longer win. The negative answers continue to be fined.
each new candidate, including areas of intersection with the previous rules.

One selection step is arranged as follows:

1. "" Search begins with an empty universal rule. It can become one.
   The result is if it satisfies the limitations and wins over the others.
2 . . . to the current candidates is added one equality for the not yet used
   Fields are added in the order of their indices: this excludes repeated
   consideration of the same conjunction in different permutations.
3. Candidates with fewer total observations `--min-support` throw away.
   Support counts all matching queries, including 204 and already covered 200.
4. At each level, expansions are maintained only `--beam-width` candidate
   They generate the next level down to the depth of `--depth`.
   The negative gain of an intermediate candidate does not in itself prohibit it.
   Expansion: A narrower conjunction may be helpful.
5: The best candidates of all depths are selected.
   With equal gain, the rule with fewer fields is preferred.
6. If gain is positive, the rule is saved, and `r_i` in its area is zeroed.
   Then the search for the next rule begins again. Primary gain ≤ 0, absence
   Candidates or achieving `--max-rules` training ends.

It’s a greedy search with a limited beam (beam search): He doesn’t go through everything
It's a set of possible rules that doesn't guarantee global optimum.
Conjunction can be lost if its intermediate conditions do not hit the beam.

For example, candidate A has 80 unexplained 200 and has 20 responses 204:
`gain(A) = 80 − 2 × 20 = 40`. In B - 50 such 200 and 3 responses 204:
`gain(B) = 44`. Selects B, although A covers more positive responses.
After choosing B, the positive responses do not increase the gain of the following.
rules, but all negative answers are still counted.

For the first rule, the positive gain condition is equivalent.
`share 200 > λ / (1 + λ)`. Primary `λ = 2` That’s more 2/3. Next step
The criterion is stricter, since some of the positive answers have already been explained.
Because of this, a campaign with a stable 200 share in 35% may remain invisible.
for a conventional covert search, even with a large number of observations.

`single_feature` limits depth to one: it looks for only one field.
It's a simple point of reference, and it can't express
a separate hypothesis intersection of the region and the device. `dnf_beam` permitting
Conjugation to `--depth` fields and after search combines compliant rules.

### Probability of covering models and consolidation of rules

For the selected rule, `support` and `successes` are saved over **all train**
in his field, including the previously explained positive responses.

```text
p_R = (successes_R + 1) / (support_R + 2).
```

It's the smoothing of Laplace: one conditional success and one failure is added.
So that the score doesn't become exactly 0 or 1 because of the final sample.
For profiles outside the combination of rules, the background is similarly calculated
The probability of `b`. "" If there are no such observations, the formula gives `b = 1/2`.

The maximum `p_R` is selected from the matching rules; if
No matches, `b` returns. "" The background doesn't compete with the odds of matching.
For example, if you have two matches with the scores of 0.7 and 0.8, the result is 0.8.
Thus, the intersection of hypotheses is not treated as an independent work of two campaigns.

For DNF variants, a subsequent combination with the 0.04 threshold is enabled:

- For the next field, the rules are grouped with completely the same others.
  conditions. For example,, `Moscow AND Telephone` and `Kazan AND Telephone` common
  `Device = Phone`.
- Within a group, rules are sorted by probability and broken down into clusters.
  The difference between the maximum and minimum probability of the cluster should not exceed
  0.04. A chain of pairwise probabilities doesn't allow you to exceed that scatter.
- The values of the selected field are combined into a list, support and successes are summed up.
  The probability is recalculated using the same smoothing formula.
  sequentially, without repetition until convergence.

The scope of the unified rules is preserved, but the forecasts within it may change.
It's a heuristic of grouping by train, not a general new probability.
Proof that the rules belong to one campaign.`single_feature`
It's not an association like that.

### `dnf_validated`: Selecting a penalty for 204

`ValidatedRuleReconstructor` retains the same search, smoothing, and combining.
But selects `λ` for the observed level of noise availability:

1. Train is divided in line order: the first 75% is internal learning.
   The last 25% is internal validation. It's the fractions of requests, not the number of days.
2. For everyone `λ` of `0.1, 0.25, 0.5, 1, 2, 4` rules learn again
   Only on the first 75%.
3. The last 25% is Brier, the average `(p − y)²`.
   Error; with exact equality, fewer rules, then more penalties.
4. "" With the fine selected, the model retrains on the entire train.
   Like `selected_negative_penalty` in the report.

Small penalty allows for low-share 200 rules: for example, `λ = 0.25`
The threshold of positive gain in the first step is 20%.
the addition of too broad rules, so the penalty is chosen according to forecasts
Test is not involved in this selection.
Restores the cause of the inaccessibility and does not introduce a time model.

### `dnf_cooldown_fsm`: User status and temporary lockdown

`CooldownReconstructor` trains DNF with the usual 2 penalty and adds to the rules
machine-gun `(user, hypothesis)`. The condition is stored as
`ready_at` is the time from which the hypothesis is again available:

```text
READY   -- observed 200 And this hypothesis is chosen --> BLOCKED until t + cooldown
BLOCKED -- current-time >= ready_at         --> READY
```

For each request, events are processed strictly in the following order:

1. There are all the same rules.
2 . These exclude those that are blocked for this user.
3. You pick the rule with the highest probability.
   The probability becomes the prediction. If all the converging rules are blocked,
   The prediction is `min(b, 0.02)`. If there's no match at all, the prediction is `b`.
4. It's only after the prediction is given that the actual answer is read. If that's 200, it was.
   The available rule is selected, it is blocked only up to `t + cooldown`.
   204's answer doesn't change the state. 200's answer with no available rule, too.
   It doesn't create a blockage: the model doesn't know which hypothesis to attribute it to.

When the rules intersect, assigning 200 to the selected hypothesis is an assumption
The real winner is not revealed to him.
Other hypotheses do not depend on this blockage.

One **common ** interval for all rules is selected from
`0, 30, 120, 300, 900, 3600` seconds. First the rules learn on the first 75%.
For each interval, the machine reproduces the entire train to warm up.
The state is the first part, but Brier counts only on the latter 25%.
With an equal error, a smaller interval is chosen, and then the rules are relearned.
All trains are assigned a selected interval.

For example, at cooldown 120 seconds after 200 at `t = 100`, the selected
The hypothesis is not available to this user `t = 220`. Requested in `t = 150`
Another convergent hypothesis may work; if it is not, the prognosis decreases.
Starting with `t = 220`, the first hypothesis is again available.

In benchmark, the forecast is built by one consecutive reproduction of the train.
and test: train warms up the state, and each test-response affects only
The `predict()` itself starts playing from an empty state.
There is no state between individual calls without `observed` locking.
It's not updated. It's important when you use a class on your own.

It's an automaton that approximates the pause effect after the display.
`min_interval`, daily limits, budget, or multiple different frequency windows.
Even with well-found rules, a single general pause can be bad for you.
campaigns with different restrictions.

### `motif_noisy_or`: Search for motives and latent activations

`MotifReconstructor` uses the same representation of conditions, but a different criterion.
Learning and other ways of combining probabilities.
for free fields and lists of permissible values in limited fields.
A query can be understood as a sequence of fixed position tokens:
Region, device, channel, etc. Positions have a fixed meaning.

For each `k` motif, the probability of `θ_k` activation is estimated, for the background, `b`.
The noisy-OR model assumes that the 200 response occurs when the background is activated.
or at least one concurrent motive:

```text
p(x) = 1 − (1 − b) × ∏ (1 − θ_k),
                         k: motive k coinciding x.
```

A product is the probability that no source has worked.
For example, with `b = 0.02` and two matching motifs with `θ₁ = 0.4`, `θ₂ = 0.5`
The forecast is `1 − 0.98 × 0.6 × 0.5 = 0.706`. versus the maximum.
In covering models, the intersection increases the probability of a response.

Learning alternates between adding a motif and reevaluating all activations.

**1. Initial model.** No rules, the background is equal to the smoothed share of 200 per train.
The same profiles are aggregated into `n_i`, `s_i`, and `f_i`.

**2 .Assessing a new motive.** With the current `p_i` forecast, the candidate changes it.
only in his field:

```text
p'_i = p_i + (1 − p_i) × θ.
Δℓ = Σ [s_i × log(p'_i / p_i) + f_i × log((1 − p'_i) / (1 − p_i))].
```

According to the matching profiles, `θ` is selected, maximizing the logarithmic increase.
plausibility `Δℓ`. The code is used 16 bisectional steps
0 to `1 − 10⁻⁶`: the function is concave, so the search does not require
For logarithms, the current forecast is limited.
Away from 0 and 1.

Difficulty penalty is deducted from the increase:

```text
score = Δℓ − 0.5 × log(max(2, N)) × C,
C = 1 + the total number of listed values in all conditions of the motive.
```

`N` is the number of original train queries, not the number of unique profiles.
The unit in `C` takes into account the activation parameter.
value. For example,, condition `Region ∈ {Moscow, Kazan} And the device = Phone`
It has a `C = 1 + 2 + 1 = 4`. "" This is a BIC-style penalty, applied as a heuristic.
A discrete motif structure, not a guarantee of the correct number of campaigns.

**3 .Initial conjunction search.** Beam search adds one equality each
in the canonical order of the fields and leaves `--beam-width` the best options
Score at each level up to `--depth` .Initial conjunctions pass the threshold
`--min-support` by number of requests. An empty rule is not added to a separate rule.
Motif: The universal source is already represented by the background.

**4 Extension of Value Lists.** The Best Conjunction Found Has Sequential Conjunction
They're looking at its fields. They're trying extra non-zero in the field they're selecting.
value while maintaining the remaining conditions. added value with the highest
Improve the score, then try again while there is improvement.
The penalty for each additional value is already included in the score.
consolidation of DNF by close shares of 200, the expansion assesses the contribution to the current
It's a model that takes into account the motives that already exist, a separate min-support threshold.
Each value added is not here. The fields pass once; the number
The above values are not limited to the `--depth` parameter.

If the final score is positive, the motif is added; otherwise, the search for new motives
The number of additions is limited to `--max-rules`.

**5 . EM: Joint activation assessment.** After motif is added, algorithm
It overestimates the background and all of `θ_k`. "" Hidden variable means whether or not it's activated.
The source is on the request; it is not the mark of the sole winner of the auction.
For a matching source with the observed 200:

```text
E[z_ik | y_i = 1, x_i] = θ_k / p_i.
```

With 204, all activations are zero. In an M-step, the expected number of activations is divided.
The number of requests where the source may have worked:

```text
θ_k(new) = θ_k × Σ(s_i / p_i) / Σ n_i,
                    profiles, coincidental k.
```

The background is updated in the same way, but matches all profiles.
Expected activations of multiple sources at one 200 can be summed up
a number greater than one: noisy-OR allows them to be activated simultaneously.
So EM here doesn't distribute exactly one winner between campaigns.
Parameters are limited to the `[10⁻⁶, 1 − 10⁻⁶]` interval; iterations cease.
When the maximum parameter change is less than `10⁻⁶` or after 200 steps.
The next motif is looking for a relatively updated model.

**6 .Removal of superfluous motives.** After searching for each rule, it is considered
How much will the train-likeness deteriorate when it is removed with the current others?
If the loss is less than the difficulty penalty saved,
You remove the best candidate, you run the EM again, then you run the EM.
It removes the early broad motives whose contribution has become small.
No new motives are found after this stage.

The method does not have a strict requirement for a proportion of 200 above 2/3: is enough improvement.
plausibility regarding the current background and other motives exceeding the penalty
A separate statistical significance test is not performed.
But the motive, which should lower the probability, the model can not express:
Adding a source to the noisy-OR only increases it.

The `probability` report of this method is a latent `θ_k`, not an observable fraction.
200 is the rule area. `support` and `successes` are the raw train counters of the area.
This includes intersections with other motives, and their attitudes are usually different from those of others.
`θ_k`, because the same profiles have backgrounds and other sources.

The idea of repetitive motifs and EM is inspired by the work of Bailey & Elkan.
[MEME, 1994](https://cdn.aaai.org/ISMB/1994/ISMB94-004.pdf). It’s self-contained
Adaptation, not MEME implementation, and not DNA alignment: categorical fields are not allowed
rearrange, delete or compare as nucleotides, activation independence
Noisy-OR is an approximation. Real Seller picks a winner with shared resources.
The method doesn't model its budgets and frequency windows.
They combine the same campaigns, even correctly predicting the answers.

### What Changes Search Parameters

| Parameter | Effect and limitation |
| --- | --- |
| `--max-rules` | The upper limit of the number of added hypotheses, (a) Unknown number of campaigns. After combining or removing the rules, there may be fewer. |
| `--depth` | Maximum number of limited fields in the initial conjunction. Woo `single_feature` always 1; Lists of motive values do not increase depth. |
| `--min-support` | Minimum number of references train-Requests for Candidate in Search of Conjunctions; non-minimum 200. |
| `--beam-width` | Number of continuing candidates at the level. Big beam expands search and increases time, But it doesn’t make it a complete brute force of rules. |

Increased depth allows you to describe more accurate intersections, but does
There's less support for them and more risk of fitting.
Helps cover more areas, but one real campaign can crash
Decreasing min-support allows for rare areas.
estimations of probabilities in which they are less stable.
search; the true number and structure of the campaigns are not specified.

## What persists

In `docs/benchmark/manager_routing/runs/reconstruction/<name>/`:

- `manager_ads.json`: Actual campaign composition and generation, coverage and
  This is the configuration of the simulator, it's not transmitted to the algorithms.
- `observations.parquet`: time, user, signs, status, train affiliation.
  There are no internal winners or campaign parameters.
- `truth_winners.parquet`: line number → real winner index, -1 for 204.
  The indexes correspond to the order of the `truth` in the JSON report.
- `test_predictions.parquet`: Prediction P(200) of each algorithm for each test
  query next to the actual status and the winner's index. `row` refers to
  `observations.parquet` and `truth_winners.parquet`.
- `report.md` : real composition of the manager, a summary table of real targeting
  and immediate hypotheses of all algorithms with IoU, detailed predictions and quality
  You can see campaigns with no immediate hypotheses in the summary table.
  A weak coincidence does not mean that the campaign is back.
- `report.json` : same data, launch parameters, signature prepared
  source, training and evaluation time, response metrics and targeting matching.

Train/test is divided by day. One auction runs continuously throughout the interval:
Volumes, frequencies and user history are not reset at the border.
Static methods don't get test answers. The machine gets the current answer.
query only after the forecast; the condition at the beginning of the test is warmed up by the train history.
Rules, probabilities and intervals are not retrained.

## How to read the result

For predictions 200/204 are considered Brier, logloss, accuracy, accuracy and recall.
(0.5 threshold) and a constant baseline with a 200 share of the train.

Targetings are compared by weighted IoU on profiles sent **test**
Weight - number of profile queries; information about future statuses for construction
No hypotheses are used. For each hypothesis, the nearest campaign is shown.
Separately greedy mutually unambiguous comparison with IoU ≥ 0.5 considers precision
and recall campaigns so that multiple copies of the rule are not counted as multiple
The matching algorithm does not guarantee optimal performance.
The association's IoU measures the recovery of the entire targeting area.

It’s **Observable equivalence on test traffic**, Not structural equality
JSON Targeting: Selective Submissions and Missing Profiles Limit Area
Budget, name, CPM, exact limits and flutes are not estimated from this data.
Several values of one trait can be restored by separate hypotheses.
A heuristic association can also glue together different real campaigns.
When intersecting campaigns, the manager's answers hide the winner; multiple campaigns
The same behavior can be indistinguishable even on an infinite log.
A no-show campaign can be obscured by limits or more expensive competitors.
The report still includes it in the real composition and denominator recall.

## Verification

```bash
python -m pytest tests/closed_stand -q
```

Check the restoration of two known conjunctions, the absence of fictional
rules in the absence of 200, protection of metrics from duplicates, causality of the machine,
Selection of intervals and full run on a small prepared stream with a known
campaign, including the contents of artifacts and the refusal to re-record.

In addition, the reproducibility and limitations of generation, absence are checked.
Read test-days at generation, abandoning universal fallback and recovery
Two noisy intersecting motifs with lists of values on independent responses.

Results of two test runs: [Reconstruction results](../../docs/benchmark/manager_routing/reconstruction.md).
