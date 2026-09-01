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


HEATBATH_HELPER = '''\n\ndef _apply_heatbath_direction(\n    y: np.ndarray,\n    move: MoveState,\n    indices: np.ndarray,\n    direction: np.ndarray,\n    current_mu: np.ndarray,\n    kappa: float,\n    rng: np.random.Generator,\n) -> bool:\n    indices = np.asarray(indices, dtype=int)\n    direction = np.asarray(direction, dtype=int)\n    amplitudes = feasible_amplitudes(\n        y,\n        indices,\n        direction,\n        lower=move.lower,\n        upper=move.upper,\n        county_code=move.county_code,\n        period_total=move.period_total,\n        period_lower=move.period_lower,\n        period_upper=move.period_upper,\n    )\n    amplitude = sample_amplitude(\n        y, indices, direction, amplitudes, current_mu[indices], kappa, rng\n    )\n    if amplitude == 0:\n        return False\n    change = amplitude * direction\n    y[indices] += change\n    for county in np.unique(move.county_code[indices]):\n        move.period_total[county] += int(change[move.county_code[indices] == county].sum())\n    return True\n'''


NEW_TRANSFER = '''def state_year_transfer(y: np.ndarray, move: MoveState, current_mu: np.ndarray, kappa: float, rng: np.random.Generator) -> bool:\n    groups = [g for g in move.free_by_state_year if len(g) >= 2]\n    if not groups:\n        return False\n    group = groups[int(rng.integers(0, len(groups)))]\n    a, b = rng.choice(group, size=2, replace=False)\n    return _apply_heatbath_direction(\n        y, move, np.asarray([a, b]), np.asarray([-1, 1]), current_mu, kappa, rng\n    )\n'''


NEW_INTERVAL = '''def period_interval_transfer(y: np.ndarray, move: MoveState, current_mu: np.ndarray, kappa: float, rng: np.random.Generator) -> bool:\n    groups = []\n    for group in move.free_by_state_year:\n        if len(group) < 2:\n            continue\n        county = move.county_code[group]\n        mask = np.asarray([int(code) in move.interval_counties for code in county])\n        if mask.sum() >= 2:\n            groups.append(group[mask])\n    if not groups:\n        return False\n    group = groups[int(rng.integers(0, len(groups)))]\n    a, b = rng.choice(group, size=2, replace=False)\n    return _apply_heatbath_direction(\n        y, move, np.asarray([a, b]), np.asarray([-1, 1]), current_mu, kappa, rng\n    )\n'''


NEW_SWAP = '''def state_2x2_swap(y: np.ndarray, move: MoveState, current_mu: np.ndarray, kappa: float, rng: np.random.Generator) -> bool:\n    states = [state for state, counties in move.state_counties.items() if len(counties) >= 2]\n    if not states:\n        return False\n    state = states[int(rng.integers(0, len(states)))]\n    counties = rng.choice(move.state_counties[state], size=2, replace=False)\n    if len(move.years) < 2:\n        return False\n    year_a, year_b = rng.choice(move.years, size=2, replace=False)\n    keys = [\n        (int(counties[0]), int(year_a)),\n        (int(counties[0]), int(year_b)),\n        (int(counties[1]), int(year_a)),\n        (int(counties[1]), int(year_b)),\n    ]\n    if any(key not in move.county_year_to_row for key in keys):\n        return False\n    indices = np.asarray([move.county_year_to_row[key] for key in keys], dtype=int)\n    if np.any(move.upper[indices] <= move.lower[indices]):\n        return False\n    return _apply_heatbath_direction(\n        y, move, indices, np.asarray([1, -1, -1, 1]), current_mu, kappa, rng\n    )\n'''


NEW_CYCLE_TAIL = '''    indices_array = np.asarray(indices, dtype=int)\n    direction = np.asarray(delta, dtype=int)\n    return _apply_heatbath_direction(\n        y, move, indices_array, direction, current_mu, kappa, rng\n    )\n'''


def replace_function(path: Path, name: str, replacement: str, next_name: str) -> bool:
    text = path.read_text(encoding="utf-8")
    start_marker = f"def {name}("
    end_marker = f"\n\ndef {next_name}("
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    current = text[start:end]
    desired = replacement.rstrip("\n")
    if current == desired:
        return False
    path.write_text(text[:start] + desired + text[end:], encoding="utf-8")
    return True


def main() -> None:
    path = ROOT / "src" / "bayes_constrained" / "sampler.py"
    changed = False
    changed |= replace_exact(
        path,
        "from .data import load_config\n",
        "from .data import load_config\nfrom .heatbath import feasible_amplitudes, sample_amplitude\n",
    )
    changed |= replace_exact(
        path,
        "\ndef state_year_transfer(",
        HEATBATH_HELPER + "\ndef state_year_transfer(",
    )
    changed |= replace_function(path, "state_year_transfer", NEW_TRANSFER, "period_interval_transfer")
    changed |= replace_function(path, "period_interval_transfer", NEW_INTERVAL, "state_2x2_swap")
    changed |= replace_function(path, "state_2x2_swap", NEW_SWAP, "state_cycle_swap")

    text = path.read_text(encoding="utf-8")
    old_tail = '''    idx = np.asarray(indices, dtype=int)\n    change = np.asarray(delta, dtype=int)\n    if rng.uniform() < 0.5:\n        change = -change\n    return _try_apply_delta(y, move, idx, change, current_mu, kappa, rng)\n'''
    if NEW_CYCLE_TAIL not in text:
        if text.count(old_tail) != 1:
            raise RuntimeError("Unable to locate the general-cycle Metropolis tail.")
        path.write_text(text.replace(old_tail, NEW_CYCLE_TAIL, 1), encoding="utf-8")
        changed = True
    print("Heat-bath count kernel applied." if changed else "Heat-bath count kernel already present.")


if __name__ == "__main__":
    main()
