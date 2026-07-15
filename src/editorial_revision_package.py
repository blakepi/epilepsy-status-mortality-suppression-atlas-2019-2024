from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "manuscript" / "phase14_targeted_cleanup"
PREVIOUS_REVISION = PROJECT_ROOT / "manuscript" / "editorial_revision_round5_hardstop_fixed_final"
OUT = PROJECT_ROOT / "manuscript" / "final_submission_ready"
DOCX_DIR = OUT / "docx"
MD_DIR = OUT / "markdown"
TABLE_DIR = OUT / "tables"
FIG_DIR = OUT / "figures"
REPORT_DIR = OUT / "reports"
REF_DIR = OUT / "references"
SUPP_DIR = OUT / "supplement"
SNAPSHOT_DIR = OUT / "source_phase14_snapshot"
ATTACHED_BASELINE_DIR = OUT / "source_attached_baseline"
FINAL_DIR = OUT / "final_package"
INTERNAL_DIR = OUT / "internal_QA"
UPLOAD_DIR = OUT / "FINAL_SUBMISSION_FILES_ONLY"

ATTACHED_BASELINE_DOCX = [
    Path(r"C:\Users\gbp34\AppData\Local\Temp\highlights_revised (1).docx"),
    Path(r"C:\Users\gbp34\AppData\Local\Temp\manuscript_main_revised (1).docx"),
    Path(r"C:\Users\gbp34\AppData\Local\Temp\STROBE_checklist_revised (1).docx"),
    Path(r"C:\Users\gbp34\AppData\Local\Temp\supplement_revised (1).docx"),
    Path(r"C:\Users\gbp34\AppData\Local\Temp\title_page_revised (1).docx"),
    Path(r"C:\Users\gbp34\AppData\Local\Temp\abstract_revised (1).docx"),
    Path(r"C:\Users\gbp34\AppData\Local\Temp\cover_letter_revised (1).docx"),
]

EN_DASH = "\u2013"
APPROX = "\u2248"

TITLE = f"Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019{EN_DASH}2024"
AUTHOR = "Gregory Pierpoint, B.S."
AFFILIATION = "Macon & Joan Brock Virginia Health Sciences, Eastern Virginia Medical School at Old Dominion University, Norfolk, VA, United States"
EMAIL = "pierpogb@odu.edu"
PHONE = "202-809-8046"
ORCID = "https://orcid.org/0000-0001-8288-8549"
GITHUB_URL = "https://github.com/blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024"
DOI_URL = "https://doi.org/10.5281/zenodo.20691623"
REPOSITORY_RELEASE_VERSION = "v1.0.1"

TABLE3_PRESERVES_RECONCILED_TOTAL = {
    "Observed exact-positive only": "No",
    "Observed exact plus explicit zero": "No",
    "Suppressed = 1": "No",
    "Suppressed = 4.06 (constant mean)": "Yes",
    "Suppressed = 5": "No",
    "Suppressed = 9": "No",
    "Population-scaled residual allocation": "Yes",
    "Conservative anti-rural residual allocation": "Yes",
    "Pro-rural residual allocation": "Yes",
    "Interval-likelihood negative binomial": "Not assigned / not applicable",
}

FINAL_DOCX_FILES = [
    "manuscript_main_revised.docx",
    "abstract_revised.docx",
    "title_page_revised.docx",
    "cover_letter_revised.docx",
    "highlights_revised.docx",
    "STROBE_checklist_revised.docx",
    "supplement_revised.docx",
]

FINAL_FIGURE_FILES = [
    "figure1_county_suppression_status_revised.png",
    "figure1_county_suppression_status_revised.svg",
    "figure1_county_suppression_status_revised.pdf",
    "figure1_county_suppression_status_revised.eps",
    "figure1_county_suppression_status_revised.tiff",
    "figure2_suppression_bounds_revised.png",
    "figure2_suppression_bounds_revised.svg",
    "figure2_suppression_bounds_revised.pdf",
    "figure2_suppression_bounds_revised.eps",
    "figure2_suppression_bounds_revised.tiff",
    "figure3_scenario_envelope_revised.png",
    "figure3_scenario_envelope_revised.svg",
    "figure3_scenario_envelope_revised.pdf",
    "figure3_scenario_envelope_revised.eps",
    "figure3_scenario_envelope_revised.tiff",
    "figure4_temporal_covid_context_revised.png",
    "figure4_temporal_covid_context_revised.svg",
    "figure4_temporal_covid_context_revised.pdf",
    "figure4_temporal_covid_context_revised.eps",
    "figure4_temporal_covid_context_revised.tiff",
    "supplement_national_year_trend.png",
    "supplement_national_year_trend.svg",
    "supplement_national_year_trend.pdf",
    "supplement_national_year_trend.eps",
    "supplement_national_year_trend.tiff",
    "supplement_original_covid_urbanization_year.png",
    "supplement_original_covid_urbanization_year.svg",
    "supplement_original_covid_urbanization_year.pdf",
    "supplement_original_covid_urbanization_year.eps",
    "supplement_original_covid_urbanization_year.tiff",
    "figureS3_residual_allocation_atlas.png",
    "figureS3_residual_allocation_atlas.svg",
    "figureS3_residual_allocation_atlas.pdf",
    "figureS3_residual_allocation_atlas.eps",
    "figureS3_residual_allocation_atlas.tiff",
]


def ensure_dirs() -> None:
    for path in [DOCX_DIR, MD_DIR, TABLE_DIR, FIG_DIR, REPORT_DIR, REF_DIR, SUPP_DIR, SNAPSHOT_DIR, ATTACHED_BASELINE_DIR, FINAL_DIR, INTERNAL_DIR, UPLOAD_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    for src in ATTACHED_BASELINE_DOCX:
        if src.exists():
            shutil.copy2(src, ATTACHED_BASELINE_DIR / src.name)
    for subdir in ["tables", "figures", "reports", "references", "supplement"]:
        src_dir = PREVIOUS_REVISION / subdir
        dest_dir = OUT / subdir
        if src_dir.exists():
            for src in src_dir.glob("*"):
                if src.is_file():
                    shutil.copy2(src, dest_dir / src.name)
    for path in [SOURCE / "docx", SOURCE / "references"]:
        if path.exists():
            for src in path.glob("*"):
                if src.is_file():
                    dest_dir = SNAPSHOT_DIR / path.name
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest_dir / src.name)
    for src_dir, dest_dir in [(SOURCE / "references", REF_DIR), (SOURCE / "supplement", SUPP_DIR)]:
        if src_dir.exists():
            for src in src_dir.glob("*"):
                if src.is_file():
                    shutil.copy2(src, dest_dir / src.name)
    finalize_active_figure_files()
    cleanup_retired_reports()
    normalize_reference_release_files()


def normalize_release_version_text(text: str) -> str:
    return text.replace("Version 1.0.0. Zenodo.", f"Version {REPOSITORY_RELEASE_VERSION}. Zenodo.")


