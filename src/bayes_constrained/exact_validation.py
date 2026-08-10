from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product
import math

import numpy as np
import pandas as pd
from scipy.special import logsumexp
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from .constraints import validate_constraints
from .heatbath import amplitude_log_weights, amplitude_probabilities, feasible_amplitudes
from .model import Design, Theta, log_likelihood, make_design, mu
from .sampler import (
    MoveState,
    build_move_state,
    period_interval_transfer,
    state_2x2_swap,
    state_cycle_swap,
    state_year_transfer,
)


@dataclass(frozen=True)
class ProposalEvent:
    indices: tuple[int, ...] | None
    delta: tuple[int, ...] | None
    probability: float


@dataclass(frozen=True)
class ExactKernelDiagnostics:
    states: int
    row_sum_error: float
    stationarity_error: float
    detailed_balance_error: float
    strongly_connected_components: int


def _state_key(y: np.ndarray) -> tuple[int, ...]:
    return tuple(np.asarray(y, dtype=int).tolist())


def enumerate_feasible_states(frame: pd.DataFrame, *, max_candidates: int = 1_000_000) -> np.ndarray:
    lower = pd.to_numeric(frame["q002_lower"], errors="raise").to_numpy(dtype=int)
    upper = pd.to_numeric(frame["q002_upper"], errors="raise").to_numpy(dtype=int)
    free = np.flatnonzero(upper > lower)
    widths = [int(upper[i] - lower[i] + 1) for i in free]
    candidates = math.prod(widths) if widths else 1
    if candidates > max_candidates:
        raise ValueError(f"Enumeration would inspect {candidates:,} candidates; limit is {max_candidates:,}.")

    feasible: list[np.ndarray] = []
    ranges = [range(int(lower[i]), int(upper[i]) + 1) for i in free]
    for values in product(*ranges) if ranges else [()]:
        y = lower.copy()
        if free.size:
            y[free] = np.asarray(values, dtype=int)
        if validate_constraints(y, frame).passed:
            feasible.append(y)
    if not feasible:
        raise ValueError("No feasible latent states were found.")
    return np.stack(feasible, axis=0)


def exact_conditional_probabilities(states: np.ndarray, theta: Theta, design: Design) -> np.ndarray:
    log_weights = np.asarray([log_likelihood(state, theta, design) for state in states], dtype=float)
    return np.exp(log_weights - logsumexp(log_weights))


def _coalesce(raw: list[tuple[tuple[int, ...] | None, tuple[int, ...] | None, float]]) -> list[ProposalEvent]:
    merged: dict[tuple[tuple[int, ...] | None, tuple[int, ...] | None], float] = {}
    for indices, delta, probability in raw:
        key = (indices, delta)
        merged[key] = merged.get(key, 0.0) + float(probability)
    return [ProposalEvent(indices=key[0], delta=key[1], probability=value) for key, value in merged.items()]


def _state_year_events(move: MoveState) -> list[ProposalEvent]:
    groups = [np.asarray(group, dtype=int) for group in move.free_by_state_year if len(group) >= 2]
    if not groups:
        return [ProposalEvent(None, None, 1.0)]
    raw: list[tuple[tuple[int, ...] | None, tuple[int, ...] | None, float]] = []
    for group in groups:
        base = 1.0 / len(groups) / (len(group) * (len(group) - 1))
        for a, b in permutations(group.tolist(), 2):
            raw.append(((int(a), int(b)), (-1, 1), base))
    return _coalesce(raw)

def _interval_events(move: MoveState) -> list[ProposalEvent]:
    groups: list[np.ndarray] = []
    for group in move.free_by_state_year:
        if len(group) < 2:
            continue
        county = move.county_code[group]
        mask = np.asarray([int(code) in move.interval_counties for code in county], dtype=bool)
        filtered = np.asarray(group[mask], dtype=int)
        if len(filtered) >= 2:
            groups.append(filtered)
    if not groups:
        return [ProposalEvent(None, None, 1.0)]
    raw: list[tuple[tuple[int, ...] | None, tuple[int, ...] | None, float]] = []
    for group in groups:
        base = 1.0 / len(groups) / (len(group) * (len(group) - 1))
        for a, b in permutations(group.tolist(), 2):
            raw.append(((int(a), int(b)), (-1, 1), base))
    return _coalesce(raw)

def _swap_2x2_events(move: MoveState) -> list[ProposalEvent]:
    states = [int(state) for state, counties in move.state_counties.items() if len(counties) >= 2]
    years = [int(year) for year in move.years]
    if not states or len(years) < 2:
        return [ProposalEvent(None, None, 1.0)]
    raw: list[tuple[tuple[int, ...] | None, tuple[int, ...] | None, float]] = []
    for state in states:
        counties = [int(code) for code in move.state_counties[state]]
        base = (
            1.0
            / len(states)
            / (len(counties) * (len(counties) - 1))
            / (len(years) * (len(years) - 1))
        )
        for county_a, county_b in permutations(counties, 2):
            for year_a, year_b in permutations(years, 2):
                keys = [
                    (county_a, year_a),
                    (county_a, year_b),
                    (county_b, year_a),
                    (county_b, year_b),
                ]
                if any(key not in move.county_year_to_row for key in keys):
                    raw.append((None, None, base))
                    continue
                indices = tuple(int(move.county_year_to_row[key]) for key in keys)
                if any(move.upper[index] <= move.lower[index] for index in indices):
                    raw.append((None, None, base))
                    continue
                raw.append((indices, (1, -1, -1, 1), base))
    return _coalesce(raw)

