# Scientific Reports v2 heavy sensitivities implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement, launch, verify, and freeze all prespecified prior, strict-Poisson, pandemic-period, and age-structure sensitivity analyses in one checksum-gated 24-chain Wahab epoch.

**Architecture:** Extend the validated sampler through explicit likelihood, design, and constraint contracts while preserving default NB2 behavior. A single immutable operational configuration maps 24 array indexes to six profiles. Generic preparation, chain, merge, and gate scripts are wrapped by fail-closed Wahab staging, submission, resume, finalization, and result-sync helpers.

**Tech Stack:** Python 3.12, NumPy, SciPy, pandas, PyArrow, statsmodels, ArviZ, pytest, Bash, Slurm.

**Spec:** `docs/superpowers/specs/2026-08-18-sr-v2-robustness-completion-design.md`

## Global Constraints

- Immutable run id: `sr-v2-heavy-sensitivity-20260818-v1`.
- Six profiles, four chains each, 180,000 iterations, 45,000 burn-in, thin 30, 4,500 retained draws per chain.
- All 48 chain and initialization seeds in the spec are unique in their respective roles.
- Default `negative_binomial_2` behavior must remain the default and pass all existing exact-kernel and engine tests.
- Poisson is strict and has no active or reported dispersion parameter.
- Pandemic exclusion models exactly 2019 and 2022–2024 and never applies the incompatible 2019–2024 Q001 county-period total.
- Age sensitivity adds archived SVI `EP_AGE17` while retaining `% age ≥65`, the county universe, and the recorded imputation policy.
- A profile PASS requires four completed chains, zero constraint failures, all-parameter R-hat at most 1.05 and ESS at least 100, and primary R-hat at most 1.03 and ESS at least 400.
- Wahab execution is `--array=1-24%8`, four CPUs and 64 GiB per task, with an `afterok` finalizer.

---

### Task 1: Canonical likelihood and model-design contracts

**Files:**
- Modify: `src/bayes_constrained/model.py`
- Modify: `src/bayes_constrained/heatbath.py`
- Modify: `src/bayes_constrained/sampler.py`
- Modify: `src/bayes_constrained/exact_validation.py`
- Create: `tests/test_sr_v2_model_sensitivities.py`

**Interfaces:**
- Produces: `LikelihoodFamily`, `normalize_likelihood_family`, `poisson_logpmf`, and `count_logpmf`.
- Produces: `make_design(..., likelihood_family=...)` and `Design.likelihood_family`.
- Preserves: all existing default call signatures through NB2 defaults.

- [ ] **Step 1: Write the failing Poisson target tests**

```python
def test_poisson_logpmf_matches_scipy() -> None:
    y = np.arange(8)
    means = np.linspace(0.2, 8.0, 8)
    assert_allclose(poisson_logpmf(y, means), scipy.stats.poisson.logpmf(y, means))

def test_strict_poisson_posterior_is_kappa_invariant() -> None:
    first = base_theta.copy(); first.log_kappa = -20.0
    second = base_theta.copy(); second.log_kappa = 20.0
    assert log_posterior_theta(y, first, poisson_design, intercept_mean=0.0) == log_posterior_theta(y, second, poisson_design, intercept_mean=0.0)
```

Also add RED tests for: unknown-family rejection, missing/nonpositive NB2 kappa, no Poisson kappa proposal/output, heat-bath/full-target ratio equality, exact Poisson detailed balance/stationarity below `1e-12`, empirical frequencies within `0.02`, and unchanged NB2 regression probabilities.

- [ ] **Step 2: Run the tests and confirm RED for missing likelihood support**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_model_sensitivities.py tests\test_sr_v2_engine.py -q`

- [ ] **Step 3: Implement the canonical pointwise dispatcher**

```python
LikelihoodFamily = Literal["negative_binomial_2", "poisson"]

def poisson_logpmf(y, mu):
    y = np.asarray(y, dtype=float)
    mu = np.clip(np.asarray(mu, dtype=float), 1e-12, np.inf)
    return y * np.log(mu) - mu - gammaln(y + 1.0)

