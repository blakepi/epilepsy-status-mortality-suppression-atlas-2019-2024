from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.sensitivity import (  # noqa: E402
    FINAL_SOURCE_FILES,
    PROFILE_IDS,
    RUN_ID,
    load_execution_spec,
    verify_hash_inventory,
)


CONFIG_PATH = ROOT / "config" / "sr_v2_heavy_sensitivity_execution.yaml"
PYTHON_SCRIPTS = tuple(ROOT / "scripts" / f"{number}_{name}.py" for number, name in (
    (100, "prepare_sr_v2_heavy_sensitivity"),
    (101, "run_sr_v2_heavy_sensitivity_chain"),
    (102, "merge_sr_v2_heavy_sensitivity"),
    (103, "gate_sr_v2_heavy_sensitivity"),
    (104, "validate_sr_v2_heavy_sensitivity_infrastructure"),
))
HPC_CONTRACTS = {
    "hpc/wahab/stage_sr_v2_heavy_sensitivity_to_scratch.sh": (),
    "hpc/wahab/sync_sr_v2_heavy_sensitivity_results_home.sh": ("--delete",),
    "hpc/wahab/slurm/63_sr_v2_heavy_sensitivity_chain_array.sbatch": ("#SBATCH --array=1-24%6", "#SBATCH --signal=B:USR1@300"),
    "hpc/wahab/slurm/64_sr_v2_finalize_heavy_sensitivity.sbatch": ("afterok",),
    "hpc/wahab/submit_sr_v2_heavy_sensitivity.sh": ("afterok",),
    "hpc/wahab/resume_sr_v2_heavy_sensitivity.sh": (),
    "hpc/wahab/submit_sr_v2_robustness_epoch.sh": ("1-4%2",),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("python", "full"), required=True)
    return parser


