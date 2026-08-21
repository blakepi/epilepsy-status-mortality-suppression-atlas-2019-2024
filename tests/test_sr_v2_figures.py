"""Contract tests for the corrected primary-association figure.

A figure is a claim about the data, so the same rule applies to it as to the
manuscript text: every plotted number must come from a frozen artifact, and
nothing may be drawn before the production gate has passed.
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
