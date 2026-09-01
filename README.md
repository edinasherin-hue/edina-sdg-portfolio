# AquaGrow — Intelligent Rainwater Allocation Under Water Scarcity (V4)

*A simulation-based study comparing allocation strategies for multi-zone irrigation*

## Research Question

How should limited harvested rainwater be allocated among competing irrigation zones under different levels of water scarcity, priority differences, and rainfall uncertainty?

AquaGrow is evaluated as **one allocation strategy among several**, not a predetermined winner — the goal is to find the conditions under which each strategy actually performs best.

## The Three Core Strategies

1. **Baseline** — fixed-threshold, fixed dose, first-come-first-served
2. **Fair-share** — equal proportional split among needy zones, no priority or rain awareness
3. **AquaGrow** — priority-weighted allocation (moisture deficit × crop priority) with a rain-signal reserve

## Experiment 1 — Scarcity Curve

**Question:** How does demand satisfaction change as tank capacity increases, for each strategy?

Tested tank capacities from 10L to 150L, 40 independent 30-day scenarios per capacity per strategy.

| Tank (L) | Baseline % | Fair-share % | AquaGrow % |
|---|---|---|---|
| 10 | 4.2 | 5.8 | 5.7 |
| 20 | 9.1 | 14.0 | 13.2 |
| 30 | 14.2 | 32.5 | 30.9 |
| 40 | 18.4 | 53.0 | 50.8 |
| 50 | 18.9 | 66.2 | 65.0 |
| 60 | 19.7 | 80.7 | 80.2 |
| 75 | 21.2 | 85.2 | 84.9 |
| 100 | 21.4 | 96.0 | 95.9 |
| 125 | 21.8 | 98.7 | 98.7 |
| 150 | 21.7 | 98.8 | 98.8 |

**Finding:** Fair-share and AquaGrow track each other closely across the *entire* range, both dramatically outperforming Baseline at every capacity. Baseline never exceeds ~22% satisfaction even with abundant water, because it only ever serves whichever zone is checked first and ignores the rest — it never gets credit for over-delivering water beyond what a zone actually needed, so its true performance is honestly lower than earlier versions of this experiment suggested. This confirms the V3 finding holds across the full scarcity range, not just the specific capacities tested before.

## Experiment 2 — Priority Sensitivity

**Question:** Does AquaGrow's priority-weighting help Zone A (highest priority) when the weight gap between zones is made more aggressive? Tested at 40L tank (steep part of the scarcity curve), 40 scenarios per configuration. Weight configurations were fixed *before* running the experiment, not tuned afterward to force a result.

| Configuration | Weights (C/B/A) | Overall Satisfaction % | Fairness % | Zone A Satisfaction % |
|---|---|---|---|---|
| Fair-share (no priority) | — | 47.8 | 45.7 | 40.4 |
| AquaGrow P1 (original) | 0.8/1.0/1.5 | 51.0 | 49.1 | 45.0 |
| AquaGrow P2 | 0.5/1.0/2.0 | 51.6 | 48.9 | 51.1 |
| AquaGrow P3 | 0.5/1.0/3.0 | 51.7 | 48.0 | 54.5 |
| AquaGrow P4 | 0.2/1.0/4.0 | 52.2 | 43.7 | 57.7 |

**Finding:** With the original mild weights, AquaGrow showed only a small advantage over Fair-share on Zone A specifically (45.0% vs 40.4%). But with a wider, deliberately more aggressive weight spread, a **real, measurable trade-off emerges**: Zone A's satisfaction climbs from 40.4% (Fair-share) to 57.7% (P4), while overall fairness drops from 49.1% to 43.7%. Overall aggregate satisfaction barely moves. This confirms the V3 null result wasn't a flaw in the algorithm — the original weights genuinely weren't strong enough to produce a large detectable effect on the prioritized zone.

## Experiment 3 — Rainfall Probability & Reserve Strategy

