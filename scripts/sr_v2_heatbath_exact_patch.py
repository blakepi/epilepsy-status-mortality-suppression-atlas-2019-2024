from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_exact(path: Path, old: str, new: str, *, expected: int = 1) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"Expected {expected} occurrence(s) in {path}, found {count}: {old[:140]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    return True


def replace_function(path: Path, name: str, replacement: str, next_name: str) -> bool:
    text = path.read_text(encoding="utf-8")
    start = text.index(f"def {name}(")
    end = text.index(f"\n\ndef {next_name}(", start)
    desired = replacement.rstrip("\n")
    if text[start:end] == desired:
        return False
    path.write_text(text[:start] + desired + text[end:], encoding="utf-8")
    return True


STATE_YEAR_EVENTS = '''def _state_year_events(move: MoveState) -> list[ProposalEvent]:
    groups = [np.asarray(group, dtype=int) for group in move.free_by_state_year if len(group) >= 2]
    if not groups:
        return [ProposalEvent(None, None, 1.0)]
    raw: list[tuple[tuple[int, ...] | None, tuple[int, ...] | None, float]] = []
    for group in groups:
        base = 1.0 / len(groups) / (len(group) * (len(group) - 1))
        for a, b in permutations(group.tolist(), 2):
            raw.append(((int(a), int(b)), (-1, 1), base))
    return _coalesce(raw)
'''


INTERVAL_EVENTS = '''def _interval_events(move: MoveState) -> list[ProposalEvent]:
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
'''


SWAP_EVENTS = '''def _swap_2x2_events(move: MoveState) -> list[ProposalEvent]:
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
'''


CYCLE_EVENTS = '''def _cycle_events(move: MoveState, *, max_cycle_half_length: int = 6, max_events: int = 2_000_000) -> list[ProposalEvent]:
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
'''


TRANSITION = '''def exact_transition_matrix(
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
'''


def main() -> None:
    path = ROOT / "src" / "bayes_constrained" / "exact_validation.py"
    changed = False
    changed |= replace_exact(
        path,
        "from .constraints import validate_constraints\n",
        "from .constraints import validate_constraints\nfrom .heatbath import amplitude_log_weights, amplitude_probabilities, feasible_amplitudes\n",
    )
    changed |= replace_function(path, "_state_year_events", STATE_YEAR_EVENTS, "_interval_events")
    changed |= replace_function(path, "_interval_events", INTERVAL_EVENTS, "_swap_2x2_events")
    changed |= replace_function(path, "_swap_2x2_events", SWAP_EVENTS, "_cycle_events")
    changed |= replace_function(path, "_cycle_events", CYCLE_EVENTS, "proposal_events")
    changed |= replace_function(path, "exact_transition_matrix", TRANSITION, "exact_kernel_diagnostics")
    print("Exact heat-bath transition audit applied." if changed else "Exact heat-bath transition audit already present.")


if __name__ == "__main__":
    main()
