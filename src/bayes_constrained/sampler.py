from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import time

import numpy as np
import pandas as pd

from .constraints import append_validation, assert_constraints, solve_and_save_initial_allocations
from .data import load_config
from .heatbath import feasible_amplitudes, sample_amplitude
from .interval_paths import IntervalPathSupport, build_interval_path_support, interval_path_direction
from .model import (
    DEFAULT_LIKELIHOOD_FAMILY,
    Design,
    Theta,
    count_logpmf,
    crude_intercept_prior,
    initialize_theta,
    log_posterior_theta,
    make_design,
    mu,
    normalize_likelihood_family,
)
from .paths import BAYES_DATA, OUTPUT_DIR, PROJECT_ROOT, rel


@dataclass
class MoveState:
    lower: np.ndarray
    upper: np.ndarray
    county_code: np.ndarray
    state_code: np.ndarray
    year_code: np.ndarray
    period_lower: np.ndarray
    period_upper: np.ndarray
    period_total: np.ndarray
    state_year_groups: list[np.ndarray]
    state_groups: dict[int, np.ndarray]
    state_counties: dict[int, np.ndarray]
    county_year_to_row: dict[tuple[int, int], int]
    free_by_state_year: list[np.ndarray]
    interval_counties: set[int]
    years: np.ndarray
    cycle_state_counties: list[tuple[int, np.ndarray]]
    interval_path_support: IntervalPathSupport


def _codes(series: pd.Series) -> tuple[np.ndarray, list[str]]:
    cats = sorted(series.astype(str).unique())
    mapping = {cat: i for i, cat in enumerate(cats)}
    return series.astype(str).map(mapping).to_numpy(dtype=int), cats


def build_move_state(frame: pd.DataFrame, y: np.ndarray) -> MoveState:
    lower = frame["q002_lower"].to_numpy(dtype=int)
    upper = frame["q002_upper"].to_numpy(dtype=int)
    county_code, counties = _codes(frame["county_fips"])
    state_code, _ = _codes(frame["state_fips"])
    year_code, _ = _codes(frame["year"])
    period = frame.drop_duplicates("county_fips").sort_values("county_fips")
    period_county_code = pd.Series(period["county_fips"]).map({county: i for i, county in enumerate(counties)}).to_numpy(dtype=int)
    period_lower = np.zeros(len(counties), dtype=int)
    period_upper = np.zeros(len(counties), dtype=int)
    period_lower[period_county_code] = period["q001_period_lower"].to_numpy(dtype=int)
    period_upper[period_county_code] = period["q001_period_upper"].to_numpy(dtype=int)
    period_total = np.bincount(county_code, weights=y, minlength=len(counties)).astype(int)

    state_year_groups: list[np.ndarray] = []
    free_by_state_year: list[np.ndarray] = []
    for s in sorted(np.unique(state_code)):
        for t in sorted(np.unique(year_code)):
            idx = np.where((state_code == s) & (year_code == t))[0]
            if len(idx):
                state_year_groups.append(idx)
                free_by_state_year.append(idx[upper[idx] > lower[idx]])

    state_groups = {int(s): np.where(state_code == s)[0] for s in np.unique(state_code)}
    state_counties = {int(s): np.unique(county_code[idx]) for s, idx in state_groups.items()}
    county_year_to_row = {(int(c), int(t)): int(i) for i, (c, t) in enumerate(zip(county_code, year_code))}
    interval_counties = set(np.where(period_upper > period_lower)[0].tolist())
    years = np.unique(year_code)
    free_mask = upper > lower
    cycle_state_counties: list[tuple[int, np.ndarray]] = []
    for state, state_county_codes in state_counties.items():
        candidates = []
        for county in state_county_codes:
            rows = np.where(
                (state_code == int(state))
                & (county_code == int(county))
                & free_mask
            )[0]
            if len(rows) >= 2:
                candidates.append(int(county))
        if len(candidates) >= 3 and len(years) >= 3:
            cycle_state_counties.append((int(state), np.asarray(candidates, dtype=int)))
    interval_path_support = build_interval_path_support(
        lower=lower,
        upper=upper,
        county_code=county_code,
        state_code=state_code,
        year_code=year_code,
        interval_counties=interval_counties,
        county_year_to_row=county_year_to_row,
    )
    return MoveState(
        lower=lower,
        upper=upper,
        county_code=county_code,
        state_code=state_code,
        year_code=year_code,
        period_lower=period_lower,
        period_upper=period_upper,
        period_total=period_total,
        state_year_groups=state_year_groups,
        state_groups=state_groups,
        state_counties=state_counties,
        county_year_to_row=county_year_to_row,
        free_by_state_year=free_by_state_year,
        interval_counties=interval_counties,
        years=years,
        cycle_state_counties=cycle_state_counties,
        interval_path_support=interval_path_support,
    )


