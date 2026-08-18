# Scientific Reports v2 triggered BYM2 sensitivity implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement, execute, independently verify, and freeze the spatial sensitivity required by the passed residual-Moran trigger without changing the corrected primary target or evidence.

**Architecture:** A canonical binary county graph and component-wise scaled ICAR precision feed an optional, non-centered BYM2 county effect through the existing `linear_predictor -> mu -> NB2` target. A separate four-chain Wahab epoch has its own fingerprints, checkpoint schema, merger, and fail-closed gate. The triggered spatial gate and the six-profile heavy gate remain independent inputs to manuscript result freeze.

**Tech Stack:** Python 3.12, NumPy, SciPy sparse matrices, pandas, PyArrow, ArviZ, pytest, Bash, Slurm.

**Spec:** `docs/superpowers/specs/2026-08-18-sr-v2-robustness-completion-design.md`

## Global Constraints

- Immutable run id: `sr-v2-spatial-sensitivity-20260818-v1`.
- Four chains. Extension epoch 0 is 180,000 iterations with 45,000 burn-in, thin 30, and 4,500 retained draws per chain. A convergence-only HOLD may receive a separately reviewed and fingerprinted extension authorization for epochs 1 through 3; every extension continues all four chains for 90,000 iterations with no new burn-in or adaptation and adds exactly 3,000 draws per chain. The only valid equal per-chain draw counts are therefore 4,500, 7,500, 10,500, and 13,500.
- `extension_epoch` (`0..3`) is distinct from `job_attempt` (`1..3` within one epoch). An incomplete-job retry resumes only failed/checkpointed indexes inside the same epoch. A convergence extension advances all four completed chains to the next epoch. No extension is allowed for a source, graph, constraint, fingerprint, or nonfinite-value failure.
- Chain seeds: `74291, 74292, 74293, 74294`; allocation initialization seeds: `74251, 74252, 74253, 74254`; spatial initialization seeds: `74261, 74262, 74263, 74264`.
- Graph: binary, symmetric, unweighted ICAR graph reconstructed from the frozen 2024 Census bytes; no row-standardized Moran weights. County order is sorted zero-padded five-digit model-frame FIPS. Edges are deduplicated lexicographic `(min_fips, max_fips)` pairs.
- Frozen graph certificate: 3,142 nodes, 9,233 undirected edges, 18 components, 14 singletons, 3,128 nonisolated nodes; county-order SHA-256 `250417302ddfc261014e7182e065ff0ebaef3a15437c8672fc05b9ab4a9c066b`; edge-list SHA-256 `59412bc9722a119487977065892db16d6bb6931725821a0adb21886ec891df39`.
- Non-singleton component sizes/scales are exact: 3,099 -> `0x1.23688b75b9ac1p-1`; 17 -> `0x1.fdba0c05e631ep-2`; 10 -> `0x1.00888ae534b68p-1`; 2 -> `0x1.ffffffffffffep-3`. Preparation independently recomputes and rejects any mismatch.
- Component order is minimum FIPS; member order is sorted FIPS. For non-singleton component `c`, `Q_c = D_c - A_c`, `g_c = exp(mean(log(diag(pinv(Q_c)))))`, and scaled precision is `g_c Q_c`. Structured effects are component-wise sum-to-zero. Singleton structured effects are exactly zero.
- BYM2 effect: `sigma_county * (sqrt(phi_structured) * u_scaled + sqrt(1 - phi_structured) * v)`, with `sigma_county ~ HalfNormal(1)` and `phi_structured ~ Beta(1,1)`. Standard singleton contribution is therefore `sigma_county * sqrt(1-phi_structured) * v`.
- The archived geography mismatch is retained, not silently crosswalked. The exact singleton authority is `02261, 02270, 09001, 09003, 09005, 09007, 09009, 09011, 09013, 09015, 15001, 15003, 15007, 46113`; the eight legacy Connecticut counties and the full limitation must be disclosed.
- Gate thresholds are inclusive: all stochastic parameters and combined county effects R-hat at most 1.05 and bulk/tail ESS at least 100; the eight primary terms plus `sigma_county` and `phi_structured` R-hat at most 1.03 and bulk/tail ESS at least 400; zero count or spatial-constraint failures. Deterministic singleton structured zeros are excluded from R-hat/ESS. Diagnostics use equal-length chains, rank-normalized split R-hat, bulk ESS, and tail ESS as implemented by the repository-pinned ArviZ version, which is recorded in the gate.
- No effect direction, attenuation, interval overlap, or value of `phi_structured` is a computational PASS criterion.
- Do not modify `outputs/scientific_reports_v2/production_8chain/**` or `outputs/scientific_reports_v2/spatial_residual_diagnostics/**`.
- Cross-plan order: spatial Task 1 may run immediately because it owns isolated files. Heavy-sensitivity Tasks 1-3 must then be reviewed before spatial Tasks 2-4 modify shared model/sampler code. A joint full-suite and fixed-seed default-NB2 regression gate is required before either remote launch.

