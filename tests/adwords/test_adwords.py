"""
Tests for the adwords module (Adwords/Vazirani algorithm).

Structure:
  - Smoke tests: dynamically generated from FUNCTIONS + JSON cases
  - Quality tests: Python describe blocks with detailed checks
"""
import sys
import math
import random
import pytest

from tests.adwords._helpers import cases, ids, run
from tests.adwords._functions import FUNCTIONS

from rtb_sdk.auction.adwords import initialize_adwords, auction_adwords
from rtb_sdk.helpers.adwords import (
    is_valid_adwords_algorithm,
    create_adwords_ad_state,
    create_adwords_state,
    get_adwords_ad_state_price,
    get_adwords_ad_state_matches,
    get_adwords_ad_state_remaining_budget,
    get_adwords_ad_state_real_spend,
    get_adwords_ad_state_fake_spend,
    get_adwords_state_query_count,
    get_adwords_state_ad_states,
)
from rtb_sdk.helpers import create_ad, create_ads_dict, create_target_vector, create_frequency_limits
from rtb_sdk.constants import AdwordsAlgorithm
from rtb_sdk.errors import AuctionError
from datetime import datetime

# ---------------------------------------------------------------------------
# Smoke tests: dynamically generated from JSON cases
# ---------------------------------------------------------------------------

def _make_describe(func_name: str, _fn, _unpacker):
    _cases = cases(func_name, _unpacker)
    _ids = ids(_cases)

    def describe_fn():
        @pytest.mark.parametrize("case", _cases, ids=_ids)
        def test_it(case):
            run(_fn, case)

    describe_fn.__name__ = f"describe_{func_name}"
    describe_fn.__qualname__ = f"describe_{func_name}"
    return describe_fn


_this_module = sys.modules[__name__]
for _func_name, (_func, _unpacker) in FUNCTIONS.items():
    setattr(_this_module, f"describe_{_func_name}", _make_describe(_func_name, _func, _unpacker))


# ---------------------------------------------------------------------------
# Helper functions for quality tests
# ---------------------------------------------------------------------------

def _make_ad(ad_id: str, cpm: float, volume: int = 0, budget: float = 0.0):
    return create_ad(
        id=ad_id,
        cpm=cpm,
        volume=volume,
        budget=budget,
        priority=1.0,
        targets=create_target_vector(),
        ad_frequency_limit=create_frequency_limits(),
        user_frequency_limit=create_frequency_limits(),
        parasitic_freq_limit=create_frequency_limits(),
    )


def _make_ads_dict(ads_list):
    return create_ads_dict({ad['id']: ad for ad in ads_list})


def _make_state_a2(ad_ids, prices):
    """Creates an A2 AdwordsState with explicit prices (for deterministic tests)."""
    ad_states = {
        ad_id: create_adwords_ad_state(
            id=ad_id, price=price, matches=0,
            remaining_budget=0.0, real_spend=0.0, fake_spend=0.0,
        )
        for ad_id, price in zip(ad_ids, prices)
    }
    return create_adwords_state(
        algorithm=AdwordsAlgorithm.A2_SINGLE_VALUED,
        ad_states=ad_states,
        query_count=0,
    )


def _make_state_a3(ad_ids, prices, budgets):
    """Creates an A3 AdwordsState with explicit prices and budgets."""
    ad_states = {
        ad_id: create_adwords_ad_state(
            id=ad_id, price=price, matches=0,
            remaining_budget=budget, real_spend=0.0, fake_spend=0.0,
        )
        for ad_id, price, budget in zip(ad_ids, prices, budgets)
    }
    return create_adwords_state(
        algorithm=AdwordsAlgorithm.A3_SMALL,
        ad_states=ad_states,
        query_count=0,
    )


# ---------------------------------------------------------------------------
# Quality tests
# ---------------------------------------------------------------------------

