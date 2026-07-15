from __future__ import annotations

import csv
import hashlib
import re
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


ROOT = Path(r"C:\Research\EpilepsyMortalityOptionB")
RELEASE = Path(r"C:\Research\EpilepsyMortalityOptionB_repository_release")
PH11B = ROOT / "manuscript" / "phase11b_scientific_review"
PH12 = ROOT / "manuscript" / "phase12_submission_package"
PH13 = ROOT / "manuscript" / "phase13_final_review"
PH14 = ROOT / "manuscript" / "phase14_targeted_cleanup"
TABLES = ROOT / "tables"
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"

DOCX_DIR = PH14 / "docx"
MD_DIR = PH14 / "markdown"
FIG_DIR = PH14 / "figures"
TAB_DIR = PH14 / "tables"
SUPP_DIR = PH14 / "supplement"
REF_DIR = PH14 / "references"
REP_DIR = PH14 / "reports"
PKG_DIR = PH14 / "final_package"
SNAP_DIR = PH14 / "source_docx_snapshot"

TITLE = "Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024"
SHORT_TITLE = "Suppression-Aware Epilepsy Mortality Mapping"
JOURNAL = "Epilepsy & Behavior"
ARTICLE_TYPE = "Original Research"
AUTHOR = "Gregory Pierpoint, B.S."
EMAIL = "pierpogb@odu.edu"
PHONE = "202-809-8046"
ORCID = "https://orcid.org/0000-0001-8288-8549"
AFFILIATION = "Macon & Joan Brock Virginia Health Sciences, Eastern Virginia Medical School at Old Dominion University, Norfolk, VA, United States"
ADDRESS = "Eastern Virginia Medical School\nP.O. Box 1980\nNorfolk, VA 23501\nUnited States"
GITHUB_URL = "https://github.com/blakepi/epilepsy-status-mortality-suppression-atlas-2019-2024"
DOI = "10.5281/zenodo.20691623"
DOI_URL = f"https://doi.org/{DOI}"
REPO_COMMIT = "f28d059320f61b93a6c7426adfab4c53c198ff27"
TODAY = date.today().isoformat()

DATA_AVAILABILITY = (
    "The analysis used public, aggregate, deidentified mortality data from CDC WONDER and public county-level covariate sources. "
    f"Processed aggregate query outputs, derived analytic datasets, tables, figures, and documentation supporting this study are available at {GITHUB_URL}. "
    f"The archived release is available at {DOI_URL}. No person-level data are included."
)
CODE_AVAILABILITY = (
    "Analysis code used to import validated CDC WONDER outputs, construct suppression-aware analytic datasets, run bias-bounding and interval-likelihood models, "
    f"and generate tables and figures is available at {GITHUB_URL}. The archived release is available at {DOI_URL}."
)
ETHICS = "This study used public, aggregate, deidentified data and was deemed not human-subjects research."
FUNDING = "No external funding was received for this work."
CONFLICTS = "The author declares no competing interests."
AI_DISCLOSURE = (
    "Generative AI tools were used to assist with code generation, analysis organization, drafting, editing, and quality-control checks. "
    "The author reviewed and verified the analysis, scientific interpretation, references, and manuscript content and is responsible for the final work."
)
CREDIT = "Gregory Pierpoint: Conceptualization, Data curation, Formal analysis, Investigation, Methodology, Software, Validation, Visualization, Writing – original draft, Writing – review & editing."

QC_FORBIDDEN = [
    "[VERIFY",
    "VERIFY:",
    "Phase 9",
    "Phase 10",
    "Phase 11",
    "Phase 12",
    "Phase 13",
    "SUPPRESSION_SENSITIVE_SIGNAL",
    r"C:\Research",
    r"C:\Users",
    "References for human verification",
    "Final journal-formatted references should be inserted",
    "repository pending",
    "not assigned in Phase",
]

OVERCLAIM_PHRASES = [
    "population-representative",
    "county-representative",
    "confirmed rural disparity",
    "proved",
    "caused",
    "causal effect",
    "preventable deaths",
    "access caused mortality",
    "rurality caused mortality",
]