## Canonical serialization

- County-order hash bytes are UTF-8 records `"<fips>\n"`, one per county in order.
- Edge-list hash bytes are UTF-8 records `"<min_fips>|<max_fips>\n"`, one per edge in order.
- Component tables use UTF-8, comma delimiters, LF line endings, and the exact singleton authority above.
- Contract/fingerprint JSON uses `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")` with no trailing newline. Floating component scales are represented by `float.hex()` strings before canonical JSON hashing.
- File manifests always hash the raw file bytes; YAML and Parquet are not semantically reserialized for hashing.

## Frozen source authorities

The operational configuration records and runtime verifies at least:

```text
38be94b401138864cf6e4cb030f2bd53e9b8ad6ea24e080e0353824124784437  outputs/scientific_reports_v2/production_8chain/production_gate.json
2842efa4c95b018aed3626b58b33e42792c0348655225c3a89ec58b4109452e6  outputs/scientific_reports_v2/production_8chain/posterior_primary_summary.csv
0f3adc1a90bd411f3065e798867423d5bd2ae1cf0c61d99d7f5f53493b362064  outputs/scientific_reports_v2/production_8chain/posterior_parameter_draws.parquet
f9eb36d8748da9a3c8f95c952a95de6d4845ecb963f329a2a61b9adb47ee056e  outputs/scientific_reports_v2/production_8chain/county_posterior_summary.csv
2f20555f4b690e1a495e2409dbb2f9bb128a6d3f7b0bb39f4017034aaf2a9e44  data/processed/bayes_constrained/model_frame.parquet
072e039b78af11a0bb4d6532bb8fb09f70b81d825a38faa3cf89670ca7843814  config/scientific_reports_v2_robustness_registry.yaml
5d3209d248add49cfd2a5a5379af3e831ec7f6136ed45654ca882cc399a190d1  outputs/scientific_reports_v2/spatial_residual_diagnostics/spatial_residual_summary.json
a44ee5945c308f1455e799c0f22bed356ff118ff6a0de5da1d1f9315c3a836c8  outputs/scientific_reports_v2/spatial_residual_diagnostics/global_morans_i.csv
6296899e8a789e219d245d109b55759dead7817f5ba93c75f0694f669231c995  outputs/scientific_reports_v2/spatial_residual_diagnostics/within_state_morans_i.csv
912ca408163016864fe64aaf667b53ad03a19ce4acbc586d3ac508395bdac980  outputs/scientific_reports_v2/spatial_residual_diagnostics/county_adjacency2024.txt
```

---

### Task 1: Canonical graph, scaled BYM2 mathematics, and frozen execution contract

