from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = ROOT / (path or "config/submission_visuals.yaml")
    with config_path.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    config["_config_path"] = str(config_path)
    return config


def rel_path(config: dict[str, Any], key: str) -> Path:
    return ROOT / config["paths"][key]


def output_dirs(config: dict[str, Any]) -> dict[str, Path]:
    return {name: ROOT / path for name, path in config["outputs"].items()}


def ensure_output_dirs(config: dict[str, Any]) -> dict[str, Path]:
    dirs = output_dirs(config)
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    for leaf in ["main", "supplement"]:
        (dirs["figures"] / leaf).mkdir(parents=True, exist_ok=True)
    return dirs


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def load_model_frame(config: dict[str, Any]) -> pd.DataFrame:
    return read_table(rel_path(config, "model_frame"))


def load_county_summary(config: dict[str, Any]) -> pd.DataFrame:
    return read_table(rel_path(config, "county_posterior_summary"))


def final_estimates(config: dict[str, Any]) -> pd.DataFrame:
    production_path = rel_path(config, "posterior_primary_summary")
    production = pd.read_csv(production_path).set_index("parameter")
    rows = []
    for item in config["final_wahab_handoff"]["primary_estimates"]:
        row = dict(item)
        if row["parameter"] not in production.index:
            raise ValueError(f"Production posterior summary is missing {row['parameter']!r}.")
        derived = production.loc[row["parameter"]]
        for key in [
            "posterior_median",
            "credible_interval_lower_95",
            "credible_interval_upper_95",
            "posterior_probability_gt_1",
            "r_hat",
            "ess_bulk",
            "ess_tail",
            "mcse_mean",
        ]:
            row[key] = derived.get(key)
        row["ess"] = row["ess_bulk"]
        row.setdefault("posterior_probability_gt_1", None)
        row.setdefault("r_hat", None)
        row.setdefault("ess", None)
        if row["estimate_type"] == "IRR":
            row["estimate_95"] = (
                f"{row['posterior_median']:.2f} "
                f"({row['credible_interval_lower_95']:.2f}-{row['credible_interval_upper_95']:.2f})"
            )
            row["interpretation"] = (
                f"Posterior median IRR {row['posterior_median']:.2f} "
                f"(95% CrI {row['credible_interval_lower_95']:.2f}-"
                f"{row['credible_interval_upper_95']:.2f}); "
                f"Pr(IRR>1)={row['posterior_probability_gt_1']:.2f}."
            )
        else:
            row["estimate_95"] = (
                f"{row['posterior_median']:.3f} "
                f"({row['credible_interval_lower_95']:.3f}-{row['credible_interval_upper_95']:.3f})"
            )
            row["interpretation"] = (
                f"Posterior median coefficient {row['posterior_median']:.3f} "
                f"(95% CrI {row['credible_interval_lower_95']:.3f}-"
                f"{row['credible_interval_upper_95']:.3f})."
            )
        rows.append(row)
    return pd.DataFrame(rows)


def primary_estimate(config: dict[str, Any]) -> dict[str, Any]:
    df = final_estimates(config)
    row = df[df["parameter"] == "primary_rurality_nonmetro_nonadjacent"].iloc[0]
    return row.to_dict()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(paths: list[Path], out_path: Path, root: Path = ROOT) -> pd.DataFrame:
    rows = []
    for path in paths:
        if path.exists() and path.is_file():
            rows.append(
                {
                    "path": str(path.relative_to(root)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    df = pd.DataFrame(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def hpc_bundle_status(config: dict[str, Any]) -> dict[str, Any]:
    verification = rel_path(config, "production_verification")
    status = {
        "production_verification_path": str(verification.relative_to(ROOT)),
        "production_verification_exists": verification.exists(),
        "using_locked_handoff": False,
        "source": config["final_wahab_handoff"]["source"],
    }
    if verification.exists():
        try:
            status["verification"] = json.loads(verification.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            status["verification_parse_error"] = str(exc)
    return status
