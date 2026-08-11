# Scientific Reports v2 latent-move profile comparison

Four proposal mixtures were compared from the same four dispersed feasible allocations with model parameters held fixed. Selection prioritizes convergence of rurality/SVI latent totals, then cell-space distance reduction and breadth of cell exploration.

| Profile | Changed proposals | Free cells changed | Cell-distance ratio | Rurality/SVI-distance ratio | Score | Runtime (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| balanced_heatbath | 0.0556 | 0.1195 | 0.9772 | 0.3815 | 0.2949 | 73.0 |
| interval_heavy | 0.1099 | 0.1655 | 0.9599 | 0.4776 | 0.2769 | 167.1 |
| exact_margin_heavy | 0.0709 | 0.1533 | 0.9626 | 0.5319 | 0.2503 | 98.4 |
| hybrid_interval | 0.0945 | 0.1561 | 0.9640 | 0.5410 | 0.2472 | 141.1 |

Selected profile: **balanced_heatbath**.

This profile is eligible for a short joint parameter/latent pilot. It is not yet a production setting and may be revised if joint-chain diagnostics expose a different bottleneck.
