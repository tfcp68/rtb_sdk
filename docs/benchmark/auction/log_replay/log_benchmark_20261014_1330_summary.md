# Summary of benchmark auctions on real logs (2026 -10 -14 )

Source: `docs/benchmark/auction/log_replay/log_benchmark_20261014_1330.md`

**Conditions:** period month (30 daylight), 32 campaigns, PRECISE-matching, seed 42, three modes of traffic. Common volume company — 6,4 million impressions.

| Traffic | Requests | Requests / volume | Sellout best_price | Loss of-limitless (best_price) | Best in revenue |
|---|---|---|---|---|---|
| shortage (×0.5) | 2,46 million | 0,38 | 37,0% | 3,8% | best_price |
| balanced (×1.0) | 4,92 million | 0,77 | 68,8% | 10,6% | best_price |
| excess (×2.0) | 9,85 million | 1,54 | 95,6% | 28,2% | best_velocity (100,3%) |

## Revenue per cent of best_price

| Algorithm | shortage | balanced | excess |
|---|---|---|---|
| best_price | 100 | 100 | 100 |
| best_heuristics | 95,6 | 98,8 | 100,3 |
| best_hybrid_0.2 | 88,4 | 98,8 | 100,3 |
| random_hybrid_0.7 | 91,8 | 95,7 | 100,3 |
| best_velocity | 77,8 | 88,3 | 100,3 |
| balancer | 84,8 | 89,6 | 98,6 |
| a2 / a3 | 83,1 | 87,3 | 95,0 |
| best_one | 82,3 | 82,6 | 92,2 |
| random_one | 68,4 | 78,0 | 97,8 |

## Findings

- **Lack of traffic (shortage, balanced):** best-paid — `best_price`, but `best_heuristics` and `best_hybrid_0.2` lag behind ~1% upon balanced (on 4–5% upon shortage).
- **Excess traffic (excess):** algorithms, considering velocity (velocity, heuristics, hybrid), overtake `best_price` (+0,3%) evenly spent volume. Greedy-algorithms (`best_one`, `best_price`) Choose expensive companies ahead of time: at `best_one` daylight ~270 thousand. before 33 thousand. toward 30-day by day.
- **Worst result:** `best_one` — lowest revenue at shortage/balanced and 92,2% upon excess (5,84 million impressions).
- **Fill at excess:** near 59-62%, ~38% requests remain unseen due to volume exhaustion and frequency limits (loss due to 25-30% limits).
- **`a2_single_valued` and `a3_small` give identical results** (impressions, revenue, Cut-offs coincide in all scenarios), lose out heuristics/hybrid and work in 10–15 slowly (200–420 against 16–70 s). It’s worth checking, degenerate a3 in a2 parameterically.
- **`balancer` :** Sustainable result (85 –99%), but in balanced mode loses more than others on limits (11,3%).

## Restrictions on running

Only PRECISE matching (fuzzy and parasitic limits do not apply) is considered as volume × CPM.
