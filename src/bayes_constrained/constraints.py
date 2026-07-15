from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy import sparse

from .data import GRAND_TOTAL
from .paths import BAYES_DATA, OUTPUT_DIR, rel


@dataclass
class ConstraintValidation:
    passed: bool
    checks: dict[str, bool]
    details: dict[str, object]

    def to_frame(self, label: str = "") -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "label": label,
                    "check": key,
                    "passed": bool(value),
                    "detail": self.details.get(key, ""),
                }
                for key, value in self.checks.items()
            ]
        )


def frame_arrays(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "lower": frame["q002_lower"].to_numpy(dtype=int),
        "upper": frame["q002_upper"].to_numpy(dtype=int),
        "status": frame["q002_count_status"].astype(str).to_numpy(),
        "county": frame["county_fips"].astype(str).to_numpy(),
        "state": frame["state_fips"].astype(str).to_numpy(),
        "year": frame["year"].astype(str).to_numpy(),
    }


def validate_constraints(y: np.ndarray, frame: pd.DataFrame, *, expected_rows: int | None = None) -> ConstraintValidation:
    y = np.asarray(y)
    arr = frame_arrays(frame)
    grand_total = int(frame.attrs.get("grand_total", GRAND_TOTAL))
    if expected_rows is None:
        expected_rows = len(frame)
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    checks["row_count_matches_frame"] = len(y) == expected_rows == len(frame)
    details["row_count_matches_frame"] = f"y={len(y)} frame={len(frame)} expected={expected_rows}"
    checks["all_counts_integer"] = bool(np.all(np.isclose(y, np.rint(y))))
    details["all_counts_integer"] = f"noninteger={int((~np.isclose(y, np.rint(y))).sum())}"
    y_int = np.rint(y).astype(int)
    checks["no_negative_counts"] = bool(np.all(y_int >= 0))
    details["no_negative_counts"] = f"min={int(y_int.min()) if len(y_int) else 'NA'}"
    checks["county_year_bounds_respected"] = bool(np.all((y_int >= arr["lower"]) & (y_int <= arr["upper"])))
    details["county_year_bounds_respected"] = f"violations={int(((y_int < arr['lower']) | (y_int > arr['upper'])).sum())}"

    exact_mask = arr["status"] == "exact"
    zero_mask = arr["status"] == "zero"
    supp_mask = arr["status"] == "suppressed_1_9"
    checks["exact_county_year_counts_unchanged"] = bool(np.all(y_int[exact_mask] == arr["lower"][exact_mask]))
    details["exact_county_year_counts_unchanged"] = f"violations={int((y_int[exact_mask] != arr['lower'][exact_mask]).sum())}"
    checks["explicit_zero_county_year_counts_unchanged"] = bool(np.all(y_int[zero_mask] == 0))
    details["explicit_zero_county_year_counts_unchanged"] = f"violations={int((y_int[zero_mask] != 0).sum())}"
    checks["suppressed_county_year_counts_remain_1_9"] = bool(np.all((y_int[supp_mask] >= 1) & (y_int[supp_mask] <= 9)))
    details["suppressed_county_year_counts_remain_1_9"] = f"violations={int(((y_int[supp_mask] < 1) | (y_int[supp_mask] > 9)).sum())}"

    work = frame[["county_fips", "year", "state_fips", "q001_period_lower", "q001_period_upper", "q004_state_year_total", "q003_national_year_total"]].copy()
    work["y"] = y_int
    county_sum = work.groupby("county_fips", sort=False)["y"].sum()
    period = frame.drop_duplicates("county_fips").set_index("county_fips")[["q001_period_lower", "q001_period_upper"]]
    period = period.loc[county_sum.index]
    period_ok = (county_sum >= period["q001_period_lower"]) & (county_sum <= period["q001_period_upper"])
    checks["county_period_constraints_respected"] = bool(period_ok.all())
    details["county_period_constraints_respected"] = f"violations={int((~period_ok).sum())}"

    state_year_sum = work.groupby(["state_fips", "year"], sort=False)["y"].sum()
    state_target = frame.drop_duplicates(["state_fips", "year"]).set_index(["state_fips", "year"])["q004_state_year_total"].loc[state_year_sum.index]
    state_ok = state_year_sum.astype(int).eq(state_target.astype(int))
    checks["state_year_totals_equal_q004"] = bool(state_ok.all())
    details["state_year_totals_equal_q004"] = f"violations={int((~state_ok).sum())}"

    national_year_sum = work.groupby("year", sort=False)["y"].sum()
    national_target = frame.drop_duplicates("year").set_index("year")["q003_national_year_total"].loc[national_year_sum.index]
    national_ok = national_year_sum.astype(int).eq(national_target.astype(int))
    checks["national_year_totals_equal_q003"] = bool(national_ok.all())
    details["national_year_totals_equal_q003"] = f"violations={int((~national_ok).sum())}"
    checks["grand_total_equals_58380"] = int(y_int.sum()) == grand_total
    details["grand_total_equals_58380"] = int(y_int.sum())
    checks["no_counties_silently_dropped"] = frame["county_fips"].nunique() == len(period)
    details["no_counties_silently_dropped"] = f"counties={frame['county_fips'].nunique()}"

    return ConstraintValidation(passed=all(checks.values()), checks=checks, details=details)


