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


PATH_MOVE = '''\n\ndef interval_path_transfer(\n    y: np.ndarray,\n    move: MoveState,\n    current_mu: np.ndarray,\n    kappa: float,\n    rng: np.random.Generator,\n) -> bool:\n    groups = move.interval_path_support.endpoint_groups\n    if not groups:\n        return False\n    group = groups[int(rng.integers(0, len(groups)))]\n    endpoint_a, endpoint_b = rng.choice(group, size=2, replace=False)\n    proposal = interval_path_direction(\n        int(endpoint_a),\n        int(endpoint_b),\n        state_code=move.state_code,\n        year_code=move.year_code,\n        support=move.interval_path_support,\n    )\n    if proposal is None:\n        return False\n    indices, direction = proposal\n    return _apply_heatbath_direction(\n        y, move, indices, direction, current_mu, kappa, rng\n    )\n'''


HPC_DISPATCH_OLD = '''                elif r < weight_transfer + weight_interval:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval + weight_swap:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["cycle_swap"] += 1\n                    accepted["cycle_swap"] += int(\n                        state_cycle_swap(\n                            y, move, current_mu, kappa, rng, max_cycle_half_length=max_cycle_half_length\n                        )\n                    )\n'''


WEIGHTED_DISPATCH_NEW = '''                elif r < weight_transfer + weight_interval:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval + weight_path:\n                    proposed["interval_path"] += 1\n                    accepted["interval_path"] += int(interval_path_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval + weight_path + weight_swap:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["cycle_swap"] += 1\n                    accepted["cycle_swap"] += int(\n                        state_cycle_swap(\n                            y, move, current_mu, kappa, rng, max_cycle_half_length=max_cycle_half_length\n                        )\n                    )\n'''


LOCAL_DISPATCH_OLD = '''                if r < 0.55:\n                    proposed["transfer"] += 1\n                    accepted["transfer"] += int(state_year_transfer(y, move, current_mu, kappa, rng))\n                elif r < 0.75:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n'''


LOCAL_DISPATCH_NEW = '''                if r < weight_transfer:\n                    proposed["transfer"] += 1\n                    accepted["transfer"] += int(state_year_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval + weight_path:\n                    proposed["interval_path"] += 1\n                    accepted["interval_path"] += int(interval_path_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval + weight_path + weight_swap:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["cycle_swap"] += 1\n                    accepted["cycle_swap"] += int(\n                        state_cycle_swap(\n                            y, move, current_mu, kappa, rng, max_cycle_half_length=max_cycle_half_length\n                        )\n                    )\n'''


def patch_sampler() -> bool:
    path = ROOT / "src" / "bayes_constrained" / "sampler.py"
    changed = False
    changed |= replace_exact(
        path,
        "from .heatbath import feasible_amplitudes, sample_amplitude\n",
        "from .heatbath import feasible_amplitudes, sample_amplitude\nfrom .interval_paths import IntervalPathSupport, build_interval_path_support, interval_path_direction\n",
    )
    changed |= replace_exact(
        path,
        '''    cycle_state_counties: list[tuple[int, np.ndarray]]\n''',
        '''    cycle_state_counties: list[tuple[int, np.ndarray]]\n    interval_path_support: IntervalPathSupport\n''',
    )
    changed |= replace_exact(
        path,
        '''        if len(candidates) >= 3 and len(years) >= 3:\n            cycle_state_counties.append((int(state), np.asarray(candidates, dtype=int)))\n    return MoveState(\n''',
        '''        if len(candidates) >= 3 and len(years) >= 3:\n            cycle_state_counties.append((int(state), np.asarray(candidates, dtype=int)))\n    interval_path_support = build_interval_path_support(\n        lower=lower,\n        upper=upper,\n        county_code=county_code,\n        state_code=state_code,\n        year_code=year_code,\n        interval_counties=interval_counties,\n        county_year_to_row=county_year_to_row,\n    )\n    return MoveState(\n''',
    )
    changed |= replace_exact(
        path,
        '''        years=years,\n        cycle_state_counties=cycle_state_counties,\n    )\n''',
        '''        years=years,\n        cycle_state_counties=cycle_state_counties,\n        interval_path_support=interval_path_support,\n    )\n''',
    )
    changed |= replace_exact(
        path,
        "\ndef state_2x2_swap(",
        PATH_MOVE + "\ndef state_2x2_swap(",
    )
    changed |= replace_exact(
        path,
        '''        "county_period_exploration": float(configured.get("county_period_exploration", configured.get("interval_transfer", 0.20))),\n        "swap_2x2": float(configured.get("swap_2x2", 0.20)),\n        "cycle_swap": float(configured.get("cycle_swap", 0.10)),\n''',
        '''        "county_period_exploration": float(configured.get("county_period_exploration", configured.get("interval_transfer", 0.25))),\n        "interval_path_transfer": float(configured.get("interval_path_transfer", 0.20)),\n        "swap_2x2": float(configured.get("swap_2x2", 0.25)),\n        "cycle_swap": float(configured.get("cycle_swap", 0.10)),\n''',
    )
    changed |= replace_exact(
        path,
        '''    weight_interval = move_weights["county_period_exploration"]\n    weight_swap = move_weights["swap_2x2"]\n    weight_cycle = move_weights["cycle_swap"]\n''',
        '''    weight_interval = move_weights["county_period_exploration"]\n    weight_path = move_weights["interval_path_transfer"]\n    weight_swap = move_weights["swap_2x2"]\n    weight_cycle = move_weights["cycle_swap"]\n''',
        expected=2,
    )
    changed |= replace_exact(
        path,
        '''        accepted = {"transfer": 0, "interval_transfer": 0, "swap_2x2": 0, "cycle_swap": 0, "blocked_refresh": 0}\n''',
        '''        accepted = {"transfer": 0, "interval_transfer": 0, "interval_path": 0, "swap_2x2": 0, "cycle_swap": 0, "blocked_refresh": 0}\n''',
        expected=2,
    )
    # The HPC and local runners intentionally have different historical loop
    # bodies, so patch them separately. Requiring two identical matches caused
    # the first isolated gate to fail before tests could run.
    changed |= replace_exact(path, HPC_DISPATCH_OLD, WEIGHTED_DISPATCH_NEW)
    changed |= replace_exact(path, LOCAL_DISPATCH_OLD, LOCAL_DISPATCH_NEW)
    return changed


def patch_latent_pilot() -> bool:
    path = ROOT / "src" / "bayes_constrained" / "latent_pilot.py"
    changed = False
    changed |= replace_exact(
        path,
        '''    build_move_state,\n    period_interval_transfer,\n    state_2x2_swap,\n''',
        '''    build_move_state,\n    period_interval_transfer,\n    interval_path_transfer,\n    state_2x2_swap,\n''',
    )
    changed |= replace_exact(
        path,
        '''            elif name == "county_period_exploration":\n                ok = period_interval_transfer(y, move, current_mu, kappa, rng)\n            elif name == "swap_2x2":\n''',
        '''            elif name == "county_period_exploration":\n                ok = period_interval_transfer(y, move, current_mu, kappa, rng)\n            elif name == "interval_path_transfer":\n                ok = interval_path_transfer(y, move, current_mu, kappa, rng)\n            elif name == "swap_2x2":\n''',
    )
    return changed


def main() -> None:
    changed = patch_sampler()
    changed |= patch_latent_pilot()
    print("Interval-endpoint path kernel applied." if changed else "Interval-endpoint path kernel already present.")


if __name__ == "__main__":
    main()
