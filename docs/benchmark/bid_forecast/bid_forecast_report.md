# Evaluating Price and Win-Probability Models in an RTB Auction

## 1. Problem Setup

We compare competition-price models and bidding strategies in a first-price RTB auction simulation. The goal is to evaluate policies' total revenue, win-probability forecast quality, and realized auction margin.

| Symbol | Meaning |
|---|---|
| $x_i$ | Categorical features of request $i$, such as device, region, category, and channel. |
| $v_i$ | CPM of the selected eligible own campaign available for the request, accounting for its limits; zero if no campaign is available. |
| $b_i$ | Our bid on request $i$. |
| $Z_i$ | Maximum CPM among competing campaigns available for the request; if none is available, the reserve price is 50. |
| $Y_i$ | Numeric outcome: $1$ for a win ($b_i>Z_i$), $0$ for a loss ($b_i\le Z_i$). Equality is a loss. |

Total revenue consists of margin from won auctions and external revenue from our campaigns:

$$G=M+O,\qquad M=\sum_{i:\,b_i>Z_i}(v_i-b_i).$$

The sum $M$ includes only won requests. $O$ is campaign revenue from served impressions outside the competitive market being evaluated. Monetary values are in simulator units: the CPM value is credited directly for each served impression, without dividing by one thousand.

The model selects the bid that maximizes predicted margin among integer bids no greater than the available value:

$$b_i^{*}=\arg\max_{b\in\mathcal{B},\,b\le v_i}(v_i-b)\hat{F}(b\mid x_i),\qquad \mathcal{B}=\{0,1,\ldots,400\},$$

where $\hat{F}(b\mid x_i)$ estimates the strict win probability $P(Z_i<b\mid x_i)$. The bid depends only on the forecast, not on $Z_i$, which is unknown to the policy. If no campaign is available ($v_i=0$), the participant does not bid.

Training is compared under **full** information, when the exact price is known, and **censored** information, when the exact price is known after a win but a loss reveals only $Z_i\ge b_i$. Data are split by time: train for training, days $[0,3)$; validation for parameter selection, $[3,5)$; test for final evaluation, $[5,7)$. The main run had 88 290 / 59 458 / 68 221 requests, respectively; environment seed 1900, selected-user fraction 0.002, and 3 competing sellers. Campaign plans were calculated using train only; campaign states, but not the planning source, were reset between phases. The maximum training sample size was 30 000, and validation 15 000. Censored training bids are drawn from a continuous uniform distribution from 50 to 360, not from the integer grid of model bids.

**Probability metrics.** In the formulas, $p_i$ is the predicted win probability at the evaluated bid, $Y_i$ is the actual outcome ($1$ for a win, $0$ for a loss), and $n$ is the number of evaluated requests. All three errors below should be minimized; they are not measured in monetary units.

**Brier score: mean squared probability error.** For each request, the forecast is compared with the outcome, and the squared difference is then averaged:

$$\mathrm{Brier}=\frac{1}{n}\sum_{i=1}^{n}(p_i-Y_i)^2.$$

For example, a forecast $p_i=0{,}8$ has an error of $0{,}04$ for a win and $0{,}64$ for a loss. The Brier score ranges from $0$ to $1$; lower is better. It is not the percentage of incorrect decisions: a Brier score of $0{,}17$ does not mean 17% classification errors. Probability is evaluated over a series of outcomes, so even a correct forecast of $0{,}8$ will sometimes be followed by a loss.

**Log-loss: logarithmic probability error.** It evaluates how much probability the model assigned to the outcome that actually occurred. If the participant won, the penalty is $-\ln p_i$; if it lost, the penalty is $-\ln(1-p_i)$:

$$\mathrm{LogLoss}=-\frac{1}{n}\sum_{i=1}^{n}\left[Y_i\ln\tilde p_i+(1-Y_i)\ln(1-\tilde p_i)\right],\qquad \tilde p_i=\min(1-\varepsilon,\max(\varepsilon,p_i)),\quad \varepsilon=10^{-6}.$$

Log-loss especially strongly penalizes confident errors: after a loss, a forecast of $0{,}99$ incurs a penalty of about $4{,}61$, while a forecast of $0{,}6$ incurs about $0{,}92$. The natural logarithm is used. Lower is better; without bounding probabilities, the error is unbounded. Probabilities are clipped using the specified $\varepsilon$ so forecasts of $0$ and $1$ do not produce an infinite penalty. Log-loss is not an error rate either.

**ECE: calibration error.** It checks whether stated confidence matches the observed win frequency. For example, about 70% of requests forecast near $0{,}7$ should be wins. Here, ECE is the request-count-weighted absolute difference between mean forecast and actual win fraction across 10 equal-width probability bins; lower is better. $n_k$ is the number of requests in bin $k$, $\bar p_k$ is the mean forecast, and $\bar Y_k$ is the mean outcome; an empty bin contributes zero.

