from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .calibration import CalibrationTruth, make_calibration_truth
from .model import Theta, make_design


@dataclass(frozen=True)
class CalibrationScenario:
    replicate_id: int
    scenario_id: str
    baseline_rate_per_100k: float
    kappa: float
    truth_seed: int
    count_seed: int
    initialization_seed_base: int

    def to_dict(self) -> dict[str, int | float | str]:
        return {
            "replicate_id": int(self.replicate_id),
            "scenario_id": self.scenario_id,
            "baseline_rate_per_100k": float(self.baseline_rate_per_100k),
            "kappa": float(self.kappa),
            "truth_seed": int(self.truth_seed),
            "count_seed": int(self.count_seed),
            "initialization_seed_base": int(self.initialization_seed_base),
        }


BATCH1_SCENARIOS = (
    CalibrationScenario(
        replicate_id=1,
        scenario_id="baseline_rate_3_4_kappa_10",
        baseline_rate_per_100k=3.4,
        kappa=10.0,
        truth_seed=51001,
        count_seed=52001,
        initialization_seed_base=53010,
    ),
    CalibrationScenario(
        replicate_id=2,
        scenario_id="lower_rate_2_4_kappa_10",
        baseline_rate_per_100k=2.4,
        kappa=10.0,
        truth_seed=51002,
        count_seed=52002,
        initialization_seed_base=53020,
    ),
    CalibrationScenario(
        replicate_id=3,
        scenario_id="higher_rate_5_0_kappa_10",
        baseline_rate_per_100k=5.0,
        kappa=10.0,
        truth_seed=51003,
        count_seed=52003,
        initialization_seed_base=53030,
    ),
    CalibrationScenario(
        replicate_id=4,
        scenario_id="baseline_rate_3_4_kappa_4",
        baseline_rate_per_100k=3.4,
        kappa=4.0,
        truth_seed=51004,
        count_seed=52004,
        initialization_seed_base=53040,
    ),
)


CALIBRATION_SCENARIO_FAMILIES = (
    ("baseline_rate_3_4_kappa_10", 3.4, 10.0),
    ("lower_rate_2_4_kappa_10", 2.4, 10.0),
    ("higher_rate_5_0_kappa_10", 5.0, 10.0),
    ("baseline_rate_3_4_kappa_4", 3.4, 4.0),
)


def _batch2_scenarios() -> tuple[CalibrationScenario, ...]:
    """Return 16 frozen replicates: four new seeds per scenario family."""

    scenarios: list[CalibrationScenario] = []
    for replicate_id in range(1, 17):
        scenario_id, baseline_rate, kappa = CALIBRATION_SCENARIO_FAMILIES[
            (replicate_id - 1) % len(CALIBRATION_SCENARIO_FAMILIES)
        ]
        scenarios.append(
            CalibrationScenario(
                replicate_id=replicate_id,
                scenario_id=scenario_id,
                baseline_rate_per_100k=baseline_rate,
                kappa=kappa,
                truth_seed=71000 + replicate_id,
                count_seed=72000 + replicate_id,
                initialization_seed_base=73000 + replicate_id * 10,
            )
        )
    return tuple(scenarios)


BATCH2_SCENARIOS = _batch2_scenarios()
BATCH_SCENARIOS = {
    1: BATCH1_SCENARIOS,
    2: BATCH2_SCENARIOS,
}


def scenarios_for_batch(batch_id: int) -> tuple[CalibrationScenario, ...]:
    try:
        return BATCH_SCENARIOS[int(batch_id)]
    except KeyError as exc:
        raise ValueError(
            f"Unknown calibration batch {batch_id}; expected one of "
            f"{sorted(BATCH_SCENARIOS)}."
        ) from exc


def valid_replicates_for_batch(batch_id: int) -> tuple[int, ...]:
    return tuple(item.replicate_id for item in scenarios_for_batch(batch_id))


def scenario_for_replicate(
    replicate_id: int,
    *,
    batch_id: int = 1,
) -> CalibrationScenario:
    scenarios = scenarios_for_batch(batch_id)
    for scenario in scenarios:
        if scenario.replicate_id == int(replicate_id):
            return scenario
    raise ValueError(
        f"Unknown batch-{batch_id} calibration replicate {replicate_id}; "
        f"expected one of {[item.replicate_id for item in scenarios]}."
    )


def make_scenario_truth(
    frame: pd.DataFrame,
    scenario: CalibrationScenario,
) -> tuple[Theta, CalibrationTruth]:
    """Construct the common coefficient truth with scenario-specific rate/dispersion."""

    theta, truth = make_calibration_truth(
        frame,
        seed=scenario.truth_seed,
        kappa=scenario.kappa,
    )
    design = make_design(frame)
    try:
        intercept_index = design.columns.index("Intercept")
    except ValueError as exc:
        raise ValueError("Calibration design has no intercept column.") from exc
    beta = theta.beta.copy()
    beta[intercept_index] = float(
        np.log(scenario.baseline_rate_per_100k / 100000.0)
    )
    updated_theta = Theta(
        beta=beta,
        state_effect=theta.state_effect.copy(),
        year_effect=theta.year_effect.copy(),
        log_sigma_state=float(theta.log_sigma_state),
        log_sigma_year=float(theta.log_sigma_year),
        log_kappa=float(np.log(scenario.kappa)),
    )
    updated_truth = CalibrationTruth(
        beta_by_term={
            term: float(value) for term, value in zip(design.columns, beta)
        },
        state_effect_by_fips=truth.state_effect_by_fips,
        year_effect_by_year=truth.year_effect_by_year,
        kappa=float(scenario.kappa),
        seed=int(scenario.truth_seed),
    )
    return updated_theta, updated_truth
