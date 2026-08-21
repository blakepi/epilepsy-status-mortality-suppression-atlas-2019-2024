"""Contract tests for the Scientific Reports v2 main figures.

A figure is a claim about the data, so the same rule applies to it as to the
manuscript text: every plotted number must come from a frozen artifact, and
nothing may be drawn before the relevant gate has passed.  Each test recomputes
the plotted values from the source files rather than trusting the sidecar.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "112_figure_sr_v2_primary_associations.py"
PRODUCTION = ROOT / "outputs/scientific_reports_v2/production_8chain"


def load_generator():
    spec = importlib.util.spec_from_file_location("sr_v2_figures", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory):
    module = load_generator()
    module.DESTINATION = tmp_path_factory.mktemp("figures")
    assert module.main([]) == 0
    stem = "figure_primary_associations"
    sidecar = json.loads((module.DESTINATION / f"{stem}.json").read_text(encoding="utf-8"))
    return module, sidecar, stem


def test_generator_refuses_when_the_production_gate_has_not_passed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_generator()
    (tmp_path / "production_gate.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    monkeypatch.setattr(module, "PRODUCTION", tmp_path)
    with pytest.raises(SystemExit):
        module.require_passed_gate()


def test_both_a_vector_and_a_raster_rendering_are_written(built) -> None:
    module, _sidecar, stem = built
    for suffix in (".pdf", ".png"):
        path = module.DESTINATION / f"{stem}{suffix}"
        assert path.is_file() and path.stat().st_size > 0, path


def test_panel_a_matches_the_frozen_posterior_summary_exactly(built) -> None:
    _module, sidecar, _stem = built
    summary = pd.read_csv(PRODUCTION / "posterior_primary_summary.csv").set_index("parameter")
    panel = [row for row in sidecar["rows"] if row["panel"] == "a"]
    assert len(panel) == 6
    for row in panel:
        frozen = summary.loc[row["contrast"]]
        assert row["irr_posterior_mean"] == pytest.approx(float(frozen["posterior_mean"]))
        assert row["credible_interval_lower_95"] == pytest.approx(
            float(frozen["credible_interval_lower_95"])
        )
        assert row["credible_interval_upper_95"] == pytest.approx(
            float(frozen["credible_interval_upper_95"])
        )


def test_panel_b_percentiles_recompute_from_the_frozen_county_summary(built) -> None:
    _module, sidecar, _stem = built
    counties = pd.read_csv(
        PRODUCTION / "county_posterior_summary.csv",
        dtype={"county_fips": str, "state_fips": str},
    )
    panel = [row for row in sidecar["rows"] if row["panel"] == "b"]
    assert len(panel) == 8
    assert sum(row["counties"] for row in panel) == 2 * len(counties)
    for row in panel:
        column = "primary_rurality" if row["family"] == "Rurality" else "svi_quartile"
        values = counties.loc[counties[column] == row["category"], "posterior_mean_rate_per_100k"]
        p5, q1, median, q3, p95 = np.percentile(values, [5, 25, 50, 75, 95])
        assert row["counties"] == int(values.size)
        assert row["rate_per_100k_p5"] == pytest.approx(float(p5))
        assert row["rate_per_100k_q1"] == pytest.approx(float(q1))
        assert row["rate_per_100k_median"] == pytest.approx(float(median))
        assert row["rate_per_100k_q3"] == pytest.approx(float(q3))
        assert row["rate_per_100k_p95"] == pytest.approx(float(p95))


def test_panel_b_shows_both_reference_categories_a_ratio_plot_hides(built) -> None:
    _module, sidecar, _stem = built
    references = {row["category"] for row in sidecar["rows"] if row.get("is_reference")}
    assert references == {"metro_large", "Q1_lowest"}


def test_sidecar_names_its_sources_and_keeps_the_interpretation_boundary(built) -> None:
    _module, sidecar, _stem = built
    assert sidecar["schema_id"] == "sr_v2_figure_primary_associations/v1"
    for relative in sidecar["sources"].values():
        assert (ROOT / "outputs/scientific_reports_v2" / relative).is_file(), relative
    boundary = sidecar["interpretation_boundary"].lower()
    assert "not observed or recovered" in boundary
    assert sidecar["counties"] == 3142


# --------------------------------------------------------------------------
# Calibration and method-performance figure
# --------------------------------------------------------------------------

CALIBRATION = ROOT / "scripts" / "113_figure_sr_v2_calibration.py"
PROGRAM = ROOT / "outputs/scientific_reports_v2/calibration_program"


def load_calibration():
    spec = importlib.util.spec_from_file_location("sr_v2_calibration_figure", CALIBRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def calibration_built(tmp_path_factory: pytest.TempPathFactory):
    module = load_calibration()
    module.DESTINATION = tmp_path_factory.mktemp("calibration")
    assert module.main([]) == 0
    stem = "figure_calibration_performance"
    sidecar = json.loads((module.DESTINATION / f"{stem}.json").read_text(encoding="utf-8"))
    return module, sidecar, stem


def test_calibration_figure_refuses_before_the_program_gate_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_calibration()
    (tmp_path / "calibration_program_summary.json").write_text(
        json.dumps({"computational_gate_pass": False}), encoding="utf-8"
    )
    monkeypatch.setattr(module, "PROGRAM", tmp_path)
    with pytest.raises(SystemExit):
        module.require_passed_program()


def test_calibration_figure_writes_vector_and_raster(calibration_built) -> None:
    module, _sidecar, stem = calibration_built
    for suffix in (".pdf", ".png"):
        path = module.DESTINATION / f"{stem}{suffix}"
        assert path.is_file() and path.stat().st_size > 0, path


def test_every_method_coverage_recomputes_from_the_frozen_program(calibration_built) -> None:
    """Each pooled coverage must be the sum of its per-parameter successes."""

    _module, sidecar, _stem = calibration_built
    comparators = pd.read_csv(PROGRAM / "comparator_calibration_summary.csv")
    program = json.loads(
        (PROGRAM / "calibration_program_summary.json").read_text(encoding="utf-8")
    )
    panel = {row["method"]: row for row in sidecar["rows"] if row["panel"] == "b"}
    assert len(panel) == 7

    primary = panel.pop("constrained_bayesian")
    assert primary["coverage_successes"] == program["coefficient_interval_coverage_successes"]
    assert primary["replicates"] == program["coefficient_interval_coverage_trials"]

    for method, row in panel.items():
        block = comparators.loc[comparators["handling_scenario"] == method]
        assert not block.empty, method
        assert row["coverage_successes"] == int(block["coverage_successes"].sum())
        assert row["replicates"] == int(block["replicates"].sum())
        assert row["coverage_fraction"] == pytest.approx(
            row["coverage_successes"] / row["replicates"]
        )


def test_bias_column_is_a_median_so_divergent_fits_cannot_dominate(calibration_built) -> None:
    """One comparator's mean bias is ~1e118; the plotted summary must be robust."""

    _module, sidecar, _stem = calibration_built
    results = pd.read_csv(PROGRAM / "comparator_results.csv")
    visible = [row for row in sidecar["rows"]
               if row.get("method") == "visible_exact_and_zero_only"][0]
    raw = results.loc[results["scenario"] == "visible_exact_and_zero_only"]
    expected = ((raw["irr"] - raw["truth_irr"]) / raw["truth_irr"] * 100.0).median()
    assert visible["median_relative_bias_percent"] == pytest.approx(float(expected))
    assert abs(visible["median_relative_bias_percent"]) < 500
    assert visible["estimates_exceeding_1000"] == int((raw["irr"] > 1000).sum()) == 7