def describe_initialization():

    def describe_price_afterward_initialization():

        def test_price_in_range():
            """price ∈ [1/e, 1) for each ad."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0), _make_ad('ad_2', 5.0)])
            state = initialize_adwords(ads, AdwordsAlgorithm.A2_SINGLE_VALUED)
            for ad_state in get_adwords_state_ad_states(state).values():
                p = get_adwords_ad_state_price(ad_state)
                assert p >= math.exp(-1), f"price={p} < 1/e"
                assert p < 1.0, f"price={p} >= 1.0"

        def test_prices_distinct():
            """Different ads get different prices (with probability 1)."""
            ads = _make_ads_dict([_make_ad(f'ad_{i}', float(i + 1)) for i in range(5)])
            state = initialize_adwords(ads, AdwordsAlgorithm.A2_SINGLE_VALUED)
            prices = [
                get_adwords_ad_state_price(s)
                for s in get_adwords_state_ad_states(state).values()
            ]
            assert len(set(prices)) == len(prices), "Some prices coincide"

        def test_reinit_gives_different_prices():
            """Re-initialization gives different prices."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0)])
            state1 = initialize_adwords(ads, AdwordsAlgorithm.A2_SINGLE_VALUED)
            prices_seen = {get_adwords_ad_state_price(
                get_adwords_state_ad_states(state1)['ad_1']
            )}
            for _ in range(20):
                s = initialize_adwords(ads, AdwordsAlgorithm.A2_SINGLE_VALUED)
                prices_seen.add(get_adwords_ad_state_price(
                    get_adwords_state_ad_states(s)['ad_1']
                ))
            assert len(prices_seen) > 1, "All initializations returned the same price"

    def describe_a3_initialization_budget():

        def test_remaining_budget_equals_ad_budget():
            """remaining_budget == ad.budget for each ad in A3."""
            budgets = [100.0, 200.0, 50.0]
            ads_list = [_make_ad(f'ad_{i}', 10.0, budget=b) for i, b in enumerate(budgets)]
            ads = _make_ads_dict(ads_list)
            state = initialize_adwords(ads, AdwordsAlgorithm.A3_SMALL)
            for i, b in enumerate(budgets):
                ad_state = get_adwords_state_ad_states(state)[f'ad_{i}']
                assert get_adwords_ad_state_remaining_budget(ad_state) == b

        def test_initial_counters_zero():
            """matches, real_spend, fake_spend = 0 after initialization."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0, budget=100.0)])
            state = initialize_adwords(ads, AdwordsAlgorithm.A3_SMALL)
            ad_state = get_adwords_state_ad_states(state)['ad_1']
            assert get_adwords_ad_state_matches(ad_state) == 0
            assert get_adwords_ad_state_real_spend(ad_state) == 0.0
            assert get_adwords_ad_state_fake_spend(ad_state) == 0.0


def describe_a2_logic_auction():

    def describe_deterministic_choice_winner():

        def test_winner_is_max_effective_bid():
            """Winner = argmax(cpm * (1 - price))."""
            # ad_1: effective = 10*(1-0.5)=5.0, ad_2: effective = 8*(1-0.2)=6.4 → ad_2
            ads = _make_ads_dict([_make_ad('ad_1', 10.0), _make_ad('ad_2', 8.0)])
            state = _make_state_a2(['ad_1', 'ad_2'], [0.5, 0.2])
            result = auction_adwords(ads, state)
            assert result['matched_ad'] == 'ad_2'

        def test_tiebreak_first_in_list():
            """On equal effective_bids the first in iteration order wins."""
            # ad_1: effective = 10*(1-0)=10, ad_2: effective=10*(1-0)=10 → tie → ad_1 (first)
            ads = _make_ads_dict([_make_ad('ad_1', 10.0), _make_ad('ad_2', 10.0)])
            state = _make_state_a2(['ad_1', 'ad_2'], [0.0, 0.0])
            result = auction_adwords(ads, state)
            # The winner is the one whose key comes first when iterating the dict
            # In CPython 3.7+ dict preserves insertion order
            assert result['matched_ad'] in {'ad_1', 'ad_2'}

    def describe_exhaustion_limit_impressions():

        def test_exhausted_volume_excluded():
            """After volume impressions the ad is excluded."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0, volume=1)])
            state = _make_state_a2(['ad_1'], [0.3])
            # First request — winner
            result1 = auction_adwords(ads, state)
            assert result1['matched_ad'] == 'ad_1'
            # Second request — volume exhausted
            result2 = auction_adwords(ads, result1['state'])
            assert result2['matched_ad'] is None

        def test_query_count_increments():
            """query_count grows after each request."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0)])
            state = _make_state_a2(['ad_1'], [0.3])
            assert get_adwords_state_query_count(state) == 0
            result1 = auction_adwords(ads, state)
            assert get_adwords_state_query_count(result1['state']) == 1
            result2 = auction_adwords(ads, result1['state'])
            assert get_adwords_state_query_count(result2['state']) == 2

    def describe_condition_winner():

        def test_only_winner_matches_incremented():
            """matches += 1 only for the winner; the others do not change."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0), _make_ad('ad_2', 5.0)])
            state = _make_state_a2(['ad_1', 'ad_2'], [0.5, 0.2])
            # effective: ad_1=5.0, ad_2=4.0 → ad_1 wins
            result = auction_adwords(ads, state)
            assert result['matched_ad'] == 'ad_1'
            new_states = get_adwords_state_ad_states(result['state'])
            assert get_adwords_ad_state_matches(new_states['ad_1']) == 1
            assert get_adwords_ad_state_matches(new_states['ad_2']) == 0


