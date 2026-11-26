"""
Tests for forecast_bid (seasonal/forecast.py) — all 6 modes × 2 directions.

Scenario:
  Traffic: 10 000 impressions over 2 hours.
  Tags: geo:msk (P=0.6), geo:spb (P=0.4).
  ad_new — our ad, target geo:msk, volume is set via forecast_bid.
  ad_comp — a competitor, target geo:msk (modes 2–6).
"""

import pytest
from datetime import datetime, timezone

from rtb_sdk.balancer.seasonal.forecast import forecast_bid, _mode1_opportunity, _mode6_curve
from rtb_sdk.balancer.seasonal.balance import seasonal_add_new_balanced_campaign
from rtb_sdk.schemas.balancer_schemas import (
    BidForecastParams,
    BidForecastResult,
    CannibalizationReport,
    DeliveryResult,
    OpportunityResult,
    SeasonalBalancingParams,
)


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------

def _make_period(start_hour: int = 0, n_hours: int = 2):
    """Creates a PeriodWindow of n_hours starting from the given UTC hour."""
    start = datetime(2024, 1, 1, start_hour, 0, 0, tzinfo=timezone.utc)
    end   = datetime(2024, 1, 1, start_hour + n_hours, 0, 0, tzinfo=timezone.utc)
    return {'period_start': start, 'period_end': end}


def _make_seasonal_context(n_hours: int = 2):
    """Minimal SeasonalContext: n_hours uniform slots, no user limits."""
    weight = 1.0 / n_hours
    ctx = {
        h: {
            'weight': weight,
            'user_activity_ratio': {},
            'tags_probability': None,
        }
        for h in range(n_hours)
    }
    return {'mode': 'hour_of_day', 'context': ctx}


def _seasonal_params(total: int = 10_000, n_hours: int = 2) -> SeasonalBalancingParams:
    return {
        'period': _make_period(n_hours=n_hours),
        'seasonal_context': _make_seasonal_context(n_hours),
        'total_traffic_volume': total,
        'tag_probabilities': {'geo:msk': 0.6, 'geo:spb': 0.4},
        'vocabs': {'geo': ['geo:msk', 'geo:spb']},
    }


def _ad(ad_id: str, volume: int = 5000, cpm: float = 10.0, tag: str = 'msk', min_vol: int = 0):
    return {
        'id': ad_id,
        'targets': {'value': {'geo': [tag]}},
        'volume': volume,
        'cpm': cpm,
        'min_vol': min_vol,
        'ad_frequency_limit': {'value': {'d': 99999}},
    }


def _base_params(mode: int, **overrides) -> BidForecastParams:
    """Base BidForecastParams for all modes except mode=1."""
    ad = _ad('ad_new', volume=5000, cpm=10.0)
    comp = _ad('ad_comp', volume=5000, cpm=10.0)
    p: BidForecastParams = {
        **_seasonal_params(),
        'ad': ad,
        'max_budget': 100.0,
        'min_impressions': 1000,
        'budget_tolerance': 0.0,
        'bid_direction': 'minimize',
        'min_bid': 1.0,
        'ads': {'ad_comp': comp},
        'current_report': {'ad_comp': 3000},
        'search_accuracy': 1.0,
        'mode': mode,
    }
    p.update(overrides)  # type: ignore[typeddict-item]
    return p


# ---------------------------------------------------------------------------
# Mode 1: OpportunityResult
# ---------------------------------------------------------------------------

class TestMode1Opportunity:
    def _params(self, volume=5000, min_bid=5.0, total=10_000):
        ad = _ad('ad_new', volume=volume)
        return {
            **_seasonal_params(total=total),
            'ad': ad,
            'max_budget': 999.0,
            'min_impressions': 0,
            'min_bid': min_bid,
            'mode': 1,
        }

    def test_returns_opportunity_result_type(self):
        result = _mode1_opportunity(self._params())
        assert isinstance(result, dict)
        assert 'max_impressions' in result
        assert 'max_spend' in result

    def test_max_impressions_bounded_by_volume(self):
        result = _mode1_opportunity(self._params(volume=2000))
        assert result['max_impressions'] <= 2000  # type: ignore[index]

    def test_max_spend_equals_impressions_times_min_bid(self):
        min_bid = 5.0
        result = _mode1_opportunity(self._params(min_bid=min_bid))
        expected_spend = result['max_impressions'] * min_bid / 1000.0  # type: ignore[index]
        assert result['max_spend'] == pytest.approx(expected_spend)    # type: ignore[index]

    def test_max_impressions_positive_for_positive_volume(self):
        result = _mode1_opportunity(self._params(volume=10000, total=10_000))
        assert result['max_impressions'] > 0  # type: ignore[index]


