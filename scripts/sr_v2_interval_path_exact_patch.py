from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_exact(path: Path, old: str, new: str, *, expected: int = 1) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"Expected {expected} occurrence(s) in {path}, found {count}: {old[:160]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    return True


PATH_EVENTS = '''\n\ndef _interval_path_events(move: MoveState) -> list[ProposalEvent]:\n    groups = move.interval_path_support.endpoint_groups\n    if not groups:\n        return [ProposalEvent(None, None, 1.0)]\n    raw: list[tuple[tuple[int, ...] | None, tuple[int, ...] | None, float]] = []\n    for group in groups:\n        base = 1.0 / len(groups) / (len(group) * (len(group) - 1))\n        for endpoint_a, endpoint_b in permutations(group.tolist(), 2):\n            proposal = interval_path_direction(\n                int(endpoint_a),\n                int(endpoint_b),\n                state_code=move.state_code,\n                year_code=move.year_code,\n                support=move.interval_path_support,\n            )\n            if proposal is None:\n                raw.append((None, None, base))\n            else:\n                indices, direction = proposal\n                raw.append((tuple(indices.tolist()), tuple(direction.tolist()), base))\n    return _coalesce(raw)\n'''


def main() -> None:
    path = ROOT / "src" / "bayes_constrained" / "exact_validation.py"
    changed = False
    changed |= replace_exact(
        path,
        "from .model import Design, Theta, log_likelihood, make_design, mu\n",
        "from .interval_paths import interval_path_direction\nfrom .model import Design, Theta, log_likelihood, make_design, mu\n",
    )
    changed |= replace_exact(
        path,
        '''    period_interval_transfer,\n    state_2x2_swap,\n''',
        '''    period_interval_transfer,\n    interval_path_transfer,\n    state_2x2_swap,\n''',
    )
    changed |= replace_exact(
        path,
        "\ndef _swap_2x2_events(",
        PATH_EVENTS + "\ndef _swap_2x2_events(",
    )
    changed |= replace_exact(
        path,
        '''    if move_name == "county_period_exploration":\n        return _interval_events(move)\n    if move_name == "swap_2x2":\n''',
        '''    if move_name == "county_period_exploration":\n        return _interval_events(move)\n    if move_name == "interval_path_transfer":\n        return _interval_path_events(move)\n    if move_name == "swap_2x2":\n''',
    )
    changed |= replace_exact(
        path,
        '''        "state_year_transfer": 0.50,\n        "county_period_exploration": 0.20,\n        "swap_2x2": 0.20,\n        "cycle_swap": 0.10,\n''',
        '''        "state_year_transfer": 0.10,\n        "county_period_exploration": 0.25,\n        "interval_path_transfer": 0.20,\n        "swap_2x2": 0.25,\n        "cycle_swap": 0.20,\n''',
    )
    changed |= replace_exact(
        path,
        '''        elif move_name == "county_period_exploration":\n            period_interval_transfer(y, move, current_mu, kappa, rng)\n        elif move_name == "swap_2x2":\n''',
        '''        elif move_name == "county_period_exploration":\n            period_interval_transfer(y, move, current_mu, kappa, rng)\n        elif move_name == "interval_path_transfer":\n            interval_path_transfer(y, move, current_mu, kappa, rng)\n        elif move_name == "swap_2x2":\n''',
    )
    print("Exact interval-path audit applied." if changed else "Exact interval-path audit already present.")


if __name__ == "__main__":
    main()
