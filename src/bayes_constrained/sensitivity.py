from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from .data import augment_age17_covariate, make_pandemic_exclusion_frame
from .model import PRIMARY_TERMS, make_design, normalize_likelihood_family


RUN_ID = "sr-v2-heavy-sensitivity-20260818-v1"
OUTPUT_ROOT = "outputs/scientific_reports_v2/heavy_sensitivity"
REPOSITORY_BASE_COMMIT = "123904015805758119d8cc9d88c6bb94efbc36e1"
PROFILE_IDS = (
    "prior_broader",
    "prior_regularizing",
    "model_family_poisson",
    "pandemic_interaction",
    "pandemic_exclusion",
    "age_structure_age17",
)
RURALITY_TERMS = (
    "primary_rurality_metro_other",
    "primary_rurality_nonmetro_adjacent",
    "primary_rurality_nonmetro_nonadjacent",
)
EXPECTED_INTERACTION_TERMS = tuple(
    f"{term}__x__{period}"
    for period in ("acute_pandemic", "later_period")
    for term in RURALITY_TERMS
)
EXPECTED_FULL_YEARS = ("2019", "2020", "2021", "2022", "2023", "2024")
EXPECTED_EXCLUSION_YEARS = ("2019", "2022", "2023", "2024")
EXPECTED_TARGETS = (
    ("prior_broader", "negative_binomial_2", "primary", "full", "broader"),
    ("prior_regularizing", "negative_binomial_2", "primary", "full", "regularizing"),
    ("model_family_poisson", "poisson", "primary", "full", "default"),
    ("pandemic_interaction", "negative_binomial_2", "pandemic_interaction", "full", "default"),
    ("pandemic_exclusion", "negative_binomial_2", "primary", "pandemic_exclusion", "default"),
    ("age_structure_age17", "negative_binomial_2", "age_structure_age17", "age17_augmented", "default"),
)
EXPECTED_CHAIN_MAP = tuple(
    (index, profile, chain, chain_seed, init_seed)
    for index, profile, chain, chain_seed, init_seed in (
        (1, "prior_broader", 1, 68291, 67291), (2, "prior_broader", 2, 68292, 67292), (3, "prior_broader", 3, 68293, 67293), (4, "prior_broader", 4, 68294, 67294),
        (5, "prior_regularizing", 1, 69291, 67391), (6, "prior_regularizing", 2, 69292, 67392), (7, "prior_regularizing", 3, 69293, 67393), (8, "prior_regularizing", 4, 69294, 67394),
        (9, "model_family_poisson", 1, 70291, 70251), (10, "model_family_poisson", 2, 70292, 70252), (11, "model_family_poisson", 3, 70293, 70253), (12, "model_family_poisson", 4, 70294, 70254),
        (13, "pandemic_interaction", 1, 71291, 71251), (14, "pandemic_interaction", 2, 71292, 71252), (15, "pandemic_interaction", 3, 71293, 71253), (16, "pandemic_interaction", 4, 71294, 71254),
        (17, "pandemic_exclusion", 1, 72291, 72251), (18, "pandemic_exclusion", 2, 72292, 72252), (19, "pandemic_exclusion", 3, 72293, 72253), (20, "pandemic_exclusion", 4, 72294, 72254),
        (21, "age_structure_age17", 1, 73291, 73251), (22, "age_structure_age17", 2, 73292, 73252), (23, "age_structure_age17", 3, 73293, 73253), (24, "age_structure_age17", 4, 73294, 73254),
    )
)
EXPECTED_THRESHOLDS = {
    "rhat_max_all": 1.05,
    "ess_bulk_min_all": 100,
    "ess_tail_min_all": 100,
    "rhat_max_primary": 1.03,
    "ess_bulk_min_primary": 400,
    "ess_tail_min_primary": 400,
    "constraint_failures_allowed": 0,
}
EXPECTED_COMPARISON = {
    "primary_parameters": list(PRIMARY_TERMS),
    "interaction_periods": ["pre_pandemic_2019", "acute_pandemic_2020_2021", "later_period_2022_2024"],
}
EXPECTED_PROTECTED_TREES = (
    "outputs/scientific_reports_v2/production_8chain",
    "outputs/scientific_reports_v2/spatial_residual_diagnostics",
)
EXPECTED_SOURCE_AUTHORITIES = {
    "config/scientific_reports_v2_robustness_registry.yaml": "072e039b78af11a0bb4d6532bb8fb09f70b81d825a38faa3cf89670ca7843814",
    "outputs/scientific_reports_v2/production_8chain/production_gate.json": "38be94b401138864cf6e4cb030f2bd53e9b8ad6ea24e080e0353824124784437",
    "outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv": "2842efa4c95b018aed3626b58b33e42792c0348655225c3a89ec58b4109452e6",
    "outputs/scientific_reports_v2/production_8chain/config/sr_v2_production.yaml": "b475ddc4547680c085b172244b567a01c59dc2920da95910ac0eecfff172a393",
    "data/processed/bayes_constrained/model_frame.parquet": "2f20555f4b690e1a495e2409dbb2f9bb128a6d3f7b0bb39f4017034aaf2a9e44",
    "data/raw/covariates/SVI_2022_US_county.csv": "bc47d244153e359d5c09f621a4bf344a1e593159c16fbd3c28a15461b70a6c0f",
}
EXPECTED_EXECUTION = {
    "chains_per_profile": 4,
    "iterations_per_chain": 180000,
    "burn_in": 45000,
    "thin": 30,
    "retained_draws_per_chain": 4500,
    "checkpoint_every": 500,
    "max_runtime_minutes": 4260,
    "stop_before_time_limit_minutes": 15,
}
EXPECTED_INTERPRETATION_BOUNDARY = (
    "Computational PASS supplements the frozen corrected primary evidence. It does not replace the primary "
    "estimand or authorize manuscript edits, repository publication, or submission."
)
FINAL_SOURCE_FILES = (
    "src/bayes_constrained/__init__.py",
    "src/bayes_constrained/paths.py",
    "src/bayes_constrained/data.py",
    "src/bayes_constrained/constraints.py",
    "src/bayes_constrained/target_density.py",
    "src/bayes_constrained/model.py",
    "src/bayes_constrained/heatbath.py",
    "src/bayes_constrained/interval_paths.py",
    "src/bayes_constrained/sampler.py",
    "src/bayes_constrained/diagnostics.py",
    "src/bayes_constrained/sensitivity.py",
    "scripts/100_prepare_sr_v2_heavy_sensitivity.py",
    "scripts/101_run_sr_v2_heavy_sensitivity_chain.py",
    "scripts/102_merge_sr_v2_heavy_sensitivity.py",
    "scripts/103_gate_sr_v2_heavy_sensitivity.py",
    "scripts/104_validate_sr_v2_heavy_sensitivity_infrastructure.py",
)


