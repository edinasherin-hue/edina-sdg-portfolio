"""
AquaGrow — Experiment 1: Scarcity Curve
==========================================

Question: How does demand satisfaction change as tank capacity increases,
for each strategy? This produces the central "scarcity curve" graph for
the final report.

Tests tank capacities from 10L to 150L in fine steps, running 40
independent 30-day scenarios at each capacity for all three strategies.
"""

import random
import statistics
import csv
from typing import List

from allocation_algorithm import (
    Zone, baseline_allocate, fair_share_allocate, smart_allocate, evaluate
)

SIMULATION_DAYS = 30
N_SCENARIOS = 40
TANK_CAPACITIES = [10, 20, 30, 40, 50, 60, 75, 100, 125, 150]

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


def generate_rainfall_litres(rng: random.Random):
    rains_today = rng.random() < 0.35
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


def run_one_scenario(strategy_name, allocate_fn, tank_capacity, seed):
    rng = random.Random(seed)
    tank = tank_capacity
    zones = fresh_zones()
    day_metrics = []

    for day in range(1, SIMULATION_DAYS + 1):
        harvestable = generate_rainfall_litres(rng)
        rain_signal_next_day = rng.random() < 0.35
        tank = min(tank_capacity, tank + harvestable)
        dry_out_zones(zones)

        if strategy_name == "AquaGrow":
            decisions = allocate_fn(zones, tank_litres=tank, rain_signal_expected=rain_signal_next_day)
        else:
            decisions = allocate_fn(zones, tank_litres=tank)

        used = sum(d.litres_allocated for d in decisions)
        tank -= used
        apply_irrigation(zones, decisions)
        day_metrics.append(evaluate(decisions, zones))

    avg_satisfaction = sum(m["demand_satisfaction_pct"] for m in day_metrics) / len(day_metrics)
    return avg_satisfaction


def run_scarcity_curve():
    strategies = [
        ("Baseline", lambda z, tank_litres: baseline_allocate(z, tank_litres=tank_litres)),
        ("Fair-share", lambda z, tank_litres: fair_share_allocate(z, tank_litres=tank_litres)),
        ("AquaGrow", lambda z, tank_litres, rain_signal_expected=False:
            smart_allocate(z, tank_litres=tank_litres, rain_signal_expected=rain_signal_expected)),
    ]

    results = []
    for tank_capacity in TANK_CAPACITIES:
        for strategy_name, fn in strategies:
            satisfactions = [
                run_one_scenario(strategy_name, fn, tank_capacity, seed=tank_capacity * 100 + i)
                for i in range(N_SCENARIOS)
            ]
            results.append({
                "tank_capacity": tank_capacity,
                "strategy": strategy_name,
                "mean_satisfaction_pct": round(statistics.mean(satisfactions), 1),
                "std_satisfaction_pct": round(statistics.stdev(satisfactions), 1),
            })

    return results


if __name__ == "__main__":
    print(f"Running scarcity curve: {len(TANK_CAPACITIES)} tank capacities x 3 strategies x {N_SCENARIOS} scenarios...")
    results = run_scarcity_curve()

    with open("scarcity_curve_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print("\nTank(L)  Strategy      Mean Satisfaction %  (±Std)")
    print("-" * 55)
    for r in results:
        print(f"{r['tank_capacity']:<8} {r['strategy']:<13} {r['mean_satisfaction_pct']:>6}  (±{r['std_satisfaction_pct']})")
