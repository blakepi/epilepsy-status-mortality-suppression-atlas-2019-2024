"""Contract tests for deterministic manuscript-result population.

Every manuscript number must be traceable to a frozen artifact, so this checks
that the generator reads the frozen evidence rather than restating it, refuses
to run when the production gate has not passed, leaves not-yet-earned
placeholders alone, and never edits the working draft in place.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "111_populate_sr_v2_manuscript_results.py"
DRAFT = ROOT / "manuscript/scientific_reports_v2/manuscript_draft_nonfinal.md"
PRIMARY = ROOT / "outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv"

# Placeholders that cannot be earned until the robustness package has run, the
# archive exists, or an institutional record is supplied.
NOT_YET_EARNED = {
    "AUTHOR_BLOCK",
    "DISCUSSION_SUPPRESSION_RESULT",
    "ETHICS_DETERMINATION",
    "FINAL_DISCUSSION_SENTENCE",
    "ONE_SENTENCE_ROBUSTNESS_RESULT",
    "REPOSITORY_DOI",
    "REPOSITORY_DOI_AND_VERSION",
    "REPOSITORY_VERSION",
    "ROBUSTNESS_RESULTS_PARAGRAPH",
    "SPATIAL_MODEL_RESULT",
    "SUPPLEMENT_ACCEPTANCE_TABLE",
    "SUPPLEMENT_PARAMETER_TABLE",
    "SUPPRESSION_SENSITIVITY_RESULT",
}


def load_generator() -> Any:
    spec = importlib.util.spec_from_file_location("sr_v2_manuscript_results", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generator_resolves_only_gate_backed_placeholders() -> None:
    module = load_generator()
    resolved = module.resolve()
    assert set(resolved).isdisjoint(NOT_YET_EARNED)
    for name, record in resolved.items():
        assert record["value"], name
        assert record["source"], name


def test_every_resolved_value_names_a_frozen_artifact() -> None:
    module = load_generator()
    for name, record in module.resolve().items():
        source = ROOT / "outputs/scientific_reports_v2" / record["source"]
        assert source.is_file(), f"{name} cites a missing artifact: {record['source']}"


def test_primary_estimates_match_the_frozen_summary_exactly() -> None:
    """The generator must read the frozen CSV, never restate a remembered value."""

    module = load_generator()
    resolved = module.resolve()
    row = module.load_primary()[module.PRIMARY_CONTRAST]
    assert resolved["PRIMARY_IRR"]["value"] == f"{float(row['posterior_mean']):.2f}"
    lower = float(row["credible_interval_lower_95"])
    upper = float(row["credible_interval_upper_95"])
    assert resolved["PRIMARY_CRI"]["value"] == f"{lower:.2f} to {upper:.2f}"


def test_posterior_probability_is_reported_at_a_resolvable_bound() -> None:
    """A finite sample cannot establish a probability of exactly one."""

    module = load_generator()
    statement = module.resolve()["PRIMARY_POSTERIOR_PROBABILITY_STATEMENT"]["value"]
    assert "greater than" in statement
    assert not re.search(r"\bprobability (of |was )?1(\.0+)?\b", statement)


def test_generator_refuses_when_the_production_gate_has_not_passed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_generator()
    failed = tmp_path / "production_gate.json"
    failed.write_text(json.dumps({"passed": False}), encoding="utf-8")
    monkeypatch.setattr(module, "PRODUCTION", tmp_path)
    with pytest.raises(SystemExit):
        module.load_gate()


def test_check_mode_writes_no_file_and_reports_outstanding_work(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_generator()
    assert module.main(["--check"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_id"] == "sr_v2_manuscript_results/v1"
    assert set(report["outstanding_placeholders"]) == NOT_YET_EARNED
    assert report["submission_ready"] is False


def test_the_working_draft_is_never_edited_in_place() -> None:
    """The draft stays the single editable source; the filled copy is derived."""

    module = load_generator()
    before = DRAFT.read_bytes()
    module.main([])
    assert DRAFT.read_bytes() == before
    assert "{{PRIMARY_IRR}}" in before.decode("utf-8")


def test_derived_manuscript_retains_exactly_the_unearned_placeholders() -> None:
    module = load_generator()
    module.main([])
    derived = (module.DESTINATION / "manuscript_draft_resolved.md").read_text(encoding="utf-8")
    assert set(re.findall(r"\{\{([A-Z_]+)\}\}", derived)) == NOT_YET_EARNED