def _local_loglik(
    y_values: np.ndarray,
    mu_values: np.ndarray,
    kappa: float | None,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> float:
    return float(
        count_logpmf(
            y_values,
            mu_values,
            likelihood_family=likelihood_family,
            kappa=kappa,
        ).sum()
    )


def _try_apply_delta(
    y: np.ndarray,
    move: MoveState,
    idx: np.ndarray,
    delta: np.ndarray,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> bool:
    old = y[idx]
    new = old + delta
    if np.any(new < move.lower[idx]) or np.any(new > move.upper[idx]):
        return False
    affected_counties = np.unique(move.county_code[idx])
    new_period_total = move.period_total[affected_counties].copy()
    for c in affected_counties:
        new_period_total[affected_counties == c] += int(delta[move.county_code[idx] == c].sum())
    if np.any(new_period_total < move.period_lower[affected_counties]) or np.any(new_period_total > move.period_upper[affected_counties]):
        return False
    old_ll = _local_loglik(
        old, current_mu[idx], kappa, likelihood_family=likelihood_family
    )
    new_ll = _local_loglik(
        new, current_mu[idx], kappa, likelihood_family=likelihood_family
    )
    if np.log(rng.uniform()) < new_ll - old_ll:
        y[idx] = new
        for c in affected_counties:
            move.period_total[c] += int(delta[move.county_code[idx] == c].sum())
        return True
    return False



def _apply_heatbath_direction(
    y: np.ndarray,
    move: MoveState,
    indices: np.ndarray,
    direction: np.ndarray,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> bool:
    indices = np.asarray(indices, dtype=int)
    direction = np.asarray(direction, dtype=int)
    amplitudes = feasible_amplitudes(
        y,
        indices,
        direction,
        lower=move.lower,
        upper=move.upper,
        county_code=move.county_code,
        period_total=move.period_total,
        period_lower=move.period_lower,
        period_upper=move.period_upper,
    )
    amplitude = sample_amplitude(
        y,
        indices,
        direction,
        amplitudes,
        current_mu[indices],
        kappa,
        rng,
        likelihood_family=likelihood_family,
    )
    if amplitude == 0:
        return False
    change = amplitude * direction
    y[indices] += change
    for county in np.unique(move.county_code[indices]):
        move.period_total[county] += int(change[move.county_code[indices] == county].sum())
    return True

def state_year_transfer(
    y: np.ndarray,
    move: MoveState,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> bool:
    groups = [g for g in move.free_by_state_year if len(g) >= 2]
    if not groups:
        return False
    group = groups[int(rng.integers(0, len(groups)))]
    a, b = rng.choice(group, size=2, replace=False)
    return _apply_heatbath_direction(
        y,
        move,
        np.asarray([a, b]),
        np.asarray([-1, 1]),
        current_mu,
        kappa,
        rng,
        likelihood_family=likelihood_family,
    )

def period_interval_transfer(
    y: np.ndarray,
    move: MoveState,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> bool:
    groups = []
    for group in move.free_by_state_year:
        if len(group) < 2:
            continue
        county = move.county_code[group]
        mask = np.asarray([int(code) in move.interval_counties for code in county])
        if mask.sum() >= 2:
            groups.append(group[mask])
    if not groups:
        return False
    group = groups[int(rng.integers(0, len(groups)))]
    a, b = rng.choice(group, size=2, replace=False)
    return _apply_heatbath_direction(
        y,
        move,
        np.asarray([a, b]),
        np.asarray([-1, 1]),
        current_mu,
        kappa,
        rng,
        likelihood_family=likelihood_family,
    )


def interval_path_transfer(
    y: np.ndarray,
    move: MoveState,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> bool:
    groups = move.interval_path_support.endpoint_groups
    if not groups:
        return False
    group = groups[int(rng.integers(0, len(groups)))]
    endpoint_a, endpoint_b = rng.choice(group, size=2, replace=False)
    proposal = interval_path_direction(
        int(endpoint_a),
        int(endpoint_b),
        state_code=move.state_code,
        year_code=move.year_code,
        support=move.interval_path_support,
    )
    if proposal is None:
        return False
    indices, direction = proposal
    return _apply_heatbath_direction(
        y,
        move,
        indices,
        direction,
        current_mu,
        kappa,
        rng,
        likelihood_family=likelihood_family,
    )

def state_2x2_swap(
    y: np.ndarray,
    move: MoveState,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> bool:
    states = [state for state, counties in move.state_counties.items() if len(counties) >= 2]
    if not states:
        return False
    state = states[int(rng.integers(0, len(states)))]
    counties = rng.choice(move.state_counties[state], size=2, replace=False)
    if len(move.years) < 2:
        return False
    year_a, year_b = rng.choice(move.years, size=2, replace=False)
    keys = [
        (int(counties[0]), int(year_a)),
        (int(counties[0]), int(year_b)),
        (int(counties[1]), int(year_a)),
        (int(counties[1]), int(year_b)),
    ]
    if any(key not in move.county_year_to_row for key in keys):
        return False
    indices = np.asarray([move.county_year_to_row[key] for key in keys], dtype=int)
    if np.any(move.upper[indices] <= move.lower[indices]):
        return False
    return _apply_heatbath_direction(
        y,
        move,
        indices,
        np.asarray([1, -1, -1, 1]),
        current_mu,
        kappa,
        rng,
        likelihood_family=likelihood_family,
    )

def state_cycle_swap(
    y: np.ndarray,
    move: MoveState,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    *,
    max_cycle_half_length: int = 6,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> bool:
    """Propose an alternating move around a simple bipartite support cycle.

    Two-by-two swaps are not a Markov basis when fixed cells create structural
    zeros. A feasible fiber can contain longer even cycles but no admissible
    2x2 rectangle. This proposal samples ordered counties and years from the
    static free-cell support and alternates +1/-1 around the resulting cycle.
    It preserves every state-year and county-period total exactly. Because the
    selection law is independent of the current counts and the opposite sign
    has the same probability, the proposal is symmetric.
    """

    years = move.years
    eligible: list[tuple[int, np.ndarray, int]] = []
    for state, counties in move.cycle_state_counties:
        maximum = min(int(max_cycle_half_length), len(counties), len(years))
        if maximum >= 3:
            eligible.append((int(state), counties, maximum))
    if not eligible:
        return False

    _, counties, maximum = eligible[int(rng.integers(0, len(eligible)))]
    length = int(rng.integers(3, maximum + 1))
    selected_counties = rng.choice(counties, size=length, replace=False)
    selected_years = rng.choice(years, size=length, replace=False)

    indices: list[int] = []
    delta: list[int] = []
    for position in range(length):
        positive_key = (int(selected_counties[position]), int(selected_years[position]))
        negative_key = (int(selected_counties[(position + 1) % length]), int(selected_years[position]))
        if positive_key not in move.county_year_to_row or negative_key not in move.county_year_to_row:
            return False
        positive = int(move.county_year_to_row[positive_key])
        negative = int(move.county_year_to_row[negative_key])
        if not (move.upper[positive] > move.lower[positive] and move.upper[negative] > move.lower[negative]):
            return False
        indices.extend([positive, negative])
        delta.extend([1, -1])

    indices_array = np.asarray(indices, dtype=int)
    direction = np.asarray(delta, dtype=int)
    return _apply_heatbath_direction(
        y,
        move,
        indices_array,
        direction,
        current_mu,
        kappa,
        rng,
        likelihood_family=likelihood_family,
    )

def blocked_refresh(
    y: np.ndarray,
    move: MoveState,
    current_mu: np.ndarray,
    kappa: float | None,
    rng: np.random.Generator,
    attempts: int = 12,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> int:
    accepted = 0
    for _ in range(attempts):
        accepted += int(
            state_year_transfer(
                y,
                move,
                current_mu,
                kappa,
                rng,
                likelihood_family=likelihood_family,
            )
        )
    return accepted


def _proposal_scales(
    theta: Theta,
    multipliers: dict[str, float] | None = None,
    *,
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> dict[str, float]:
    base = {
        "beta": 0.01,
        "state": 0.01,
        "year": 0.01,
        "log_sigma_state": 0.05,
        "log_sigma_year": 0.05,
        "log_kappa": 0.05,
    }
    if multipliers:
        for key, value in multipliers.items():
            if key in base:
                base[key] *= float(value)
    if normalize_likelihood_family(likelihood_family) == "poisson":
        del base["log_kappa"]
    return base



def _normalized_move_weights(settings: dict) -> dict[str, float]:
    configured = settings.get("move_weights", {}) or {}
    values = {
        "state_year_transfer": float(configured.get("state_year_transfer", configured.get("transfer", 0.50))),
        "county_period_exploration": float(configured.get("county_period_exploration", configured.get("interval_transfer", 0.25))),
        "interval_path_transfer": float(configured.get("interval_path_transfer", 0.20)),
        "swap_2x2": float(configured.get("swap_2x2", 0.25)),
        "cycle_swap": float(configured.get("cycle_swap", 0.10)),
    }
    values = {key: max(value, 0.0) for key, value in values.items()}
    total = sum(values.values())
    if total <= 0:
        raise ValueError("At least one latent-count move weight must be positive.")
    return {key: value / total for key, value in values.items()}

def _theta_to_rows(theta: Theta, design: Design, chain: int, draw: int, iteration: int) -> list[dict]:
    rows = []
    for term, value in zip(design.columns, theta.beta):
        rows.append({"chain": chain, "draw": draw, "iteration": iteration, "parameter": term, "value": float(value)})
    for state, value in zip(design.states, theta.state_effect - theta.state_effect.mean()):
        rows.append({"chain": chain, "draw": draw, "iteration": iteration, "parameter": f"state_effect[{state}]", "value": float(value)})
    for year, value in zip(design.years, theta.year_effect - theta.year_effect.mean()):
        rows.append({"chain": chain, "draw": draw, "iteration": iteration, "parameter": f"year_effect[{year}]", "value": float(value)})
    rows.extend(
        [
            {"chain": chain, "draw": draw, "iteration": iteration, "parameter": "sigma_state", "value": float(np.exp(theta.log_sigma_state))},
            {"chain": chain, "draw": draw, "iteration": iteration, "parameter": "sigma_year", "value": float(np.exp(theta.log_sigma_year))},
        ]
    )
    if design.likelihood_family == "negative_binomial_2":
        rows.append(
            {"chain": chain, "draw": draw, "iteration": iteration, "parameter": "kappa", "value": float(np.exp(theta.log_kappa))}
        )
    return rows


def _center_random_effects(theta: Theta) -> Theta:
    """Project random effects onto the identified sum-to-zero parameterization."""

    centered = theta.copy()
    centered.state_effect = centered.state_effect - centered.state_effect.mean()
    centered.year_effect = centered.year_effect - centered.year_effect.mean()
    return centered


def _update_theta_block(
    y: np.ndarray,
    theta: Theta,
    design: Design,
    intercept_mean: float,
    rng: np.random.Generator,
    block: str,
    scale: float,
    current_lp: float,
) -> tuple[Theta, float, bool]:
    proposal = theta.copy()
    if block == "beta":
        proposal.beta = theta.beta + rng.normal(0, scale, size=len(theta.beta))
    elif block == "state":
        proposal.state_effect = theta.state_effect + rng.normal(0, scale, size=len(theta.state_effect))
    elif block == "year":
        proposal.year_effect = theta.year_effect + rng.normal(0, scale, size=len(theta.year_effect))
    elif block == "log_sigma_state":
        proposal.log_sigma_state = theta.log_sigma_state + float(rng.normal(0, scale))
    elif block == "log_sigma_year":
        proposal.log_sigma_year = theta.log_sigma_year + float(rng.normal(0, scale))
    elif block == "log_kappa":
        proposal.log_kappa = theta.log_kappa + float(rng.normal(0, scale))
    else:
        raise ValueError(block)
    proposal = _center_random_effects(proposal)
    proposed_lp = log_posterior_theta(y, proposal, design, intercept_mean=intercept_mean)
    if np.isfinite(proposed_lp) and np.log(rng.uniform()) < proposed_lp - current_lp:
        return proposal, proposed_lp, True
    return theta, current_lp, False


def _settings(config: dict, mode: str) -> dict:
    if mode == "quick":
        settings = config["run"].copy()
        settings.update(config.get("quick_test", {}))
        settings["mode"] = "quick_test"
        return settings
    settings = config["run"].copy()
    settings.update(config.get("production_runtime", {}))
    settings["mode"] = "production"
    settings["requested_n_iter"] = config["run"]["n_iter"]
    settings["requested_burn_in"] = config["run"]["burn_in"]
    settings["requested_thin"] = config["run"]["thin"]
    return settings


def _load_config_path(config_path: str | Path | None) -> dict:
    if config_path is None:
        return load_config()
    import yaml

    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config["_config_path"] = str(path)
    return config


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _merge_selected_tuning(settings: dict) -> dict:
    import yaml

    selected_path = settings.get("selected_tuning_path")
    if not selected_path:
        return settings
    path = _resolve_project_path(selected_path)
    if not path.exists():
        return settings
    with path.open("r", encoding="utf-8") as handle:
        selected = yaml.safe_load(handle) or {}
    for key in [
        "count_move_sweeps_per_iter",
        "max_count_proposals_per_iter",
        "blocked_refresh_frequency",
        "blocked_refresh_attempts",
        "block_size",
        "max_cycle_half_length",
        "move_weights",
        "proposal_scale_multipliers",
    ]:
        if key in selected:
            settings[key] = selected[key]
    settings["selected_tuning_source"] = str(path)
    return settings


def _hpc_settings(config: dict, mode: str, array_task_id: int | None) -> dict:
    settings = dict(config.get("run", {}))
    settings["mode"] = mode
    if mode == "smoke":
        settings.update(config.get("smoke", {}))
    elif mode == "tune":
        tuning = list(config.get("tuning_configurations", []))
        if not tuning:
            raise ValueError("Tune mode requires tuning_configurations in the config.")
        task_index = max(int(array_task_id or 1) - 1, 0) % len(tuning)
        settings.update(tuning[task_index])
        settings["tuning_task_index"] = task_index + 1
    elif mode == "extend":
        settings["n_iter"] = int(settings.get("extension_n_iter", 150000))
        settings["burn_in"] = int(settings.get("extension_burn_in", 0))
        settings["thin"] = int(settings.get("extension_thin", settings.get("thin", 50)))
        settings = _merge_selected_tuning(settings)
    elif mode == "production":
        settings = _merge_selected_tuning(settings)
    else:
        raise ValueError(f"Unsupported HPC mode: {mode}")
    return settings


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_json(path: Path, payload: dict) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _theta_payload(theta: Theta) -> dict[str, object]:
    theta = _center_random_effects(theta)
    return {
        "beta": theta.beta,
        "state_effect": theta.state_effect,
        "year_effect": theta.year_effect,
        "log_sigma_state": float(theta.log_sigma_state),
        "log_sigma_year": float(theta.log_sigma_year),
        "log_kappa": float(theta.log_kappa),
    }


def _theta_from_payload(payload: dict[str, object]) -> Theta:
    theta = Theta(
        beta=np.asarray(payload["beta"], dtype=float),
        state_effect=np.asarray(payload["state_effect"], dtype=float),
        year_effect=np.asarray(payload["year_effect"], dtype=float),
        log_sigma_state=float(payload["log_sigma_state"]),
        log_sigma_year=float(payload["log_sigma_year"]),
        log_kappa=float(payload["log_kappa"]),
    )
    return _center_random_effects(theta)


class LikelihoodFamilyMismatchError(ValueError):
    """Raised when persisted chain evidence belongs to a different target."""


def _validated_evidence_likelihood_family(
    recorded_family: object | None,
    *,
    expected_likelihood_family: str,
    source: str,
) -> str:
    """Validate persisted target identity, with legacy evidence treated as NB2.

    Checkpoints and statuses written before likelihood-family sensitivities did
    not carry this field and can only belong to the historical default NB2
    target. This compatibility rule is deliberately one-way: missing metadata
    can never authorize Poisson evidence reuse.
    """

    expected = normalize_likelihood_family(expected_likelihood_family)
    recorded = normalize_likelihood_family(
        DEFAULT_LIKELIHOOD_FAMILY
        if recorded_family is None
        else str(recorded_family)
    )
    if recorded != expected:
        raise LikelihoodFamilyMismatchError(
            f"{source} likelihood family mismatch: "
            f"recorded={recorded!r} requested={expected!r}"
        )
    return recorded


def save_chain_checkpoint(
    path: Path,
    *,
    y: np.ndarray,
    theta: Theta,
    rng: np.random.Generator,
    iteration: int,
    saved_draws: int,
    current_lp: float,
    accepted: dict[str, int],
    proposed: dict[str, int],
    param_accept: dict[str, int],
    param_prop: dict[str, int],
    likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp.npz")
    theta_state = _theta_payload(theta)
    family = normalize_likelihood_family(likelihood_family)
    np.savez_compressed(
        tmp,
        y=np.asarray(y, dtype=np.int16),
        beta=theta_state["beta"],
        state_effect=theta_state["state_effect"],
        year_effect=theta_state["year_effect"],
        log_sigma_state=np.asarray(theta_state["log_sigma_state"]),
        log_sigma_year=np.asarray(theta_state["log_sigma_year"]),
        log_kappa=np.asarray(theta_state["log_kappa"]),
        rng_state=np.asarray(json.dumps(rng.bit_generator.state)),
        iteration=np.asarray(int(iteration)),
        saved_draws=np.asarray(int(saved_draws)),
        current_lp=np.asarray(float(current_lp)),
        accepted_json=np.asarray(json.dumps(accepted)),
        proposed_json=np.asarray(json.dumps(proposed)),
        param_accept_json=np.asarray(json.dumps(param_accept)),
        param_prop_json=np.asarray(json.dumps(param_prop)),
        likelihood_family=np.asarray(family),
    )
    os.replace(tmp, path)


def load_chain_checkpoint(
    path: Path,
    *,
    expected_likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> dict[str, object]:
    data = np.load(path, allow_pickle=True)
    recorded_family = (
        str(data["likelihood_family"].item())
        if "likelihood_family" in data.files
        else None
    )
    family = _validated_evidence_likelihood_family(
        recorded_family,
        expected_likelihood_family=expected_likelihood_family,
        source=str(path),
    )
    rng = np.random.default_rng()
    rng.bit_generator.state = json.loads(str(data["rng_state"].item()))
    theta = _theta_from_payload(
        {
            "beta": data["beta"],
            "state_effect": data["state_effect"],
            "year_effect": data["year_effect"],
            "log_sigma_state": data["log_sigma_state"].item(),
            "log_sigma_year": data["log_sigma_year"].item(),
            "log_kappa": data["log_kappa"].item(),
        }
    )
    return {
        "y": data["y"].astype(int),
        "theta": theta,
        "rng": rng,
        "iteration": int(data["iteration"].item()),
        "saved_draws": int(data["saved_draws"].item()),
        "current_lp": float(data["current_lp"].item()),
        "accepted": json.loads(str(data["accepted_json"].item())),
        "proposed": json.loads(str(data["proposed_json"].item())),
        "param_accept": json.loads(str(data["param_accept_json"].item())),
        "param_prop": json.loads(str(data["param_prop_json"].item())),
        "likelihood_family": family,
    }


def latest_valid_checkpoint(
    checkpoint_dir: Path,
    *,
    expected_likelihood_family: str = DEFAULT_LIKELIHOOD_FAMILY,
) -> Path | None:
    checkpoints = sorted(checkpoint_dir.glob("checkpoint_iter_*.npz"))
    for path in reversed(checkpoints):
        try:
            load_chain_checkpoint(
                path,
                expected_likelihood_family=expected_likelihood_family,
            )
            return path
        except LikelihoodFamilyMismatchError:
            raise
        except Exception:
            continue
    return None


def _initial_allocation_path(chain_id: int) -> Path:
    direct = BAYES_DATA / f"initial_allocation_chain{chain_id}.parquet"
    if direct.exists():
        return direct
    available = sorted(BAYES_DATA.glob("initial_allocation_chain*.parquet"))
    if not available:
        raise FileNotFoundError("No initial allocation parquet files were found; run script 30 first.")
    return available[(chain_id - 1) % len(available)]


def _acceptance_rows(chain: int, accepted: dict[str, int], proposed: dict[str, int], param_accept: dict[str, int], param_prop: dict[str, int]) -> list[dict]:
    rows = []
    for move_name in accepted:
        rows.append(
            {
                "chain": chain,
                "block": move_name,
                "accepted": int(accepted[move_name]),
                "proposed": int(proposed[move_name]),
                "acceptance_rate": accepted[move_name] / proposed[move_name] if proposed[move_name] else np.nan,
                "type": "count_move",
            }
        )
    for block in param_accept:
        rows.append(
            {
                "chain": chain,
                "block": block,
                "accepted": int(param_accept[block]),
                "proposed": int(param_prop[block]),
                "acceptance_rate": param_accept[block] / param_prop[block] if param_prop[block] else np.nan,
                "type": "parameter",
            }
        )
    return rows


def _load_existing_chain_outputs(chain_dir: Path) -> tuple[list[dict], list[np.ndarray], list[dict], list[dict]]:
    rows_path = chain_dir / "draws_params.parquet"
    parameter_rows = pd.read_parquet(rows_path).to_dict("records") if rows_path.exists() else []
    latent_path = chain_dir / "draws_latent.npz"
    latent_draws = [row.astype(np.int16) for row in np.load(latent_path, allow_pickle=True)["y"]] if latent_path.exists() else []
    validation_path = chain_dir / "latent_validation.csv"
    validation_rows = pd.read_csv(validation_path).to_dict("records") if validation_path.exists() else []
    runtime_path = chain_dir / "runtime_log.csv"
    runtime_rows = pd.read_csv(runtime_path).to_dict("records") if runtime_path.exists() else []
    return parameter_rows, latent_draws, validation_rows, runtime_rows


def _write_chain_outputs(
    chain_dir: Path,
    *,
    chain_id: int,
    parameter_rows: list[dict],
    latent_draws: list[np.ndarray],
    validation_rows: list[dict],
    acceptance_rows: list[dict],
    runtime_rows: list[dict],
    status: dict,
) -> None:
    chain_dir.mkdir(parents=True, exist_ok=True)
    _atomic_parquet(chain_dir / "draws_params.parquet", pd.DataFrame(parameter_rows))
    latent = np.stack(latent_draws, axis=0).astype(np.int16) if latent_draws else np.empty((0, 0), dtype=np.int16)
    latent_tmp = (chain_dir / "draws_latent.npz").with_suffix(".npz.tmp.npz")
    np.savez_compressed(latent_tmp, y=latent)
    os.replace(latent_tmp, chain_dir / "draws_latent.npz")
    _atomic_csv(chain_dir / "latent_validation.csv", pd.DataFrame(validation_rows))
    _atomic_csv(chain_dir / "acceptance_rates.csv", pd.DataFrame(acceptance_rows))
    _atomic_csv(chain_dir / "runtime_log.csv", pd.DataFrame(runtime_rows))
    status = {**status, "chain_id": chain_id, "updated": datetime.now().isoformat(timespec="seconds")}
    _atomic_json(chain_dir / "chain_status.json", status)


def _write_resolved_config(path: Path, config: dict, settings: dict, args: dict) -> None:
    import yaml

    serializable = {key: value for key, value in config.items() if not key.startswith("_")}
    payload = {"config": serializable, "resolved_settings": settings, "arguments": args}
    _atomic_write_text(path, yaml.safe_dump(payload, sort_keys=False))


def run_mcmc_chain_hpc(
    frame: pd.DataFrame,
    *,
    config_path: str | Path,
    mode: str,
    chain_id: int,
    array_task_id: int | None = None,
    seed: int | None = None,
    out_dir: str | Path = OUTPUT_DIR / "hpc",
    checkpoint_dir: str | Path | None = None,
    checkpoint_every: int = 250,
    resume: bool = False,
    max_runtime_minutes: int | None = None,
    stop_before_time_limit_minutes: int = 10,
    force: bool = False,
    model_name: str = "primary",
) -> dict:
    config = _load_config_path(config_path)
    settings = _hpc_settings(config, mode, array_task_id)
    likelihood_family = normalize_likelihood_family(
        settings.get(
            "likelihood_family",
            settings.get("likelihood", DEFAULT_LIKELIHOOD_FAMILY),
        )
    )
    settings["likelihood_family"] = likelihood_family
    seeds = list(settings.get("random_seeds") or config.get("run", {}).get("random_seeds") or [17291])
    if seed is None:
        seed = int(seeds[(chain_id - 1) % len(seeds)]) + (100000 if mode == "extend" else 0)

    out_root = _resolve_project_path(out_dir)
    chain_dir = out_root / "chains" / f"chain_{chain_id:02d}"
    checkpoint_root = Path(checkpoint_dir) if checkpoint_dir else chain_dir / "checkpoints"
    if not checkpoint_root.is_absolute():
        checkpoint_root = PROJECT_ROOT / checkpoint_root
    status_path = chain_dir / "chain_status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status_family = _validated_evidence_likelihood_family(
            status.get("likelihood_family"),
            expected_likelihood_family=likelihood_family,
            source=str(status_path),
        )
        status["likelihood_family"] = status_family
        if status.get("status") == "completed" and not force:
            return status

    _write_resolved_config(
        chain_dir / "chain_config_resolved.yaml",
        config,
        settings,
        {
            "mode": mode,
            "chain_id": chain_id,
            "array_task_id": array_task_id,
            "seed": seed,
            "out_dir": str(out_root),
            "checkpoint_dir": str(checkpoint_root),
            "checkpoint_every": checkpoint_every,
            "resume": resume,
        },
    )

    design = make_design(
        frame, model=model_name, likelihood_family=likelihood_family
    )
    intercept_mean = crude_intercept_prior(frame)
    n_iter = int(settings["n_iter"])
    burn_in = int(settings.get("burn_in", 0))
    thin = int(settings.get("thin", 1))
    max_count_proposals = int(settings.get("max_count_proposals_per_iter", 350))
    blocked_frequency = int(settings.get("blocked_refresh_frequency", 25))
    blocked_attempts = int(settings.get("blocked_refresh_attempts", 12))
    checkpoint_every = max(1, int(checkpoint_every or settings.get("checkpoint_every", 250)))
    move_weights = _normalized_move_weights(settings)
    weight_transfer = move_weights["state_year_transfer"]
    weight_interval = move_weights["county_period_exploration"]
    weight_path = move_weights["interval_path_transfer"]
    weight_swap = move_weights["swap_2x2"]
    weight_cycle = move_weights["cycle_swap"]
    max_cycle_half_length = int(settings.get("max_cycle_half_length", 6))

    checkpoint_root.mkdir(parents=True, exist_ok=True)
    latest = (
        latest_valid_checkpoint(
            checkpoint_root,
            expected_likelihood_family=likelihood_family,
        )
        if resume
        else None
    )
    if latest is not None:
        checkpoint = load_chain_checkpoint(
            latest,
            expected_likelihood_family=likelihood_family,
        )
        parameter_rows, latent_draws, validation_rows, runtime_rows = (
            _load_existing_chain_outputs(chain_dir)
        )
        y = checkpoint["y"]
        theta = checkpoint["theta"]
        rng = checkpoint["rng"]
        start_iteration = int(checkpoint["iteration"])
        saved = int(checkpoint["saved_draws"])
        current_lp = float(checkpoint["current_lp"])
        accepted = {key: int(value) for key, value in checkpoint["accepted"].items()}
        proposed = {key: int(value) for key, value in checkpoint["proposed"].items()}
        param_accept = {key: int(value) for key, value in checkpoint["param_accept"].items()}
        param_prop = {key: int(value) for key, value in checkpoint["param_prop"].items()}
        resume_source = rel(latest)
    else:
        parameter_rows, latent_draws, validation_rows, runtime_rows = (
            [],
            [],
            [],
            [],
        )
        rng = np.random.default_rng(int(seed))
        init_path = _initial_allocation_path(chain_id)
        y = pd.read_parquet(init_path)["latent_count"].to_numpy(dtype=int).copy()
        assert_constraints(y, frame, label=f"chain{chain_id}_start")
        theta = initialize_theta(frame, y, design)
        current_lp = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
        scales0 = _proposal_scales(
            theta,
            settings.get("proposal_scale_multipliers"),
            likelihood_family=likelihood_family,
        )
        accepted = {"transfer": 0, "interval_transfer": 0, "interval_path": 0, "swap_2x2": 0, "cycle_swap": 0, "blocked_refresh": 0}
        proposed = {key: 0 for key in accepted}
        param_accept = {key: 0 for key in scales0}
        param_prop = {key: 0 for key in scales0}
        start_iteration = 0
        saved = 0
        resume_source = ""

    move = build_move_state(frame, y)
    target_iteration = start_iteration + n_iter if mode == "extend" else n_iter
    deadline_seconds = None
    if max_runtime_minutes:
        usable_minutes = max(1, int(max_runtime_minutes) - int(stop_before_time_limit_minutes or 0))
        deadline_seconds = time.monotonic() + usable_minutes * 60
    stop_requested = {"value": False}

    def _handle_signal(signum: int, _frame: object) -> None:
        stop_requested["value"] = True
        runtime_rows.append({"event": "signal_received", "signum": int(signum), "time": datetime.now().isoformat(timespec="seconds")})

    previous_handler = signal.signal(signal.SIGUSR1, _handle_signal) if hasattr(signal, "SIGUSR1") else None

    started = datetime.now().isoformat(timespec="seconds")
    status = "running"
    try:
        for iteration in range(start_iteration + 1, target_iteration + 1):
            current_mu = mu(theta, design)
            kappa = (
                None
                if likelihood_family == "poisson"
                else float(np.exp(theta.log_kappa))
            )
            free_cells = int((move.upper > move.lower).sum())
            count_moves = min(max_count_proposals, max(1, int(free_cells * float(settings.get("count_move_sweeps_per_iter", 0.1)))))
            for _ in range(count_moves):
                r = rng.uniform()
                if r < weight_transfer:
                    proposed["transfer"] += 1
                    accepted["transfer"] += int(
                        state_year_transfer(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            likelihood_family=likelihood_family,
                        )
                    )
                elif r < weight_transfer + weight_interval:
                    proposed["interval_transfer"] += 1
                    accepted["interval_transfer"] += int(
                        period_interval_transfer(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            likelihood_family=likelihood_family,
                        )
                    )
                elif r < weight_transfer + weight_interval + weight_path:
                    proposed["interval_path"] += 1
                    accepted["interval_path"] += int(
                        interval_path_transfer(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            likelihood_family=likelihood_family,
                        )
                    )
                elif r < weight_transfer + weight_interval + weight_path + weight_swap:
                    proposed["swap_2x2"] += 1
                    accepted["swap_2x2"] += int(
                        state_2x2_swap(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            likelihood_family=likelihood_family,
                        )
                    )
                else:
                    proposed["cycle_swap"] += 1
                    accepted["cycle_swap"] += int(
                        state_cycle_swap(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            max_cycle_half_length=max_cycle_half_length,
                            likelihood_family=likelihood_family,
                        )
                    )
            if blocked_frequency and iteration % blocked_frequency == 0:
                proposed["blocked_refresh"] += blocked_attempts
                accepted["blocked_refresh"] += blocked_refresh(
                    y,
                    move,
                    current_mu,
                    kappa,
                    rng,
                    attempts=blocked_attempts,
                    likelihood_family=likelihood_family,
                )
            current_lp = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
            scales = _proposal_scales(
                theta,
                settings.get("proposal_scale_multipliers"),
                likelihood_family=likelihood_family,
            )
            for block, scale in scales.items():
                param_prop[block] += 1
                theta, current_lp, ok = _update_theta_block(y, theta, design, intercept_mean, rng, block, scale, current_lp)
                param_accept[block] += int(ok)
            if iteration > burn_in and (iteration - burn_in) % thin == 0:
                saved += 1
                validation = assert_constraints(y, frame, label=f"chain{chain_id}_draw{saved}")
                validation_rows.extend(validation.to_frame(f"chain{chain_id}_draw{saved}").to_dict("records"))
                parameter_rows.extend(_theta_to_rows(theta, design, chain_id, saved, iteration))
                latent_draws.append(y.astype(np.int16).copy())

            should_checkpoint = iteration % checkpoint_every == 0 or stop_requested["value"]
            if deadline_seconds is not None and time.monotonic() >= deadline_seconds:
                runtime_rows.append({"event": "deadline_checkpoint", "iteration": iteration, "time": datetime.now().isoformat(timespec="seconds")})
                should_checkpoint = True
                stop_requested["value"] = True
            if should_checkpoint:
                validation = assert_constraints(y, frame, label=f"chain{chain_id}_checkpoint_iter_{iteration}")
                validation_rows.extend(validation.to_frame(f"chain{chain_id}_checkpoint_iter_{iteration}").to_dict("records"))
                checkpoint_path = checkpoint_root / f"checkpoint_iter_{iteration:09d}.npz"
                save_chain_checkpoint(
                    checkpoint_path,
                    y=y,
                    theta=theta,
                    rng=rng,
                    iteration=iteration,
                    saved_draws=saved,
                    current_lp=current_lp,
                    accepted=accepted,
                    proposed=proposed,
                    param_accept=param_accept,
                    param_prop=param_prop,
                    likelihood_family=likelihood_family,
                )
                _write_chain_outputs(
                    chain_dir,
                    chain_id=chain_id,
                    parameter_rows=parameter_rows,
                    latent_draws=latent_draws,
                    validation_rows=validation_rows,
                    acceptance_rows=_acceptance_rows(chain_id, accepted, proposed, param_accept, param_prop),
                    runtime_rows=runtime_rows,
                    status={
                        "status": "checkpointed",
                        "mode": mode,
                        "iteration": iteration,
                        "target_iteration": target_iteration,
                        "saved_draws": saved,
                        "likelihood_family": likelihood_family,
                        "latest_checkpoint": rel(checkpoint_path),
                        "resume_source": resume_source,
                    },
                )
            if stop_requested["value"]:
                status = "checkpointed"
                break
        else:
            status = "completed"

        final_iteration = iteration if "iteration" in locals() else start_iteration
        if status == "completed":
            validation = assert_constraints(y, frame, label=f"chain{chain_id}_completed")
            validation_rows.extend(validation.to_frame(f"chain{chain_id}_completed").to_dict("records"))
            checkpoint_path = checkpoint_root / f"checkpoint_iter_{final_iteration:09d}.npz"
            save_chain_checkpoint(
                checkpoint_path,
                y=y,
                theta=theta,
                rng=rng,
                iteration=final_iteration,
                saved_draws=saved,
                current_lp=current_lp,
                accepted=accepted,
                proposed=proposed,
                param_accept=param_accept,
                param_prop=param_prop,
                likelihood_family=likelihood_family,
            )
        runtime_rows.append(
            {
                "event": status,
                "mode": mode,
                "iteration": final_iteration,
                "saved_draws": saved,
                "started": started,
                "finished": datetime.now().isoformat(timespec="seconds"),
            }
        )
        final_status = {
            "status": status,
            "mode": mode,
            "iteration": final_iteration,
            "target_iteration": target_iteration,
            "saved_draws": saved,
            "likelihood_family": likelihood_family,
            "seed": int(seed),
            "config_path": config.get("_config_path", ""),
            "resume_source": resume_source,
            "grand_total": int(y.sum()),
            "suppressed_cells_treated_as_zero": False,
            "outputs": {
                "draws_params": rel(chain_dir / "draws_params.parquet"),
                "draws_latent": rel(chain_dir / "draws_latent.npz"),
                "latent_validation": rel(chain_dir / "latent_validation.csv"),
                "acceptance_rates": rel(chain_dir / "acceptance_rates.csv"),
                "runtime_log": rel(chain_dir / "runtime_log.csv"),
            },
        }
        _write_chain_outputs(
            chain_dir,
            chain_id=chain_id,
            parameter_rows=parameter_rows,
            latent_draws=latent_draws,
            validation_rows=validation_rows,
            acceptance_rows=_acceptance_rows(chain_id, accepted, proposed, param_accept, param_prop),
            runtime_rows=runtime_rows,
            status=final_status,
        )
        return final_status
    except Exception as exc:
        runtime_rows.append({"event": "failed", "error": repr(exc), "time": datetime.now().isoformat(timespec="seconds")})
        _write_chain_outputs(
            chain_dir,
            chain_id=chain_id,
            parameter_rows=parameter_rows,
            latent_draws=latent_draws,
            validation_rows=validation_rows,
            acceptance_rows=_acceptance_rows(chain_id, accepted, proposed, param_accept, param_prop),
            runtime_rows=runtime_rows,
            status={
                "status": "failed",
                "mode": mode,
                "error": repr(exc),
                "saved_draws": saved,
                "likelihood_family": likelihood_family,
            },
        )
        raise
    finally:
        if previous_handler is not None and hasattr(signal, "SIGUSR1"):
            signal.signal(signal.SIGUSR1, previous_handler)


def run_mcmc(frame: pd.DataFrame, *, mode: str = "production", model_name: str = "primary") -> dict:
    config = load_config()
    settings = _settings(config, mode)
    likelihood_family = normalize_likelihood_family(
        settings.get(
            "likelihood_family",
            settings.get("likelihood", DEFAULT_LIKELIHOOD_FAMILY),
        )
    )
    settings["likelihood_family"] = likelihood_family
    seeds = config["run"].get("random_seeds", [17291, 17292, 17293, 17294])
    manifest_path = OUTPUT_DIR / "initial_allocation_manifest.csv"
    if not manifest_path.exists():
        solve_and_save_initial_allocations(frame, seeds=seeds)

    design = make_design(
        frame, model=model_name, likelihood_family=likelihood_family
    )
    intercept_mean = crude_intercept_prior(frame)
    n_iter = int(settings["n_iter"])
    burn_in = int(settings["burn_in"])
    thin = int(settings["thin"])
    max_count_proposals = int(settings.get("max_count_proposals_per_iter", 350))
    blocked_frequency = int(settings.get("blocked_refresh_frequency", 25))
    n_chains = int(settings.get("n_chains", 4))
    move_weights = _normalized_move_weights(settings)
    weight_transfer = move_weights["state_year_transfer"]
    weight_interval = move_weights["county_period_exploration"]
    weight_path = move_weights["interval_path_transfer"]
    weight_swap = move_weights["swap_2x2"]
    weight_cycle = move_weights["cycle_swap"]
    max_cycle_half_length = int(settings.get("max_cycle_half_length", 6))
    chain_rows = []
    latent_draws = []
    draw_meta = []
    acceptance_rows = []
    run_started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for chain in range(1, n_chains + 1):
        seed = int(seeds[chain - 1])
        rng = np.random.default_rng(seed)
        init_path = BAYES_DATA / f"initial_allocation_chain{chain}.parquet"
        y = pd.read_parquet(init_path)["latent_count"].to_numpy(dtype=int).copy()
        assert_constraints(y, frame, label=f"chain{chain}_start")
        move = build_move_state(frame, y)
        theta = initialize_theta(frame, y, design)
        current_lp = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
        scales = _proposal_scales(theta, likelihood_family=likelihood_family)
        accepted = {"transfer": 0, "interval_transfer": 0, "interval_path": 0, "swap_2x2": 0, "cycle_swap": 0, "blocked_refresh": 0}
        proposed = {key: 0 for key in accepted}
        param_accept = {key: 0 for key in scales}
        param_prop = {key: 0 for key in scales}
        saved = 0
        for iteration in range(1, n_iter + 1):
            current_mu = mu(theta, design)
            kappa = (
                None
                if likelihood_family == "poisson"
                else float(np.exp(theta.log_kappa))
            )
            free_cells = int((move.upper > move.lower).sum())
            count_moves = min(max_count_proposals, max(1, int(free_cells * float(settings.get("count_move_sweeps_per_iter", 0.1)))))
            for _ in range(count_moves):
                r = rng.uniform()
                if r < 0.55:
                    proposed["transfer"] += 1
                    accepted["transfer"] += int(
                        state_year_transfer(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            likelihood_family=likelihood_family,
                        )
                    )
                elif r < 0.75:
                    proposed["interval_transfer"] += 1
                    accepted["interval_transfer"] += int(
                        period_interval_transfer(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            likelihood_family=likelihood_family,
                        )
                    )
                else:
                    proposed["swap_2x2"] += 1
                    accepted["swap_2x2"] += int(
                        state_2x2_swap(
                            y,
                            move,
                            current_mu,
                            kappa,
                            rng,
                            likelihood_family=likelihood_family,
                        )
                    )
            if blocked_frequency and iteration % blocked_frequency == 0:
                proposed["blocked_refresh"] += 12
                accepted["blocked_refresh"] += blocked_refresh(
                    y,
                    move,
                    current_mu,
                    kappa,
                    rng,
                    attempts=12,
                    likelihood_family=likelihood_family,
                )
            # Count moves mutate y. Refresh the current target value before any
            # parameter Metropolis ratio is evaluated. The v1 local runner
            # compared proposals against a log posterior from the previous y.
            current_lp = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)
            for block, scale in scales.items():
                param_prop[block] += 1
                theta, current_lp, ok = _update_theta_block(y, theta, design, intercept_mean, rng, block, scale, current_lp)
                param_accept[block] += int(ok)
            if iteration > burn_in and (iteration - burn_in) % thin == 0:
                saved += 1
                validation = assert_constraints(y, frame, label=f"chain{chain}_draw{saved}")
                append_validation(f"chain{chain}_draw{saved}", validation)
                chain_rows.extend(_theta_to_rows(theta, design, chain, saved, iteration))
                latent_draws.append(y.astype(np.int16).copy())
                draw_meta.append({"chain": chain, "draw": saved, "iteration": iteration})
        for move_name in accepted:
            acceptance_rows.append(
                {
                    "chain": chain,
                    "block": move_name,
                    "accepted": accepted[move_name],
                    "proposed": proposed[move_name],
                    "acceptance_rate": accepted[move_name] / proposed[move_name] if proposed[move_name] else np.nan,
                    "type": "count_move",
                }
            )
        for block in param_accept:
            acceptance_rows.append(
                {
                    "chain": chain,
                    "block": block,
                    "accepted": param_accept[block],
                    "proposed": param_prop[block],
                    "acceptance_rate": param_accept[block] / param_prop[block] if param_prop[block] else np.nan,
                    "type": "parameter",
                }
            )

    draws_df = pd.DataFrame(chain_rows)
    draws_df.to_csv(OUTPUT_DIR / "posterior_parameter_draws.csv", index=False)
    acceptance_df = pd.DataFrame(acceptance_rows)
    acceptance_df.to_csv(OUTPUT_DIR / "mcmc_acceptance_rates.csv", index=False)
    if latent_draws:
        y_draws = np.stack(latent_draws, axis=0)
    else:
        y_draws = np.empty((0, len(frame)), dtype=np.int16)
    np.savez_compressed(
        OUTPUT_DIR / "posterior_draws_primary.npz",
        y=y_draws,
        draw_meta=pd.DataFrame(draw_meta).to_records(index=False),
        county_fips=frame["county_fips"].astype(str).to_numpy(),
        year=frame["year"].astype(str).to_numpy(),
    )
    run_meta = {
        "mode": settings["mode"],
        "model_name": model_name,
        "likelihood_family": likelihood_family,
        "started": run_started,
        "finished": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_chains": n_chains,
        "n_iter": n_iter,
        "burn_in": burn_in,
        "thin": thin,
        "saved_draws": len(latent_draws),
        "parameter_draws_csv": rel(OUTPUT_DIR / "posterior_parameter_draws.csv"),
        "latent_draws_npz": rel(OUTPUT_DIR / "posterior_draws_primary.npz"),
        "acceptance_csv": rel(OUTPUT_DIR / "mcmc_acceptance_rates.csv"),
        "requested_n_iter": settings.get("requested_n_iter", n_iter),
        "note": "Production runtime profile is computationally bounded; the full 40,000-iteration specification is retained in config/bayes_constrained.yaml.",
    }
    pd.DataFrame([run_meta]).to_csv(OUTPUT_DIR / "mcmc_run_metadata.csv", index=False)
    return run_meta
