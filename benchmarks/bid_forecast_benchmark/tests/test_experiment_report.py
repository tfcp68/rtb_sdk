import unittest

from articles_prorotypes.bench.experiment_report import NEW, OLD, fmt, load, render
from pathlib import Path


class ExperimentReportTests(unittest.TestCase):
    def test_default_new_source_is_probability_artifact(self):
        self.assertEqual(NEW, OLD.parent.parent / "fixed_scenario_probability_100" / "fixed_scenario_validation.json")

    def test_render_preserves_full_and_censored_strategy_values(self):
        old, new = load(OLD), load(NEW)
        page = render(old, new, (OLD, NEW))
        full = next(r for r in new["raw_runs"] if r.get("regime") == "full" and r["strategy"] == "NTM (tree, wins-only)")
        censored = next(r for r in new["raw_runs"] if r.get("regime") == "censored" and r["strategy"] == "NTM (tree, wins-only)")
        self.assertNotEqual(full["ours_total"], censored["ours_total"])
        full_row = page.split('<td>FULL</td><th>NTM (tree, wins-only)</th>', 1)[1].split('</tr>', 1)[0]
        censored_row = page.split('<td>CENSORED</td><th>NTM (tree, wins-only)</th>', 1)[1].split('</tr>', 1)[0]
        self.assertIn(f'<td>{fmt(full["ours_total"])}</td>', full_row)
        self.assertIn(f'<td>{fmt(censored["ours_total"])}</td>', censored_row)

    def test_report_leaders_are_selected_from_exact_regime_rows(self):
        old, new = load(OLD), load(NEW)
        page = render(old, new, (OLD, NEW))
        for regime in ("full", "censored"):
            models = [r for r in new["raw_runs"] if r.get("regime") == regime]
            winner = max(models, key=lambda r: r["ours_total"])
            self.assertIn(f'{regime.upper()} лидирует: {winner["strategy"]}', page)
            self.assertIn(fmt(winner["ours_total"]), page)
        full_nm = next(r["ours_total"] for r in new["raw_runs"] if r.get("regime") == "full" and r["strategy"] == "NM (wins-only global)")
        censored_nm = next(r["ours_total"] for r in new["raw_runs"] if r.get("regime") == "censored" and r["strategy"] == "NM (wins-only global)")
        self.assertNotEqual(full_nm, censored_nm)

    def test_charts_and_embedding_metadata_are_present(self):
        page = render(load(OLD), load(NEW), (OLD, NEW))
        self.assertIn('aria-label="100 значений random по min–max"', page)
        self.assertIn('aria-label="Стратегии против среднего random в отклонении"', page)
        self.assertIn('transform="rotate(-90 8 115)"', page)
        self.assertIn("sampled market requests", page)
        self.assertIn("fixed_scenario_validation --prepared", page)
        self.assertIn("var(--foreground,#122b35)", page)
        self.assertIn("body{margin:0;background:transparent", page)
        self.assertIn("<div class=\"report\">", page)
        self.assertNotIn("<script", page)

    def test_probability_metrics_are_rendered_with_exact_artifact_values(self):
        old = load(OLD)
        new = load(NEW)
        page = render(old, new, (OLD, NEW))
        metrics = new["provenance"]["probability_diagnostics"]["metrics"]
        m = metrics["full: Cui point-mean"]["chosen_bid_probability"]
        self.assertIn(f'<td>{m["n"]:,} / {m["n_all"]:,}</td>', page)
        self.assertIn(f'<td>{fmt(m["brier"],4)}</td>', page)
        self.assertIn(f'<td>{fmt(m["logloss"],4)}</td>', page)
        self.assertIn(f'<td>{m["confidently_wrong_count"]}</td>', page)
        self.assertIn(fmt(metrics["full: SM (KM global)"]["actual_replay"]["market_profit"]), page)
        self.assertIn(fmt(metrics["full: SM (KM global)"]["local_oracle"]["regret_sum"]), page)
        baseline_metrics = metrics["baseline: truthful b=v"]
        self.assertIn(f'<td>{fmt(baseline_metrics["actual_replay"]["market_profit"])}</td>', page)
        self.assertIn("<td>—</td><td>", page)
        self.assertIn("фиксированный probe", page)
        self.assertIn("0,9", page)
        self.assertIn("hindsight", page)

    def test_probability_section_gracefully_handles_artifacts_without_metrics(self):
        old = load(OLD)
        new = load(NEW.parent.parent / "fixed_scenario_train_only_100" / "fixed_scenario_validation.json")
        page = render(old, new, (OLD, NEW))
        self.assertIn("Диагностика отсутствует", page)
if __name__ == "__main__":
    unittest.main()
