"""
AquaGrow — Experiment 3: Rainfall Probability & Reserve Strategy
====================================================================

Question: Given a rain signal that's correct with probability p (the
environment's true daily rain probability), what reserve fraction
performs best?

IMPORTANT — honesty about the model: this does NOT simulate a real
weather forecasting system. It models an environment where rain occurs
on ~p of days, and the system's rain-signal is calibrated to that same
p (i.e., a "perfectly calibrated" simulated signal for testing purposes
only). This tests how RESERVE STRATEGY should respond to different
levels of rain frequency/uncertainty in the environment, not real
forecast skill.

Tests rain probability tiers (20%, 50%, 80%) x reserve fractions
(0%, 10%, 20%, 30%, 40%, 50%) at a fixed moderate-scarcity tank capacity,
to find which reserve setting performs best under each rain regime.
"""

import random
import statistics
import csv
from typing import List

from allocation_algorithm import Zone, smart_allocate, evaluate

SIMULATION_DAYS = 30
N_SCENARIOS = 40
TEST_TANK_CAPACITY = 40  # moderate scarcity, matches Experiment 2

RAIN_PROBABILITIES = [0.20, 0.50, 0.80]
RESERVE_FRACTIONS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50]

CATCHMENT_AREA_M2 = 12.0
RUNOFF_COEFFICIENT = 0.80


def fresh_zones() -> List[Zone]:
    return [
        Zone(name="Zone A", crop="Tomatoes", soil_moisture_pct=45, target_moisture_pct=60,
             priority_weight=1.5, max_capacity_litres=60),
        Zone(name="Zone B", crop="Herbs", soil_moisture_pct=50, target_moisture_pct=55,
             priority_weight=1.0, max_capacity_litres=40),
        Zone(name="Zone C", crop="Succulents", soil_moisture_pct=52, target_moisture_pct=50,
             priority_weight=0.8, max_capacity_litres=20),
    ]


def generate_rainfall_litres(rng: random.Random, rain_probability: float):
    rains_today = rng.random() < rain_probability
    if not rains_today:
        return 0.0
    rainfall_depth_mm = rng.uniform(5, 40)
    return round(rainfall_depth_mm * CATCHMENT_AREA_M2 * RUNOFF_COEFFICIENT, 1)


def dry_out_zones(zones, evaporation_rate=4.0):
    for z in zones:
        z.soil_moisture_pct = max(5.0, z.soil_moisture_pct - evaporation_rate)


def apply_irrigation(zones, decisions, moisture_gain_per_litre=0.8):
    decision_map = {d.zone: d.litres_allocated for d in decisions}
    for z in zones:
        litres = decision_map.get(z.name, 0.0)
        z.soil_moisture_pct = min(100.0, z.soil_moisture_pct + litres * moisture_gain_per_litre)


def run_one_scenario(rain_probability, reserve_fraction, seed):
    rng = random.Random(seed)
    tank = TEST_TANK_CAPACITY
    zones = fresh_zones()
    day_metrics = []

    for day in range(1, SIMULATION_DAYS + 1):
        harvestable = generate_rainfall_litres(rng, rain_probability)
        # Rain signal calibrated to the same probability (see module docstring)
        rain_signal_next_day = rng.random() < rain_probability
        tank = min(TEST_TANK_CAPACITY, tank + harvestable)
        dry_out_zones(zones)

        decisions = smart_allocate(
            zones, tank_litres=tank,
            rain_signal_expected=rain_signal_next_day,
            rain_reserve_fraction=reserve_fraction,
        )
        used = sum(d.litres_allocated for d in decisions)
        tank -= used
        apply_irrigation(zones, decisions)
        day_metrics.append(evaluate(decisions, zones))

    avg_satisfaction = sum(m["demand_satisfaction_pct"] for m in day_metrics) / len(day_metrics)
    avg_unmet = sum(m["unmet_demand_litres"] for m in day_metrics)
    return avg_satisfaction, avg_unmet


def run_forecast_uncertainty_experiment():
    results = []
    for rain_prob in RAIN_PROBABILITIES:
        for reserve in RESERVE_FRACTIONS:
            satisfactions, unmets = [], []
            for i in range(N_SCENARIOS):
                s, u = run_one_scenario(rain_prob, reserve, seed=int(rain_prob * 1000) + i)
                satisfactions.append(s)
                unmets.append(u)
            results.append({
                "rain_probability": rain_prob,
                "reserve_fraction": reserve,
                "mean_satisfaction_pct": round(statistics.mean(satisfactions), 1),
                "mean_unmet_demand_litres": round(statistics.mean(unmets), 1),
            })
    return results


def find_best_reserve_per_probability(results):
    best = {}
    for r in results:
        p = r["rain_probability"]
        if p not in best or r["mean_satisfaction_pct"] > best[p]["mean_satisfaction_pct"]:
            best[p] = r
    return best


if __name__ == "__main__":
    print(f"Running forecast uncertainty: {len(RAIN_PROBABILITIES)} rain probabilities x "
          f"{len(RESERVE_FRACTIONS)} reserve fractions x {N_SCENARIOS} scenarios...")
    results = run_forecast_uncertainty_experiment()

    with open("forecast_uncertainty_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'Rain Prob':<11} {'Reserve %':<11} {'Satisfaction %':>15} {'Unmet Demand (L)':>18}")
    print("-" * 60)
    for r in results:
        print(f"{r['rain_probability']:<11} {r['reserve_fraction']:<11} "
              f"{r['mean_satisfaction_pct']:>15} {r['mean_unmet_demand_litres']:>18}")

    best = find_best_reserve_per_probability(results)
    print("\nBest reserve fraction per rain probability:")
    for p, r in sorted(best.items()):
        print(f"  Rain probability {p}: best reserve = {r['reserve_fraction']} "
              f"(satisfaction {r['mean_satisfaction_pct']}%)")