$$\mathrm{ECE}=\sum_{k=1}^{10}\frac{n_k}{n}\left|\bar p_k-\bar Y_k\right|.$$

An ECE of $0{,}04$ means an average weighted discrepancy of 4 percentage points within the chosen bins. A low ECE alone does not prove that a forecast is useful: a constant probability close to the overall win rate may be well calibrated but fail to distinguish requests.

**Mean forecast and actual win fraction** are, respectively, the mean of $p_i$ and the mean of $Y_i$ over the same sample. Their difference shows overall probability overprediction or underprediction, but matching means do not guarantee calibration within request groups.

**Monetary metrics.** In the economic table, total revenue is $G$, and the two differences show how much it exceeds the mean random-strategy revenue and shading revenue; a positive value is better. In the margin table, expected margin is the sum of $(v_i-b_i)p_i$ over our bids, and actual margin is the sum of margins from wins. Their difference shows how far the predicted monetary result diverged from the realized result; it is not a separate calibration metric.

**Local regret** is the margin lost relative to a decision-maker that knows the current price $Z_i$ in advance and chooses the best allowable grid bid separately for each request. Lower is better. It is calculated on the actual requests and states of this policy; it does not model the effect of alternative bids on future requests and is not a gap from the global campaign optimum. External revenue $O$ is excluded from expected/actual margin and regret.

## 2. Results

Here, “online” means a sequential simulation with three competing managers and our participant, not operation on a real ad exchange. After each request, the states of campaigns that served it are updated; models are not retrained during the test.

- **Table 1** gives total revenue and probability diagnostics at the own bids of online policies; revenue is compared with 100 online random-bid runs.
- **Table 2** is not an online run of the policies being studied. It is a static forecast check on a shared market trajectory with the same three managers. Probe bids do not affect subsequent states.
- **Table 3** gives expected and actual margins for the same online policies; local regret is calculated after the run using prices known to the evaluator.

### Table 1. Economic Results and Forecast Quality of Online Policies, Three Managers

Mean total revenue across 100 random runs was **14 576 238**; the minimum was **14 561 124**, the maximum **14 585 295**, and the 5th / 50th / 95th percentiles were **14 568 452 / 14 576 155 / 14 582 803**. The runs vary the bid seed, not the market environment.

Revenue and probability metrics in each row belong to the same online policy in the environment with three competing managers. “At model-selected bids” means the model selects bid $b_i^{*}$ and its forecast $p_i=\hat{F}(b_i^{*}\mid x_i)$ is compared with the actual auction outcome $Y_i$. These are online decision results, not a separate experiment with a different bidding rule. Technically, diagnostics were computed in a deterministic replay of the same policy; replay revenues match the main runs.

Probability metrics and actual win fraction are calculated only for requests with an available campaign ($v_i>0$); $n$ is their count, including cases with a zero bid. Total revenue $G$ covers the entire phase and includes external revenue. For shading and truthful, the actual win fraction is reported, but forecast, Brier, log-loss, and ECE are absent because these strategies do not predict probabilities. Fractions in the table range from $0$ to $1$: for example, $0{,}2091$ means 20,91%.

