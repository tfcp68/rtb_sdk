# Hypothesis: the hour weight `w_h` mixes reach and frequency

A draft document for testing an idea proposed as a follow-up to
[`frequency_accounting_improvements.md`](../../../frequency_accounting_improvements.md)
(section 0). Not a fact — a hypothesis that is to be confirmed or rejected on
real logs before being written up as a section of the main doc.

## The idea

`compute_hour_shares()`/`weights_dict` in `build_seasonal_context()`
(`src/rtb_sdk/balancer/seasonal/balance.py:398`) take the hour weight `w_h` from
`normalize_counts(state['counts'])` — that is, from the **total number of events**
(impressions) in that hour, computed by `process_log_chunk()`
(`src/rtb_sdk/balancer/seasonal/seasonality.py:97`):

```python
counts[h] = counts.get(h, 0.0) + value   # value is almost always 1.0 (one impression)
```

This number decomposes into two independent factors:

```
counts[h] = reach[h] × freq[h]

reach[h] = |{uid : uid appeared in hour h}|     — how many distinct users
freq[h]  = counts[h] / reach[h]                 — how many impressions per user on average
```

After normalization the model uses only the product (`w_h`), never
splitting it into `reach[h]` and `freq[h]`. Meanwhile the code already collects all the raw
material needed for the split — `user_counts_by_hour[h][uid]`
(`seasonality.py:102`) — but uses it only inside
`_compute_user_ratio()` (`balance.py:300`) for the saturation coefficient
on top of an already computed limit. The very fact "hour weight = achievable volume" is
never checked against what this weight is actually made of.

### Why this may be a problem

For volume constraints (`ad_frequency_limit`, the whole volume balancer) the difference
does not matter — traffic is traffic, no matter how many distinct people it came from.

But for **user** constraints (`user_frequency_limit`, sections 1 and 5
of the main doc) it is fundamental: the real delivery ceiling per hour is
`reach[h] × user_period_limit`, not the traffic volume itself. Two hours with the
same `w_h` but a different `reach`/`freq` decomposition give different
real capacity:

| Hour | `reach[h]` | `freq[h]` | `w_h` (= reach×freq) | Real ceiling for a user-capped campaign |
|---|---|---|---|---|
| A: broad reach | 10,000 | 1.2 | 12,000 | high — many distinct people, the limit barely bites |
| B: narrow core | 500 | 24 | 12,000 | low — the same 500 people are browsing actively, `user_frequency_limit` is exhausted almost immediately regardless of volume |

A model operating only on `w_h` will see the same "weight" in A and B and allocate the
same traffic volume — although the capacity for a user-capped campaign in B is
an order of magnitude lower. Section 1 of the doc (`compute_aggregate_user_headroom`) and section 5
(`UserActivityMixture`, the shares `π_i` by user type) implicitly
assume that the audience composition (the shares of "casual/active/super-active"
users) is the same in all hours — the decomposition below tests whether this is
so.

## Hypothesis

**H0 (the current model is already sufficient):** `freq[h]` is approximately constant across all
hours (a low coefficient of variation), and/or the composition of user segments
(`user shares`, by analogy with section 5) does not depend on the hour. Then
`w_h ≈ const × reach[h]`, and the current weight is already a good proxy for reach;
the decomposition would make no practical difference.

**H1 (the decomposition is needed):** `freq[h]` varies noticeably across hours
(a high CoV) and/or the shares of user segments in `reach[h]` change from
hour to hour. Then an identical `w_h` masks a different reach, and the model
systematically errs in predicting volume for user-capped campaigns
precisely in the hours where `freq[h]` is anomalous (in either direction — both for narrow
"core" hours and for hours with an inflow of new users).

## Verification plan

Implemented in [`check_reach_vs_volume.py`](check_reach_vs_volume.py). Steps:

1. **Loading the log.** Format — `{user_id, date[, tags]}`, as in
   `data/requests.json` (schema example: 14,674 records, 2,432 unique
   `user_id`s, but only 24 minutes of a single day — this is not enough for
   an hourly profile; the script explicitly warns about this and draws no conclusions
   when hour coverage is incomplete).
2. **Bucketing by hour** — with the same `_get_h_type()` function as the
   production code (`hour_of_day` or `hour_of_week`), so that the result is
   comparable with the real `weights_dict`.
3. **Counting per hour:** `counts[h]`, `reach[h] = |unique uid|`,
   `freq[h] = counts[h] / reach[h]`.
4. **Comparing distributions:** `w_h = normalize(counts)` (what the model
   uses now) against `reach_share_h = normalize(reach)` (what
   should be used for user-capped campaigns) — the maximum
   divergence and the Pearson/Spearman correlation between them.
5. **CoV(freq[h])** across all hours — the threshold for accepting H1 (preliminarily:
   CoV > 0.15 or max|w_h − reach_share_h| > 0.05 → H1 confirmed; below —
   H0, the model is correct as is).
6. **User segmentation.** Split `user_id`s into activity buckets by
   quantiles of the total number of requests over the whole period (the analog of
   casual/active/super-active from section 5 of the main doc) and for
   each hour compute the share of `reach[h]` attributable to each segment.
   Check whether these shares are stable across hours or are also hour-dependent — this is
   a separate, subtler version of the hypothesis: not only do `reach` vs `freq`
   diverge from `w_h`, but the *composition* of reach differs between hours.
7. **Coverage completeness check** — there should not be many hour buckets with zero or
   single `reach[h]`; if hour coverage is incomplete
   (as in the attached example), the script prints a warning and gives no
   final verdict on CoV/correlation.
8. **Verdict** — the script prints a table for each hour (`counts`, `reach`,
   `freq`, `w_h`, `reach_share`) and the final H0/H1 decision with numbers.

## What to do based on the result

- **H0 confirmed** — the decomposition can be skipped; the current `w_h` is
  sufficient as a proxy for user-capped campaigns as well; close this hypothesis with no
  code changes.
- **H1 confirmed** — write it up as a new section of `frequency_accounting_improvements.md`
  (analogous to section 0: `HourShares`, but for `reach`/`freq` instead of
  `day/week/month` shares), with an explicit formula for replacing `w_h` by `reach_share_h`
  wherever the weight is used to estimate the capacity of user-capped campaigns
  (`compute_aggregate_user_headroom` from section 1, the weights `π_i` of the mixture from
  section 5), and with calibration via the backtesting infrastructure already
  proposed in section 6.

## Data limitation

The attached `data/requests.json` is only a schema example (24 minutes, a single
day), insufficient for computing an hourly profile over a day/week. For a
meaningful verdict, a log is needed covering at least a full
`hour_of_day` cycle (24 hours) — ideally several weeks for the
`hour_of_week` mode, so that `reach[h]`/`freq[h]` are not noise from a small
sample.