**Files:**
- Create: `config/sr_v2_spatial_sensitivity_execution.yaml`
- Create: `src/bayes_constrained/spatial_bym2.py`
- Create: `tests/test_sr_v2_spatial_sensitivity.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class BYM2Prior:
    sigma_county_halfnormal_sd: float

@dataclass(frozen=True)
class BYM2Graph:
    counties: tuple[str, ...]
    row_county_index: np.ndarray
    adjacency: csr_matrix
    scaled_precision: csr_matrix
    component_id: np.ndarray
    components: tuple[np.ndarray, ...]
    component_scale: np.ndarray
    singleton_mask: np.ndarray
    contract_sha256: str

def build_bym2_graph(frame, adjacency_path, *, expected_sha256, frozen_contract=None) -> BYM2Graph: ...
def componentwise_center(values, graph) -> np.ndarray: ...
def validate_structured_effect(values, graph, *, atol=1e-12) -> None: ...
def combined_county_effect(structured, unstructured, log_sigma, logit_phi, graph) -> np.ndarray: ...
def bym2_log_prior(structured, unstructured, log_sigma, logit_phi, graph, prior) -> float: ...
```

- [ ] **Step 1: Write RED graph and parameterization tests**

Add tests for exact archived graph counts/hashes/component sizes/singleton set; rejection of missing/extra/duplicate counties or adjacency mismatch; component ordering; independent scale recomputation; unit geometric mean marginal variance; component-wise rather than global centering; exact singleton zero; contribution identity; `log_sigma` and `logit_phi` Jacobians; finite valid density; and deterministic target invariance under a jointly permuted county/graph order after unpermuting.

Use a three-component synthetic graph (path of three, edge of two, singleton) to lock the path scale `0.40933683318226494`, edge scale `0.25`, centering, and singleton rules. Do not claim a short recovery run proves posterior propriety; it is only a computational recovery check.

- [ ] **Step 2: Confirm RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_sensitivity.py -q --basetemp=<unique-temp>`

- [ ] **Step 3: Implement graph and BYM2 primitives**

Canonicalize graph bytes as specified globally. Reject nonfinite states, `phi` outside `(0,1)`, materially noncentered structured fields, or nonzero singleton structured values. Include correct Jacobians:

```text
log p(log_sigma) = -0.5 * (exp(log_sigma) / 1.0)^2 + log_sigma + constant
log p(logit_phi) = log(phi) + log(1-phi) + constant
```

Fixed graph normalizers may be omitted from MCMC ratios. Store component scales as `float.hex()` strings in canonical JSON before hashing.

- [ ] **Step 4: Write the immutable operational YAML**

Include schema/run/model ids, exact source hashes, graph certificate, model formula/priors, seeds, run sizes, bounded extensions, MALA schedule, comparison rows, threshold classes, and output schemas. The exact comparison order is the six rurality/SVI terms plus `z_pct_age65` and `z_pct_male`.

- [ ] **Step 5: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_sensitivity.py -q --basetemp=<unique-temp>
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_diagnostics.py tests\test_sr_v2_engine.py -q --basetemp=<unique-temp>
git add config/sr_v2_spatial_sensitivity_execution.yaml src/bayes_constrained/spatial_bym2.py tests/test_sr_v2_spatial_sensitivity.py
git commit -m "feat: freeze SR-v2 BYM2 graph and target contract"
```

### Task 2: Canonical target, MALA updates, and fingerprinted checkpointing

**Files:**
- Modify: `src/bayes_constrained/model.py`
- Modify: `src/bayes_constrained/sampler.py`
- Modify: `src/bayes_constrained/diagnostics.py`
- Modify: `src/bayes_constrained/spatial_bym2.py`
- Modify: `tests/test_sr_v2_spatial_sensitivity.py`
- Create: `tests/fixtures/sr_v2_primary_rng_reference.json`

**Interfaces:**
- Optional spatial state appended to `Theta`: `spatial_structured`, `spatial_unstructured`, `log_sigma_county`, `logit_phi_structured`.
- Optional `Design.spatial_graph`; default remains `None`.
- Spatial-disabled predictor, likelihood, prior, parameter rows, proposal scales, checkpoint schema, and exact kernels remain unchanged.

- [ ] **Step 1: Write RED canonical-target and checkpoint tests**