| Information regime | Policy | Total revenue | Difference vs. mean random bids | Difference vs. shading | $n$ | Actual win fraction | Mean forecast | Brier | Log-loss | ECE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full prices | SM (global Kaplan–Meier) | 15 233 644 | +657 406 | +255 901 | 65 725 | 0,2091 | 0,2480 | 0,1673 | 0,5178 | 0,0389 |
| Full prices | NM (global, wins only) | 15 233 644 | +657 406 | +255 901 | 65 725 | 0,2091 | 0,2480 | 0,1673 | 0,5178 | 0,0389 |
| Full prices | NTM (tree, wins only) | 15 172 627 | +596 389 | +194 884 | 65 714 | 0,2479 | 0,2754 | 0,1761 | 0,5328 | 0,0533 |
| Full prices | STM (Kaplan–Meier tree) | 15 172 627 | +596 389 | +194 884 | 65 714 | 0,2479 | 0,2754 | 0,1761 | 0,5328 | 0,0533 |
| Full prices | STM pruned (simplified using validation) | 15 163 835 | +587 597 | +186 092 | 65 714 | 0,2471 | 0,2736 | 0,1748 | 0,5296 | 0,0446 |
| Full prices | Cui, lognormal mixture | 14 693 164 | +116 926 | −284 579 | 66 272 | 0,2819 | 0,2027 | 0,2360 | 0,9867 | 0,1769 |
| Full prices | Cui, point mean | 14 468 040 | −108 198 | −509 703 | 67 453 | 0,1173 | 0,2973 | 0,1800 | 2,4867 | 0,1800 |
| Censored prices | SM (global Kaplan–Meier) | 15 233 644 | +657 406 | +255 901 | 65 725 | 0,2091 | 0,2481 | 0,1673 | 0,5178 | 0,0389 |
| Censored prices | NM (global, wins only) | 15 239 869 | +663 631 | +262 126 | 65 728 | 0,2052 | 0,4330 | 0,2150 | 0,6228 | 0,2279 |
| Censored prices | NTM (tree, wins only) | 15 210 066 | +633 828 | +232 323 | 65 717 | 0,2358 | 0,4145 | 0,2101 | 0,6060 | 0,1807 |
| Censored prices | STM (Kaplan–Meier tree) | 15 169 928 | +593 690 | +192 185 | 65 718 | 0,2368 | 0,2649 | 0,1749 | 0,5311 | 0,0593 |
| Censored prices | STM pruned (simplified using validation) | 15 175 499 | +599 261 | +197 756 | 65 720 | 0,2333 | 0,2607 | 0,1726 | 0,5261 | 0,0542 |
| Censored prices | Cui, lognormal mixture | 14 829 498 | +253 260 | −148 245 | 66 206 | 0,2456 | 0,3420 | 0,2404 | 0,7789 | 0,1936 |
| Censored prices | Cui, point mean | 14 709 465 | +133 227 | −268 278 | 67 083 | 0,1614 | 0,5347 | 0,3733 | 5,1579 | 0,3733 |
| Baseline strategy | Shading, $\alpha v$ | 14 977 743 | +401 505 | 0 | 67 453 | 0,1061 | — | — | — | — |
| Baseline strategy | Truthful, $b=v$ | 13 804 190 | −772 048 | −1 173 553 | 65 668 | 0,3694 | — | — | — | — |

13 of the 14 model policies outperformed every random run; the exception was full Cui point-mean. Truthful also did not outperform any run, while shading outperformed them all. There were no ties. For full SM, auction margin was **1 115 069**, and external revenue was **14 118 575**; total revenue therefore includes campaign serving outside the market.

### Table 2. Shared Static Probe, Not an Online Policy

The shared probe set contains all 68 221 requests. Its trajectory was generated without our market bids; request value is the maximum CPM of our own targeting-eligible campaigns, without considering their limits. Random integer bids from 50 to 360 (seed 1 001 003) are applied to this fixed trajectory and do not change its state. Thus, all models are evaluated on the same requests, prices, and bids. The actual win fraction for every model is 0,5578.

| Information regime | Model | Mean forecast | Actual win fraction | Brier ↓ | Log-loss ↓ | ECE ↓ |
|---|---|---:|---:|---:|---:|---:|
| Full prices | SM (global Kaplan–Meier) | 0,5560 | 0,5578 | 0,1745 | 0,5027 | 0,0094 |
| Full prices | NM (global, wins only) | 0,5560 | 0,5578 | 0,1745 | 0,5027 | 0,0094 |
| Full prices | NTM (tree, wins only) | 0,5452 | 0,5578 | 0,1569 | 0,4619 | 0,0212 |
| Full prices | STM (Kaplan–Meier tree) | 0,5452 | 0,5578 | 0,1569 | 0,4619 | 0,0212 |
| Full prices | STM pruned (validation) | 0,5447 | 0,5578 | 0,1571 | 0,4623 | 0,0174 |
| Full prices | Cui, lognormal mixture | 0,5475 | 0,5578 | 0,1668 | 0,6338 | 0,0945 |
| Full prices | Cui, point mean | 0,5438 | 0,5578 | 0,2296 | 3,1723 | 0,2296 |
| Censored prices | SM (global Kaplan–Meier) | 0,5580 | 0,5578 | 0,1745 | 0,5026 | 0,0082 |
| Censored prices | NM (global, wins only) | 0,7358 | 0,5578 | 0,2142 | 0,6017 | 0,1781 |
| Censored prices | NTM (tree, wins only) | 0,6914 | 0,5578 | 0,1831 | 0,5387 | 0,1342 |
| Censored prices | STM (Kaplan–Meier tree) | 0,5457 | 0,5578 | 0,1605 | 0,4714 | 0,0195 |
| Censored prices | STM pruned (validation) | 0,5456 | 0,5578 | 0,1607 | 0,4724 | 0,0188 |
| Censored prices | Cui, lognormal mixture | 0,6836 | 0,5578 | 0,1925 | 0,7173 | 0,1569 |
| Censored prices | Cui, point mean | 0,6833 | 0,5578 | 0,2498 | 3,4512 | 0,2498 |

