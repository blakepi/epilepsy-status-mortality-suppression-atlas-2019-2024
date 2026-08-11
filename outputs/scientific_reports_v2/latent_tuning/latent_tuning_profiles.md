# Scientific Reports v2 latent-move profile comparison

Four circuit-aware proposal mixtures were compared from the same four dispersed feasible allocations with model parameters held fixed. Selection prioritizes convergence of rurality/SVI latent totals, then cell-space distance reduction and breadth of cell exploration.

| Profile | Changed proposals | Free cells changed | Cell-distance ratio | Rurality/SVI-distance ratio | Score | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balanced_circuit_heatbath | 0.0834 | 0.1578 | 0.9620 | 0.5294 | 0.2530 | 116.3 |
| direct_interval_heavy | 0.1106 | 0.1639 | 0.9616 | 0.5772 | 0.2361 | 158.2 |
| exact_margin_heavy | 0.0649 | 0.1538 | 0.9638 | 0.5887 | 0.2274 | 77.7 |
| interval_path_heavy | 0.0874 | 0.1583 | 0.9634 | 0.7131 | 0.1793 | 120.4 |

Selected profile: **balanced_circuit_heatbath**.

This profile is eligible for a short joint parameter/latent pilot. It is not yet a production setting and may be revised if joint-chain diagnostics expose a different bottleneck.
