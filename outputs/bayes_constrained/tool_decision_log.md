# Tool Decision Log

- Python was used as the primary implementation language because the existing repository is Python-based and the required workflow depends on pandas/numpy/scipy sparse matrices, MILP initialization, custom constrained MCMC, validation, tables, figures, and python-docx manuscript generation.
- `scipy.optimize.milp` was used for feasible integer initialization because it is available in the project environment and directly supports bounded integer decision variables with sparse linear constraints.
- A custom constrained MCMC sampler was used for the primary model because the latent county-year death counts are discrete integers subject to county-year, county-period, state-year, national-year, and grand-total constraints.
- Stan/CmdStanPy/CmdStanR were limited to possible validation roles because Stan does not directly sample unknown discrete parameters and relaxing integer counts would violate the primary constraint target.
- R was not used in the mandatory path because the repository has a complete Python pipeline and no existing mandatory R build route.
- NIMBLE was not used; it was not available as part of the project environment.
- ArviZ/posterior/bayesplot were not used; ArviZ was unavailable, so split R-hat, approximate ESS, traces, densities, and hyperparameter plots were generated with NumPy/pandas/matplotlib.
- Optional acceleration packages such as numba were unavailable and were not required for the validated primary path.
- Final conclusions come from the validated Python constrained path: model frame, MILP initial allocations, custom sampler, per-draw validator, generated summaries, and manuscript-integrated tables/figures.