def count_logpmf(y, mu, *, likelihood_family, kappa=None):
    family = normalize_likelihood_family(likelihood_family)
    if family == "poisson":
        return poisson_logpmf(y, mu)
    if kappa is None or not np.isfinite(kappa) or kappa <= 0:
        raise ValueError("NB2 requires finite positive kappa")
    return nb2_logpmf(y, mu, kappa)
```

Route full likelihood, all heat-bath weights, all count moves, and exact transition/empirical validation through this dispatcher. Under Poisson, skip the kappa prior, omit `log_kappa` proposals, omit `kappa` draw rows, and store the likelihood family in resolved config and chain status.

- [ ] **Step 4: Implement the pandemic interaction design**

Add exact year mapping and six columns named:

```text
primary_rurality_metro_other__x__acute_pandemic
primary_rurality_nonmetro_adjacent__x__acute_pandemic
primary_rurality_nonmetro_nonadjacent__x__acute_pandemic
primary_rurality_metro_other__x__later_period
primary_rurality_nonmetro_adjacent__x__later_period
primary_rurality_nonmetro_nonadjacent__x__later_period
```

Reject years outside 2019–2024. Do not add period main effects.

- [ ] **Step 5: Verify RED-to-GREEN and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_model_sensitivities.py tests\test_sr_v2_engine.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Commit:

```powershell
git add src/bayes_constrained/model.py src/bayes_constrained/heatbath.py src/bayes_constrained/sampler.py src/bayes_constrained/exact_validation.py tests/test_sr_v2_model_sensitivities.py
git commit -m "feat: add strict Poisson and pandemic interaction targets"
```

### Task 2: Pandemic-exclusion and age-structure frame contracts

**Files:**
- Modify: `src/bayes_constrained/data.py`
- Modify: `src/bayes_constrained/constraints.py`
- Modify: `src/bayes_constrained/sampler.py`
- Modify: `src/bayes_constrained/model.py`
- Modify: `src/submission_viz/tables.py`
- Modify: `tests/test_sr_v2_model_sensitivities.py`
- Modify: `tests/test_bayes_constrained.py`

**Interfaces:**
- Produces: `make_pandemic_exclusion_frame(frame, excluded_years=("2020", "2021"))`.
- Produces: `augment_age17_covariate(frame, svi_path) -> pd.DataFrame`.
- Produces: explicit constraint contract `full_period` or `selected_years_no_period_total`.

- [ ] **Step 1: Write failing frame and constraint tests**

Add tests proving: source frames are not mutated; retained years and reset indexes are exact; retained Q002/Q003/Q004 values are unchanged; Q001 bounds are tautological retained annual sums; original Q001 values survive in audit columns; corrupted retained state-year totals still fail; interval counties derive from bound width; and `age_structure_age17` contains both standardized age columns without changing counties.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_model_sensitivities.py -q`

- [ ] **Step 3: Implement the exclusion transformation**

```python
out = frame.loc[~frame["year"].astype(str).isin(excluded_years)].copy(deep=True).reset_index(drop=True)
out["source_full_period_q001_lower"] = out["q001_period_lower"]
out["source_full_period_q001_upper"] = out["q001_period_upper"]
out["q001_period_status"] = "not_applied_full_period_year_subset"
out[["q001_period_lower", "q001_period_upper"]] = retained_annual_bound_sums(out)
out["q001_period_exact_count"] = np.nan
out.attrs["grand_total"] = int(out.drop_duplicates("year")["q003_national_year_total"].sum())
out.attrs["q001_constraint_policy"] = "full_period_q001_not_applied"
```

Rename the validation check to `grand_total_matches_modeled_years` and report included years and expected total. Determine interval counties structurally from `period_upper > period_lower`.

- [ ] **Step 4: Implement archived age-17 augmentation**

Load `data/raw/covariates/SVI_2022_US_county.csv`, normalize `FIPS`, derive `pct_age17 = EP_AGE17`, merge with `many_to_one` validation, apply the existing state/national imputation policy to unmatched counties, and add `z_pct_age17`. Preserve row count, county set, and an imputation flag.

