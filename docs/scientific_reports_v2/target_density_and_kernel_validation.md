# Scientific Reports v2: corrected target density and latent-kernel validation

## Frozen baseline

Scientific Reports v2 branches from the immutable `v1.1.1` tag at commit `50b468d212616ee80be55045dedf8a696db14df5`. The archived v1.1.1 outputs remain historical artifacts and are not overwritten. No v1.1.1 estimate is relabeled as a corrected v2 result.

## Implemented target density

For county-year cell i, let Y_i denote the observed or latent G40/G41 mortality-mention count. Exact and explicit-zero cells are fixed. A suppressed county-year cell is restricted to an integer in its public interval, ordinarily {1,...,9}. Let F be the set of integer count vectors satisfying the county-year bounds, county-period constraints, state-year totals, and their compatible higher-level reconciliation totals.

Conditional on parameters theta, the model uses the negative-binomial-2 likelihood

Y_i | theta ~ NB2(mu_i, kappa), with Var(Y_i | theta) = mu_i + mu_i^2 / kappa,

and

log(mu_i) = log(N_i) + x_i^T beta + u_s(i) + gamma_t(i).

The state and year effects obey sum-to-zero constraints. The posterior sampled by the count/parameter chain is proportional to the feasible-state indicator, the product negative-binomial likelihood, and the documented fixed-effect, random-effect, scale, and dispersion priors.

The fixed-effect and hyperprior families remain those documented in v1.1.1 unless a later prespecified sensitivity changes them. Scientific Reports v2 corrects the Gaussian normalizing power for centered random effects: a zero-sum vector of length S has S-1, not S, free dimensions. Its conditional log density kernel is

-0.5 * sum_s(u_s^2 / sigma^2) - (S-1) * log(sigma).

The v1.1.1 code counted S normalizing factors before the log-scale Jacobian, adding one unintended -log(sigma) term per centered random-effect family. The v2 helper `centered_normal_log_density` uses the correct subspace dimension. Exact importance reweighting of the 36,000 archived parameter draws shows that this correction alone changes the nonmetro-nonadjacent median IRR from 1.234985 to 1.234585, a -0.032% shift. It changes the state-effect scale median by approximately 1.35% and the year-effect scale median by approximately 13.65%. This reweighting isolates the prior correction only and does not replace corrected sampling.

## Confirmed local-runner defect

The legacy local runner permitted latent-count moves to change y, then evaluated the first parameter Metropolis proposal against a cached log posterior computed for the preceding y. The HPC production path refreshed the target after count moves, but the local path did not. Scientific Reports v2 refreshes the current log posterior immediately after the count-move sweep and before any parameter proposal. The local and HPC paths now use the same target bookkeeping.

## Why invariant checks were not enough

Constraint compliance does not establish irreducibility or correct stationary probabilities. A three-county by three-year toy system was constructed whose free-cell support is a chordless six-cycle. All county-period and year margins are exact, and the fiber contains exactly two feasible allocations.

State-year transfers cannot move because every county-period total is fixed. The support contains no all-free 2x2 rectangle, so the v1.1.1 2x2 move cannot connect the two allocations. The resulting latent kernel has two strongly connected components even though every state it visits is legal. This is a concrete counterexample to treating zero constraint violations as sufficient evidence of posterior exploration.

The real model frame was also audited structurally. It contains 9,695 free latent county-year cells. The exact-margin county-by-year support has cycle rank 3,628, and supported 2x2 cycles span all 3,628 cycle-space dimensions over GF(2). Thus the adversarial chordless-cycle obstruction is a genuine generic failure mode but was not detected as an unspanned support direction in the present application. Bounds and posterior concentration can nevertheless make single-unit transitions mix slowly.

## General-cycle and exact heat-bath repair

The v2 engine adds an alternating simple-cycle direction on the county-by-year bipartite free-cell support. For a selected state, it samples distinct counties and years, constructs an even cycle, and alternates +1 and -1 around that cycle. The direction preserves each selected exact county-period total and every state-year total.

