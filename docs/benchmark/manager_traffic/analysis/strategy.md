# Strategy: How to Handle a “Manager Campaign” in an Online Auction and Raise 200 Share

Status: **ideas and plan**, no implementation, based on `eda_findings.md` (facts about the flow) and `oracle.md` (limits of the possible), no real response codes yet, all the estimates of the effect below are preliminary.

## 1. The problem is formal.

- To request *x*, the manager returns 200 ("sold") or another 2 xx (the customer says 204 is not accurate). For 200, we get a fixed R, the price is independent of the manager's internal campaign.
- Manager — black-box; campaign/spinner/Prices are unknown to us.
- Required: ** Same volume of V** requests sent, but **higher proportion of 200 ** (less than 2 xx non-200).
- For us, each request sent costs the same (there is no price per request).

Equivalent wording: online selection of queries with an upper limit on the scope; the decision “send / do not send” for each incoming request (nearby is the decision “what our campaign to give instead”).

## 2. "" The big question is, is there a choice?

From `oracle.md`: Optimization is possible **only if the pool of queries that can be sent to the manager is greater than the quota V**.

| Script | Pool | Quotas V | Freedom of choice |
|---|---|---|---|
| S1: prefix | `no_web_mobile` (12.8 million/days) | pool | **no** (q = 1), Optimization is impossible |
| S2: quota < set-top | `no_web_mobile` | for example 50% current volume | yes: select the best of the consoles |
| S3: pooled | device (20.7 million/days) | prefix (12.8 million = 62%) or 80% everything | yes: We can also send a portion of the web/cellphone, and select prefixes |

This is the reason why we need markups for each `device_type`: the pool is given by any subset of devices, the quota is given by a single parameter, and we need to ask the customer which scenario is real and what exactly "80%" means (A/B/C variants in `oracle.md`, section 5).

## 3 .Solution architecture (as part of an online auction)

The manager is embedded in the auction as a **pseudo-campaign** with special properties:

- «targeting»: any requests from the pool (markup/segments);
- price = R · p̂(x), whereabouts p̂(x) — probability 200 (yield);
- without their own frequency limits (the manager may have their own – this is checked according to the data);
- volume limited to pacing: while `shipped < quota(t)`.

Solution to request *x*:

1. If p̂(x)·R ≥ threshold τ(t) and the quota for the current hour is not exhausted — send out;
2 . . . otherwise - to give our campaigns (ordinary auction).

Thread τ(t) feed-in, Towards the end of the period, send it exactly V requests: flow (forecast «yesterday» ≈10% MAPE, peak/minimum 5.3× — `eda_findings.md`, section 4). If we have our own value on the side of the request E[v_ours(x)], generalize: dispatch, when R·p̂(x) ≥ E[v_ours(x)] + λ(t) (λ — quota multiplier). That’s consistent with «price-rate» at the current auction (`best_price`): A new strategy with an expected price R·p̂(x).

## 4. Evaluation ideas p̂(x)

Ideas are sorted from simple to complex; each is applicable only after response codes appear.

### 4.1 Hierarchical score by profile (base)

- Profile = tagging. Key hierarchy EDA: `device×ep×place` (44 profile, 99% traffic) → `+region` (12.9 thousand.) → `+channel` or `+category` (80–590 thousand.).
- p̂ — Beta-posterior (empirical Bayes / hierarchical shrinkage): `p̂ = (k + m·p̂_parent)/(n + m)`.
- Why it works: the stream is very stable (tags almost do not change every day, “new” profiles 0.03 – 1%), for detailed data profiles, compression is not necessary.
- Quick start: profile table → (successes, attempts), updated stream.

### 4.2 User Features

- 81-93% requests come from already seen users; the user does not change the device.
- Signs: day-by-day serial number, interval, number 200/not-200 for the user N hours/days, Number of requests to the manager today.
- Hypotheses to test: (?) The manager has his own frequency limits → p(200) decreases with the increase in the number of sendings to one user; (b) VOD-rhythm 8–10–16 minute: position `ad_position` 2–3 block sells worse/better than first; (in) The first user requests per day are sold better.
- Model: logistic regression / GBM on top of the profile; online state - counters by `client_id` (`client_id` logs have 99.9% requests).