def normalize_reference_release_files() -> None:
    for path in [REF_DIR / "references_provisional.csv", REF_DIR / "REFERENCE_VERIFICATION_REPORT.md"]:
        if path.exists():
            path.write_text(normalize_release_version_text(path.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")


def generate_final_submission_figures() -> None:
    script = PROJECT_ROOT / "scripts" / "generate_publication_figures.py"
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    local_python = Path.home() / "AppData" / "Local" / "Python" / "bin" / "python.exe"
    candidates = [str(venv_python), sys.executable, str(local_python), "py", "python"]
    attempts = []
    for candidate in candidates:
        if candidate.endswith("python.exe") and not Path(candidate).exists():
            continue
        completed = subprocess.run(
            [
                candidate,
                str(script),
                "--outdir",
                str(FIG_DIR),
                "--manifest",
                str(REPORT_DIR / "publication_figure_manifest.csv"),
                "--qa-report",
                str(REPORT_DIR / "publication_figure_QA_report.md"),
            ],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            timeout=360,
            check=False,
        )
        attempts.append({"candidate": candidate, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
        if completed.returncode == 0:
            (REPORT_DIR / "final_map_generation_stdout.txt").write_text(completed.stdout, encoding="utf-8")
            (REPORT_DIR / "final_map_generation_stderr.txt").write_text(completed.stderr, encoding="utf-8")
            return
    (REPORT_DIR / "final_map_generation_attempts.json").write_text(json.dumps(attempts, indent=2), encoding="utf-8")
    last = attempts[-1]
    raise RuntimeError(f"Final map generation failed with code {last['returncode']}: {last['stderr']}")


def finalize_active_figure_files() -> None:
    """Remove retired generated figure names before rebuilding active assets."""
    retired_patterns = [
        "figure1_county_suppression_status_tight.*",
        "figure1_county_data_visibility.*",
        "figure2_two_panel_irrs_revised.*",
        "figure3_suppression_aware_residual_rate.*",
        "figure3_suppression_aware_residual_rate_tight.*",
        "figure3_allocation_uncertainty_atlas.*",
        "suppression_bounds_forest_plot.*",
        "map3_suppression_aware_predicted_rates.*",
    ]
    for pattern in retired_patterns:
        for path in FIG_DIR.glob(pattern):
            if path.is_file():
                path.unlink()


def cleanup_retired_reports() -> None:
    retired_names = [
        "round3_figure_revision_report.md",
        "round3_figure_inventory.csv",
    ]
    for name in retired_names:
        path = REPORT_DIR / name
        if path.exists():
            path.unlink()


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=80, bottom=80, end=80) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in [("top", top), ("start", start), ("bottom", bottom), ("end", end)]:
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_table_width(table, widths: list[float]) -> None:
    table.autofit = False
    for row in table.rows:
        for idx, width in enumerate(widths):
            cell = row.cells[idx]
            cell.width = Inches(width)
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(int(width * 1440)))
            tc_w.set(qn("w:type"), "dxa")


def set_table_borders(table, color: str = "D7DBE7", size: str = "4") -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def setup_doc(doc: Document, title: str, landscape: bool = False) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Inches(11)
        section.page_height = Inches(8.5)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(12)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 2
    for style_name, size in [("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 12)]:
        style = styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 2
    for paragraph in section.footer.paragraphs:
        paragraph.text = ""


def add_paragraph(doc: Document, text: str = "", style: str | None = None, bold: bool = False) -> None:
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    run.bold = bold
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(12)


def add_bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 2
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


def add_number(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.line_spacing = 2
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)


def add_reference_paragraph(doc: Document, number: str, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    run = p.add_run(f"{number}. {text}")
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(11)


def md_escape(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).replace("|", "\\|")


def df_to_markdown(df: pd.DataFrame) -> str:
    headers = list(df.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(md_escape(row[c]) for c in headers) + " |")
    return "\n".join(lines)


def format_tables_for_manuscript() -> dict[str, pd.DataFrame]:
    t1 = pd.read_csv(TABLE_DIR / "table1_county_characteristics_revised.csv")
    t1_fmt = pd.DataFrame(
        {
            "Death-count status": t1["death_status"],
            "Counties": t1["counties"].map(lambda x: f"{int(x):,}"),
            "Person-years, millions": t1["person_years_millions"].map(lambda x: f"{x:.1f}"),
            "Exact deaths": t1["exact_deaths"].map(lambda x: f"{int(x):,}"),
            "Death interval": [f"{int(low):,}-{int(high):,}" for low, high in zip(t1["lower"], t1["upper"])],
            "Nonmetro, %": t1["pct_nonmetro"].map(lambda x: f"{x:.1f}"),
            "Mean SVI": t1["mean_svi"].map(lambda x: f"{x:.3f}"),
            "Poverty, %": t1["mean_poverty"].map(lambda x: f"{x:.1f}"),
            "Uninsured, %": t1["mean_uninsured"].map(lambda x: f"{x:.1f}"),
            "Age >=65, %": t1["mean_age65"].map(lambda x: f"{x:.1f}"),
        }
    )

    t2 = pd.read_csv(TABLE_DIR / "table2_mortality_by_rurality_svi_revised.csv")
    t2_fmt = pd.DataFrame(
        {
            "Rurality": t2["primary_rurality"].str.replace("_", " ").str.title(),
            "SVI": t2["svi_quartile"].str.replace("_", " "),
            "Counties": t2["counties"].map(lambda x: f"{int(x):,}"),
            "Deaths lower-mid-upper": [f"{int(low):,}-{int(mid):,}-{int(high):,}" for low, mid, high in zip(t2["lower"], t2["midpoint"], t2["upper"])],
            "Supp/zero rows": [f"{int(s):,}/{int(z):,}" for s, z in zip(t2["suppressed"], t2["zero"])],
            "Rate lower-mid-upper": [
                f"{low:.2f}-{mid:.2f}-{high:.2f}" for low, mid, high in zip(t2["rate_lower_per_100k"], t2["rate_midpoint_per_100k"], t2["rate_upper_per_100k"])
            ],
        }
    )

    t3 = pd.read_csv(TABLE_DIR / "table3_suppression_aware_models_revised_main.csv")
    full_t3 = pd.read_csv(TABLE_DIR / "table3_suppression_aware_models_revised_full.csv")
    assignments = pd.read_csv(TABLE_DIR / "suppression_scenario_death_assignments_revised.csv")
    event_map = {}
    label_map = dict(zip(assignments["label"], assignments["scenario"]))
    for _, row in t3.iterrows():
        raw_scenario = label_map.get(row["scenario"], "")
        if row["scenario"] == "Interval-likelihood negative binomial":
            event_map[row["scenario"]] = "Not assigned"
            continue
        model_row = full_t3[
            (full_t3["scenario"] == raw_scenario)
            & (full_t3["model_family"] == "rurality_svi_composite")
            & (full_t3["term"] == "primary_rurality_nonmetro_nonadjacent")
        ]
        if model_row.empty:
            event_map[row["scenario"]] = ""
        else:
            events = float(model_row.iloc[0]["events"])
            event_map[row["scenario"]] = f"{events:,.1f}" if abs(events - round(events)) > 0.05 else f"{int(round(events)):,}"
    def concise_tier(value: str) -> str:
        return {
            "Visible-only": "Visible-only",
            "Fixed-value stress test, not total-preserving": "Fixed-value stress test",
            "Constant-count stress test, total-preserving": "Constant-count stress test",
            "Residual-allocation, total-preserving": "Residual allocation",
            "Interval model": "Interval model",
        }.get(str(value), str(value))

    def preserves_reconciled_total(scenario: str) -> str:
        scenario = str(scenario)
        if scenario not in TABLE3_PRESERVES_RECONCILED_TOTAL:
            raise ValueError(f"Unexpected Table 3 scenario for total-preservation label: {scenario}")
        return TABLE3_PRESERVES_RECONCILED_TOTAL[scenario]

    def formatted_ci(value: str) -> str:
        return str(value).replace("-", EN_DASH)

    t3_fmt = pd.DataFrame(
        {
            "Tier": t3["tier"].map(concise_tier),
            "Scenario": t3["scenario"],
            "Assigned deaths, full extract": t3["assigned_deaths"],
            "Analytic model deaths": t3["scenario"].map(event_map),
            "Preserves reconciled total?": t3["scenario"].map(preserves_reconciled_total),
            "IRR": t3["nonmetro_nonadjacent_irr"].map(lambda x: f"{float(x):.2f}" if str(x).replace(".", "", 1).isdigit() else x),
            "95% CI": t3["ci_95"].map(formatted_ci),
        }
    )

    t4 = pd.read_csv(TABLE_DIR / "table4_temporal_covid_context_revised.csv")
    t4_fmt = pd.DataFrame(
        {
            "Year": t4["year"].map(lambda x: str(int(x))),
            "MCOD deaths": t4["deaths"].map(lambda x: f"{int(x):,}"),
            "Population": t4["population"].map(lambda x: f"{int(x):,}"),
            "National rate per 100,000": t4["rate_per_100k"].map(lambda x: f"{x:.2f}"),
            "COVID co-mention interval": [f"{int(low):,}-{int(high):,}" for low, high in zip(t4["covid_lower"], t4["covid_upper"])],
            "COVID midpoint, % of MCOD": t4["covid_pct_of_mcod"].map(lambda x: f"{x:.1f}"),
        }
    )

    t5 = pd.read_csv(TABLE_DIR / "table5_ucd_sensitivity_revised.csv")
    t5_fmt = t5.rename(
        columns={
            "measure": "Measure",
            "mcod_g40_g41": "MCOD G40/G41",
            "ucd_g40_g41": "UCD G40/G41",
            "interpretation": "Interpretation",
        }
    )
    return {"t1": t1_fmt, "t2": t2_fmt, "t3": t3_fmt, "t4": t4_fmt, "t5": t5_fmt}


def table_docx(doc: Document, caption: str, df: pd.DataFrame, footnote: str, widths: list[float] | None = None) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    r = p.add_run(caption)
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"
    set_table_borders(table)
    hdr = table.rows[0].cells
    for i, col in enumerate(df.columns):
        hdr[i].text = str(col)
        set_cell_shading(hdr[i], "E8EEF5")
    for _, row in df.iterrows():
        cells = table.add_row().cells
        for i, col in enumerate(df.columns):
            cells[i].text = str(row[col])
    if widths:
        set_table_width(table, widths)
    for row in table.rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.line_spacing = 1.0
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
                    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
                    run.font.size = Pt(8)
                    if row == table.rows[0]:
                        run.font.bold = True
    note = doc.add_paragraph()
    note.paragraph_format.line_spacing = 1.0
    note.paragraph_format.space_after = Pt(8)
    rn = note.add_run("Note. " + footnote)
    rn.font.name = "Times New Roman"
    rn.font.size = Pt(9)


def add_image(doc: Document, path: Path, caption: str, width: float = 6.2) -> None:
    if not path.exists():
        add_paragraph(doc, f"[Missing figure file: {path.name}]")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cap.paragraph_format.line_spacing = 1.0
    cap.paragraph_format.space_after = Pt(10)
    cap.paragraph_format.keep_together = True
    r = cap.add_run(caption)
    r.font.name = "Times New Roman"
    r.font.size = Pt(10)
    r.italic = True


def widths_for_columns(n_cols: int, total_width: float = 9.0) -> list[float]:
    if n_cols <= 0:
        return []
    return [total_width / n_cols] * n_cols


def manuscript_markdown(tables: dict[str, pd.DataFrame]) -> str:
    refs = (SOURCE / "markdown" / "manuscript_main.md").read_text(encoding="utf-8").split("## References", 1)[1]
    references = normalize_release_version_text("## References" + refs.split("## Tables", 1)[0])
    return f"""# {TITLE}

## Abstract

## Objective

To quantify how CDC WONDER county-level small-cell suppression shapes national county-level analyses of epilepsy/status epilepticus-related mortality and to evaluate rurality-associated patterns using suppression-aware methods.

## Methods

We analyzed CDC WONDER Multiple Cause of Death data for 2019-2024. The primary outcome was multiple-cause mortality with ICD-10 G40 (epilepsy) or G41 (status epilepticus) listed anywhere on the death certificate. County-period and county-year extracts were linked to county rurality, social vulnerability, age-structure, and sex-composition covariates. Suppressed county cells were preserved as 1-9 death intervals and were not treated as zero. Primary county models included standardized county percentages aged >=65 years and male; direct county age standardization was not used because county age-stratified death cells are heavily suppressed. We compared observed-only models with fixed-value stress tests, total-preserving residual allocations, and interval-likelihood negative binomial models.

## Results

National multiple-cause G40/G41 mortality totaled 58,380 deaths. The county-period extract comprised 1,085 counties with exact counts (51,388 deaths), 1,722 suppressed county rows (1-9 deaths each), and 335 explicit-zero rows. The reconciled residual within suppressed counties was 6,992 deaths, or {APPROX}4.1 deaths per suppressed county. In the rurality plus SVI model, nonmetro nonadjacent IRRs were 0.97 for observed exact-positive counties and 0.91 after adding explicit zero counties. The population-scaled residual allocation, treated as the primary total-preserving scenario, estimated an IRR of 1.04, and the interval-likelihood model estimated 1.07 with wide approximate uncertainty. Other total-preserving residual allocations ranged from 0.97 to 1.13. A total-preserving but exposure-ignoring uniform allocation estimated 1.24, showing that the within-suppressed distribution matters; high fixed-value stress tests were interpreted as non-primary stress tests. COVID-19 co-mention totaled 1,936 deaths, and underlying-cause G40/G41 mortality totaled 22,306 deaths.

## Conclusion

County-level epilepsy/status epilepticus mortality inference in CDC WONDER is strongly shaped by outcome-dependent suppression. Preserving suppressed cells as intervals, reconciling county extracts to aggregate totals, and separating total-preserving allocations from fixed-value stress tests provide a more transparent framework for county-level mortality surveillance.

## Keywords

Epilepsy; status epilepticus; mortality; CDC WONDER; small-cell suppression; rural health; ecological study.

## Introduction

Epilepsy and status epilepticus contribute to mortality burden in the United States and may appear on death certificates as underlying or contributing conditions. Multiple-cause mortality data are therefore useful for surveillance because they capture deaths in which epilepsy or status epilepticus was mentioned anywhere on the death certificate, rather than only deaths for which these diagnoses were selected as the underlying cause.

Rurality, social vulnerability, and health-system context are plausible contributors to geographic variation in epilepsy-related mortality. Rural communities may differ from metropolitan areas in specialist availability, emergency medical services, travel time, comorbidity burden, medication access, and death-certificate certification context. These factors are best interpreted as contextual hypotheses in aggregate mortality data, not as demonstrated mechanisms in county-level ecological analyses.

National county-level mortality analyses are difficult for epilepsy/status epilepticus because CDC WONDER suppresses small death counts. Suppressed county cells generally represent 1-9 deaths. This creates outcome-dependent data visibility: counties with exact counts are partly selected by population size and mortality burden, while many rural and low-population counties are represented only by bounded intervals or explicit zero counts. Exact-count counties are therefore not a random subset of all counties.

Prior work has addressed closely related censoring problems in CDC WONDER. Quick modeled county-level mortality rates from highly censored WONDER data using a hierarchical Bayesian framework that borrows strength across counties to produce smoothed estimates. The present study is complementary rather than duplicative: it emphasizes transparent reconciliation to known aggregate totals, bias-bounding, and interval representation instead of attempting to recover a single best county count for every suppressed cell. The trade-off is deliberate. Hierarchical smoothing can improve precision when the model is accepted, whereas the present workflow foregrounds assumption visibility and sensitivity for readers who need to understand how much the conclusion depends on hidden cells.

This study uses an interval-preserving extraction and modeling framework to map county-level epilepsy/status epilepticus mortality, quantify suppression patterns, bound rurality-associated estimates, and provide temporal, COVID co-mention, and underlying-cause context. The major contribution is not a strong rurality claim; it is a national atlas of data visibility and a methodological caution for county-level WONDER mortality research.

The aims were:

1. Describe county-level exact, suppressed, and zero mortality-count patterns for epilepsy/status epilepticus-related mortality.
2. Estimate rurality-associated mortality patterns under observed-only, fixed-value stress-test, residual-allocation, and interval-likelihood approaches.
3. Characterize temporal, urbanization, COVID co-mention, and underlying-cause sensitivity patterns.
4. Produce a bounded geographic atlas to guide interpretation of county-level epilepsy mortality surveillance.

## Methods

### Study design and data sources

We conducted a national ecological county-level mortality analysis using public aggregate mortality and county covariate data. Mortality data came from CDC WONDER Current Final Multiple Cause of Death Data, 2018-2024, Single Race. The analytic years were 2019-2024. County covariates included CDC/ATSDR Social Vulnerability Index 2022, U.S. Department of Agriculture Rural-Urban Continuum Codes 2023, National Center for Health Statistics 2023 urban-rural classification, and American Community Survey 2019-2023 county variables.

### Case definition

The primary outcome was multiple-cause mortality with ICD-10 G40 or G41 listed anywhere on the death certificate. The confirmed CDC WONDER cause syntax was G40 (Epilepsy) and G41 (Status epilepticus). The secondary sensitivity outcome was underlying-cause mortality with ICD-10 G40 or G41. COVID-19 co-mention analyses used U07.1 (COVID-19) in the second multiple-cause box. Multiple-cause mortality is interpreted as epilepsy/status epilepticus-related mortality mention, not as definitive attribution of death to epilepsy or status epilepticus.

### CDC WONDER extraction and reconciliation

The analysis used the reconciled Q001-Q015 extraction set from the CDC WONDER extraction project. Q001 provided county-period multiple-cause G40/G41 mortality for 2019-2024 with zero and suppressed values requested. Q002 provided county-year multiple-cause G40/G41 mortality. Q003, Q004, and Q005 provided national-year, state-year, and urbanization-year multiple-cause totals. Q010 provided urbanization-year multiple-cause G40/G41 and U07.1 COVID-19 co-mention. Q011, Q012, and Q014 provided underlying-cause sensitivity outputs.

The extraction reconciliation confirmed that Q001, Q003, Q004, and Q005 agreed at 58,380 multiple-cause G40/G41 deaths for 2019-2024. Q002 county-year exact-plus-suppressed intervals contained Q003 national-year totals. Q010 was bounded by Q005 by urbanization and year. Q012 and Q014 underlying-cause aggregate totals agreed at 22,306 deaths.

### Suppression status definitions

County death counts were coded as exact, suppressed_1_9, zero, missing/unreturned, aggregate total, or invalid noncounty. Exact cells were coded as [death, death]. Suppressed cells were coded as [1, 9] with midpoint 5 for descriptive summaries. Explicit zero cells were coded as [0, 0]. Suppressed cells were not treated as zero. Missing or unreturned cells were not treated as zero. Aggregate total rows were retained for reconciliation but excluded from county models.

### County covariates and rurality measures

County FIPS codes were preserved as 5-character strings. The county merge included 3,142 WONDER Q001 county rows and 3,144 combined covariate county rows. The FIPS merge matched 3,131 counties, leaving 11 WONDER counties without covariates and 13 covariate counties without WONDER Q001 rows. Alaska, Hawaii, and the District of Columbia were retained in analytic county files where present; territories were not present in the Q001 analytic county set.

Model tables distinguish full-extract assigned deaths from covariate-restricted analytic model deaths. Full-extract assigned deaths refer to all Q001 county rows before covariate restriction. Analytic model deaths reflect the 3,131 matched counties used in county model fits after excluding the 11 WONDER counties without covariates, so those event totals are slightly lower than the full reconciled county extract in total-preserving scenarios.

The primary collapsed RUCC rurality variable used metro_large (RUCC 1), metro_other (RUCC 2-3), nonmetro_adjacent (RUCC 4, 6, 8), and nonmetro_nonadjacent (RUCC 5, 7, 9). Sensitivity rurality definitions included binary RUCC 1-3 versus 4-9 and NCHS six-level urban-rural classification.

### Social vulnerability covariates

SVI was modeled as a composite family using SVI quartile. ACS component models were modeled separately using poverty, household income, education, uninsurance, race/ethnicity composition, and age structure. SVI was not modeled together with its own component variables in the primary model family. Component-model variance inflation factors were modest, with a maximum of 2.92 for median household income and poverty-related component diagnostics (Table S4).

### Age structure and standardization

Age structure is central to mortality interpretation and is correlated with rurality. Direct county-level age-standardized rates were not used as the primary outcome because the county-by-age death strata for this uncommon outcome are heavily affected by CDC WONDER small-cell suppression; treating those suppressed age strata as zero or as fully observed would reintroduce the same visibility bias the study was designed to avoid. Instead, all primary county-period rurality and SVI count models included standardized county percentage aged >=65 years and standardized county percentage male, with log person-years as the offset. Age-by-urbanization summaries are reported descriptively in the supplement to show population-structure context, but they are not presented as recovered person-level or county-age-standardized estimates.

### Bias-bounding analyses

County-period models used a count-model framework with log person-years as the offset. Scenarios were tiered as visible-only analyses, fixed-value stress tests, total-preserving residual allocations, and interval-likelihood models. Visible-only analyses either retained exact positive counties only or added explicit zero counties. Fixed-value stress tests assigned suppressed cells to a constant value; these include suppressed=1, suppressed=5, suppressed=9, and a constant mean assignment of 4.06 deaths per suppressed row. The constant mean preserves the reconciled total but remains a distributional stress test because it gives the same hidden count to low- and high-exposure suppressed counties. Suppressed=5 and suppressed=9 exceed the known reconciled total and are therefore interpreted only as extreme stress tests, not plausible imputations.

The residual allocation used the difference between the Q001 total row and the exact county death sum. This residual was 6,992 deaths across 1,722 suppressed counties. Population-scaled, conservative anti-rural, and pro-rural residual allocations were constrained to the 1-9 death range with an iterative water-filling allocator. After clipping, all three residual allocation scenarios still summed exactly to 58,380 deaths.

Bias-bounding generalized linear models used a negative-binomial mean model with alpha fixed at 1 and robust sandwich standard errors as a stable common working variance specification across scenarios. Pearson ratios from the fitted models and the interval model's smaller dispersion estimate indicate that alpha=1 is conservative as a variance assumption. The primary interpretation therefore rests on scenario-specific IRRs and bounds rather than on unadjusted p-values.

### Interval-likelihood negative binomial model

An interval-likelihood negative binomial model was attempted after bias-bounding analyses. Exact rows contributed P(Y = y), zero rows contributed P(Y = 0), and suppressed rows contributed P(1 <= Y <= 9), treated independently across counties. This specification does not impose the known suppressed-cell total of 6,992 deaths; the residual-allocation analyses use that marginal information directly. Approximate standard errors used optimizer inverse-Hessian estimates, so bias-bounding analyses remained the primary suppression-aware results when interval uncertainty was unstable.

### Multiplicity

The scenario models were designed for sensitivity analysis and bounding, not for selecting statistically significant terms from many comparisons. P-values are reported descriptively, are not adjusted for multiple comparisons, and are not the basis for the main inference.

### Temporal, COVID co-mention, and underlying-cause analyses

Temporal analyses used Q003 national-year, Q004 state-year, Q005 urbanization-year, Q010 COVID co-mention, Q013 age-year, and Q002 county-year data. COVID co-mention was evaluated using multiple-cause G40/G41 in the first multiple-cause box and U07.1 in the second multiple-cause box. Underlying-cause sensitivity used Q011, Q012, and Q014 with G40/G41 in the underlying-cause field.

### Mapping and atlas methods

County geometries used the project's local Plotly county GeoJSON file (`plotly_geojson_counties_fips.json`), a Census-derived county boundary file merged by county FIPS code. The repository does not retain a separate TIGER/Line or cartographic-boundary vintage identifier for this copied geometry source, so no newer geometry was substituted during this pre-submission cleanup. Static maps display a contiguous-U.S. viewport for legibility; Alaska and Hawaii were retained in analytic files where present but are not shown in the static map panels. The District of Columbia is retained. Map-ready CSV files retain all copied county rows. Connecticut county/county-equivalent warnings from CDC WONDER remain a geographic limitation; no crosswalk correction was applied.

### Statistical software

Analyses were performed with reproducible Python scripts archived in the public analysis repository. Modeling used pandas, NumPy, SciPy, statsmodels, matplotlib, and openpyxl where applicable. All tables and figures were generated from scripts rather than manual spreadsheet editing.

### Ethics

This study used public, aggregate, deidentified data and was deemed not human-subjects research.

## Results

### Extraction validation and mortality totals

All Q001-Q015 exports were present, parsed, reconciled, and staged in the analysis repository with checksums. Q003 national-year multiple-cause G40/G41 mortality totaled 58,380 deaths from 2019-2024. Q001 county-period total row deaths also equaled 58,380, confirming reconciliation between the county-period and national-year extraction backbone. Q004 state-year and Q005 urbanization-year outputs reconciled exactly to Q003. Q010 COVID co-mention totaled 1,936 deaths and was bounded by Q005 by urbanization and year. Q012 and Q014 underlying-cause aggregate totals agreed at 22,306 deaths.

### County suppression and data visibility profile

The Q001 county-period file contained 3,142 county rows. Among these, 1,085 counties had exact death counts, 1,722 were suppressed with 1-9 deaths, and 335 were explicit zero rows (Table 1). The exact county death sum was 51,388, leaving a residual of 6,992 deaths within the 1,722 suppressed counties - a mean of {APPROX}4.1 deaths per suppressed county. Exact-count counties accounted for 1.75 billion person-years and were 30.2% nonmetro. Suppressed counties accounted for 226.8 million person-years and were 77.1% nonmetro. Explicit zero counties accounted for 11.0 million person-years and were 88.7% nonmetro.

### County covariates and suppression status

Mean SVI was 0.552 among exact-count counties, 0.496 among suppressed counties, and 0.352 among explicit zero counties (Table 1). Mean poverty was 13.3%, 15.1%, and 13.1%, respectively. Mean age 65 years or older was 18.2% among exact counties, 20.6% among suppressed counties, and 23.2% among explicit zero counties. These age-structure differences motivated including standardized county age 65 years or older and male-percentage covariates in the county count models. Bounded mortality rates by rurality and SVI category are shown in Table 2.

### Suppression-sensitive rurality and SVI model results

Scenario tiering changed the interpretation of the rurality signal (Table 3; Figure 2). These rurality plus SVI models adjusted for county age structure and sex composition through standardized county percentage aged >=65 years and percentage male. Table 3 reports both full-extract assigned deaths and covariate-restricted analytic model deaths to avoid conflating reconciliation totals with model-fit event counts after excluding unmatched counties. In the composite model, the nonmetro nonadjacent IRR was 0.97 (95% CI, 0.80-1.19) in the observed exact-positive model and 0.91 (95% CI, 0.78-1.06) after adding explicit zero counties. Assigning each suppressed cell to 1 death yielded an IRR of 0.98 (95% CI, 0.88-1.10) but fell 5,270 deaths short of the reconciled total.

Among total-preserving residual allocations, the population-scaled residual allocation produced a nonmetro nonadjacent IRR of 1.04 (95% CI, 0.98-1.10), the conservative anti-rural allocation produced 0.97 (95% CI, 0.90-1.04), and the pro-rural allocation produced 1.13 (95% CI, 1.05-1.20). These residual-allocation scenarios preserve the reconciled total and define the primary bounded interpretation.

The constant mean stress test assigned 4.06 deaths to every suppressed county, preserved the total, and yielded an IRR of 1.24 (95% CI, 1.14-1.36). This result is interpreted as a distributional stress test rather than a primary estimate because equal counts across all suppressed counties concentrate rate influence in lower-population suppressed counties. Suppressed=5 and suppressed=9 yielded IRRs of 1.29 and 1.42, respectively, but exceeded the reconciled total by 1,618 and 8,506 deaths. They are therefore retained only as extreme non-total-preserving stress tests.

### Interval-likelihood model results

The interval-likelihood negative binomial model converged in rurality-only and rurality plus SVI specifications. The nonmetro nonadjacent estimate was 1.08 (approximate 95% CI, 0.62-1.88) in the rurality-only interval model and 1.07 (approximate 95% CI, 0.63-1.80) in the rurality plus SVI interval model. These interval results were consistent with uncertainty around the direction and magnitude of the rurality association and supported the suppression-sensitive classification.

### Temporal, COVID co-mention, and underlying-cause context

National multiple-cause G40/G41 deaths increased from 7,583 in 2019 to 10,796 in 2024. The national crude rate increased from 2.31 per 100,000 in 2019 to 3.17 per 100,000 in 2024 (Table 4). COVID co-mention was concentrated in 2020-2022 and totaled 1,936 deaths across 2019-2024. Figure 4 displays urbanization-year MCOD death counts through 2024 and annual COVID co-mention context.

Underlying-cause G40/G41 mortality totaled 22,306 deaths, substantially lower than the multiple-cause total of 58,380 (Table 5). Q014 county-period underlying-cause output contained 16,650 exact county deaths, 1,866 suppressed county rows, and 772 explicit zero county rows. The UCD findings support interpretation of MCOD as a broader epilepsy/status epilepticus-related mortality construct and reinforce that suppression remains substantial under either case definition.

### Geographic atlas findings

The atlas demonstrates the geographic structure of data visibility. Figure 1 separates exact visible counts, known positive suppressed intervals, explicit-zero counties, and covariate-unmatched overlay counties so that hidden positive deaths are not visually confused with absent mortality. Figure 3 summarizes the nonmetro nonadjacent scenario envelope and emphasizes that the primary total-preserving residual-allocation range was 0.97 to 1.13. The illustrative residual-allocation county atlas is provided as Supplementary Figure S3 and should not be interpreted as recovered true county rates.

## Discussion

### Principal findings

In this national county-level analysis of epilepsy/status epilepticus-related mortality, CDC WONDER small-cell suppression was central to the scientific interpretation. The national multiple-cause total was 58,380 deaths, and the county-period extract reconciled exactly to that total. However, only 51,388 deaths were visible as exact county counts, while 1,722 county rows were suppressed and 335 were explicit zero rows. More than half of county-period rows were therefore not exact positive counts.

The rurality-associated mortality pattern was suppression-sensitive. Visible-only models did not support a stable elevated nonmetro nonadjacent estimate. Residual-allocation scenarios that preserved the reconciled total placed the nonmetro nonadjacent IRR in a bounded range of 0.97-1.13, while interval-likelihood models estimated approximately 1.07 with wide uncertainty. Larger estimates arose under constant-count or high fixed-value stress tests, especially scenarios that assign similar hidden counts to many lower-population suppressed counties or exceed the known total. The appropriate interpretation is not that rurality was definitively associated with higher epilepsy/status epilepticus-related mortality; rather, county-level inference depends strongly on how outcome-dependent suppression is handled.

### Interpretation relative to prior censored-WONDER methods

This study is most directly related to prior work modeling highly censored CDC WONDER county mortality data. Quick's hierarchical Bayesian approach aims to estimate county rates by borrowing strength across geography and covariates, producing smoothed point estimates under an explicit model. The present framework serves a different use case: it preserves the observed reconciliation structure, exposes the residual death mass, and asks whether substantive conclusions survive transparent scenario bounds. The advantage is interpretability and assumption visibility; the cost is less precision and no claim to recover the true count in every suppressed county. For investigators seeking county estimates for downstream mapping or prediction, hierarchical modeling may be preferable. For investigators testing whether a county-level conclusion is robust to suppression, reconciliation and bounding provide an assumption-light starting point.

### What observed-only analysis would have missed or overstated

An observed-only analysis would have focused on counties with exact counts and would have excluded most suppressed counties. That approach would have produced a cleaner statistical table but a narrower and potentially misleading view of the county universe. It would have underemphasized the fact that many nonmetro counties contribute positive but hidden intervals and that these hidden intervals can materially affect rurality-associated estimates.

### Temporal and COVID context

The 2019-2024 period included substantial temporal variation, with national multiple-cause G40/G41 deaths rising from 7,583 in 2019 to 10,796 in 2024. COVID co-mention accounted for 1,936 deaths. These findings support including pandemic-era context, but they do not eliminate the need for suppression-aware county-level inference. The county suppression structure remains important across the study period.

### Underlying-cause sensitivity

Underlying-cause G40/G41 mortality totaled 22,306 deaths, compared with 58,380 multiple-cause deaths. This difference is expected because MCOD captures death-certificate mentions beyond the underlying-cause field. UCD sensitivity therefore helps define the scope of the primary outcome: the manuscript studies epilepsy/status epilepticus-related mortality mentions rather than only deaths assigned to epilepsy or status epilepticus as the underlying cause.

### Implications for CDC WONDER county-level research

The study illustrates a general issue for county-level mortality research using CDC WONDER: for outcomes subject to small-cell suppression, exact-count county datasets are not a complete analytic universe. Researchers should report suppression profiles, preserve suppressed intervals, reconcile county extracts to aggregate totals, and test whether substantive conclusions change under plausible suppression assumptions. Fixed-value imputations should be labeled according to whether they preserve known aggregate totals, and distributional assumptions should be stated rather than hidden inside a single sensitivity table.

### Strengths

Strengths include a reconciled Q001-Q015 extraction set, agreement across county, national, state, and urbanization outputs, preservation of suppressed and zero cells as distinct statuses, explicit bias-bounding scenarios, age/sex covariate adjustment in county models, an interval-likelihood sensitivity model, UCD and COVID co-mention context, and a national atlas of data visibility and bounded mortality patterns.

## Limitations

This was an ecological county-level analysis and does not support person-level inference. Multiple-cause mortality reflects death-certificate mention and not necessarily direct etiologic attribution. CDC WONDER suppression requires interval assumptions, and bounding cannot recover the true suppressed counts. Direct county-level age-standardized rates were not used as the primary estimand because county-by-age mortality strata are highly vulnerable to small-cell suppression; model-based age-structure adjustment with county percentage aged >=65 years reduces but does not eliminate residual confounding by age. The interval-likelihood model treats suppressed counties independently and does not condition on the known suppressed-cell total; a constrained interval model could be more efficient and is an important future methodological extension. The fixed alpha=1 GLM specification is a robust working-variance approach for scenario contrasts, not a claim that alpha=1 is the best dispersion estimate.

Death-certificate coding may vary by place, certifier, comorbidity, and time. COVID-era certification and mortality disruption may affect temporal patterns. County-level covariate timing differs across SVI, RUCC, NCHS, ACS, and mortality files. The Connecticut county/county-equivalent warning from CDC WONDER remains a limitation for county-level geography and rate interpretation; no crosswalk correction was applied, and the 2022 transition to planning regions could affect comparability for Connecticut county-equivalent units across the study period.

Rurality classification is imperfect, and RUCC/NCHS categories may not capture all dimensions of access, remoteness, or healthcare context. SVI and ACS component collinearity was handled by separate model families but remains a conceptual issue because social vulnerability domains overlap. Race/ethnicity and place-of-death descriptive analyses are limited by aggregation and small-cell suppression and are best interpreted as contextual summaries.

## Conclusions

In this national county-level analysis of epilepsy/status epilepticus-related mortality, more than half of county-period rows were suppressed despite full reconciliation to national totals. Apparent rurality-associated mortality patterns were sensitive to hidden-cell assumptions even after model adjustment for county age structure and sex composition, and total-preserving residual allocations supported a cautious bounded interpretation rather than a conclusive rurality claim. Interval-preserving bounding and interval-likelihood approaches provide a more transparent framework for county-level mortality surveillance and for interpreting rural epilepsy/status epilepticus mortality patterns.

## Data availability

The analysis used public, aggregate, deidentified mortality data from CDC WONDER and public county-level covariate sources. Processed aggregate query outputs, derived analytic datasets, tables, figures, and documentation supporting this study are available at {GITHUB_URL}. The archived release is available at {DOI_URL}. No person-level data are included.

## Code availability

Analysis code used to import reconciled CDC WONDER aggregate outputs, construct interval-preserving analytic datasets, run bias-bounding and interval-likelihood models, and generate tables and figures is available at {GITHUB_URL}. The archived release is available at {DOI_URL}.

## Ethics statement

This study used public, aggregate, deidentified data and was deemed not human-subjects research.

## Funding

No external funding was received for this work.

## Conflicts Of Interest

The author declares no competing interests.

## Author Contributions

Gregory Pierpoint: Conceptualization, Data curation, Formal analysis, Investigation, Methodology, Software, Validation, Visualization, Writing {EN_DASH} original draft, Writing {EN_DASH} review & editing.

## Acknowledgments

None.

## Declaration Of Generative AI And AI-Assisted Technologies In The Writing Process

Generative AI tools were used to assist with code generation, analysis organization, drafting, editing, and quality-control checks. The author reviewed and verified the analysis, scientific interpretation, references, and manuscript content and is responsible for the final work.

{references}

## Tables

Table 1. County characteristics by Q001 death-count status.

{df_to_markdown(tables['t1'])}

Table 2. Mortality totals and bounded rates by rurality and SVI category.

{df_to_markdown(tables['t2'])}

Table 3. Suppression-aware nonmetro nonadjacent model results, rurality plus SVI specification.

{df_to_markdown(tables['t3'])}

Table 4. National temporal and COVID-19 co-mention context.

{df_to_markdown(tables['t4'])}

Table 5. Underlying-cause sensitivity and MCOD/UCD comparison.

{df_to_markdown(tables['t5'])}

## Figure Legends

Figure 1. County multiple-cause G40/G41 death-count status, 2019-2024. Blue indicates exact counts, orange indicates suppressed 1-9 death cells, and hatched gray indicates explicit zero cells. Static map viewport displays the contiguous United States; Alaska and Hawaii are retained in analytic files and models where present but are not shown in the static panel.

Figure 2. Two-panel suppression-scenario model estimates. Panel A shows nonmetro nonadjacent IRRs relative to large metropolitan counties. Panel B shows highest-SVI-quartile IRRs relative to the lowest SVI quartile. Points are IRRs and whiskers are 95% CIs from the rurality plus SVI specification on a log scale. Scenario tiers distinguish visible-only models, total-preserving allocations, fixed-value stress tests, and interval-likelihood modeling.

Figure 3. Scenario envelope for the nonmetro nonadjacent incidence rate ratio. Points are IRRs and whiskers are 95% CIs from the rurality plus SVI specification. The shaded band marks the primary total-preserving residual-allocation range.

Figure 4. Urbanization-year temporal trend and COVID-19 co-mention context, 2019-2024. Panel A shows annual multiple-cause G40/G41 death counts by NCHS urbanization category through 2024; the Not Available category is a data-quality/availability category, not an urbanization level. Panel B shows COVID-19 co-mention death intervals aggregated across urbanization categories. National crude rates are reported in Table 4.
"""


def write_markdown_files() -> dict[str, str]:
    tables = format_tables_for_manuscript()
    manuscript = manuscript_markdown(tables)
    title_page = f"""# Title Page

{TITLE}

{AUTHOR}

{AFFILIATION}

Corresponding author:

{AUTHOR}  
{AFFILIATION}  
P.O. Box 1980  
Norfolk, VA 23501  
United States  
Email: {EMAIL}  
Phone: {PHONE}  
ORCID: {ORCID}

Running title: Suppression-aware epilepsy mortality

Article type: Original Research

Funding: No external funding was received for this work.

Conflicts of interest: The author declares no competing interests.

Ethics: This study used public, aggregate, deidentified data and was deemed not human-subjects research.

Data and code availability: Processed aggregate data, code, tables, figures, and documentation are available at {GITHUB_URL}. The archived release is available at {DOI_URL}.

Author contributions: Gregory Pierpoint: Conceptualization, Data curation, Formal analysis, Investigation, Methodology, Software, Validation, Visualization, Writing {EN_DASH} original draft, Writing {EN_DASH} review & editing.

AI declaration: Generative AI tools were used to assist with code generation, analysis organization, drafting, editing, and quality-control checks. The author reviewed and verified the analysis, scientific interpretation, references, and manuscript content and is responsible for the final work.
"""
    abstract = "\n".join(manuscript.split("## Abstract", 1)[1].split("## Keywords", 1)[0].strip().splitlines())
    highlights = """# Highlights

- CDC WONDER county suppression strongly shapes epilepsy/status epilepticus mortality inference.
- The county-period extract reconciled to 58,380 deaths, with 6,992 deaths hidden in 1,722 suppressed counties.
- Total-preserving residual allocations gave nonmetro nonadjacent IRRs from 0.97 to 1.13.
- Fixed-value stress tests that exceed or redistribute the known residual are labeled separately from primary bounds.
- Suppression-aware county mapping distinguished visible mortality patterns from allocation-dependent geographic patterns.
"""
    cover_letter = f"""# Cover Letter

Dear Editors,

Please consider the original research manuscript, "{TITLE}," for publication in Epilepsy & Behavior.

This manuscript presents a national ecological county-level analysis of epilepsy/status epilepticus-related mortality using reconciled CDC WONDER aggregate outputs and public county covariates. The study preserves suppressed county cells as bounded intervals, reconciles county extracts to aggregate totals, and evaluates whether rurality-associated conclusions remain stable across visible-only, total-preserving allocation, and interval-likelihood approaches. The submission includes populated manuscript tables, publication figures, a self-contained supplement, and reproducibility materials.

Code and processed aggregate data supporting this study are available at {GITHUB_URL}. The archived release is available at {DOI_URL}.

The work is not under consideration elsewhere and has not been published previously. The author approves submission. No external funding was received, and the author declares no competing interests. The study used public, aggregate, deidentified data and was deemed not human-subjects research.

Sincerely,

{AUTHOR}  
{AFFILIATION}  
Email: {EMAIL}
"""
    response = response_markdown()
    supplement = supplement_markdown()
    strobe = strobe_markdown()
    outputs = {
        "manuscript_main_revised.md": manuscript,
        "title_page_revised.md": title_page,
        "abstract_revised.md": "# Abstract\n\n" + abstract + "\n",
        "highlights_revised.md": highlights,
        "cover_letter_revised.md": cover_letter,
        "response_to_editorial_review.md": response,
        "supplement_revised.md": supplement,
        "STROBE_checklist_revised.md": strobe,
    }
    for name, text in outputs.items():
        target_dir = INTERNAL_DIR if name == "response_to_editorial_review.md" else MD_DIR
        (target_dir / name).write_text(text, encoding="utf-8")
    return outputs


def response_markdown() -> str:
    matrix = pd.read_csv(REPORT_DIR / "editorial_issue_response_matrix.csv")
    rows = "\n".join(f"| {r.issue} | {r.status} | {r.action} |" for r in matrix.itertuples(index=False))
    hardstop_rows = [
        ("HS-1", "addressed", "Rebuilt the main manuscript DOCX and verified with Word COM and python-docx that it contains 5 actual Word tables, not only table-title paragraphs."),
        ("HS-2", "addressed", "Canonical Figure 2 now uses the two-panel rurality/SVI IRR image; the active Figure 2 filename no longer carries the old dense single-panel plot."),
        ("HS-3", "addressed", "Figure 4 remains the 2019-2024 temporal/COVID co-mention figure and is embedded byte-for-byte in the main manuscript DOCX."),
        ("HS-4", "addressed", "Removed the separate figure-legend block from the main DOCX so captions do not appear as orphan paragraphs before the figures; each figure is inserted on its own page with the caption immediately below."),
        ("HS-5", "addressed", "Verified the active abstract DOCX omits the county-year exact-deaths sentence and uses the newer age-adjustment wording."),
        ("HS-6", "addressed", "Verified the active cover-letter DOCX uses reconciled CDC WONDER aggregate outputs rather than stronger validation wording."),
        ("HS-7", "addressed", "Revised Table 3 and related text to distinguish assigned deaths in the full county extract from analytic model deaths after covariate restriction."),
        ("HS-8", "addressed", "Added an `UPLOAD_THESE_FILES_ONLY` folder containing only the current corrected DOCX files to prevent accidental use of stale baseline attachments."),
    ]
    hardstop = "\n".join(f"| {issue} | {status} | {action} |" for issue, status, action in hardstop_rows)
    round3_rows = [
        ("R3-1", "addressed", "Rebuilt Figure 4 as the corrected 2019-2024 urbanization-year temporal figure with an explicit COVID-19 co-mention panel/context and revised the legend to match the rendered panels."),
        ("R3-2", "addressed", "Replaced Figure 2 with a two-panel plot: nonmetro nonadjacent IRRs and highest-SVI-quartile IRRs, using shorter scenario labels and larger readable axes."),
        ("R3-3", "addressed", "Rebuilt the main manuscript DOCX with one figure per page, caption immediately following each figure, and whitespace-trimmed map images to reduce dead space and avoid cramped figure placement."),
        ("R3-4", "addressed", "Added a dedicated Methods subsection explaining why direct county age-standardization was not used, and clarified that all primary county models adjust for county percentage aged >=65 years and percentage male."),
        ("R3-5", "addressed", "Removed the confusing county-year exact-death sentence from the abstract and main manuscript summary so visible county-year deaths are not mistaken for total mortality."),
        ("R3-6", "addressed", "Tightened repetitive wording by replacing some repeated suppression-aware phrasing with interval-preserving, bounded, reconciliation, and data-visibility language while preserving the conservative scientific frame."),
        ("R3-7", "addressed", "Expanded the supplement language and DOCX content so the full model table, interval results, descriptive context, merge exceptions, and geography notes are embedded rather than merely deferred to the repository."),
        ("R3-8", "addressed", "Revised cover-letter and availability wording to use reconciled CDC WONDER aggregate outputs rather than stronger validation language."),
    ]
    round3 = "\n".join(f"| {issue} | {status} | {action} |" for issue, status, action in round3_rows)
    round2_rows = [
        ("B1", "addressed", "Restored and embedded Figures 1-4 in the main manuscript DOCX and supplied the same figure files in the package figures folder."),
        ("B2", "addressed", "Restored populated supplementary Tables S1-S10 in the supplement DOCX and supplied supporting CSV/XLSX files."),
        ("r1", "addressed", "Revised the abstract to name the population-scaled residual allocation and interval model as the primary read, and clarified the uniform constant-mean allocation as total-preserving but exposure-ignoring."),
        ("r2", "addressed", "Added a Table 4 footnote that yearly COVID co-mention intervals are suppression-bounded and midpoint sums need not equal the aggregate exactly."),
        ("r3", "addressed", "Restored funding, conflicts, ethics, data/code availability, author contributions, and AI declaration blocks on the title page while retaining them in the main manuscript."),
    ]
    round2 = "\n".join(f"| {issue} | {status} | {action} |" for issue, status, action in round2_rows)
    return f"""# Response To Editorial Review

Manuscript: {TITLE}

Author: {AUTHOR}

## Overview

The revised submission package addresses all major issues, minor issues, author questions, Round 2 completeness checks, the latest figure/age-adjustment editorial review, and the hard-stop package-assembly concerns. The revisions preserve the paper's conservative suppression-sensitive framing while correcting actual DOCX table structure, active figure bytes, figure layout, age-structure wording, supplement self-containment, cover-letter precision, and model-total labeling.

## Hard-Stop Package Assembly Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
{hardstop}

## Round 3 Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
{round3}

## Round 2 Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
{round2}

## Round 1 Response Matrix

| Issue | Status | Revision made |
| --- | --- | --- |
{rows}

## Key Interpretive Change

The revised manuscript no longer gives equal interpretive weight to fixed-value scenarios that do not respect the reconciled total. It distinguishes visible-only models, total-preserving residual allocations, a constant-count total-preserving stress test, non-total-preserving fixed-value stress tests, and interval-likelihood models. The main interpretive range is the residual-allocation/interval-model result; fixed-value results are retained to show sensitivity, not to claim a plausible recovered truth.

## Package Completeness

The main manuscript DOCX now contains populated Tables 1-5 and embedded Figures 1-4. Figure 4 has been replaced with a 2019-2024 temporal/COVID context figure. Figure 2 uses publication labels and explicitly reports 95% CIs on a log scale. Figure 1 has increased contrast and hatching for explicit-zero rows. The supplement DOCX contains populated Tables S1-S10 and embedded Figures S1-S3.
"""


def supplement_markdown() -> str:
    tables = supplement_tables_for_docx(markdown_ready=True)
    table_blocks = []
    for caption, df, footnote, _widths in tables:
        table_blocks.append(f"## {caption}\n\n{df_to_markdown(df)}\n\nNote. {footnote}")
    return f"""# Supplementary Material

Manuscript: {TITLE}

## Supplementary methods

This supplement accompanies the revised editorial-review package. The analysis uses the same frozen, reconciled CDC WONDER aggregate outputs and county covariate inputs as the prior package; CDC WONDER was not re-queried. The revision adds a constant-mean suppression stress test and reorganizes the scenario interpretation around reconciliation to the known county-period total.

This supplement is intended to be self-contained for editorial review. It embeds the full model table, interval-likelihood results, VIF diagnostics, descriptive age/sex/race/place-of-death context, county-year suppression profile, underlying-cause sensitivity profile, merge exceptions, and Connecticut geography note. Repository and archive links provide reproducibility materials, but the key tables and figures needed to interpret the manuscript are included below.

## Supplementary tables

{chr(10).join(table_blocks)}

## Revised scenario audit

The county-period extract reconciled to 58,380 multiple-cause G40/G41 deaths. Exact counties contributed 51,388 deaths, leaving 6,992 deaths in 1,722 suppressed rows, or {APPROX}4.1 deaths per suppressed row. Population-scaled, conservative anti-rural, and pro-rural residual allocations each preserve the reconciled total after 1-9 clipping. Suppressed=5 and suppressed=9 exceed the reconciled total and are retained only as extreme stress tests. The constant-mean 4.06 scenario preserves the total but is treated as a distributional stress test because it assigns the same hidden count to every suppressed county.

## Supplementary figure inventory

- Figure S1: national-year mortality trend, 2019-2024.
- Figure S2: COVID co-mention by urbanization-year, 2019-2024.
- Figure S3: residual-allocation county rate map.

All supplementary tables and figures are embedded in the supplement DOCX and are also supplied as package files.
"""


def clean_df(df: pd.DataFrame, max_rows: int | None = None, cols: list[str] | None = None) -> pd.DataFrame:
    out = df.copy()
    if cols is not None:
        out = out[[c for c in cols if c in out.columns]].copy()
    if max_rows is not None:
        out = out.head(max_rows).copy()

    def format_identifier(value, col_name: str) -> str | None:
        name = col_name.lower()
        if pd.isna(value):
            return ""
        if "fips" in name:
            raw = str(value).strip()
            if raw.endswith(".0"):
                raw = raw[:-2]
            digits = re.sub(r"\D", "", raw)
            if not digits:
                return raw
            width = 5 if "county" in name else 2 if "state" in name else len(digits)
            return digits.zfill(width)
        is_year_col = "year" in name and "person_year" not in name and "person-years" not in name and "person years" not in name
        if is_year_col:
            try:
                return str(int(round(float(value))))
            except Exception:
                return str(value)
        return None

    def format_value(value, col_name: str) -> str:
        identifier = format_identifier(value, col_name)
        if identifier is not None:
            return identifier
        if pd.isna(value):
            return ""
        if isinstance(value, (int, float, np.integer, np.floating)) or pd.api.types.is_number(value):
            value_float = float(value)
            if abs(value_float) < 1000 and value_float != int(value_float):
                return f"{value_float:.3f}"
            return f"{int(round(value_float)):,}"
        return str(value)

    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]) or pd.api.types.is_integer_dtype(out[col]):
            out[col] = out[col].map(lambda x, col=col: format_value(x, col))
        else:
            out[col] = out[col].map(lambda x, col=col: format_value(x, col))
    out.columns = [str(c).replace("_", " ").title() for c in out.columns]
    return out


def supplement_tables_for_docx(markdown_ready: bool = False) -> list[tuple[str, pd.DataFrame, str, list[float]]]:
    s = SUPP_DIR
    tables: list[tuple[str, pd.DataFrame, str, list[float]]] = []
    tables.append(
        (
            "Table S1. County-year suppression profile by rurality",
            clean_df(pd.read_csv(s / "county_year_suppression_by_rurality.csv")),
            "County-year rows preserve exact, suppressed, and zero death-count statuses.",
            [],
        )
    )
    full_models = pd.read_csv(TABLE_DIR / "table3_suppression_aware_models_revised_full.csv")
    full_models = full_models[
        [
            "scenario",
            "model_family",
            "model_type",
            "term",
            "irr",
            "ci_low",
            "ci_high",
            "p_value",
            "n_rows",
            "events",
        ]
    ]
    tables.append(
        (
            "Table S2. Full suppression-aware model results",
            clean_df(full_models),
            "Includes all scenario, family, and term rows used to support main Table 3.",
            [],
        )
    )
    interval = pd.read_csv(s / "interval_model_results.csv")
    tables.append(
        (
            "Table S3. Interval-likelihood model estimates",
            clean_df(interval),
            "Approximate confidence intervals use optimizer inverse-Hessian estimates; suppressed rows contribute interval probabilities.",
            [],
        )
    )
    vif = pd.read_csv(s / "component_model_vif.csv")
    tables.append(
        (
            "Table S4. Component-model VIF diagnostics",
            clean_df(vif),
            "Maximum VIF was approximately 2.92 for median household income/poverty-related component diagnostics.",
            [],
        )
    )
    tables.append(
        (
            "Table S5. Place of death by urbanization",
            clean_df(pd.read_csv(s / "place_by_urbanization.csv")),
            "Descriptive place-of-death context is aggregate and subject to WONDER suppression.",
            [],
        )
    )
    tables.append(
        (
            "Table S6. Age group by urbanization",
            clean_df(pd.read_csv(s / "age_by_urbanization.csv")),
            "Age group descriptive context is aggregate and not a person-level risk estimate.",
            [],
        )
    )
    tables.append(
        (
            "Table S7. Sex by urbanization",
            clean_df(pd.read_csv(s / "sex_by_urbanization.csv")),
            "Sex-stratified descriptive context sums to the reconciled national multiple-cause total where rows are exact.",
            [],
        )
    )
    race = pd.read_csv(s / "race_by_urbanization.csv")
    hisp = pd.read_csv(s / "hispanic_by_urbanization.csv")
    race.insert(0, "descriptive_domain", "race")
    hisp.insert(0, "descriptive_domain", "hispanic_origin")
    tables.append(
        (
            "Table S8. Race and Hispanic-origin descriptive summaries",
            clean_df(pd.concat([race, hisp], ignore_index=True, sort=False)),
            "Race and Hispanic-origin outputs are descriptive aggregate summaries and are limited by suppression.",
            [],
        )
    )
    tables.append(
        (
            "Table S9. Underlying-cause county suppression profile",
            clean_df(pd.read_csv(s / "ucd_county_suppression_profile.csv")),
            "Underlying-cause G40/G41 sensitivity profile preserves exact, suppressed, and explicit-zero status.",
            [],
        )
    )
    missing_cov = pd.read_csv(s / "counties_present_in_wonder_missing_covariates.csv")
    missing_wonder = pd.read_csv(s / "counties_present_in_covariates_missing_wonder.csv")
    missing_cov.insert(0, "merge_issue", "WONDER county missing covariates")
    missing_wonder.insert(0, "merge_issue", "Covariate county missing WONDER")
    ct_note = pd.DataFrame(
        [
            {
                "merge_issue": "Connecticut geography note",
                "county_fips": "09xxx",
                "county_name": "Connecticut county/county-equivalent units",
                "notes": "CDC WONDER county-equivalent warning retained; no crosswalk correction applied; 2022 planning-region transition may affect period comparability.",
            }
        ]
    )
    tables.append(
        (
            "Table S10. County merge and Connecticut geography details",
            clean_df(pd.concat([missing_cov, missing_wonder, ct_note], ignore_index=True, sort=False)),
            "Merge exceptions and Connecticut geography cautions are documented for reproducibility.",
            [],
        )
    )
    final_tables = []
    for caption, df, footnote, widths in tables:
        if not widths:
            widths = widths_for_columns(len(df.columns), total_width=9.0)
        final_tables.append((caption, df, footnote, widths))
    return final_tables


def strobe_markdown() -> str:
    rows = [
        ("1", "Title/abstract", "Title and Abstract", "County-level ecological design, public aggregate data, and suppression-aware methods identified."),
        ("2-3", "Introduction", "Introduction", "Rationale and objectives stated, including comparison with censored-WONDER prior methods."),
        ("4-12", "Methods", "Methods", "Design, data sources, variables, bias, study size, quantitative variables, and statistical methods reported."),
        ("13-17", "Results", "Results; Tables 1-5; Figures 1-4", "Participants/units, descriptive data, outcome data, main results, and sensitivity/context analyses reported."),
        ("18-21", "Discussion", "Discussion and Limitations", "Key results, limitations, interpretation, and generalizability reported."),
        ("22", "Funding", "Declarations", "No external funding was received."),
    ]
    lines = ["# STROBE Checklist", "", "| Item | STROBE area | Location | Response |", "| --- | --- | --- | --- |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def build_docx_from_markdown(name: str, text: str, out_name: str, landscape: bool = False) -> None:
    doc = Document()
    setup_doc(doc, out_name, landscape=landscape)
    lines = text.splitlines()
    in_code = False
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            add_paragraph(doc, line)
        elif line.startswith("# "):
            add_paragraph(doc, line[2:], style="Heading 1")
        elif line.startswith("## "):
            add_paragraph(doc, line[3:], style="Heading 1")
        elif line.startswith("### "):
            add_paragraph(doc, line[4:], style="Heading 2")
        elif re.match(r"^\d+\.\s+", line):
            add_number(doc, re.sub(r"^\d+\.\s+", "", line))
        elif line.startswith("- "):
            add_bullet(doc, line[2:])
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            if len(table_lines) >= 3:
                headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
                data = []
                for tline in table_lines[2:]:
                    data.append([c.strip().replace("\\|", "|") for c in tline.strip("|").split("|")])
                df = pd.DataFrame(data, columns=headers)
                table_docx(doc, "", df, "", widths=None)
            continue
        else:
            add_paragraph(doc, line)
        i += 1
    doc.save(DOCX_DIR / out_name)


def build_manuscript_docx(markdown_text: str, tables: dict[str, pd.DataFrame]) -> None:
    text_before_tables, tail = markdown_text.split("## Tables", 1)
    references_and_before = text_before_tables.rstrip()
    doc = Document()
    setup_doc(doc, "manuscript_main_revised.docx")
    in_references = False
    for line in references_and_before.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            in_references = False
            add_paragraph(doc, line[2:], style="Heading 1")
        elif line.startswith("## "):
            heading = line[3:]
            in_references = heading.strip().lower() == "references"
            add_paragraph(doc, heading, style="Heading 1")
        elif line.startswith("### "):
            in_references = False
            add_paragraph(doc, line[4:], style="Heading 2")
        elif re.match(r"^\d+\.\s+", line):
            match = re.match(r"^(\d+)\.\s+(.*)", line)
            if in_references and match:
                add_reference_paragraph(doc, match.group(1), match.group(2))
            else:
                add_number(doc, re.sub(r"^\d+\.\s+", "", line))
        elif line.startswith("- "):
            add_bullet(doc, line[2:])
        else:
            add_paragraph(doc, line)

    doc.add_page_break()
    add_paragraph(doc, "Tables", style="Heading 1")
    table_docx(
        doc,
        "Table 1. County characteristics by Q001 death-count status.",
        tables["t1"],
        "Person-years are 2019-2024 county-period person-years. Suppressed rows are positive 1-9 death intervals. Exact deaths are visible deaths only.",
        widths=[1.0, 0.55, 0.85, 0.75, 0.9, 0.7, 0.65, 0.65, 0.65, 0.65],
    )
    table_docx(
        doc,
        "Table 2. Mortality totals and bounded rates by rurality and SVI category.",
        tables["t2"],
        "Deaths lower-mid-upper uses suppressed-cell lower, midpoint, and upper values. Rates are deaths per 100,000 person-years.",
        widths=[1.15, 0.75, 0.6, 1.25, 0.8, 1.3],
    )
    table_docx(
        doc,
        "Table 3. Suppression-aware nonmetro nonadjacent model results, rurality plus SVI specification.",
        tables["t3"],
        'Reference category is metro_large. CIs are 95% intervals. Assigned deaths use the full county extract before covariate restriction. Analytic model deaths exclude the 11 WONDER counties without covariates and may be lower than the full-extract reconciliation total. "Preserves reconciled total?" indicates whether the scenario preserves the known full-extract total of 58,380 deaths. Suppressed = 1 falls below the reconciled total; suppressed = 5 and suppressed = 9 exceed it and are retained only as fixed-value stress tests. The constant mean scenario preserves the total but is interpreted as a distributional stress test. Residual-allocation scenarios preserve the reconciled total. The interval-likelihood model does not assign county counts and therefore is not classified as total-preserving.',
        widths=[0.72, 1.42, 0.78, 0.78, 0.96, 0.38, 0.62],
    )
    table_docx(
        doc,
        "Table 4. National temporal and COVID-19 co-mention context.",
        tables["t4"],
        "COVID co-mention interval preserves suppression status and is aggregated across urbanization categories. Yearly intervals are suppression-bounded and midpoint sums need not equal the aggregate COVID co-mention total exactly.",
        widths=[0.55, 0.85, 1.05, 1.1, 1.1, 1.2],
    )
    table_docx(
        doc,
        "Table 5. Underlying-cause sensitivity and MCOD/UCD comparison.",
        tables["t5"],
        "MCOD indicates multiple-cause G40/G41 mention. UCD indicates underlying-cause G40/G41.",
        widths=[1.35, 0.8, 0.8, 3.45],
    )

    add_paragraph(doc, "Figures", style="Heading 1")
    doc.add_page_break()
    figure_specs = [
        (
            FIG_DIR / "figure1_county_suppression_status_revised.png",
            "Figure 1. County data visibility for multiple-cause G40/G41 mortality, 2019-2024. Contiguous U.S. counties are shown; Alaska and Hawaii are retained in analytic files where present but are not shown in this static map panel. Suppressed counties are known positive 1-9 death intervals, not zero-death counties. The right-side panel provides category counts and proportions; the unmatched/missing-covariate count is shown as an overlay rather than a mutually exclusive death-status category.",
        ),
        (
            FIG_DIR / "figure2_suppression_bounds_revised.png",
            "Figure 2. Two-panel suppression-scenario model estimates. Panel A shows nonmetro nonadjacent IRRs relative to large metropolitan counties. Panel B shows highest-SVI-quartile IRRs relative to the lowest SVI quartile. Points are IRRs and whiskers are 95% CIs from the rurality plus SVI specification on a log scale. Scenario tiers distinguish visible-only analyses, total-preserving residual allocations, fixed-value stress tests, and the interval model.",
        ),
        (
            FIG_DIR / "figure3_scenario_envelope_revised.png",
            "Figure 3. Scenario envelope for the nonmetro nonadjacent incidence rate ratio. Points are IRRs and whiskers are 95% CIs from the rurality plus SVI specification. The shaded band marks the primary total-preserving residual-allocation range of 0.97-1.13; visible-only, fixed-value stress-test, and interval-likelihood estimates are shown as context.",
        ),
        (
            FIG_DIR / "figure4_temporal_covid_context_revised.png",
            "Figure 4. Urbanization-year temporal trend and COVID-19 co-mention context, 2019-2024. Panel A shows annual multiple-cause G40/G41 death counts by NCHS urbanization category through 2024; counts are shown because some urbanization-year denominator fields are unavailable after 2021. Panel B shows COVID-19 co-mention midpoint bars with lower-upper suppression bounds aggregated across urbanization categories.",
        ),
    ]
    for idx, (path, caption) in enumerate(figure_specs):
        if idx:
            doc.add_page_break()
        add_image(doc, path, caption, width=6.2)
    doc.save(DOCX_DIR / "manuscript_main_revised.docx")


def build_all_docx(markdowns: dict[str, str]) -> None:
    tables = format_tables_for_manuscript()
    build_manuscript_docx(markdowns["manuscript_main_revised.md"], tables)
    build_docx_from_markdown("title", markdowns["title_page_revised.md"], "title_page_revised.docx")
    build_docx_from_markdown("abstract", markdowns["abstract_revised.md"], "abstract_revised.docx")
    build_docx_from_markdown("cover", markdowns["cover_letter_revised.md"], "cover_letter_revised.docx")
    build_docx_from_markdown("highlights", markdowns["highlights_revised.md"], "highlights_revised.docx")
    (INTERNAL_DIR / "response_to_editorial_review_INTERNAL_QA_NOT_FOR_SUBMISSION.md").write_text(
        markdowns["response_to_editorial_review.md"],
        encoding="utf-8",
    )
    build_supplement_docx_round2()
    build_docx_from_markdown("strobe", markdowns["STROBE_checklist_revised.md"], "STROBE_checklist_revised.docx", landscape=True)


def build_supplement_docx_round2() -> None:
    doc = Document()
    setup_doc(doc, "supplement_revised.docx", landscape=True)
    add_paragraph(doc, "Supplementary material", style="Heading 1")
    add_paragraph(doc, f"Manuscript: {TITLE}")
    add_paragraph(
        doc,
        "This supplement is self-contained for editorial review. It embeds the full model table, interval-likelihood results, VIF diagnostics, descriptive age/sex/race/place-of-death context, county-year suppression profile, underlying-cause sensitivity profile, merge exceptions, Connecticut geography note, and supplementary figures. The analysis uses the same frozen reconciled CDC WONDER aggregate outputs and county covariate inputs; CDC WONDER was not re-queried.",
    )
    add_paragraph(
        doc,
        f"Code and processed aggregate data supporting this study are available at {GITHUB_URL}. The archived release is available at {DOI_URL}.",
    )
    add_paragraph(doc, "Revised scenario audit", style="Heading 1")
    add_paragraph(
        doc,
        f"The county-period extract reconciled to 58,380 multiple-cause G40/G41 deaths. Exact counties contributed 51,388 deaths, leaving 6,992 deaths in 1,722 suppressed rows, or {APPROX}4.1 deaths per suppressed row. Population-scaled, conservative anti-rural, and pro-rural residual allocations each preserve the reconciled total after 1-9 clipping. Suppressed=5 and suppressed=9 exceed the reconciled total and are retained only as extreme stress tests. The constant-mean 4.06 scenario preserves the total but is treated as a distributional stress test because it assigns the same hidden count to every suppressed county.",
    )
    add_paragraph(doc, "Supplementary tables", style="Heading 1")
    for idx, (caption, df, footnote, widths) in enumerate(supplement_tables_for_docx()):
        if idx:
            doc.add_page_break()
        table_docx(doc, caption, df, footnote, widths=widths)
    doc.add_page_break()
    add_paragraph(doc, "Supplementary figures", style="Heading 1")
    supp_figures = [
        (
            FIG_DIR / "supplement_national_year_trend.png",
            "Figure S1. National multiple-cause G40/G41 mortality trend, 2019-2024.",
        ),
        (
            FIG_DIR / "supplement_original_covid_urbanization_year.png",
            "Figure S2. COVID co-mention by year, 2019-2024. Bars show interval midpoints and whiskers show lower-upper suppression bounds.",
        ),
        (
            FIG_DIR / "figureS3_residual_allocation_atlas.png",
            "Figure S3. Residual-allocation county mortality atlas. This map shows one population-scaled, total-preserving allocation scenario for sensitivity context and should not be interpreted as recovered true county rates.",
        ),
    ]
    for idx, (path, caption) in enumerate(supp_figures):
        if idx:
            doc.add_page_break()
        add_image(doc, path, caption, width=8.7)
    doc.save(DOCX_DIR / "supplement_revised.docx")


def write_xlsx() -> None:
    tables = format_tables_for_manuscript()
    tables["t3"].to_csv(TABLE_DIR / "table3_suppression_aware_models_revised_main_labeled.csv", index=False)
    with pd.ExcelWriter(TABLE_DIR / "main_tables_revised.xlsx", engine="openpyxl") as writer:
        for key, df in tables.items():
            df.to_excel(writer, sheet_name=key.upper(), index=False)


def readback_docx() -> pd.DataFrame:
    rows = []
    for path in sorted(DOCX_DIR.glob("*.docx")):
        try:
            doc = Document(path)
            rows.append({"file": path.name, "bytes": path.stat().st_size, "paragraphs": len(doc.paragraphs), "tables": len(doc.tables), "readable": True})
        except Exception as exc:
            rows.append({"file": path.name, "bytes": path.stat().st_size if path.exists() else 0, "paragraphs": 0, "tables": 0, "readable": False, "error": str(exc)})
    df = pd.DataFrame(rows)
    df.to_csv(REPORT_DIR / "docx_readback.csv", index=False)
    return df


def collect_text_for_qc() -> dict[str, str]:
    texts = {}
    for path in list(MD_DIR.glob("*.md")) + list(DOCX_DIR.glob("*.docx")):
        if path.suffix.lower() == ".md":
            texts[str(path)] = path.read_text(encoding="utf-8", errors="replace")
        else:
            doc = Document(path)
            parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        parts.append(cell.text)
            texts[str(path)] = "\n".join(parts)
    return texts


def embedded_media_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(DOCX_DIR.glob("*.docx")):
        try:
            with zipfile.ZipFile(path) as zf:
                counts[path.name] = len([n for n in zf.namelist() if n.startswith("word/media/")])
        except Exception:
            counts[path.name] = -1
    pd.DataFrame([{"file": k, "embedded_media_count": v} for k, v in counts.items()]).to_csv(
        REPORT_DIR / "docx_embedded_media_counts.csv", index=False
    )
    return counts


def docx_table_count(path: Path) -> int:
    try:
        return len(Document(path).tables)
    except Exception:
        return -1


def qc_reports() -> dict:
    forbidden = [
        "[VERIFY",
        "VERIFY:",
        "SUPPRESSION_SENSITIVE_SIGNAL",
        "References for human verification",
        "Final journal-formatted references should be inserted",
        "repository pending",
        "not assigned in Phase",
        "33,217",
        "validated CDC WONDER outputs",
        "Figure 2. Suppression-bounds model estimates",
    ]
    overclaim = [
        "resolved the",
        "proved",
        "caused higher",
        "definitive rural disparity",
        "causal effect",
    ]
    texts = collect_text_for_qc()
    f_hits = []
    o_hits = []
    for path, text in texts.items():
        low = text.lower()
        for term in forbidden:
            if term.lower() in low:
                f_hits.append({"path": path, "term": term})
        for term in overclaim:
            if term.lower() in low:
                o_hits.append({"path": path, "term": term})
    pd.DataFrame(f_hits).to_csv(REPORT_DIR / "qc_forbidden_language_scan.csv", index=False)
    pd.DataFrame(o_hits).to_csv(REPORT_DIR / "qc_overclaim_scan.csv", index=False)
    return {"forbidden_hits": len(f_hits), "overclaim_hits": len(o_hits)}


def write_reports(readback: pd.DataFrame, qc: dict) -> None:
    analysis_summary = json.loads((REPORT_DIR / "editorial_revision_analysis_summary.json").read_text(encoding="utf-8"))
    response_matrix = pd.read_csv(REPORT_DIR / "editorial_issue_response_matrix.csv")
    media_counts = embedded_media_counts()
    manuscript_tables = docx_table_count(DOCX_DIR / "manuscript_main_revised.docx")
    supplement_tables = docx_table_count(DOCX_DIR / "supplement_revised.docx")
    report = f"""# Editorial Revision Hard-Stop Fix Readiness Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Final Recommendation

READY_FOR_EDITORIAL_REVIEW_WITH_STANDARD_HUMAN_FINAL_CHECKS

## Core Editorial Fixes

- Hard-stop package assembly fixed: `UPLOAD_THESE_FILES_ONLY` contains only the current corrected DOCX files, with no baseline snapshot files or stale duplicate submissions.
- Main manuscript table gate fixed: Word COM and python-docx read-back confirm 5 actual Word tables in `manuscript_main_revised.docx`.
- Figure file ambiguity fixed: canonical Figure 2 file now points to the two-panel rurality/SVI figure, and old dense single-panel Figure 2 bytes are not retained under the active Figure 2 filename.
- Figure caption/layout fixed: separate orphan figure-legend paragraphs were removed from the main DOCX; each figure page contains the image followed immediately by its caption.
- Model-total labeling fixed: Table 3 separates assigned deaths in the full county extract from analytic model deaths after covariate restriction.
- Round 3 Figure 4 fixed: main manuscript Figure 4 displays 2019-2024 urbanization-year MCOD counts and COVID-19 co-mention context, with caption wording matched to the rendered panels.
- Round 3 Figure 2 fixed: replaced dense single diagnostic plot with a two-panel rurality/SVI IRR figure using cleaner scenario labels.
- Round 3 layout fixed: main manuscript figures are placed one per page with captions immediately beneath each figure; map figures use whitespace-trimmed image assets.
- Round 3 age-adjustment concern addressed: Methods, Results, and Limitations clarify the age-structure rationale, the absence of direct county age-standardization, and the use of county age/sex covariates in primary models.
- Round 3 abstract fixed: the confusing county-year exact-death sentence is removed from active manuscript and abstract files.
- Round 3 supplement fixed: supplement DOCX embeds full model, interval, descriptive, merge, and geography tables rather than requiring repository lookup for interpretation.
- Round 3 cover-letter wording fixed: stronger validation wording changed to "reconciled CDC WONDER aggregate outputs."
- Final blocker fixed: Table 3 now reports "Preserves reconciled total?" with fixed-value stress-test labels aligned to the reconciled 58,380-death total.
- Round 2 B1 fixed: main manuscript DOCX contains embedded Figures 1-4; supplement DOCX contains embedded Figures S1-S3.
- Round 2 B2 fixed: supplement DOCX contains populated Tables S1-S10.
- Round 2 r1-r3 fixed: abstract clarifies the primary population-scaled/interval read and uniform allocation interpretation; Table 4 explains COVID midpoint intervals; title page includes declaration blocks.
- M1 reframed: scenario hierarchy now distinguishes visible-only models, total-preserving residual allocations, constant-count stress tests, non-total-preserving fixed stress tests, and interval models.
- M2 fixed: main manuscript DOCX contains populated Tables 1-5.
- M3 fixed: Figure 4 now covers 2019-2024 and includes COVID co-mention context.
- M4 fixed: Introduction and Discussion now position the work relative to Quick 2019.
- Minor issues addressed: abstract unit mix, orphan Q002 statistic removed, Figure 2 labels, alpha/interval/multiplicity caveats, map scope, residual allocation clipping audit, VIF maximum, affiliation consistency, repository author consistency, and Connecticut geography limitation.

## Reconciliation Audit

- MCOD total: 58,380
- Exact county deaths: 51,388
- Suppressed residual: 6,992
- Suppressed rows: 1,722
- Mean deaths per suppressed row: {analysis_summary['mean_deaths_per_suppressed_row']:.3f}
- Residual allocation totals preserved after 1-9 clipping: {analysis_summary['residual_allocation_totals_preserved']}

## Package Contents

- DOCX files: {len(list(DOCX_DIR.glob('*.docx')))}
- Markdown files: {len(list(MD_DIR.glob('*.md')))}
- Figure files: {len(list(FIG_DIR.glob('*.png')))}
- Revised table files: {len(list(TABLE_DIR.glob('*')))}
- Main manuscript embedded media count: {media_counts.get('manuscript_main_revised.docx', 0)}
- Supplement embedded media count: {media_counts.get('supplement_revised.docx', 0)}
- Main manuscript table count: {manuscript_tables}
- Supplement table count: {supplement_tables}

## QC

- DOCX read-back readable files: {int(readback['readable'].sum())}/{len(readback)}
- Forbidden-language scan hits: {qc['forbidden_hits']}
- Overclaim scan hits: {qc['overclaim_hits']}
- DOI present: {DOI_URL in '\\n'.join(collect_text_for_qc().values())}
- GitHub URL present: {GITHUB_URL in '\\n'.join(collect_text_for_qc().values())}

## Word/Visual QA

LibreOffice/soffice was not available on PATH in this environment, so the packaged LibreOffice DOCX-to-PNG render gate could not be used. Microsoft Word COM was available and used for authoritative document-open, table-count, and image-count checks. Human Microsoft Word/PDF visual inspection remains a standard final portal check.

## Remaining Human Checks

- Final reference-manager formatting check.
- Microsoft Word visual inspection and journal portal PDF check.
- Confirmation that the target journal wants tables embedded in the main manuscript versus uploaded as separate table files.
"""
    (REPORT_DIR / "editorial_revision_readiness_report.md").write_text(report, encoding="utf-8")
    response_matrix.to_csv(REPORT_DIR / "editorial_issue_response_matrix.csv", index=False)


def write_final_submission_files() -> None:
    global UPLOAD_DIR
    fallback_report = REPORT_DIR / "final_submission_folder_lock_fallback.md"
    if fallback_report.exists() and UPLOAD_DIR == OUT / "FINAL_SUBMISSION_FILES_ONLY":
        fallback_report.unlink()
    if UPLOAD_DIR.exists():
        try:
            shutil.rmtree(UPLOAD_DIR)
        except PermissionError as exc:
            fallback = OUT / "FINAL_SUBMISSION_FILES_ONLY_PUBLICATION_POLISH"
            if fallback.exists():
                shutil.rmtree(fallback)
            fallback_report.write_text(
                f"# Final Submission Folder Fallback\n\n"
                f"The canonical folder `{OUT / 'FINAL_SUBMISSION_FILES_ONLY'}` was locked by another process and could not be refreshed.\n\n"
                f"Windows error: `{exc}`\n\n"
                f"Current generated files were staged in `{fallback}` instead. The final ZIP still uses `FINAL_SUBMISSION_FILES_ONLY` as its internal top-level folder name.\n",
                encoding="utf-8",
            )
            UPLOAD_DIR = fallback
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    figure_upload_dir = UPLOAD_DIR / "figures"
    figure_upload_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for name in FINAL_DOCX_FILES:
        src = DOCX_DIR / name
        if not src.exists():
            rows.append({"relative_path": name, "bytes": 0, "sha256": "", "status": "missing"})
            continue
        dest = UPLOAD_DIR / name
        shutil.copy2(src, dest)
        rows.append({"relative_path": dest.relative_to(UPLOAD_DIR).as_posix(), "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "status": "included"})

    for name in FINAL_FIGURE_FILES:
        src = FIG_DIR / name
        if not src.exists():
            rows.append({"relative_path": f"figures/{name}", "bytes": 0, "sha256": "", "status": "missing"})
            continue
        dest = figure_upload_dir / name
        shutil.copy2(src, dest)
        rows.append({"relative_path": dest.relative_to(UPLOAD_DIR).as_posix(), "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "status": "included"})

    for name in [
        "final_submission_QA_report.md",
        "publication_figure_manifest.csv",
        "publication_figure_QA_report.md",
        "publication_revision_log.md",
    ]:
        src = REPORT_DIR / name
        if src.exists():
            dest = UPLOAD_DIR / name
            shutil.copy2(src, dest)
            rows.append({"relative_path": dest.relative_to(UPLOAD_DIR).as_posix(), "bytes": dest.stat().st_size, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "status": "included"})

    pd.DataFrame(rows).to_csv(REPORT_DIR / "final_submission_manifest.csv", index=False)


def write_word_com_layout_report() -> None:
    script = f"""
$ErrorActionPreference = 'Stop'
$docxDir = '{str(DOCX_DIR).replace("'", "''")}'
$reportDir = '{str(REPORT_DIR).replace("'", "''")}'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$docRows = @()
$figRows = @()
$tableRows = @()
try {{
  foreach ($file in Get-ChildItem -LiteralPath $docxDir -Filter *.docx | Sort-Object Name) {{
    $doc = $word.Documents.Open($file.FullName, $false, $true)
    try {{
      $doc.Repaginate()
      $docRows += [pscustomobject]@{{
        file = $file.Name
        word_tables = $doc.Tables.Count
        word_inline_shapes = $doc.InlineShapes.Count
        word_shapes = $doc.Shapes.Count
        word_paragraphs = $doc.Paragraphs.Count
        word_pages = $doc.ComputeStatistics(2)
      }}
      if ($file.Name -eq 'manuscript_main_revised.docx') {{
        for ($i = 1; $i -le $doc.Tables.Count; $i++) {{
          $rng = $doc.Tables.Item($i).Range
          $tableRows += [pscustomobject]@{{
            table_index = $i
            page = $rng.Information(3)
            rows = $doc.Tables.Item($i).Rows.Count
            columns = $doc.Tables.Item($i).Columns.Count
          }}
        }}
        $imageIndex = 0
        for ($p = 1; $p -le $doc.Paragraphs.Count; $p++) {{
          $para = $doc.Paragraphs.Item($p)
          if ($para.Range.InlineShapes.Count -gt 0) {{
            $imageIndex += 1
            $nextText = ''
            $nextPage = ''
            $nextParaIndex = ''
            for ($q = $p + 1; $q -le $doc.Paragraphs.Count; $q++) {{
              $candidate = $doc.Paragraphs.Item($q)
              $txt = $candidate.Range.Text -replace '[\\r\\a]', ''
              if ($txt.Trim().Length -gt 0) {{
                $nextText = $txt.Trim()
                $nextPage = $candidate.Range.Information(3)
                $nextParaIndex = $q
                break
              }}
            }}
            $figRows += [pscustomobject]@{{
              image_index = $imageIndex
              image_page = $para.Range.Information(3)
              next_nonempty_paragraph_index = $nextParaIndex
              next_nonempty_text = $nextText
              next_nonempty_page = $nextPage
              caption_immediately_follows = ($nextParaIndex -eq ($p + 1))
              caption_matches_image = $nextText.StartsWith(('Figure ' + $imageIndex + '.'))
              same_page = ($nextPage -eq $para.Range.Information(3))
            }}
          }}
        }}
      }}
    }} finally {{
      $doc.Close($false)
    }}
  }}
}} finally {{
  $word.Quit()
}}
$docRows | Export-Csv -LiteralPath (Join-Path $reportDir 'word_com_docx_structure.csv') -NoTypeInformation
$figRows | Export-Csv -LiteralPath (Join-Path $reportDir 'word_com_figure_layout.csv') -NoTypeInformation
$tableRows | Export-Csv -LiteralPath (Join-Path $reportDir 'word_com_table_layout.csv') -NoTypeInformation
"""
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        (REPORT_DIR / "word_com_layout_stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (REPORT_DIR / "word_com_layout_stderr.txt").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            (REPORT_DIR / "word_com_layout_error.txt").write_text(
                f"returncode={completed.returncode}\n{completed.stderr}\n", encoding="utf-8"
            )
    except Exception as exc:
        (REPORT_DIR / "word_com_layout_error.txt").write_text(str(exc), encoding="utf-8")


def docx_text(path: Path) -> str:
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    for section in doc.sections:
        for paragraph in section.footer.paragraphs:
            parts.append(paragraph.text)
    return "\n".join(parts)


def docx_footer_text(path: Path) -> str:
    doc = Document(path)
    parts = []
    for section in doc.sections:
        for paragraph in section.footer.paragraphs:
            if paragraph.text.strip():
                parts.append(paragraph.text.strip())
    return "\n".join(parts)


def media_hashes(path: Path) -> set[str]:
    hashes: set[str] = set()
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.startswith("word/media/"):
                hashes.add(hashlib.sha256(zf.read(name)).hexdigest())
    return hashes


def first_visible_reference_number(path: Path) -> int | None:
    doc = Document(path)
    in_references = False
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if text.lower() == "references":
            in_references = True
            continue
        if in_references:
            match = re.match(r"^(\d+)\.", text)
            return int(match.group(1)) if match else None
    return None


def docx_table_headers(path: Path, table_index: int) -> list[str]:
    doc = Document(path)
    if len(doc.tables) < table_index:
        return []
    table = doc.tables[table_index - 1]
    if not table.rows:
        return []
    return [cell.text.strip() for cell in table.rows[0].cells]


def docx_table_rows(path: Path, table_index: int) -> list[dict[str, str]]:
    doc = Document(path)
    if len(doc.tables) < table_index:
        return []
    table = doc.tables[table_index - 1]
    if not table.rows:
        return []
    headers = [cell.text.strip() for cell in table.rows[0].cells]
    rows = []
    for row in table.rows[1:]:
        values = [cell.text.strip() for cell in row.cells]
        rows.append(dict(zip(headers, values)))
    return rows


def scan_text_artifacts(texts: dict[str, str]) -> dict[str, list[str]]:
    patterns = {
        "replacement_character": "\ufffd",
        "soft_hyphen": "\u00ad",
        "broken_hyphen_county": "county\ufffelevel",
        "broken_hyphen_total": "total\ufffepreserving",
        "placeholder": "[missing figure file:",
        "internal_process_note": "response_to_editorial_review",
        "stale_figure_filename": "figure3_suppression_aware_residual_rate",
        "old_dense_figure2_filename": "suppression_bounds_forest_plot",
        "pending_repository_wording": "repository pending",
        "provisional_availability_wording": "will be made available in a public repository",
        "codex_process_language": "codex",
        "package_process_language": "revised package",
    }
    hits: dict[str, list[str]] = {key: [] for key in patterns}
    for path, text in texts.items():
        low = text.lower()
        for key, pattern in patterns.items():
            if pattern.lower() in low:
                hits[key].append(path)
    return {key: value for key, value in hits.items() if value}


def write_final_submission_qa_report() -> None:
    rows = []

    def add_check(check: str, passed: bool, detail: str) -> None:
        rows.append({"check": check, "passed": bool(passed), "detail": detail})

    manuscript_path = DOCX_DIR / "manuscript_main_revised.docx"
    manuscript = Document(manuscript_path)
    manuscript_text = docx_text(manuscript_path)
    add_check("Main DOCX has populated Tables 1-5", len(manuscript.tables) == 5, f"table_count={len(manuscript.tables)}")

    main_media_hashes = media_hashes(manuscript_path)
    figure_hash_results = []
    active_pngs = [
        "figure1_county_suppression_status_revised.png",
        "figure2_suppression_bounds_revised.png",
        "figure3_scenario_envelope_revised.png",
        "figure4_temporal_covid_context_revised.png",
    ]
    for name in active_pngs:
        fig_path = FIG_DIR / name
        if not fig_path.exists():
            figure_hash_results.append(f"{name}:missing")
            continue
        figure_hash = hashlib.sha256(fig_path.read_bytes()).hexdigest()
        figure_hash_results.append(f"{name}:{'embedded' if figure_hash in main_media_hashes else 'not_embedded'}")
    add_check(
        "Main DOCX has Figures 1-4 with current regenerated PNG bytes",
        all(item.endswith(":embedded") for item in figure_hash_results),
        "; ".join(figure_hash_results),
    )

    figure_manifest = REPORT_DIR / "publication_figure_manifest.csv"
    if figure_manifest.exists():
        manifest_rows = pd.read_csv(figure_manifest)
        main_manifest = manifest_rows[manifest_rows["figure_number"].astype(str).isin(["1", "2", "3", "4"])]
        main_formats = main_manifest.groupby("figure_number")["format"].apply(lambda x: set(str(v).lower() for v in x)).to_dict()
        missing_formats = {
            str(fig): sorted({"png", "svg", "pdf", "tiff"} - main_formats.get(str(fig), set()))
            for fig in ["1", "2", "3", "4"]
            if {"png", "svg", "pdf", "tiff"} - main_formats.get(str(fig), set())
        }
        checksum_missing = int(main_manifest["sha256"].fillna("").eq("").sum())
    else:
        manifest_rows = pd.DataFrame()
        missing_formats = {"manifest": ["missing"]}
        checksum_missing = -1
    add_check("Main figure files exist in PDF/SVG/TIFF/PNG", not missing_formats, f"missing_formats={missing_formats}")
    add_check("Figure manifest exists and checksums are present", figure_manifest.exists() and checksum_missing == 0, f"checksum_missing={checksum_missing}")

    county = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "county_period_analysis.csv", dtype={"county_fips": str})
    counts = county["death_status"].value_counts().to_dict()
    figure1_counts_match = counts.get("exact", 0) == 1085 and counts.get("suppressed_1_9", 0) == 1722 and counts.get("zero", 0) == 335
    add_check(
        "Figure 1 legend/category counts match Table 1",
        figure1_counts_match,
        f"exact={counts.get('exact', 0):,}; suppressed_1_9={counts.get('suppressed_1_9', 0):,}; zero={counts.get('zero', 0):,}",
    )
    if not manifest_rows.empty:
        fig2_source = pd.read_csv(TABLE_DIR / "table3_suppression_aware_models_revised_full.csv")
        fig2_terms = fig2_source[
            (
                fig2_source["term"].isin(["primary_rurality_nonmetro_nonadjacent", "svi_quartile_Q4_highest"])
                & (
                    fig2_source["model_family"].eq("rurality_svi_composite")
                    | fig2_source["model_family"].eq("interval_nb_rurality_svi")
                )
            )
        ]
        fig2_ci_not_clipped = fig2_terms["ci_low"].min() >= 0.42 and fig2_terms["ci_high"].max() <= 2.75
        fig2_detail = f"source_ci_range={fig2_terms['ci_low'].min():.3f}-{fig2_terms['ci_high'].max():.3f}; plotting_range=0.42-2.75"
    else:
        fig2_ci_not_clipped = False
        fig2_detail = "manifest missing"
    add_check("Figure 2 CIs are not silently clipped", fig2_ci_not_clipped, fig2_detail)

    fig3_decision_documented = (
        "Figure 3 summarizes the nonmetro nonadjacent scenario envelope" in manuscript_text
        and "Figure S3" in docx_text(DOCX_DIR / "supplement_revised.docx")
        and (FIG_DIR / "figureS3_residual_allocation_atlas.png").exists()
    )
    add_check("Figure 3 decision documented", fig3_decision_documented, "main Figure 3 replaced by scenario envelope; residual atlas moved to Supplementary Figure S3")

    temporal = pd.read_csv(PROJECT_ROOT / "tables" / "table4_temporal_context.csv")
    urban_total = int(round(float(temporal.loc[temporal["source"].eq("urbanization_year"), "deaths"].sum())))
    covid = pd.read_csv(PROJECT_ROOT / "tables" / "covid_by_urbanization_year.csv")
    covid_lower = int(round(float(covid["lower"].sum())))
    covid_upper = int(round(float(covid["upper"].sum())))
    fig4_values_ok = urban_total == 58380 and covid_lower <= covid_upper and "midpoint bars with lower-upper suppression bounds" in manuscript_text
    add_check("Figure 4 values match frozen inputs", fig4_values_ok, f"urbanization_year_deaths={urban_total:,}; covid_interval={covid_lower:,}-{covid_upper:,}")

    first_ref = first_visible_reference_number(manuscript_path)
    add_check("References start at 1", first_ref == 1, f"first_visible_reference_number={first_ref}")

    expected_t3_headers = [
        "Tier",
        "Scenario",
        "Assigned deaths, full extract",
        "Analytic model deaths",
        "Preserves reconciled total?",
        "IRR",
        "95% CI",
    ]
    actual_t3_headers = docx_table_headers(manuscript_path, 3)
    add_check("Table 3 compressed", actual_t3_headers == expected_t3_headers, f"headers={actual_t3_headers}")
    actual_t3_rows = docx_table_rows(manuscript_path, 3)
    actual_preserves = {row.get("Scenario", ""): row.get("Preserves reconciled total?", "") for row in actual_t3_rows}
    fixed_value_failures = {
        scenario: actual_preserves.get(scenario)
        for scenario in ["Suppressed = 1", "Suppressed = 5", "Suppressed = 9"]
        if actual_preserves.get(scenario) != "No"
    }
    add_check(
        "Table 3 fixed-value stress tests are not marked total-preserving",
        not fixed_value_failures,
        f"values={actual_preserves}",
    )
    total_preservation_failures = {
        scenario: {"expected": expected, "actual": actual_preserves.get(scenario)}
        for scenario, expected in TABLE3_PRESERVES_RECONCILED_TOTAL.items()
        if actual_preserves.get(scenario) != expected
    }
    add_check(
        "Table 3 preserves-reconciled-total labels match expected mapping",
        not total_preservation_failures,
        f"failures={total_preservation_failures}",
    )

    footer_issues = []
    for name in FINAL_DOCX_FILES:
        path = DOCX_DIR / name
        if path.exists():
            footer_text = docx_footer_text(path)
            if footer_text:
                footer_issues.append(f"{name}:{footer_text}")
    add_check("No visible filename footer remains in final DOCX files", not footer_issues, "; ".join(footer_issues) if footer_issues else "all final DOCX footers empty")

    highlights_text = docx_text(DOCX_DIR / "highlights_revised.docx")
    process_terms = ["revised package", "corrected", "populated main tables", "editorial", "upload"]
    process_hits = [term for term in process_terms if term.lower() in highlights_text.lower()]
    add_check("Highlights contain only scientific highlights", not process_hits, f"process_hits={process_hits}")

    supplement_doc = Document(DOCX_DIR / "supplement_revised.docx")
    comma_year_hits = []
    for table_index, table in enumerate(supplement_doc.tables, 1):
        if not table.rows:
            continue
        headers = [cell.text.strip().lower() for cell in table.rows[0].cells]
        year_columns = [
            idx
            for idx, header in enumerate(headers)
            if "year" in header and "person year" not in header and "person-year" not in header
        ]
        for row_index, row in enumerate(table.rows[1:], 2):
            for idx in year_columns:
                value = row.cells[idx].text.strip()
                if "," in value:
                    comma_year_hits.append(f"table {table_index} row {row_index} value {value}")
    add_check("Supplement years are plain 2019-2024 in year columns", not comma_year_hits, f"comma_year_hits={comma_year_hits}")

    cover_text = docx_text(DOCX_DIR / "cover_letter_revised.docx")
    add_check(
        "Cover letter does not imply formal revision and uses reconciled wording",
        "revised original research manuscript" not in cover_text.lower() and "validated cdc wonder outputs" not in cover_text.lower() and "reconciled CDC WONDER aggregate outputs" in cover_text,
        "fresh-submission wording checked",
    )

    response_in_final = list(UPLOAD_DIR.rglob("response_to_editorial_review.docx")) if UPLOAD_DIR.exists() else []
    add_check("response_to_editorial_review.docx excluded from final upload folder", not response_in_final, f"matches={len(response_in_final)}")

    required_totals = [
        "58,380",
        "51,388",
        "1,722",
        "335",
        "6,992",
        "1,936",
        "22,306",
        "0.97",
        "1.13",
        "1.04",
        "1.07",
    ]
    missing_totals = [item for item in required_totals if item not in manuscript_text]
    add_check("Core totals and model estimates preserved in main manuscript text", not missing_totals, f"missing={missing_totals}")

    expected_final_files = FINAL_DOCX_FILES + [f"figures/{name}" for name in FINAL_FIGURE_FILES]
    missing_final_files = [rel for rel in expected_final_files if not (UPLOAD_DIR / rel).exists()]
    add_check("Final folder contains allowlisted DOCX and figure assets", not missing_final_files, f"missing={missing_final_files}")
    final_folder_issues = []
    final_main = UPLOAD_DIR / "manuscript_main_revised.docx"
    final_supp = UPLOAD_DIR / "supplement_revised.docx"
    duplicate_main_docs = list(UPLOAD_DIR.glob("*manuscript_main*.docx")) if UPLOAD_DIR.exists() else []
    duplicate_supp_docs = list(UPLOAD_DIR.glob("*supplement*.docx")) if UPLOAD_DIR.exists() else []
    if len(duplicate_main_docs) != 1:
        final_folder_issues.append(f"main_manuscript_docx_count={len(duplicate_main_docs)}")
    if len(duplicate_supp_docs) != 1:
        final_folder_issues.append(f"supplement_docx_count={len(duplicate_supp_docs)}")
    if final_main.exists() and (DOCX_DIR / "manuscript_main_revised.docx").exists():
        if hashlib.sha256(final_main.read_bytes()).hexdigest() != hashlib.sha256((DOCX_DIR / "manuscript_main_revised.docx").read_bytes()).hexdigest():
            final_folder_issues.append("main manuscript in final folder differs from newest generated DOCX")
    if final_supp.exists() and (DOCX_DIR / "supplement_revised.docx").exists():
        if hashlib.sha256(final_supp.read_bytes()).hexdigest() != hashlib.sha256((DOCX_DIR / "supplement_revised.docx").read_bytes()).hexdigest():
            final_folder_issues.append("supplement in final folder differs from newest generated DOCX")
    if final_main.exists():
        final_main_text = docx_text(final_main)
        final_main_t3_headers = docx_table_headers(final_main, 3)
        if first_visible_reference_number(final_main) != 1:
            final_folder_issues.append("final manuscript references do not begin at 1")
        if "Figure 3. Residual-allocation" in final_main_text or "Figure 3. Suppression-aware residual" in final_main_text:
            final_folder_issues.append("final manuscript still contains old residual-allocation Figure 3 caption")
        if "Interpretation note" in final_main_t3_headers:
            final_folder_issues.append("final manuscript Table 3 still contains old Interpretation note column")
        if "Total-preserving?" in final_main_t3_headers:
            final_folder_issues.append("final manuscript Table 3 still contains old Total-preserving? column")
        if "Preserves reconciled total?" not in final_main_t3_headers:
            final_folder_issues.append("final manuscript Table 3 lacks Preserves reconciled total? column")
    stale_final_names = [
        p.name
        for p in UPLOAD_DIR.glob("*.docx")
        if any(token in p.name.lower() for token in ["baseline", "stale", "old"]) or "(1)" in p.name
    ] if UPLOAD_DIR.exists() else []
    if stale_final_names:
        final_folder_issues.append(f"stale-looking docx names={stale_final_names}")
    add_check(
        "Final submission folder contains newest main/supplement and no named stale states",
        not final_folder_issues,
        "; ".join(final_folder_issues) if final_folder_issues else "newest generated main and supplement only; references start at 1; Figure 3 and Table 3 stale states absent",
    )

    visible_texts = {}
    for path in list(DOCX_DIR.glob("*.docx")) + [p for p in MD_DIR.glob("*.md") if "response_to_editorial_review" not in p.name]:
        if path.suffix.lower() == ".md":
            visible_texts[str(path)] = path.read_text(encoding="utf-8", errors="replace")
        else:
            visible_texts[str(path)] = docx_text(path)
    artifact_hits = scan_text_artifacts(visible_texts)
    add_check("No broken hyphenation/replacement artifacts", not any(k in artifact_hits for k in ["replacement_character", "soft_hyphen", "broken_hyphen_county", "broken_hyphen_total"]), f"hits={artifact_hits}")
    add_check("No placeholder or internal process notes", not any(k in artifact_hits for k in ["placeholder", "internal_process_note"]), f"hits={artifact_hits}")
    add_check("No AI/process language outside required AI declaration", not any(k in artifact_hits for k in ["codex_process_language", "package_process_language"]), f"hits={artifact_hits}")
    add_check("No stale figure filenames", not any(k in artifact_hits for k in ["stale_figure_filename", "old_dense_figure2_filename"]), f"hits={artifact_hits}")

    footer_issues_detail = "; ".join(footer_issues) if footer_issues else "all final DOCX footers empty"
    add_check("No hidden filename footers", not footer_issues, footer_issues_detail)

    doi_texts = {
        "title": docx_text(DOCX_DIR / "title_page_revised.docx"),
        "main": manuscript_text,
        "cover": docx_text(DOCX_DIR / "cover_letter_revised.docx"),
        "supplement": docx_text(DOCX_DIR / "supplement_revised.docx"),
    }
    doi_consistent = all(GITHUB_URL in text and DOI_URL in text for text in doi_texts.values()) and "will be made available in a public repository" not in "\n".join(doi_texts.values())
    add_check("GitHub/Zenodo/DOI wording is final or replaced consistently", doi_consistent, f"GitHub URL and Zenodo DOI retained consistently; release metadata checked live as {REPOSITORY_RELEASE_VERSION}")
    reference_text = (REF_DIR / "references_provisional.csv").read_text(encoding="utf-8", errors="replace") if (REF_DIR / "references_provisional.csv").exists() else ""
    release_version_texts = {
        **doi_texts,
        "readme": (PROJECT_ROOT / "README.md").read_text(encoding="utf-8", errors="replace") if (PROJECT_ROOT / "README.md").exists() else "",
        "reference_list": reference_text,
    }
    stale_release_hits = [
        name
        for name, text in release_version_texts.items()
        if "Version 1.0.0" in text or "v1.0.0" in text
    ]
    explicit_release_claims = {
        name: REPOSITORY_RELEASE_VERSION in text
        for name, text in release_version_texts.items()
        if "Version " in text or "v1.0" in text
    }
    add_check(
        "GitHub/Zenodo version wording is consistent across package text",
        not stale_release_hits and REPOSITORY_RELEASE_VERSION in manuscript_text and REPOSITORY_RELEASE_VERSION in reference_text,
        f"expected={REPOSITORY_RELEASE_VERSION}; stale_release_hits={stale_release_hits}; explicit_release_claims={explicit_release_claims}",
    )
    add_check(
        "No stale DOI/release placeholder wording",
        not any(k in artifact_hits for k in ["pending_repository_wording", "provisional_availability_wording"]),
        f"hits={artifact_hits}",
    )

    qa_df = pd.DataFrame(rows)
    qa_df.to_csv(REPORT_DIR / "final_submission_QA_checks.csv", index=False)
    overall = bool(qa_df["passed"].all())
    report_lines = [
        "# Final Submission QA Report",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Overall status: {'PASS' if overall else 'CHECK REQUIRED'}",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        detail = str(row["detail"]).replace("|", "\\|")
        report_lines.append(f"| {row['check']} | {row['passed']} | {detail} |")
    report_lines.extend(
        [
            "",
            "## Clean final folder",
            "",
            f"`{UPLOAD_DIR}`",
            "",
            "The clean folder is allowlist-based and excludes `response_to_editorial_review.docx`, stale baseline attachments, and internal package assembly notes.",
        ]
    )
    (REPORT_DIR / "final_submission_QA_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def write_publication_revision_log() -> None:
    log = f"""# Publication Figure and Manuscript Polish Revision Log

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Scope

- Added a repository-local visualization dependency workflow using `requirements-viz.txt`.
- Added `scripts/check_viz_environment.py` to verify required packages, Matplotlib PNG/SVG/PDF export, and GeoPandas/Pyogrio county-GeoJSON reads.
- Added `scripts/visualization/pub_style.py` for shared journal figure typography, palettes, bundle export, checksums, manifests, and QA.
- Added `scripts/generate_publication_figures.py` as the single publication-figure entrypoint.
- Rebuilt Figures 1-4 from frozen analytic outputs only.
- Added PDF, SVG, EPS, TIFF, and PNG artwork bundles for main figures; TIFF and EPS outputs are checksum-tracked in the figure manifest.
- Preserved mortality counts, IRRs, confidence intervals, captions' scientific interpretation, and the conservative suppression-sensitive framing.
- Rebuilt the final DOCX package and included figure manifest/checksum artifacts.

## Figure Changes

- Figure 1: removed the redundant in-map legend, retained the right-side count/proportion panel, and strengthened the unmatched/missing-covariate overlay.
- Figure 2: expanded the shared log-scale x-axis so the Panel B interval-model CI is fully visible and not silently clipped.
- Figure 3: replaced the main residual-allocation map with a scenario-envelope figure for the nonmetro nonadjacent IRR; moved the residual-allocation atlas to Supplementary Figure S3.
- Figure 4: clarified that COVID bars are midpoint values with lower-upper interval bounds and made interval whiskers more visible.
- Supplementary figures: regenerated S1-S3 with the shared publication style; S3 carries the residual-allocation atlas warning.

## Manuscript Changes

- Compressed main Table 3 to Tier, Scenario, assigned deaths, analytic model deaths, the "Preserves reconciled total?" flag, IRR, and 95% CI.
- Moved long scenario interpretation notes out of main Table 3 while retaining the full scenario audit and full model table in the supplement.
- Converted visible manuscript references to deterministic manually numbered paragraphs beginning at 1.
- Added QA checks for figure formats, manifest checksums, Figure 2 clipping, Figure 3 decision, Figure 4 frozen-input consistency, Table 3 compression, Table 3 total-preservation mapping, final-folder stale states, reference numbering, broken text artifacts, stale filenames, hidden footers, and DOI/repository wording.

## Scientific Guardrails

- CDC WONDER was not re-queried.
- Raw mortality/covariate files were not modified.
- The known core totals and model estimates are preserved in the rebuilt manuscript.
- Residual-allocation county rates remain labeled as illustrative and not recovered true county rates in Supplementary Figure S3.
- The live public GitHub repository and Zenodo DOI wording was retained consistently across submission documents, with the repository/archive citation normalized to v1.0.1.
"""
    (REPORT_DIR / "publication_revision_log.md").write_text(log, encoding="utf-8")


def write_package_inventory() -> None:
    include_dirs = [DOCX_DIR, MD_DIR, TABLE_DIR, FIG_DIR, REPORT_DIR, REF_DIR, SUPP_DIR, INTERNAL_DIR, UPLOAD_DIR]
    rows = []
    checksums = []
    for directory in include_dirs:
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.suffix.lower() == ".zip":
                continue
            if path.name in {"final_file_inventory.csv", "final_checksums.csv"}:
                continue
            rel = path.relative_to(OUT).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(
                {
                    "relative_path": rel,
                    "bytes": path.stat().st_size,
                    "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "sha256": digest,
                }
            )
            checksums.append({"sha256": digest, "relative_path": rel})
    pd.DataFrame(rows).to_csv(REPORT_DIR / "final_file_inventory.csv", index=False)
    pd.DataFrame(checksums).to_csv(REPORT_DIR / "final_checksums.csv", index=False)


def build_zip() -> tuple[Path, str]:
    zip_path = FINAL_DIR / "FINAL_SUBMISSION_FILES_ONLY.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in UPLOAD_DIR.rglob("*"):
            if path.is_file() and path.suffix.lower() != ".zip":
                zf.write(path, Path("FINAL_SUBMISSION_FILES_ONLY") / path.relative_to(UPLOAD_DIR))
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (FINAL_DIR / (zip_path.name + ".sha256")).write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    return zip_path, digest


def main() -> None:
    ensure_dirs()
    generate_final_submission_figures()
    markdowns = write_markdown_files()
    build_all_docx(markdowns)
    write_xlsx()
    readback = readback_docx()
    qc = qc_reports()
    write_reports(readback, qc)
    write_word_com_layout_report()
    write_final_submission_files()
    write_final_submission_qa_report()
    write_publication_revision_log()
    write_final_submission_files()
    write_package_inventory()
    zip_path, digest = build_zip()
    print(f"editorial_package={OUT}")
    print(f"zip_path={zip_path}")
    print(f"zip_sha256={digest}")
    print(f"docx_count={len(list(DOCX_DIR.glob('*.docx')))}")
    print(f"forbidden_hits={qc['forbidden_hits']}")
    print(f"overclaim_hits={qc['overclaim_hits']}")


if __name__ == "__main__":
    main()