def _cycle_events(move: MoveState, *, max_cycle_half_length: int = 6, max_events: int = 2_000_000) -> list[ProposalEvent]:
    years = [int(year) for year in move.years]
    eligible: list[tuple[int, list[int], int]] = []
    for state, counties_array in move.cycle_state_counties:
        candidates = [int(county) for county in counties_array]
        maximum = min(int(max_cycle_half_length), len(candidates), len(years))
        if maximum >= 3:
            eligible.append((int(state), candidates, maximum))
    if not eligible:
        return [ProposalEvent(None, None, 1.0)]

    anticipated = 0
    for _, candidates, maximum in eligible:
        for length in range(3, maximum + 1):
            anticipated += math.perm(len(candidates), length) * math.perm(len(years), length)
    if anticipated > max_events:
        raise ValueError(f"Exact cycle proposal enumeration requires {anticipated:,} events; limit is {max_events:,}.")

    raw: list[tuple[tuple[int, ...] | None, tuple[int, ...] | None, float]] = []
    for _, candidates, maximum in eligible:
        for length in range(3, maximum + 1):
            base = (
                1.0
                / len(eligible)
                / (maximum - 2)
                / math.perm(len(candidates), length)
                / math.perm(len(years), length)
            )
            for counties in permutations(candidates, length):
                for selected_years in permutations(years, length):
                    indices: list[int] = []
                    direction: list[int] = []
                    supported = True
                    for position in range(length):
                        positive_key = (int(counties[position]), int(selected_years[position]))
                        negative_key = (int(counties[(position + 1) % length]), int(selected_years[position]))
                        if positive_key not in move.county_year_to_row or negative_key not in move.county_year_to_row:
                            supported = False
                            break
                        positive = int(move.county_year_to_row[positive_key])
                        negative = int(move.county_year_to_row[negative_key])
                        if not (move.upper[positive] > move.lower[positive] and move.upper[negative] > move.lower[negative]):
                            supported = False
                            break
                        indices.extend([positive, negative])
                        direction.extend([1, -1])
                    if not supported:
                        raw.append((None, None, base))
                    else:
                        raw.append((tuple(indices), tuple(direction), base))
    return _coalesce(raw)

def proposal_events(move: MoveState, move_name: str, *, max_cycle_half_length: int = 6) -> list[ProposalEvent]:
    if move_name == "state_year_transfer":
        return _state_year_events(move)
    if move_name == "county_period_exploration":
        return _interval_events(move)
    if move_name == "swap_2x2":
        return _swap_2x2_events(move)
    if move_name == "cycle_swap":
        return _cycle_events(move, max_cycle_half_length=max_cycle_half_length)
    raise ValueError(f"Unknown move: {move_name}")


def normalized_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    values = {
        "state_year_transfer": 0.50,
        "county_period_exploration": 0.20,
        "swap_2x2": 0.20,
        "cycle_swap": 0.10,
    }
    if weights:
        for key, value in weights.items():
            if key in values:
                values[key] = float(value)
    total = sum(max(value, 0.0) for value in values.values())
    if total <= 0:
        raise ValueError("At least one count-move weight must be positive.")
    return {key: max(value, 0.0) / total for key, value in values.items()}



def _apply_event_if_feasible(
    source: np.ndarray,
    event: ProposalEvent,
    move: MoveState,
    period_total: np.ndarray,
) -> np.ndarray | None:
    if event.indices is None or event.delta is None:
        return None
    indices = np.asarray(event.indices, dtype=int)
    delta = np.asarray(event.delta, dtype=int)
    proposed_values = source[indices] + delta
    if np.any(proposed_values < move.lower[indices]) or np.any(proposed_values > move.upper[indices]):
        return None
    affected = np.unique(move.county_code[indices])
    updated_totals = period_total[affected].copy()
    for county in affected:
        updated_totals[affected == county] += int(delta[move.county_code[indices] == county].sum())
    if np.any(updated_totals < move.period_lower[affected]) or np.any(updated_totals > move.period_upper[affected]):
        return None
    proposed = source.copy()
    proposed[indices] = proposed_values
    return proposed

