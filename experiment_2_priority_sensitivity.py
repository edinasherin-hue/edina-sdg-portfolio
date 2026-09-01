"""
AquaGrow — Experiment 2: Priority Sensitivity
================================================

Question: Does AquaGrow's priority-weighting actually help Zone A (the
highest-priority zone) when the weight gap between zones is made much
larger? V3 found no benefit with mild weights (0.8/1.0/1.5) — this tests
whether a stronger, deliberately more aggressive weight spread changes
that finding, run at a fixed moderate-scarcity tank capacity where
allocation strategy has room to matter (per the scarcity curve).

IMPORTANT: we are NOT tuning weights until AquaGrow "wins" — we're testing
a pre-defined range of weight configurations and reporting what happens
at each, including if none of them show a benefit.
"""

import random
import statistics
import csv
from typing import List
from dataclasses import replace

from allocation_algorithm import (
    Zone, fair_share_allocate, smart_allocate, evaluate
)

SIMULATION_DAYS = 30
N_SCENARIOS = 40
TEST_TANK_CAPACITY = 40  # moderate scarcity — steep part of the scarcity curve

CATCHMENT_AREA_M2 = 12.0
RUNOFF_COEFFICIENT = 0.80

# Pre-defined weight configurations (Zone A, Zone B, Zone C) — decided BEFORE
# running the experiment, not tuned afterward to force a particular result.
WEIGHT_CONFIGS = {
    "P1 (0.8/1.0/1.5)":            (0.8, 1.0, 1.5),
    "P2 (0.5/1.0/2.0)":            (0.5, 1.0, 2.0),
    "P3 (0.5/1.0/3.0)":            (0.5, 1.0, 3.0),
    "P4 (0.2/1.0/4.0)":            (0.2, 1.0, 4.0),
}


def make_zones(weight_c, weight_b, weight_a) -> List[Zone]:
    return [
        Zone(name="Zone A", crop="Tomatoes", soil_moisture_pct=45, target_moisture_pct=60,
             priority_weight=weight_a, max_capacity_litres=60),
        Zone(name="Zone B", crop="Herbs", soil_moisture_pct=50, target_moisture_pct=55,
             priority_weight=weight_b, max_capacity_litres=40),
        Zone(name="Zone C", crop="Succulents", soil_moisture_pct=52, target_moisture_pct=50,
             priority_weight=weight_c, max_capacity_litres=20),
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


def run_one_scenario(zones_factory, is_aquagrow, seed):
    rng = random.Random(seed)
    tank = TEST_TANK_CAPACITY
    zones = zones_factory()

    per_zone_required = {z.name: 0.0 for z in zones}
    per_zone_allocated = {z.name: 0.0 for z in zones}
    day_metrics = []

    for day in range(1, SIMULATION_DAYS + 1):
        harvestable = generate_rainfall_litres(rng)
        rain_signal_next_day = rng.random() < 0.35
        tank = min(TEST_TANK_CAPACITY, tank + harvestable)
        dry_out_zones(zones)

        if is_aquagrow:
            decisions = smart_allocate(zones, tank_litres=tank, rain_signal_expected=rain_signal_next_day)
        else:
            decisions = fair_share_allocate(zones, tank_litres=tank)

        used = sum(d.litres_allocated for d in decisions)
        tank -= used
        apply_irrigation(zones, decisions)

        for d in decisions:
            per_zone_required[d.zone] += d.required_litres
            per_zone_allocated[d.zone] += d.litres_allocated

        day_metrics.append(evaluate(decisions, zones))

    avg_satisfaction = sum(m["demand_satisfaction_pct"] for m in day_metrics) / len(day_metrics)
    avg_fairness = sum(m["fairness_min_zone_satisfaction_pct"] for m in day_metrics) / len(day_metrics)
    zone_a_sat = min(100.0, per_zone_allocated["Zone A"] / per_zone_required["Zone A"] * 100) \
        if per_zone_required["Zone A"] > 0.01 else 100.0

    return avg_satisfaction, avg_fairness, zone_a_sat


def run_priority_sensitivity():
    results = []

    # Fair-share baseline (weight-independent, run once for comparison)
    fs_satisfactions, fs_fairness, fs_zone_a = [], [], []
    for i in range(N_SCENARIOS):
        s, f, za = run_one_scenario(lambda: make_zones(0.8, 1.0, 1.5), is_aquagrow=False, seed=2000 + i)
        fs_satisfactions.append(s)
        fs_fairness.append(f)
        fs_zone_a.append(za)
    results.append({
        "config": "Fair-share (no priority)",
        "zone_C_weight": "—", "zone_B_weight": "—", "zone_A_weight": "—",
        "mean_satisfaction_pct": round(statistics.mean(fs_satisfactions), 1),
        "mean_fairness_pct": round(statistics.mean(fs_fairness), 1),
        "mean_zone_A_satisfaction_pct": round(statistics.mean(fs_zone_a), 1),
    })

    # AquaGrow across each weight configuration
    for config_name, (wc, wb, wa) in WEIGHT_CONFIGS.items():
        satisfactions, fairnesses, zone_as = [], [], []
        for i in range(N_SCENARIOS):
            s, f, za = run_one_scenario(lambda: make_zones(wc, wb, wa), is_aquagrow=True, seed=3000 + i)
            satisfactions.append(s)
            fairnesses.append(f)
            zone_as.append(za)
        results.append({
            "config": f"AquaGrow {config_name}",
            "zone_C_weight": wc, "zone_B_weight": wb, "zone_A_weight": wa,
            "mean_satisfaction_pct": round(statistics.mean(satisfactions), 1),
            "mean_fairness_pct": round(statistics.mean(fairnesses), 1),
            "mean_zone_A_satisfaction_pct": round(statistics.mean(zone_as), 1),
        })

    return results


if __name__ == "__main__":
    print(f"Running priority sensitivity at {TEST_TANK_CAPACITY}L tank, {N_SCENARIOS} scenarios per config...")
    results = run_priority_sensitivity()

    with open("priority_sensitivity_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'Config':<30} {'Weights (C/B/A)':<18} {'Satisfaction%':>14} {'Fairness%':>11} {'Zone A Sat%':>13}")
    print("-" * 90)
    for r in results:
        weights = f"{r['zone_C_weight']}/{r['zone_B_weight']}/{r['zone_A_weight']}"
        print(f"{r['config']:<30} {weights:<18} {r['mean_satisfaction_pct']:>14} "
              f"{r['mean_fairness_pct']:>11} {r['mean_zone_A_satisfaction_pct']:>13}")
