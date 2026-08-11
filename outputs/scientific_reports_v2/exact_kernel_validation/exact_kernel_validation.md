# Exact enumerable-kernel validation

Two deliberately adversarial finite fibers are evaluated against their exact conditional posterior distributions.

1. A chordless six-cycle demonstrates that transfer and 2x2 moves do not form a universal connecting move family.
2. A cross-year path between interval-margin endpoints demonstrates that cycles plus same-year interval transfers are also insufficient in general.

## chordless_six_cycle_structural_support

- Feasible states: 2
- Exact probabilities: [0.5331948544600152, 0.46680514553998537]
- Empirical probabilities: [0.5353965517241379, 0.4646034482758621]
- Maximum empirical absolute error: 0.002202
- Blocked strongly connected components: 2
- Repaired strongly connected components: 1
- Repaired stationarity error: 1.665e-16
- Repaired detailed-balance error: 1.388e-17
- Status: PASS

## cross_year_interval_endpoint_path

- Feasible states: 2
- Exact probabilities: [0.7173541861973528, 0.2826458138026469]
- Empirical probabilities: [0.7146551724137931, 0.2853448275862069]
- Maximum empirical absolute error: 0.002699
- Blocked strongly connected components: 2
- Repaired strongly connected components: 1
- Repaired stationarity error: 3.331e-16
- Repaired detailed-balance error: 2.498e-16
- Status: PASS

Overall status: **PASS**.

These finite tests establish correctness for the enumerated cases; they do not replace full-data dispersed-start, movement, and joint-chain diagnostics.
