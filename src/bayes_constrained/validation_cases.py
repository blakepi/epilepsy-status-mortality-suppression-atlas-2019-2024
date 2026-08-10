from __future__ import annotations

import numpy as np
import pandas as pd

from .model import Theta, make_design


def structural_six_cycle_frame() -> pd.DataFrame:
    """Two-state fiber that cannot be traversed by 2x2 moves.

    The free-cell support is a chordless six-cycle. Every county-period and
    year margin is fixed. The two feasible allocations differ by an
    alternating length-six cycle, while no all-free 2x2 rectangle exists.
    """

    counties = [
        ("01001", "A", "metro_large", 850.0),
        ("01003", "B", "metro_other", 1500.0),
        ("01005", "C", "nonmetro_adjacent", 1050.0),
    ]
    years = ["2019", "2020", "2021"]
    free = {
        ("01001", "2019"),
        ("01001", "2020"),
        ("01003", "2020"),
        ("01003", "2021"),
        ("01005", "2021"),
        ("01005", "2019"),
    }
    rows = []
    for county_fips, county_name, rurality, base_population in counties:
        for year_index, year in enumerate(years):
            is_free = (county_fips, year) in free
            rows.append(
                {
                    "county_fips": county_fips,
                    "county_name": county_name,
                    "state_fips": "01",
                    "state_name": "Toy",
                    "year": year,
                    "population": base_population + 50.0 * year_index,
                    "q002_count_status": "suppressed_1_9" if is_free else "zero",
                    "q002_lower": 1 if is_free else 0,
                    "q002_upper": 2 if is_free else 0,
                    "q001_period_status": "exact",
                    "q001_period_lower": 3,
                    "q001_period_upper": 3,
                    "q004_state_year_total": 3,
                    "q003_national_year_total": 3,
                    "primary_rurality": rurality,
                    "svi_quartile": "Q1_lowest",
                    "z_pct_age65": 0.0,
                    "z_pct_male": 0.0,
                }
            )
    frame = pd.DataFrame(rows)
    frame.attrs["grand_total"] = 9
    return frame


def structural_six_cycle_theta(frame: pd.DataFrame) -> Theta:
    design = make_design(frame)
    beta = np.zeros(len(design.columns), dtype=float)
    beta[0] = -6.8
    if "primary_rurality_metro_other" in design.columns:
        beta[design.columns.index("primary_rurality_metro_other")] = 1.2
    if "primary_rurality_nonmetro_adjacent" in design.columns:
        beta[design.columns.index("primary_rurality_nonmetro_adjacent")] = -1.0
    return Theta(
        beta=beta,
        state_effect=np.zeros(len(design.states), dtype=float),
        year_effect=np.asarray([0.8, -0.4, -0.4], dtype=float),
        log_sigma_state=np.log(0.2),
        log_sigma_year=np.log(0.2),
        log_kappa=np.log(3.0),
    )