- [ ] **Step 5: Run focused/full tests and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_model_sensitivities.py tests\test_bayes_constrained.py -q
.\.venv\Scripts\python.exe -m pytest -q
git add src/bayes_constrained/data.py src/bayes_constrained/constraints.py src/bayes_constrained/sampler.py src/bayes_constrained/model.py src/submission_viz/tables.py tests/test_sr_v2_model_sensitivities.py tests/test_bayes_constrained.py
git commit -m "feat: add temporal exclusion and age-structure contracts"
```

### Task 3: Immutable 24-chain preparation, execution, merge, and gate

**Files:**
- Create: `config/sr_v2_heavy_sensitivity_execution.yaml`
- Create: `src/bayes_constrained/sensitivity.py`
- Create: `scripts/100_prepare_sr_v2_heavy_sensitivity.py`
- Create: `scripts/101_run_sr_v2_heavy_sensitivity_chain.py`
- Create: `scripts/102_merge_sr_v2_heavy_sensitivity.py`
- Create: `scripts/103_gate_sr_v2_heavy_sensitivity.py`
- Create: `scripts/104_validate_sr_v2_heavy_sensitivity_infrastructure.py`
- Create: `tests/test_sr_v2_heavy_sensitivity.py`

**Interfaces:**
- Produces: `SensitivityProfile`, `load_execution_spec`, `profile_fingerprint`, `build_sensitivity_frame`, `derive_period_irrs`.
- Produces: run root `outputs/scientific_reports_v2/heavy_sensitivity/sr-v2-heavy-sensitivity-20260818-v1/`.

- [ ] **Step 1: Write failing mapping, fingerprint, resume, and gate tests**

The test fixture must assert exact 24-row order, seeds, four chains per profile, seed uniqueness, target-signature differences, 4,500 draws, no Poisson kappa, exact interaction terms, retained exclusion years, age columns, changed-manifest resume refusal, completed-chain idempotence, tamper HOLD, missing-chain HOLD, and convergence HOLD.

- [ ] **Step 2: Run tests and confirm RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_heavy_sensitivity.py -q`

- [ ] **Step 3: Write the exact operational YAML**

The file must contain the run id, hashes of the frozen registry and primary authority, iteration constants, gate thresholds, all 24 mappings from the spec, and these target contracts:

```yaml
prior_broader: {likelihood: negative_binomial_2, model: primary, frame: full, prior: broader}
prior_regularizing: {likelihood: negative_binomial_2, model: primary, frame: full, prior: regularizing}
model_family_poisson: {likelihood: poisson, model: primary, frame: full, prior: default}
pandemic_interaction: {likelihood: negative_binomial_2, model: pandemic_interaction, frame: full, prior: default}
pandemic_exclusion: {likelihood: negative_binomial_2, model: primary, frame: pandemic_exclusion, prior: default}
age_structure_age17: {likelihood: negative_binomial_2, model: age_structure_age17, frame: age17_augmented, prior: default}
```

- [ ] **Step 4: Implement atomic prepare and fail-closed resume**

Preparation verifies the passed primary gate and hashes all inputs, writes to a temporary run root, creates fresh feasible starts, then atomically publishes. It refuses conflicting existing runs and provides no force-overwrite path. The chain runner accepts only `--run-id` and `--array-index`, verifies the manifest/fingerprint before checkpoint load, and writes profile-local status plus artifact hashes.

- [ ] **Step 5: Implement merge and computational gate**

The merger requires exactly four completed chains per profile. It derives IRRs draw by draw, including interaction sums, and writes normalized comparisons with the primary posterior. The gate checks all input/output hashes, zero constraint failures, parameter-schema correctness, included years, required columns, and convergence thresholds. PASS means sensitivity computational completeness only.

- [ ] **Step 6: Implement infrastructure validator**

The validator supports `--scope python` and `--scope full`. Python scope checks AST entrypoints, exact YAML mappings, unique seeds, fail-closed file creation, and resume guards. Full scope additionally checks the HPC DAG contracts introduced in Task 5.