def assert_constraints(y: np.ndarray, frame: pd.DataFrame, *, label: str = "") -> ConstraintValidation:
    validation = validate_constraints(y, frame)
    if not validation.passed:
        failed = {key: validation.details[key] for key, value in validation.checks.items() if not value}
        raise AssertionError(f"Constraint validation failed for {label}: {failed}")
    return validation


def _constraint_matrix(frame: pd.DataFrame) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray]:
    n = len(frame)
    grand_total = int(frame.attrs.get("grand_total", GRAND_TOTAL))
    rows = []
    cols = []
    data = []
    lb = []
    ub = []
    row_id = 0

    def add_row(indices: np.ndarray, lower: float, upper: float) -> None:
        nonlocal row_id
        rows.extend([row_id] * len(indices))
        cols.extend(indices.tolist())
        data.extend([1.0] * len(indices))
        lb.append(float(lower))
        ub.append(float(upper))
        row_id += 1

    index = np.arange(n)
    for (_, _), group in frame.groupby(["state_fips", "year"], sort=False):
        target = int(group["q004_state_year_total"].iloc[0])
        add_row(index[group.index.to_numpy()], target, target)

    for _, group in frame.groupby("year", sort=False):
        target = int(group["q003_national_year_total"].iloc[0])
        add_row(index[group.index.to_numpy()], target, target)

    for _, group in frame.groupby("county_fips", sort=False):
        lower = int(group["q001_period_lower"].iloc[0])
        upper = int(group["q001_period_upper"].iloc[0])
        add_row(index[group.index.to_numpy()], lower, upper)

    add_row(index, grand_total, grand_total)
    matrix = sparse.csr_matrix((data, (rows, cols)), shape=(row_id, n))
    return matrix, np.asarray(lb), np.asarray(ub)


def solve_feasible_allocation(
    frame: pd.DataFrame,
    *,
    seed: int = 17291,
    objective: str = "random",
    time_limit_seconds: int = 300,
) -> np.ndarray:
    lower = frame["q002_lower"].to_numpy(dtype=float)
    upper = frame["q002_upper"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    if objective == "population":
        pop = pd.to_numeric(frame["population"], errors="coerce").to_numpy(dtype=float)
        pop = np.where(np.isfinite(pop), pop, np.nanmedian(pop))
        c = -pop / max(float(np.nanmax(pop)), 1.0) + rng.normal(0, 1e-4, len(frame))
    else:
        c = rng.normal(0, 1e-3, len(frame))

    matrix, lb, ub = _constraint_matrix(frame)
    constraints = LinearConstraint(matrix, lb=lb, ub=ub)
    result = milp(
        c=c,
        integrality=np.ones(len(frame), dtype=int),
        bounds=Bounds(lower, upper),
        constraints=constraints,
        options={"time_limit": time_limit_seconds, "mip_rel_gap": 0.0, "disp": False},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"SciPy MILP failed: status={result.status} message={result.message}")
    y = np.rint(result.x).astype(int)
    assert_constraints(y, frame, label=f"milp_seed_{seed}")
    return y


def solve_and_save_initial_allocations(frame: pd.DataFrame, seeds: list[int] | None = None) -> pd.DataFrame:
    if seeds is None:
        seeds = [17291, 17292, 17293, 17294]
    rows = []
    validation_frames = []
    for chain, seed in enumerate(seeds, start=1):
        y = solve_feasible_allocation(frame, seed=seed, objective="random")
        out = frame[["county_fips", "county_name", "state_fips", "state_name", "year", "population", "q002_count_status"]].copy()
        out["latent_count"] = y
        path = BAYES_DATA / f"initial_allocation_chain{chain}.parquet"
        out.to_parquet(path, index=False)
        csv_path = path.with_suffix(".csv.gz")
        out.to_csv(csv_path, index=False, compression="gzip")
        validation = assert_constraints(y, frame, label=f"chain{chain}_initial")
        validation_frames.append(validation.to_frame(f"chain{chain}_initial"))
        rows.append(
            {
                "chain": chain,
                "seed": seed,
                "path": rel(path),
                "csv_gz_path": rel(csv_path),
                "total": int(y.sum()),
                "validation_passed": validation.passed,
            }
        )
    init = pd.DataFrame(rows)
    init.to_csv(OUTPUT_DIR / "initial_allocation_manifest.csv", index=False)
    validation_df = pd.concat(validation_frames, ignore_index=True)
    validation_df.to_csv(OUTPUT_DIR / "constraint_validation_summary.csv", index=False)
    write_validation_markdown(validation_df, OUTPUT_DIR / "constraint_validation_summary.md")
    return init


def write_validation_markdown(validation_df: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Constraint Validation Summary",
        "",
        "| Label | Check | Passed | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in validation_df.iterrows():
        detail = str(row["detail"]).replace("|", "\\|")
        lines.append(f"| {row['label']} | {row['check']} | {row['passed']} | {detail} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_validation(label: str, validation: ConstraintValidation) -> None:
    path = OUTPUT_DIR / "constraint_validation_summary.csv"
    old = pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()
    new = validation.to_frame(label)
    out = pd.concat([old, new], ignore_index=True) if not old.empty else new
    out.to_csv(path, index=False)
    write_validation_markdown(out, OUTPUT_DIR / "constraint_validation_summary.md")
