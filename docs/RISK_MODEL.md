# Delay-risk model

The initial model is deliberately deterministic and explainable. Scores are capped at 100 and combine:

| Factor | Maximum contribution |
|---|---:|
| Positive planned-minus-actual variance | 35 |
| Critical-path status | 18 |
| Delayed predecessors | 18 |
| Stale evidence beyond 24 hours | 12 |
| Planned finish overdue | 10 |
| Safety/quality interruptions | 7 |

Bands: low `<25`, medium `<50`, high `<75`, critical `≥75`.

Every assessment stores the score, band, named factor contributions, reasons, recommendation, model version, and calculation time. The score is an operational triage indicator, not a contractual delay entitlement or probabilistic forecast trained on industry data.
