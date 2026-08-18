# Scientific Reports v2 spatial diagnostic implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a checksum-bound, computationally tractable residual Moran diagnostic from the passed corrected production run and resolve the prespecified spatial-model branch.

**Architecture:** Preserve the existing scientific statistic and deterministic permutations while replacing dense matrix multiplication with a CSR implementation. Bind the runner to a frozen production authority manifest, archive source provenance, and emit a fail-closed result whose action directly controls whether a spatial random-effect sensitivity is required.

**Tech Stack:** Python 3.12, NumPy, SciPy sparse matrices, pandas, PyArrow, pytest.

**Spec:** `docs/superpowers/specs/2026-08-18-sr-v2-robustness-completion-design.md`

## Global Constraints

- Do not modify `outputs/scientific_reports_v2/production_8chain/**`.
- Preserve county ordering, row standardization, seeds `20260811` and `20260812`, 9,999 global permutations, 999 within-state permutations, and the existing two-sided p-value formula.
- Global trigger: Pearson Moran's I at least `0.02` and two-sided permutation p at most `0.05`.
- Repeated-state trigger: at least three states satisfying the same thresholds.
- The output must record hashes for the production gate, posterior parameter draws, county posterior summary, model frame, and downloaded adjacency bytes.

---

### Task 1: Sparse-equivalent Moran implementation and runner preflight

**Files:**
- Modify: `src/bayes_constrained/spatial_diagnostics.py`
- Modify: `scripts/90_run_sr_v2_spatial_residual_diagnostics.py`
- Modify: `tests/test_sr_v2_spatial_diagnostics.py`

**Interfaces:**
- Consumes: dense row-standardized `numpy.ndarray` weights produced by `row_standardized_weights`.
- Produces: `permutation_morans_i(...) -> MoranResult` with unchanged public signature and deterministic results; `production_input_manifest() -> dict[str, dict[str, object]]` in the runner.

- [ ] **Step 1: Write failing sparse-equivalence and integrity tests**

```python
def test_sparse_permutation_matches_reference_dense_algorithm() -> None:
    values = np.array([1.0, 1.0, -1.0, -1.0])
    weights = row_standardized_weights(COUNTIES, neighbor_map(ADJACENCY, COUNTIES))
    expected = reference_dense_permutation(values, weights, permutations=199, seed=42)
    assert permutation_morans_i(values, weights, permutations=199, seed=42).to_dict() == expected

def test_spatial_runner_rejects_changed_production_input(tmp_path: Path) -> None:
    manifest = build_input_manifest(tmp_path, EXPECTED_INPUTS)
    (tmp_path / "posterior_primary_summary.csv").write_text("tampered\n")
    with pytest.raises(RuntimeError, match="SHA-256"):
        verify_input_manifest(tmp_path, manifest)
```

- [ ] **Step 2: Run the focused tests and confirm the expected RED state**

Run: `..\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_diagnostics.py -q`

Expected: FAIL because the sparse implementation and runner manifest functions do not exist.

- [ ] **Step 3: Implement one CSR-backed quadratic-form path**

```python
from scipy.sparse import csr_matrix

def _moran_components(values: np.ndarray, weights: np.ndarray | csr_matrix):
    x = np.asarray(values, dtype=float)
    w = weights if isinstance(weights, csr_matrix) else csr_matrix(weights)
    centered = x - x.mean()
    return centered, w, float(centered @ centered), float(w.sum())
```

Convert the filtered weight matrix to CSR once per call to `permutation_morans_i`; compute every simulated numerator as `permuted_centered @ (sparse_weights @ permuted_centered)`. Do not change RNG construction or permutation order.

Add SHA-256 verification for these exact runner inputs:

```text
outputs/scientific_reports_v2/production_8chain/production_gate.json
outputs/scientific_reports_v2/production_8chain/posterior_parameter_draws.parquet
outputs/scientific_reports_v2/production_8chain/county_posterior_summary.csv
data/processed/bayes_constrained/model_frame.parquet
```

The runner writes `production_input_sha256.csv` before analysis and rechecks it before publishing PASS evidence.

- [ ] **Step 4: Add retrieval provenance to the adjacency manifest**

`download_county_adjacency` must return `url`, `retrieved_utc`, `path`, `bytes`, and `sha256`. The timestamp is UTC ISO-8601. The runner includes this object verbatim in `spatial_residual_summary.json`.

- [ ] **Step 5: Run focused and full regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_diagnostics.py tests\test_sr_v2_engine.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass; the default NB2 production tests remain unchanged.

- [ ] **Step 6: Commit**

```powershell
git add src/bayes_constrained/spatial_diagnostics.py scripts/90_run_sr_v2_spatial_residual_diagnostics.py tests/test_sr_v2_spatial_diagnostics.py
git commit -m "perf: make SR-v2 spatial diagnostic sparse and fail closed"
```