Before modifying shared code, freeze a short fixed-seed default-NB2 reference trace, acceptance counters, checkpoint key/schema, and final RNG state in the fixture. Test exact spatial-disabled equality to that reference so an inactive conditional cannot consume RNG draws. Also test zero-spatial/default predictor equality; legacy positional `Theta` compatibility; canonical NB2 likelihood use; latent-count local/full-target ratio equality with spatial effects; spatial effect constant across year rows for a county; finite full target; exact forward/reverse MALA density on the centered subspace; short synthetic recovery; complete spatial checkpoint round-trip/RNG continuation; and rejection of wrong target/chain/graph/source/schema fingerprints or corrupt sidecar hashes.

- [ ] **Step 2: Implement optional canonical model state**

`linear_predictor` adds the combined county effect via `row_county_index` only when `Design.spatial_graph` is present. `log_prior` calls the BYM2 prior only for spatial designs. `log_posterior_theta` remains the single full target; do not duplicate NB2 or latent-count likelihood code.

- [ ] **Step 3: Implement spatial update blocks**

Update `(log_sigma_county, logit_phi_structured)` with a symmetric two-dimensional random walk (initial SDs 0.08 and 0.15). Every five iterations in every epoch, update the joint structured/unstructured field with MALA using the exact canonical full target for acceptance and the exact constrained-subspace forward/reverse proposal correction; only adaptation is disabled after epoch-0 burn-in.

Let `P` subtract each non-singleton component mean and set singleton structured coordinates to zero. For county-aggregated NB2 log-mean score `s` (with row score `y - (y+kappa)*mu/(kappa+mu)` and zero derivative for clipped predictor rows), use:

```text
grad_u = sigma_county * sqrt(phi_structured) * P@s - Q_star@u
grad_v = sigma_county * sqrt(1-phi_structured) * s - v
u_proposed = u + 0.5*epsilon_u^2*grad_u + epsilon_u*P@z_u
v_proposed = v + 0.5*epsilon_v^2*grad_v + epsilon_v*z_v
```

Use exact forward/reverse Gaussian squared norms on the rank-reduced centered subspace in the Hastings correction. Acceptance always evaluates `log_posterior_theta`.

Initial steps are `epsilon_u=0.02` and `epsilon_v=0.04`. After attempted-MALA window `j` of 100 proposals during epoch-0 burn-in, update the common multiplier by `log(m_next)=clip(log(m)+min(0.05,j^-0.6)*(window_acceptance-0.574), log(0.1), log(5.0))`; then set `epsilon_u=.02*m`, `epsilon_v=.04*m`. Freeze after iteration 45,000 and never adapt during an extension epoch.

- [ ] **Step 4: Add schema-v2 spatial checkpoints and bounded draw storage**

Fingerprints use the canonical serialization above over run/model/config/input/source/graph/likelihood/prior/design/parameter schema, extension epoch and reviewed extension-authorization hash and, per chain, chain id plus all three seeds. A checkpoint stores these hashes, extension epoch, job attempt, the full current spatial state, RNG state, current target, committed draw ranges, pending buffers, adaptation state, and a sidecar SHA-256. Resume recomputes target and validates constraints before loading.

At every 250 saved draws, atomically write matching numbered spatial and scalar chunks. Spatial chunks contain only float64 structured and unstructured arrays in frozen county order; combined effects are derived in float64 from those arrays and the scalar `sigma_county`/`phi_structured` draws. Before publishing any checkpoint, either atomically flush the pending matching chunks and manifest or serialize the entire pending spatial/scalar buffer inside the checkpoint. The checkpoint records exact chunk hashes/ranges, next draw id, output positions, and RNG state; it must never acknowledge a draw absent from committed chunks or its pending buffer. Resume rejects orphan, overlapping, missing, or checkpoint-disagreeing chunks. Add crash-window tests after each write/rename boundary. At completion merge verified chunks into `draws_spatial.npz` and scalar Parquet without duplicate draws.

