# Full-data latent support-graph diagnostics

The exact-margin free-cell support is represented as a bipartite graph linking counties to years within each state. Two-by-two moves traverse length-four cycles. Edges that belong to a cycle but no length-four cycle require longer alternating moves or another Markov-basis element.

| Quantity | Value |
| --- | ---: |
| free cells | 9,695 |
| exact margin free cells | 4,837 |
| interval margin free cells | 4,858 |
| exact margin counties | 960 |
| interval margin counties | 1,722 |
| exact support components | 50 |
| exact support cycle rank | 3,628 |
| exact support cycle edges | 4,790 |
| exact support four cycle edges | 4,790 |
| exact support long cycle only edges | 0 |
| cyclic components without four cycle | 0 |
| states | 51 |
| states with exact support cycles | 50 |
| states with long cycle only edges | 0 |
| states with cyclic component without four cycle | 0 |

This is a structural-support diagnostic, not a proof that the full bounded fiber is irreducible. It determines whether the support contains real-data cycle directions that the v1.1.1 length-four move family could not directly traverse.
