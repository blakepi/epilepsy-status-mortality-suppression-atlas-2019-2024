# Scientific Reports v2: target density and first inference-engine repair

## Frozen baseline

Scientific Reports v2 branches from the immutable `v1.1.1` tag at commit `50b468d212616ee80be55045dedf8a696db14df5`. The archived v1.1.1 outputs remain historical artifacts and are not overwritten. No v1.1.1 estimate should be relabeled as a corrected v2 result.

## Implemented target density

For county-year cell i, let Y_i denote the observed or latent G40/G41 mortality-mention count. Exact and explicit-zero cells are fixed. A suppressed county-year cell is restricted to an integer in its public interval, ordinarily {1,...,9}. Let F be the set of integer count vectors satisfying the county-year bounds, county-period constraints, state-year totals, and their compatible higher-level reconciliation totals.

Conditional on parameters theta, the model uses the negative-binomial-2 likelihood

Y_i | theta ~ NB2(mu_i, kappa), with Var(Y_i | theta) = mu_i + mu_i^2 / kappa,

and

log(mu_i) = log(N_i) + x_i^T beta + u_s(i) + gamma_t(i).

The state and year effects obey sum-to-zero constraints. The posterior sampled by the count/parameter chain is proportional to the feasible-state indicator, the product negative-binomial likelihood, and the documented fixed-effect, random-effect, scale, and dispersion priors.

The fixed-effect and hyperprior families remain those documented in v1.1.1 unless a later prespecified sensitivity changes them. Scientific Reports v2 corrects the Gaussian normalizing power for centered random effects: a zero-sum vector of length S has S-1, not S, free dimensions. Its conditional log density kernel is

-0.5 * sum_s(u_s^2 / sigma^2) - (S-1) * log(sigma).

The v1.1.1 code counted S normalizing factors before the log-scale Jacobian, adding one unintended -log(sigma) term per centered random-effect family. The v2 helper `centered_normal_log_density` uses the correct subspace dimension. A corrected production rerun is required to determine the numerical effect.

## Confirmed local-runner defect

The legacy local runner permitted latent-count moves to change y, then evaluated the first parameter Metropolis proposal against a cached log posterior computed for the preceding y. The HPC production path refreshed the target after count moves, but the local path did not. Scientific Reports v2 refreshes the current log posterior immediately after the count-move sweep and before any parameter proposal. The local and HPC paths must agree before a new release is frozen.

## Exact counterexample to the v1.1.1 move family

Constraint compliance does not establish irreducibility. A three-county by three-year toy system was constructed whose free-cell support is a chordless six-cycle. All county-period and year margins are exact. The fiber contains exactly two feasible allocations.

State-year transfers cannot move because every county-period total is fixed. The support contains no all-free 2x2 rectangle, so the v1.1.1 2x2 swap cannot move either. The resulting latent kernel has two strongly connected components even though every state it visits is legal. This is a concrete counterexample to treating invariant checks as sufficient evidence of posterior exploration.

## General-cycle repair

The v2 engine adds an alternating simple-cycle proposal on the county-by-year bipartite free-cell support. For a selected state, it samples distinct counties and years, constructs an even cycle, and alternates +1 and -1 around that cycle. The move preserves each selected county-period total and every state-year total exactly. The support selection is independent of current count values and the opposite sign is proposed with equal probability, so the proposal is symmetric and uses the same local likelihood-ratio Metropolis rule as the existing count moves.

The existing 2x2 move remains as the efficient length-four special case. Longer cycles have positive proposal probability up to the number of modeled years. This addresses the demonstrated structural-zero failure mode, although full-data exploration still requires empirical support-graph and dispersed-start diagnostics.

## Exact enumerable validation

The new validation module enumerates all feasible states for deliberately small systems, computes their exact conditional posterior probabilities for fixed parameters, constructs the exact transition matrix implied by each move mixture, and reports row-stochasticity error, posterior stationarity error, detailed-balance error, strongly connected components, and empirical versus exact state frequencies from the actual stochastic move implementation.

The chordless six-cycle test is required to show that the legacy 2x2-only kernel is disconnected and that the general-cycle kernel is connected, reversible, stationary for the exact target, and empirically calibrated within a prespecified Monte Carlo tolerance.

## Constraint geometry

The v2 identifiability module builds the equality system on free suppressed cells only, after fixed exact and zero cells are removed. Its exact rank calculation uses the bipartite incidence structure linking state-year margins to exact county-period margins. Interval-constrained counties appear as half-edges. A connected component without an interval half-edge contributes one margin dependency; a component with a half-edge has full row rank.

National-year rows are algebraic sums of state-year rows over the same modeled universe, and the grand total is their sum. They remain important reconciliation checks but are not counted as independent identifying information. The generated report distinguishes nominal rows, nonzero reduced rows, independent equality rank, affine nullity, interval inequalities, and cell bounds.

## Gate status

This execution unit can pass only when:

1. the corrected target-density tests pass;
2. local and HPC count/parameter bookkeeping are aligned;
3. the six-cycle counterexample is reproduced;
4. the repaired exact transition matrix has one strongly connected component, negligible stationarity and detailed-balance errors, and empirical frequencies agreeing with the exact posterior;
5. the full model-frame rank/nullity report is generated without changing source data.

Passing this gate does not authorize manuscript submission or validate the old 1.23 estimate under the corrected model. It authorizes pilot tuning, latent-space diagnostics, and the corrected eight-chain production rerun.