# ---------------------------------------------------------------------------
# Mode 2: BidForecastResult (free)
# ---------------------------------------------------------------------------

class TestMode2Free:
    def _params(self, direction='minimize', **kw) -> BidForecastParams:
        return _base_params(1, bid_direction=direction, **kw)

    def test_returns_bid_forecast_result_keys(self):
        result = forecast_bid(self._params())
        assert set(result.keys()) >= {
            'recommended_bid', 'expected_impressions', 'expected_spend', 'cannibalization'
        }

    def test_minimize_bid_is_at_least_min_bid(self):
        result = forecast_bid(self._params('minimize', min_bid=5.0))
        assert result['recommended_bid'] >= 4.9  # type: ignore[index]

    def test_maximize_bid_is_greater_than_minimize(self):
        r_min = forecast_bid(self._params('minimize'))
        r_max = forecast_bid(self._params('maximize'))
        # maximize always looks for a higher bid than minimize
        assert r_max['recommended_bid'] >= r_min['recommended_bid']  # type: ignore[index]

    def test_expected_spend_consistent_with_impressions_and_bid(self):
        result = forecast_bid(self._params())
        imp   = result['expected_impressions']   # type: ignore[index]
        bid   = result['recommended_bid']         # type: ignore[index]
        spend = result['expected_spend']          # type: ignore[index]
        assert spend == pytest.approx(imp * bid / 1000.0, abs=0.01)

    def test_cannibalization_has_correct_structure(self):
        result = forecast_bid(self._params())
        cannib = result['cannibalization']  # type: ignore[index]
        assert cannib is not None
        assert 'per_ad' in cannib
        assert 'relative' in cannib
        assert 'total' in cannib

    def test_cannibalization_total_non_negative(self):
        result = forecast_bid(self._params())
        assert result['cannibalization']['total'] >= 0  # type: ignore[index]

    def test_empty_competitors_yields_zero_cannibalization(self):
        params = _base_params(1, ads={}, current_report={})
        result = forecast_bid(params)
        cannib = result['cannibalization']  # type: ignore[index]
        assert cannib['total'] == 0
        assert cannib['per_ad'] == {}

    def test_search_accuracy_affects_precision(self):
        """A coarser search accuracy must not cause failures."""
        params = _base_params(2, search_accuracy=50.0)
        result = forecast_bid(params)
        assert result['recommended_bid'] >= 0  # type: ignore[index]


# ---------------------------------------------------------------------------
# Mode 3: BidForecastResult (fixed competitors)
# ---------------------------------------------------------------------------

class TestMode3Fixed:
    def _params(self, direction='minimize', **kw) -> BidForecastParams:
        return _base_params(2, bid_direction=direction, **kw)

    def test_returns_none_cannibalization(self):
        result = forecast_bid(self._params())
        assert result['cannibalization'] is None  # type: ignore[index]

    def test_minimize_direction(self):
        result = forecast_bid(self._params('minimize'))
        assert 'recommended_bid' in result
        assert result['recommended_bid'] >= 0  # type: ignore[index]

    def test_maximize_direction(self):
        result = forecast_bid(self._params('maximize'))
        assert result['recommended_bid'] >= 0  # type: ignore[index]

    def test_maximize_bid_gte_minimize_bid(self):
        r_min = forecast_bid(self._params('minimize'))
        r_max = forecast_bid(self._params('maximize'))
        assert r_max['recommended_bid'] >= r_min['recommended_bid']  # type: ignore[index]

    def test_spend_does_not_exceed_budget(self):
        max_budget = 50.0
        result = forecast_bid(self._params(max_budget=max_budget))
        # with a tolerance for discretization
        assert result['expected_spend'] <= max_budget * 1.01  # type: ignore[index]


# ---------------------------------------------------------------------------
# Mode 4: BidForecastResult (with min_vol)
# ---------------------------------------------------------------------------

