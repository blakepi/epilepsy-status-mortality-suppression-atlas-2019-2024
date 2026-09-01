from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .constraints import validate_constraints
from .exact_validation import (
    enumerate_feasible_states,
    exact_conditional_probabilities,
    exact_kernel_diagnostics,
    exact_transition_matrix,
)
from .model import Theta, make_design


@dataclass(frozen=True)
class RandomCaseResult:
    case_id: int
    feasible_states: int
    free_cells: int
    exact_county_margins: int
    interval_county_margins: int
    legacy_components: int
    repaired_components: int
    row_sum_error: float
    stationarity_error: float
    detailed_balance_error: float
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def generate_random_case(rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray, Theta]:
    counties = ["01001", "01003", "01005"]
    rurality = ["metro_large", "metro_other", "nonmetro_adjacent"]
    years = ["2019", "2020", "2021"]

    for _ in range(2_000):
        truth = rng.integers(1, 3, size=(3, 3), endpoint=False)
        free_mask = rng.random((3, 3)) < rng.uniform(0.55, 0.90)
        free_count = int(free_mask.sum())
        if not 4 <= free_count <= 8:
            continue
        if (free_mask.sum(axis=0) < 2).any():
            continue

        rows: list[dict[str, object]] = []
        county_bounds: list[tuple[int, int, str]] = []
        for county_index in range(3):
            cell_lower = np.where(free_mask[county_index], 1, truth[county_index])
            cell_upper = np.where(free_mask[county_index], 2, truth[county_index])
            total = int(truth[county_index].sum())
            use_exact = bool(rng.uniform() < 0.55)
            lower_total = int(cell_lower.sum())
            upper_total = int(cell_upper.sum())
            if use_exact or lower_total == upper_total:
                county_bounds.append((total, total, "exact"))
            else:
                lower_total = max(1, lower_total)
                if not lower_total <= total <= upper_total:
                    break
                county_bounds.append((lower_total, upper_total, "suppressed_1_9"))
        if len(county_bounds) != 3:
            continue

        year_totals = truth.sum(axis=0).astype(int)
        for county_index, county in enumerate(counties):
            period_lower, period_upper, period_status = county_bounds[county_index]
            for year_index, year in enumerate(years):
                free = bool(free_mask[county_index, year_index])
                value = int(truth[county_index, year_index])
                rows.append(
                    {
                        "county_fips": county,
                        "county_name": f"Toy {county_index + 1}",
                        "state_fips": "01",
                        "state_name": "Toy",
                        "year": year,
                        "population": float(700 + 450 * county_index + 80 * year_index),
                        "q002_count_status": "suppressed_1_9" if free else "exact",
                        "q002_lower": 1 if free else value,
                        "q002_upper": 2 if free else value,
                        "q001_period_status": period_status,
                        "q001_period_lower": period_lower,
                        "q001_period_upper": period_upper,
                        "q004_state_year_total": int(year_totals[year_index]),
                        "q003_national_year_total": int(year_totals[year_index]),
                        "primary_rurality": rurality[county_index],
                        "svi_quartile": ["Q1_lowest", "Q2", "Q3"][county_index],
                        "z_pct_age65": float(county_index - 1),
                        "z_pct_male": float(year_index - 1),
                    }
                )
        frame = pd.DataFrame(rows)
        frame.attrs["grand_total"] = int(truth.sum())
        flattened = truth.reshape(-1).astype(int)
        if not validate_constraints(flattened, frame).passed:
            continue

        try:
            states = enumerate_feasible_states(frame, max_candidates=20_000)
        except ValueError:
            continue
        if not 2 <= len(states) <= 150:
            continue

        design = make_design(frame)
        beta = rng.normal(0.0, 0.35, size=len(design.columns))
        beta[0] = -6.8
        state_effect = np.zeros(len(design.states), dtype=float)
        year_effect = rng.normal(0.0, 0.35, size=len(design.years))
        year_effect -= year_effect.mean()
        theta = Theta(
            beta=beta,
            state_effect=state_effect,
            year_effect=year_effect,
            log_sigma_state=np.log(0.25),
            log_sigma_year=np.log(0.25),
            log_kappa=np.log(float(rng.uniform(1.5, 8.0))),
        )
        return frame, states, theta
    raise RuntimeError("Unable to generate a suitable enumerable random case.")


def validate_random_cases(*, cases: int = 30, seed: int = 20260810) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    for case_id in range(1, cases + 1):
        frame, states, theta = generate_random_case(rng)
        design = make_design(frame)
        probabilities = exact_conditional_probabilities(states, theta, design)
        legacy_transition = exact_transition_matrix(
            states,
            frame,
            theta,
            design,
            weights={
                "state_year_transfer": 0.55,
                "county_period_exploration": 0.20,
                "interval_path_transfer": 0.0,
                "swap_2x2": 0.25,
                "cycle_swap": 0.0,
            },
            max_cycle_half_length=3,
        )
        repaired_transition = exact_transition_matrix(
            states,
            frame,
            theta,
            design,
            weights={
                "state_year_transfer": 0.05,
                "county_period_exploration": 0.25,
                "interval_path_transfer": 0.30,
                "swap_2x2": 0.25,
                "cycle_swap": 0.15,
            },
            max_cycle_half_length=3,
        )
        legacy = exact_kernel_diagnostics(probabilities, legacy_transition)
        repaired = exact_kernel_diagnostics(probabilities, repaired_transition)
        passed = bool(
            repaired.strongly_connected_components == 1
            and repaired.row_sum_error < 1e-12
            and repaired.stationarity_error < 1e-12
            and repaired.detailed_balance_error < 1e-12
        )
        county = frame.drop_duplicates("county_fips")
        exact_counties = int(
            pd.to_numeric(county["q001_period_lower"], errors="raise").eq(
                pd.to_numeric(county["q001_period_upper"], errors="raise")
            ).sum()
        )
        result = RandomCaseResult(
            case_id=case_id,
            feasible_states=int(len(states)),
            free_cells=int((frame["q002_upper"] > frame["q002_lower"]).sum()),
            exact_county_margins=exact_counties,
            interval_county_margins=int(len(county) - exact_counties),
            legacy_components=int(legacy.strongly_connected_components),
            repaired_components=int(repaired.strongly_connected_components),
            row_sum_error=float(repaired.row_sum_error),
            stationarity_error=float(repaired.stationarity_error),
            detailed_balance_error=float(repaired.detailed_balance_error),
            passed=passed,
        )
        rows.append(result.to_dict())
        if not passed:
            failures.append(
                {
                    "case_id": case_id,
                    "frame": frame.to_dict("records"),
                    "states": states.tolist(),
                    "probabilities": probabilities.tolist(),
                    "result": result.to_dict(),
                }
            )
    return pd.DataFrame(rows), failures
