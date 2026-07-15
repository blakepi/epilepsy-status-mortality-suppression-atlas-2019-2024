from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import HPC_OUT, PROJECT_ROOT, chain_status_paths, rel

import sys

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from bayes_constrained.diagnostics import diagnostics_table  # noqa: E402
from bayes_constrained.paths import OUTPUT_DIR  # noqa: E402


def main() -> None:
    HPC_OUT.mkdir(parents=True, exist_ok=True)
    status_rows = []
    draw_frames = []
    acceptance_frames = []
    validation_frames = []
    latent_arrays = []
    draw_meta = []
    for status_path in chain_status_paths():
        chain_dir = status_path.parent
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status_rows.append({"chain": chain_dir.name, **status})
        draws_path = chain_dir / "draws_params.parquet"
        if draws_path.exists():
            draw_frames.append(pd.read_parquet(draws_path))
        acc_path = chain_dir / "acceptance_rates.csv"
        if acc_path.exists():
            acceptance_frames.append(pd.read_csv(acc_path))
        val_path = chain_dir / "latent_validation.csv"
        if val_path.exists():
            validation_frames.append(pd.read_csv(val_path))
        latent_path = chain_dir / "draws_latent.npz"
        if latent_path.exists():
            y = np.load(latent_path, allow_pickle=True)["y"]
            if y.size:
                latent_arrays.append(y.astype(np.int16))
                for draw_index in range(y.shape[0]):
                    draw_meta.append({"chain": status.get("chain_id"), "draw": draw_index + 1})
    status_df = pd.DataFrame(status_rows)
    status_df.to_csv(HPC_OUT / "chain_status_summary.csv", index=False)
    if not draw_frames:
        raise SystemExit("No per-chain parameter draws found.")
    draws = pd.concat(draw_frames, ignore_index=True)
    draws.to_csv(OUTPUT_DIR / "posterior_parameter_draws.csv", index=False)
    draws.to_csv(HPC_OUT / "posterior_parameter_draws_hpc.csv", index=False)
    if acceptance_frames:
        pd.concat(acceptance_frames, ignore_index=True).to_csv(OUTPUT_DIR / "mcmc_acceptance_rates.csv", index=False)
    if validation_frames:
        pd.concat(validation_frames, ignore_index=True).to_csv(HPC_OUT / "hpc_constraint_validation_summary.csv", index=False)
    if latent_arrays:
        latent = np.concatenate(latent_arrays, axis=0)
        np.savez_compressed(
            OUTPUT_DIR / "posterior_draws_primary.npz",
            y=latent,
            draw_meta=pd.DataFrame(draw_meta).to_records(index=False),
        )
    diagnostics = diagnostics_table(draws)
    diagnostics.to_csv(HPC_OUT / "hpc_mcmc_diagnostics.csv", index=False)
    runtime = status_df[["chain", "status", "mode", "iteration", "target_iteration", "saved_draws", "grand_total"]]
    runtime.to_csv(HPC_OUT / "hpc_runtime_summary.csv", index=False)
    print(f"chain_status_summary={rel(HPC_OUT / 'chain_status_summary.csv')}")
    print(f"hpc_mcmc_diagnostics={rel(HPC_OUT / 'hpc_mcmc_diagnostics.csv')}")


if __name__ == "__main__":
    main()