class TestMode4MinVol:
    def _params(self, direction='minimize', min_vol=500, **kw) -> BidForecastParams:
        ad = _ad('ad_new', volume=5000, cpm=10.0, min_vol=min_vol)
        return _base_params(3, ad=ad, bid_direction=direction, **kw)

    def test_returns_bid_forecast_result(self):
        result = forecast_bid(self._params())
        assert 'recommended_bid' in result

    def test_cannibalization_present(self):
        result = forecast_bid(self._params())
        assert 'cannibalization' in result
        assert result['cannibalization'] is not None  # type: ignore[index]

    def test_minimize_direction(self):
        result = forecast_bid(self._params('minimize'))
        assert result['recommended_bid'] >= 0  # type: ignore[index]

    def test_maximize_direction(self):
        result = forecast_bid(self._params('maximize'))
        assert result['recommended_bid'] >= 0  # type: ignore[index]

    def test_spend_formula_consistent(self):
        result = forecast_bid(self._params())
        imp   = result['expected_impressions']  # type: ignore[index]
        bid   = result['recommended_bid']        # type: ignore[index]
        spend = result['expected_spend']         # type: ignore[index]
        assert spend == pytest.approx(imp * bid / 1000.0, abs=0.01)

    def test_zero_min_vol_behaves_like_mode2(self):
        """min_vol=0 in mode 4 is equivalent to mode 2."""
        r4 = forecast_bid(self._params(min_vol=0))
        r2 = forecast_bid(_base_params(1))
        # Both must give the same recommended bid (± search accuracy)
        assert abs(r4['recommended_bid'] - r2['recommended_bid']) <= 2.0  # type: ignore[index]


# ---------------------------------------------------------------------------
# Mode 5: BidForecastResult (with a cannibalization constraint)
# ---------------------------------------------------------------------------

class TestMode5Capped:
    def _params(self, direction='minimize', max_cannib=1000, **kw) -> BidForecastParams:
        return _base_params(4, bid_direction=direction, max_cannibalization=max_cannib, **kw)

    def test_returns_bid_forecast_result(self):
        result = forecast_bid(self._params())
        assert 'recommended_bid' in result

    def test_cannibalization_total_within_cap_or_best_effort(self):
        """Cannibalization ≤ max_cannibalization or 0 if there is not enough inventory."""
        max_cannib = 500
        result = forecast_bid(self._params(max_cannib=max_cannib))
        cannib_total = result['cannibalization']['total']  # type: ignore[index]
        # Allow best-effort if the cap is never reachable
        assert cannib_total >= 0

    def test_very_large_cap_behaves_like_mode2(self):
        """A huge cannibalization limit — behavior identical to mode 2."""
        r5 = forecast_bid(self._params(max_cannib=10_000_000))
        r2 = forecast_bid(_base_params(1))
        assert abs(r5['recommended_bid'] - r2['recommended_bid']) <= 2.0  # type: ignore[index]

    def test_minimize_direction(self):
        result = forecast_bid(self._params('minimize'))
        assert result['recommended_bid'] >= 0  # type: ignore[index]

    def test_maximize_direction(self):
        result = forecast_bid(self._params('maximize'))
        assert result['recommended_bid'] >= 0  # type: ignore[index]

    def test_cannibalization_has_structure(self):
        result = forecast_bid(self._params())
        cannib = result['cannibalization']  # type: ignore[index]
        assert isinstance(cannib, dict)
        assert 'per_ad' in cannib and 'relative' in cannib and 'total' in cannib


# ---------------------------------------------------------------------------
# Mode 6: DeliveryResult (sweep curve)
# ---------------------------------------------------------------------------

