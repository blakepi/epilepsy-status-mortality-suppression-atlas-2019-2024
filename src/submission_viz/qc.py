from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image

from .io import ROOT, ensure_output_dirs, hpc_bundle_status, load_config, rel_path, sha256_file


def _scan_text(path: Path, phrases: list[str]) -> list[str]:
    if not path.exists() or path.suffix.lower() not in {".md", ".txt", ".csv", ".json", ".svg"}:
        return []
    lowered = path.read_text(encoding="utf-8", errors="ignore").lower()
    return [phrase for phrase in phrases if phrase.lower() in lowered]


def _docx_xml(path: Path) -> str:
    if not path.exists():
        return ""
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8", errors="ignore")


def _docx_text(path: Path) -> str:
    text = re.sub(r"<[^>]+>", " ", _docx_xml(path))
    return re.sub(r"\s+", " ", text)


def _scan_docx(path: Path, phrases: list[str]) -> list[str]:
    lowered = _docx_text(path).lower()
    return [phrase for phrase in phrases if phrase.lower() in lowered]


def _scan_xlsx(path: Path, phrases: list[str]) -> list[str]:
    if not path.exists() or path.suffix.lower() != ".xlsx":
        return []
    try:
        workbook = pd.read_excel(path, sheet_name=None, dtype=str)
    except Exception:
        return []
    lowered = "\n".join(
        "\n".join(df.fillna("").astype(str).to_numpy().ravel())
        for df in workbook.values()
    ).lower()
    return [phrase for phrase in phrases if phrase.lower() in lowered]


def _docx_stats(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    xml = _docx_xml(path)
    with zipfile.ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
    text = _docx_text(path)
    words = re.findall(r"\b[\w']+\b", text)
    return {
        "exists": True,
        "bytes": path.stat().st_size,
        "word_tables": xml.count("<w:tbl>"),
        "embedded_media": len(media),
        "paragraph_tags": xml.count("<w:p"),
        "word_count_approx": len(words),
    }


def _required_figure_paths(dirs: dict[str, Path], config: dict) -> list[Path]:
    stems = [
        "main/figure1_suppression_aware_modeling_necessity",
        "main/figure2_primary_posterior_irrs",
        "main/figure3_suppression_handling_comparison",
        "main/figure4_posterior_county_maps",
        "supplement/figureS1_convergence_gate_card",
        "supplement/figureS2_final_posterior_mrr_summary",
        "supplement/figureS3_probability_uncertainty_maps",
        "supplement/figureS4_constraint_validation_summary",
    ]
    return [dirs["figures"] / f"{stem}.{ext}" for stem in stems for ext in config["style"]["export_formats"]]


def _image_dimensions(path: Path) -> str:
    if path.suffix.lower() in {".png", ".tif", ".tiff"}:
        with Image.open(path) as im:
            w, h = im.size
        return f"{w}x{h} px"
    if path.suffix.lower() == ".svg":
        text = path.read_text(encoding="utf-8", errors="ignore")[:1000]
        viewbox = re.search(r'viewBox="([^"]+)"', text)
        if viewbox:
            return f"viewBox {viewbox.group(1)}"
        width = re.search(r'width="([^"]+)"', text)
        height = re.search(r'height="([^"]+)"', text)
        if width and height:
            return f"{width.group(1)} x {height.group(1)}"
    return "not inspected"


def _figure_inventory(required_figures: list[Path]) -> list[dict]:
    records = []
    for path in required_figures:
        record = {
            "path": str(path.relative_to(ROOT)),
            "format": path.suffix.lower().lstrip("."),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "dimensions": "missing",
        }
        if path.exists():
            try:
                record["dimensions"] = _image_dimensions(path)
            except Exception as exc:
                record["dimensions"] = f"inspection failed: {exc}"
        records.append(record)
    return records


def _submission_scan_paths(dirs: dict[str, Path]) -> list[Path]:
    paths: list[Path] = []
    if dirs["manuscript"].exists():
        paths.extend(
            p
            for p in dirs["manuscript"].rglob("*")
            if p.is_file() and p.suffix.lower() in {".docx", ".md", ".txt", ".csv", ".json"}
        )
    for root in [dirs["tables"], dirs["figures"]]:
        if root.exists():
            paths.extend(
                p
                for p in root.rglob("*")
                if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".md", ".txt", ".json", ".svg"}
            )
    package_dir = dirs["package"]
    if package_dir.exists():
        for path in package_dir.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(package_dir)
            rel_parts = {part.lower() for part in rel.parts}
            name = path.name.lower()
            if "qc" in rel_parts or "readme" in name or "manifest" in name or name.startswith("submission_qc_report"):
                continue
            if path.suffix.lower() in {".docx", ".md", ".txt", ".csv", ".xlsx", ".json", ".svg"}:
                paths.append(path)
    return sorted(set(paths))