- [ ] **Step 5: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_sensitivity.py tests\test_sr_v2_engine.py tests\test_bayes_constrained.py -q --basetemp=<unique-temp>
.\.venv\Scripts\python.exe -m pytest -q --basetemp=<unique-temp>
git add src/bayes_constrained/model.py src/bayes_constrained/sampler.py src/bayes_constrained/diagnostics.py src/bayes_constrained/spatial_bym2.py tests/test_sr_v2_spatial_sensitivity.py tests/fixtures/sr_v2_primary_rng_reference.json
git commit -m "feat: add checkpointed SR-v2 BYM2 sampler"
```

### Task 3: Atomic preparation, chain runner, merger, and fail-closed gate

**Files:**
- Create: `scripts/106_prepare_sr_v2_spatial_sensitivity.py`
- Create: `scripts/107_run_sr_v2_spatial_sensitivity_chain.py`
- Create: `scripts/108_merge_sr_v2_spatial_sensitivity.py`
- Create: `scripts/109_gate_sr_v2_spatial_sensitivity.py`
- Create: `tests/test_sr_v2_spatial_sensitivity_pipeline.py`

**Interfaces:**
- Produces: `outputs/scientific_reports_v2/spatial_sensitivity/sr-v2-spatial-sensitivity-20260818-v1/`.
- Gate starts as HOLD and publishes PASS atomically only after every source, graph, chain, draw, diagnostic, comparison, and output-manifest check passes.

- [ ] **Step 1: Write RED preparation, resume, merge, and gate tests**

Require exact mapping/seeds/run size; triggered diagnostic and passed primary; every frozen input hash; atomic conflicting-run refusal with no force path; four distinct constraint-valid starts; fingerprinted retry without duplicate draws; extension epochs distinct from job attempts; reviewed extension authorization; exact allowed iteration/draw pairs; completed-chain idempotence only after artifact hashes verify; HOLD on missing/extra/wrong-seed/wrong-draw/tampered chains; inclusive diagnostic thresholds and one-ULP failures; centering/scaling/singleton/contribution checks; exact eight comparison rows; output tamper detection; and no passed comparison on HOLD.

- [ ] **Step 2: Implement atomic preparation**

Write the frozen county order, edge list, component table, scale certificate, source/input manifests, operational-config hash, target/chain fingerprints, and four fresh feasible latent-count/spatial initializations to a temporary run root, then atomically publish. Existing identical preparation is idempotent; any conflict is HOLD.

- [ ] **Step 3: Implement strict chain execution and resume**

The runner accepts only `--run-id`, `--array-index`, and manifest-bound `--extension-epoch`, resolves the immutable mapping, verifies all manifests before checkpoint discovery, rejects incompatible/corrupt checkpoints, and writes atomic status plus per-artifact hashes. USR1/deadline checkpoint status exits 75 so `afterok` cannot finalize an incomplete epoch. Within-epoch retry resumes only failed/checkpointed indexes; an extension authorization continues all four prior completed chains with adaptation frozen.

- [ ] **Step 4: Implement merge and gate**

The merger requires exactly four completed chains with a common extension epoch and the exact matching iteration/draw pair: `(180000,4500)`, `(270000,7500)`, `(360000,10500)`, or `(450000,13500)`. It writes scalar and spatial diagnostics, county structured/unstructured/combined summaries, acceptance/constraint summaries, a pre-gate raw/merged artifact manifest, and a candidate primary-versus-spatial comparison.

The release sequence is fixed: merge and candidate comparison -> pre-gate manifest -> independent verifier -> final release manifest -> gate last. The release manifest covers all existing raw/merged/candidate/verifier artifacts and contains a `planned_outputs` entry mapping final `primary_vs_spatial.csv` to the exact candidate byte hash; it does not claim that the final path already exists and does not cover the gate itself. The gate validates that mapping, exact graph/run/seed/draw schemas, zero failures, all thresholds, hashes, and eight comparison rows. Only then does it publish those exact candidate bytes atomically as `primary_vs_spatial.csv`, rehash them, and atomically publish `spatial_sensitivity_gate.json` recording the final hash, action `freeze_spatial_sensitivity`, `submission_authorized: false`, and a noncausal interpretation boundary. A comparison without a passed gate is never authorized evidence.

- [ ] **Step 5: Add an implementation-independent result verifier**

`scripts/109_gate_sr_v2_spatial_sensitivity.py --independent-verify` must execute an isolated verifier code path that does not import `spatial_bym2`, the merger, or their helpers. An AST/import test enforces that boundary. It reconstructs the graph/scales from frozen bytes, hashes all artifacts, recomputes raw-chain rank-normalized split R-hat and bulk/tail ESS, recomputes comparisons, verifies protected trees, and writes `independent_spatial_sensitivity_verification.json`. Adversarial fixtures corrupt one source, graph edge, chunk, diagnostic, comparison cell, or manifest hash at a time.

- [ ] **Step 6: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_sensitivity_pipeline.py tests\test_sr_v2_spatial_sensitivity.py -q --basetemp=<unique-temp>
.\.venv\Scripts\python.exe -m pytest -q --basetemp=<unique-temp>
git add scripts/106_prepare_sr_v2_spatial_sensitivity.py scripts/107_run_sr_v2_spatial_sensitivity_chain.py scripts/108_merge_sr_v2_spatial_sensitivity.py scripts/109_gate_sr_v2_spatial_sensitivity.py tests/test_sr_v2_spatial_sensitivity_pipeline.py
git commit -m "feat: add fail-closed SR-v2 BYM2 sensitivity epoch"
```

