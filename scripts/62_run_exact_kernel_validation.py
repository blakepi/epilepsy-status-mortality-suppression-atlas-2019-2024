from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.exact_validation import (  # noqa: E402
    empirical_count_kernel_frequencies,
    enumerate_feasible_states,
    exact_conditional_probabilities,
    exact_kernel_diagnostics,
    exact_transition_matrix,
)
from bayes_constrained.model import make_design  # noqa: E402
from bayes_constrained.validation_cases import structural_six_cycle_frame, structural_six_cycle_theta  # noqa: E402


def _diagnostic_payload(diagnostics: object) -> dict[str, object]:
    return {key: getattr(diagnostics, key) for key in diagnostics.__dataclass_fields__}


def main() -> None:
    frame = structural_six_cycle_frame()
    states = enumerate_feasible_states(frame)
    theta = structural_six_cycle_theta(frame)
    design = make_design(frame)
    probabilities = exact_conditional_probabilities(states, theta, design)

    legacy_transition = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "swap_2x2": 1.0,
            "cycle_swap": 0.0,
        },
    )
    repaired_transition = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "swap_2x2": 0.0,
            "cycle_swap": 1.0,
        },
    )
    legacy = exact_kernel_diagnostics(probabilities, legacy_transition)
    repaired = exact_kernel_diagnostics(probabilities, repaired_transition)
    empirical = empirical_count_kernel_frequencies(
        states[0],
        states,
        frame,
        theta,
        steps=100_000,
        burn_in=5_000,
        seed=20260810,
        weights={
            "state_year_transfer": 0.0,
            "county_period_exploration": 0.0,
            "swap_2x2": 0.0,
            "cycle_swap": 1.0,
        },
    )

    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "exact_kernel_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "case": "chordless_six_cycle_structural_support",
        "feasible_states": int(len(states)),
        "exact_probabilities": probabilities.tolist(),
        "empirical_probabilities": empirical.tolist(),
        "maximum_empirical_absolute_error": float(np.max(np.abs(empirical - probabilities))),
        "legacy_2x2_only": _diagnostic_payload(legacy),
        "repaired_general_cycle": _diagnostic_payload(repaired),
        "pass": bool(
            legacy.strongly_connected_components > 1
            and repaired.strongly_connected_components == 1
            and repaired.row_sum_error < 1e-12
            and repaired.stationarity_error < 1e-12
            and repaired.detailed_balance_error < 1e-12
            and np.max(np.abs(empirical - probabilities)) < 0.025
        ),
    }
    (output_dir / "exact_kernel_validation.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Exact enumerable-kernel validation",
        "",
        "The test fiber contains two legal allocations separated by a chordless six-cycle in the free-cell support. The v1.1.1 transfer/2x2 move family cannot move between them. The Scientific Reports v2 general-cycle proposal connects the fiber while preserving exact margins.",
        "",
        f"- Feasible states: {len(states)}",
        f"- Exact probabilities: {probabilities.tolist()}",
        f"- Empirical probabilities: {empirical.tolist()}",
        f"- Maximum empirical absolute error: {payload['maximum_empirical_absolute_error']:.6f}",
        f"- Legacy strongly connected components: {legacy.strongly_connected_components}",
        f"- Repaired strongly connected components: {repaired.strongly_connected_components}",
        f"- Repaired stationarity error: {repaired.stationarity_error:.3e}",
        f"- Repaired detailed-balance error: {repaired.detailed_balance_error:.3e}",
        f"- Final status: {'PASS' if payload['pass'] else 'FAIL'}",
        "",
        "This finite test establishes correctness for the enumerated case; it is not, by itself, a proof that every full-data fiber is connected. Additional support-graph and dispersed-start diagnostics remain required before the corrected production run is frozen.",
    ]
    (output_dir / "exact_kernel_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not payload["pass"]:
        raise SystemExit("Exact kernel validation failed.")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
