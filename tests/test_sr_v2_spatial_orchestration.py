"""Contract tests for the lean SR-v2 BYM2 cluster orchestration.

The orchestration layer is deliberately thin: every scientific guarantee lives
in the reviewed Task 3 code (scripts 106-109 and
``bayes_constrained.spatial_pipeline``).  These tests therefore check two things
and nothing else:

* that the batch and driver scripts call the reviewed entry points, wire the
  dependency graph correctly, and preserve the exit statuses that carry meaning;
* that the controller translates reviewed answers into exit codes and fails
  closed when a reviewed validator refuses.

They deliberately do not re-test the science, and they do not need a Linux
sandbox: the shell files are checked as text, and the controller is exercised
in-process.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
WAHAB = ROOT / "hpc" / "wahab"
CONTROLLER_PATH = ROOT / "scripts" / "110_orchestrate_sr_v2_spatial_sensitivity.py"

RUN_ID = "sr-v2-spatial-sensitivity-20260818-v1"

BENCHMARK = WAHAB / "slurm/65_sr_v2_spatial_sensitivity_benchmark.sbatch"
CHAIN_ARRAY = WAHAB / "slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch"
FINALIZER = WAHAB / "slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch"
STAGE = WAHAB / "stage_sr_v2_spatial_sensitivity_to_scratch.sh"
SYNC = WAHAB / "sync_sr_v2_spatial_sensitivity_results_home.sh"
SUBMIT = WAHAB / "submit_sr_v2_spatial_sensitivity.sh"
RESUME = WAHAB / "resume_sr_v2_spatial_sensitivity.sh"

ORCHESTRATION_FILES = (BENCHMARK, CHAIN_ARRAY, FINALIZER, STAGE, SYNC, SUBMIT, RESUME)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_controller() -> Any:
    spec = importlib.util.spec_from_file_location(
        "sr_v2_spatial_orchestrator", CONTROLLER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Shell contract
# --------------------------------------------------------------------------


def test_every_orchestration_file_exists_with_a_login_shell_shebang() -> None:
    for path in ORCHESTRATION_FILES:
        assert path.is_file(), path
        assert read(path).startswith("#!/bin/bash -l\n"), path


@pytest.mark.skipif(os.name == "nt", reason="NTFS carries no POSIX mode bits")
def test_every_orchestration_file_is_executable_on_posix() -> None:
    for path in ORCHESTRATION_FILES:
        assert stat.S_IMODE(path.stat().st_mode) & stat.S_IXUSR, path


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is unavailable")
def test_every_orchestration_file_parses() -> None:
    for path in ORCHESTRATION_FILES:
        # Relative, with cwd set: an absolute Windows path is mangled by the
        # POSIX-path translation in a Windows bash build.
        result = subprocess.run(
            ["bash", "-n", path.relative_to(ROOT).as_posix()],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{path.name}: {result.stderr}"


def test_batch_jobs_call_only_reviewed_entry_points() -> None:
    """The batch layer starts reviewed code; it never re-derives a verdict."""

    expected = {
        BENCHMARK: ("110_orchestrate_sr_v2_spatial_sensitivity.py",),
        CHAIN_ARRAY: (
            "110_orchestrate_sr_v2_spatial_sensitivity.py",
            "107_run_sr_v2_spatial_sensitivity_chain.py",
        ),
        FINALIZER: (
            "108_merge_sr_v2_spatial_sensitivity.py",
            "109_gate_sr_v2_spatial_sensitivity.py",
        ),
    }
    for path, entry_points in expected.items():
        text = read(path)
        for entry_point in entry_points:
            assert entry_point in text, f"{path.name} must call {entry_point}"
        # A second implementation of the trust chain in shell is exactly what
        # this layer was rewritten to remove.
        assert "sha256sum -c" not in text, path.name
        assert "<<'PY'" not in text and '<<"PY"' not in text, path.name


def test_finalizer_runs_merge_verify_release_then_gate_in_order() -> None:
    text = read(FINALIZER)
    order = [
        text.index("108_merge_sr_v2_spatial_sensitivity.py"),
        text.index("--independent-verify"),
        text.index("--write-release-manifest"),
        text.index("--gate"),
    ]
    assert order == sorted(order), "the gate must run last"


def test_submit_wires_the_benchmark_gated_dependency_graph() -> None:
    """A run that cannot fit the cluster envelope must never reach the chains."""

    text = read(SUBMIT)
    assert "106_prepare_sr_v2_spatial_sensitivity.py --launch-envelope" in text
    assert re.search(r"benchmark_job=.*sbatch --parsable[^\n]*65_", text)
    assert re.search(r'chain_job=.*--dependency="afterok:\$\{benchmark_job\}"', text)
    assert re.search(r'finalize_job=.*--dependency="afterok:\$\{chain_job\}"', text)
    assert "LAUNCH_ENVELOPE" in text


def test_chain_array_is_throttled_two_at_a_time_over_four_chains() -> None:
    text = read(CHAIN_ARRAY)
    assert "#SBATCH --array=1-4%2" in text


def test_chain_array_forwards_usr1_and_preserves_the_runner_exit_status() -> None:
    """Exit 75 is a cooperative checkpoint, not a chain failure."""

    text = read(CHAIN_ARRAY)
    assert "#SBATCH --signal=B:USR1@300" in text
    assert re.search(r"trap 'kill -USR1 \"\$CHAIN_PID\"", text)
    assert "CHAIN_RC=$?" in text
    assert 'exit "$CHAIN_RC"' in text
    # The status must be reported, never rewritten to 0.
    assert "exit 0" not in text


def test_chain_array_checks_chain_scoped_authority_only_when_extending() -> None:
    """Throttling means peers advance first, so authority is per chain."""

    text = read(CHAIN_ARRAY)
    guard = text.index('if [ "$EXTENSION_EPOCH" -ne 0 ]')
    call = text.index("chain-authorize")
    assert guard < call
    assert "--chain-id" in text and "--to-epoch" in text


def test_resume_never_chooses_chains_itself() -> None:
    text = read(RESUME)
    assert "retry-select" in text and "extension-authorize" in text
    # Retry must run the reviewed selection verbatim, never a hand-built range.
    assert 'ARRAY_SPEC="$(' in text
    assert "chain_status.json" not in text


def test_resume_treats_an_empty_retry_selection_as_success() -> None:
    """Nothing to retry is a normal outcome, not an operator-facing failure."""

    text = read(RESUME)
    assert re.search(r'if \[ "\$SELECT_RC" -eq 3 \]', text)
    assert "resume_status=nothing_to_do" in text


def test_resume_refuses_epoch_zero_as_an_extension() -> None:
    text = read(RESUME)
    assert re.search(r'if \[ "\$MODE" = "extend" \] && \[ "\$EPOCH" = "0" \]', text)


def test_sync_is_transport_only_and_never_prunes_the_home_record() -> None:
    text = read(SYNC)
    assert "--delete" not in text.replace("--delete is deliberately not offered", "")
    assert "rsync" in text
    assert RUN_ID in text


def test_stage_fails_closed_on_a_missing_required_input() -> None:
    text = read(STAGE)
    assert "Missing required spatial-sensitivity staging input" in text
    for required in (
        "config/sr_v2_spatial_sensitivity_execution.yaml",
        "data/processed/bayes_constrained/model_frame.parquet",
        "outputs/scientific_reports_v2/production_8chain",
        "outputs/scientific_reports_v2/spatial_residual_diagnostics",
    ):
        assert required in text, required


# --------------------------------------------------------------------------
# Controller contract
# --------------------------------------------------------------------------


def test_controller_exposes_exactly_the_operational_subcommands() -> None:
    parser = load_controller().build_parser()
    choices = next(
        action.choices for action in parser._actions if getattr(action, "choices", None)
    )
    assert set(choices) == {
        "prepared",
        "benchmark-run",
        "benchmark-validate",
        "benchmark-hold",
        "retry-select",
        "extension-authorize",
        "chain-authorize",
    }


def test_controller_fails_closed_when_a_reviewed_validator_refuses(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_controller()

    def refuse(*_args: object, **_kwargs: object) -> dict[str, Any]:
        raise ValueError("reviewed validator refused")

    module.select_retry_indexes = refuse
    assert module.main(["retry-select", "--extension-epoch", "0"]) == module.EXIT_REFUSED
    assert "reviewed validator refused" in capsys.readouterr().err


def test_controller_retry_select_emits_explicit_indexes_never_a_range(
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_controller()
    module.select_retry_indexes = lambda *_a, **_k: {
        "schema_id": "sr_v2_spatial_retry_selection/v1",
        "run_id": RUN_ID,
        "extension_epoch": 1,
        "selected_array_indexes": [1, 3],
    }
    assert module.main(["retry-select", "--extension-epoch", "1"]) == module.EXIT_OK
    assert capsys.readouterr().out.strip() == "1,3"


def test_controller_signals_nothing_to_do_when_no_chain_needs_a_retry() -> None:
    module = load_controller()
    module.select_retry_indexes = lambda *_a, **_k: {
        "schema_id": "sr_v2_spatial_retry_selection/v1",
        "run_id": RUN_ID,
        "extension_epoch": 2,
        "selected_array_indexes": [],
    }
    assert (
        module.main(["retry-select", "--extension-epoch", "2"])
        == module.EXIT_NOTHING_TO_DO
    )


def test_controller_rejects_a_retry_selection_for_the_wrong_identity() -> None:
    module = load_controller()
    module.select_retry_indexes = lambda *_a, **_k: {
        "schema_id": "sr_v2_spatial_retry_selection/v1",
        "run_id": "some-other-run",
        "extension_epoch": 1,
        "selected_array_indexes": [1],
    }
    assert module.main(["retry-select", "--extension-epoch", "1"]) == module.EXIT_REFUSED


@pytest.mark.parametrize("epoch", ["-1", "4", "9"])
def test_controller_rejects_epochs_outside_zero_to_three(epoch: str) -> None:
    module = load_controller()
    module.select_retry_indexes = lambda *_a, **_k: pytest.fail("must not be reached")
    assert module.main(["retry-select", "--extension-epoch", epoch]) == module.EXIT_REFUSED


@pytest.mark.parametrize("chain_id", ["0", "5"])
def test_controller_rejects_chain_ids_outside_one_to_four(chain_id: str) -> None:
    module = load_controller()
    module.validate_chain_extension_authorization = lambda *_a, **_k: pytest.fail(
        "must not be reached"
    )
    assert (
        module.main(["chain-authorize", "--chain-id", chain_id, "--to-epoch", "1"])
        == module.EXIT_REFUSED
    )


def test_controller_extension_commands_refuse_epoch_zero() -> None:
    module = load_controller()
    module.validate_extension_authorization = lambda *_a, **_k: pytest.fail(
        "must not be reached"
    )
    module.validate_chain_extension_authorization = lambda *_a, **_k: pytest.fail(
        "must not be reached"
    )
    assert (
        module.main(["extension-authorize", "--to-epoch", "0"]) == module.EXIT_REFUSED
    )
    assert (
        module.main(["chain-authorize", "--chain-id", "1", "--to-epoch", "0"])
        == module.EXIT_REFUSED
    )


def test_controller_benchmark_hold_requires_a_reason() -> None:
    module = load_controller()
    recorded: list[str] = []
    module.set_benchmark_failure_hold = lambda _root, *, reason: recorded.append(reason) or {
        "reason": reason
    }
    assert module.main(["benchmark-hold", "--reason", "   "]) == module.EXIT_REFUSED
    assert not recorded
    assert module.main(["benchmark-hold", "--reason", "benchmark_rc_70"]) == module.EXIT_OK
    assert recorded == ["benchmark_rc_70"]