### Task 4: Checksum-gated Wahab orchestration

**Files:**
- Create: `hpc/wahab/stage_sr_v2_spatial_sensitivity_to_scratch.sh`
- Create: `hpc/wahab/sync_sr_v2_spatial_sensitivity_results_home.sh`
- Create: `hpc/wahab/slurm/65_sr_v2_spatial_sensitivity_benchmark.sbatch`
- Create: `hpc/wahab/slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch`
- Create: `hpc/wahab/slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch`
- Create: `hpc/wahab/submit_sr_v2_spatial_sensitivity.sh`
- Create: `hpc/wahab/resume_sr_v2_spatial_sensitivity.sh`
- Modify: `tests/test_sr_v2_spatial_sensitivity_pipeline.py`

**Interfaces:**
- Full-frame preflight benchmark on `main`, two hours, four CPUs, 64 GiB.
- Then spatial array `1-4%2`, `main`, 72 hours, four CPUs, 64 GiB/task, `--signal=B:USR1@300`.
- Independent `afterok` finalizer on `timed-main`, two hours, eight CPUs, 64 GiB.

- [ ] **Step 1: Add RED static DAG and shell tests**

Require exact resources, SHA-256 checks before Python, EXIT-trap sync, no `--delete` or force overwrite, run-specific paths, exit 75 checkpointing, `extension_epoch 0..3`, `job_attempt 1..3` per epoch, completed-chain exclusion for within-epoch retry, all-chain inclusion for an authorized extension, old-finalizer cancellation/ledgering, and new `afterok` finalizer creation.

- [ ] **Step 2: Implement staging and sync**

Stage only committed source/config plus the prepared spatial run inputs and frozen production/diagnostic authorities. Generate `inputs_sha256.txt` in home, copy it, and require `sha256sum -c` in scratch. Sync only the run-specific spatial root and matching logs.

- [ ] **Step 3: Implement array, finalizer, submit, and resume wrappers**

The benchmark runs 2,000 full-frame iterations of the exact prepared target without publishing scientific draws, records iterations/second, `/usr/bin/time -v` peak RSS, and chunk throughput, and extrapolates the 180,000-iteration epoch with a 20% overhead factor. It exits nonzero unless projected runtime is at most 65 hours and peak RSS at most 56 GiB. The spatial array depends `afterok` on this benchmark. On benchmark failure, the submit/resume helper cancels and records the unsatisfiable spatial array/finalizer, leaves spatial status HOLD, and never converts the failure into a chain retry or extension.