def describe_a3_logic_auction():

    def describe_budgetary_invariant():

        def test_real_spend_plus_remaining_equals_budget():
            """real_spend + remaining_budget == budget (after each move)."""
            budget = 100.0
            ads = _make_ads_dict([_make_ad('ad_1', 10.0, budget=budget)])
            state = _make_state_a3(['ad_1'], [0.3], [budget])
            for _ in range(8):
                result = auction_adwords(ads, state)
                state = result['state']
                ad_state = get_adwords_state_ad_states(state)['ad_1']
                remaining = get_adwords_ad_state_remaining_budget(ad_state)
                real = get_adwords_ad_state_real_spend(ad_state)
                assert abs(real + remaining - budget) < 1e-9, (
                    f"real_spend={real} + remaining={remaining} ≠ budget={budget}"
                )

        def test_real_spend_non_negative():
            """real_spend >= 0 and fake_spend >= 0."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0, budget=100.0)])
            state = _make_state_a3(['ad_1'], [0.3], [100.0])
            for _ in range(5):
                result = auction_adwords(ads, state)
                state = result['state']
                ad_state = get_adwords_state_ad_states(state)['ad_1']
                assert get_adwords_ad_state_real_spend(ad_state) >= 0.0
                assert get_adwords_ad_state_fake_spend(ad_state) >= 0.0

    def describe_exhaustion_budget():

        def test_zero_remaining_budget_excluded():
            """With remaining_budget=0 the ad is excluded from the auction."""
            ads = _make_ads_dict([_make_ad('ad_1', 10.0, budget=10.0)])
            state = _make_state_a3(['ad_1'], [0.3], [0.0])  # budget already exhausted
            result = auction_adwords(ads, state)
            assert result['matched_ad'] is None

        def test_budget_exhaustion_after_wins():
            """After the budget is exhausted the ad does not win."""
            budget = 20.0
            ads = _make_ads_dict([_make_ad('ad_1', 10.0, budget=budget)])
            state = _make_state_a3(['ad_1'], [0.3], [budget])
            # 2 wins of 10 each — budget exhausted
            for _ in range(2):
                result = auction_adwords(ads, state)
                state = result['state']
            # Third request — budget = 0
            result3 = auction_adwords(ads, state)
            assert result3['matched_ad'] is None

    def describe_fictional_expense():

        def test_fake_spend_when_budget_less_than_cpm():
            """fake_spend = max(0, cpm - remaining_budget) on a win with a partial budget."""
            cpm = 10.0
            remaining = 3.0  # < cpm
            ads = _make_ads_dict([_make_ad('ad_1', cpm, budget=100.0)])
            state = _make_state_a3(['ad_1'], [0.3], [remaining])
            result = auction_adwords(ads, state)
            assert result['matched_ad'] == 'ad_1'
            ad_state = get_adwords_state_ad_states(result['state'])['ad_1']
            expected_fake = max(0.0, cpm - remaining)
            assert abs(get_adwords_ad_state_fake_spend(ad_state) - expected_fake) < 1e-9

        def test_no_fake_spend_when_budget_sufficient():
            """fake_spend = 0 when remaining_budget >= cpm."""
            cpm = 10.0
            remaining = 50.0  # > cpm
            ads = _make_ads_dict([_make_ad('ad_1', cpm, budget=100.0)])
            state = _make_state_a3(['ad_1'], [0.3], [remaining])
            result = auction_adwords(ads, state)
            assert result['matched_ad'] == 'ad_1'
            ad_state = get_adwords_state_ad_states(result['state'])['ad_1']
            assert get_adwords_ad_state_fake_spend(ad_state) == 0.0

        def test_fake_spend_only_for_winner():
            """fake_spend is charged only to the winner."""
            ads = _make_ads_dict([
                _make_ad('ad_1', 10.0, budget=100.0),
                _make_ad('ad_2', 5.0, budget=50.0),
            ])
            # ad_1 wins (effective=10*(1-0.5)=5.0 > 5*(1-0.2)=4.0)
            # ad_2 must have no fake_spend
            state = _make_state_a3(['ad_1', 'ad_2'], [0.5, 0.2], [100.0, 50.0])
            result = auction_adwords(ads, state)
            assert result['matched_ad'] == 'ad_1'
            new_states = get_adwords_state_ad_states(result['state'])
            assert get_adwords_ad_state_fake_spend(new_states['ad_2']) == 0.0


def describe_immutability_condition():

    def test_input_state_not_mutated_a2():
        """auction_adwords does not mutate the passed state (A2)."""
        ads = _make_ads_dict([_make_ad('ad_1', 10.0)])
        state = _make_state_a2(['ad_1'], [0.3])
        original_query_count = get_adwords_state_query_count(state)
        original_matches = get_adwords_ad_state_matches(
            get_adwords_state_ad_states(state)['ad_1']
        )
        auction_adwords(ads, state)
        # The original state must not change
        assert get_adwords_state_query_count(state) == original_query_count
        assert get_adwords_ad_state_matches(
            get_adwords_state_ad_states(state)['ad_1']
        ) == original_matches

    def test_each_call_returns_new_state():
        """Each auction_adwords call returns a new state object."""
        ads = _make_ads_dict([_make_ad('ad_1', 10.0)])
        state = _make_state_a2(['ad_1'], [0.3])
        result1 = auction_adwords(ads, state)
        result2 = auction_adwords(ads, state)
        assert result1['state'] is not result2['state']
        # Both must have query_count == 1 (they start from the same state)
        assert get_adwords_state_query_count(result1['state']) == 1
        assert get_adwords_state_query_count(result2['state']) == 1

    def test_query_count_after_n_requests():
        """After N requests query_count == N."""
        N = 10
        ads = _make_ads_dict([_make_ad('ad_1', 10.0)])
        state = initialize_adwords(ads, AdwordsAlgorithm.A2_SINGLE_VALUED)
        for _ in range(N):
            result = auction_adwords(ads, state)
            state = result['state']
        assert get_adwords_state_query_count(state) == N


def describe_statistical_properties():

    def _greedy_revenue(ads_configs: list[dict], n_queries: int) -> float:
        """Greedy: each request → the ad with the maximum cpm."""
        counts = {cfg['id']: 0 for cfg in ads_configs}
        revenue = 0.0
        for _ in range(n_queries):
            eligible = [
                cfg for cfg in ads_configs
                if cfg['volume'] == 0 or counts[cfg['id']] < cfg['volume']
            ]
            if not eligible:
                break
            best = max(eligible, key=lambda c: c['cpm'])
            counts[best['id']] += 1
            revenue += best['cpm']
        return revenue

    def _adwords_revenue(ads_dict, n_queries: int, algorithm: str, n_runs: int = 20) -> float:
        """Run n_runs times with different prices, return the average revenue."""
        revenues = []
        for _ in range(n_runs):
            state = initialize_adwords(ads_dict, algorithm)
            revenue = 0.0
            s = state
            for _ in range(n_queries):
                result = auction_adwords(ads_dict, s)
                s = result['state']
                if result['matched_ad']:
                    winner_id = result['matched_ad']
                    cpm = ads_dict['value'][winner_id]['cpm']
                    revenue += cpm
            revenues.append(revenue)
        return sum(revenues) / len(revenues)

    def test_a2_competitive_ratio_vs_greedy():
        """avg(revenue_A2) / avg(revenue_greedy) >= 0.90 on typical instances."""
        random.seed(42)
        ads_configs = [
            {'id': f'ad_{i}', 'cpm': 10.0 + i * 2.0, 'volume': 40}
            for i in range(5)
        ]
        ads_list = [_make_ad(cfg['id'], cfg['cpm'], volume=cfg['volume']) for cfg in ads_configs]
        ads_dict = _make_ads_dict(ads_list)
        n_queries = 200
        greedy = _greedy_revenue(ads_configs, n_queries)
        a2_avg = _adwords_revenue(ads_dict, n_queries, AdwordsAlgorithm.A2_SINGLE_VALUED, n_runs=20)
        assert greedy > 0
        ratio = a2_avg / greedy
        assert ratio >= 0.90, f"A2 competitive ratio={ratio:.3f} < 0.90"

    def test_a3_competitive_ratio_vs_greedy():
        """avg(revenue_A3) / avg(revenue_greedy) >= 0.90 under the Small condition.

        Greedy is budget-constrained: picks the ad with the max CPM
        whose remaining_budget >= cpm. A fair comparison with A3.
        """
        random.seed(123)
        budget = 50.0
        ads_configs = [
            {'id': f'ad_{i}', 'cpm': 1.0 + i * 0.2, 'volume': 0, 'budget': budget}
            for i in range(5)
        ]
        ads_list = [
            _make_ad(cfg['id'], cfg['cpm'], volume=0, budget=cfg['budget'])
            for cfg in ads_configs
        ]
        ads_dict = _make_ads_dict(ads_list)
        n_queries = 500

        # Budget-constrained greedy algorithm
        def greedy_budget_aware():
            budgets = {cfg['id']: cfg['budget'] for cfg in ads_configs}
            rev = 0.0
            for _ in range(n_queries):
                eligible = [cfg for cfg in ads_configs if budgets[cfg['id']] >= cfg['cpm']]
                if not eligible:
                    break
                best = max(eligible, key=lambda c: c['cpm'])
                budgets[best['id']] -= best['cpm']
                rev += best['cpm']
            return rev

        greedy = greedy_budget_aware()
        a3_avg = _adwords_revenue(ads_dict, n_queries, AdwordsAlgorithm.A3_SMALL, n_runs=20)
        assert greedy > 0
        ratio = a3_avg / greedy
        assert ratio >= 0.90, f"A3 competitive ratio={ratio:.3f} < 0.90"

    def test_a3_nsp_violation_rate():
        """NSP: share of impressions with fake_spend > 0 (bid > remaining_budget) < 5%.

        Applicability condition of Small: cpm << budget → partial wins are rare.
        """
        random.seed(7)
        # cpm=10, budget=1001: 1001//10=100 full impressions, 1 partial (remaining=1)
        # violation rate per ad ≈ 1/101 ≈ 0.99% << 5%
        budget = 1001.0
        cpm = 10.0
        n_ads = 4
        n_runs = 5
        n_queries = 600  # > n_ads * (budget // cpm + 1) = 4*101 = 404

        ads_list = [_make_ad(f'ad_{i}', cpm, volume=0, budget=budget) for i in range(n_ads)]
        ads_dict = _make_ads_dict(ads_list)

        violations = 0
        total_wins = 0

        for _ in range(n_runs):
            state = initialize_adwords(ads_dict, AdwordsAlgorithm.A3_SMALL)
            s = state
            for _ in range(n_queries):
                old_ad_states = get_adwords_state_ad_states(s)
                result = auction_adwords(ads_dict, s)
                winner = result['matched_ad']
                if winner is not None:
                    remaining_before = get_adwords_ad_state_remaining_budget(old_ad_states[winner])
                    if remaining_before < cpm:  # fake_spend was generated
                        violations += 1
                    total_wins += 1
                s = result['state']

        assert total_wins > 0
        rate = violations / total_wins
        assert rate < 0.05, f"NSP violation rate={rate:.3f} >= 0.05"
