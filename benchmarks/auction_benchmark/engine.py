"""
Auction benchmark engine.

Two modes:
  - Classic strategies (best_one, best_price, best_velocity, best_heuristics,
    best_hybrid/random_hybrid and their random variants): 1 run, deterministic
    or with a fixed seed. The winner selection logic is implemented directly without
    calling the SDK auction(), which gives a ~10× speedup and makes it possible to process
    10M requests.

  - Adwords (a2_single_valued, a3_small): N runs with different random
    initialization prices. The SDK functions initialize_adwords /
    auction_adwords are used. For each run the requests are identical, only the
    weight initialization changes.

Balancer (balancer): first the SDK functions balance_traffic +
  convert_report_to_auction_data build the planned traffic distribution
  (objective=maximize_money, total_traffic_volume = the scenario's number of requests),
  then for each request the balancer's auction formula is applied
  (weight = distribution[ad] * P(request) / P(ad)). The weight depends only on the
  tag combination and the candidate set, so it is computed once per
  combination. The result goes into the classic tables under the name "balancer".

Both modes use a precomputed match table:
  combo_idx → [ad_id, ...]  (which ads fit a given tag combination).
Requests are represented as an array of combination indices (numpy), which avoids
recomputing the matching in the hot loop.

Simplifications (recorded in the report):
  - Tag filtering: only precise match (per each vocab constraint).
  - User frequency limits and min_interval are not applied.
  - For the classic velocity/heuristics strategies the monthly counter =
    the total number of impressions since the start of the simulation (the whole run counts as 1 month).
"""
from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .seeds import VOCABS, TAG_WEIGHTS


# ─── Result types ───────────────────────────────────────────────────────

@dataclass
class SingleRunResult:
    """Result of a single run (classic or one adwords run)."""
    total_impressions: int
    total_revenue: float
    total_requests: int
    misses: int
    per_ad_impressions: dict[str, int]
    per_ad_volume: dict[str, int]

    @property
    def fill_rate(self) -> float:
        return (self.total_impressions / self.total_requests) if self.total_requests else 0.0

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.fill_rate

    @property
    def avg_cpm_per_hit(self) -> float:
        return (self.total_revenue / self.total_impressions) if self.total_impressions else 0.0


@dataclass
class MultiRunStats:
    """Statistics of N runs (for adwords)."""
    algorithm: str
    n_runs: int
    impressions_min: int
    impressions_max: int
    impressions_mean: float
    impressions_median: float
    revenue_min: float
    revenue_max: float
    revenue_mean: float
    revenue_median: float
    fill_rate_min: float
    fill_rate_max: float
    fill_rate_mean: float
    fill_rate_median: float
    per_run_results: list[SingleRunResult] = field(default_factory=list, repr=False)


# ─── Precomputations ────────────────────────────────────────────────

def build_combo_index(
    vocabs: dict[str, list[str]] = VOCABS,
    tag_weights: dict[str, dict[str, float]] = TAG_WEIGHTS,
) -> tuple[list[tuple], np.ndarray]:
    """Enumerates all possible request tag combinations.

    Returns:
        combos:       list of (city, age, gender, device, interest) — raw tags
        combo_probs:  np.array of probabilities of each combination
    """
    vocab_order = ["City", "Age", "Gender", "Device", "Interest"]
    tag_lists = [vocabs[v] for v in vocab_order]
    weight_lists = [
        [tag_weights[v][t] for t in vocabs[v]]
        for v in vocab_order
    ]

    combos = list(
        (city, age, gender, device, interest)
        for city, age, gender, device, interest
        in __import__("itertools").product(*tag_lists)
    )

    # Probability of a combination = product of the weights of the individual tags
    probs = np.array([
        math.prod(weight_lists[vi][tag_lists[vi].index(combo[vi])] for vi in range(5))
        for combo in combos
    ])
    probs /= probs.sum()  # normalization in case of rounding errors
    return combos, probs