def test_only_the_divergent_comparator_is_flagged(calibration_built) -> None:
    _module, sidecar, _stem = calibration_built
    flagged = {row["method"] for row in sidecar["rows"]
               if row["panel"] == "b" and row["estimates_exceeding_1000"]}
    assert flagged == {"visible_exact_and_zero_only"}


def test_panel_a_contrast_coverage_matches_the_frozen_summary(calibration_built) -> None:
    _module, sidecar, _stem = calibration_built
    frozen = pd.read_csv(PROGRAM / "coefficient_calibration_summary.csv").set_index("parameter")
    panel = [row for row in sidecar["rows"] if row["panel"] == "a"]
    assert len(panel) == 7
    for row in panel:
        if row["contrast"] == "pooled":
            continue
        record = frozen.loc[row["contrast"]]
        assert row["coverage_successes"] == int(record["coverage_successes"])
        assert row["coverage_fraction"] == pytest.approx(float(record["coverage_fraction"]))
        assert row["coverage_exact_95_lower"] == pytest.approx(
            float(record["coverage_exact_95_lower"])
        )


def test_calibration_sidecar_carries_the_no_precise_claim_boundary(calibration_built) -> None:
    """The registry forbids claiming coverage equals nominal; the figure records that."""

    _module, sidecar, _stem = calibration_built
    assert sidecar["precise_nominal_coverage_claim_authorized"] is False
    assert "does not authorize" in sidecar["interpretation_boundary"]
    assert sidecar["replicates"] == 20
    assert sidecar["suppressed_cells_total"] == 4337