More importantly, v2 no longer restricts a selected direction to a single +/-1 Metropolis step. For each selected pair, 2x2 rectangle, or longer cycle, the engine enumerates every integer amplitude compatible with county-year bounds and county-period bounds, evaluates the negative-binomial likelihood at every admissible point on that finite line, and samples the amplitude from its exact conditional distribution. Zero amplitude is included. This random-scan heat-bath update has the intended conditional target by construction and can traverse several count units in one accepted block update.

The 2x2 move remains the efficient length-four special case. Longer cycles retain positive selection probability as protection against structural-zero fibers. Interval-margin transfers use the same full-line heat-bath mechanism while allowing county-period totals to vary within their public ranges.

## Exact enumerable validation

The validation module enumerates every feasible state for deliberately small systems, computes the exact conditional posterior probabilities for fixed parameters, constructs the exact transition matrix implied by the production heat-bath move mixture, and reports row-stochasticity error, posterior stationarity error, detailed-balance error, strongly connected components, and empirical versus exact state frequencies from the actual stochastic implementation.

For the chordless six-cycle test, the 2x2-only kernel has two strongly connected components. The repaired general-cycle heat-bath kernel has one component, row-sum error below 5e-16, stationarity error below 2e-16, and detailed-balance error below 2e-17. Exact state probabilities were 0.53319 and 0.46681; empirical frequencies were 0.52759 and 0.47241 after simulation.

Thirty additional reproducible bounded fibers, each fully enumerated, also passed. They contained 2-18 feasible states and mixtures of exact and interval county-period margins. The maximum repaired stationarity error was 3.33e-16 and maximum detailed-balance error was 1.53e-16. These finite tests establish correctness for the tested systems, not a theorem covering every possible full-data fiber.

## Constraint geometry

The v2 identifiability module builds the equality system on free suppressed cells only, after fixed exact and zero cells are removed. Its exact rank calculation uses the bipartite incidence structure linking state-year margins to exact county-period margins. Interval-constrained counties appear as half-edges. A connected component without an interval half-edge contributes one margin dependency; a component with a half-edge has full row rank.

The application has 9,695 free latent variables and 1,256 independent public equalities, leaving equality nullity 8,439 before county-year bounds and 1,722 county-period interval inequalities are applied. Six national-year rows are algebraic sums of state-year rows over the same modeled universe, and the grand total is their sum. These seven rows remain important reconciliation checks but are not counted as independent identifying information.

## Full-data movement pilot

Four independently generated feasible allocations were evolved for 25,000 fixed-parameter heat-bath proposals each. Every recorded state remained constraint-valid. The median chain changed 13.62% of free cells relative to its own start, versus approximately 9% under the earlier single-unit pilot. Pairwise cell-space distance declined only modestly, with a median final-to-start L1 ratio of 0.970. The interval-margin move changed state most often; cycle blocks changed state least often because randomly selected long supports frequently had only zero as an admissible amplitude.

This pilot supports the heat-bath repair but does not establish full posterior convergence. Proposal-profile tuning and joint parameter/latent pilots are therefore required before HPC production.

## Current gate status

The first inference-engine gate has passed:

1. the corrected target-density tests pass;
2. local and HPC count/parameter bookkeeping are aligned;
3. the six-cycle counterexample is reproduced;
4. exact repaired transition matrices are connected and stationary in the tested fibers;
5. randomized exact validation passes 30 of 30 systems;
6. the full model-frame rank/nullity and support-graph reports are generated without changing source data;
7. all recorded fixed-parameter pilot states satisfy every public constraint.

Passing this gate does not authorize manuscript submission or validate the archived 1.23 estimate under the corrected joint sampler. It authorizes proposal tuning, a short corrected joint pilot, and then—only if those diagnostics pass—the corrected eight-chain production run.