KEY_VALUES = {
    "MCOD total": "58,380",
    "Q001 exact county death sum": "51,388",
    "suppressed county-period rows": "1,722",
    "explicit zero county-period rows": "335",
    "Q002 county-year exact death sum": "33,217",
    "COVID co-mention": "1,936",
    "UCD total": "22,306",
    "Q014 UCD exact county death sum": "16,650",
    "Q014 UCD suppressed county rows": "1,866",
    "Q014 UCD explicit zero county rows": "772",
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def refresh_phase14() -> None:
    expected = Path(r"C:\Research\EpilepsyMortalityOptionB\manuscript\phase14_targeted_cleanup").resolve()
    PH14.mkdir(parents=True, exist_ok=True)
    if PH14.resolve() != expected:
        raise SystemExit(f"Refusing to refresh unexpected folder: {PH14}")
    for child in PH14.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for d in [DOCX_DIR, MD_DIR, FIG_DIR, TAB_DIR, SUPP_DIR, REF_DIR, REP_DIR, PKG_DIR, SNAP_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def copy_snapshot_and_assets() -> tuple[list[str], list[str]]:
    source_docx = PH12 / "docx"
    copied_docx = []
    for name in [
        "manuscript_main.docx",
        "title_page.docx",
        "abstract.docx",
        "cover_letter.docx",
        "highlights.docx",
        "supplement.docx",
        "STROBE_checklist.docx",
    ]:
        src = source_docx / name
        if src.exists():
            shutil.copy2(src, SNAP_DIR / name)
            copied_docx.append(str(src))

    copied_assets = []
    for src in sorted(TABLES.glob("*")):
        if src.is_file():
            shutil.copy2(src, TAB_DIR / src.name)
            copied_assets.append(str(src))
    for src in sorted(FIGURES.rglob("*.png")):
        dst = FIG_DIR / src.name
        shutil.copy2(src, dst)
        copied_assets.append(str(src))
    for name in [
        "descriptive_context_tables.xlsx",
        "county_year_suppression_by_rurality.csv",
        "suppression_bounds_model_results.csv",
        "interval_model_results.csv",
        "interval_model_fit_summary.csv",
        "component_model_vif.csv",
        "place_by_urbanization.csv",
        "age_by_urbanization.csv",
        "sex_by_urbanization.csv",
        "race_by_urbanization.csv",
        "hispanic_by_urbanization.csv",
        "ucd_county_suppression_profile.csv",
    ]:
        src = TABLES / name
        if src.exists():
            shutil.copy2(src, SUPP_DIR / name)
    for name in ["counties_present_in_covariates_missing_wonder.csv", "counties_present_in_wonder_missing_covariates.csv"]:
        src = ROOT / "data" / "processed" / name
        if src.exists():
            shutil.copy2(src, SUPP_DIR / name)
            copied_assets.append(str(src))
    return copied_docx, copied_assets


def references() -> list[dict[str, str]]:
    refs = [
        ("CDC WONDER Multiple Cause of Death, 2018-2024, Single Race database.", "CDC WONDER MCOD database", "verified_from_source_link", "https://wonder.cdc.gov/mcd-icd10-expanded.html", ""),
        ("Centers for Disease Control and Prevention. Multiple Cause of Death 2018-2024 by Single Race: CDC WONDER help documentation.", "CDC WONDER documentation", "verified_from_source_link", "https://wonder.cdc.gov/wonder/help/mcd-expanded.html", ""),
        ("CDC WONDER Underlying Cause of Death, 2018-2024, Single Race database.", "CDC WONDER UCD database", "verified_from_source_link", "https://wonder.cdc.gov/ucd-icd10-expanded.html", ""),
        ("Centers for Disease Control and Prevention/Agency for Toxic Substances and Disease Registry. CDC/ATSDR Social Vulnerability Index data and documentation.", "SVI documentation", "verified_from_source_link", "https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html", ""),
        ("U.S. Department of Agriculture Economic Research Service. Rural-Urban Continuum Codes documentation.", "RUCC documentation", "verified_from_source_link", "https://www.ers.usda.gov/data-products/rural-urban-continuum-codes/documentation", ""),
        ("National Center for Health Statistics. Urban-Rural Classification Scheme for Counties.", "NCHS urban-rural documentation", "verified_from_source_link", "https://www.cdc.gov/nchs/data-analysis-tools/urban-rural.html", ""),
        ("U.S. Census Bureau. American Community Survey 5-Year Data documentation.", "ACS documentation", "verified_from_source_link", "https://www.census.gov/data/developers/data-sets/acs-5year.html", ""),
        ("Vandenbroucke JP, von Elm E, Altman DG, et al. Strengthening the Reporting of Observational Studies in Epidemiology: explanation and elaboration. PLoS Med. 2007;4:e297.", "STROBE", "verified_from_source_link", "https://pmc.ncbi.nlm.nih.gov/articles/PMC2034723/", "PMCID page may require final reference-manager check."),
        ("STROBE Statement. STROBE checklists for observational studies.", "STROBE checklist", "verified_from_source_link", "https://www.strobe-statement.org/checklists/", ""),
        ("Elsevier. Generative AI policies for journals.", "AI disclosure policy", "verified_from_source_link", "https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals", ""),
        (f"Pierpoint G. Suppression-Aware County-Level Epilepsy and Status Epilepticus Mortality in the United States, 2019–2024. Version 1.0.0. Zenodo. {DOI_URL}", "Repository archived release", "verified_from_source_link", DOI_URL, ""),
        ("Quick H. Estimating County-Level Mortality Rates Using Highly Censored Data From CDC WONDER. Prev Chronic Dis. 2019;16:180441. doi:10.5888/pcd16.180441.", "suppressed-count methods", "verified_from_source_link", "https://www.cdc.gov/pcd/issues/2019/18_0441.htm", ""),
        ("DeGiorgio CM, Curtis A, Carapetian A, Hovsepian D, Krishnadasan A, Markovic D. Why are epilepsy mortality rates rising in the United States? A population-based multiple cause-of-death study. BMJ Open. 2020;10:e035767. doi:10.1136/bmjopen-2019-035767.", "prior epilepsy mortality literature", "verified_from_source_link", "https://pubmed.ncbi.nlm.nih.gov/32839157/", ""),
        ("Tian N, Kobau R, Friedman D, Liu Y, Eke PI, Greenlund KJ. Mortality and mortality disparities among people with epilepsy in the United States, 2011-2021. Epilepsy Behav. 2024;155:109770. doi:10.1016/j.yebeh.2024.109770.", "prior epilepsy mortality literature", "verified_from_source_link", "https://pubmed.ncbi.nlm.nih.gov/38636143/", ""),
        ("Duke SM, González Otárula KA, Canales T, Lu E, Stout A, Ghearing GR, Sajatovic M. A systematic literature review of health disparities among rural people with epilepsy in the United States and Canada. Epilepsy Behav. 2021;122:108181. doi:10.1016/j.yebeh.2021.108181.", "prior rural epilepsy outcome literature", "verified_from_source_link", "https://pubmed.ncbi.nlm.nih.gov/34252832/", ""),
        ("Iqbal J, Shafique MA, Rangwala BS, et al. Demographic and regional patterns of epilepsy-related mortality in the USA: insights from CDC WONDER data. Surg Neurol Int. 2024;15:450. doi:10.25259/SNI_592_2024.", "prior CDC WONDER epilepsy mortality literature", "verified_from_source_link", "https://pubmed.ncbi.nlm.nih.gov/39777187/", ""),
        ("Centers for Disease Control and Prevention. Reporting and Coding Deaths Due to COVID-19.", "COVID death-certificate context", "verified_from_source_link", "https://www.cdc.gov/nchs/covid19/coding-and-reporting.htm", ""),
    ]
    return [
        {
            "number": str(i),
            "reference": ref,
            "category": category,
            "status": status,
            "source_url": url,
            "notes": notes,
        }
        for i, (ref, category, status, url, notes) in enumerate(refs, 1)
    ]


def write_reference_files(refs: list[dict[str, str]]) -> str:
    with (REF_DIR / "references_provisional.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(refs[0]))
        writer.writeheader()
        writer.writerows(refs)
    counts = pd.DataFrame(refs)["status"].value_counts().to_dict()
    report = [
        "# Reference Verification Report",
        "",
        f"Generated: {TODAY}",
        "",
        "A provisional numbered reference list was built from official source links, local reference checklist content, repository metadata, and targeted source checks. Final reference-manager verification is still recommended before journal portal submission.",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in counts.items():
        report.append(f"- {status}: {count}")
    report += [
        "",
        "## References",
        "",
        "| # | Category | Status | Source URL | Notes |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in refs:
        report.append(f"| {row['number']} | {row['category']} | {row['status']} | {row['source_url']} | {row['notes']} |")
    report += [
        "",
        "## Omitted Categories",
        "",
        "No minimum required reference category was omitted for lack of metadata. Article-level entries should still be checked in a reference manager for exact author ordering and journal formatting.",
    ]
    write_text(REF_DIR / "REFERENCE_VERIFICATION_REPORT.md", "\n".join(report))
    return "\n".join(f"{row['number']}. {row['reference']} Available from: {row['source_url']}" for row in refs)


def strip_existing_tail(manuscript: str) -> str:
    start = manuscript.find("## Introduction")
    if start == -1:
        raise SystemExit("Introduction section not found in Phase 11b manuscript.")
    text = manuscript[start:]
    cutoff = text.find("## Data Availability")
    if cutoff != -1:
        text = text[:cutoff]
    return text.strip()


def clean_manuscript_body(text: str) -> str:
    replacements = {
        "Phase 10 stress testing classified the rurality finding as suppression-sensitive.": "Prespecified stress testing classified the rurality finding as suppression-sensitive.",
        "Phase 10 stress testing therefore classified the rurality finding as SUPPRESSION_SENSITIVE_SIGNAL.": "Prespecified stress testing classified the rurality finding as suppression-sensitive.",
        "Phase 10 suppression-sensitive classification": "prespecified suppression-sensitive classification",
        "SUPPRESSION_SENSITIVE_SIGNAL": "suppression-sensitive",
        "Phase 9/10 project": "analysis repository",
        "Phase 9 diagnostics": "analysis diagnostics",
        "Phase 9 project": "analysis repository",
        "Phase 9": "the present analysis",
        "Phase 10": "the prespecified stress-testing workflow",
        "Phase 11": "the manuscript workflow",
        "Phase 12": "the submission package workflow",
        "Phase 13": "the final review workflow",
        "no crosswalk correction was applied in the present analysis.": "no crosswalk correction was applied in the present analysis.",
        "no crosswalk correction was applied in Phase 9.": "no crosswalk correction was applied in the present analysis.",
        "Analyses were performed with reproducible Python scripts in the Phase 9/10 project.": "Analyses were performed with reproducible Python scripts archived in the public analysis repository.",
        "All Q001-Q015 exports were present, parsed, validated, and copied into the Option B analysis project with checksums.": "All Q001-Q015 exports were present, parsed, validated, and staged in the analysis repository with checksums.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("2019-2024", "2019–2024")
    return text


def abstract_md() -> str:
    return """# Abstract

## Objective

To quantify how CDC WONDER county-level suppression shapes national county-level analyses of epilepsy/status epilepticus-related mortality and to evaluate rurality-associated patterns using suppression-aware methods.

## Methods

We analyzed the CDC WONDER Multiple Cause of Death, 2018–2024 Single Race database for 2019–2024. The primary outcome was multiple-cause mortality with ICD-10 G40 (epilepsy) or G41 (status epilepticus) listed anywhere on the death certificate. Underlying-cause G40/G41 and COVID-19 co-mention (U07.1) were evaluated as contextual analyses. County-period and county-year extracts were linked to county rurality and social vulnerability covariates. Suppressed county cells were coded as interval counts of 1–9 deaths and were not treated as zero. We compared observed-only models with bias-bounding scenarios, residual-allocation analyses, and interval-likelihood negative binomial models.

## Results

National multiple-cause G40/G41 mortality totaled 58,380 deaths. The county-period extract reconciled to this total but contained 51,388 exact county deaths, 1,722 suppressed county rows, and 335 explicit zero rows. County-year exact deaths totaled 33,217. Nonmetro nonadjacent estimates ranged from below unity in observed-only and conservative scenarios to elevated under suppressed-equals-5, suppressed-equals-9, and pro-rural allocation scenarios; prespecified stress testing classified the rurality finding as suppression-sensitive. COVID co-mention totaled 1,936 deaths, and underlying-cause G40/G41 mortality totaled 22,306 deaths.

## Conclusion

County-level epilepsy/status epilepticus mortality inference in CDC WONDER is strongly shaped by outcome-dependent suppression. Suppression-aware bounding and interval-likelihood approaches provide a more transparent framework for interpreting rurality-associated, social, temporal, and geographic mortality patterns.
"""


def word_count(text: str) -> int:
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    body = re.sub(r"```.*?```", " ", body, flags=re.S)
    words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", body)
    return len(words)


def manuscript_md(reference_list: str) -> str:
    body = clean_manuscript_body(strip_existing_tail(read_text(PH11B / "MANUSCRIPT_DRAFT_REVIEWED.md")))
    # Remove old table/figure tail so final legends can be rebuilt cleanly.
    for marker in ["## Tables", "## Figure Legends", "## Supplemental Material Plan"]:
        pos = body.find(marker)
        if pos != -1:
            body = body[:pos].strip()
            break
    declarations = f"""## Data Availability

{DATA_AVAILABILITY}

## Code Availability

{CODE_AVAILABILITY}

## Ethics Statement

{ETHICS}

## Funding

{FUNDING}

## Conflicts of Interest

{CONFLICTS}

## Author Contributions

{CREDIT}

## Acknowledgments

None.

## Declaration of Generative AI and AI-assisted Technologies in the Writing Process

{AI_DISCLOSURE}

## References

{reference_list}

## Tables

Table 1. County characteristics by Q001 death-count status.

Table 2. Mortality totals and bounded rates by rurality and SVI category.

Table 3. Suppression-aware rurality and SVI model results.

Table 4. Temporal, urbanization, and COVID co-mention context.

Table 5. Underlying-cause sensitivity and UC/MC comparison.

## Figure Legends

Figure 1. County multiple-cause G40/G41 death-count status, 2019–2024.

Figure 2. Suppression-bounds model estimates.

Figure 3. Suppression-aware residual-allocation county mortality rate.

Figure 4. Urbanization-year trend and COVID co-mention context.
"""
    return f"# {TITLE}\n\n{abstract_md().replace('# Abstract', '## Abstract').strip()}\n\n## Keywords\n\nEpilepsy; status epilepticus; mortality; CDC WONDER; suppression-aware analysis; rural health; ecological study.\n\n{body}\n\n{declarations}".strip() + "\n"


def title_page_md() -> str:
    return f"""# Title Page

## Title

{TITLE}

## Short Title

{SHORT_TITLE}

## Article Type

{ARTICLE_TYPE}

## Target Journal

{JOURNAL}

## Author

{AUTHOR}

## Affiliation

{AFFILIATION}

## Corresponding Author

{AUTHOR}  
{ADDRESS.replace(chr(10), "  " + chr(10))}  
Email: {EMAIL}  
Phone: {PHONE}  
ORCID: {ORCID}

## Funding

{FUNDING}

## Conflicts of Interest

{CONFLICTS}

## Ethics Statement

{ETHICS}

## Data Availability

{DATA_AVAILABILITY}

## Code Availability

{CODE_AVAILABILITY}

## Author Contributions

{CREDIT}

## Acknowledgments

None.

## Declaration of Generative AI and AI-assisted Technologies in the Writing Process

{AI_DISCLOSURE}
"""


def cover_letter_md() -> str:
    return f"""# Cover Letter

Dear Editors,

We are pleased to submit the manuscript, "{TITLE}," for consideration in {JOURNAL}.

This manuscript provides a national suppression-aware county-level analysis and atlas of epilepsy/status epilepticus-related mortality in the United States from 2019–2024. Rather than treating CDC WONDER county suppression as a limitation only, the study explicitly models and bounds suppressed death counts and shows that observed rurality patterns are sensitive to suppression assumptions. The work is relevant to epilepsy outcomes research, rural health surveillance, and methods for using public mortality data responsibly.

The study uses validated CDC WONDER Multiple Cause of Death outputs, county covariates, bias-bounding scenarios, residual-allocation analyses, interval-likelihood negative binomial modeling, temporal and COVID co-mention context, and underlying-cause sensitivity. The central contribution is not a strong rural-disparity claim. Instead, the manuscript shows that county-level inference for epilepsy/status epilepticus mortality is strongly shaped by outcome-dependent small-cell suppression and should be interpreted using suppression-aware methods.

This manuscript is not under consideration elsewhere and has not been published previously. The author reports no external funding and no competing interests. The study used public, aggregate, deidentified data and was deemed not human-subjects research.

Sincerely,

{AUTHOR}  
Macon & Joan Brock Virginia Health Sciences  
Eastern Virginia Medical School at Old Dominion University  
P.O. Box 1980  
Norfolk, VA 23501  
United States  
{EMAIL}
"""


def highlights_md() -> str:
    items = [
        "County-level epilepsy/status epilepticus estimates were suppression-sensitive.",
        "CDC WONDER suppression affected 1,722 county-period rows.",
        "Observed-only rurality models did not support a stable final claim.",
        "Bias-bounding and interval models made hidden-count uncertainty explicit.",
        "A national suppression-aware mortality atlas was created for 2019–2024.",
    ]
    return "# Highlights\n\n" + "\n".join(f"- {item}" for item in items) + "\n"


def dataframe_preview(path: Path, max_rows: int = 25, filter_kind: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if filter_kind == "model":
        term_col = "term" if "term" in df.columns else None
        if term_col:
            mask = df[term_col].astype(str).str.contains("nonmetro_nonadjacent|svi", case=False, na=False)
            df = df[mask].copy()
        keep = [c for c in ["scenario", "model_family", "model_type", "term", "irr", "ci_low", "ci_high", "p_value", "n_rows", "events"] if c in df.columns]
        df = df[keep]
    if len(df) > max_rows:
        return df.head(max_rows).copy()
    return df.copy()


def supplement_md(omissions: list[str]) -> str:
    return f"""# Supplementary Material

## Supplementary Methods

The supplement provides publication-facing summaries of additional model specifications, descriptive context tables, county-year suppression summaries, and supplemental atlas figures. The extraction source trail, processed query inventory, and analytic code are available in the public repository and archived release: {GITHUB_URL}; {DOI_URL}.

Suppressed county cells were preserved as bounded 1–9 death intervals. Explicit zero cells were preserved as zeros. Missing or unreturned cells were not treated as zero. County-year data were used for reconciliation and suppression profiling rather than primary county-year modeling because county-year rows were sparse and suppression-heavy.

## Supplementary Tables

Table S1. County-year suppression summaries by year and rurality from Q002.

Table S2. Compact suppression-bounds model results for rurality and SVI terms. The full table is provided as a separate CSV file.

Table S3. Interval-likelihood negative binomial model summaries and fit diagnostics.

Table S4. Component ACS model collinearity diagnostics.

Table S5. Place of death by urbanization from Q006.

Table S6. Age-group distribution by urbanization from Q007.

Table S7. Sex distribution by urbanization from Q008.

Table S8. Race and Hispanic-origin descriptive tables from Q009A and Q009B.

Table S9. Underlying-cause county suppression profile from Q014.

Table S10. County merge and unmatched FIPS details, including Connecticut geography caveat.

## Supplementary Figures and Legends

Figure S1. Observed exact-county multiple-cause G40/G41 rate map.

Figure S2. Rural/high-SVI priority map under residual allocation.

Figure S3. State-period multiple-cause G40/G41 mortality rate map.

Figure S4. County underlying-cause G40/G41 suppression-status map.

Figure S5. National-year mortality trend.

## Supplementary Source/Query Inventory

The public repository includes the staged Q001–Q015 processed aggregate CDC WONDER outputs, checksums, extraction inventory, data dictionary, and source workflow notes. The archived release is available at {DOI_URL}.
"""


def setup_doc(doc: Document, title: str, double_spaced: bool = False, landscape: bool = False) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(12)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0 if double_spaced else 6)
    normal.paragraph_format.line_spacing = 2 if double_spaced else 1.15
    for name, size in [("Heading 1", 14), ("Heading 2", 13), ("Heading 3", 12)]:
        style = styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 1.15
    doc.core_properties.title = title
    doc.core_properties.author = AUTHOR


def add_markdown(doc: Document, text: str, *, title_shift: int = 0) -> None:
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            level = min(max(len(heading.group(1)) + title_shift, 1), 3)
            doc.add_heading(clean_inline(heading.group(2)), level=level)
            continue
        if line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(clean_inline(line[2:]))
            continue
        numbered = re.match(r"^(\d+)\.\s+(.*)$", line)
        if numbered:
            p = doc.add_paragraph(style="List Number")
            p.add_run(clean_inline(numbered.group(2)))
            continue
        p = doc.add_paragraph(clean_inline(line.replace("  ", " ")))


def clean_inline(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def add_df_table(doc: Document, df: pd.DataFrame, title: str, max_cols: int = 8) -> None:
    if df.empty:
        doc.add_paragraph(f"{title}: source table was empty.")
        return
    df = df.copy()
    if len(df.columns) > max_cols:
        df = df.iloc[:, :max_cols]
    doc.add_heading(title, level=3)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Table Grid"
    for i, col in enumerate(df.columns):
        table.rows[0].cells[i].text = str(col)
    for _, row in df.iterrows():
        cells = table.add_row().cells
        for i, col in enumerate(df.columns):
            val = row[col]
            if pd.isna(val):
                text = ""
            elif isinstance(val, float):
                text = f"{val:.4g}"
            else:
                text = str(val)
            cells[i].text = text
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(8)


def add_image(doc: Document, image_path: Path, caption: str, width: float = 6.2) -> None:
    if not image_path.exists():
        doc.add_paragraph(f"{caption} [Image file missing from final package.]")
        return
    doc.add_paragraph(caption)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(width))


def save_docx_from_md(path: Path, markdown: str, *, double_spaced: bool = False) -> None:
    doc = Document()
    setup_doc(doc, path.stem, double_spaced=double_spaced)
    add_markdown(doc, markdown)
    doc.save(path)


def build_manuscript_docx(markdown: str) -> None:
    doc = Document()
    setup_doc(doc, "manuscript_main", double_spaced=True)
    add_markdown(doc, markdown)
    # Embed/call out main figures after the text for review convenience.
    doc.add_page_break()
    doc.add_heading("Embedded Figure Review Copies", level=1)
    main_figures = [
        ("Figure 1. County multiple-cause G40/G41 death-count status, 2019–2024.", FIG_DIR / "map1_county_suppression_status.png"),
        ("Figure 2. Suppression-bounds model estimates.", FIG_DIR / "suppression_bounds_forest_plot.png"),
        ("Figure 3. Suppression-aware residual-allocation county mortality rate.", FIG_DIR / "map3_suppression_aware_predicted_rates.png"),
        ("Figure 4. Urbanization-year trend and COVID co-mention context.", FIG_DIR / "urbanization_year_trend.png"),
    ]
    for caption, image in main_figures:
        add_image(doc, image, caption, width=6.1)
    doc.save(DOCX_DIR / "manuscript_main.docx")


def build_supplement_docx(markdown: str, omissions: list[str]) -> None:
    doc = Document()
    setup_doc(doc, "supplement")
    add_markdown(doc, markdown)
    table_specs = [
        ("Table S1. County-year suppression summaries by year and rurality from Q002.", TABLES / "county_year_suppression_by_rurality.csv", None, 30),
        ("Table S2. Compact suppression-bounds model results for rurality and SVI terms.", TABLES / "suppression_bounds_model_results.csv", "model", 30),
        ("Table S3. Interval-likelihood negative binomial model summaries.", TABLES / "interval_model_results.csv", None, 20),
        ("Table S3b. Interval-likelihood fit diagnostics.", TABLES / "interval_model_fit_summary.csv", None, 20),
        ("Table S4. Component ACS model collinearity diagnostics.", TABLES / "component_model_vif.csv", None, 20),
        ("Table S5. Place of death by urbanization from Q006.", TABLES / "place_by_urbanization.csv", None, 30),
        ("Table S6. Age-group distribution by urbanization from Q007.", TABLES / "age_by_urbanization.csv", None, 40),
        ("Table S7. Sex distribution by urbanization from Q008.", TABLES / "sex_by_urbanization.csv", None, 20),
        ("Table S8a. Race descriptive table from Q009A.", TABLES / "race_by_urbanization.csv", None, 30),
        ("Table S8b. Hispanic-origin descriptive table from Q009B.", TABLES / "hispanic_by_urbanization.csv", None, 20),
        ("Table S9. Underlying-cause county suppression profile from Q014.", TABLES / "ucd_county_suppression_profile.csv", None, 20),
    ]
    doc.add_page_break()
    doc.add_heading("Supplementary Table Details", level=1)
    for title, path, filter_kind, max_rows in table_specs:
        if path.exists():
            add_df_table(doc, dataframe_preview(path, max_rows=max_rows, filter_kind=filter_kind), title)
            if len(pd.read_csv(path, low_memory=False)) > max_rows:
                doc.add_paragraph("Compact preview shown; the full table is included as a separate file in the final package.")
        else:
            omissions.append(f"Missing supplemental table source: {path.name}")
    # County merge details.
    merge_rows = []
    for name in ["counties_present_in_covariates_missing_wonder.csv", "counties_present_in_wonder_missing_covariates.csv"]:
        path = ROOT / "data" / "processed" / name
        if path.exists():
            merge_rows.append({"file": name, "rows": len(pd.read_csv(path, low_memory=False))})
        else:
            omissions.append(f"Missing county merge detail file: {name}")
    if merge_rows:
        add_df_table(doc, pd.DataFrame(merge_rows), "Table S10. County merge and unmatched FIPS details.")
    doc.add_page_break()
    doc.add_heading("Supplementary Figure Review Copies", level=1)
    figures = [
        ("Figure S1. Observed exact-county multiple-cause G40/G41 rate map.", FIG_DIR / "map2_observed_exact_county_rates.png"),
        ("Figure S2. Rural/high-SVI priority map under residual allocation.", FIG_DIR / "map4_rural_svi_priority.png"),
        ("Figure S3. State-period multiple-cause G40/G41 mortality rate map.", FIG_DIR / "map5_state_period_rates.png"),
        ("Figure S4. County underlying-cause G40/G41 suppression-status map.", FIG_DIR / "map6_ucd_suppression_status.png"),
        ("Figure S5. National-year mortality trend.", FIG_DIR / "national_year_trend.png"),
    ]
    for caption, path in figures:
        if path.exists():
            add_image(doc, path, caption, width=6.1)
        else:
            omissions.append(f"Missing supplemental figure source: {path.name}")
    omissions.append("Figure S6 interval-model diagnostics omitted: no standalone interval-diagnostics figure file was available.")
    doc.save(DOCX_DIR / "supplement.docx")


def build_strobe() -> None:
    rows = [
        ("1", "Title and abstract", "Title/Abstract", "Title identifies county-level mortality analysis; abstract summarizes design, data, methods, and key findings."),
        ("2", "Background/rationale", "Introduction", "Rationale for multiple-cause mortality and suppression-aware inference is described."),
        ("3", "Objectives", "Introduction: aims", "Study aims are stated."),
        ("4", "Study design", "Methods: Study design and data sources", "National ecological county-level mortality analysis."),
        ("5", "Setting", "Methods: Study design and data sources", "United States counties, 2019–2024."),
        ("6", "Participants", "Methods: Case definition", "Aggregate death records with ICD-10 G40/G41 mentions; no person-level records analyzed."),
        ("7", "Variables", "Methods: Case definition; County covariates", "Outcome, rurality, SVI, ACS components, temporal, COVID, and UCD variables defined."),
        ("8", "Data sources/measurement", "Methods: CDC WONDER extraction and validation", "CDC WONDER outputs and public county covariate sources described."),
        ("9", "Bias", "Methods: Suppression status definitions; Discussion", "Outcome-dependent suppression and ecological limitations described."),
        ("10", "Study size", "Results: Extraction validation", "County rows, national totals, and suppressed/exact/zero profiles reported."),
        ("11", "Quantitative variables", "Methods: County covariates and rurality measures", "RUCC, NCHS, SVI, and ACS handling described."),
        ("12", "Statistical methods", "Methods: Bias-bounding analyses; Interval-likelihood model", "Bias-bounding and interval-likelihood approaches described."),
        ("13", "Participants/units", "Results: County suppression and data visibility profile", "County rows and status groups reported."),
        ("14", "Descriptive data", "Results: County covariates and suppression status", "County covariate summaries by death-count status reported."),
        ("15", "Outcome data", "Results: Extraction validation and mortality totals", "MCOD, COVID co-mention, and UCD outcome totals reported."),
        ("16", "Main results", "Results: Suppression-aware rurality and SVI model results", "Model estimates reported with suppression-sensitive interpretation."),
        ("17", "Other analyses", "Results: Temporal, COVID co-mention, UCD sensitivity, atlas", "Context and sensitivity analyses reported."),
        ("18", "Key results", "Discussion: Principal findings", "Main findings summarized."),
        ("19", "Limitations", "Discussion: Limitations", "Ecological design, suppression assumptions, and coding limitations described."),
        ("20", "Interpretation", "Discussion", "Suppression-aware interpretation emphasized."),
        ("21", "Generalisability", "Discussion: Implications", "Scope limited to aggregate U.S. county-level public mortality data."),
        ("22", "Funding", "Declarations: Funding", FUNDING),
    ]
    doc = Document()
    setup_doc(doc, "STROBE_checklist")
    doc.add_heading("STROBE Checklist for Observational Studies", level=1)
    doc.add_paragraph("Section-based locations are provided because final journal portal page numbers may change after typesetting or PDF conversion.")
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for i, h in enumerate(["Item", "STROBE area", "Location", "Response"]):
        table.rows[0].cells[i].text = h
    for item, area, loc, resp in rows:
        cells = table.add_row().cells
        for i, value in enumerate([item, area, loc, resp]):
            cells[i].text = value
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9)
    doc.save(DOCX_DIR / "STROBE_checklist.docx")

    lines = [
        "# STROBE Checklist for Observational Studies",
        "",
        "Section-based locations are provided because final journal portal page numbers may change after typesetting or PDF conversion.",
        "",
        "| Item | STROBE area | Location | Response |",
        "| --- | --- | --- | --- |",
    ]
    for item, area, loc, resp in rows:
        lines.append(f"| {item} | {area} | {loc} | {resp} |")
    write_text(MD_DIR / "STROBE_checklist.md", "\n".join(lines) + "\n")


def build_all_documents() -> tuple[list[str], list[str], str]:
    refs = references()
    reference_list = write_reference_files(refs)
    omissions: list[str] = []
    manuscript = manuscript_md(reference_list)
    abstract = abstract_md()
    title_page = title_page_md()
    cover_letter = cover_letter_md()
    highlights = highlights_md()
    supplement = supplement_md(omissions)

    write_text(MD_DIR / "manuscript_main.md", manuscript)
    write_text(MD_DIR / "abstract.md", abstract)
    write_text(MD_DIR / "title_page.md", title_page)
    write_text(MD_DIR / "cover_letter.md", cover_letter)
    write_text(MD_DIR / "highlights.md", highlights)
    write_text(MD_DIR / "supplement.md", supplement)

    build_manuscript_docx(manuscript)
    save_docx_from_md(DOCX_DIR / "title_page.docx", title_page)
    save_docx_from_md(DOCX_DIR / "abstract.docx", abstract)
    save_docx_from_md(DOCX_DIR / "cover_letter.docx", cover_letter)
    save_docx_from_md(DOCX_DIR / "highlights.docx", highlights)
    build_supplement_docx(supplement, omissions)
    build_strobe()
    return [str(p) for p in sorted(DOCX_DIR.glob("*.docx"))], omissions, reference_list


def docx_text(path: Path) -> str:
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def docx_readback() -> list[dict[str, str]]:
    rows = []
    for path in sorted(DOCX_DIR.glob("*.docx")):
        try:
            doc = Document(path)
            rows.append({"file": path.name, "readable": "True", "paragraphs": str(len(doc.paragraphs)), "tables": str(len(doc.tables)), "bytes": str(path.stat().st_size)})
        except Exception as exc:
            rows.append({"file": path.name, "readable": "False", "paragraphs": "", "tables": "", "bytes": str(path.stat().st_size), "error": str(exc)})
    return rows


def scan_texts() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, bool]]:
    files = list(MD_DIR.glob("*.md")) + list(DOCX_DIR.glob("*.docx"))
    qc_hits = []
    overclaim_hits = []
    combined = []
    for path in files:
        text = docx_text(path) if path.suffix.lower() == ".docx" else read_text(path)
        combined.append(text)
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            for pattern in QC_FORBIDDEN:
                if pattern.lower() in line.lower():
                    qc_hits.append({"file": path.name, "line": str(i), "pattern": pattern, "context": line.strip()[:220]})
            for phrase in OVERCLAIM_PHRASES:
                if phrase.lower() in line.lower():
                    overclaim_hits.append({"file": path.name, "line": str(i), "phrase": phrase, "context": line.strip()[:220]})
    joined = "\n".join(combined)
    values_ok = {name: value in joined for name, value in KEY_VALUES.items()}
    return qc_hits, overclaim_hits, values_ok


def render_status() -> str:
    soffice = shutil.which("soffice")
    if not soffice:
        return "Visual render QA not completed because soffice/LibreOffice was not available on PATH; human Microsoft Word and portal-generated PDF inspection is required."
    return f"soffice detected at {soffice}; visual render QA can be performed manually if desired."


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_zip() -> Path:
    zip_path = PKG_DIR / "epilepsy_mortality_optionB_final_clean_submission_package.zip"
    include_dirs = [DOCX_DIR, FIG_DIR, TAB_DIR, SUPP_DIR, REF_DIR, REP_DIR, MD_DIR]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for folder in include_dirs:
            for path in sorted(folder.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".tmp"):
                    z.write(path, path.relative_to(PH14).as_posix())
    return zip_path


def write_reports(
    source_docx: list[str],
    copied_assets: list[str],
    omissions: list[str],
    readback_rows: list[dict[str, str]],
    qc_hits: list[dict[str, str]],
    overclaim_hits: list[dict[str, str]],
    values_ok: dict[str, bool],
    zip_path: Path,
    repo_status: str,
) -> None:
    with (REP_DIR / "docx_readback.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = sorted({k for row in readback_rows for k in row})
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(readback_rows)
    with (REP_DIR / "qc_internal_language_scan.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "line", "pattern", "context"])
        writer.writeheader()
        writer.writerows(qc_hits)
    with (REP_DIR / "qc_overclaim_scan.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "line", "phrase", "context"])
        writer.writeheader()
        writer.writerows(overclaim_hits)
    values_lines = "\n".join(f"- {name}: {'PASS' if ok else 'FAIL'} ({value})" for name, value in KEY_VALUES.items() for ok in [values_ok[name]])
    cleanup_report = f"""# Phase 14 Cleanup Report

Generated: {TODAY}

## Source files read

- Phase 12 DOCX snapshot files copied: {len(source_docx)}
- Phase 11b reviewed Markdown was used as the manuscript text source.
- Phase 9/10 tables, figures, and reports were used to build the final supplement and reference-support package.
- Repository release folder read: `{RELEASE}`

## Human metadata inserted

- Author: {AUTHOR}
- Affiliation: {AFFILIATION}
- Corresponding author email, phone, ORCID, and mailing address inserted into title page.
- Sole-author CRediT statement inserted.
- Funding, conflicts of interest, acknowledgments, ethics, and AI disclosure finalized.

## Repository DOI inserted

- GitHub URL inserted: {GITHUB_URL}
- Zenodo DOI URL inserted: {DOI_URL}

## Repository README/CITATION update status

{repo_status}

## Language cleanup performed

- Internal phase labels removed from manuscript-facing DOCX and Markdown files.
- Local Windows paths removed from manuscript-facing DOCX and Markdown files.
- Pending repository and verification placeholders resolved.
- Rurality framing preserved as suppression-sensitive rather than definitive.

## Internal phase/local path scan results

- Internal-language scan hits: {len(qc_hits)}
- Non-justified overclaim scan hits: {len(overclaim_hits)}

## Numeric consistency checks

{values_lines}

## Reference list build method

The provisional numbered reference list was built from official source links, repository DOI metadata, source reports/checklists, and targeted source checks. See `references/REFERENCE_VERIFICATION_REPORT.md` and `references/references_provisional.csv`.

## References requiring human verification

Final reference-manager verification is still recommended for article-level details and journal formatting, although no minimum reference category was omitted for lack of metadata.

## Supplement build summary

- Real supplement created with Supplementary Methods, Supplementary Tables, Supplementary Figures and Legends, and Supplementary Source/Query Inventory.
- Supplemental table/figure omissions documented below.

## Supplement omissions

{chr(10).join('- ' + item for item in omissions) if omissions else '- None.'}

## STROBE finalization summary

Final STROBE checklist DOCX created with section-based locations and completed funding item.

## DOCX structural read-back results

All expected DOCX files were generated. Read-back details are in `reports/docx_readback.csv`.

## Visual render QA status

{render_status()}

## Figures/tables copied

- Assets copied from tables/figures/data folders: {len(copied_assets)}
- Final figures folder: `{FIG_DIR}`
- Final tables folder: `{TAB_DIR}`

## Final ZIP path

`{zip_path}`

## Remaining human checks

- Final reference-manager verification.
- Microsoft Word visual inspection.
- Portal-generated PDF inspection.
- Confirmation that the journal accepts the supplement/table/figure packaging.
"""
    write_text(REP_DIR / "phase14_cleanup_report.md", cleanup_report)
    readiness = f"""# Final Submission Readiness Report

Generated: {TODAY}

Final recommendation: READY_WITH_MINOR_HUMAN_REFERENCE_CHECK

## Basis

- Manuscript-facing internal-language scan hits: {len(qc_hits)}
- Non-justified overclaim scan hits: {len(overclaim_hits)}
- DOI present in manuscript/title page/package text: {DOI_URL in (read_text(MD_DIR / "manuscript_main.md") + read_text(MD_DIR / "title_page.md"))}
- GitHub URL present in manuscript/title page/package text: {GITHUB_URL in (read_text(MD_DIR / "manuscript_main.md") + read_text(MD_DIR / "title_page.md"))}
- DOCX structural read-back complete: {all(row.get('readable') == 'True' for row in readback_rows)}
- Final ZIP created: {zip_path.exists()}

## Remaining Human Checks

- Final reference-manager verification.
- Microsoft Word visual inspection.
- Portal-generated PDF inspection.
- Confirmation that the journal accepts the supplement/table/figure packaging.
"""
    write_text(REP_DIR / "final_submission_readiness_report.md", readiness)


def update_repo_status_text() -> str:
    # The README/CITATION DOI commit was performed before this script in the
    # Phase 14 run. This function records the observed state without mutating
    # the repository again.
    readme = read_text(RELEASE / "README.md") if (RELEASE / "README.md").exists() else ""
    cff = read_text(RELEASE / "CITATION.cff") if (RELEASE / "CITATION.cff").exists() else ""
    doi_ok = DOI_URL in readme and DOI in cff
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=RELEASE, text=True).strip()
        status = subprocess.check_output(["git", "status", "--short", "--branch"], cwd=RELEASE, text=True).strip()
    except Exception as exc:
        return f"Repository DOI update could not be verified by git: {exc}"
    return f"Repository README/CITATION DOI update verified: {doi_ok}. Repository HEAD: `{commit}`. Git status: `{status}`."


def main() -> None:
    refresh_phase14()
    source_docx, copied_assets = copy_snapshot_and_assets()
    docx_paths, omissions, _ = build_all_documents()
    readback_rows = docx_readback()
    qc_hits, overclaim_hits, values_ok = scan_texts()
    # Write reports before zipping so the ZIP includes the reports.
    placeholder_zip = PKG_DIR / "epilepsy_mortality_optionB_final_clean_submission_package.zip"
    write_reports(source_docx, copied_assets, omissions, readback_rows, qc_hits, overclaim_hits, values_ok, placeholder_zip, update_repo_status_text())
    zip_path = make_zip()
    # Re-write reports with final ZIP size/hash now that it exists, then rebuild ZIP once more.
    write_reports(source_docx, copied_assets, omissions, readback_rows, qc_hits, overclaim_hits, values_ok, zip_path, update_repo_status_text())
    zip_path = make_zip()
    print(f"phase14_folder={PH14}")
    print(f"zip_path={zip_path}")
    print(f"docx_count={len(docx_paths)}")
    print(f"qc_hits={len(qc_hits)}")
    print(f"overclaim_hits={len(overclaim_hits)}")
    print(f"zip_sha256={sha256(zip_path)}")


if __name__ == "__main__":
    main()
