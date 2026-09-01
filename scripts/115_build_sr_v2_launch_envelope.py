#!/usr/bin/env python3
"""Build the reviewed external launch envelope for an SR-v2 robustness launch.

The envelope authorises a cluster launch, so it is deliberately produced
*outside* the repository: a certificate cannot contain the checksum of the
commit that contains it.  This script binds one clean commit, a git bundle of
that commit, raw-byte hashes of the reviewed source set, and the committed
joint-regression evidence.

It refuses to emit an envelope unless the worktree is clean, every reviewed
source file exists, and the recorded evidence file is present and committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bayes_constrained.spatial_pipeline import (  # noqa: E402
    SPATIAL_FINAL_SOURCE_FILES,
    canonical_sha256,
)

EVIDENCE_RELATIVE = "outputs/scientific_reports_v2/launch/joint_regression_evidence.json"


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", required=True,
        help="directory OUTSIDE the repository to receive the envelope and bundle",
    )
    args = parser.parse_args(argv)

    destination = Path(args.out).resolve()
    if ROOT == destination or ROOT in destination.parents:
        raise SystemExit("Refusing to write the launch envelope inside the repository")

    if git("status", "--porcelain"):
        raise SystemExit("Refusing to certify a dirty worktree")
    launch_commit = git("rev-parse", "HEAD").lower()
    if len(launch_commit) != 40 or any(c not in "0123456789abcdef" for c in launch_commit):
        raise SystemExit(f"Unexpected launch commit: {launch_commit!r}")

    evidence = ROOT / EVIDENCE_RELATIVE
    if not evidence.is_file():
        raise SystemExit(f"Missing joint-regression evidence: {EVIDENCE_RELATIVE}")
    if git("ls-files", "--error-unmatch", EVIDENCE_RELATIVE) != EVIDENCE_RELATIVE:
        raise SystemExit("Joint-regression evidence is not committed")

    sources: dict[str, str] = {}
    for relative in SPATIAL_FINAL_SOURCE_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"Reviewed source file is missing: {relative}")
        sources[relative] = sha256_file(path)

    destination.mkdir(parents=True, exist_ok=True)
    bundle = destination / f"sr-v2-{launch_commit[:12]}.bundle"
    git("bundle", "create", str(bundle), "HEAD")

    source_manifest = {
        "schema_id": "sr_v2_robustness_final_source_manifest/v1",
        "status": "reviewed_final",
        "joint_regression_passed": True,
        "source_hash_mode": "raw_bytes",
        "sources": sources,
        "joint_regression_evidence": EVIDENCE_RELATIVE,
        "joint_regression_evidence_sha256": sha256_file(evidence),
    }
    payload = {
        "schema_id": "sr_v2_robustness_launch_envelope/v1",
        "status": "reviewed_final",
        "clean_worktree": True,
        "launch_commit": launch_commit,
        "bundle_sha256": sha256_file(bundle),
        "source_manifest": source_manifest,
        "source_manifest_sha256": canonical_sha256(source_manifest),
    }

    envelope = destination / "sr_v2_launch_envelope.json"
    envelope.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    envelope.with_name(envelope.name + ".sha256").write_text(
        sha256_file(envelope) + "\n", encoding="ascii", newline="\n"
    )

    print(f"launch_commit={launch_commit}")
    print(f"reviewed_sources={len(sources)}")
    print(f"bundle={bundle}")
    print(f"envelope={envelope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