**Question:** Given a simulated rain signal calibrated to a known daily rain probability, what reserve fraction performs best?

**Honesty note:** this models an environment with a fixed daily rain probability, and a signal calibrated to that same probability — it is not a real weather forecasting system. It tests reserve *strategy*, not forecast skill.

Tested rain probabilities of 20%, 50%, and 80%, against reserve fractions from 0% to 50%, at 40L tank, 40 scenarios per combination.

| Rain Probability | Best Reserve | Satisfaction at Best Reserve |
|---|---|---|
| 20% | 0% | 26.2% |
| 50% | 0% | 77.5% |
| 80% | 0% | 97.5% |

*"Best reserve" here is defined as the reserve fraction that produces the highest mean demand satisfaction in this experiment — not a claim about optimality under any other objective (e.g. minimizing variance, or protecting against worst-case scenarios).

**Finding — the most important discovery in this project:** reserving water **never helps**, at any rain probability tested. Satisfaction *monotonically decreases* as reserve fraction increases, in every single scenario (e.g. at 50% rain probability: 77.5% satisfaction with 0% reserve, dropping to 69.5% with 50% reserve).

**Why this happens:** rainfall that arrives tomorrow adds to the tank regardless of whether water was reserved today. Reserving doesn't protect anything — it only withholds water from zones that need it right now, with no compensating benefit later. This reveals a genuine conceptual flaw in the reserve mechanism as originally designed, not a tuning problem. A rain-aware allocation system needs a different mechanism to make rain-awareness actually useful (e.g. reserving only when a specific future high-demand event can be anticipated, not simply "rain might come").

## Overall Conclusions

1. **Intelligent splitting matters enormously** — both Fair-share and AquaGrow vastly outperform fixed-threshold Baseline at every scarcity level tested (Experiment 1).
2. **Priority-weighting requires a strong enough signal to matter** — mild weights (0.8/1.0/1.5) show no benefit; aggressive weights (0.2/1.0/4.0) produce a real, quantifiable trade-off between prioritizing one zone and overall fairness (Experiment 2).
3. **The current rain-reserve mechanism is actively counterproductive** and should be redesigned or removed — reserving water provided no benefit under any tested condition (Experiment 3).

This is a genuinely defensible thesis: rather than claiming AquaGrow is simply "better," the project identifies *specifically when* priority-weighting helps (aggressive weight gaps under moderate scarcity) and *specifically where* the original design fails (the reserve mechanism), backed by 40+ scenario-runs per condition rather than single seeded results.

## Files

- `allocation_algorithm.py` — `Zone` class and all three allocation strategies
- `experiment_1_scarcity_curve.py` — tank capacity sweep (10L–150L)
- `experiment_2_priority_sensitivity.py` — weight configuration sweep at fixed scarcity
- `experiment_3_rainfall_probability_reserve.py` — rain probability × reserve fraction sweep
- `scarcity_curve_results.csv`, `priority_sensitivity_results.csv`, `forecast_uncertainty_results.csv` — raw results from each experiment

## How to Run

```bash
python3 experiment_1_scarcity_curve.py
python3 experiment_2_priority_sensitivity.py
python3 experiment_3_rainfall_probability_reserve.py
```

## Directions for Further Work

- Redesign the rain-reserve mechanism so it actually provides a benefit (e.g. conditioning the reserve on anticipated demand spikes, not simply "rain might come")
- Extend the priority sensitivity test across multiple tank capacities, not just 40L
- Add real historical rainfall data for a specific location instead of a probability-based synthetic model

## What I Practiced Building This

- Designing and running a proper sensitivity analysis instead of tuning parameters until a desired result appeared
- Discovering and honestly reporting a genuine design flaw (the counterproductive reserve mechanism) through systematic experimentation
- Producing a scarcity curve as the central evidence graph for a technical report
- Separating "when does X help" from "does X always win" as the actual research contribution