def _entrypoint_and_flags(path: Path) -> tuple[bool, set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    has_entrypoint = False
    flags: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            has_name = any(isinstance(child, ast.Name) and child.id == "__name__" for child in ast.walk(node.test))
            has_main = any(isinstance(child, ast.Constant) and child.value == "__main__" for child in ast.walk(node.test))
            has_entrypoint = has_entrypoint or (has_name and has_main)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("--"):
            flags.add(node.value)
    return has_entrypoint, flags


def validate_python() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    spec = load_execution_spec(CONFIG_PATH)
    checks.append({"check": "immutable_run_id", "passed": spec.run_id == RUN_ID, "detail": spec.run_id})
    checks.append({"check": "exact_profile_order", "passed": tuple(profile.profile_id for profile in spec.profiles) == PROFILE_IDS, "detail": str([profile.profile_id for profile in spec.profiles])})
    expected_rows = [(index, profile, chain, chain_seed, init_seed) for index, profile, chain, chain_seed, init_seed in (
        (1, "prior_broader", 1, 68291, 67291), (2, "prior_broader", 2, 68292, 67292), (3, "prior_broader", 3, 68293, 67293), (4, "prior_broader", 4, 68294, 67294),
        (5, "prior_regularizing", 1, 69291, 67391), (6, "prior_regularizing", 2, 69292, 67392), (7, "prior_regularizing", 3, 69293, 67393), (8, "prior_regularizing", 4, 69294, 67394),
        (9, "model_family_poisson", 1, 70291, 70251), (10, "model_family_poisson", 2, 70292, 70252), (11, "model_family_poisson", 3, 70293, 70253), (12, "model_family_poisson", 4, 70294, 70254),
        (13, "pandemic_interaction", 1, 71291, 71251), (14, "pandemic_interaction", 2, 71292, 71252), (15, "pandemic_interaction", 3, 71293, 71253), (16, "pandemic_interaction", 4, 71294, 71254),
        (17, "pandemic_exclusion", 1, 72291, 72251), (18, "pandemic_exclusion", 2, 72292, 72252), (19, "pandemic_exclusion", 3, 72293, 72253), (20, "pandemic_exclusion", 4, 72294, 72254),
        (21, "age_structure_age17", 1, 73291, 73251), (22, "age_structure_age17", 2, 73292, 73252), (23, "age_structure_age17", 3, 73293, 73253), (24, "age_structure_age17", 4, 73294, 73254),
    )]
    actual_rows = [(row.array_index, row.profile_id, row.chain_id, row.chain_seed, row.initialization_seed) for row in spec.chain_map]
    checks.append({"check": "exact_24_row_map", "passed": actual_rows == expected_rows, "detail": f"rows={len(actual_rows)}"})
    try:
        verify_hash_inventory(ROOT, spec.source_authorities)
        hashes_ok, hash_detail = True, f"authorities={len(spec.source_authorities)}"
    except Exception as exc:
        hashes_ok, hash_detail = False, str(exc)
    checks.append({"check": "frozen_hashes", "passed": hashes_ok, "detail": hash_detail})
    checks.append({
        "check": "final_source_manifest_contract",
        "passed": tuple(spec.final_source_files) == FINAL_SOURCE_FILES,
        "detail": f"required_sources={len(spec.final_source_files)} union_superset_allowed=true external_launch_envelope_required=true preparation_ready=false",
    })
    all_entrypoints = True
    runner_flags: set[str] = set()
    for path in PYTHON_SCRIPTS:
        if not path.is_file():
            all_entrypoints = False
            continue
        entrypoint, flags = _entrypoint_and_flags(path)
        all_entrypoints = all_entrypoints and entrypoint
        if path.name.startswith("101_"):
            runner_flags = flags
    checks.append({"check": "ast_entrypoints", "passed": all_entrypoints, "detail": f"scripts={len(PYTHON_SCRIPTS)}"})
    checks.append({"check": "runner_cli_exact", "passed": runner_flags == {"--run-id", "--array-index"}, "detail": f"flags={sorted(runner_flags)}"})
    prepare_flags = _entrypoint_and_flags(PYTHON_SCRIPTS[0])[1]
    checks.append({"check": "no_prepare_overwrite_flag", "passed": not ({"--force", "--overwrite"} & prepare_flags), "detail": f"flags={sorted(prepare_flags)}"})
    module_source = (ROOT / "src" / "bayes_constrained" / "sensitivity.py").read_text(encoding="utf-8")
    prepare_source = PYTHON_SCRIPTS[0].read_text(encoding="utf-8")
    runner_source = PYTHON_SCRIPTS[1].read_text(encoding="utf-8")
    exclusive_publish = all(token in module_source for token in ("target.mkdir()", "os.path.lexists(target)", "ordered.append(marker)"))
    marker_last = "commit_marker=\"prepared_run_manifest.json.sha256\"" in prepare_source
    checks.append({"check": "atomic_exclusive_publish", "passed": "open(\"x\"" in module_source and exclusive_publish and marker_last, "detail": "exclusive mkdir reservation and manifest-sidecar-last commit"})
    checks.append({"check": "resume_fingerprint_guards", "passed": "profile_fingerprint" in runner_source and "completed_chain_is_reusable" in runner_source and "latest_checkpoint_sha256" in runner_source, "detail": "manifest, fingerprint, checkpoint, artifact guards present"})
    return checks


def validate_full() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for relative, required in HPC_CONTRACTS.items():
        path = ROOT / relative
        if not path.is_file():
            checks.append({"check": f"hpc:{relative}", "passed": False, "detail": "Task 5 contract not present"})
            continue
        source = path.read_text(encoding="utf-8")
        passed = all((token not in source if token == "--delete" else token in source) for token in required)
        checks.append({"check": f"hpc:{relative}", "passed": passed, "detail": f"tokens={required}"})
    return checks


def main() -> None:
    args = build_parser().parse_args()
    checks = validate_python()
    if args.scope == "full":
        checks.extend(validate_full())
    payload = {"scope": args.scope, "passed": all(bool(row["passed"]) for row in checks), "checks": checks}
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
