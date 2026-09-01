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


def structural_interval_path_frame() -> pd.DataFrame:
    """Two-state fiber requiring a path between interval-margin endpoints.

    County A has one free cell in 2019, county B has one free cell in 2020,
    and exact-margin county C connects the two years. Changing the admissible
    allocation requires an alternating A-2019-C-2020-B path. Same-year
    interval transfers and all cycle moves are unavailable.
    """

    rows = [
        {
            "county_fips": "01001",
            "county_name": "A",
            "state_fips": "01",
            "state_name": "Toy",
            "year": "2019",
            "population": 800.0,
            "q002_count_status": "suppressed_1_9",
            "q002_lower": 1,
            "q002_upper": 2,
            "q001_period_status": "suppressed_1_9",
            "q001_period_lower": 1,
            "q001_period_upper": 2,
            "q004_state_year_total": 3,
            "q003_national_year_total": 3,
            "primary_rurality": "metro_large",
            "svi_quartile": "Q1_lowest",
            "z_pct_age65": -1.0,
            "z_pct_male": 0.0,
        },
        {
            "county_fips": "01001",
            "county_name": "A",
            "state_fips": "01",
            "state_name": "Toy",
            "year": "2020",
            "population": 820.0,
            "q002_count_status": "zero",
            "q002_lower": 0,
            "q002_upper": 0,
            "q001_period_status": "suppressed_1_9",
            "q001_period_lower": 1,
            "q001_period_upper": 2,
            "q004_state_year_total": 3,
            "q003_national_year_total": 3,
            "primary_rurality": "metro_large",
            "svi_quartile": "Q1_lowest",
            "z_pct_age65": -1.0,
            "z_pct_male": 0.0,
        },
        {
            "county_fips": "01003",
            "county_name": "B",
            "state_fips": "01",
            "state_name": "Toy",
            "year": "2019",
            "population": 1200.0,
            "q002_count_status": "zero",
            "q002_lower": 0,
            "q002_upper": 0,
            "q001_period_status": "suppressed_1_9",
            "q001_period_lower": 1,
            "q001_period_upper": 2,
            "q004_state_year_total": 3,
            "q003_national_year_total": 3,
            "primary_rurality": "metro_other",
            "svi_quartile": "Q2",
            "z_pct_age65": 1.0,
            "z_pct_male": 0.0,
        },
        {
            "county_fips": "01003",
            "county_name": "B",
            "state_fips": "01",
            "state_name": "Toy",
            "year": "2020",
            "population": 1240.0,
            "q002_count_status": "suppressed_1_9",
            "q002_lower": 1,
            "q002_upper": 2,
            "q001_period_status": "suppressed_1_9",
            "q001_period_lower": 1,
            "q001_period_upper": 2,
            "q004_state_year_total": 3,
            "q003_national_year_total": 3,
            "primary_rurality": "metro_other",
            "svi_quartile": "Q2",
            "z_pct_age65": 1.0,
            "z_pct_male": 0.0,
        },
        {
            "county_fips": "01005",
            "county_name": "C",
            "state_fips": "01",
            "state_name": "Toy",
            "year": "2019",
            "population": 1000.0,
            "q002_count_status": "suppressed_1_9",
            "q002_lower": 1,
            "q002_upper": 2,
            "q001_period_status": "exact",
            "q001_period_lower": 3,
            "q001_period_upper": 3,
            "q004_state_year_total": 3,
            "q003_national_year_total": 3,
            "primary_rurality": "nonmetro_adjacent",
            "svi_quartile": "Q3",
            "z_pct_age65": 0.0,
            "z_pct_male": 0.0,
        },
        {
            "county_fips": "01005",
            "county_name": "C",
            "state_fips": "01",
            "state_name": "Toy",
            "year": "2020",
            "population": 1030.0,
            "q002_count_status": "suppressed_1_9",
            "q002_lower": 1,
            "q002_upper": 2,
            "q001_period_status": "exact",
            "q001_period_lower": 3,
            "q001_period_upper": 3,
            "q004_state_year_total": 3,
            "q003_national_year_total": 3,
            "primary_rurality": "nonmetro_adjacent",
            "svi_quartile": "Q3",
            "z_pct_age65": 0.0,
            "z_pct_male": 0.0,
        },
    ]
    frame = pd.DataFrame(rows)
    frame.attrs["grand_total"] = 6
    return frame


def structural_interval_path_theta(frame: pd.DataFrame) -> Theta:
    design = make_design(frame)
    beta = np.zeros(len(design.columns), dtype=float)
    beta[0] = -6.7
    if "primary_rurality_metro_other" in design.columns:
        beta[design.columns.index("primary_rurality_metro_other")] = 0.8
    if "primary_rurality_nonmetro_adjacent" in design.columns:
        beta[design.columns.index("primary_rurality_nonmetro_adjacent")] = -0.5
    return Theta(
        beta=beta,
        state_effect=np.zeros(len(design.states), dtype=float),
        year_effect=np.asarray([0.35, -0.35], dtype=float),
        log_sigma_state=np.log(0.2),
        log_sigma_year=np.log(0.2),
        log_kappa=np.log(4.0),
    )