def _color_audit() -> tuple[bool, str]:
    try:
        import numpy as np
        from colorspacious import cspace_convert
        from matplotlib.colors import to_rgb

        colors = ["#1B4F72", "#7D3C98", "#D68910", "#117864", "#B03A2E", "#566573"]
        rgb = np.array([to_rgb(c) for c in colors])
        lab = cspace_convert(rgb, "sRGB1", "CAM02-UCS")
        distances = [
            float(np.linalg.norm(lab[i] - lab[j]))
            for i in range(len(lab))
            for j in range(i + 1, len(lab))
        ]
        return min(distances) > 10, f"minimum CAM02-UCS color distance={min(distances):.1f}"
    except Exception as exc:
        return False, f"colorspacious audit unavailable: {exc}"


def _diagnostics_status(config: dict, dirs: dict[str, Path]) -> dict:
    table = dirs["tables"] / "s1_diagnostics.csv"
    status = {
        "status": "missing",
        "complete_final_per_parameter_diagnostics": False,
        "primary_rhat": config["final_wahab_handoff"]["primary_rhat"],
        "primary_ess": config["final_wahab_handoff"]["primary_ess"],
        "notes": [],
    }
    if not table.exists():
        status["notes"].append("Supplementary Table S1 CSV is missing.")
        return status
    df = pd.read_csv(table, dtype=str).fillna("")
    status["rows"] = len(df)
    required = {"R-hat", "Bulk ESS", "Tail ESS", "Diagnostic status"}
    if not required.issubset(df.columns):
        status["status"] = "failed_modern_columns_missing"
        status["notes"].append(f"Missing columns: {sorted(required - set(df.columns))}")
        return status
    blanks = df[
        (df["R-hat"].str.strip() == "")
        | (df["Bulk ESS"].str.strip() == "")
        | (df["Tail ESS"].str.strip() == "")
    ]
    if not blanks.empty:
        status["notes"].append(f"{len(blanks)} rows have blank R-hat/bulk ESS/tail ESS cells.")
    numeric = df[["R-hat", "Bulk ESS", "Tail ESS"]].apply(pd.to_numeric, errors="coerce")
    status["maximum_rhat"] = float(numeric["R-hat"].max())
    status["minimum_bulk_ess"] = float(numeric["Bulk ESS"].min())
    status["minimum_tail_ess"] = float(numeric["Tail ESS"].min())
    complete = (
        len(df) == int(config["final_wahab_handoff"]["parameter_count"])
        and numeric.notna().all().all()
        and status["maximum_rhat"] <= 1.01
        and status["minimum_bulk_ess"] >= 400
        and status["minimum_tail_ess"] >= 400
        and df["Diagnostic status"].eq("Pass").all()
    )
    status["complete_final_per_parameter_diagnostics"] = bool(complete)
    status["status"] = "complete_all_parameter_diagnostics" if complete else "failed_all_parameter_diagnostics"
    primary = df[df.apply(lambda r: "nonmetro nonadjacent" in " ".join(map(str, r.values)).lower(), axis=1)]
    if primary.empty or "1.000935" not in " ".join(primary.astype(str).to_numpy().ravel()) or "4024.4" not in " ".join(primary.astype(str).to_numpy().ravel()):
        status["status"] = "failed_primary_values_missing"
        status["notes"].append("Primary R-hat/ESS values were not found in S1.")
    return status


def _constraint_status(config: dict) -> dict:
    path = rel_path(config, "constraint_validation")
    if not path.exists():
        return {"exists": False, "failures": None}
    df = pd.read_csv(path)
    required = {"check", "labels_checked", "validation_records", "failed_records"}
    if not required.issubset(df.columns):
        return {"exists": True, "failures": None, "schema_error": sorted(required - set(df.columns))}
    return {
        "exists": True,
        "check_records": int(df["validation_records"].sum()),
        "checks": int(df["check"].nunique()),
        "chain_check_rows": int(len(df)),
        "chain_specific_labels": int(df.groupby("chain")["labels_checked"].max().sum()) if "chain" in df else None,
        "failures": int(df["failed_records"].sum()),
    }