The finalizer verifies inputs, runs merge, writes the pre-gate manifest, runs independent verification, writes the final release manifest, runs the gate last, and syncs on every exit. Within-epoch resume validates the original target, selects only checkpointed/failed indexes, refuses job attempt four, cancels and records the prior unsatisfiable finalizer, and submits a new finalizer. A convergence extension requires a reviewed `extension_authorization_epoch_N.json`, advances all four chains, freezes adaptation, and fingerprints the new authorization.

- [ ] **Step 4: Verify and commit**

```powershell
bash -n hpc/wahab/stage_sr_v2_spatial_sensitivity_to_scratch.sh hpc/wahab/sync_sr_v2_spatial_sensitivity_results_home.sh hpc/wahab/submit_sr_v2_spatial_sensitivity.sh hpc/wahab/resume_sr_v2_spatial_sensitivity.sh hpc/wahab/slurm/65_sr_v2_spatial_sensitivity_benchmark.sbatch hpc/wahab/slurm/66_sr_v2_spatial_sensitivity_chain_array.sbatch hpc/wahab/slurm/67_sr_v2_finalize_spatial_sensitivity.sbatch
.\.venv\Scripts\python.exe -m pytest tests\test_sr_v2_spatial_sensitivity_pipeline.py -q --basetemp=<unique-temp>
.\.venv\Scripts\python.exe -m pytest -q --basetemp=<unique-temp>
git add hpc/wahab tests/test_sr_v2_spatial_sensitivity_pipeline.py
git commit -m "hpc: add SR-v2 BYM2 sensitivity Slurm epoch"
```

### Task 5: Authenticated execution, independent retrieval, and evidence freeze

**Dependencies:** Spatial Tasks 1-4 and heavy-sensitivity Tasks 1-5 must be independently reviewed first. Heavy Task 6 exclusively owns the one-time code transfer and combined submission. It submits the heavy array at `%6`, the spatial benchmark, the benchmark-dependent spatial array at `%2`, and separate finalizers/gates. This task never submits a duplicate job.

**Files:**
- Create remotely: timestamped clean clone and run-specific spatial scratch/output roots.
- Create locally after completion: verified spatial run root and matching Slurm logs.
- Modify: `.gitattributes`
- Modify: `docs/scientific_reports_v2/active_execution_status.md`

- [ ] **Step 1: Verify the combined-launch handoff**

Read the combined launch ledger and require verified Git bundle SHA-256, remote commit id, timestamped clone, frozen source hashes, benchmark id, spatial array id, and spatial finalizer id. If any is absent, HOLD; do not resubmit.

- [ ] **Step 2: Monitor the recorded independent spatial DAG**

Require the benchmark and all four spatial tasks and finalizer to show `sacct` `COMPLETED`/`0:0`; inspect statuses and stderr. Use bounded resume only after fingerprint diagnosis. Never rerun a verified completed chain.

- [ ] **Step 3: Require remote gate and independent-verifier PASS**

Verify exact chains, seeds, iterations/draws or recorded extensions, constraints, graph/scales, diagnostics, comparisons, manifests, and both PASS artifacts. Dashboard status alone is insufficient.

- [ ] **Step 4: Package, download, and verify**

Create a run-specific tar plus sidecar SHA-256 on Wahab. Download both, verify archive safety/hash, extract into a new timestamped staging directory, and recompute every internal hash before selective integration.

- [ ] **Step 5: Preserve bytes, status, and evidence**

Add `outputs/scientific_reports_v2/spatial_sensitivity/** -text` plus exact log coverage. Confirm Git no-filter blob equality, unchanged `v1.1.1`, unchanged production/diagnostic trees, and current active-status wording.

```powershell
git add .gitattributes docs/scientific_reports_v2/active_execution_status.md outputs/scientific_reports_v2/spatial_sensitivity logs/slurm
git commit -m "data: freeze verified SR-v2 BYM2 sensitivity"
```

- [ ] **Step 6: Preserve the manuscript boundary**

The manuscript collector must first verify the trigger action; because it is triggered, a documented non-run is invalid. It then requires the passed spatial gate, independent-verifier PASS, valid comparison/output hashes, and the noncausal interpretation boundary. Machine completion never authorizes submission.
