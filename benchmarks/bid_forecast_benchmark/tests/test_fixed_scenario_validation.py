import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

PATH = Path(__file__).parents[1] / "bench" / "fixed_scenario_validation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("fixed_scenario_validation", PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_online_metrics_adds_outside_revenue_once():
    fv = load_module()
    out = {"v": [10., 4., 8.], "b": [7., 3., 5.],
           "won": [True, False, True], "our_outside_revenue": 11.0}
    got = fv.online_metrics(out)
    assert got["market_profit"] == 6.0
    assert got["ours_total"] == 17.0
    assert got["wins"] == 2
    assert got["spend"] == 12.0


def test_alpha_is_selected_by_full_online_validation_total():
    fv = load_module()
    scores = fv.select_alpha({0.5: 20.0, 0.6: 25.0, 0.7: 24.0})
    assert scores["selected_alpha"] == 0.6
    assert scores["scores"] == {"0.5": 20.0, "0.6": 25.0, "0.7": 24.0}


def test_comparison_pairs_every_random_run_and_counts_ties_strictly():
    fv = load_module()
    result = fv.compare_runs(10.0, [8.0, 10.0, 12.0, 14.0])
    assert result["paired_deltas"] == [2.0, 0.0, -2.0, -4.0]
    assert result["fraction_random_runs_beaten"] == 0.25
    assert result["ties"] == 1
    assert result["random_min"] == 8.0 and result["random_max"] == 14.0
    assert result["random_p05"] == pytest.approx(8.3)
    assert result["random_p50"] == 11.0
    assert result["random_p95"] == pytest.approx(13.7)
    assert result["exceeds_random_p95"] is False
    assert result["delta_mean"] == -1.0
    assert fv.compare_runs(10.0, [8.0], shading_total=6.0)["delta_vs_shading"] == 4.0


def test_comparison_quantiles_sort_random_values_without_reordering_pairings():
    fv = load_module()
    result = fv.compare_runs(10.0, [14.0, 8.0, 12.0, 10.0])
    assert result["paired_deltas"] == [-4.0, 2.0, -2.0, 0.0]
    assert result["random_p05"] == pytest.approx(8.3)
    assert result["random_p50"] == 11.0
    assert result["random_p95"] == pytest.approx(13.7)


@pytest.mark.parametrize("values", [[float("nan")], [float("inf")], []])
def test_comparison_rejects_empty_or_nonfinite_values(values):
    fv = load_module()
    with pytest.raises(ValueError):
        fv.compare_runs(1.0, values)


def test_report_writer_refuses_existing_output(tmp_path):
    fv = load_module()
    target = tmp_path / "exists.json"
    target.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        fv.write_report(tmp_path, {"raw_runs": [], "comparisons": [], "configuration": {}})
    assert target.read_text(encoding="utf-8") == "keep"


def test_run_rejects_missing_sources_before_importing_numpy(tmp_path):
    fv = load_module()
    args = SimpleNamespace(environment_seed=1, bid_seed=1, random_replicates=100,
                           competitors=1, train_cap=1, val_cap=1, cui_estimators=1,
                           depth=1, min_leaf=1, sample=.1, q=.8, reserve=1., b_max=2.,
                           cui_min_impressions=1., prepared=str(tmp_path / "missing"),
                           manager_ads=str(tmp_path / "ads"), our_ads=str(tmp_path / "ours"),
                           output_dir=str(tmp_path / "out"))
    with pytest.raises(FileNotFoundError, match="prepared data"):
        fv.run(args)


def test_run_rejects_negative_seed(tmp_path):
    fv = load_module()
    args = SimpleNamespace(environment_seed=-1, bid_seed=1, random_replicates=100,
                           competitors=1, train_cap=1, val_cap=1, cui_estimators=1,
                           depth=1, min_leaf=1, sample=.1, q=.8, reserve=1., b_max=2.,
                           cui_min_impressions=1., prepared=str(tmp_path / "missing"),
                           manager_ads=str(tmp_path / "ads"), our_ads=str(tmp_path / "ours"),
                           output_dir=str(tmp_path / "out"))
    with pytest.raises(ValueError, match="non-negative"):
        fv.run(args)