def _production_source_status(config: dict) -> dict:
    verification_path = rel_path(config, "production_verification")
    manifest_path = verification_path.parent / "derived_artifact_manifest.csv"
    status = {
        "verification_exists": verification_path.exists(),
        "manifest_exists": manifest_path.exists(),
        "passed": False,
        "mismatches": [],
    }
    if not verification_path.exists() or not manifest_path.exists():
        return status
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    manifest = pd.read_csv(manifest_path).set_index("path")
    configured = {
        "county_posterior_summary.csv": rel_path(config, "county_posterior_summary"),
        "adjusted_rates_by_rurality.csv": rel_path(config, "adjusted_rates_table"),
        "production_constraint_validation_summary.csv": rel_path(config, "constraint_validation"),
        "parameter_diagnostics_all.csv": rel_path(config, "parameter_diagnostics"),
        "posterior_primary_summary.csv": rel_path(config, "posterior_primary_summary"),
    }
    for manifest_name, path in configured.items():
        if not path.exists() or manifest_name not in manifest.index:
            status["mismatches"].append(f"missing {manifest_name}")
            continue
        expected = str(manifest.loc[manifest_name, "sha256"])
        actual = sha256_file(path)
        if expected != actual:
            status["mismatches"].append(f"hash mismatch {manifest_name}")
    status["verification"] = verification
    status["passed"] = bool(verification.get("passed")) and not status["mismatches"]
    return status