- [ ] **Step 7: Run tests and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_heavy_sensitivity.py tests\test_sr_v2_model_sensitivities.py -q
.\.venv\Scripts\python.exe scripts\104_validate_sr_v2_heavy_sensitivity_infrastructure.py --scope python
.\.venv\Scripts\python.exe -m pytest -q
git add config/sr_v2_heavy_sensitivity_execution.yaml src/bayes_constrained/sensitivity.py scripts/100_prepare_sr_v2_heavy_sensitivity.py scripts/101_run_sr_v2_heavy_sensitivity_chain.py scripts/102_merge_sr_v2_heavy_sensitivity.py scripts/103_gate_sr_v2_heavy_sensitivity.py scripts/104_validate_sr_v2_heavy_sensitivity_infrastructure.py tests/test_sr_v2_heavy_sensitivity.py
git commit -m "feat: add fail-closed SR-v2 heavy sensitivity epoch"
```

### Task 4: Refreshed suppression-handling comparators

**Files:**
- Create: `src/bayes_constrained/suppression_sensitivity.py`
- Create: `scripts/105_run_sr_v2_suppression_sensitivity.py`
- Create: `tests/test_sr_v2_suppression_sensitivity.py`
- Create: `outputs/scientific_reports_v2/suppression_sensitivity/**`

**Interfaces:**
- Consumes: frozen registry, processed model frame, passed primary summary.
- Produces: `scenario_comparison.csv`, `suppression_sensitivity_summary.json`, and a PASS/HOLD gate.

- [ ] **Step 1: Write failing six-scenario and primary-agreement tests**

Assert the exact registry scenario ids, exclusion of legacy extras, deterministic feasible population-favoring allocation, explicit visible-only population, current-primary numerical agreement, and HOLD on stale v1 values.

- [ ] **Step 2: Confirm RED and implement the minimal comparator module**

Reuse scenario-construction and GLM logic from `src/04_suppression_bounds_models.py` without importing its command-side effects. Emit all primary rurality/SVI comparisons and clearly label the constrained row as posterior while other rows are deterministic/GLM comparators.

- [ ] **Step 3: Run, verify, and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_suppression_sensitivity.py -q
.\.venv\Scripts\python.exe scripts\105_run_sr_v2_suppression_sensitivity.py
.\.venv\Scripts\python.exe -m pytest -q
git add src/bayes_constrained/suppression_sensitivity.py scripts/105_run_sr_v2_suppression_sensitivity.py tests/test_sr_v2_suppression_sensitivity.py outputs/scientific_reports_v2/suppression_sensitivity
git commit -m "data: refresh SR-v2 suppression comparators"
```

### Task 5: Checksum-gated Wahab orchestration

**Files:**
- Create: `hpc/wahab/stage_sr_v2_heavy_sensitivity_to_scratch.sh`
- Create: `hpc/wahab/sync_sr_v2_heavy_sensitivity_results_home.sh`
- Create: `hpc/wahab/slurm/63_sr_v2_heavy_sensitivity_chain_array.sbatch`
- Create: `hpc/wahab/slurm/64_sr_v2_finalize_heavy_sensitivity.sbatch`
- Create: `hpc/wahab/submit_sr_v2_heavy_sensitivity.sh`
- Create: `hpc/wahab/resume_sr_v2_heavy_sensitivity.sh`
- Modify: `scripts/104_validate_sr_v2_heavy_sensitivity_infrastructure.py`
- Modify: `tests/test_sr_v2_heavy_sensitivity.py`

**Interfaces:**
- Produces: Slurm array/finalizer DAG and append-only `submitted_jobs.tsv`.
- Preserves: run-specific sync only; no `--delete`.

- [ ] **Step 1: Add RED static tests for the exact DAG**

Require `#SBATCH --array=1-24%8`, `--signal=B:USR1@300`, four CPUs, 64G, 72 hours, `afterok`, SHA-256 checks before Python execution, EXIT-trap sync, no delete/force overwrite, three-attempt resume cap, completed-chain exclusion, and new-finalizer creation.

- [ ] **Step 2: Implement staging and sync**

Staging includes source/config plus the passed production gate/config/summaries, frozen registry, execution spec, generated run manifest, and feasible starts. Generate `inputs_sha256.txt` at home, copy it, and require `sha256sum -c` in scratch. Sync only the run root and matching Slurm logs.

- [ ] **Step 3: Implement array/finalizer wrappers**

The array wrapper maps `SLURM_ARRAY_TASK_ID` through the immutable manifest. USR1 or the 71h45m usable deadline checkpoints, writes `status=checkpointed`, syncs, and exits 75. The finalizer verifies all manifests, runs merge then gate, writes the final manifest, and syncs on exit.

- [ ] **Step 4: Implement submit/resume helpers**

Submit performs prepare, dry-run staging, real staging, scratch hash verification, then submits array and `afterok` finalizer. Resume verifies the original target, selects only incomplete indexes, refuses attempt four, cancels the unsatisfiable old finalizer while recording it, and attaches a new finalizer.

- [ ] **Step 5: Run static/focused/full tests and commit**

```powershell
bash -n hpc/wahab/stage_sr_v2_heavy_sensitivity_to_scratch.sh hpc/wahab/sync_sr_v2_heavy_sensitivity_results_home.sh hpc/wahab/submit_sr_v2_heavy_sensitivity.sh hpc/wahab/resume_sr_v2_heavy_sensitivity.sh
.\.venv\Scripts\python.exe scripts\104_validate_sr_v2_heavy_sensitivity_infrastructure.py --scope full
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_heavy_sensitivity.py -q
.\.venv\Scripts\python.exe -m pytest -q
git add hpc/wahab scripts/104_validate_sr_v2_heavy_sensitivity_infrastructure.py tests/test_sr_v2_heavy_sensitivity.py
git commit -m "hpc: add SR-v2 heavy sensitivity Slurm epoch"
```

### Task 6: Authenticated launch, monitoring, retrieval, and freeze

**Files:**
- Create remotely: run-specific scratch clone and heavy-sensitivity output root.
- Create locally after completion: verified run root and matching Slurm logs.
- Modify: `.gitattributes`
- Modify: `docs/scientific_reports_v2/active_execution_status.md`

**Interfaces:**
- Consumes: Tasks 1–5 commits and the frozen remote production evidence.
- Produces: passed `heavy_sensitivity_gate.json` and byte-identical local evidence.

- [ ] **Step 1: Transfer code without pushing a shared branch**

Create a local Git bundle or format-patch for the implementation commits, upload it through authenticated Open OnDemand, and create a timestamped remote clone/worktree. Verify commit id and bundle SHA-256. Copy only the required production inputs from the verified remote root and validate their hashes.

- [ ] **Step 2: Run dry-run and authenticated submit**

```bash
bash hpc/wahab/stage_sr_v2_heavy_sensitivity_to_scratch.sh --dry-run
bash hpc/wahab/submit_sr_v2_heavy_sensitivity.sh --run-id sr-v2-heavy-sensitivity-20260818-v1
```

Record array and finalizer job ids locally and remotely. Do not accept dashboard status as completion evidence.

- [ ] **Step 3: Monitor fail-closed**

Require `sacct` COMPLETED/`0:0` for all 24 tasks and finalizer. If a task checkpoints/fails, inspect status/stderr and use the bounded resume helper only after verifying fingerprints. Never rerun completed tasks.

- [ ] **Step 4: Verify the remote gate**

Require all six profiles passed, exactly four completed chains/profile, expected draws/seeds/years/parameter schemas, zero constraint failures, complete comparisons, and all source/output hashes. Inspect every stderr and finalizer log.

- [ ] **Step 5: Package, download, and verify**

Create a run-specific tar and sidecar SHA-256 on Wahab. Download both through authenticated Open OnDemand, compare archive SHA-256, reject unsafe archive paths, extract to a new timestamped staging directory, and recompute every internal hash before copying into this clone.

- [ ] **Step 6: Preserve bytes, update status, and commit**

Add `-text` coverage for the heavy-sensitivity root and exact Slurm log names. Confirm the Git index blob ids equal no-filter working-tree blob ids and that `v1.1.1`/production evidence are unchanged.

```powershell
git add .gitattributes docs/scientific_reports_v2/active_execution_status.md outputs/scientific_reports_v2/heavy_sensitivity logs/slurm
git commit -m "data: freeze verified SR-v2 robustness sensitivities"
```
