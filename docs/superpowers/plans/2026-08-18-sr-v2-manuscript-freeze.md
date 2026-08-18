# Scientific Reports v2 manuscript result-freeze implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the passed primary, calibration, spatial, robustness, and suppression evidence into a hash-bound Scientific Reports manuscript, supplement, tables, figures, and fail-closed package without inventing human-only metadata.

**Architecture:** One pure aggregation/rendering module validates eight evidence families and atomically publishes a machine result-freeze contract. Existing manuscript and supplement Markdown remain templates; legacy submission builders are refactored to read the passed contract instead of embedded result literals. Submission QC distinguishes machine-complete documents from the five unresolved human/archive fields.

**Tech Stack:** Python 3.12, pandas, PyYAML, python-docx, Matplotlib, openpyxl, pytest.

**Spec:** `docs/superpowers/specs/2026-08-18-sr-v2-robustness-completion-design.md`

## Global Constraints

- Require PASS from primary, calibration, spatial decision, heavy sensitivity, age analysis, and suppression sensitivity before rendering machine results.
- Calibration wording must retain `precise_nominal_coverage_claim_authorized: false`.
- If the spatial trigger requires a spatial model, that model’s passed summary is mandatory; otherwise render a deterministic documented non-run.
- Leave exactly five human-only placeholders unresolved: `AUTHOR_BLOCK`, `ETHICS_DETERMINATION`, `REPOSITORY_DOI_AND_VERSION`, `REPOSITORY_VERSION`, and `REPOSITORY_DOI`.
- The machine pipeline never sets `submission_authorized: true`.
- Remove result-facing references to `Final Wahab HPC`, seeds 18291–18298, and old hardcoded diagnostics.

---

### Task 1: Eight-family result aggregator and authoritative renderer

**Files:**
- Create: `src/submission_viz/result_freeze.py`
- Create: `scripts/110_freeze_sr_v2_manuscript_results.py`
- Create: `tests/test_sr_v2_manuscript_freeze.py`
- Modify: `manuscript/scientific_reports_v2/placeholder_manifest.yaml`
- Modify: `manuscript/scientific_reports_v2/manuscript_draft_nonfinal.md`
- Modify: `manuscript/scientific_reports_v2/supplement_methods_validation_nonfinal.md`

**Interfaces:**
- Produces: `FamilyEvidence`, eight `collect_*` functions, `build_machine_contract`, `build_machine_replacements`, `build_supplement_tables`, `render_template`, and `freeze_results`.
- Produces: `outputs/scientific_reports_v2/manuscript_result_freeze/**`.

- [ ] **Step 1: Write the failing authority and family-gate tests**

```python
def test_machine_and_human_placeholder_partition_is_exact() -> None:
    manifest = load_placeholder_manifest(FIXTURE_ROOT)
    assert human_keys(manifest) == {
        "AUTHOR_BLOCK", "ETHICS_DETERMINATION", "REPOSITORY_DOI_AND_VERSION",
        "REPOSITORY_VERSION", "REPOSITORY_DOI",
    }

def test_missing_family_writes_hold_and_no_rendered_manuscript(tmp_path: Path) -> None:
    report = freeze_results(tmp_path)
    assert report["passed"] is False
    assert not (tmp_path / "manuscript_results_frozen_nonfinal.md").exists()
```

Add RED tests for all eight family predicates, precise-coverage prohibition, spatial trigger branching, age analysis/fallback evidence, suppression-primary agreement, human-key replacement rejection, unresolved-placeholder rules, S1–S9 schemas, output hashes, and end-to-end PASS fixtures.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_manuscript_freeze.py -q`

- [ ] **Step 3: Implement the pure evidence collectors**

```python
@dataclass(frozen=True)
class FamilyEvidence:
    family: str
    passed: bool
    sources: tuple[Path, ...]
    checks: tuple[dict[str, object], ...]
    values: dict[str, object]
```

Collectors require exact current artifacts for primary, calibration, spatial, prior, model family, temporal, age, and suppression. They validate upstream gates, required rows/columns, interpretation bounds, and SHA-256. They never load result values from `submission_visuals.yaml`.

- [ ] **Step 4: Implement atomic HOLD-to-PASS publication**

`freeze_results` first writes a temporary HOLD gate, validates all families in memory, builds replacements and S1–S9 tables, writes outputs to a temporary directory, hashes them, then atomically publishes the directory and PASS gate. Any exception leaves a HOLD and no rendered manuscript.

- [ ] **Step 5: Make placeholder authority explicit**

Every manifest entry gains `authority`, exact `source`, exact `gate`, and `renderer`. Register `CALIBRATION_RESULTS_PARAGRAPH` and `CALIBRATION_TABLE` as machine placeholders and replace the currently embedded calibration prose/table with those placeholders. The renderer rejects unregistered, empty, nested, or human-key replacements and leaves only the exact human set unresolved.

- [ ] **Step 6: Run tests and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_manuscript_freeze.py -q
.\.venv\Scripts\python.exe -m pytest -q
git add src/submission_viz/result_freeze.py scripts/110_freeze_sr_v2_manuscript_results.py tests/test_sr_v2_manuscript_freeze.py manuscript/scientific_reports_v2
git commit -m "feat: add fail-closed SR-v2 manuscript result freeze"
```

### Task 2: Contract-backed tables, manuscript builders, and QC