### Task 2: Execute and freeze the spatial decision

**Files:**
- Create: `outputs/scientific_reports_v2/spatial_residual_diagnostics/**`
- Modify: `.gitattributes`
- Modify: `docs/scientific_reports_v2/active_execution_status.md`

**Interfaces:**
- Consumes: Task 1 runner and passed production evidence.
- Produces: `spatial_residual_summary.json` with one of the two exact `recommended_action` values.

- [ ] **Step 1: Run the diagnostic in the project environment**

Run: `.\.venv\Scripts\python.exe -B scripts\90_run_sr_v2_spatial_residual_diagnostics.py`

Expected: exit 0 and a complete output directory. A network/download failure is a HOLD; do not substitute an unverified adjacency file.

- [ ] **Step 2: Verify output gates and hashes**

Run a read-only verifier that checks: input hashes, adjacency hash, 3,142 counties, both global residual rows, deterministic permutation counts, finite statistics, threshold/action consistency, and the absence of writes under `production_8chain`.

- [ ] **Step 3: Record the branch decision**

If the action is `run_spatial_random_effect_sensitivity`, append a new plan task for an identifiable structured-plus-unstructured county model before manuscript freeze. If the action is the non-trigger value, write a machine-readable `spatial_model_decision.json` with `performed: false`, the threshold evidence, and the exact reason.

- [ ] **Step 4: Preserve bytes and update status**

Add:

```gitattributes
outputs/scientific_reports_v2/spatial_residual_diagnostics/** -text
```

Update the active status with the generated action and artifact paths; do not interpret a non-trigger as proof of independence.

- [ ] **Step 5: Commit**

```powershell
git add .gitattributes docs/scientific_reports_v2/active_execution_status.md outputs/scientific_reports_v2/spatial_residual_diagnostics
git commit -m "data: freeze SR-v2 spatial residual diagnostic"
```

### Task 3: Implement and freeze the triggered identifiable county spatial sensitivity

**Trigger evidence:**
- `outputs/scientific_reports_v2/spatial_residual_diagnostics/spatial_residual_summary.json`
- `recommended_action: run_spatial_random_effect_sensitivity`

**Interfaces:**
- Consumes the frozen corrected-production inputs and the archived 2024 Census adjacency bytes and SHA-256.
- Adds a county structured-plus-unstructured effect using the scaled BYM2 parameterization: a component-wise sum-to-zero, unit-generalized-variance intrinsic-CAR term plus an independent unit-variance county term, combined through one marginal scale and one mixing fraction. Singleton counties have zero structured contribution and retain the unstructured term.
- Produces a fail-closed, hash-bound spatial-sensitivity summary and primary-versus-spatial comparison required by manuscript result freeze.

- [ ] **Step 1: Freeze the model and execution contract**

Write the adjacency-component ordering, scaling constants, centering constraints, priors for marginal scale and mixing fraction, exact chain seeds/iterations/burn-in/thinning, convergence thresholds, source hashes, and required comparison rows to an immutable operational configuration. Refuse any adjacency or corrected-production hash mismatch.

- [ ] **Step 2: Write RED identifiability and target tests**

Test component-wise sum-to-zero structure, unit generalized-variance scaling, singleton behavior, separate structured/unstructured contributions, finite log density, default-model non-regression, checkpoint round trips, and permutation-invariant results under a jointly permuted county/adjacency ordering. Include a small proper-posterior synthetic recovery test.

- [ ] **Step 3: Implement the BYM2 county effect through canonical model paths**

Extend design, target, parameter updates, serialization, and summaries without duplicating the NB2 likelihood or latent-count kernel. Report the marginal spatial scale, mixing fraction, county combined effects, and the same prespecified rurality/SVI contrasts as the primary model.

- [ ] **Step 4: Add fail-closed preparation, chain, merge, and gate runners**

Require dispersed feasible starts, the frozen adjacency/component contract, zero constraint failures, all-parameter finite diagnostics, prespecified R-hat and bulk/tail ESS thresholds, exact completed-chain/draw counts, and source/output SHA-256. A partial or hash-mismatched run remains HOLD and publishes no passed comparison.

- [ ] **Step 5: Execute and independently verify the sensitivity**

Run the frozen multi-chain configuration in the authorized project environment. Independently verify chain completion, seeds, draws, constraint preservation, diagnostics, adjacency and production hashes, structured-effect centering/scaling, and primary-versus-spatial contrast equality with the machine-readable source tables.

- [ ] **Step 6: Freeze evidence before manuscript results**

Preserve all sensitivity evidence with `-text`, update the active execution status, and commit the implementation and passed outputs. The manuscript result-freeze gate must require the passed spatial-sensitivity summary because the trigger branch is active; do not interpret attenuation, persistence, or any spatial parameter as causal geographic evidence.
