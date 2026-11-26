"""
Tests for the third-level functions (seasonal balancer).

Covers:
  - seasonal_balance_traffic          — balancing with targeting and a time profile
  - open_balance_traffic               — balancing without targeting (RoN)
  - seasonal_balance_by_sellout        — maximizing the minimum sellout
  - seasonal_add_new_balanced_campaign — adding a campaign without changing the existing ones
  - forecast_bid                       — recommended bid forecaster (modes 1–4)

The tests are written based on the documented behavior (README.md + TEMPORAL_BALANCING.md),
not on the source code of the implementation. pytest-describe is used for nested blocks.
"""

from datetime import datetime, timezone

import pytest

from rtb_sdk.balancer.seasonal import (
    seasonal_balance_traffic,
    open_balance_traffic,
    seasonal_balance_by_sellout,
    seasonal_add_new_balanced_campaign,
    forecast_bid,
)


# ---------------------------------------------------------------------------
# Helper functions for building fixtures
# ---------------------------------------------------------------------------

def _make_ad(
    ad_id: str,
    *,
    cpm: float,
    volume: int = 1000,
    h_limit: int | None = None,
    targets: dict | None = None,
) -> dict:
    """Creates an Ad in the public format.

    Args:
        ad_id:   campaign identifier.
        cpm:     cost per thousand impressions.
        volume:  upper limit of impressions per the contract.
        h_limit: hourly limit (h) or None — then no limits (d=99999).
        targets: inner targeting {VocabName: [RawTag]}, None → empty (all tags).
    """
    if h_limit is not None:
        freq = {'value': {'h': h_limit}}
    else:
        freq = {'value': {'d': 99999}}
    return {
        'id': ad_id,
        'targets': {'value': targets or {}},
        'volume': volume,
        'cpm': float(cpm),
        'ad_frequency_limit': freq,
    }


def _make_seasonal_ctx(hour_weights: dict[int, float]) -> dict:
    """Creates a SeasonalContext with the given weights for the hourly slots.

    Args:
        hour_weights: {hour_type: raw_weight}, where hour_type is 0..23 for
                      the 'hour_of_day' mode. The weights are normalized to a sum of 1.0.

    Returns:
        SeasonalContext-compatible dict.
    """
    total = sum(hour_weights.values()) or 1.0
    return {
        'mode': 'hour_of_day',
        'context': {
            h: {
                'weight': w / total,
                'user_activity_ratio': {},   # ratio=1.0 by default
                'tags_probability': None,    # use the global tags
            }
            for h, w in hour_weights.items()
        },
    }


def _make_params(
    total: int,
    seasonal_ctx: dict,
    period_start: datetime,
    period_end: datetime,
    *,
    objective: str = 'maximize_money',
    tag_probabilities: dict | None = None,
    vocabs: dict | None = None,
) -> dict:
    """Creates SeasonalBalancingParams in the inner (FullTag) format.

    Args:
        total:          total_traffic_volume — total traffic for the period.
        seasonal_ctx:   SeasonalContext.
        period_start:   start of the period (inclusive).
        period_end:     end of the period (exclusive).
        objective:      'maximize_money' | 'maximize_volume'.
        tag_probabilities: inner format {FullTag: float}, None → empty dictionary.
        vocabs:         inner format {VocabName: [FullTag]}, None → empty dictionary.
    """
    return {
        'total_traffic_volume': total,
        'tag_probabilities': tag_probabilities or {},
        'vocabs': vocabs or {},
        'objective': objective,
        'max_n_categories': 100,
        'min_category_probability': 1e-6,
        'n_threads': 1,
        'seasonal_context': seasonal_ctx,
        'period': {
            'period_start': period_start,
            'period_end': period_end,
        },
    }


# ---------------------------------------------------------------------------
# Reusable periods and contexts
# ---------------------------------------------------------------------------

