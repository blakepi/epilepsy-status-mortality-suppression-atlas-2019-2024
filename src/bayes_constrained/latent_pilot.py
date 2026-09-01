from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from .constraints import assert_constraints
from .model import Theta, log_likelihood, make_design, mu
from .sampler import (
    _normalized_move_weights,
    build_move_state,
    period_interval_transfer,
    interval_path_transfer,
    state_2x2_swap,
    state_cycle_swap,
    state_year_transfer,
)


@dataclass(frozen=True)
class PilotOutputs:
    trajectories: pd.DataFrame
    acceptance: pd.DataFrame
    pairwise: pd.DataFrame
    final_states: np.ndarray


def theta_from_parameter_summary(frame: pd.DataFrame, path: Path) -> Theta:
    summary = pd.read_csv(path)
    median = summary.set_index("parameter")["posterior_median"]
    scale = summary.set_index("parameter")["scale"]
    design = make_design(frame)

    beta = np.zeros(len(design.columns), dtype=float)
    for index, parameter in enumerate(design.columns):
        value = float(median.loc[parameter])
        if str(scale.loc[parameter]) == "mortality_rate_ratio":
            value = float(np.log(value))
        beta[index] = value
    state_effect = np.asarray([float(median.loc[f"state_effect[{state}]"]) for state in design.states], dtype=float)
    year_effect = np.asarray([float(median.loc[f"year_effect[{year}]"]) for year in design.years], dtype=float)
    state_effect -= state_effect.mean()
    year_effect -= year_effect.mean()
    return Theta(
        beta=beta,
        state_effect=state_effect,
        year_effect=year_effect,
        log_sigma_state=float(np.log(float(median.loc["sigma_state"]))),
        log_sigma_year=float(np.log(float(median.loc["sigma_year"]))),
        log_kappa=float(np.log(float(median.loc["kappa"]))),
    )


def _hash_state(y: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(y, dtype=np.int16).tobytes()).hexdigest()[:16]


def _group_indices(frame: pd.DataFrame, column: str) -> dict[str, np.ndarray]:
    return {
        str(group): group_frame.index.to_numpy(dtype=int)
        for group, group_frame in frame.groupby(column, sort=True, dropna=False)
    }


def _snapshot(
    *,
    chain: int,
    proposal: int,
    y: np.ndarray,
    start: np.ndarray,
    free_mask: np.ndarray,
    start_period_total: np.ndarray,
    period_total: np.ndarray,
    theta: Theta,
    design: object,
    rurality_groups: dict[str, np.ndarray],
    svi_groups: dict[str, np.ndarray],
) -> dict[str, object]:
    difference = np.asarray(y - start, dtype=int)
    row: dict[str, object] = {
        "chain": chain,
        "proposal": proposal,
        "state_hash": _hash_state(y),
        "log_likelihood": float(log_likelihood(y, theta, design)),
        "l1_distance_free_cells": int(np.abs(difference[free_mask]).sum()),
        "changed_free_cells": int((difference[free_mask] != 0).sum()),
        "fraction_free_cells_changed": float((difference[free_mask] != 0).mean()),
        "maximum_absolute_cell_change": int(np.abs(difference[free_mask]).max()) if free_mask.any() else 0,
        "changed_county_period_totals": int((period_total != start_period_total).sum()),
    }
    for label, indices in rurality_groups.items():
        row[f"rurality_total__{label}"] = int(y[indices].sum())
    for label, indices in svi_groups.items():
        row[f"svi_total__{label}"] = int(y[indices].sum())
    return row


