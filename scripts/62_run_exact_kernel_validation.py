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
from bayes_constrained.validation_cases import (  # noqa: E402
    structural_interval_path_frame,
    structural_interval_path_theta,
    structural_six_cycle_frame,
    structural_six_cycle_theta,
)


def _diagnostic_payload(diagnostics: object) -> dict[str, object]:
    return {key: getattr(diagnostics, key) for key in diagnostics.__dataclass_fields__}


def run_case(
    *,
    name: str,
    frame: object,
    theta: object,
    blocked_weights: dict[str, float],
    repaired_weights: dict[str, float],
    seed: int,
    max_cycle_half_length: int,
) -> dict[str, object]:
    states = enumerate_feasible_states(frame)
    design = make_design(frame)
    probabilities = exact_conditional_probabilities(states, theta, design)
    blocked_transition = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights=blocked_weights,
        max_cycle_half_length=max_cycle_half_length,
    )
    repaired_transition = exact_transition_matrix(
        states,
        frame,
        theta,
        design,
        weights=repaired_weights,
        max_cycle_half_length=max_cycle_half_length,
    )
    blocked = exact_kernel_diagnostics(probabilities, blocked_transition)
    repaired = exact_kernel_diagnostics(probabilities, repaired_transition)
    empirical = empirical_count_kernel_frequencies(
        states[0],
        states,
        frame,
        theta,
        steps=60_000,
        burn_in=2_000,
        seed=seed,
        weights=repaired_weights,
        max_cycle_half_length=max_cycle_half_length,
    )
    maximum_error = float(np.max(np.abs(empirical - probabilities)))
    return {
        "case": name,
        "feasible_states": int(len(states)),
        "exact_probabilities": probabilities.tolist(),
        "empirical_probabilities": empirical.tolist(),
        "maximum_empirical_absolute_error": maximum_error,
        "blocked_kernel": _diagnostic_payload(blocked),
        "repaired_kernel": _diagnostic_payload(repaired),
        "pass": bool(
            blocked.strongly_connected_components > 1
            and repaired.strongly_connected_components == 1
            and repaired.row_sum_error < 1e-12
            and repaired.stationarity_error < 1e-12
            and repaired.detailed_balance_error < 1e-12
            and maximum_error < 0.025
        ),
    }


def main() -> None:
    cycle_frame = structural_six_cycle_frame()
    path_frame = structural_interval_path_frame()
    cases = [
        run_case(
            name="chordless_six_cycle_structural_support",
            frame=cycle_frame,
            theta=structural_six_cycle_theta(cycle_frame),
            blocked_weights={
                "state_year_transfer": 0.0,
                "county_period_exploration": 0.0,
                "interval_path_transfer": 0.0,
                "swap_2x2": 1.0,
                "cycle_swap": 0.0,
            },
            repaired_weights={
                "state_year_transfer": 0.0,
                "county_period_exploration": 0.0,
                "interval_path_transfer": 0.0,
                "swap_2x2": 0.0,
                "cycle_swap": 1.0,
            },
            seed=20260810,
            max_cycle_half_length=6,
        ),
        run_case(
            name="cross_year_interval_endpoint_path",
            frame=path_frame,
            theta=structural_interval_path_theta(path_frame),
            blocked_weights={
                "state_year_transfer": 0.25,
                "county_period_exploration": 0.25,
                "interval_path_transfer": 0.0,
                "swap_2x2": 0.25,
                "cycle_swap": 0.25,
            },
            repaired_weights={
                "state_year_transfer": 0.0,
                "county_period_exploration": 0.0,
                "interval_path_transfer": 1.0,
                "swap_2x2": 0.0,
                "cycle_swap": 0.0,
            },
            seed=20260811,
            max_cycle_half_length=2,
        ),
    ]
    payload = {
        "cases": cases,
        "cases_passed": int(sum(bool(case["pass"]) for case in cases)),
        "cases_total": len(cases),
        "pass": all(bool(case["pass"]) for case in cases),
    }

    output_dir = ROOT / "outputs" / "scientific_reports_v2" / "exact_kernel_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "exact_kernel_validation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Exact enumerable-kernel validation",
        "",
        "Two deliberately adversarial finite fibers are evaluated against their exact conditional posterior distributions.",
        "",
        "1. A chordless six-cycle demonstrates that transfer and 2x2 moves do not form a universal connecting move family.",
        "2. A cross-year path between interval-margin endpoints demonstrates that cycles plus same-year interval transfers are also insufficient in general.",
        "",
    ]
    for case in cases:
        blocked = case["blocked_kernel"]
        repaired = case["repaired_kernel"]
        lines.extend(
            [
                f"## {case['case']}",
                "",
                f"- Feasible states: {case['feasible_states']}",
                f"- Exact probabilities: {case['exact_probabilities']}",
                f"- Empirical probabilities: {case['empirical_probabilities']}",
                f"- Maximum empirical absolute error: {case['maximum_empirical_absolute_error']:.6f}",
                f"- Blocked strongly connected components: {blocked['strongly_connected_components']}",
                f"- Repaired strongly connected components: {repaired['strongly_connected_components']}",
                f"- Repaired stationarity error: {repaired['stationarity_error']:.3e}",
                f"- Repaired detailed-balance error: {repaired['detailed_balance_error']:.3e}",
                f"- Status: {'PASS' if case['pass'] else 'FAIL'}",
                "",
            ]
        )
    lines.extend(
        [
            f"Overall status: **{'PASS' if payload['pass'] else 'FAIL'}**.",
            "",
            "These finite tests establish correctness for the enumerated cases; they do not replace full-data dispersed-start, movement, and joint-chain diagnostics.",
        ]
    )
    (output_dir / "exact_kernel_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not payload["pass"]:
        raise SystemExit("Exact kernel validation failed.")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