def precompute_matching(
    ad_data: dict[str, dict],
    combos: list[tuple],
) -> dict[int, list[str]]:
    """For each tag combination builds a list of matching ad_ids.

    Precise match: for each vocab constraint of the campaign the request tag
    must belong to the campaign's set of raw tags.

    Returns:
        {combo_idx: [ad_id, ...]}  (may be empty)
    """
    vocab_order = ["City", "Age", "Gender", "Device", "Interest"]
    # Convert targets to frozenset for fast lookup
    ad_tag_sets: dict[str, dict[str, frozenset]] = {
        ad_id: {
            vocab: frozenset(raw_tags)
            for vocab, raw_tags in data["targets"].items()
        }
        for ad_id, data in ad_data.items()
    }

    result: dict[int, list[str]] = {}
    for idx, combo in enumerate(combos):
        combo_dict = dict(zip(vocab_order, combo))
        matching = []
        for ad_id, vocab_sets in ad_tag_sets.items():
            ok = True
            for vocab, allowed in vocab_sets.items():
                if combo_dict.get(vocab) not in allowed:
                    ok = False
                    break
            if ok:
                matching.append(ad_id)
        result[idx] = matching
    return result


def generate_request_sequence(
    n: int,
    combo_probs: np.ndarray,
    seed: int = 42,
) -> np.ndarray:
    """Generates a sequence of n requests as an array of combo_idx.

    The same seed → the same request stream for all algorithms.
    """
    rng = np.random.default_rng(seed)
    return rng.choice(len(combo_probs), size=n, p=combo_probs)


# ─── Classic strategies (fast implementation without SDK overhead) ───────────