With full information, NTM matches STM, and SM matches NM, across all reported metrics. This is a match on this dataset; the models differ with censored information. The lowest Brier score is 0,1569 for full NTM/STM; the lowest ECE is 0,0082 for censored SM. Censored NM overpredicts the mean: 0,7358 versus an actual fraction of 0,5578.

### Table 3. Online Policy Margins and Local Reference

| Information regime | Model | Expected auction margin | Actual auction margin | Local grid regret |
|---|---|---:|---:|---:|
| Full prices | SM / NM | 1 909 867 / 1 909 867 | 1 115 069 / 1 115 069 | 901 402 / 901 402 |
| Full prices | NTM / STM | 1 598 739 / 1 598 739 | 1 156 527 / 1 156 527 | 614 671 / 614 671 |
| Full prices | STM pruned | 1 590 029 | 1 147 970 | 613 829 |
| Full prices | Cui mixture | 858 605 | 680 509 | 836 106 |
| Full prices | Cui point-mean | 1 141 425 | 385 835 | 1 380 513 |
| Censored prices | SM | 1 910 059 | 1 115 069 | 901 402 |
| Censored prices | NM | 3 404 923 | 1 085 029 | 973 837 |
| Censored prices | NTM | 2 601 931 | 1 163 661 | 699 107 |
| Censored prices | STM | 1 605 111 | 1 143 923 | 666 014 |
| Censored prices | STM pruned | 1 603 388 | 1 145 054 | 688 015 |
| Censored prices | Cui mixture | 1 595 405 | 767 428 | 931 861 |
| Censored prices | Cui point-mean | 2 373 045 | 604 810 | 1 155 397 |

Expected margin, realized margin, local regret, total revenue, and probability metrics measure different outcomes. For example, the high expected forecast of censored NM did not lead to the highest actual margin.

## 3. Models Used

**SM, global Kaplan–Meier.** Estimates one price distribution without request features. Exact win prices are treated as events and losses as censoring: the price is known to be at least the bid, but its exact value is unknown. The win probability sums price masses strictly below the bid; any unallocated tail mass remains in the tail.

**NM, global distribution of wins.** The NM label does not mean a normal distribution. The model counts exact prices among wins only and normalizes them; it ignores losses and the information they contain.

**NTM, tree with win-only price estimates.** An empirical distribution of exact win prices is built in each leaf. Losses are not included in the price-distribution estimate, but their rows participate in category grouping and in checking the minimum child-node size.

**STM, Kaplan–Meier tree.** Uses the same categorical tree structure, but accounts for exact win prices and censored losses through Kaplan–Meier in each leaf.

**STM pruned.** After STM training, it checks whether to collapse branches based on the validation observations' negative log-likelihood. A removal is accepted if NLL does not increase. Validation is used to simplify the tree, not to tune revenue.

Trees search for category splits based on divergence between child-group distributions, measured by Kullback–Leibler divergence (KL). Each group must have at least 200 observations; maximum depth is 5. The practical seeded search redistributes categories between two groups; it is not exhaustive. A missing or unknown category is assigned a direction pseudo-randomly with a fixed seed.

**Cui mixture.** The adaptation estimates segments of price history by mean and standard deviation, then combines their lognormal distributions into a mixture. Two gradient-boosting regressors predict the mean and standard deviation, with 20 trees each. A history node is used when it has at least 5 weighted impressions; training uses win prices only. Segment weights are equal, not estimated as future traffic shares.

**Cui point-mean.** This baseline strategy replaces the mixture with a point mass at the predicted mean: a win is predicted only when the bid is strictly above that mean. Standard deviation is not used.

**Baseline strategies.** Shading bids $\alpha v$, where $\alpha=0{,}4$ was selected using validation. Truthful bids $b=v$. A random bid is chosen uniformly between the reserve and the value of the available campaign; 100 runs were conducted with seeds 1000–1099. These strategies do not produce probability forecasts.

## 4. Limitations and Conclusions

- Results apply to one simulation environment. The 100 random runs change the bid seed, not the market, and do not provide an uncertainty interval across different markets.
- Total revenue includes external campaign revenue and depends on campaign composition, limits, and traffic plan; it is not equal to trading margin.
- Our online trajectories are endogenous: wins change competitors' remaining campaign limits and may change prices on later requests. The shared probe measures forecasts on a fixed trajectory.
- Methods were adapted to this simulation and are not literal reproductions of published experiments. Prices and outcomes come from simulated campaigns on a prepared request stream, not observations of real auction prices; results cannot be transferred directly to real auctions.
- Several independent market seeds, campaign plans, and time periods should be evaluated separately, with auction margin and external revenue reported separately.