### 4.3 Time.

- Inside the day, p(200) can change shape: the manager's budgets are selected by the evening, the flutes are turned on and off.
- Idea: p  as a function (profile, hour); for nonstationarity, exponential forgetting or change-point detector at (profile, hour).
- Verification in data: steps P(200) in a stable segment over time.

### 4.4 Bandit Layer (Learning Online)

- The task is **knapsack-bandit** (a bandit with a limit on the number of impressions): each “profile” is a hand, reward = 1 at 200; budget = quota V.
- Algorithms: Thompson sampling by Beta-posteriore profiles + threshold τ(t); for non-stationarity - discounted TS / sliding window.
- Contextual version: LinUCB / Thompson on top of the GBM embed profile.
- Needed for: (1) training on low-frequency profiles, (2) drift, (3) research of new segments.

### 4.5: How to Rebuild a Manager’s “Company”

- No query logs (`eda_findings.md`, section 6) can be used for coded logs.
  - decision-maker / RuleFit on (tagging → 200): high-leaf p̂ — «targeting» company manager;
  - posteriorization (profile clustering p(hour, day)): Profiles from one company will have associated time curves (switch-on/flute-off);
  - change-point detector p̂(segment, time): kick-off/stoppage.
- Recovery is not necessary for our purpose: enough p̂(x); recovery, if **explain** change p(200) keep up the segment, When the manager’s company left.

## 5 Exploration and non-displacement (important)

We’re watching the outcome **only for sent requests**. If the optimizer sends only «best», valuation p̂ No updates for the remaining segments (loop: bias).

- Reserve **randomness ε** (1–2%) uniform selection requests from the pool — estimation p̂ control «basic» sellout.
- For offline evaluation of policies by logs: inverse probabilities (IPS) and doubly robust; for this, logged solutions must have a non-zero probability (ε guarantees).
- Measuring the effect in A/B:, the control group receives the previous policy, the test - the optimizer; the metric - the share of 200 with an equal V.

## 6 - Metrics and limitations (guardrails)

Basic: 200's share of shipments at the same volume.

- fulfillment of quota V (deviation ≤ 1-2%) and uniformity over the hours;
- share 2xx, delay/timeouts of manager’s response;
- income from our party on requests not sent to the manager (so as not to exchange the 200 manager for the loss of our sales);
- Diversity of traffic sent: if you send only a narrow “gold” segment to the manager, his campaigns can adapt (prices, limits), and the p(200) of the segment will fall (feedback to the manager);
- Arrangement: Perhaps the manager has the conditions for the traffic structure (diversification, minimum share of platforms).

## 7 . Work plan (order)

1. **Get logs**: manager response code, manager's "gone" feature, response time; ≥ 7 days, preferably ≥ 14 (to see twice weekends). Check the new format with the same token search (as in 10 k sample): the code can be inside `path`.
2. **Confirm the script and "80%"** (2 and `oracle.md`, 5).
3. **EDA with codes** (`eda_findings.md` repeat with target variable): P(200) by profile, by clock, by user frequency; O₁/O₂ oracles on real data.
4. **Basic model** 4.1 (hierarchical profile score) + threshold τ(t) → offline check on deferred days (training recently 1 – 5, checking 6 –7).
5. **User features** 4.2 → measure gain over 4.1; **Temporary** 4.3.
6. **Online**: Expected Price + Pacing + ε-Research, A/B 5 –10% Traffic Auction Strategy.
7. **Bandit layer** 4.4 for low-frequency profiles and drift.

## 8 Risks

- No choice (S1): optimise; Then the winnings can be obtained only by expanding the pool or changing the quota/arrangement.
- Low variance p(x): ceiling (`oracle.md`, κ ≳ 30 → +2–4 p.p.).
- Drift: p(200) changes with the change of management companies - you need monitoring and quick forgetting.
- Choice bias: Without ε-study, the model degrades.
- Contract: The volume and structure of traffic agreed with the manager may limit selection.
- 204 as “not sold” can mean different things (no ads, filter, timeout): 2 xx codes should be divided into data rather than merged into “not-200”.
