# Constraint geometry and identifiability

The rank is computed on free county-year latent cells after fixed exact and zero cells are removed. National-year and grand-total rows are treated as reconciliation checks because they are algebraic sums of the state-year rows over the same modeled universe.

| Quantity | Value |
| --- | ---: |
| latent variables | 9,695 |
| nominal state year equalities | 306 |
| nominal county period equalities | 1,420 |
| nominal national year equalities | 6 |
| nominal grand total equalities | 1 |
| nonzero reduced equalities | 1,259 |
| independent equalities | 1,256 |
| equality nullity | 8,439 |
| intrinsic margin dependencies | 3 |
| algebraically redundant higher level equalities | 7 |
| zero information equalities | 467 |
| county period interval constraints | 1,722 |
| latent cell bound constraints | 9,695 |
| graph components | 50 |
| graph components without interval half edge | 3 |

The equality nullity is the affine dimension before cell bounds and county-period interval inequalities are applied. It therefore measures residual freedom under independent public equalities, not the number of posterior-identifiable individual counts.