@dataclass(frozen=True)
class SensitivityProfile:
    profile_id: str
    likelihood: str
    model: str
    frame: str
    prior: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.profile_id,
            "likelihood": self.likelihood,
            "model": self.model,
            "frame": self.frame,
            "prior": self.prior,
        }


@dataclass(frozen=True)
class ChainAssignment:
    array_index: int
    profile_id: str
    chain_id: int
    chain_seed: int
    initialization_seed: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "array_index": self.array_index,
            "profile": self.profile_id,
            "chain": self.chain_id,
            "chain_seed": self.chain_seed,
            "initialization_seed": self.initialization_seed,
        }


@dataclass(frozen=True)
class ExecutionSpec:
    path: Path
    schema_id: str
    run_id: str
    repository_base_commit: str
    output_root: str
    iterations_per_chain: int
    burn_in: int
    thin: int
    retained_draws_per_chain: int
    checkpoint_every: int
    max_runtime_minutes: int
    stop_before_time_limit_minutes: int
    thresholds: dict[str, float | int]
    profiles: tuple[SensitivityProfile, ...]
    chain_map: tuple[ChainAssignment, ...]
    source_authorities: dict[str, str]
    final_source_files: tuple[str, ...]
    launch_envelope_schema: str
    comparison: dict[str, Any]
    interpretation_boundary: str
    raw: dict[str, Any]

    def profile(self, profile_id: str) -> SensitivityProfile:
        matches = [profile for profile in self.profiles if profile.profile_id == profile_id]
        if len(matches) != 1:
            raise ValueError(f"Unknown sensitivity profile {profile_id!r}")
        return matches[0]

    def assignment(self, array_index: int) -> ChainAssignment:
        matches = [row for row in self.chain_map if row.array_index == int(array_index)]
        if len(matches) != 1:
            raise ValueError(f"Array index must identify exactly one chain: {array_index}")
        return matches[0]


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_canonical_text(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    payload = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_manifest_sidecar(manifest_path: str | Path) -> str:
    path = Path(manifest_path)
    sidecar = path.with_name(f"{path.name}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise ValueError(f"Manifest or SHA-256 sidecar is missing: {path}")
    expected = sidecar.read_text(encoding="ascii").strip().lower()
    actual = sha256_file(path)
    if expected != actual:
        raise ValueError(f"Manifest SHA-256 mismatch: expected {expected}, found {actual}")
    return actual


def atomic_json(path: str | Path, payload: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def _require_sha256_mapping(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{label} must be a nonempty path-to-SHA-256 mapping")
    result = {str(key): str(item).lower() for key, item in value.items()}
    invalid = {key: item for key, item in result.items() if len(item) != 64 or any(c not in "0123456789abcdef" for c in item)}
    if invalid:
        raise ValueError(f"{label} contains invalid SHA-256 values: {sorted(invalid)}")
    return result


def load_execution_spec(path: str | Path) -> ExecutionSpec:
    config_path = Path(path).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Heavy-sensitivity execution config must be a mapping")
    execution = raw.get("execution", {})
    profiles = tuple(
        SensitivityProfile(
            profile_id=str(row["id"]),
            likelihood=str(row["likelihood"]),
            model=str(row["model"]),
            frame=str(row["frame"]),
            prior=str(row["prior"]),
        )
        for row in raw.get("profiles", [])
    )
    chain_map = tuple(
        ChainAssignment(
            array_index=int(row["array_index"]),
            profile_id=str(row["profile"]),
            chain_id=int(row["chain"]),
            chain_seed=int(row["chain_seed"]),
            initialization_seed=int(row["initialization_seed"]),
        )
        for row in raw.get("chain_map", [])
    )
    spec = ExecutionSpec(
        path=config_path,
        schema_id=str(raw.get("schema_id", "")),
        run_id=str(raw.get("run_id", "")),
        repository_base_commit=str(raw.get("repository_base_commit", "")),
        output_root=str(raw.get("output_root", "")),
        iterations_per_chain=int(execution.get("iterations_per_chain", 0)),
        burn_in=int(execution.get("burn_in", 0)),
        thin=int(execution.get("thin", 0)),
        retained_draws_per_chain=int(execution.get("retained_draws_per_chain", 0)),
        checkpoint_every=int(execution.get("checkpoint_every", 0)),
        max_runtime_minutes=int(execution.get("max_runtime_minutes", 0)),
        stop_before_time_limit_minutes=int(execution.get("stop_before_time_limit_minutes", 0)),
        thresholds={str(key): value for key, value in raw.get("thresholds", {}).items()},
        profiles=profiles,
        chain_map=chain_map,
        source_authorities=_require_sha256_mapping(raw.get("source_authorities"), "source_authorities"),
        final_source_files=tuple(map(str, raw.get("final_source_manifest", {}).get("required_sources", []))),
        launch_envelope_schema=str(raw.get("launch_envelope", {}).get("schema_id", "")),
        comparison=dict(raw.get("comparison", {})),
        interpretation_boundary=str(raw.get("interpretation_boundary", "")),
        raw=raw,
    )
    _validate_spec(spec)
    return spec


def _validate_spec(spec: ExecutionSpec) -> None:
    expected_top_keys = {
        "schema_id", "run_id", "repository_base_commit", "output_root", "source_authorities",
        "final_source_manifest", "launch_envelope", "execution", "thresholds", "profiles", "chain_map", "comparison",
        "interpretation_boundary", "protected_trees",
    }
    if set(spec.raw) != expected_top_keys:
        raise ValueError("Heavy-sensitivity config top-level keys differ from the frozen contract")
    if spec.schema_id != "sr_v2_heavy_sensitivity_execution/v1" or spec.run_id != RUN_ID:
        raise ValueError("Unexpected heavy-sensitivity schema or immutable run id")
    actual_targets = tuple((p.profile_id, p.likelihood, p.model, p.frame, p.prior) for p in spec.profiles)
    if actual_targets != EXPECTED_TARGETS:
        raise ValueError("Sensitivity target contract differs from the frozen six-profile contract")
    actual_map = tuple((r.array_index, r.profile_id, r.chain_id, r.chain_seed, r.initialization_seed) for r in spec.chain_map)
    if actual_map != EXPECTED_CHAIN_MAP:
        raise ValueError("Heavy-sensitivity chain map or seeds differ from the frozen chain map")
    if spec.repository_base_commit != REPOSITORY_BASE_COMMIT:
        raise ValueError("Repository base commit differs from the frozen contract")
    if spec.output_root != OUTPUT_ROOT:
        raise ValueError("Heavy-sensitivity output root differs from the frozen output root")
    if spec.thresholds != EXPECTED_THRESHOLDS:
        raise ValueError("Heavy-sensitivity threshold contract changed")
    if spec.comparison != EXPECTED_COMPARISON:
        raise ValueError("Heavy-sensitivity comparison rows changed")
    if spec.source_authorities != EXPECTED_SOURCE_AUTHORITIES:
        raise ValueError("Heavy-sensitivity source-authority contract changed")
    if spec.raw.get("execution") != EXPECTED_EXECUTION:
        raise ValueError("Heavy-sensitivity execution controls changed")
    if spec.interpretation_boundary != EXPECTED_INTERPRETATION_BOUNDARY:
        raise ValueError("Heavy-sensitivity interpretation boundary changed")
    if tuple(map(str, spec.raw.get("protected_trees", []))) != EXPECTED_PROTECTED_TREES:
        raise ValueError("Heavy-sensitivity protected trees changed")
    final_contract = spec.raw.get("final_source_manifest", {})
    if (
        final_contract.get("schema_id") != "sr_v2_robustness_final_source_manifest/v1"
        or final_contract.get("required_status") != "reviewed_final"
        or final_contract.get("source_hash_mode") != "raw_bytes"
        or spec.final_source_files != FINAL_SOURCE_FILES
    ):
        raise ValueError("Final source manifest contract changed")
    if spec.raw.get("launch_envelope") != {
        "schema_id": "sr_v2_robustness_launch_envelope/v1",
        "required_status": "reviewed_final",
        "requires_clean_worktree": True,
    }:
        raise ValueError("Reviewed launch-envelope contract changed")
    if (spec.iterations_per_chain, spec.burn_in, spec.thin, spec.retained_draws_per_chain) != (180000, 45000, 30, 4500):
        raise ValueError("Heavy-sensitivity iteration contract changed")
    if (spec.iterations_per_chain - spec.burn_in) // spec.thin != spec.retained_draws_per_chain:
        raise ValueError("Retained draw count is inconsistent with iteration settings")


def verify_hash_inventory(
    root: str | Path,
    inventory: Mapping[str, str],
    *,
    canonical_text: bool = False,
) -> dict[str, str]:
    base = Path(root).resolve()
    verified: dict[str, str] = {}
    for relative, expected in inventory.items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError(f"Required hashed input is missing or escapes root: {relative}")
        actual = sha256_canonical_text(path) if canonical_text else sha256_file(path)
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {relative}: expected {expected}, found {actual}")
        verified[str(relative)] = actual
    return verified


def safe_relative_path(root: str | Path, relative: str | Path, *, must_exist: bool = False) -> Path:
    base = Path(root).resolve()
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or candidate == Path("."):
        raise ValueError(f"Manifest path must be a nonempty relative path: {relative}")
    resolved = (base / candidate).resolve(strict=False)
    if not resolved.is_relative_to(base):
        raise ValueError(f"Manifest path escapes declared root: {relative}")
    if must_exist and not resolved.exists():
        raise ValueError(f"Manifest path does not exist: {relative}")
    return resolved


def load_final_source_manifest(
    root: str | Path,
    spec: ExecutionSpec,
    envelope_path: str | Path,
) -> dict[str, Any]:
    base = Path(root).resolve()
    path = Path(envelope_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Reviewed external launch envelope is required before preparation: {path}")
    envelope_hash = verify_manifest_sidecar(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    envelope_required = {
        "schema_id": "sr_v2_robustness_launch_envelope/v1",
        "status": "reviewed_final",
        "clean_worktree": True,
    }
    envelope_changed = {key: (value, payload.get(key)) for key, value in envelope_required.items() if payload.get(key) != value}
    if envelope_changed:
        raise ValueError(f"Reviewed launch envelope contract mismatch: {envelope_changed}")
    source_manifest = payload.get("source_manifest")
    if not isinstance(source_manifest, dict):
        raise ValueError("Launch envelope does not contain the reviewed final source manifest")
    required = {
        "schema_id": "sr_v2_robustness_final_source_manifest/v1",
        "status": "reviewed_final",
        "joint_regression_passed": True,
        "source_hash_mode": "raw_bytes",
    }
    changed = {key: (value, source_manifest.get(key)) for key, value in required.items() if source_manifest.get(key) != value}
    if changed:
        raise ValueError(f"Final source manifest contract mismatch: {changed}")
    manifest_hash = canonical_sha256(source_manifest)
    if payload.get("source_manifest_sha256") != manifest_hash:
        raise ValueError("Launch envelope final-source-manifest SHA-256 mismatch")
    launch_commit = str(payload.get("launch_commit", ""))
    bundle_hash = str(payload.get("bundle_sha256", ""))
    if len(launch_commit) != 40 or any(c not in "0123456789abcdef" for c in launch_commit.lower()):
        raise ValueError("Final source manifest launch commit is invalid")
    if len(bundle_hash) != 64 or any(c not in "0123456789abcdef" for c in bundle_hash.lower()):
        raise ValueError("Final source manifest bundle SHA-256 is invalid")
    sources = _require_sha256_mapping(source_manifest.get("sources"), "final source manifest sources")
    if not set(spec.final_source_files).issubset(sources):
        raise ValueError("Final source manifest omits executable sources required by the heavy workflow")
    for relative, expected in sources.items():
        source_path = safe_relative_path(base, relative, must_exist=True)
        actual = sha256_file(source_path)
        if actual != expected:
            raise ValueError(f"Final source SHA-256 mismatch for {relative}: expected {expected}, found {actual}")
    evidence_relative = str(source_manifest.get("joint_regression_evidence", ""))
    evidence_path = safe_relative_path(base, evidence_relative, must_exist=True)
    evidence_hash = str(source_manifest.get("joint_regression_evidence_sha256", ""))
    if sha256_file(evidence_path) != evidence_hash:
        raise ValueError("Final source manifest joint-regression evidence SHA-256 mismatch")
    return {
        **source_manifest,
        "manifest_sha256": manifest_hash,
        "envelope_path": str(path),
        "envelope_sha256": envelope_hash,
        "launch_commit": launch_commit,
        "bundle_sha256": bundle_hash,
    }


@contextmanager
def acquire_prepare_lock(path: str | Path):
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = lock_path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise FileExistsError(f"Exclusive preparation lock already exists: {lock_path}") from exc
    try:
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        os.fsync(handle.fileno())
        yield lock_path
    finally:
        handle.close()
        lock_path.unlink(missing_ok=True)


def publish_directory_no_clobber(
    staging: str | Path,
    destination: str | Path,
    *,
    before_commit: Callable[[], None] | None = None,
    commit_marker: str | None = None,
) -> None:
    source = Path(staging)
    target = Path(destination)
    if os.path.lexists(target):
        raise FileExistsError(f"Destination exists; refusing to replace conflicting run: {target}")
    entries = list(source.iterdir())
    marker = source / commit_marker if commit_marker is not None else None
    if marker is not None and marker not in entries:
        raise ValueError(f"Publication commit marker is missing from staging: {commit_marker}")
    if before_commit is not None:
        before_commit()
    try:
        target.mkdir()
    except FileExistsError as exc:
        raise FileExistsError(f"Destination exists; refusing to replace conflicting run: {target}") from exc
    ordered = [entry for entry in entries if entry != marker]
    if marker is not None:
        ordered.append(marker)
    for entry in ordered:
        os.rename(entry, target / entry.name)
    source.rmdir()


def load_declared_checkpoint(
    checkpoint_dir: str | Path,
    declared_name: str,
    *,
    expected_target_identity: Mapping[str, object],
    expected_likelihood_family: str,
) -> dict[str, object]:
    from .sampler import load_chain_checkpoint

    root = Path(checkpoint_dir).resolve()
    declared = safe_relative_path(root, declared_name, must_exist=True)
    files = [path for path in root.iterdir() if path.is_file()]
    checkpoints: list[tuple[int, Path]] = []
    for path in files:
        match = re.fullmatch(r"checkpoint_iter_(\d+)\.npz", path.name)
        if match:
            checkpoints.append((int(match.group(1)), path))
            if not path.with_name(f"{path.name}.sha256").is_file():
                raise ValueError(f"Checkpoint SHA-256 sidecar is missing: {path.name}")
        elif path.name.endswith(".npz.sha256"):
            checkpoint = path.with_name(path.name.removesuffix(".sha256"))
            if not checkpoint.is_file():
                raise ValueError(f"Orphan checkpoint SHA-256 sidecar: {path.name}")
        else:
            raise ValueError(f"Unexpected checkpoint artifact: {path.name}")
    checkpoints.sort(key=lambda row: row[0])
    if not checkpoints or checkpoints[-1][1] != declared:
        raise ValueError("A newer or different checkpoint exists than the status-declared checkpoint")
    family = normalize_likelihood_family(expected_likelihood_family)
    identity_family = normalize_likelihood_family(str(expected_target_identity.get("likelihood", "")))
    if family != identity_family:
        raise ValueError(
            f"Declared expected family differs from target identity likelihood: {family!r} != {identity_family!r}"
        )
    return load_chain_checkpoint(
        declared,
        expected_likelihood_family=family,
        expected_target_identity=dict(expected_target_identity),
    )


def build_sensitivity_frame(
    source_frame: pd.DataFrame,
    profile: SensitivityProfile,
    *,
    svi_path: str | Path,
) -> pd.DataFrame:
    if profile.frame == "full":
        frame = source_frame.copy(deep=True)
        frame.attrs = dict(source_frame.attrs)
    elif profile.frame == "pandemic_exclusion":
        frame = make_pandemic_exclusion_frame(source_frame)
    elif profile.frame == "age17_augmented":
        frame = augment_age17_covariate(source_frame, svi_path)
    else:
        raise ValueError(f"Unknown sensitivity frame contract: {profile.frame!r}")
    frame.attrs["included_years"] = sorted(frame["year"].astype(str).unique())
    return frame


def expected_parameter_schema(frame: pd.DataFrame, profile: SensitivityProfile) -> list[str]:
    design = make_design(frame, model=profile.model, likelihood_family=profile.likelihood)
    schema = list(design.columns)
    schema.extend(f"state_effect[{state}]" for state in design.states)
    schema.extend(f"year_effect[{year}]" for year in design.years)
    schema.extend(("sigma_state", "sigma_year"))
    if profile.likelihood == "negative_binomial_2":
        schema.append("kappa")
    return schema


def checkpoint_target_identity(
    *,
    spec: ExecutionSpec,
    profile: SensitivityProfile,
    assignment: ChainAssignment,
    profile_fingerprint_value: str,
    operational_config_sha256: str,
    profile_config_sha256: str,
    frame_sha256: str,
    final_source_manifest_sha256: str,
    parameter_schema: Sequence[str],
) -> dict[str, object]:
    return {
        "schema_id": "sr_v2_heavy_checkpoint_target/v1",
        "run_id": spec.run_id,
        "profile": profile.profile_id,
        "profile_fingerprint": profile_fingerprint_value,
        "model": profile.model,
        "likelihood": profile.likelihood,
        "frame": profile.frame,
        "prior": profile.prior,
        "operational_config_sha256": operational_config_sha256,
        "profile_config_sha256": profile_config_sha256,
        "frame_sha256": frame_sha256,
        "final_source_manifest_sha256": final_source_manifest_sha256,
        "parameter_schema_sha256": canonical_sha256(list(parameter_schema)),
        "array_index": assignment.array_index,
        "chain_id": assignment.chain_id,
        "chain_seed": assignment.chain_seed,
        "initialization_seed": assignment.initialization_seed,
    }


def validate_chain_draws(
    draws: pd.DataFrame,
    *,
    chain_id: int,
    parameter_schema: Sequence[str],
    retained_draws: int,
    burn_in: int,
    thin: int,
) -> None:
    expected_columns = ["chain", "draw", "iteration", "parameter", "value"]
    if list(draws.columns) != expected_columns:
        raise ValueError(f"Unexpected parameter-draw columns: {list(draws.columns)}")
    expected_rows = len(parameter_schema) * retained_draws
    if len(draws) != expected_rows:
        raise ValueError(f"Parameter draw row count mismatch: expected {expected_rows}, found {len(draws)}")
    labels: dict[str, np.ndarray] = {}
    for column in ("chain", "draw", "iteration"):
        try:
            values = pd.to_numeric(draws[column], errors="raise").to_numpy(dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Parameter draw {column} labels must be finite integral values") from exc
        if not np.isfinite(values).all() or not np.equal(values, np.rint(values)).all():
            raise ValueError(f"Parameter draw {column} labels must be finite integral values")
        labels[column] = values.astype(np.int64)
    if draws.duplicated(["chain", "draw", "parameter"]).any():
        raise ValueError("Duplicate (chain, draw, parameter) rows")
    if set(labels["chain"].tolist()) != {int(chain_id)}:
        raise ValueError("Parameter draw chain label does not match declared chain")
    if not np.isfinite(pd.to_numeric(draws["value"], errors="coerce").to_numpy(dtype=float)).all():
        raise ValueError("Parameter draws contain nonfinite values")
    expected_draw_ids = list(range(1, retained_draws + 1))
    expected_iterations = {draw: burn_in + draw * thin for draw in expected_draw_ids}
    for parameter in parameter_schema:
        mask = draws["parameter"].astype(str).eq(parameter).to_numpy()
        order = np.argsort(labels["draw"][mask], kind="stable")
        actual_draws = labels["draw"][mask][order].tolist()
        if actual_draws != expected_draw_ids:
            raise ValueError(f"Parameter {parameter} does not have the exact draw-id grid")
        actual_iterations = labels["iteration"][mask][order].tolist()
        wanted_iterations = [expected_iterations[draw] for draw in expected_draw_ids]
        if actual_iterations != wanted_iterations:
            raise ValueError(f"Parameter {parameter} violates the retained iteration schedule")
    if draws["parameter"].drop_duplicates().astype(str).tolist() != list(parameter_schema):
        raise ValueError("Parameter draw schema/order mismatch")


def validate_diagnostics_table(
    diagnostics: pd.DataFrame,
    *,
    parameter_schema: Sequence[str],
    chains: int = 4,
    draws_per_chain: int = 4500,
) -> None:
    required = {"parameter", "r_hat", "ess_bulk", "ess_tail", "chains", "draws_per_chain", "draws"}
    if not required <= set(diagnostics.columns) or len(diagnostics) != len(parameter_schema):
        raise ValueError("Diagnostic row count/columns do not match the exact parameter schema")
    if diagnostics["parameter"].astype(str).duplicated().any() or sorted(diagnostics["parameter"].astype(str)) != sorted(parameter_schema):
        raise ValueError("Diagnostic parameter cardinality differs from the exact schema")
    metadata_ok = (
        diagnostics["chains"].eq(chains).all()
        and diagnostics["draws_per_chain"].eq(draws_per_chain).all()
        and diagnostics["draws"].eq(chains * draws_per_chain).all()
    )
    if not metadata_ok:
        raise ValueError("Diagnostic chains/draws metadata is not the exact 4x4500 grid")
    numeric = diagnostics[["r_hat", "ess_bulk", "ess_tail"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("Diagnostics contain nonfinite values")


def expected_comparison_keys(profile_id: str) -> set[tuple[str, str]]:
    if profile_id == "pandemic_interaction":
        keys = {(term, period) for term in RURALITY_TERMS for period in EXPECTED_COMPARISON["interaction_periods"]}
        keys.update((term, "modeled_period") for term in PRIMARY_TERMS if term not in RURALITY_TERMS)
        return keys
    return {(term, "modeled_period") for term in PRIMARY_TERMS}


def validate_comparison_table(comparisons: pd.DataFrame, *, profile_id: str) -> None:
    required = {"profile", "parameter", "period", "sensitivity_median", "sensitivity_lower_95", "sensitivity_upper_95", "primary_median", "primary_lower_95", "primary_upper_95"}
    if not required <= set(comparisons.columns):
        raise ValueError("Comparison key/value columns are incomplete")
    if set(comparisons["profile"].astype(str)) != {profile_id}:
        raise ValueError("Comparison profile label mismatch")
    if comparisons.duplicated(["parameter", "period"]).any():
        raise ValueError("Comparison key rows are duplicated")
    actual = set(zip(comparisons["parameter"].astype(str), comparisons["period"].astype(str), strict=True))
    if actual != expected_comparison_keys(profile_id):
        raise ValueError(f"Comparison key schema mismatch for {profile_id}")
    numeric_columns = [column for column in required if column not in {"profile", "parameter", "period"}]
    if not np.isfinite(comparisons[numeric_columns].to_numpy(dtype=float)).all():
        raise ValueError("Comparison table contains nonfinite values")


def profile_fingerprint(
    profile: SensitivityProfile,
    assignment: ChainAssignment,
    *,
    run_id: str,
    included_years: Sequence[str],
    execution: Mapping[str, object],
    config_sha256: str,
    input_hashes: Mapping[str, str],
    source_hashes: Mapping[str, str],
    parameter_schema: Sequence[str],
    launch_provenance: Mapping[str, str] | None = None,
) -> str:
    payload = {
        "schema_id": "sr_v2_heavy_sensitivity_target_fingerprint/v1",
        "run_id": run_id,
        "profile": profile.to_dict(),
        "assignment": assignment.to_dict(),
        "included_years": list(map(str, included_years)),
        "execution": dict(execution),
        "operational_config_sha256": config_sha256,
        "input_hashes": dict(sorted(input_hashes.items())),
        "source_hashes": dict(sorted(source_hashes.items())),
        "launch_provenance": dict(sorted((launch_provenance or {}).items())),
        "parameter_schema": list(map(str, parameter_schema)),
    }
    return canonical_sha256(payload)


def preparation_identity(
    spec: ExecutionSpec,
    *,
    config_sha256: str,
    final_source_manifest: Mapping[str, object],
) -> str:
    return canonical_sha256(
        {
            "schema_id": "sr_v2_heavy_sensitivity_preparation_identity/v1",
            "run_id": spec.run_id,
            "repository_base_commit": spec.repository_base_commit,
            "operational_config_sha256": config_sha256,
            "source_authorities": spec.source_authorities,
            "final_source_manifest_sha256": final_source_manifest["manifest_sha256"],
            "launch_envelope_sha256": final_source_manifest["envelope_sha256"],
            "launch_commit": final_source_manifest["launch_commit"],
            "bundle_sha256": final_source_manifest["bundle_sha256"],
            "joint_regression_evidence_sha256": final_source_manifest["joint_regression_evidence_sha256"],
            "profiles": [profile.to_dict() for profile in spec.profiles],
            "chain_map": [row.to_dict() for row in spec.chain_map],
        }
    )


def assert_manifest_matches(expected: Mapping[str, object], actual: Mapping[str, object]) -> None:
    identity_fields = (
        "schema_id", "run_id", "preparation_identity", "operational_config_sha256",
        "final_source_manifest_sha256", "launch_envelope_sha256", "launch_commit", "bundle_sha256",
    )
    differences = [field for field in identity_fields if expected.get(field) != actual.get(field)]
    if differences:
        raise ValueError(
            "Existing run does not match the immutable preparation manifest; "
            f"changed fields: {differences}"
        )


def _safe_artifact_path(chain_dir: Path, relative: str) -> Path:
    root = chain_dir.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Chain artifact is missing or escapes chain root: {relative}")
    return path


def completed_chain_is_reusable(
    chain_dir: str | Path,
    status: Mapping[str, object],
    *,
    run_id: str,
    array_index: int,
    fingerprint: str,
    expected_draws: int,
    required_artifacts: Sequence[str] | None = None,
    expected_parameter_schema: Sequence[str] | None = None,
    expected_years: Sequence[str] | None = None,
    expected_terminal_iteration: int | None = None,
    target_identity: Mapping[str, object] | None = None,
) -> bool:
    if status.get("status") != "completed":
        return False
    expected = {
        "run_id": run_id,
        "array_index": int(array_index),
        "profile_fingerprint": fingerprint,
        "saved_draws": int(expected_draws),
    }
    changed = {key: (expected_value, status.get(key)) for key, expected_value in expected.items() if status.get(key) != expected_value}
    if changed:
        raise ValueError(f"Completed chain identity mismatch: {changed}")
    if expected_parameter_schema is not None and list(status.get("parameter_schema", [])) != list(expected_parameter_schema):
        raise ValueError("Completed chain parameter schema does not match its target")
    if expected_years is not None and list(map(str, status.get("included_years", []))) != list(map(str, expected_years)):
        raise ValueError("Completed chain included-year contract does not match its target")
    inventory = status.get("artifact_sha256")
    if not isinstance(inventory, Mapping) or not inventory:
        raise ValueError("Completed chain has no artifact SHA-256 inventory")
    if required_artifacts is not None and set(map(str, inventory)) != set(map(str, required_artifacts)):
        raise ValueError("Completed chain artifact inventory is incomplete or contains unexpected paths")
    root = Path(chain_dir)
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "chain_status.json"
    }
    if actual_files != set(map(str, inventory)):
        raise ValueError(
            f"Completed chain contains orphan/missing files: actual={sorted(actual_files)} declared={sorted(inventory)}"
        )
    for relative, expected_hash in inventory.items():
        actual = sha256_file(_safe_artifact_path(root, str(relative)))
        if actual != expected_hash:
            raise ValueError(
                f"Artifact SHA-256 mismatch for {relative}: expected {expected_hash}, found {actual}"
            )
    declared_checkpoint = str(status.get("latest_checkpoint", ""))
    if target_identity is not None:
        declared_path = Path(declared_checkpoint)
        if (
            declared_path.is_absolute()
            or len(declared_path.parts) != 2
            or declared_path.parts[0] != "checkpoints"
            or declared_checkpoint not in inventory
            or status.get("latest_checkpoint_sha256") != inventory.get(declared_checkpoint)
        ):
            raise ValueError("Completed chain latest checkpoint declaration is not exact")
        checkpoint = load_declared_checkpoint(
            root / "checkpoints",
            declared_path.name,
            expected_target_identity=target_identity,
            expected_likelihood_family=str(target_identity.get("likelihood", "")),
        )
        if expected_terminal_iteration is not None and (
            int(checkpoint["iteration"]) != int(expected_terminal_iteration)
            or int(checkpoint["saved_draws"]) != int(expected_draws)
        ):
            raise ValueError("Completed chain terminal checkpoint iteration/draw state is not exact")
    return True


def derive_period_irrs(parameter_draws: pd.DataFrame) -> pd.DataFrame:
    required = {"chain", "draw", "parameter", "value"}
    missing = required - set(parameter_draws.columns)
    if missing:
        raise ValueError(f"Interaction draws are missing columns: {sorted(missing)}")
    index = ["chain", "draw"]
    wide = parameter_draws.pivot(index=index, columns="parameter", values="value")
    rows: list[dict[str, object]] = []
    for chain_draw, values in wide.sort_index().iterrows():
        for term in RURALITY_TERMS:
            if term not in values.index:
                continue
            main = float(values[term])
            terms = (
                ("pre_pandemic_2019", main),
                ("acute_pandemic_2020_2021", main + float(values[f"{term}__x__acute_pandemic"])),
                ("later_period_2022_2024", main + float(values[f"{term}__x__later_period"])),
            )
            for period, coefficient in terms:
                rows.append(
                    {
                        "chain": int(chain_draw[0]),
                        "draw": int(chain_draw[1]),
                        "parameter": term,
                        "period": period,
                        "log_coefficient": coefficient,
                        "irr": float(np.exp(coefficient)),
                    }
                )
    return pd.DataFrame(rows)


def _check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def evaluate_profile_gate(
    *,
    profile: SensitivityProfile,
    chain_records: Sequence[Mapping[str, object]],
    diagnostics: pd.DataFrame,
    comparisons: pd.DataFrame,
    expected_schema: Sequence[str],
    expected_years: Sequence[str],
    expected_comparison_parameters: Sequence[str],
    thresholds: Mapping[str, float | int],
    primary_parameters: Sequence[str] = PRIMARY_TERMS,
) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    chain_ids = [int(row.get("chain_id", -1)) for row in chain_records]
    checks.append(_check("exact_four_completed_chains", chain_ids == [1, 2, 3, 4] and all(row.get("status") == "completed" for row in chain_records), f"chain_ids={chain_ids}"))
    checks.append(_check("expected_draws", len(chain_records) == 4 and all(int(row.get("saved_draws", -1)) == 4500 for row in chain_records), f"draws={[row.get('saved_draws') for row in chain_records]}"))
    checks.append(_check("artifact_hashes", len(chain_records) == 4 and all(row.get("hashes_verified") is True for row in chain_records), f"verified={[row.get('hashes_verified') for row in chain_records]}"))
    failures = sum(int(row.get("constraint_failures", -1)) for row in chain_records) if len(chain_records) == 4 else -1
    checks.append(_check("zero_constraint_failures", failures == int(thresholds["constraint_failures_allowed"]), f"failures={failures}"))
    schema_ok = len(chain_records) == 4 and all(list(row.get("parameter_schema", [])) == list(expected_schema) for row in chain_records)
    if profile.likelihood == "poisson":
        schema_ok = schema_ok and "kappa" not in expected_schema
    if profile.model == "pandemic_interaction":
        schema_ok = schema_ok and [term for term in expected_schema if "__x__" in term] == list(EXPECTED_INTERACTION_TERMS)
    checks.append(_check("exact_parameter_schema", schema_ok, f"expected_parameters={len(expected_schema)}"))
    years_ok = len(chain_records) == 4 and all(list(map(str, row.get("included_years", []))) == list(map(str, expected_years)) for row in chain_records)
    checks.append(_check("included_years", years_ok, f"expected={list(expected_years)}"))

    try:
        validate_diagnostics_table(diagnostics, parameter_schema=expected_schema)
        diagnostics_valid, diagnostics_detail = True, f"parameters={len(diagnostics)} chains=4 draws_per_chain=4500"
    except Exception as exc:
        diagnostics_valid, diagnostics_detail = False, str(exc)
    checks.append(_check("diagnostics_complete_and_finite", diagnostics_valid, diagnostics_detail))
    if diagnostics_valid:
        all_ok = bool(
            (diagnostics["r_hat"] <= float(thresholds["rhat_max_all"])).all()
            and (diagnostics["ess_bulk"] >= float(thresholds["ess_bulk_min_all"])).all()
            and (diagnostics["ess_tail"] >= float(thresholds["ess_tail_min_all"])).all()
        )
        primary = diagnostics[diagnostics["parameter"].isin(primary_parameters)]
        expected_primary = sorted(set(expected_schema) & set(primary_parameters))
        primary_ok = sorted(primary["parameter"].astype(str)) == expected_primary and bool(
            (primary["r_hat"] <= float(thresholds["rhat_max_primary"])).all()
            and (primary["ess_bulk"] >= float(thresholds["ess_bulk_min_primary"])).all()
            and (primary["ess_tail"] >= float(thresholds["ess_tail_min_primary"])).all()
        )
    else:
        all_ok = primary_ok = False
    checks.append(_check("all_parameter_convergence", all_ok, "inclusive R-hat and ESS thresholds"))
    checks.append(_check("primary_parameter_convergence", primary_ok, "inclusive primary R-hat and ESS thresholds"))
    try:
        validate_comparison_table(comparisons, profile_id=profile.profile_id)
        comparison_valid, comparison_detail = True, f"keys={len(comparisons)}"
    except Exception as exc:
        comparison_valid, comparison_detail = False, str(exc)
    checks.append(_check("complete_primary_comparisons", comparison_valid, comparison_detail))
    passed = all(bool(row["passed"]) for row in checks)
    return {
        "profile": profile.profile_id,
        "passed": passed,
        "status": "PASS" if passed else "HOLD",
        "checks": checks,
    }


def artifact_inventory(root: str | Path, relative_paths: Iterable[str | Path]) -> dict[str, str]:
    base = Path(root).resolve()
    result: dict[str, str] = {}
    for relative in relative_paths:
        relative_path = Path(relative)
        path = (base / relative_path).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError(f"Cannot hash missing/out-of-root artifact: {relative_path}")
        result[relative_path.as_posix()] = sha256_file(path)
    return result
