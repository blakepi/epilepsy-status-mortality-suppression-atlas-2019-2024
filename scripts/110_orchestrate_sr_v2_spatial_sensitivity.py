#!/usr/bin/env python3
"""Operational controller for the SR-v2 BYM2 spatial-sensitivity cluster run.

Every scientific guarantee already lives in the reviewed Task 3 API: preparation
identity, chain custody across retries and extension epochs, the merge, the
independent verifier, and the gate are implemented in scripts 106-109 and in
``bayes_constrained.spatial_pipeline``.

This module exists only so the batch scripts can ask that reviewed code the few
operational questions a launcher actually needs -- may this wave start, which
chains need a retry, did the benchmark hold its limits -- without embedding
Python inside a shell heredoc, where it could not be imported, unit-tested, or
linted.  It adds no validation of its own and deliberately holds no scientific
logic; it translates reviewed answers into exit codes and stdout.

Exit codes
    0   the reviewed validator accepted
    3   nothing to do (no chain needs a retry)
    64  usage error
    70  the reviewed validator refused
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.spatial_pipeline import (  # noqa: E402
    RUN_ID,
    select_retry_indexes,
    set_benchmark_failure_hold,
    spatial_run_root,
    validate_benchmark_evidence,
    validate_chain_extension_authorization,
    validate_extension_authorization,
    validate_prepared_source_envelope,
)

CONFIG_PATH = ROOT / "config/sr_v2_spatial_sensitivity_execution.yaml"

EXIT_OK = 0
EXIT_NOTHING_TO_DO = 3
EXIT_USAGE = 64
EXIT_REFUSED = 70


def _chain_runner() -> Any:
    """Import the reviewed chain runner, whose module name is not an identifier."""

    path = ROOT / "scripts/107_run_sr_v2_spatial_sensitivity_chain.py"
    spec = importlib.util.spec_from_file_location("sr_v2_spatial_chain_runner", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load the reviewed chain runner from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _emit(payload: Any) -> None:
    """Write one canonical JSON object to stdout for the calling batch script."""

    json.dump(payload, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")


def _prepared() -> dict[str, Any]:
    return validate_prepared_source_envelope(ROOT, config_path=CONFIG_PATH)


def _exact_epoch(value: int, *, label: str) -> int:
    if type(value) is not int or not 0 <= value <= 3:
        raise ValueError(f"{label} must be an exact integer in 0..3")
    return value


def cmd_prepared(_args: argparse.Namespace) -> int:
    _emit(_prepared())
    return EXIT_OK


def cmd_benchmark_run(_args: argparse.Namespace) -> int:
    """Run the reviewed 2,000-iteration throughput canary before the real array.

    ``benchmark_prepared_target`` never touches the scientific chain namespace
    and publishes no draws; it exists so a run that cannot fit the 65-hour or
    56-GiB envelope fails in minutes instead of taking four chains down with it.
    """

    output_path = spatial_run_root(ROOT) / "benchmark/benchmark_report.json"
    _emit(_chain_runner().benchmark_prepared_target(root=ROOT, output_path=output_path))
    return EXIT_OK


def cmd_benchmark_validate(_args: argparse.Namespace) -> int:
    prepared = _prepared()
    manifest = prepared["manifest"]
    mapping = manifest["chain_mapping"]
    validated = validate_benchmark_evidence(
        spatial_run_root(ROOT),
        preparation_identity=manifest["preparation_identity"],
        target_fingerprints=[row["target_fingerprint"] for row in mapping],
        launch_envelope_sha256=prepared["launch_envelope_sha256"],
        final_source_manifest_sha256=prepared["final_source_manifest_sha256"],
    )
    report = validated.get("report") if isinstance(validated, dict) else None
    if not isinstance(report, dict):
        raise ValueError("benchmark validator returned no report")
    # The benchmark is the throughput canary for exactly the first chain target.
    if type(report.get("array_index")) is not int or report["array_index"] != 1:
        raise ValueError("benchmark evidence must be for exact array index 1")
    if report.get("target_fingerprint") != mapping[0]["target_fingerprint"]:
        raise ValueError("benchmark evidence target fingerprint mismatch")
    _emit(validated)
    return EXIT_OK


def cmd_benchmark_hold(args: argparse.Namespace) -> int:
    reason = str(args.reason).strip()
    if not reason:
        raise ValueError("--reason must be a nonempty string")
    _emit(set_benchmark_failure_hold(ROOT, reason=reason))
    return EXIT_OK


def cmd_retry_select(args: argparse.Namespace) -> int:
    epoch = _exact_epoch(args.extension_epoch, label="--extension-epoch")
    payload = select_retry_indexes(spatial_run_root(ROOT), extension_epoch=epoch)
    if (
        payload.get("schema_id") != "sr_v2_spatial_retry_selection/v1"
        or payload.get("run_id") != RUN_ID
        or payload.get("extension_epoch") != epoch
    ):
        raise ValueError("retry selector identity mismatch")
    selected = payload["selected_array_indexes"]
    if not selected:
        return EXIT_NOTHING_TO_DO
    # A Slurm array specification, e.g. "1,3" -- never a range, so a chain that
    # already verified as complete can never be silently re-run.
    sys.stdout.write(",".join(str(index) for index in selected) + "\n")
    return EXIT_OK


def cmd_extension_authorize(args: argparse.Namespace) -> int:
    epoch = _exact_epoch(args.to_epoch, label="--to-epoch")
    if epoch == 0:
        raise ValueError("--to-epoch must be an extension epoch in 1..3")
    _emit(validate_extension_authorization(spatial_run_root(ROOT), to_extension_epoch=epoch))
    return EXIT_OK


def cmd_chain_authorize(args: argparse.Namespace) -> int:
    epoch = _exact_epoch(args.to_epoch, label="--to-epoch")
    if epoch == 0:
        raise ValueError("--to-epoch must be an extension epoch in 1..3")
    chain_id = args.chain_id
    if type(chain_id) is not int or not 1 <= chain_id <= 4:
        raise ValueError("--chain-id must be an exact integer in 1..4")
    # Chain-scoped so a throttled %2 wave may start after its peers advanced.
    _emit(
        validate_chain_extension_authorization(
            spatial_run_root(ROOT), chain_id=chain_id, to_extension_epoch=epoch
        )
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("prepared", help="print the validated prepared envelope").set_defaults(
        handler=cmd_prepared
    )
    sub.add_parser(
        "benchmark-run", help="run the reviewed 2,000-iteration throughput canary"
    ).set_defaults(handler=cmd_benchmark_run)
    sub.add_parser(
        "benchmark-validate", help="validate immutable benchmark evidence for array index 1"
    ).set_defaults(handler=cmd_benchmark_validate)

    hold = sub.add_parser("benchmark-hold", help="record a canonical benchmark failure hold")
    hold.add_argument("--reason", required=True)
    hold.set_defaults(handler=cmd_benchmark_hold)

    retry = sub.add_parser("retry-select", help="print the exact array indexes needing a retry")
    retry.add_argument("--extension-epoch", required=True, type=int)
    retry.set_defaults(handler=cmd_retry_select)

    extend = sub.add_parser(
        "extension-authorize", help="validate reviewed convergence-only extension authority"
    )
    extend.add_argument("--to-epoch", required=True, type=int)
    extend.set_defaults(handler=cmd_extension_authorize)

    chain = sub.add_parser(
        "chain-authorize", help="validate one chain's prior-epoch authority in a throttled wave"
    )
    chain.add_argument("--chain-id", required=True, type=int)
    chain.add_argument("--to-epoch", required=True, type=int)
    chain.set_defaults(handler=cmd_chain_authorize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:  # argparse already reported the problem
        return EXIT_USAGE if error.code else EXIT_OK
    try:
        return int(args.handler(args))
    except Exception as error:  # fail closed: the launcher must never proceed
        sys.stderr.write(f"{args.command}: {type(error).__name__}: {error}\n")
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