def _expand_citations(match: str) -> set[int]:
    out: set[int] = set()
    for part in re.split(r",\s*", match.replace("–", "-")):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            if left.isdigit() and right.isdigit():
                out.update(range(int(left), int(right) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out


def _reference_crosscheck(config: dict, dirs: dict[str, Path]) -> dict:
    refs_path = rel_path(config, "references")
    listed: set[int] = set()
    if refs_path.exists():
        refs = pd.read_csv(refs_path)
        listed = {int(x) for x in refs["number"].dropna().astype(int)}
    text = ""
    for path in [dirs["manuscript"] / "manuscript_submission.md", dirs["manuscript"] / "supplement_submission.md"]:
        if path.exists():
            text += "\n" + path.read_text(encoding="utf-8", errors="ignore")
    cited: set[int] = set()
    for match in re.findall(r"\[([0-9,\s–-]+)\]", text):
        cited.update(_expand_citations(match))
    return {
        "listed": sorted(listed),
        "cited": sorted(cited),
        "uncited_listed": sorted(listed - cited),
        "cited_missing_from_list": sorted(cited - listed),
        "reference_17_cited": 17 in cited,
    }


def _all_table_inventory(dirs: dict[str, Path]) -> list[dict]:
    records = []
    if not dirs["tables"].exists():
        return records
    for path in sorted(p for p in dirs["tables"].rglob("*") if p.is_file()):
        records.append({"path": str(path.relative_to(ROOT)), "format": path.suffix.lower().lstrip("."), "bytes": path.stat().st_size})
    return records


def _write_report(report: dict, out: Path) -> None:
    lines = ["# Final Submission QC Report", "", f"Final PASS/FAIL: {'PASS' if report['passed'] else 'FAIL'}", ""]
    lines.extend(
        [
            "## Summary",
            "",
            f"- Submission-facing stale phrase count: {report['stale_phrase_count_submission_materials']}",
            f"- Diagnostics completeness status: {report['diagnostics_status']['status']}",
            f"- Constraint validation failures: {report['constraint_validation_summary'].get('failures')}",
            f"- Manuscript word count: {report['docx_word_counts'].get('manuscript', 'missing')}",
            f"- Supplement word count: {report['docx_word_counts'].get('supplement', 'missing')}",
            f"- Reference 17 cited: {report['reference_crosscheck']['reference_17_cited']}",
            "",
        ]
    )
    if report["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {item}" for item in report["failures"])
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
        lines.append("")
    lines.extend(["## Diagnostics", "", "```json", json.dumps(report["diagnostics_status"], indent=2), "```", ""])
    lines.extend(["## Constraint Validation Summary", "", "```json", json.dumps(report["constraint_validation_summary"], indent=2), "```", ""])
    lines.extend(["## Reference Cross-Check", "", "```json", json.dumps(report["reference_crosscheck"], indent=2), "```", ""])
    lines.extend(["## Figure File Inventory", ""])
    for item in report["figure_inventory"]:
        lines.append(f"- {item['path']} | {item['format']} | {item['dimensions']} | {item['bytes']:,} bytes")
    lines.extend(["", "## Table Inventory", ""])
    for item in report["table_inventory"]:
        lines.append(f"- {item['path']} | {item['format']} | {item['bytes']:,} bytes")
    lines.extend(["", "## DOCX Structural Checks", "", "```json", json.dumps(report["docx_structural_checks"], indent=2), "```", ""])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def run_qc(config: dict | None = None, exit_nonzero: bool = False) -> dict:
    config = config or load_config()
    dirs = ensure_output_dirs(config)
    failures: list[str] = []
    warnings: list[str] = []

    required_figures = _required_figure_paths(dirs, config)
    figure_inventory = _figure_inventory(required_figures)
    missing_figures = [item["path"] for item in figure_inventory if not item["exists"] or item["bytes"] == 0]
    if missing_figures:
        failures.append("Missing required figure files: " + ", ".join(missing_figures[:10]))

    for item in figure_inventory:
        if item["format"] in {"png", "tiff", "tif"} and item["exists"]:
            dims = item["dimensions"].split()[0]
            if "x" in dims:
                w, h = [int(x) for x in dims.split("x")]
                if w < 1200 or h < 900:
                    warnings.append(f"Small raster dimensions for {item['path']}: {dims}")

    required_tables = [
        "table1_data_structure_constraints.csv",
        "table2_primary_posterior_estimates.csv",
        "table3_adjusted_rates_by_rurality.csv",
        "table4_suppression_handling_comparison.csv",
        "table1_data_structure_constraints.png",
        "table2_primary_posterior_estimates.png",
        "table3_adjusted_rates_by_rurality.png",
        "table4_suppression_handling_comparison.png",
        "s1_diagnostics.csv",
        "s2_constraint_validation.csv",
        "s4_sensitivity_summaries.csv",
        "s5_county_posterior_dictionary.csv",
        "submission_tables_workbook.xlsx",
        "publication_tables.docx",
    ]
    for name in required_tables:
        path = dirs["tables"] / name
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f"Missing required table output: {path.relative_to(ROOT)}")
    table_inventory = _all_table_inventory(dirs)

    table2 = dirs["tables"] / "table2_primary_posterior_estimates.csv"
    if table2.exists():
        df = pd.read_csv(table2)
        text = " ".join(map(str, df.to_numpy().ravel()))
        if not all(x in text for x in ["1.23", "1.17–1.30", "1.001", "4024.4", "8819.1"]):
            failures.append("Table 2 does not contain final primary values 1.23, 1.17–1.30, rank-normalized R-hat 1.001, bulk ESS 4024.4, and tail ESS 8819.1.")
        if "primary_rurality" in text or "svi_quartile" in text:
            failures.append("Main Table 2 leaks raw parameter names.")

    table4 = dirs["tables"] / "table4_suppression_handling_comparison.csv"
    if table4.exists():
        df4 = pd.read_csv(table4)
        if "Nonmetro nonadjacent mortality rate ratio" not in df4.columns:
            failures.append("Table 4 does not use the requested mortality-rate-ratio column heading.")
        if "1.17-1.30" in " ".join(map(str, df4.to_numpy().ravel())):
            failures.append("Table 4 contains a hyphenated Bayesian interval.")

    phrases = config.get("stale_phrase_blocklist", [])
    hits: list[tuple[Path, list[str]]] = []
    for path in _submission_scan_paths(dirs):
        if path.suffix.lower() == ".docx":
            found = _scan_docx(path, phrases)
        elif path.suffix.lower() == ".xlsx":
            found = _scan_xlsx(path, phrases)
        else:
            found = _scan_text(path, phrases)
        if found:
            hits.append((path, found))
    stale_phrase_count = sum(len(found) for _, found in hits)
    if hits:
        failures.append("Stale submission-facing language found: " + "; ".join(f"{p.relative_to(ROOT)} -> {found}" for p, found in hits[:10]))

    docx_paths = {
        "manuscript": dirs["manuscript"] / "manuscript_submission.docx",
        "supplement": dirs["manuscript"] / "supplement_submission.docx",
    }
    docx_structural_checks = {name: _docx_stats(path) for name, path in docx_paths.items()}
    docx_word_counts = {
        name: stats.get("word_count_approx", "missing")
        for name, stats in docx_structural_checks.items()
    }
    if docx_structural_checks["manuscript"].get("word_tables", 0) < 4:
        failures.append("Main manuscript DOCX has fewer than four native Word tables.")
    if docx_structural_checks["manuscript"].get("embedded_media", 0) < 4:
        failures.append("Main manuscript DOCX has fewer than four embedded figures.")
    if docx_structural_checks["supplement"].get("word_tables", 0) < 7:
        failures.append("Supplement DOCX has fewer than seven native Word tables.")

    diagnostics_status = _diagnostics_status(config, dirs)
    if diagnostics_status["status"] != "complete_all_parameter_diagnostics":
        failures.append(f"Supplementary Table S1 diagnostics are incomplete or failed: {diagnostics_status['status']}")
    if any("blank" in note.lower() for note in diagnostics_status.get("notes", [])):
        failures.append("Supplementary Table S1 contains blank R-hat/ESS cells.")

    constraint_status = _constraint_status(config)
    if not constraint_status.get("exists"):
        failures.append("Constraint validation file is missing.")
    elif constraint_status.get("failures", 1) != 0:
        failures.append("Constraint validation contains failed records.")

    production_source_status = _production_source_status(config)
    if not production_source_status["passed"]:
        failures.append(f"Production-source provenance failed: {production_source_status['mismatches']}")

    reference_crosscheck = _reference_crosscheck(config, dirs)
    if reference_crosscheck["cited_missing_from_list"]:
        failures.append(f"Citations missing from reference list: {reference_crosscheck['cited_missing_from_list']}")
    if reference_crosscheck["uncited_listed"]:
        failures.append(f"Listed references not cited: {reference_crosscheck['uncited_listed']}")
    if not reference_crosscheck["reference_17_cited"]:
        failures.append("Reference 17 is not cited.")

    ok_color, color_detail = _color_audit()
    if not ok_color:
        warnings.append(color_detail)

    package_dir = dirs["package"]
    if package_dir.exists():
        forbidden_package_names = []
        for path in package_dir.rglob("*"):
            if path.is_file():
                name = path.name.lower()
                if any(token in name for token in ["manuscript_submission_revised", "supplement_submission_revised", "manuscript_submission(1)", "supplement_submission(1)", "old", "stale", "round4", "round5"]):
                    forbidden_package_names.append(str(path.relative_to(ROOT)))
        if forbidden_package_names:
            failures.append("Package contains forbidden older/stale filenames: " + ", ".join(forbidden_package_names[:10]))
        if not (package_dir / "manuscript_submission_FINAL.docx").exists():
            failures.append("Package is missing manuscript_submission_FINAL.docx.")
        if not (package_dir / "supplement_submission_FINAL.docx").exists():
            failures.append("Package is missing supplement_submission_FINAL.docx.")
        if not any(p.name.lower().startswith("strobe_checklist") for p in package_dir.rglob("*") if p.is_file()):
            failures.append("Package is missing a STROBE checklist.")

    report = {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "stale_phrase_count_submission_materials": stale_phrase_count,
        "stale_phrase_hits": [
            {"path": str(path.relative_to(ROOT)), "phrases": found}
            for path, found in hits
        ],
        "diagnostics_status": diagnostics_status,
        "constraint_validation_summary": constraint_status,
        "production_source_status": production_source_status,
        "figure_inventory": figure_inventory,
        "table_inventory": table_inventory,
        "reference_crosscheck": reference_crosscheck,
        "docx_structural_checks": docx_structural_checks,
        "docx_word_counts": docx_word_counts,
        "hpc_status_internal": hpc_bundle_status(config),
        "color_audit": color_detail,
    }
    final_md = dirs["qc"] / "SUBMISSION_QC_REPORT_FINAL.md"
    final_json = dirs["qc"] / "SUBMISSION_QC_REPORT_FINAL.json"
    _write_report(report, final_md)
    final_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Compatibility aliases for existing scripts.
    _write_report(report, dirs["qc"] / "SUBMISSION_QC_REPORT_REVISED.md")
    (dirs["qc"] / "SUBMISSION_QC_REPORT_REVISED.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_report(report, dirs["qc"] / "SUBMISSION_QC_REPORT.md")
    (dirs["qc"] / "SUBMISSION_QC_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if exit_nonzero and failures:
        raise SystemExit(1)
    return report
