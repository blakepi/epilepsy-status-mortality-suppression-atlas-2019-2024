from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from .data import augment_age17_covariate, make_pandemic_exclusion_frame
from .model import PRIMARY_TERMS, make_design


RUN_ID = "sr-v2-heavy-sensitivity-20260818-v1"
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
    reviewed_sources: dict[str, str]
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
        reviewed_sources=_require_sha256_mapping(raw.get("reviewed_sources"), "reviewed_sources"),
        comparison=dict(raw.get("comparison", {})),
        interpretation_boundary=str(raw.get("interpretation_boundary", "")),
        raw=raw,
    )
    _validate_spec(spec)
    return spec


def _validate_spec(spec: ExecutionSpec) -> None:
    if spec.schema_id != "sr_v2_heavy_sensitivity_execution/v1" or spec.run_id != RUN_ID:
        raise ValueError("Unexpected heavy-sensitivity schema or immutable run id")
    if tuple(profile.profile_id for profile in spec.profiles) != PROFILE_IDS:
        raise ValueError("Sensitivity profiles are not in the frozen six-profile order")
    if spec.raw.get("reviewed_source_hash_mode") != "canonical_lf_utf8":
        raise ValueError("Reviewed source hashes must use the cross-platform canonical-LF contract")
    if len(spec.chain_map) != 24 or [row.array_index for row in spec.chain_map] != list(range(1, 25)):
        raise ValueError("Chain map must contain ordered array indexes 1 through 24")
    if len({row.chain_seed for row in spec.chain_map}) != 24 or len({row.initialization_seed for row in spec.chain_map}) != 24:
        raise ValueError("All chain seeds and initialization seeds must be unique by role")
    for profile_id in PROFILE_IDS:
        rows = [row for row in spec.chain_map if row.profile_id == profile_id]
        if [row.chain_id for row in rows] != [1, 2, 3, 4]:
            raise ValueError(f"Profile {profile_id} must have chains 1 through 4")
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
        "parameter_schema": list(map(str, parameter_schema)),
    }
    return canonical_sha256(payload)


def preparation_identity(spec: ExecutionSpec, *, config_sha256: str) -> str:
    return canonical_sha256(
        {
            "schema_id": "sr_v2_heavy_sensitivity_preparation_identity/v1",
            "run_id": spec.run_id,
            "repository_base_commit": spec.repository_base_commit,
            "operational_config_sha256": config_sha256,
            "source_authorities": spec.source_authorities,
            "reviewed_sources": spec.reviewed_sources,
            "profiles": [profile.to_dict() for profile in spec.profiles],
            "chain_map": [row.to_dict() for row in spec.chain_map],
        }
    )


def assert_manifest_matches(expected: Mapping[str, object], actual: Mapping[str, object]) -> None:
    identity_fields = ("run_id", "preparation_identity", "operational_config_sha256")
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
    for relative, expected_hash in inventory.items():
        actual = sha256_file(_safe_artifact_path(root, str(relative)))
        if actual != expected_hash:
            raise ValueError(
                f"Artifact SHA-256 mismatch for {relative}: expected {expected_hash}, found {actual}"
            )
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

    diag_parameters = diagnostics["parameter"].astype(str).tolist() if "parameter" in diagnostics else []
    diag_complete = sorted(diag_parameters) == sorted(map(str, expected_schema))
    numeric_columns = ["r_hat", "ess_bulk", "ess_tail"]
    finite = all(column in diagnostics for column in numeric_columns) and np.isfinite(diagnostics[numeric_columns].to_numpy(dtype=float)).all()
    checks.append(_check("diagnostics_complete_and_finite", diag_complete and finite, f"parameters={len(diag_parameters)}"))
    if diag_complete and finite:
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
    actual_comparisons = sorted(comparisons["parameter"].astype(str).unique()) if "parameter" in comparisons else []
    checks.append(_check("complete_primary_comparisons", actual_comparisons == sorted(map(str, expected_comparison_parameters)), f"parameters={actual_comparisons}"))
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
