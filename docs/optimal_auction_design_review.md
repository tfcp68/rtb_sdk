# Optimal construction of the auction: expectation, price, probability and other approaches

Date of source review and verification: **18 November 2026 year-end**.

The review covers classical auction theory and its application to RTB advertising systems. The focus on RTB is based on the purpose of the repository. Each approach is based on the principle, expected outcome and constraints. Formulas and training examples labeled as withdrawal or adaptation are explained by the author of the review, not the results of experiments in the project.

## 1: What exactly needs to be optimized

An “optimal auction” only makes sense after choosing the target and the side of the market.

| Staging | Who decides? | Purpose | Typical solution |
|---|---|---|---|
| Allocation of the request | Platform, campaigner | Expected net income from the request | Expected payment minus costs |
| Purchase of the show | Participant of an external auction, DSP | Expected profit or target actions under the budget | Optimization of the bet and probability of winning |
| Rules of bidding | Salesman, stockholder | Expected revenue from strategic participants | Reserve price, Myersonian |
| Efficiency of distribution | Market organizer | Total value of the resource for participants | Vickrey / VCG |
| Work on the horizon | Platform or advertiser | Income per day/Flying with Limits and Liabilities | Pacing, online matching, dynamic optimization |

Internally selecting a campaign at known fixed prices can be a task of allocating resources without strategic bidding. In this auction, it is necessary to determine **winner, and payment**: Changing payment changes the behavior of participants. The basis of this distinction is set out in [lecture Roughgarden mechanism](https://theory.stanford.edu/~tim/f13/l/l2.pdf).

### Symbols

| The symbol | Value |
|---|---|
| `x` | Context of the request: user, tagging, time, position, history |
| `s` | Current status: budgets, frequency, planner |
| `i` | Candidate: campaign, manager |
| `p_i(x,s)` | Probability of paid success in selecting a candidate |
| `r_i` | Paying the Platform on Success, cash-for-performance |
| `c_i` | Expected cost of solution |
| `v(x)` | Cash value of winnings for the buyer |
| `b` | Buyer’s rate |
| `w(b\mid x)` | Probability of winning an external auction with a bet `b` |
| `R` | Accidental income or profit, depending |

**Don’t mix probabilities:** sale, gain, click and conversion — flux. The probability of an algorithm randomly selecting a campaign is also not the probability of a successful sale.

## 2: Maximizing the Mathematical Expectation of Income

### Principle

For each permissible action, the expected financial result is calculated, then the maximum is selected:

$
i^*(x,s)=\arg\max_{i\in A(x,s)}\mathbb E[R_i\mid x,s].
$

If the success payout is fixed, the failure is zero, and `c_i` already includes the expected costs:

$
S_i=p_i r_i-c_i.
$

If it is permissible to sell nothing, a zero-revenue rejection is added to the set of actions: negative estimates should not force the system to make a loss-making trade.

Price and event independence is not required if `r_i` is a fixed payout or **conditional average payout on success**.

$
\mathbb E[R_i\mid x,s]
=p_i\mathbb E[P_i\mid \mathrm{success},x,s]-\mathbb E[C_i\mid x,s].
$

### Example: Price vs Probability

Training example; the payout is indicated for one successful sale, the cost is zero.

| Candidate | Payment on sale | Probability of sale | Expected income |
|---|---:|---:|---:|
| A | 120 ₽ | 0,30 | 36 ₽ |
| B | 80 ₽ | 0,70 | 56 ₽ |
| C | 60 ₽ | 0,90 | 54 ₽ |

A choice of price only will give A, probabilities — C, income-expected — **B**. Nana 1 000 The same independent expectation requests will be 36 000, 56 000 and 54 000 ₽. Regarding A advantage B in this example — near 55,6%; This is an example of arithmetic, non-prognostication.

### Expected output and boundaries

The method is optimal for one solution with the right conditional expectations and neutrality to risk. The choice of the maximum on each request maximizes the sum of expectations if the decisions do not change the availability and results of future actions.

The method does not automatically take into account the future value of the budget, the obligations of plans and training. The probability error directly turns into a monetary error: at a fixed payout `r`, the `Δp` error gives the `r·Δp` error.

**Ground:** conditional waiting; linkage, Response forecasts and monetary targets are used in [Zhang, Yuan, Wang, KDD 2014](https://wnzhang.net/papers/ortb-kdd.pdf). The Rule of Internal Choice — self-conclusion for the said setting.

## 3 Price and Probability Accounting: eCPM, CPC and CPA

### Principle

All offers are translated into expected money into the same unit, e.g. 1 000 **incoming display features**:

| Payment model | Expected income by 1 000 possibility |
|---|---|
| CPM, pay-per-view | `CPM × P(paid-out)` |
| CPC, click-rate | `1000 × CPC × P(pay-click)` |
| CPA, conversion fee | `1000 × CPA × P(paid-for conversion)` |

If the CTR is given conditionally for display, then:

$
P(\mathrm{click}\mid x,i)
=P(\mathrm{show}\mid x,i)P(\mathrm{click}\mid\mathrm{show},x,i).
$

Similarly, for post-click conversions, `P(conversion | click, show, x, i)` is added. This is a chain rule of probabilities. For non-click conversions, you need a different event model. If the model already gives the probability of the final event to the incoming query, multiplying again by the probability of showing is wrong.

### Expected output

You get a general monetary rating of offers with different payment schemes. With pay-per-view and guaranteed display, the click-through rate is not a multiplier of the platform's direct revenue; it can affect the advertiser's value or quality, which requires a separate goal.

### Restrictions

Commissions should be considered, cancellation, attribution and confirmation delays. «The bid price» The actual payment may vary. Formulas above — adjustment of expectation to payment units; Probability assessment should be checked separately. Seems. [Official Probability Calibration Documentation](https://scikit-learn.org/stable/modules/calibration.html).

## 4 : Optimal bet based on probability of winning

### Principle: First price

If the winner pays his bet and the loss payment is zero, the buyer’s expected profit is:

$
U(b\mid x)=(v(x)-b)w(b\mid x).
$

Here, `v` and `b` should be in the same units. An increase in the bet usually increases the chance of winning, while reducing the profit on winning.

$
(v-b)w'(b)=w(b).
$

This is a derivative of the previous formula; in practice, you can go over the grid of allowable rates.

### Example

With `v = 100 ₽`, variants of `(b, w)` give:

| Bet | Chance of winning | Expected earnings |
|---|---:|---:|
| 40 ₽ | 0,30 | 18 ₽ |
| 60 ₽ | 0,60 | 24 ₽ |
| 80 ₽ | 0,85 | 17 ₽ |

The best of these three bets — 60 ₽. Maximizing `b×w(b)` This would mean an increase in expected **expense**, not profit.

### Expected output and constraints

Lowering your bet relative to your own value, bid shading, can increase profits. You need to evaluate the winning curve in context; losing usually only tells you that the winning threshold was higher than the bet. With budget constraints, optimization changes to the task of the entire period.

**Source on the rules of the first price and utility: ** [Roughgarden, Lecture 2 ](https://theory.stanford.edu/~tim/f13/l/l2.pdf). The conclusion of the maximum conditions and the table are educational. [Zhang et al.](https://wnzhang.net/papers/ortb-kdd.pdf) consider functional optimization of RTB bets on a budget; their specific formulas depend on the payment model and assumptions and are not a universal formula for the first price.

## 5. Second price: Vickrey

### Principle

For one lot, the maximum bet wins, the winner pays the second highest. With a `r` reserve, the sale occurs only at a rate not lower than `r`, the winner's payment is the maximum of the reserve and the second bet.

For a participant with its known `v` value, quasi-linear utility, and no binding budget constraint, a true `b=v` rate is a weakly dominant strategy. Raising a bet above value creates a risk of a bad win; reducing it can deprive a bargain.

If `M` is a continuous random threshold of victory without reserve:

$
U(b)=\int_{-\infty}^{b}(v-m)\,dF_M(m).
$

### Expected output

A simple mechanism for disclosing private values and efficiently allocating one lot under standard premises does not, by itself, maximize a seller's revenue.

### Restrictions

Inferences about truthfulness are not automatically carried over to multiple GSP slots, shared budgets, total unknown value, or externalities. GSP and VCG in particular are different mechanisms.

**Source:** [Roughgarden, Mechanism Design Basics](https://theory.stanford.edu/~tim/f13/l/l2.pdf).

## 6 : Optimum Seller's Revenue: Myerson Auction

### Principle

In the base model, one lot is sold, participants are risk-neutral, their private values are independent and have known distributions of `F_i` with `f_i` densities.

$
\phi_i(v)=v-\frac{1-F_i(v)}{f_i(v)}.
$

With regularity, the monotony of `φ_i`, the lot is received by the participant with the maximum non-negative virtual value; the payment is determined by the critical value for winning. The value of saving the lot by the seller here is assumed to be zero. For equally distributed participants, this is realized by a second price with a `r` reserve that satisfies `φ(r)=0`. When irregular, virtual value smoothing, ironing, is required.

### Example and expected outcome

With two independent values of `Uniform[0,1]`, `φ(v)=2v−1`, the optimal reserve is `0,5`. The expected return on the second price increases from `1/3` without a reserve to `5/12` with a reserve, but the probability of selling decreases from 1 to `3/4`.

The method maximises the expected revenue in its model among mechanisms with corresponding constraints on stimuli compatibility and individual rationality.

### Restrictions

We need distributions **values**, Not just the observed strategic rates. Asymmetry, dependency, Budgets and re-engagement require a different model. Increased revenue may be accompanied by a decrease fill rate.

**Source:** [Roger Myerson, Optimal Auction Design, 1981, DOI](https://doi.org/10.1287/moor.6.1.58); [paperback](https://ranger.uta.edu/~weems/NOTES6319/PAPERSTWO/myerson.pdf).

## 7 : Reserve price and trade-off between price and sale

### Principle

In the simplest model of a fixed offer to one buyer:

$
r^*=\arg\max_r r\,P(V\ge r).
$

With several participants in the auction of the second price, the entire payment should be assessed:

$
\mathbb E[\max(r,V_{(2)})\,\mathbf 1\{V_{(1)}\ge r\}],
$

whereabouts `V_(1)` and `V_(2)` — first and second-highest value. Formula `r×P(sale)` insufficient: payment may exceed the reserve.

### Expected output

Reserve eliminates too cheap sales and can increase revenue due to fewer deals. Training example for a single buyer: price 100 ₽ probability of purchase 0,8 waiting 80 ₽; price 150 ₽ likely 0,4 — 60 ₽.

### Limitations and data

Historical responses after applying the previous threshold are censored: when a reserve changes, participants can change bets or participation; static log replay does not reflect this; the reserve should be checked as a separate policy with revenue per incoming request and fill rate.

**Ground:** [Myerson, 1981](https://doi.org/10.1287/moor.6.1.58). The formulas of expected payments above directly follow from the rules of sale and are explanatory conclusions.

## 8 Budgets, quotas and rate of expenditure: pacing

### Principle

Optimize the total result on the horizon `T`, for example:

$
\max_\pi\mathbb E\left[\sum_{t=1}^{T} R_t\right],
\qquad \sum_t C_{it}\le B_i.
$

One way is to scale your bets with `α_i∈[0,1]`: `b_it=α_i v_it`. The other is to only allow the campaign to the percentage of queries. The controller adjusts the pace for actual consumption and available traffic.

### Expected output

The resource is not exhausted on the first queries; it is possible to participate in more valuable future trades. The first-price pacing equilibrium model has proven the useful properties of equilibrium and the possibility of calculating it through a convex program.

### Restrictions

The equilibrium model does not prove the optimality of any particular online controller: too much slowing will leave the budget or plan unfulfilled; the limit of impressions, the limit of sending to the manager and the cash budget are different resources; if the quota is spent only on success, its expected consumption is `p`; if it is sent, one.

**Source: ** [Conitzer et al., Pacing Equilibrium in First-Price Auction Markets, arXiv 2018 ; EC 2019 ](https://arxiv.org/abs/1811.07166) .

## 9 . Online matching and MSVV: value adjusted for resource balance

### Principle

In the AdWords task, the requests come in sequential. `t` is paid to the `i` participant, `b_it` is paid, `B_i` is budgeted. MSVV uses a balancing multiplier:

$
S_{it}=b_{it}(1-e^{u_i-1}),
$

where `u_i` is the share of the budget already spent, and the more the budget is exhausted, the less effective the new appointment will be.

### Expected output

The trade-off between a high immediate rate and saving the resource for the future: For the initial formulation of AdWords at low bets relative to budgets, a competitive attitude is achieved asymptotically equal to `1−1/e≈0,632` , relative to the offline optimal.

This is the lower bound in the theoretical model, **non-promise 63,2%**.

### Restrictions

The limit on the number of impressions is not the same as the monetary budget of the original model. Substituting `p_i r_i` instead of deterministic revenue and adding frequencies, deadlines or training creates a new production; the guarantee must be proved anew. MSVV also does not automatically set a uniform clock pace and minimal execution of the plan.

**Sources:** [Mehta, Saberi, Vazirani, Vazirani, JACM 2007](https://doi.org/10.1145/1284320.1284321); [authorial](https://ics.uci.edu/~vazirani/Adwords.pdf).

## 10: Learning in progress: contextual bandits and Thompson Sampling

### Principle

If the probabilities are unknown, the constant choice of the maximum current estimate prevents the collection of data on the remaining candidates. The contextual bandit takes into account the features of the request and combines income generation with research. This is a suitable setting when the result of only the selected action is observed. See [Li et al., WWW 2010 ](https://arxiv.org/abs/1003.0146) .

In a simple stationary case, Bernoulli-success for each candidate:

$
p_i\sim\operatorname{Beta}(a_i,b_i),\qquad
\tilde p_i\sim\operatorname{Beta}(a_i,b_i),\qquad
i^*=\arg\max_i(\tilde p_i r_i-c_i).
$

After success, `a_i` increases, after failure, `b_i`. Sampling from a posteriori distribution is the basic idea of Thompson Sampling. A separate Beta model for a candidate without signs is not a full-fledged context bandit.

### Expected output

Reducing accumulated regrets about good policies, mastering new candidates and segments, part of the immediate income is spent on getting information.

### Restrictions

Drifting requires forgetting, a sliding window, or a dynamic model. With resource constraints, budgeted bandits/bandits with knapsacks. Simple random rotation without updating knowledge does not in itself provide effective learning. Probabilities of action must be preserved for policy evaluation.

**Source:** [Russo et al., A Tutorial on Thompson Sampling, 2018](https://arxiv.org/abs/1707.02038). Monetary rating in the formula — adaptation of the basic algorithm.

## 11 Dynamic Optimization and Opportunity Cost

### Principle

The solution is evaluated along with the change in the future state.

$
V_t(s)=\mathbb E_{x_t}\left[\max_{a\in A(x_t,s)}
\mathbb E[R_t+V_{t+1}(s')\mid x_t,s,a]\right].
$

Approximate rating with shadow resource prices:

$
S_i=\mathbb E[R_i]-\sum_k\lambda_k\mathbb E[\Delta q_{ik}].
$

`λ_k` expresses the monetary value of saving a unit of resource. For example, sending to a manager consumes quota and time, and a successful display can additionally consume the campaign limit.

### Expected output

An algorithm may reject a more profitable action now if it blocks even more profitable future sales, and for rare targeting or the last acceptable display to the user, this is especially important.

### Restrictions

Accurate dynamic models quickly become computationally complex, you need transition models, future traffic models, and correct accounting for resource-consuming events. Practical approximations: LP forecast, sliding-horizon recalculation, learnable shadow prices.

**Status:** general mathematical statement and applied conclusion of the review author. A close RTB problem of long-term rate and budget optimization is explored in [Weinan Zhang, UCL, 2016 ](https://discovery.ucl.ac.uk/id/eprint/1496878/) dissertation; this is not a statement of equivalence of all the algorithms listed.

## 12: Accounting for risk and uncertainty

### 12.1: A Careful Assessment of Probability

Instead of a point estimate, you can use the lower confidence or Bayesian limit `p_i^lower`:

$
S_i=r_i p_i^{\mathrm{lower}}-c_i.
$

**Expected output:** fewer decisions based on randomly inflated probabilities with few observations. **Limitation:** Systematically cautious selection makes it difficult to research new candidates; The width of the interval depends on the statistical model. It’s an engineering heuristic, Not a universally optimal auction.

### 12.2 .CVaR: Limiting bad outcomes

Expectation can be maximized while limiting the risk of underperformance or loss. For accidental loss `L`:

$
\operatorname{CVaR}_\alpha(L)
=\min_\eta\left[\eta+\frac{1}{1-\alpha}\mathbb E[(L-\eta)_+]\right].
$

At `α=0,95`, the index reflects the average weight of the worst five percent tail, with correct accounting for the mass at the border.

**Expected outcome: ** fewer severe failures at the cost of a possible decrease in average income. ** Limitation: ** need loss scenarios and dependencies between requests; it is more reasonable to estimate the risk of the outcome over the period than a separate binary response.

**Source: ** [Rockafellar, Uryasev, Optimization of Conditional Value-at-Risk](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf). Application to auction plans - adaptation, the initial work is devoted to the general method of risk management.

### 12.3: Robic mechanism for inaccurate distribution

Instead of the optimum for a single `F` score, we look for a mechanism that works well for a class of close distributions. **Result:** Revenue resistance to data errors; **Restriction:** Guarantee only applies to a selected class of uncertainty. This is different from adding an arbitrary penalty to the rating.

**Source:** [Guo, Jordan, Zampetakis, Robust Learning of Optimal Auctions, NeurIPS 2021](https://proceedings.neurips.cc/paper/2021/hash/b19aa25ff58940d974234b48391b9549-Abstract.html).

## 13. Other objectives: VCG, fairness and a few lots

### 13.1 VCG: Maximizing Total Value

**Principle:** The allowable distribution with the maximum amount of declared values is selected. Each participant pays an external loss, What his presence creates for others.

**Expected output:** Efficient distribution and truthfulness with quasilinear utilities and precise optimization. For one lot, the mechanism of the second price is obtained.

**Restrictions:** Maximizing social value does not equal maximizing site revenue. With complex sets of lots, calculating the optimum can be difficult; The arbitrary replacement of the exact optimum with a heuristic can destroy truthfulness.

**Source:** [Roughgarden, Multi-Parameter Mechanism Design and the VCG Mechanism](https://theory.stanford.edu/~tim/f13/l/l7.pdf).

### 13.2: Execution of Plans and Justice

**Principle:** There are clearly limits on minimum delivery, traffic, frequency and concentration. For example,, Optimized income with acceptable underperformance; or a weighted objective is applied `revenue − penalty`.

**Expected outcome:** Managed trade-off between money and liabilities.**Limitation:** Penalty ratios require business sense.Limitation may not be feasible if suitable traffic is lacking; `volume`'s upper limit alone does not guarantee minimum delivery.

**Status:** designing, not a separate theorem. Related Model of Distribution of Limited Advertising Resources — [AdWords and generalized online matching](https://doi.org/10.1145/1284320.1284321).

### 13.3 Total Value and Related lots

With an overall unknown value, the winner may be the one with the most inflated signal, the winner's curse. If the combinations of lots are valuable, the independent sale of each lot can lead to poor distribution, you need models of information, interdependence and batch bids.

**Expected outcome:** Rules better reflect the economics of the subject matter.**Limitation:** Formulas for one independent private lot are not automatically carried over.

**Source for context:** [NSF: interview Paul Milgrom the design of auctions and winner’s curse](https://www.nsf.gov/science-matters/greatest-auction-ever-qa-paul-milgrom-2020-nobel-laureate).

## 14: Probability quality and result verification

### Calibration

For a monetary rating, you need to check the numerical probabilities. Highly ROC-AUC shows the quality of the ranking, proverbial, among the predictions `p≈0,7` success happens approximately in 70% cases. Used reliability diagram, Brier score and log loss; The last two assess the overall quality of the probabilistic forecast, not just calibration. Calibration should be on the data, graduated. Seems. [scikit-learn: Probability calibration](https://scikit-learn.org/stable/modules/calibration.html).

### Evaluation of journal policy

The outcome of a chosen action is observed, and the results of the others are usually unknown, and the average return on requests chosen by the previous policy is not an unbiased estimate of the new policy.

In the presence of the `x_t` context, `a_t` actions, `R_t` rewards, and the probability of its selection by the old `μ(a_t|x_t)` policy, the IPS is applied:

$
\hat V_{IPS}(\pi)=\frac1N\sum_t
\frac{\pi(a_t\mid x_t)}{\mu(a_t\mid x_t)}R_t.
$

Coverage required: The new policy must have a non-zero probability in the old one. Small denominators increase variance; weight reduction reduces it by the cost of displacement. **Expected output:** More accurate comparison of partial feedback policies. Seems. [Swaminathan, Joachims, Counterfactual Risk Minimization, ICML 2015](https://proceedings.mlr.press/v37/swaminathan15.html).

Doubly robust Evaluation combines reward model and correction through probability of action; Under standard conditions, its validity is maintained, If at least one of these parts is correct. Coverage is still necessary. Seems. [Dudík, Langford, Li, ICML 2011](https://www.microsoft.com/en-us/research/publication/doubly-robust-policy-evaluation-and-learning-2/).

For politics, budget-changing, frequencies and future states, one-step IPS/DR-lack of: It evaluates decisions in the allocation of journal contexts. We need a model of sequential transitions, special trajectories assessment or experiment. This limitation is particularly significant for routing to a manager with internal limits.

### Practical Comparison Protocol – Recommendation for the Project

1: Determine the paid success, monetary reward, and event of each limit being written off.
2: Save candidates, choice, probability of choice, forecasts, prices, actual payouts, delay, and pre-decision condition.
3: Separate learning, calibration and test by time; do not use future answers and future counters.
4: Compare choice by price, probability, expectation, and expectation with constraints on identical streams.
5. In the simulator separately check the exhaustion of the budget, cold start, drift, timeouts and frequency limits.
6. Confirm the effect of a controlled experiment. Shared budgets and auctions create group interactions, Therefore, the unit of randomization should take into account these relationships; Regular splitting of requests may not be enough. Seems. [Liao, Kroer: A/B Testing for First-Price Pacing Equilibria](https://arxiv.org/abs/2301.02276).

The main metric for the platform is **net income for all incoming queries** Additional: sales, fill rate, quota expense, fulfillment of plans, revenue for the period, delays and frequencies. An increase in the share of success among those sent can be accompanied by a drop in total revenue if the algorithm sharply reduced the number of shipments.

## 15 Applied Analysis: Choosing Between a Manager and Another Sell

The following formulas — self-adaptation to the script, localized [managerial strategy](benchmark/manager_traffic/analysis/strategy.md). These are the calculation scenarios, Not a statement about current production.

Let the manager pay `r_m` on success with `p_m(x,s)` probability. "" Let another sale give the expected net revenue of `d`.

### If the request is lost after failure

At the `c_m` call price, a manager is selected when:

$
p_m r_m-c_m>d.
$

With `r_m=120 ₽`, `d=50 ₽`, `c_m=0`, the threshold is `p_m>0,4167`.

### If a backup sale is possible after failure

Let `f_m` be the expected net reserve revenue ** conditionally on the manager's failure **, taking into account the loss of time and availability of reserve demand:

$
S_m=p_m r_m+(1-p_m)f_m-c_m.
$

With `p_m=0,4`, `r_m=120 ₽`, `f_m=50 ₽`, `c_m=0`, we get `78 ₽` versus `50 ₽` direct selling. Without a backup sale, the manager's expectation would be `48 ₽`.

You can't automatically substitute `f_m=d` : after a timeout, the reserve demand may disappear, and the failure itself carries information about the quality of the request, and at limits, the alternative cost of consuming resources is added to the rating.

If the manager's payout is fixed and there are no alternatives, the maximization of probability and expected revenue is the same, and when different payouts, backup sales, or resource expenditures are different, the match disappears.

## 16: How to choose an approach

| Conditions | Starting point | What needs to improve | Check it out |
|---|---|---|---|
| Fixed payments, probability | `p×payment−cost` | Income per request | Calibration, unit |
| Different CPM/CPC/CPA | Overall expected monetary valuation | Comparability of proposals | Conditionality of probabilities |
| Buyer pays his bet | `(v−b)w(b)` | Profit on winnings, taking into account chance | Winning curve, budget |
| One lot, private | Vickrey | Effectiveness and truthfulness | Model premises |
| The seller chooses rules for the sake of revenue | Myerson / reserve | Expected revenue | Value distributions, fill rate |
| Budgets and plans for the period | Pacing | Expenditure and Outcome on the Horizon | Underexpenditure, write-off |
| Consistent allocation of limited resources | MSVV / online matching | Preserving valuable future opportunities | Conformity of the theoretical model |
| Probability unknown | Contextual bandit / Thompson Sampling | Training and accrued income | The cost of research, drift |
| Strong impact on future availability | Dynamic model, shadow-price | Full-time income | Quality of the transition model |
| Big failures matter | CVaR / robustness | Sustainability | Scripts, risk-cutting |
| Several linked lots | VCG / combinatorial | Total value of distribution | Computational complexity |

For internal selection in this project, a reasonable sequence of studies: ** expected net revenue → probabilities → quotas and pacers → training in new segments → dynamic cost of restrictions**. Changing the rules of external trading requires a separate analysis of participants’ incentives and payments.

## 17 - Communication with repository materials

- [General arrangement of the auction SDK](../src/rtb_sdk/auction/README.md): choice, price, priorities and limits. Random mixing `BEST_PRICE` The other strategy is not equivalent to calculating the expected income.
- [New auction](../src/rtb_sdk/auction/adwords/README.md): description of resource allocation and status of algorithms.
- [MSVV](auction_msvv_implementation.md) : local distribution options. Guarantees need to be checked against the original formulation, especially when transitioning between monetary and quantitative resources.
- [Probability Assessment Guidelines](../benchmarks/closed_stand/PROBABILITY_GUIDE.md): metric, calibration and limitations of historical verification.
- [Manager strategy](benchmark/manager_traffic/analysis/strategy.md): Applied statement of the probability of success and selection of requests; document, unproven effect.

## 18 : The main sources for further reading

1. **Myerson, 1981. Optimal Auction Design.** Theory of Maximizing Expected Revenue, virtuality, optimal mechanisms. [DOI](https://doi.org/10.1287/moor.6.1.58).
2. **Roughgarden, 2013. Mechanism Design Basics.** Rules of first and second prices, utility and incentives. [Lecture](https://theory.stanford.edu/~tim/f13/l/l2.pdf).
3. **Roughgarden, 2013. Multi-Parameter Mechanism Design and the VCG Mechanism.** Total value and payments VCG. [Lecture](https://theory.stanford.edu/~tim/f13/l/l7.pdf).
4. **Zhang, Yuan, Wang, 2014. Optimal Real-Time Bidding for Display Advertising.** Betting, response, Budget and functional optimization. [Article by the authors](https://wnzhang.net/papers/ortb-kdd.pdf).
5. **Zhang, 2016. Optimal Real-Time Bidding for Display Advertising.** Extensive task study RTB. [Thesis UCL](https://discovery.ucl.ac.uk/id/eprint/1496878/).
6. **Mehta et al., 2007. AdWords and generalized online matching.** Online-budgeting. [DOI](https://doi.org/10.1145/1284320.1284321).
7. **Conitzer et al., 2018–2021. Pacing Equilibrium in First-Price Auction Markets.** Pacing Theory in Auction Markets. [Article](https://arxiv.org/abs/1811.07166).
8. **Li et al., 2010. A Contextual-Bandit Approach to Personalized News Article Recommendation.** Contextual research and partial feedback; recommendation, not the auction theorem. [Article](https://arxiv.org/abs/1003.0146).
9. **Russo et al., 2018. A Tutorial on Thompson Sampling.** Principles of Bayesian Research. [Review](https://arxiv.org/abs/1707.02038).
10. **Rockafellar, Uryasev. Optimization of Conditional Value-at-Risk.** Optimization of tail risk. [Author’s version](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf).
11. **Guo, Jordan, Zampetakis, 2021. Robust Learning of Optimal Auctions.** Learning mechanisms for distorted data. [NeurIPS](https://proceedings.neurips.cc/paper/2021/hash/b19aa25ff58940d974234b48391b9549-Abstract.html).
12. **Swaminathan, Joachims, 2015. Counterfactual Risk Minimization: Learning from Logged Bandit Feedback.** Training and evaluation of decision journals. [ICML / PMLR](https://proceedings.mlr.press/v37/swaminathan15.html).
13. **Dudík, Langford, Li, 2011. Doubly Robust Policy Evaluation and Learning.** Combination of the reward model and the probability of choice. [Microsoft Research](https://www.microsoft.com/en-us/research/publication/doubly-robust-policy-evaluation-and-learning-2/).
14. **Liao, Kroer, 2023. Statistical Inference and A/B Testing for First-Price Pacing Equilibria.** Statistical verification in markets with pacing. [Article](https://arxiv.org/abs/2301.02276).
15. **scikit-learn. Probability calibration.** Official guidance for probabilities verification and calibration. [Documentation](https://scikit-learn.org/stable/modules/calibration.html).