def exact_transition_matrix(
    states: np.ndarray,
    frame: pd.DataFrame,
    theta: Theta,
    design: Design,
    *,
    weights: dict[str, float] | None = None,
    max_cycle_half_length: int = 6,
) -> np.ndarray:
    states = np.asarray(states, dtype=int)
    state_lookup = {_state_key(state): index for index, state in enumerate(states)}
    mixture = normalized_weights(weights)
    matrix = np.zeros((len(states), len(states)), dtype=float)
    current_mu = mu(theta, design)
    kappa = float(np.exp(theta.log_kappa))

    # Block selection depends only on the static free-cell support. Conditional
    # on a selected direction, the production kernel samples every feasible
    # integer amplitude from its exact NB2 full conditional.
    template_move = build_move_state(frame, states[0].copy())
    events_by_move = {
        move_name: proposal_events(
            template_move, move_name, max_cycle_half_length=max_cycle_half_length
        )
        for move_name, move_weight in mixture.items()
        if move_weight > 0
    }

    for source_index, source in enumerate(states):
        period_total = np.bincount(
            template_move.county_code,
            weights=source,
            minlength=len(template_move.period_lower),
        ).astype(int)
        for move_name, move_weight in mixture.items():
            if move_weight <= 0:
                continue
            for event in events_by_move[move_name]:
                mass = move_weight * event.probability
                if event.indices is None or event.delta is None:
                    matrix[source_index, source_index] += mass
                    continue
                indices = np.asarray(event.indices, dtype=int)
                direction = np.asarray(event.delta, dtype=int)
                amplitudes = feasible_amplitudes(
                    source,
                    indices,
                    direction,
                    lower=template_move.lower,
                    upper=template_move.upper,
                    county_code=template_move.county_code,
                    period_total=period_total,
                    period_lower=template_move.period_lower,
                    period_upper=template_move.period_upper,
                )
                probabilities = amplitude_probabilities(
                    amplitude_log_weights(
                        source,
                        indices,
                        direction,
                        amplitudes,
                        current_mu[indices],
                        kappa,
                    )
                )
                for amplitude, probability in zip(amplitudes, probabilities):
                    proposed = source.copy()
                    proposed[indices] += int(amplitude) * direction
                    target_index = state_lookup.get(_state_key(proposed))
                    if target_index is None:
                        raise AssertionError(
                            "A heat-bath-feasible proposal was absent from the enumerated state space."
                        )
                    matrix[source_index, target_index] += mass * float(probability)
    return matrix

def exact_kernel_diagnostics(probabilities: np.ndarray, transition: np.ndarray, *, tolerance: float = 1e-14) -> ExactKernelDiagnostics:
    probabilities = np.asarray(probabilities, dtype=float)
    transition = np.asarray(transition, dtype=float)
    flow = probabilities[:, None] * transition
    adjacency = csr_matrix((transition > tolerance).astype(np.int8))
    components, _ = connected_components(adjacency, directed=True, connection="strong")
    return ExactKernelDiagnostics(
        states=int(len(probabilities)),
        row_sum_error=float(np.max(np.abs(transition.sum(axis=1) - 1.0))),
        stationarity_error=float(np.max(np.abs(probabilities @ transition - probabilities))),
        detailed_balance_error=float(np.max(np.abs(flow - flow.T))),
        strongly_connected_components=int(components),
    )


def empirical_count_kernel_frequencies(
    initial_state: np.ndarray,
    states: np.ndarray,
    frame: pd.DataFrame,
    theta: Theta,
    *,
    steps: int = 100_000,
    burn_in: int = 5_000,
    seed: int = 20260810,
    weights: dict[str, float] | None = None,
    max_cycle_half_length: int = 6,
) -> np.ndarray:
    if burn_in >= steps:
        raise ValueError("burn_in must be less than steps")
    design = make_design(frame)
    current_mu = mu(theta, design)
    kappa = float(np.exp(theta.log_kappa))
    mixture = normalized_weights(weights)
    thresholds = np.cumsum([mixture[key] for key in mixture])
    names = list(mixture)
    state_lookup = {_state_key(state): index for index, state in enumerate(np.asarray(states, dtype=int))}
    counts = np.zeros(len(states), dtype=int)
    y = np.asarray(initial_state, dtype=int).copy()
    move = build_move_state(frame, y)
    rng = np.random.default_rng(seed)

    for step in range(steps):
        draw = float(rng.uniform())
        move_name = names[int(np.searchsorted(thresholds, draw, side="right"))]
        if move_name == "state_year_transfer":
            state_year_transfer(y, move, current_mu, kappa, rng)
        elif move_name == "county_period_exploration":
            period_interval_transfer(y, move, current_mu, kappa, rng)
        elif move_name == "swap_2x2":
            state_2x2_swap(y, move, current_mu, kappa, rng)
        else:
            state_cycle_swap(y, move, current_mu, kappa, rng, max_cycle_half_length=max_cycle_half_length)
        if step >= burn_in:
            index = state_lookup.get(_state_key(y))
            if index is None:
                raise AssertionError("The empirical kernel left the enumerated feasible state space.")
            counts[index] += 1
    return counts / counts.sum()
