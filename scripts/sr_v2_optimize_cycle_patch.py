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


def main() -> None:
    path = ROOT / "src" / "bayes_constrained" / "sampler.py"
    changed = False
    changed |= replace_exact(
        path,
        '''    free_by_state_year: list[np.ndarray]\n    interval_counties: set[int]\n''',
        '''    free_by_state_year: list[np.ndarray]\n    interval_counties: set[int]\n    years: np.ndarray\n    cycle_state_counties: list[tuple[int, np.ndarray]]\n''',
    )
    changed |= replace_exact(
        path,
        '''    period_status = frame.drop_duplicates("county_fips").sort_values("county_fips")["q001_period_status"].astype(str).to_numpy()\n    interval_counties = set(np.where(period_status == "suppressed_1_9")[0].tolist())\n    return MoveState(\n''',
        '''    period_status = frame.drop_duplicates("county_fips").sort_values("county_fips")["q001_period_status"].astype(str).to_numpy()\n    interval_counties = set(np.where(period_status == "suppressed_1_9")[0].tolist())\n    years = np.unique(year_code)\n    free_mask = upper > lower\n    cycle_state_counties: list[tuple[int, np.ndarray]] = []\n    for state, state_county_codes in state_counties.items():\n        candidates = []\n        for county in state_county_codes:\n            rows = np.where(\n                (state_code == int(state))\n                & (county_code == int(county))\n                & free_mask\n            )[0]\n            if len(rows) >= 2:\n                candidates.append(int(county))\n        if len(candidates) >= 3 and len(years) >= 3:\n            cycle_state_counties.append((int(state), np.asarray(candidates, dtype=int)))\n    return MoveState(\n''',
    )
    changed |= replace_exact(
        path,
        '''        free_by_state_year=free_by_state_year,\n        interval_counties=interval_counties,\n    )\n''',
        '''        free_by_state_year=free_by_state_year,\n        interval_counties=interval_counties,\n        years=years,\n        cycle_state_counties=cycle_state_counties,\n    )\n''',
    )
    changed |= replace_exact(
        path,
        '''    years = np.unique(move.year_code)\n    eligible: list[tuple[int, np.ndarray, int]] = []\n    for state, counties in move.state_counties.items():\n        candidates = []\n        for county in counties:\n            rows = np.where(\n                (move.state_code == int(state))\n                & (move.county_code == int(county))\n                & (move.upper > move.lower)\n            )[0]\n            if len(rows) >= 2:\n                candidates.append(int(county))\n        maximum = min(int(max_cycle_half_length), len(candidates), len(years))\n        if maximum >= 3:\n            eligible.append((int(state), np.asarray(candidates, dtype=int), maximum))\n''',
        '''    years = move.years\n    eligible: list[tuple[int, np.ndarray, int]] = []\n    for state, counties in move.cycle_state_counties:\n        maximum = min(int(max_cycle_half_length), len(counties), len(years))\n        if maximum >= 3:\n            eligible.append((int(state), counties, maximum))\n''',
    )
    print("Cycle support cache applied." if changed else "Cycle support cache already present.")


if __name__ == "__main__":
    main()