def _select_winner(
    strategy: str,
    candidates: list[str],
    ad_data: dict[str, dict],
    impressions: dict[str, int],
) -> Optional[str]:
    """Picks the auction winner among candidates by the given strategy.

    Implements the same logic as the SDK auction(), but without the overhead
    of creating TypedDict objects and validation in the hot loop.
    """
    if not candidates:
        return None

    if strategy == "best_one":
        return candidates[0]

    if strategy == "random_one":
        return random.choice(candidates)

    if strategy == "best_price":
        return max(candidates, key=lambda aid: ad_data[aid]["cpm"])

    if strategy == "random_price":
        cpms = [ad_data[aid]["cpm"] for aid in candidates]
        max_cpm = max(cpms)
        weights = [c / max_cpm + 1e-9 for c in cpms]
        return random.choices(candidates, weights=weights, k=1)[0]

    is_hybrid = strategy.startswith(("best_hybrid_", "random_hybrid_"))

    if strategy in ("best_velocity", "random_velocity",
                    "best_heuristics", "random_heuristics") or is_hybrid:
        # velocity_factor = (month_limit - current) / month_limit
        # month_limit = ad volume (with DATE_ZERO..DATE_INFINITY and zero freq limits)
        volumes = [ad_data[aid]["volume"] for aid in candidates]
        max_vol = max(volumes)

        vel = {}
        for aid, vol in zip(candidates, volumes):
            cur = impressions[aid]
            if vol <= 0:
                vel[aid] = (max_vol - cur) / max_vol if max_vol > 0 else 1.0
            else:
                vel[aid] = (vol - cur) / vol

        if strategy == "best_velocity":
            return max(candidates, key=lambda aid: vel[aid])

        if strategy == "random_velocity":
            weights = [vel[aid] + 1e-9 for aid in candidates]
            return random.choices(candidates, weights=weights, k=1)[0]

        # best_hybrid_<threshold>: if at least one candidate has not reached
        # velocity_threshold in plan fulfillment (1 - vel) — best_velocity,
        # otherwise — best_price.
        if strategy.startswith("best_hybrid_"):
            velocity_threshold = float(strategy[len("best_hybrid_"):])
            if any(1 - vel[aid] < velocity_threshold for aid in candidates):
                return max(candidates, key=lambda aid: vel[aid])
            return max(candidates, key=lambda aid: ad_data[aid]["cpm"])

        # random_hybrid_<price_probability>: with probability price_probability —
        # best_price, otherwise — best_velocity.
        if strategy.startswith("random_hybrid_"):
            price_probability = float(strategy[len("random_hybrid_"):])
            if random.random() < price_probability:
                return max(candidates, key=lambda aid: ad_data[aid]["cpm"])
            return max(candidates, key=lambda aid: vel[aid])

        # heuristics
        max_cpm = max(ad_data[aid]["cpm"] for aid in candidates)
        max_pri = max(ad_data[aid]["priority"] for aid in candidates)
        scores = {}
        for aid in candidates:
            pf = ad_data[aid]["cpm"] / max_cpm if max_cpm > 0 else 0.0
            rf = ad_data[aid]["priority"] / max_pri if max_pri > 0 else 0.0
            vf = vel[aid]
            scores[aid] = pf * rf * vf

        if strategy == "best_heuristics":
            return max(candidates, key=lambda aid: scores[aid])

        # random_heuristics
        weights = [scores[aid] + 1e-9 for aid in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    return None  # unknown strategy


def run_classic(
    strategy: str,
    ad_data: dict[str, dict],
    combo_to_matching: dict[int, list[str]],
    request_seq: np.ndarray,
    seed: int = 0,
) -> SingleRunResult:
    """Runs a classic strategy over the whole request stream.

    Applies a volume constraint: as soon as an ad accumulates volume
    impressions — it is excluded from the pool (analogous to how A2 checks matches).
    """
    random.seed(seed)

    impressions = {aid: 0 for aid in ad_data}
    revenue = 0.0
    misses = 0
    active: set[str] = set(ad_data.keys())

    for combo_idx in request_seq:
        raw_candidates = combo_to_matching[int(combo_idx)]
        # Filter by active ones (those that have not exhausted volume)
        candidates = [aid for aid in raw_candidates if aid in active]

        if not candidates:
            misses += 1
            continue

        winner = _select_winner(strategy, candidates, ad_data, impressions)

        if winner is None:
            misses += 1
            continue

        impressions[winner] += 1
        revenue += ad_data[winner]["cpm"]

        vol = ad_data[winner]["volume"]
        if vol > 0 and impressions[winner] >= vol:
            active.discard(winner)

    return SingleRunResult(
        total_impressions=sum(impressions.values()),
        total_revenue=revenue,
        total_requests=len(request_seq),
        misses=misses,
        per_ad_impressions=dict(impressions),
        per_ad_volume={aid: ad_data[aid]["volume"] for aid in ad_data},
    )


# ─── Balancer (balance_traffic + balancer auction) ─────────────────────

BALANCER_STRATEGY = "balancer"


def _build_balancer_weights(
    ad_data: dict[str, dict],
    combos: list[tuple],
    combo_to_matching: dict[int, list[str]],
    n_requests: int,
    vocabs: dict[str, list[str]] = VOCABS,
    tag_weights: dict[str, dict[str, float]] = TAG_WEIGHTS,
) -> tuple[dict[int, dict[str, float]], int]:
    """Balancing + precomputing the balancer auction weights.

    Returns:
        weights:  {combo_idx: {ad_id: weight}} — only for matching ads;
        planned:  total impression plan from the balance_traffic report.
    """
    from rtb_sdk.balancer import balance_traffic, convert_report_to_auction_data
    from rtb_sdk.helpers.balancer.optimize_params_helpers import create_balancing_params
    from rtb_sdk.constants.tag_constants import TAG_EMPTY, TAG_OTHER

    typed_ads, _ = _build_typed_ads(ad_data)
    params = create_balancing_params(
        total_traffic_volume=n_requests,
        tag_probabilities_outer=tag_weights,
        vocabs_outer=vocabs,
        objective="maximize_money",
    )
    report = balance_traffic(typed_ads, params)
    bd = convert_report_to_auction_data(typed_ads, report, params)

    narrow_vocabs = bd["vocabs"]
    tag_probs = bd["tag_probabilities"]
    distribution = bd["ads_distribution"]
    ad_probs = bd["ads_probabilities"]

    vocab_order = ["City", "Age", "Gender", "Device", "Interest"]
    weights: dict[int, dict[str, float]] = {}
    for idx, combo in enumerate(combos):
        matching = combo_to_matching[idx]
        if not matching:
            continue
        request = dict(zip(vocab_order, combo))
        req_prob = 1.0
        for vocab_name in narrow_vocabs:
            raw_tag = request.get(vocab_name, TAG_EMPTY)
            vp = tag_probs.get(vocab_name, {})
            req_prob *= vp.get(raw_tag, vp.get(TAG_OTHER, 0.0))
        w = {}
        for aid in matching:
            ap = ad_probs.get(aid, 1.0)
            w[aid] = distribution.get(aid, 0) * req_prob / ap if ap > 0 else 0.0
        weights[idx] = w
    return weights, sum(report.values())


def run_balancer(
    ad_data: dict[str, dict],
    combos: list[tuple],
    combo_to_matching: dict[int, list[str]],
    request_seq: np.ndarray,
    seed: int = 0,
) -> SingleRunResult:
    """Balancer run: balance_traffic → balancer auction.

    As in run_classic, an ad that has exhausted volume leaves the pool.
    A request without a nonzero total candidate weight is a miss (like None
    in the SDK balancer auction).
    """
    random.seed(seed)
    weights, _ = _build_balancer_weights(
        ad_data, combos, combo_to_matching, len(request_seq),
    )

    impressions = {aid: 0 for aid in ad_data}
    revenue = 0.0
    misses = 0
    active: set[str] = set(ad_data.keys())

    for combo_idx in request_seq:
        w = weights.get(int(combo_idx))
        if not w:
            misses += 1
            continue
        cand = [aid for aid in w if aid in active]
        cw = [w[aid] for aid in cand]
        if not cand or sum(cw) <= 0:
            misses += 1
            continue
        winner = random.choices(cand, weights=cw, k=1)[0]

        impressions[winner] += 1
        revenue += ad_data[winner]["cpm"]
        vol = ad_data[winner]["volume"]
        if vol > 0 and impressions[winner] >= vol:
            active.discard(winner)

    return SingleRunResult(
        total_impressions=sum(impressions.values()),
        total_revenue=revenue,
        total_requests=len(request_seq),
        misses=misses,
        per_ad_impressions=dict(impressions),
        per_ad_volume={aid: ad_data[aid]["volume"] for aid in ad_data},
    )


# ─── Adwords (A2/A3) — via SDK ───────────────────────────────────────────

def _build_typed_ads(ad_data: dict[str, dict]):
    """Creates typed Ad objects and an AdsDict for the SDK adwords."""
    from rtb_sdk.helpers.auction import (
        create_ad, create_ads_dict, create_target_vector, create_frequency_limits,
    )
    from rtb_sdk.constants import DATE_ZERO, DATE_INFINITY

    ads = {}
    for ad_id, data in ad_data.items():
        tv = create_target_vector(data["targets"])
        ad = create_ad(
            id=ad_id,
            targets=tv,
            cpm=data["cpm"],
            priority=data["priority"],
            volume=data["volume"],
            budget=data["budget"],
            start_date=DATE_ZERO,
            end_date=DATE_INFINITY,
        )
        ads[ad_id] = ad
    return ads, create_ads_dict(ads)


def _build_subset_ads_dicts(
    all_typed_ads: dict,
    unique_subsets: set[frozenset],
) -> dict[frozenset, object]:
    """Precomputes an AdsDict for each unique subset of ad_ids."""
    from rtb_sdk.helpers.auction import create_ads_dict
    result = {}
    for subset in unique_subsets:
        subset_ads = {aid: all_typed_ads[aid] for aid in subset}
        result[subset] = create_ads_dict(subset_ads)
    return result


def _run_adwords_single(
    algorithm: str,
    full_ads_dict,
    subset_ads_dicts: dict[frozenset, object],
    combo_to_matching: dict[int, list[str]],
    request_seq: np.ndarray,
    ad_data: dict[str, dict],
) -> SingleRunResult:
    """One adwords run (a fresh weight initialization)."""
    from rtb_sdk.auction.adwords.adwords import initialize_adwords, auction_adwords
    from rtb_sdk.helpers.auction import create_ads_dict

    state = initialize_adwords(full_ads_dict, algorithm)

    impressions = {aid: 0 for aid in ad_data}
    revenue = 0.0
    misses = 0

    empty_ads = create_ads_dict({})

    for combo_idx in request_seq:
        raw_matching = combo_to_matching[int(combo_idx)]

        if not raw_matching:
            # No matches — MISS without calling the algorithm
            misses += 1
            continue

        subset_key = frozenset(raw_matching)
        ads_dict = subset_ads_dicts.get(subset_key, empty_ads)

        result = auction_adwords(ads_dict, state)
        state = result["state"]

        winner_id = result["matched_ad"]
        if winner_id is not None:
            impressions[winner_id] += 1
            revenue += ad_data[winner_id]["cpm"]
        else:
            misses += 1

    return SingleRunResult(
        total_impressions=sum(impressions.values()),
        total_revenue=revenue,
        total_requests=len(request_seq),
        misses=misses,
        per_ad_impressions=dict(impressions),
        per_ad_volume={aid: ad_data[aid]["volume"] for aid in ad_data},
    )


def run_adwords_multi(
    algorithm: str,
    ad_data: dict[str, dict],
    combo_to_matching: dict[int, list[str]],
    request_seq: np.ndarray,
    n_runs: int,
    progress_cb=None,
) -> MultiRunStats:
    """N adwords runs with different random initializations.

    Args:
        algorithm:    'a2_single_valued' | 'a3_small'
        ad_data:      dictionary of ad parameters
        combo_to_matching: precomputed match table
        request_seq:  the same request stream for all runs
        n_runs:       number of runs
        progress_cb:  callable(run_idx, total) for the progress indicator

    Returns:
        MultiRunStats with min/max/mean/median over all runs
    """
    all_typed_ads, full_ads_dict = _build_typed_ads(ad_data)

    # Precompute an AdsDict for all unique subsets
    unique_subsets: set[frozenset] = {
        frozenset(combo_to_matching[int(idx)])
        for idx in set(request_seq)
        if combo_to_matching[int(idx)]
    }
    subset_ads_dicts = _build_subset_ads_dicts(all_typed_ads, unique_subsets)

    per_run: list[SingleRunResult] = []
    for i in range(n_runs):
        r = _run_adwords_single(
            algorithm, full_ads_dict, subset_ads_dicts,
            combo_to_matching, request_seq, ad_data,
        )
        per_run.append(r)
        if progress_cb:
            progress_cb(i + 1, n_runs)

    imp_arr  = np.array([r.total_impressions for r in per_run], dtype=float)
    rev_arr  = np.array([r.total_revenue     for r in per_run])
    fill_arr = np.array([r.fill_rate         for r in per_run])

    return MultiRunStats(
        algorithm=algorithm,
        n_runs=n_runs,
        impressions_min=int(imp_arr.min()),
        impressions_max=int(imp_arr.max()),
        impressions_mean=float(imp_arr.mean()),
        impressions_median=float(np.median(imp_arr)),
        revenue_min=float(rev_arr.min()),
        revenue_max=float(rev_arr.max()),
        revenue_mean=float(rev_arr.mean()),
        revenue_median=float(np.median(rev_arr)),
        fill_rate_min=float(fill_arr.min()),
        fill_rate_max=float(fill_arr.max()),
        fill_rate_mean=float(fill_arr.mean()),
        fill_rate_median=float(np.median(fill_arr)),
        per_run_results=per_run,
    )


# ─── Orchestrating a single scenario ───────────────────────────────────────────

def run_scenario(
    ad_data: dict[str, dict],
    n_requests: int,
    classic_strategies: list[str],
    adwords_algorithms: list[str],
    adwords_runs: int,
    request_seed: int = 42,
    classic_seed: int = 0,
    progress_cb=None,
    with_balancer: bool = True,
) -> dict:
    """Runs all algorithms on a single scenario.

    Returns dict:
        {
          'combos':           list[tuple],
          'request_seq':      np.ndarray,
          'combo_to_matching': dict,
          'classic': {strategy: SingleRunResult},
          'adwords': {algorithm: MultiRunStats},
        }
    """
    combos, combo_probs = build_combo_index()
    request_seq = generate_request_sequence(n_requests, combo_probs, seed=request_seed)
    combo_to_matching = precompute_matching(ad_data, combos)

    classic_results: dict[str, SingleRunResult] = {}
    for strat in classic_strategies:
        classic_results[strat] = run_classic(
            strat, ad_data, combo_to_matching, request_seq, seed=classic_seed,
        )

    if with_balancer:
        classic_results[BALANCER_STRATEGY] = run_balancer(
            ad_data, combos, combo_to_matching, request_seq, seed=classic_seed,
        )

    adwords_results: dict[str, MultiRunStats] = {}
    for algo in adwords_algorithms:
        # Create a separate callback for each algorithm (resets the ETA timer)
        algo_cb = progress_cb(algo) if callable(progress_cb) else progress_cb
        adwords_results[algo] = run_adwords_multi(
            algo, ad_data, combo_to_matching, request_seq,
            n_runs=adwords_runs, progress_cb=algo_cb,
        )

    return {
        "combos": combos,
        "request_seq": request_seq,
        "combo_to_matching": combo_to_matching,
        "classic": classic_results,
        "adwords": adwords_results,
    }
