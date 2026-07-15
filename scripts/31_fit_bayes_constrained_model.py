from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.data import load_model_frame  # noqa: E402
from bayes_constrained.sampler import run_mcmc, run_mcmc_chain_hpc  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["quick", "smoke", "tune", "production", "extend"], default="production")
    parser.add_argument("--model", default="primary")
    parser.add_argument("--config", default=None)
    parser.add_argument("--chain-id", type=int, default=None)
    parser.add_argument("--array-task-id", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-runtime-minutes", type=int, default=None)
    parser.add_argument("--stop-before-time-limit-minutes", type=int, default=10)
    args = parser.parse_args()
    frame = load_model_frame()
    use_hpc_runner = args.mode in {"smoke", "tune", "extend"} or args.chain_id is not None or args.out_dir is not None
    if use_hpc_runner:
        if args.config is None:
            raise SystemExit("--config is required for smoke/tune/production/extend HPC chain runs.")
        chain_id = int(args.chain_id or args.array_task_id or 1)
        meta = run_mcmc_chain_hpc(
            frame,
            config_path=args.config,
            mode=args.mode,
            chain_id=chain_id,
            array_task_id=args.array_task_id,
            seed=args.seed,
            out_dir=args.out_dir or "outputs/bayes_constrained/hpc",
            checkpoint_dir=args.checkpoint_dir,
            checkpoint_every=args.checkpoint_every,
            resume=args.resume,
            force=args.force,
            max_runtime_minutes=args.max_runtime_minutes,
            stop_before_time_limit_minutes=args.stop_before_time_limit_minutes,
            model_name=args.model,
        )
    else:
        meta = run_mcmc(frame, mode=args.mode, model_name=args.model)
    print(f"mode={meta['mode']}")
    print(f"saved_draws={meta['saved_draws']}")
    if "parameter_draws_csv" in meta:
        print(f"posterior_parameter_draws={meta['parameter_draws_csv']}")
    if "outputs" in meta:
        print(f"chain_outputs={meta['outputs']}")


if __name__ == "__main__":
    main()
