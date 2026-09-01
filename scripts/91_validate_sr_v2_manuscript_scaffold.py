from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript" / "scientific_reports_v2" / "manuscript_draft_nonfinal.md"
SUPPLEMENT = ROOT / "manuscript" / "scientific_reports_v2" / "supplement_methods_validation_nonfinal.md"
MANIFEST = ROOT / "manuscript" / "scientific_reports_v2" / "placeholder_manifest.yaml"
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "manuscript_scaffold_qc"
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
WORD = re.compile(r"\b[\w–-]+\b")
SUPPLEMENT_TABLE_SHELLS = {
    "ALL_PARAMETER_DIAGNOSTICS_TABLE",
    "ACCEPTANCE_TABLE",
    "LATENT_SUMMARY_DIAGNOSTICS_TABLE",
    "PRIOR_SENSITIVITY_TABLE",
    "TEMPORAL_MODEL_FAMILY_TABLE",
    "SPATIAL_SENSITIVITY_TABLE",
    "CALIBRATION_TABLE",
    "SUPPRESSION_HANDLING_TABLE",
}


def between(text: str, start: str, end: str) -> str:
    if start not in text or end not in text:
        raise ValueError(f"Could not locate manuscript range {start!r} to {end!r}.")
    return text.split(start, 1)[1].split(end, 1)[0].strip()


def check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["working", "submission"],
        default="working",
    )
    args = parser.parse_args()

    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    supplement = SUPPLEMENT.read_text(encoding="utf-8")
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    registered = set((manifest.get("placeholders") or {}).keys()) | SUPPLEMENT_TABLE_SHELLS
    found_main = set(PLACEHOLDER.findall(manuscript))
    found_supplement = set(PLACEHOLDER.findall(supplement))
    found_all = found_main | found_supplement
    unregistered = sorted(found_all - registered)

    title_line = next(
        line[2:].strip()
        for line in manuscript.splitlines()
        if line.startswith("# ")
    )
    title_words = WORD.findall(title_line)
    abstract = between(manuscript, "## Abstract", "**Keywords:**")
    abstract_without_comment = re.sub(r"<!--.*?-->", "", abstract, flags=re.S)
    abstract_words = WORD.findall(PLACEHOLDER.sub("placeholder", abstract_without_comment))
    keyword_line = next(
        line for line in manuscript.splitlines() if line.startswith("**Keywords:**")
    )
    keywords = [
        value.strip()
        for value in keyword_line.split(":", 1)[1].split(";")
        if value.strip()
    ]

    required_main_sections = [
        "## Abstract",
        "## Introduction",
        "## Results",
        "## Discussion",
        "## Methods",
        "## References",
    ]
    required_method_subsections = [
        "### Public suppression and feasible latent state space",
        "### Negative-binomial mortality model",
        "### Priors",
        "### Feasible initialization and constrained-count proposals",
        "### Exact kernel validation",
        "### Convergence and latent-space exploration",
        "### Truth-known calibration",
        "### Prespecified robustness analyses",
        "### Residual spatial diagnostic",
        "### Ethics, data availability, code availability, and generative AI",
    ]
    prohibited = [
        str(value)
        for value in (manifest.get("prohibited_literal_fragments") or [])
    ]
    prohibited_hits = [
        value
        for value in prohibited
        if value in manuscript or value in supplement
    ]
    structured_abstract_labels = [
        label
        for label in ["Objective:", "Methods:", "Results:", "Conclusions:"]
        if label in abstract
    ]

    checks = [
        check("title_word_limit", len(title_words) <= 20, f"{len(title_words)} words"),
        check("abstract_word_limit", len(abstract_words) <= 200, f"{len(abstract_words)} words"),
        check(
            "abstract_unstructured",
            not structured_abstract_labels,
            str(structured_abstract_labels),
        ),
        check("keyword_limit", len(keywords) <= 6, f"{len(keywords)} keywords"),
        check(
            "required_main_sections",
            all(section in manuscript for section in required_main_sections),
            str(
                [
                    section
                    for section in required_main_sections
                    if section not in manuscript
                ]
            ),
        ),
        check(
            "required_method_subsections",
            all(section in manuscript for section in required_method_subsections),
            str(
                [
                    section
                    for section in required_method_subsections
                    if section not in manuscript
                ]
            ),
        ),
        check("all_placeholders_registered", not unregistered, str(unregistered)),
        check("prohibited_fragments_absent", not prohibited_hits, str(prohibited_hits)),
        check(
            "elsevier_policy_absent",
            "Elsevier" not in manuscript,
            "Elsevier reference removed",
        ),
        check(
            "wahab_not_scientific_label",
            "Final Wahab HPC" not in manuscript,
            "cluster label absent",
        ),
        check(
            "supplement_identifies_rank_and_nullity",
            all(token in supplement for token in ["9,695", "1,256", "8,439"]),
            "latent count, rank, and nullity stated",
        ),
        check(
            "supplement_documents_cycle_move",
            "General alternating-cycle swap" in supplement,
            "connectivity repair documented",
        ),
        check(
            "supplement_documents_exact_validation",
            "Exact finite-state validation" in supplement,
            "finite-state target validation documented",
        ),
    ]
    if args.mode == "submission":
        checks.append(
            check(
                "no_unresolved_submission_placeholders",
                not found_all,
                str(sorted(found_all)),
            )
        )
        gate_path = (
            ROOT
            / "outputs"
            / "scientific_reports_v2"
            / "production_8chain"
            / "production_gate.json"
        )
        gate_passed = False
        if gate_path.exists():
            gate_passed = bool(
                json.loads(gate_path.read_text(encoding="utf-8")).get(
                    "passed",
                    False,
                )
            )
        checks.append(
            check(
                "corrected_production_gate_passed",
                gate_passed,
                str(gate_path),
            )
        )

    passed = all(bool(row["passed"]) for row in checks)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "passed": passed,
        "title": title_line,
        "title_words": len(title_words),
        "abstract_words": len(abstract_words),
        "keywords": keywords,
        "main_placeholders": sorted(found_main),
        "supplement_placeholders": sorted(found_supplement),
        "checks": checks,
        "interpretation_boundary": (
            "Working mode validates the method-forward scaffold while permitting registered locked placeholders. Submission mode additionally requires a passed corrected production gate and zero unresolved placeholders."
        ),
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / f"manuscript_qc_{args.mode}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Scientific Reports v2 manuscript QC: {args.mode}",
        "",
        f"Status: **{'PASS' if passed else 'HOLD'}**",
        "",
        f"- Title words: {len(title_words)}",
        f"- Abstract words: {len(abstract_words)}",
        f"- Keywords: {len(keywords)}",
        f"- Registered unresolved placeholders: {len(found_all)}",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {row['check']} | {row['passed']} | {row['detail']} |"
        for row in checks
    )
    (OUTPUT_ROOT / f"manuscript_qc_{args.mode}.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not passed:
        failed = [row for row in checks if not row["passed"]]
        raise SystemExit(f"Manuscript QC is on HOLD: {failed}")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