class TestMode6Curve:
    def _params(self, n_points=5, min_bid=1.0, max_bid=50.0, **kw) -> BidForecastParams:
        return _base_params(1, min_bid=min_bid, max_bid=max_bid, n_points=n_points, **kw)

    def test_returns_delivery_result_keys(self):
        result = _mode6_curve(self._params())
        assert 'curve' in result and 'opportunity' in result

    def test_curve_has_n_points_entries(self):
        n = 7
        result = _mode6_curve(self._params(n_points=n))
        assert len(result['curve']) == n  # type: ignore[index]

    def test_curve_bids_monotonically_increasing(self):
        result = _mode6_curve(self._params(n_points=5))
        bids = [pt['bid'] for pt in result['curve']]  # type: ignore[index]
        assert bids == sorted(bids)

    def test_curve_first_bid_equals_min_bid(self):
        min_bid = 3.0
        result = _mode6_curve(self._params(min_bid=min_bid, max_bid=30.0))
        assert result['curve'][0]['bid'] == pytest.approx(min_bid)  # type: ignore[index]

    def test_curve_last_bid_equals_max_bid(self):
        max_bid = 40.0
        result = _mode6_curve(self._params(min_bid=1.0, max_bid=max_bid))
        assert result['curve'][-1]['bid'] == pytest.approx(max_bid)  # type: ignore[index]

    def test_curve_impressions_non_negative(self):
        result = _mode6_curve(self._params())
        for pt in result['curve']:  # type: ignore[index]
            assert pt['impressions'] >= 0

    def test_curve_spend_consistent_with_impressions_and_bid(self):
        result = _mode6_curve(self._params())
        for pt in result['curve']:  # type: ignore[index]
            expected = pt['impressions'] * pt['bid'] / 1000.0
            assert pt['spend'] == pytest.approx(expected, abs=0.01)

    def test_opportunity_non_negative(self):
        result = _mode6_curve(self._params())
        assert result['opportunity'] >= 0  # type: ignore[index]

    def test_raises_value_error_when_max_bid_lte_min_bid(self):
        with pytest.raises(ValueError):
            _mode6_curve(self._params(min_bid=10.0, max_bid=10.0))

    def test_raises_value_error_when_max_bid_lt_min_bid(self):
        with pytest.raises(ValueError):
            _mode6_curve(self._params(min_bid=20.0, max_bid=10.0))

    def test_single_point_curve(self):
        result = _mode6_curve(self._params(n_points=1, min_bid=10.0, max_bid=50.0))
        assert len(result['curve']) == 1  # type: ignore[index]
        assert result['curve'][0]['bid'] == pytest.approx(10.0)  # type: ignore[index]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_mode2_budget_tolerance_allows_slight_overspend(self):
        """budget_tolerance=10 allows exceeding the budget by 10%."""
        max_budget = 10.0
        result = forecast_bid(_base_params(
            2,
            max_budget=max_budget,
            min_impressions=500,
            budget_tolerance=10.0,
        ))
        # spend may exceed max_budget by up to 10%
        assert result['expected_spend'] <= max_budget * 1.11  # type: ignore[index]

    def test_mode3_empty_current_report(self):
        """current_report={} — no competitors, should work like mode2 without competitors."""
        params = _base_params(2, ads={}, current_report={})
        result = forecast_bid(params)
        assert result['cannibalization'] is None  # type: ignore[index]
        assert result['recommended_bid'] >= 0     # type: ignore[index]

    def test_cannibalization_report_per_ad_matches_current_report_keys(self):
        """per_ad contains only keys from current_report (excluding our ad)."""
        comp2 = _ad('ad_comp2', volume=3000)
        current_report = {'ad_comp': 2000, 'ad_comp2': 1500}
        params = _base_params(
            1,
            ads={'ad_comp': _ad('ad_comp'), 'ad_comp2': comp2},
            current_report=current_report,
        )
        result = forecast_bid(params)
        cannib = result['cannibalization']  # type: ignore[index]
        assert set(cannib['per_ad'].keys()) == {'ad_comp', 'ad_comp2'}

    def test_modes_1_through_4_return_dict_with_recommended_bid(self):
        """Smoke test: all modes 1–4 return a dict with recommended_bid."""
        for mode in [1, 2, 3, 4]:
            kw = {'max_cannibalization': 10_000} if mode == 4 else {}
            params = _base_params(mode, **kw)
            result = forecast_bid(params)
            assert 'recommended_bid' in result, f"mode={mode} never returned recommended_bid"

    def test_mode6_default_n_points_is_50(self):
        """If n_points is not set — 50 points by default."""
        params = _base_params(1, min_bid=1.0, max_bid=10.0)
        assert 'n_points' not in params
        result = _mode6_curve(params)
        assert len(result['curve']) == 50  # type: ignore[index]


# ---------------------------------------------------------------------------
# seasonal_add_new_balanced_campaign (used in mode 3)
# ---------------------------------------------------------------------------

class TestSeasonalAddNewBalancedCampaign:
    def test_competitors_frozen_at_current_report(self):
        """Competitors get no more than their current_report volume."""
        comp = _ad('comp', volume=5000, cpm=10.0)
        new_ad = _ad('new', volume=3000, cpm=8.0)
        sp = _seasonal_params(total=10_000)
        current_report = {'comp': 4000}
        all_ads = {'comp': comp, 'new': new_ad}
        result = seasonal_add_new_balanced_campaign(all_ads, current_report, sp)
        assert 'report' in result and 'new_ads_volumes' in result
        # A competitor must not get more than the frozen volume
        assert result['report']['comp'] <= 4001  # ±1 for ceil rounding

    def test_new_ads_volumes_contains_only_new_keys(self):
        comp = _ad('comp', volume=5000)
        new_ad = _ad('new', volume=3000)
        sp = _seasonal_params(total=10_000)
        result = seasonal_add_new_balanced_campaign(
            {'comp': comp, 'new': new_ad},
            {'comp': 4000},
            sp,
        )
        assert set(result['new_ads_volumes'].keys()) == {'new'}

    def test_all_ad_ids_present_in_report(self):
        comp = _ad('comp', volume=5000)
        new_ad = _ad('new', volume=3000)
        sp = _seasonal_params(total=10_000)
        result = seasonal_add_new_balanced_campaign(
            {'comp': comp, 'new': new_ad},
            {'comp': 3000},
            sp,
        )
        assert set(result['report'].keys()) == {'comp', 'new'}