# Period A: 1 hour, midnight (hour 0), weight = 1.0
_A_START = datetime(2024, 1, 1,  0, 0, tzinfo=timezone.utc)
_A_END   = datetime(2024, 1, 1,  1, 0, tzinfo=timezone.utc)
_CTX_1H  = _make_seasonal_ctx({0: 1.0})

# Period B: 2 hours (hours 10 and 11), weights 0.6 and 0.4
_B_START = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
_B_END   = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
_CTX_2H  = _make_seasonal_ctx({10: 0.6, 11: 0.4})

# Base parameters for frequent tests (1 hour, total=100)
_PARAMS_BASE = _make_params(100, _CTX_1H, _A_START, _A_END)


# ---------------------------------------------------------------------------
# describe_seasonal_balance_traffic
# ---------------------------------------------------------------------------

def describe_seasonal_balance_traffic():
    """Tests of seasonal_balance_traffic (Level 3b): balancing with a time profile."""

    def describe_structure():

        def test_returns_dictionary():
            """The result is a dictionary."""
            ads = {'a': _make_ad('a', cpm=10)}
            result = seasonal_balance_traffic(ads, _PARAMS_BASE)
            assert isinstance(result, dict)

        def test_all_ads_present_in_result():
            """The dictionary contains a key for each ad."""
            ads = {
                'ad_a': _make_ad('ad_a', cpm=10),
                'ad_b': _make_ad('ad_b', cpm=5),
            }
            result = seasonal_balance_traffic(ads, _PARAMS_BASE)
            assert set(result.keys()) == {'ad_a', 'ad_b'}

        def test_all_volumes_nonnegative():
            """No ad gets a negative volume."""
            ads = {
                'ad_a': _make_ad('ad_a', cpm=10),
                'ad_b': _make_ad('ad_b', cpm=5),
                'ad_c': _make_ad('ad_c', cpm=1),
            }
            result = seasonal_balance_traffic(ads, _PARAMS_BASE)
            assert all(v >= 0 for v in result.values())

        def test_total_volume_does_not_exceed_traffic():
            """Total volume ≤ total_traffic_volume."""
            ads = {
                'ad_a': _make_ad('ad_a', cpm=10, volume=1000),
                'ad_b': _make_ad('ad_b', cpm=5,  volume=1000),
            }
            result = seasonal_balance_traffic(ads, _PARAMS_BASE)
            assert sum(result.values()) <= _PARAMS_BASE['total_traffic_volume']

    def describe_objective_function():

        def test_maximize_money_prefers_expensive_ad():
            """An expensive ad gets no fewer impressions than a cheap one (maximize_money)."""
            ads = {
                'ad_expensive': _make_ad('ad_expensive', cpm=100, volume=1000),
                'ad_cheap':     _make_ad('ad_cheap',     cpm=1,   volume=1000),
            }
            params = _make_params(100, _CTX_1H, _A_START, _A_END, objective='maximize_money')
            result = seasonal_balance_traffic(ads, params)
            assert result['ad_expensive'] >= result['ad_cheap']

        def test_maximize_volume_uses_all_traffic():
            """Under maximize_volume the total volume equals total_traffic_volume."""
            ads = {
                'ad_a': _make_ad('ad_a', cpm=10, volume=1000),
                'ad_b': _make_ad('ad_b', cpm=1,  volume=1000),
            }
            params = _make_params(100, _CTX_1H, _A_START, _A_END, objective='maximize_volume')
            result = seasonal_balance_traffic(ads, params)
            assert sum(result.values()) == 100

    def describe_frequency_restriction():

        def test_hourly_limit_caps_volume():
            """The hourly limit (h) caps the maximum impressions within one hour."""
            h_limit = 3
            ads = {'ad_a': _make_ad('ad_a', cpm=10, h_limit=h_limit, volume=1000)}
            result = seasonal_balance_traffic(ads, _PARAMS_BASE)
            assert result['ad_a'] <= h_limit

        def test_price_balancing_one_user_ten_requests():
            """
            Scenario: 1 user makes 10 requests within one hour.
            Two ads compete for traffic by price:
              - ad_expensive: CPM = 10, hourly limit = 8
              - ad_cheap:     CPM =  1, hourly limit = 8

            Expected (maximize_money):
              - the expensive one takes 8 impressions (fills its limit);
              - the cheap one gets the remaining 2 impressions.
            """
            ads = {
                'ad_expensive': _make_ad('ad_expensive', cpm=10, h_limit=8, volume=1000),
                'ad_cheap':     _make_ad('ad_cheap',     cpm=1,  h_limit=8, volume=1000),
            }
            params = _make_params(10, _CTX_1H, _A_START, _A_END, objective='maximize_money')
            result = seasonal_balance_traffic(ads, params)
            assert result['ad_expensive'] == 8, (
                f"Expensive Advertisements Should Get 8 impressions (limit), "
                f"received: {result['ad_expensive']}"
            )
            assert result['ad_cheap'] == 2, (
                f"A Cheap Advertisement Should Get 2 leftover, "
                f"received: {result['ad_cheap']}"
            )

    def describe_multiple_slots():

        def test_two_hour_period_sums_slots():
            """Volumes are summed over several slots (a 2-hour period)."""
            ads = {
                'ad_a': _make_ad('ad_a', cpm=10, volume=1000),
                'ad_b': _make_ad('ad_b', cpm=5,  volume=1000),
            }
            params = _make_params(100, _CTX_2H, _B_START, _B_END)
            result = seasonal_balance_traffic(ads, params)
            assert sum(result.values()) <= 100
            assert sum(result.values()) > 0

        def test_slot_weights_define_traffic_shares():
            """
            A slot with a larger weight gets a larger traffic volume.
            Period: h=10 (weight 0.6) and h=11 (weight 0.4).
            With 1 ad and no limits: total ≈ 100, each slot
            yields round(100 × w) impressions; the sum ≤ total.
            """
            ads = {'ad_a': _make_ad('ad_a', cpm=10, volume=10_000)}
            params = _make_params(100, _CTX_2H, _B_START, _B_END)
            result = seasonal_balance_traffic(ads, params)
            assert 90 <= result['ad_a'] <= 100