def test_run_replays_fixed_scenario_and_writes_reports(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")

    fv = load_module()
    from articles_prorotypes.bench import fixed_scenario_validation as runner
    from articles_prorotypes.bench import multi_competitor as mc
    from articles_prorotypes.bench import online_benchmark as ob
    from articles_prorotypes.bench import price_benchmark as pb
    from articles_prorotypes.cui.cui2011 import CuiForecaster
    import articles_prorotypes.wang.wang2016 as wang

    class FakeMarket:
        POOL_DEVICES = ("fixture",)

        @staticmethod
        def load_prepared(path):
            return SimpleNamespace(n_days=7, vocabs={}, combos=np.array([[0], [1], [2]]),
                                   day_arrays=lambda day: (np.array([0]), np.array([0], dtype=np.uint32),
                                                           np.array([day % 3]),),
                                   combo_counts=np.ones(3), root="fixture",
                                   meta={"days": [{"name": str(i)} for i in range(7)]})

        @staticmethod
        def pool_mask_of(prep, devices):
            return [True, True, True]

        @staticmethod
        def load_ads_file(path):
            return [{"id": str(path), "cpm": 10}]

    monkeypatch.setattr(mc, "stand", FakeMarket)
    monkeypatch.setattr(mc, "make_competitor", lambda manager, *a, **kw: manager)
    env_seeds = []
    bids_by_call = []

    def fake_market(prep, days, sample, comps, ours, pool, q, seed, reserve, bid_of=None, our_limits=False,
                    planning=None):
        env_seeds.append(seed)
        phase = days[0]
        combos = np.array([0, 1] if phase == 0 else [1, 2])
        v = np.array([10., 10.])
        z = np.array([8., 8.])
        b = np.zeros(2)
        won = np.zeros(2, dtype=bool)
        if bid_of:
            b = np.array([bid_of(int(c), float(value), float(price), i) for i, (c, value, price)
                          in enumerate(zip(combos, v, z))])
            won = b > z
        bids_by_call.append(tuple(b.tolist()))
        return {"combo": combos, "z": z, "v": v, "b": b, "won": won,
                "our_outside_revenue": 100. if our_limits and bid_of and b[0] > 6 else 0.,
                "shown": [1], "our_shown": 0,
                "campaign_plans": {"competitors": [[10]], "ours": [10]}}

    monkeypatch.setattr(mc, "run_market", fake_market)
    fits = []
    monkeypatch.setattr(wang, "SurvivalTree", lambda depth, leaf, *a, **kw:
                        SimpleNamespace(depth=depth, min_leaf=leaf,
                                        fit=lambda obs, **kwargs: (fits.append((depth, leaf)) or object())))
    monkeypatch.setattr(pb, "observations", lambda prep, data, idx, regime, *a, **kw: ([], []))
    fitted_model_ids = set()

    def predict(prep, model, uniq):
        assert_domain(uniq)
        if not isinstance(model, tuple):
            fitted_model_ids.add(id(model))
        return np.ones((len(uniq), len(pb.GRID)))

    monkeypatch.setattr(pb, "predict_matrix", predict)
    monkeypatch.setattr(pb, "ALPHAS", [0.5, 0.8])
    validation_bids = []
    original_metrics = runner.online_metrics

    def track_validation(out):
        if out["our_outside_revenue"] and len(validation_bids) < 1:
            validation_bids.append(tuple(out["b"].tolist()))
        return original_metrics(out)

    monkeypatch.setattr(runner, "online_metrics", track_validation)
    monkeypatch.setattr(ob, "policy_from_F", lambda F, idx: (lambda c, v, z, i: 5.))
    monkeypatch.setattr(wang, "fit_baseline", lambda *args: object())
    monkeypatch.setattr(CuiForecaster, "fit", lambda self, rows: self)
    monkeypatch.setattr(CuiForecaster, "predict_samples", lambda self, feats: [])
    def assert_domain(uniq):
        # test includes combo id=2, which training does not contain.
        assert 2 in uniq

    for name in ("prepared", "manager", "ours"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "input").write_text("fixture", encoding="utf-8")
    output = tmp_path / "output"
    args = SimpleNamespace(prepared=str(tmp_path / "prepared"), manager_ads=str(tmp_path / "manager"),
                           our_ads=str(tmp_path / "ours"), output_dir=str(output), environment_seed=77,
                           bid_seed=13, random_replicates=100, sample=.5, q=.8, reserve=1., b_max=20.,
                           competitors=1, train_cap=10, val_cap=10, cui_estimators=2,
                           cui_min_impressions=1., depth=2, min_leaf=7)
    payload = runner.run(args)
    assert set(env_seeds) == {77}
    random_raw = [r for r in payload["raw_runs"] if r["strategy"] == "random bid U(R,v)"]
    assert len(random_raw) == 100
    assert len({r["bid_seed"] for r in random_raw}) == 100
    random_calls = [call for call in bids_by_call if call[0] != call[1]]
    assert len(random_calls) == 100
    assert len(set(random_calls)) > 1
    assert (2, 7) in fits
    assert len(fitted_model_ids) == 10  # two fitted baselines in each regime plus eight fixed tree fits
    assert len(fits) == 6
    assert validation_bids == [(8., 8.)]
    assert payload["validation_alpha"]["selected_alpha"] == .8
    assert payload["validation_alpha"]["scores"] == {"0.5": 0.0, "0.8": 100.0}
    shade_total = next(r["ours_total"] for r in payload["raw_runs"]
                       if r.get("strategy") == "shade alpha*v")
    for comparison in payload["comparisons"]:
        fixed_total = next(r["ours_total"] for r in payload["raw_runs"]
                           if r.get("strategy") == comparison["strategy"].split(": ", 1)[1]
                           and r.get("regime") == comparison["strategy"].split(": ", 1)[0])
        assert comparison["delta_vs_shading"] == pytest.approx(fixed_total - shade_total)
    assert len(payload["comparisons"]) == 16
    assert all(len(row["deltas"]) == 100 for row in payload["comparisons"])
    assert any(row["delta_vs_shading"] != row["delta_mean"] for row in payload["comparisons"])
    assert (output / "fixed_scenario_validation.json").exists()
    report = (output / "fixed_scenario_validation.md").read_text(encoding="utf-8")
    assert "Strategy delta vs frozen shading" in report
    saved = json.loads((output / "fixed_scenario_validation.json").read_text(encoding="utf-8"))
    assert "multi_competitor.py" in saved["provenance"]["code_sha256"]
    assert saved["provenance"]["code_sha256"]["stand.py"]
    assert saved["provenance"]["code_sha256"]["fixed_scenario_validation.py"]
    assert saved["provenance"]["code_sha256"]["ads.py"]
    assert saved["provenance"]["code_sha256"]["stream.py"]
    assert saved["provenance"]["campaign_planning"]["training_days"] == [0, 3]
    assert saved["provenance"]["split"] == {"train": [0, 3], "validation": [3, 5], "test": [5, 7]}
    assert saved["provenance"]["request_counts"] == {"train": 2, "validation": 2, "test": 2}
    diags = saved["provenance"]["probability_diagnostics"]
    assert diags["version"]
    assert diags["probe"]["rows"] == 2
    assert len(diags["metrics"]) == 16
    assert len({entry["common_probe"]["status"] for entry in diags["metrics"].values()}) > 1
    assert all(entry["chosen_bid_probability"]["status"] == "available"
               for key, entry in diags["metrics"].items() if key.startswith(("full:", "censored:")))