**Files:**
- Modify: `src/submission_viz/tables.py`
- Modify: `src/submission_viz/manuscript_text.py`
- Modify: `src/submission_viz/io.py`
- Modify: `src/submission_viz/qc.py`
- Modify: `config/submission_visuals.yaml`
- Modify: `scripts/91_validate_sr_v2_manuscript_scaffold.py`
- Modify: `tests/test_sr_v2_manuscript_freeze.py`

**Interfaces:**
- Consumes: passed `manuscript_result_freeze_gate.json` and `machine_authorized_values.json`.
- Produces: contract-backed S1–S9 tables, manuscript/supplement Markdown and DOCX, and result-freeze/submission QC modes.

- [ ] **Step 1: Write RED tests against legacy literals and stale sources**

Assert that builders refuse a failed/tampered freeze gate, Table 2 values equal the current machine contract, stale YAML scalars cannot override evidence, and result-facing source contains none of the prohibited cluster/seed/diagnostic literals.

- [ ] **Step 2: Replace legacy table mapping**

Build exactly:

```text
table_s1_parameter_diagnostics.csv
table_s2_acceptance.csv
table_s3_latent_diagnostics.csv
table_s4_prior_sensitivity.csv
table_s5_temporal_model_family_age.csv
table_s6_spatial_sensitivity.csv
table_s7_calibration.csv
table_s8_suppression_handling.csv
table_s9_covariate_imputation_age_inventory.csv
```

`build_supplement_tables` reads only passed normalized freeze tables.

- [ ] **Step 3: Replace embedded manuscript prose with frozen Markdown**

`_main_markdown` and `_supplement_markdown` verify the freeze gate/output hashes and load the rendered files. Remove old seeds, `Final Wahab HPC`, and embedded result claims. `submission_visuals.yaml` retains only paths to the gate and machine contract for results.

- [ ] **Step 4: Replace literal QC with hash-backed equality**

Add `_result_freeze_status`. Replace the old Table 2 literal assertion with comparisons against the current contract. Add `--mode result-freeze` to script 91: all machine placeholders resolved, exactly five human placeholders unresolved, gate/hash valid. Keep `--mode submission` at zero unresolved placeholders.

- [ ] **Step 5: Run focused/full tests and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_manuscript_freeze.py -q
.\.venv\Scripts\python.exe -m pytest -q
git add src/submission_viz config/submission_visuals.yaml scripts/91_validate_sr_v2_manuscript_scaffold.py tests/test_sr_v2_manuscript_freeze.py
git commit -m "fix: bind SR-v2 submission assets to frozen evidence"
```

### Task 3: Generate, inspect, and package the machine-complete manuscript

**Files:**
- Create: `outputs/scientific_reports_v2/manuscript_result_freeze/**`
- Create/modify: `outputs/submission/**`
- Modify: `.gitattributes`
- Modify: `docs/scientific_reports_v2/active_execution_status.md`

**Interfaces:**
- Consumes: passed result-freeze pipeline from Tasks 1–2.
- Produces: machine-complete nonfinal documents, figures/tables, and QC evidence; submission remains human-gated.

- [ ] **Step 1: Run the result freeze and result-freeze QC**

```powershell
.\.venv\Scripts\python.exe scripts\110_freeze_sr_v2_manuscript_results.py
.\.venv\Scripts\python.exe scripts\91_validate_sr_v2_manuscript_scaffold.py --mode result-freeze
```

Expected: PASS with all machine placeholders populated and exactly five human placeholders remaining.

- [ ] **Step 2: Rebuild manuscript assets in dependency order**

```powershell
.\.venv\Scripts\python.exe scripts\50_build_submission_figures.py
.\.venv\Scripts\python.exe scripts\51_build_submission_tables.py
.\.venv\Scripts\python.exe scripts\52_polish_manuscript_submission.py
.\.venv\Scripts\python.exe scripts\53_build_submission_supplement.py
.\.venv\Scripts\python.exe scripts\54_qc_submission_package.py
```

Do not run script 55 unless package QC passes. Script 55 rebuilds its package directory.

- [ ] **Step 3: Render and visually inspect every page**

Convert manuscript and supplement DOCX files to PDF in an isolated render directory. Check titles, equations, tables, figure legends, reference numbering, page breaks, and supplementary table widths. Any rendering correction receives a test or deterministic build check before regeneration.

- [ ] **Step 4: Run current Scientific Reports policy verification**

Verify title/abstract/keyword, data/code availability, competing-interest, author-contribution, supplementary-file, and AI-disclosure requirements against official current journal guidance. Record source URLs and access date in a policy-QC artifact; distinguish explicit requirements from recommendations.

- [ ] **Step 5: Run package build only after QC PASS**

Run: `.\.venv\Scripts\python.exe scripts\55_package_submission_assets.py`

Then rerun package QC against the final package and verify every manifest hash.

- [ ] **Step 6: Preserve byte evidence and commit**

Add `-text` coverage for result-freeze/QC manifests where byte identity is required. Update active status with machine PASS and the exact five human/external HOLD items.

```powershell
git add .gitattributes docs/scientific_reports_v2/active_execution_status.md outputs/scientific_reports_v2/manuscript_result_freeze outputs/submission
git commit -m "docs: freeze SR-v2 manuscript from verified evidence"
```

- [ ] **Step 7: Final verification boundary**

Run full pytest, result-freeze QC, package QC, hash audit, placeholder audit, and v1.1.1/production immutability checks. Report machine completion separately from human author/ethics/DOI approval. Do not push, publish, mint a DOI, or upload to the journal without explicit authorization.
