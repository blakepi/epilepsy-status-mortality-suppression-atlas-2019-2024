from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = (
    ROOT
    / "manuscript"
    / "scientific_reports_v2"
    / "manuscript_draft_nonfinal.md"
)
OUTPUT_ROOT = ROOT / "outputs" / "scientific_reports_v2" / "citation_qc"
REFERENCE_LINE = re.compile(r"^(\d+)\.\s", re.MULTILINE)
CITATION_GROUP = re.compile(r"\[(\d+(?:\s*[–-]\s*\d+)?(?:\s*,\s*\d+(?:\s*[–-]\s*\d+)?)*)\]")

# These are semantic citation corrections, not blind numeric shifting. The
# working reference list places Quick 2019 at 11, the four applied epilepsy
# sources at 12–15, the COVID coding source at 16, and county adjacency at 17.
NORMALIZATIONS = {
    "their uncertainty [12].": "their uncertainty [11].",
    "rural populations [13–16].": "rural populations [12–15].",
    "primary likelihood [3,17].": "primary likelihood [3,16].",
    "county-adjacency file [18].": "county-adjacency file [17].",
}


def expanded_citation_numbers(group: str) -> list[int]:
    numbers: list[int] = []
    for token in group.split(","):
        token = token.strip().replace("–", "-")
        if "-" in token:
            left, right = [int(value.strip()) for value in token.split("-", 1)]
            if right < left:
                raise ValueError(f"Descending citation range: {token}")
            numbers.extend(range(left, right + 1))
        else:
            numbers.append(int(token))
    return numbers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    original = MANUSCRIPT.read_text(encoding="utf-8")
    normalized = original
    applied: list[dict[str, str]] = []
    for old, new in NORMALIZATIONS.items():
        if old in normalized:
            normalized = normalized.replace(old, new)
            applied.append({"old": old, "new": new})

    reference_section = normalized.split("## References", 1)[1]
    locked_section = ""
    if "## Locked placeholders" in reference_section:
        reference_section, locked_section = reference_section.split(
            "## Locked placeholders",
            1,
        )
    reference_numbers = [int(value) for value in REFERENCE_LINE.findall(reference_section)]
    expected = list(range(1, max(reference_numbers, default=0) + 1))
    references_contiguous = reference_numbers == expected

    body = normalized.split("## References", 1)[0]
    cited_numbers: list[int] = []
    for match in CITATION_GROUP.finditer(body):
        cited_numbers.extend(expanded_citation_numbers(match.group(1)))
    maximum_reference = max(reference_numbers, default=0)
    out_of_range = sorted(
        {
            number
            for number in cited_numbers
            if number < 1 or number > maximum_reference
        }
    )
    unresolved_old_fragments = [old for old in NORMALIZATIONS if old in normalized]
    passed = bool(
        references_contiguous
        and maximum_reference > 0
        and not out_of_range
        and not unresolved_old_fragments
    )

    if args.write and normalized != original:
        MANUSCRIPT.write_text(normalized, encoding="utf-8")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "write_mode": bool(args.write),
        "passed": passed,
        "manuscript_changed": normalized != original,
        "normalizations_applied": applied,
        "reference_count": maximum_reference,
        "references_contiguous": references_contiguous,
        "citation_groups": len(CITATION_GROUP.findall(body)),
        "cited_numbers": sorted(set(cited_numbers)),
        "out_of_range_citations": out_of_range,
        "unresolved_old_fragments": unresolved_old_fragments,
        "interpretation_boundary": (
            "This audit verifies numeric citation integrity and a small set of semantic mappings in the nonfinal working draft. Bibliographic metadata and DOI resolution remain separate final-package gates."
        ),
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "citation_qc.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Scientific Reports v2 citation QC",
        "",
        f"Status: **{'PASS' if passed else 'HOLD'}**",
        "",
        f"- References: {maximum_reference}",
        f"- Numeric citation groups: {report['citation_groups']}",
        f"- Manuscript changed: {report['manuscript_changed']}",
        f"- Out-of-range citations: {out_of_range}",
        f"- Unresolved semantic corrections: {unresolved_old_fragments}",
    ]
    (OUTPUT_ROOT / "citation_qc.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not passed:
        raise SystemExit(f"Citation QC is on HOLD: {report}")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
