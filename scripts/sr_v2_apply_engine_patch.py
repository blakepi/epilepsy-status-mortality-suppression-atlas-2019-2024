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


def insert_before(path: Path, anchor: str, insertion: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if insertion.strip() in text:
        return False
    if text.count(anchor) != 1:
        raise RuntimeError(f"Expected one anchor in {path}: {anchor!r}")
    path.write_text(text.replace(anchor, insertion + anchor, 1), encoding="utf-8")
    return True


def patch_model() -> bool:
    path = ROOT / "src" / "bayes_constrained" / "model.py"
    changed = False
    changed |= replace_exact(
        path,
        "from .data import RURAL_ORDER, SVI_ORDER\n",
        "from .data import RURAL_ORDER, SVI_ORDER\nfrom .target_density import centered_normal_log_density\n",
    )
    changed |= replace_exact(
        path,
        '''    state = theta.state_effect - theta.state_effect.mean()\n    year = theta.year_effect - theta.year_effect.mean()\n    lp += float((-0.5 * (state / sigma_state) ** 2 - np.log(sigma_state)).sum())\n    lp += float((-0.5 * (year / sigma_year) ** 2 - np.log(sigma_year)).sum())\n''',
        '''    state = theta.state_effect - theta.state_effect.mean()\n    year = theta.year_effect - theta.year_effect.mean()\n    # The effects live on sum-to-zero subspaces of dimensions S-1 and T-1.\n    # Counting S or T Gaussian normalizers would add an unintended -log(sigma)\n    # term and over-shrink the corresponding hierarchical scale.\n    lp += centered_normal_log_density(state, sigma_state)\n    lp += centered_normal_log_density(year, sigma_year)\n''',
    )
    return changed


CYCLE_FUNCTION = '''\n\ndef state_cycle_swap(\n    y: np.ndarray,\n    move: MoveState,\n    current_mu: np.ndarray,\n    kappa: float,\n    rng: np.random.Generator,\n    *,\n    max_cycle_half_length: int = 6,\n) -> bool:\n    \"\"\"Propose an alternating move around a simple bipartite support cycle.\n\n    Two-by-two swaps are not a Markov basis when fixed cells create structural\n    zeros. A feasible fiber can contain longer even cycles but no admissible\n    2x2 rectangle. This proposal samples ordered counties and years from the\n    static free-cell support and alternates +1/-1 around the resulting cycle.\n    It preserves every state-year and county-period total exactly. Because the\n    selection law is independent of the current counts and the opposite sign\n    has the same probability, the proposal is symmetric.\n    \"\"\"\n\n    years = np.unique(move.year_code)\n    eligible: list[tuple[int, np.ndarray, int]] = []\n    for state, counties in move.state_counties.items():\n        candidates = []\n        for county in counties:\n            rows = np.where(\n                (move.state_code == int(state))\n                & (move.county_code == int(county))\n                & (move.upper > move.lower)\n            )[0]\n            if len(rows) >= 2:\n                candidates.append(int(county))\n        maximum = min(int(max_cycle_half_length), len(candidates), len(years))\n        if maximum >= 3:\n            eligible.append((int(state), np.asarray(candidates, dtype=int), maximum))\n    if not eligible:\n        return False\n\n    _, counties, maximum = eligible[int(rng.integers(0, len(eligible)))]\n    length = int(rng.integers(3, maximum + 1))\n    selected_counties = rng.choice(counties, size=length, replace=False)\n    selected_years = rng.choice(years, size=length, replace=False)\n\n    indices: list[int] = []\n    delta: list[int] = []\n    for position in range(length):\n        positive_key = (int(selected_counties[position]), int(selected_years[position]))\n        negative_key = (int(selected_counties[(position + 1) % length]), int(selected_years[position]))\n        if positive_key not in move.county_year_to_row or negative_key not in move.county_year_to_row:\n            return False\n        positive = int(move.county_year_to_row[positive_key])\n        negative = int(move.county_year_to_row[negative_key])\n        if not (move.upper[positive] > move.lower[positive] and move.upper[negative] > move.lower[negative]):\n            return False\n        indices.extend([positive, negative])\n        delta.extend([1, -1])\n\n    idx = np.asarray(indices, dtype=int)\n    change = np.asarray(delta, dtype=int)\n    if rng.uniform() < 0.5:\n        change = -change\n    return _try_apply_delta(y, move, idx, change, current_mu, kappa, rng)\n'''


WEIGHT_HELPER = '''\n\ndef _normalized_move_weights(settings: dict) -> dict[str, float]:\n    configured = settings.get("move_weights", {}) or {}\n    values = {\n        "state_year_transfer": float(configured.get("state_year_transfer", configured.get("transfer", 0.50))),\n        "county_period_exploration": float(configured.get("county_period_exploration", configured.get("interval_transfer", 0.20))),\n        "swap_2x2": float(configured.get("swap_2x2", 0.20)),\n        "cycle_swap": float(configured.get("cycle_swap", 0.10)),\n    }\n    values = {key: max(value, 0.0) for key, value in values.items()}\n    total = sum(values.values())\n    if total <= 0:\n        raise ValueError("At least one latent-count move weight must be positive.")\n    return {key: value / total for key, value in values.items()}\n'''


def patch_sampler() -> bool:
    path = ROOT / "src" / "bayes_constrained" / "sampler.py"
    changed = False
    changed |= insert_before(path, "\ndef blocked_refresh(", CYCLE_FUNCTION)
    changed |= insert_before(path, "\ndef _theta_to_rows(", WEIGHT_HELPER)
    changed |= replace_exact(
        path,
        '''        "block_size",\n        "move_weights",\n''',
        '''        "block_size",\n        "max_cycle_half_length",\n        "move_weights",\n''',
    )
    changed |= replace_exact(
        path,
        '''    move_weights = settings.get("move_weights", {})\n    weight_transfer = float(move_weights.get("state_year_transfer", move_weights.get("transfer", 0.55)))\n    weight_interval = float(move_weights.get("county_period_exploration", move_weights.get("interval_transfer", 0.20)))\n    weight_swap = float(move_weights.get("swap_2x2", 0.25))\n    weight_total = max(weight_transfer + weight_interval + weight_swap, 1e-12)\n    weight_transfer /= weight_total\n    weight_interval /= weight_total\n''',
        '''    move_weights = _normalized_move_weights(settings)\n    weight_transfer = move_weights["state_year_transfer"]\n    weight_interval = move_weights["county_period_exploration"]\n    weight_swap = move_weights["swap_2x2"]\n    weight_cycle = move_weights["cycle_swap"]\n    max_cycle_half_length = int(settings.get("max_cycle_half_length", 6))\n''',
    )
    changed |= replace_exact(
        path,
        '''        accepted = {"transfer": 0, "interval_transfer": 0, "swap_2x2": 0, "blocked_refresh": 0}\n''',
        '''        accepted = {"transfer": 0, "interval_transfer": 0, "swap_2x2": 0, "cycle_swap": 0, "blocked_refresh": 0}\n''',
        expected=2,
    )
    changed |= replace_exact(
        path,
        '''                elif r < weight_transfer + weight_interval:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n''',
        '''                elif r < weight_transfer + weight_interval:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval + weight_swap:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["cycle_swap"] += 1\n                    accepted["cycle_swap"] += int(\n                        state_cycle_swap(\n                            y, move, current_mu, kappa, rng, max_cycle_half_length=max_cycle_half_length\n                        )\n                    )\n''',
    )
    changed |= replace_exact(
        path,
        '''    n_chains = int(settings.get("n_chains", 4))\n    chain_rows = []\n''',
        '''    n_chains = int(settings.get("n_chains", 4))\n    move_weights = _normalized_move_weights(settings)\n    weight_transfer = move_weights["state_year_transfer"]\n    weight_interval = move_weights["county_period_exploration"]\n    weight_swap = move_weights["swap_2x2"]\n    weight_cycle = move_weights["cycle_swap"]\n    max_cycle_half_length = int(settings.get("max_cycle_half_length", 6))\n    chain_rows = []\n''',
    )
    changed |= replace_exact(
        path,
        '''                if r < 0.55:\n                    proposed["transfer"] += 1\n                    accepted["transfer"] += int(state_year_transfer(y, move, current_mu, kappa, rng))\n                elif r < 0.75:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n''',
        '''                if r < weight_transfer:\n                    proposed["transfer"] += 1\n                    accepted["transfer"] += int(state_year_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval:\n                    proposed["interval_transfer"] += 1\n                    accepted["interval_transfer"] += int(period_interval_transfer(y, move, current_mu, kappa, rng))\n                elif r < weight_transfer + weight_interval + weight_swap:\n                    proposed["swap_2x2"] += 1\n                    accepted["swap_2x2"] += int(state_2x2_swap(y, move, current_mu, kappa, rng))\n                else:\n                    proposed["cycle_swap"] += 1\n                    accepted["cycle_swap"] += int(\n                        state_cycle_swap(\n                            y, move, current_mu, kappa, rng, max_cycle_half_length=max_cycle_half_length\n                        )\n                    )\n''',
    )
    changed |= replace_exact(
        path,
        '''            if blocked_frequency and iteration % blocked_frequency == 0:\n                proposed["blocked_refresh"] += 12\n                accepted["blocked_refresh"] += blocked_refresh(y, move, current_mu, kappa, rng, attempts=12)\n            for block, scale in scales.items():\n''',
        '''            if blocked_frequency and iteration % blocked_frequency == 0:\n                proposed["blocked_refresh"] += 12\n                accepted["blocked_refresh"] += blocked_refresh(y, move, current_mu, kappa, rng, attempts=12)\n            # Count moves mutate y. Refresh the current target value before any\n            # parameter Metropolis ratio is evaluated. The v1 local runner\n            # compared proposals against a log posterior from the previous y.\n            current_lp = log_posterior_theta(y, theta, design, intercept_mean=intercept_mean)\n            for block, scale in scales.items():\n''',
    )
    return changed


def main() -> None:
    changed = patch_model()
    changed |= patch_sampler()
    print("Scientific Reports v2 engine patch applied." if changed else "Scientific Reports v2 engine patch already present.")


if __name__ == "__main__":
    main()
