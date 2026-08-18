# Scientific Reports v2 robustness completion design

## Authority and objective

This design implements Phases 6–8 of `SCIENTIFIC_REPORTS_V2_EXECUTION_PLAN.md` under the prespecification in `config/scientific_reports_v2_robustness_registry.yaml`. The passed corrected production gate at `outputs/scientific_reports_v2/production_8chain/production_gate.json` is the primary-result authority. The archived `v1.1.1` tag and commit `50b468d212616ee80be55045dedf8a696db14df5` remain immutable.

The objective is to complete the prespecified spatial, prior, model-family, pandemic-period, age-structure, and suppression-handling checks; freeze a single machine-readable robustness result; and populate the Scientific Reports manuscript only from passed evidence. Human-only author, ethics, and repository DOI/version fields remain outside the machine pipeline.

## Global invariants

- Never mutate `outputs/scientific_reports_v2/production_8chain/**` after commit `a6de9ae`.
- Every derived analysis records SHA-256 hashes of the production gate, primary summary, frozen registry, operational configuration, and direct inputs.
- Every chain uses a fresh feasible initialization. No sensitivity chain resumes a primary or different-target checkpoint.
- A missing, incomplete, tampered, or nonconverged analysis writes a machine-readable HOLD and exits nonzero.
- No robustness estimate enters the manuscript until the aggregate robustness gate passes.
- The machine pipeline never supplies `AUTHOR_BLOCK`, `ETHICS_DETERMINATION`, `REPOSITORY_DOI_AND_VERSION`, `REPOSITORY_VERSION`, or `REPOSITORY_DOI`.
- All public result files and Slurm evidence are covered by `-text` rules before Git indexing so Windows line-ending conversion cannot invalidate hashes.

## Design rulings

### Spatial diagnostic

The existing Moran implementation is scientifically retained but its dense permutation implementation is replaced internally by a SciPy CSR calculation. The county ordering, row-standardized weights, RNG seed, permutation sequence, expected statistic, and two-sided p-value rule remain unchanged. The diagnostic runs locally from the frozen production summaries and archives the Census adjacency bytes, URL, retrieval timestamp, and SHA-256.

If `recommended_action` is `run_spatial_random_effect_sensitivity`, the result freeze requires a separately passed structured-plus-unstructured county sensitivity. If the action is the non-trigger branch, the manuscript records that the prespecified threshold was not met and does not imply spatial independence.

### Model-family sensitivity

The model-family sensitivity is strict Poisson, not an arbitrarily large NB2 dispersion. One canonical `count_logpmf` dispatcher supplies the full target, local count moves, heat-bath weights, and exact finite-state validation. Under Poisson, `Theta.log_kappa` remains only as an inert checkpoint-compatibility field: it is not updated, included in the prior, serialized as a posterior parameter, or reported as a diagnostic.

### Pandemic interaction

The full 2019–2024 constraints remain active. The 2019 period is the interaction reference. Six rurality interaction columns are added: each of the three nonreference rurality indicators crossed with acute pandemic (2020–2021) and later period (2022–2024). Annual year effects remain in the model, so no redundant pandemic-period intercept is added. Period-specific rurality IRRs are calculated draw by draw before exponentiation and quantiles.

### Pandemic exclusion

The retained years are 2019 and 2022–2024. Annual county-cell bounds and compatible state-year and national-year equalities remain active. The 2019–2024 Q001 county-period total is incompatible with the subset and is not applied. For engine compatibility, retained-period county bounds are set to the tautological sums of retained annual lower and upper bounds, and the modeled grand total is the sum of retained Q003 national-year totals. The transformation preserves source Q001 fields as audit columns and records the policy `full_period_q001_not_applied`.

### Age-structure sensitivity

The archived 2022 SVI county file already supplies percentage aged under 18 (`EP_AGE17`) across the same public county covariate source. The sensitivity retains standardized percentage aged 65 or older and adds standardized percentage aged under 18, preserving the county universe and existing imputation policy. This satisfies the registry’s “augment if reproducibly available” branch without importing an unversioned new covariate source.

### Heavy sensitivity epoch

The immutable run id is `sr-v2-heavy-sensitivity-20260818-v1`. Each profile uses four chains, 180,000 iterations, 45,000 burn-in iterations, thinning by 30, and 4,500 retained draws per chain.

| Array indexes | Profile | Chain seeds | Initialization seeds |
| --- | --- | --- | --- |
| 1–4 | `prior_broader` | 68291–68294 | 67291–67294 |
| 5–8 | `prior_regularizing` | 69291–69294 | 67391–67394 |
| 9–12 | `model_family_poisson` | 70291–70294 | 70251–70254 |
| 13–16 | `pandemic_interaction` | 71291–71294 | 71251–71254 |
| 17–20 | `pandemic_exclusion` | 72291–72294 | 72251–72254 |
| 21–24 | `age_structure_age17` | 73291–73294 | 73251–73254 |

Wahab uses `main`, 72 hours, one task, four CPUs, 64 GiB per array task, `--array=1-24%8`, and `--signal=B:USR1@300`. The concurrency matches the already successful eight-chain primary run. A timeout checkpoint exits nonzero so `afterok` cannot finalize partial work. A bounded resume submits only checkpointed/failed indexes, refuses more than three attempts, never reruns completed chains, and attaches a new finalizer.

### Suppression handling

The refreshed comparator includes exactly the six registry scenarios: visible exact/zero only, fixed 1, fixed 5, fixed 9, population-favoring feasible allocation, and constrained Bayesian primary. The constrained row is loaded from the corrected primary summary and must match it numerically. Legacy extra scenarios and v1 literals are excluded.

### Manuscript result freeze

A pure aggregator validates eight evidence families: primary, calibration, spatial, prior, model-family, temporal, age, and suppression. It emits a HOLD before validation and atomically replaces it with PASS only after every required artifact and hash validates. It renders all machine-authorized placeholders, leaves exactly the five human-only placeholders unresolved, produces normalized Supplementary Tables S1–S9, and records `submission_authorized: false`.

The legacy submission layer is changed to read the passed result-freeze contract rather than hardcoded seeds, cluster wording, diagnostic values, or YAML scalars. Submission-mode QC still requires zero placeholders; therefore the final machine state remains HOLD until the human-only fields and immutable archive DOI/version are supplied and separately approved.

## Data flow

```text
passed primary evidence
  ├─ local sparse Moran diagnostic ── spatial action
  ├─ refreshed suppression comparators
  └─ checksum-gated 24-chain Wahab epoch
       └─ afterok merge and computational gate
            └─ verified local retrieval
                 └─ eight-family robustness/result freeze
                      ├─ frozen nonfinal manuscript and supplement
                      ├─ S1–S9 tables and figures
                      └─ submission/package QC
```

## Verification boundary

Passing the heavy sensitivity and manuscript-result gates authorizes scientific result freeze and document generation. It does not authorize GitHub push, DOI minting, repository publication, journal upload, or statements about institutional ethics review. Those remain explicit human/external gates.
