from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_exact(path: Path, old: str, new: str, *, expected: int = 1) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"Expected {expected} occurrence(s) in {path}, found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    return True


FAST_HELPER = '''\n\ndef _apply_event_if_feasible(\n    source: np.ndarray,\n    event: ProposalEvent,\n    move: MoveState,\n    period_total: np.ndarray,\n) -> np.ndarray | None:\n    if event.indices is None or event.delta is None:\n        return None\n    indices = np.asarray(event.indices, dtype=int)\n    delta = np.asarray(event.delta, dtype=int)\n    proposed_values = source[indices] + delta\n    if np.any(proposed_values < move.lower[indices]) or np.any(proposed_values > move.upper[indices]):\n        return None\n    affected = np.unique(move.county_code[indices])\n    updated_totals = period_total[affected].copy()\n    for county in affected:\n        updated_totals[affected == county] += int(delta[move.county_code[indices] == county].sum())\n    if np.any(updated_totals < move.period_lower[affected]) or np.any(updated_totals > move.period_upper[affected]):\n        return None\n    proposed = source.copy()\n    proposed[indices] = proposed_values\n    return proposed\n'''


NEW_TRANSITION = '''def exact_transition_matrix(\n    states: np.ndarray,\n    frame: pd.DataFrame,\n    theta: Theta,\n    design: Design,\n    *,\n    weights: dict[str, float] | None = None,\n    max_cycle_half_length: int = 6,\n) -> np.ndarray:\n    states = np.asarray(states, dtype=int)\n    state_lookup = {_state_key(state): index for index, state in enumerate(states)}\n    mixture = normalized_weights(weights)\n    matrix = np.zeros((len(states), len(states)), dtype=float)\n    log_likelihoods = np.asarray([log_likelihood(state, theta, design) for state in states], dtype=float)\n\n    # Proposal selection depends on the static support, not on current counts.\n    # Enumerate each move law once, then apply fast cell-bound and county-margin\n    # checks for every source state. This makes randomized finite-fiber audits\n    # practical without changing the exact transition probabilities.\n    template_move = build_move_state(frame, states[0].copy())\n    events_by_move = {\n        move_name: proposal_events(\n            template_move, move_name, max_cycle_half_length=max_cycle_half_length\n        )\n        for move_name, move_weight in mixture.items()\n        if move_weight > 0\n    }\n\n    for source_index, source in enumerate(states):\n        period_total = np.bincount(\n            template_move.county_code, weights=source, minlength=len(template_move.period_lower)\n        ).astype(int)\n        for move_name, move_weight in mixture.items():\n            if move_weight <= 0:\n                continue\n            for event in events_by_move[move_name]:\n                mass = move_weight * event.probability\n                proposed = _apply_event_if_feasible(source, event, template_move, period_total)\n                if proposed is None:\n                    matrix[source_index, source_index] += mass\n                    continue\n                target_index = state_lookup.get(_state_key(proposed))\n                if target_index is None:\n                    raise AssertionError(\n                        "A fast-feasible proposal was absent from the enumerated state space."\n                    )\n                log_ratio = log_likelihoods[target_index] - log_likelihoods[source_index]\n                acceptance = 1.0 if log_ratio >= 0 else float(np.exp(log_ratio))\n                matrix[source_index, target_index] += mass * acceptance\n                matrix[source_index, source_index] += mass * (1.0 - acceptance)\n    return matrix\n'''


def main() -> None:
    path = ROOT / "src" / "bayes_constrained" / "exact_validation.py"
    changed = False
    changed |= replace_exact(
        path,
        '''def _cycle_events(move: MoveState, *, max_cycle_half_length: int = 6, max_events: int = 2_000_000) -> list[ProposalEvent]:\n    years = [int(year) for year in np.unique(move.year_code)]\n    eligible: list[tuple[int, list[int], int]] = []\n    for state, counties_array in move.state_counties.items():\n        candidates: list[int] = []\n        for county in counties_array:\n            rows = np.where(\n                (move.state_code == int(state))\n                & (move.county_code == int(county))\n                & (move.upper > move.lower)\n            )[0]\n            if len(rows) >= 2:\n                candidates.append(int(county))\n        maximum = min(int(max_cycle_half_length), len(candidates), len(years))\n        if maximum >= 3:\n            eligible.append((int(state), candidates, maximum))\n''',
        '''def _cycle_events(move: MoveState, *, max_cycle_half_length: int = 6, max_events: int = 2_000_000) -> list[ProposalEvent]:\n    years = [int(year) for year in move.years]\n    eligible: list[tuple[int, list[int], int]] = []\n    for state, counties_array in move.cycle_state_counties:\n        candidates = [int(county) for county in counties_array]\n        maximum = min(int(max_cycle_half_length), len(candidates), len(years))\n        if maximum >= 3:\n            eligible.append((int(state), candidates, maximum))\n''',
    )
    changed |= replace_exact(
        path,
        '\ndef exact_transition_matrix(\n',
        FAST_HELPER + '\ndef exact_transition_matrix(\n',
    )
    text = path.read_text(encoding="utf-8")
    start = text.index("def exact_transition_matrix(\n")
    end = text.index("\n\ndef exact_kernel_diagnostics", start)
    current = text[start:end]
    if current != NEW_TRANSITION.rstrip("\n"):
        path.write_text(text[:start] + NEW_TRANSITION.rstrip("\n") + text[end:], encoding="utf-8")
        changed = True
    print("Exact-validation cache applied." if changed else "Exact-validation cache already present.")


if __name__ == "__main__":
    main()