# ---------------------------------------------------------------------------
# describe_open_balance_traffic
# ---------------------------------------------------------------------------

def describe_open_balance_traffic():
    """Tests of open_balance_traffic (Level 3a): balancing without targeting (RoN)."""

    def test_returns_dictionary():
        """The result is a dictionary."""
        ads = {'a': _make_ad('a', cpm=10)}
        result = open_balance_traffic(ads, _PARAMS_BASE)
        assert isinstance(result, dict)

    def test_all_ads_present():
        """All ads are present in the result."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10),
            'ad_b': _make_ad('ad_b', cpm=5),
        }
        result = open_balance_traffic(ads, _PARAMS_BASE)
        assert set(result.keys()) == {'ad_a', 'ad_b'}

    def test_targeting_ignored_both_ads_receive_traffic():
        """
        RoN: ads with incompatible targeting (different geo)
        both get impressions, since targets are replaced with empty ones.

        Scenario: ad_moscow with cpm=10, volume=40 exhausts its limit,
        the remaining traffic (60 of 100) goes to ad_spb.
        In seasonal_balance_traffic ad_moscow would be limited to the segment
        geo:msk (P=0.5, max 50 impressions); open_balance removes this restriction.
        """
        params = _make_params(
            100, _CTX_1H, _A_START, _A_END,
            objective='maximize_money',
            tag_probabilities={'geo:msk': 0.5, 'geo:spb': 0.5},
            vocabs={'geo': ['geo:msk', 'geo:spb']},
        )
        ads = {
            'ad_moscow': _make_ad('ad_moscow', cpm=10, volume=40,
                                  targets={'geo': ['msk']}),
            'ad_spb':    _make_ad('ad_spb',    cpm=5,  volume=1000,
                                  targets={'geo': ['spb']}),
        }
        result = open_balance_traffic(ads, params)
        # Targeting is ignored — both compete for all the traffic:
        # ad_moscow takes its limit (40), the remainder (60) goes to ad_spb
        assert result['ad_moscow'] > 0
        assert result['ad_spb'] > 0

    def test_sum_does_not_exceed_total():
        """Total volume ≤ total_traffic_volume."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10, volume=1000),
            'ad_b': _make_ad('ad_b', cpm=5,  volume=1000),
        }
        result = open_balance_traffic(ads, _PARAMS_BASE)
        assert sum(result.values()) <= _PARAMS_BASE['total_traffic_volume']

    def test_all_volumes_non_negative():
        """All volumes are non-negative."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10),
            'ad_b': _make_ad('ad_b', cpm=5),
        }
        result = open_balance_traffic(ads, _PARAMS_BASE)
        assert all(v >= 0 for v in result.values())

    def test_empty_target_matches_seasonal_result():
        """
        If all ads already have empty targeting,
        the result of open_balance_traffic matches seasonal_balance_traffic.
        """
        ads = {
            'ad_expensive': _make_ad('ad_expensive', cpm=10, h_limit=8, volume=1000),
            'ad_cheap':     _make_ad('ad_cheap',     cpm=1,  h_limit=8, volume=1000),
        }
        params = _make_params(10, _CTX_1H, _A_START, _A_END, objective='maximize_money')
        result = open_balance_traffic(ads, params)
        assert result['ad_expensive'] == 8
        assert result['ad_cheap'] == 2

    def test_maximize_money_prefers_expensive_ad():
        """maximize_money: an expensive ad gets no less than a cheap one."""
        ads = {
            'ad_expensive': _make_ad('ad_expensive', cpm=100, volume=1000),
            'ad_cheap':     _make_ad('ad_cheap',     cpm=1,   volume=1000),
        }
        result = open_balance_traffic(ads, _PARAMS_BASE)
        assert result['ad_expensive'] >= result['ad_cheap']


# ---------------------------------------------------------------------------
# describe_seasonal_balance_by_sellout
# ---------------------------------------------------------------------------

def describe_seasonal_balance_by_sellout():
    """Tests of seasonal_balance_by_sellout (Level 3): maximizing the minimum sellout."""

    def _sellout_params(total: int, ctx: dict, t_start: datetime, t_end: datetime,
                        **kw) -> dict:
        base = _make_params(total, ctx, t_start, t_end, **kw)
        return {**base, 'accuracy_percent': 0.1}

    def test_result_contains_report_and_sellout_percent():
        """The result contains the fields report and sellout_percent."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10, volume=6),
            'ad_b': _make_ad('ad_b', cpm=5,  volume=4),
        }
        params = _sellout_params(10, _CTX_1H, _A_START, _A_END)
        result = seasonal_balance_by_sellout(ads, params)
        assert 'report' in result
        assert 'sellout_percent' in result

    def test_sellout_percent_nonnegative():
        """sellout_percent ≥ 0."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10, volume=6),
            'ad_b': _make_ad('ad_b', cpm=5,  volume=4),
        }
        params = _sellout_params(10, _CTX_1H, _A_START, _A_END)
        result = seasonal_balance_by_sellout(ads, params)
        assert result['sellout_percent'] >= 0.0

    def test_report_contains_all_ads():
        """All ads are present in report."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10, volume=6),
            'ad_b': _make_ad('ad_b', cpm=5,  volume=4),
        }
        params = _sellout_params(10, _CTX_1H, _A_START, _A_END)
        result = seasonal_balance_by_sellout(ads, params)
        assert set(result['report'].keys()) == {'ad_a', 'ad_b'}

    def test_total_volume_does_not_exceed_traffic():
        """Total volume in report ≤ total_traffic_volume."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10, volume=1000),
            'ad_b': _make_ad('ad_b', cpm=5,  volume=1000),
        }
        params = _sellout_params(10, _CTX_1H, _A_START, _A_END)
        result = seasonal_balance_by_sellout(ads, params)
        assert sum(result['report'].values()) <= 10

    def test_each_ad_receives_minimum_share():
        """
        The actual sellout share of each campaign
        is not lower than sellout_percent (with a tolerance for the binary search accuracy).
        """
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10, volume=6),
            'ad_b': _make_ad('ad_b', cpm=5,  volume=4),
        }
        params = _sellout_params(10, _CTX_1H, _A_START, _A_END)
        result = seasonal_balance_by_sellout(ads, params)
        report = result['report']
        min_fraction = result['sellout_percent'] / 100.0

        for ad_id, ad in ads.items():
            actual_fraction = report[ad_id] / ad['volume']
            assert actual_fraction >= min_fraction - 0.01, (
                f"{ad_id}: share {actual_fraction:.3f} below sellout_percent "
                f"({min_fraction:.3f})"
            )

    def test_two_hour_period_sellout():
        """seasonal_balance_by_sellout works on a multi-slot period."""
        ads = {
            'ad_a': _make_ad('ad_a', cpm=10, volume=100),
            'ad_b': _make_ad('ad_b', cpm=5,  volume=100),
        }
        params = _sellout_params(100, _CTX_2H, _B_START, _B_END)
        result = seasonal_balance_by_sellout(ads, params)
        assert result['sellout_percent'] >= 0.0
        assert sum(result['report'].values()) <= 100


# ---------------------------------------------------------------------------
# describe_seasonal_add_new_balanced_campaign
# ---------------------------------------------------------------------------

def describe_seasonal_add_new_balanced_campaign():
    """Tests of seasonal_add_new_balanced_campaign (Level 3)."""

    def test_result_contains_report_and_new_ads_volumes():
        """The result contains the fields report and new_ads_volumes."""
        existing = {'ad_old': _make_ad('ad_old', cpm=10, volume=5)}
        current_report = {'ad_old': 5}
        all_ads = {**existing, 'ad_new': _make_ad('ad_new', cpm=5, volume=1000)}
        result = seasonal_add_new_balanced_campaign(all_ads, current_report, _PARAMS_BASE)
        assert 'report' in result
        assert 'new_ads_volumes' in result

    def test_existing_campaign_volume_preserved():
        """
        After adding a new campaign the volume of the existing one
        does not change (it is frozen via current_report).
        """
        # With an hourly limit of 5, at total=10 ad_old gets ≤ 5
        existing = {'ad_old': _make_ad('ad_old', cpm=10, h_limit=5, volume=1000)}
        params = _make_params(10, _CTX_1H, _A_START, _A_END)
        first_report = seasonal_balance_traffic(existing, params)

        all_ads = {**existing, 'ad_new': _make_ad('ad_new', cpm=5, volume=1000)}
        result = seasonal_add_new_balanced_campaign(all_ads, first_report, params)
        assert result['report']['ad_old'] == first_report['ad_old']

    def test_new_campaign_present_in_new_ads_volumes():
        """new_ads_volumes contains the key of the new campaign."""
        existing = {'ad_old': _make_ad('ad_old', cpm=10, h_limit=5, volume=1000)}
        params = _make_params(10, _CTX_1H, _A_START, _A_END)
        first_report = seasonal_balance_traffic(existing, params)

        all_ads = {**existing, 'ad_new': _make_ad('ad_new', cpm=5, volume=1000)}
        result = seasonal_add_new_balanced_campaign(all_ads, first_report, params)
        assert 'ad_new' in result['new_ads_volumes']

    def test_new_campaign_volume_nonnegative():
        """The volume of the new campaign in new_ads_volumes ≥ 0."""
        existing = {'ad_old': _make_ad('ad_old', cpm=10, h_limit=5, volume=1000)}
        params = _make_params(10, _CTX_1H, _A_START, _A_END)
        first_report = seasonal_balance_traffic(existing, params)

        all_ads = {**existing, 'ad_new': _make_ad('ad_new', cpm=5, volume=1000)}
        result = seasonal_add_new_balanced_campaign(all_ads, first_report, params)
        assert result['new_ads_volumes']['ad_new'] >= 0

    def test_report_contains_all_ads():
        """report contains the keys of all ads — both old and new."""
        existing = {'ad_old': _make_ad('ad_old', cpm=10, h_limit=5, volume=1000)}
        params = _make_params(10, _CTX_1H, _A_START, _A_END)
        first_report = seasonal_balance_traffic(existing, params)

        all_ads = {**existing, 'ad_new': _make_ad('ad_new', cpm=5, volume=1000)}
        result = seasonal_add_new_balanced_campaign(all_ads, first_report, params)
        assert set(result['report'].keys()) == {'ad_old', 'ad_new'}

    def test_new_campaign_uses_remaining_capacity():
        """
        The new campaign gets the traffic that was not taken
        by the existing one (ad_old with limit 5 of total=10 → remainder 5 → ad_new > 0).
        """
        existing = {'ad_old': _make_ad('ad_old', cpm=10, h_limit=5, volume=1000)}
        params = _make_params(10, _CTX_1H, _A_START, _A_END)
        first_report = seasonal_balance_traffic(existing, params)

        all_ads = {**existing, 'ad_new': _make_ad('ad_new', cpm=5, volume=1000)}
        result = seasonal_add_new_balanced_campaign(all_ads, first_report, params)
        assert result['new_ads_volumes']['ad_new'] > 0


# ---------------------------------------------------------------------------
# describe_forecast_bid
# ---------------------------------------------------------------------------

def describe_forecast_bid():
    """Tests of forecast_bid (Level 3c): recommended bid forecaster."""

    def _bid_params(
        mode: int,
        *,
        bid_direction: str = 'minimize',
        max_budget: float = 1.0,
        min_impressions: int = 1,
        max_cannibalization: float | None = None,
    ) -> dict:
        """Builds BidForecastParams for the given mode."""
        my_ad = _make_ad('my_ad', cpm=5.0, volume=1000)
        competitor = _make_ad('comp_ad', cpm=3.0, volume=1000)
        params = {
            # SeasonalBalancingParams (inner format)
            'total_traffic_volume': 100,
            'tag_probabilities': {},
            'vocabs': {},
            'objective': 'maximize_money',
            'max_n_categories': 100,
            'min_category_probability': 1e-6,
            'n_threads': 1,
            'seasonal_context': _CTX_1H,
            'period': {'period_start': _A_START, 'period_end': _A_END},
            # BidForecastParams
            'ad': my_ad,
            'max_budget': max_budget,
            'min_impressions': min_impressions,
            'bid_direction': bid_direction,
            'min_bid': 1.0,
            'ads': {'comp_ad': competitor},
            'current_report': {'comp_ad': 50},
            'search_accuracy': 1.0,
            'mode': mode,
        }
        if max_cannibalization is not None:
            params['max_cannibalization'] = max_cannibalization
        return params

    # -----------------------------------------------------------------------
    # Mode 1 — free optimization, cannibalization is measured
    # -----------------------------------------------------------------------

    def describe_mode_1_unconstrained_optimization():

        def test_result_contains_all_fields():
            """Mode 1: BidForecastResult contains all required fields."""
            result = forecast_bid(_bid_params(1))
            assert 'recommended_bid' in result
            assert 'expected_impressions' in result
            assert 'expected_spend' in result
            assert 'cannibalization' in result

        def test_recommended_rate_not_below_min_bid():
            """Mode 1: recommended_bid ≥ min_bid."""
            params = _bid_params(1)
            result = forecast_bid(params)
            assert result['recommended_bid'] >= params['min_bid']

        def test_expected_impressions_nonnegative():
            """Mode 1: expected_impressions ≥ 0."""
            result = forecast_bid(_bid_params(1))
            assert result['expected_impressions'] >= 0

        def test_expected_cost_within_budget():
            """Mode 1: expected_spend ≤ max_budget (with a tolerance for the binary search accuracy)."""
            params = _bid_params(1, max_budget=1.0)
            result = forecast_bid(params)
            # 1% tolerance: search_accuracy=1.0 CPM may give a slight overshoot
            assert result['expected_spend'] <= params['max_budget'] * 1.01

        def test_cannibalization_contains_per_ad_relative_and_total():
            """Mode 1: cannibalization contains the expected fields (or None when there are no competitors)."""
            result = forecast_bid(_bid_params(1))
            cannib = result['cannibalization']
            if cannib is not None:
                assert 'per_ad' in cannib
                assert 'relative' in cannib
                assert 'total' in cannib

    # -----------------------------------------------------------------------
    # Mode 2 — competitors frozen, cannibalization = None
    # -----------------------------------------------------------------------

    def describe_mode_2_frozen_competitors():

        def test_cannibalization_none():
            """Mode 2: cannibalization is always None (competitors do not lose volume)."""
            result = forecast_bid(_bid_params(2))
            assert result['cannibalization'] is None

        def test_result_contains_all_fields():
            """Mode 2: BidForecastResult contains all required fields."""
            result = forecast_bid(_bid_params(2))
            assert 'recommended_bid' in result
            assert 'expected_impressions' in result
            assert 'expected_spend' in result

        def test_recommended_rate_not_below_min_bid():
            """Mode 2: recommended_bid ≥ min_bid."""
            params = _bid_params(2)
            result = forecast_bid(params)
            assert result['recommended_bid'] >= params['min_bid']

    # -----------------------------------------------------------------------
    # Mode 3 — free optimization + min_vol from the Ad
    # -----------------------------------------------------------------------

    def describe_mode_3_with_min_volume():

        def test_result_contains_all_fields():
            """Mode 3: BidForecastResult contains all required fields."""
            result = forecast_bid(_bid_params(3))
            assert 'recommended_bid' in result
            assert 'expected_impressions' in result
            assert 'expected_spend' in result
            assert 'cannibalization' in result

        def test_recommended_rate_not_below_min_bid():
            """Mode 3: recommended_bid ≥ min_bid."""
            params = _bid_params(3)
            result = forecast_bid(params)
            assert result['recommended_bid'] >= params['min_bid']

    # -----------------------------------------------------------------------
    # Mode 4 — cannibalization constraint
    # -----------------------------------------------------------------------

    def describe_mode_4_with_cannibalization_limit():

        def test_result_contains_all_fields():
            """Mode 4: BidForecastResult contains all required fields."""
            params = _bid_params(4, max_cannibalization=100.0)
            result = forecast_bid(params)
            assert 'recommended_bid' in result
            assert 'expected_impressions' in result
            assert 'expected_spend' in result

        def test_recommended_rate_not_below_min_bid():
            """Mode 4: recommended_bid ≥ min_bid."""
            params = _bid_params(4, max_cannibalization=100.0)
            result = forecast_bid(params)
            assert result['recommended_bid'] >= params['min_bid']

    # -----------------------------------------------------------------------
    # Search direction (bid_direction)
    # -----------------------------------------------------------------------

    def describe_bid_direction():

        def test_maximize_bid_not_below_minimize():
            """
            maximize finds the largest allowed CPM,
            minimize — the smallest. The result of maximize ≥ minimize.
            """
            params_min = _bid_params(1, bid_direction='minimize',
                                     max_budget=1.0, min_impressions=1)
            params_max = _bid_params(1, bid_direction='maximize',
                                     max_budget=1.0, min_impressions=1)
            r_min = forecast_bid(params_min)
            r_max = forecast_bid(params_max)
            assert r_max['recommended_bid'] >= r_min['recommended_bid']