def run_fixed_theta_latent_pilot(
    frame: pd.DataFrame,
    initial_states: list[np.ndarray],
    theta: Theta,
    *,
    proposals_per_chain: int = 25_000,
    record_every: int = 500,
    seed: int = 20260810,
    move_weights: dict[str, float] | None = None,
    max_cycle_half_length: int = 6,
) -> PilotOutputs:
    design = make_design(frame)
    current_mu = mu(theta, design)
    kappa = float(np.exp(theta.log_kappa))
    weights = _normalized_move_weights({"move_weights": move_weights or {}})
    names = list(weights)
    thresholds = np.cumsum([weights[name] for name in names])
    free_mask = frame["q002_upper"].to_numpy(dtype=int) > frame["q002_lower"].to_numpy(dtype=int)
    rurality_groups = _group_indices(frame, "primary_rurality")
    svi_groups = _group_indices(frame, "svi_quartile")

    trajectory_rows: list[dict[str, object]] = []
    acceptance_rows: list[dict[str, object]] = []
    final_states: list[np.ndarray] = []

    for chain, initial in enumerate(initial_states, start=1):
        y = np.asarray(initial, dtype=int).copy()
        assert_constraints(y, frame, label=f"latent_pilot_chain{chain}_start")
        move = build_move_state(frame, y)
        start_period_total = move.period_total.copy()
        start = y.copy()
        rng = np.random.default_rng(seed + chain)
        proposed = {name: 0 for name in names}
        accepted = {name: 0 for name in names}
        trajectory_rows.append(
            _snapshot(
                chain=chain,
                proposal=0,
                y=y,
                start=start,
                free_mask=free_mask,
                start_period_total=start_period_total,
                period_total=move.period_total,
                theta=theta,
                design=design,
                rurality_groups=rurality_groups,
                svi_groups=svi_groups,
            )
        )

        for proposal in range(1, proposals_per_chain + 1):
            draw = float(rng.uniform())
            position = min(int(np.searchsorted(thresholds, draw, side="right")), len(names) - 1)
            name = names[position]
            proposed[name] += 1
            if name == "state_year_transfer":
                ok = state_year_transfer(y, move, current_mu, kappa, rng)
            elif name == "county_period_exploration":
                ok = period_interval_transfer(y, move, current_mu, kappa, rng)
            elif name == "interval_path_transfer":
                ok = interval_path_transfer(y, move, current_mu, kappa, rng)
            elif name == "swap_2x2":
                ok = state_2x2_swap(y, move, current_mu, kappa, rng)
            elif name == "cycle_swap":
                ok = state_cycle_swap(
                    y,
                    move,
                    current_mu,
                    kappa,
                    rng,
                    max_cycle_half_length=max_cycle_half_length,
                )
            else:
                raise ValueError(name)
            accepted[name] += int(ok)
            if proposal % record_every == 0 or proposal == proposals_per_chain:
                assert_constraints(y, frame, label=f"latent_pilot_chain{chain}_proposal{proposal}")
                trajectory_rows.append(
                    _snapshot(
                        chain=chain,
                        proposal=proposal,
                        y=y,
                        start=start,
                        free_mask=free_mask,
                        start_period_total=start_period_total,
                        period_total=move.period_total,
                        theta=theta,
                        design=design,
                        rurality_groups=rurality_groups,
                        svi_groups=svi_groups,
                    )
                )
        assert_constraints(y, frame, label=f"latent_pilot_chain{chain}_final")
        final_states.append(y.copy())
        for name in names:
            acceptance_rows.append(
                {
                    "chain": chain,
                    "move": name,
                    "proposed": int(proposed[name]),
                    "accepted": int(accepted[name]),
                    "acceptance_rate": accepted[name] / proposed[name] if proposed[name] else np.nan,
                }
            )

    pairwise_rows: list[dict[str, object]] = []
    for left in range(len(final_states)):
        for right in range(left + 1, len(final_states)):
            start_left = np.asarray(initial_states[left], dtype=int)
            start_right = np.asarray(initial_states[right], dtype=int)
            final_left = final_states[left]
            final_right = final_states[right]
            pairwise_rows.append(
                {
                    "chain_left": left + 1,
                    "chain_right": right + 1,
                    "starting_l1_distance_free": int(np.abs(start_left[free_mask] - start_right[free_mask]).sum()),
                    "final_l1_distance_free": int(np.abs(final_left[free_mask] - final_right[free_mask]).sum()),
                    "starting_cells_different": int((start_left[free_mask] != start_right[free_mask]).sum()),
                    "final_cells_different": int((final_left[free_mask] != final_right[free_mask]).sum()),
                }
            )
    return PilotOutputs(
        trajectories=pd.DataFrame(trajectory_rows),
        acceptance=pd.DataFrame(acceptance_rows),
        pairwise=pd.DataFrame(pairwise_rows),
        final_states=np.stack(final_states, axis=0),
    )
