"""
AquaGrow — Core Allocation Algorithm (V2 - Debugged)
=====================================================
Fixes applied:
- Fixed order bias in _iterative_allocate by taking round snapshots of remaining supply.
- Fixed evaluate() so demand satisfaction and unmet demand are grounded in useful water delivered.
- Added boundary safeguards for target_moisture_pct and zero supply.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Zone:
    name: str
    crop: str
    soil_moisture_pct: float      # current reading, e.g. 22.0
    target_moisture_pct: float    # ideal moisture level, e.g. 60.0
    priority_weight: float        # 1.0 = normal, >1.0 = higher-value crop
    max_capacity_litres: float    # max water this zone can physically absorb per cycle

    def deficit_pct(self) -> float:
        """How far below target this zone currently is, in percentage points."""
        return max(0.0, self.target_moisture_pct - self.soil_moisture_pct)

    def required_litres(self) -> float:
        """Physically grounded water requirement."""
        if self.target_moisture_pct <= 0:
            return 0.0
        deficit_fraction = self.deficit_pct() / self.target_moisture_pct
        return min(self.max_capacity_litres, self.max_capacity_litres * deficit_fraction)

    def needs_water(self) -> bool:
        return self.required_litres() > 0.01


@dataclass
class Decision:
    zone: str
    litres_allocated: float
    required_litres: float
    reason: str


# ---------------------------------------------------------------------------
# STRATEGY 1 — Fixed-threshold baseline
# ---------------------------------------------------------------------------

def baseline_allocate(
    zones: List[Zone],
    tank_litres: float,
    threshold_pct: float = 30.0,
    fixed_dose_litres: float = 30.0,
) -> List[Decision]:
    decisions = []
    remaining = max(0.0, tank_litres)

    for z in zones:
        req = z.required_litres()
        if z.soil_moisture_pct < threshold_pct and remaining > 0:
            dose = min(fixed_dose_litres, remaining, z.max_capacity_litres)
            decisions.append(Decision(
                zone=z.name, litres_allocated=round(dose, 1), required_litres=round(req, 1),
                reason=(f"Moisture {z.soil_moisture_pct:.0f}% is below the "
                        f"{threshold_pct:.0f}% threshold; fixed dose applied "
                        f"regardless of other zones' needs.")
            ))
            remaining -= dose
        else:
            decisions.append(Decision(
                zone=z.name, litres_allocated=0.0, required_litres=round(req, 1),
                reason=f"Moisture {z.soil_moisture_pct:.0f}% is at/above threshold."
            ))

    return decisions


# ---------------------------------------------------------------------------
# Shared iterative redistribution engine (Synchronous round-based)
# ---------------------------------------------------------------------------

def _iterative_allocate(
    zones: List[Zone],
    usable_supply: float,
    score_fn,
    rain_note: str = "",
) -> List[Decision]:
    """
    Allocates usable supply proportionally to score_fn(zone).
    Synchronously computes each zone's share per round and redistributes
    surplus from capped zones to active zones with remaining need.
    """
    allocated: Dict[str, float] = {z.name: 0.0 for z in zones}
    remaining_supply = max(0.0, usable_supply)

    active = [z for z in zones if z.needs_water()]
    max_rounds = len(zones) + 2

    for _ in range(max_rounds):
        if remaining_supply <= 0.01 or not active:
            break

        scores = {z.name: max(0.0, score_fn(z)) for z in active}
        total_score = sum(scores.values())
        if total_score <= 0:
            break

        # Snapshot remaining supply for synchronous round allocation
        round_supply = remaining_supply
        round_allocated = {}

        for z in active:
            remaining_need = z.required_litres() - allocated[z.name]
            share = scores[z.name] / total_score
            tentative = round_supply * share
            round_allocated[z.name] = min(tentative, remaining_need)

        round_total_given = sum(round_allocated.values())
        if round_total_given <= 0.001:
            break

        for z in active:
            allocated[z.name] += round_allocated[z.name]

        remaining_supply -= round_total_given
        active = [z for z in active if (z.required_litres() - allocated[z.name]) > 0.01]

    decisions = []
    for z in zones:
        req = z.required_litres()
        litres = round(allocated[z.name], 1)
        req_rounded = round(req, 1)

        if req <= 0.01:
            decisions.append(Decision(
                zone=z.name, litres_allocated=0.0, required_litres=req_rounded,
                reason=(f"No irrigation needed — moisture {z.soil_moisture_pct:.0f}% "
                        f"is at/above its {z.target_moisture_pct:.0f}% target.")
            ))
        else:
            pct_met = (litres / req * 100) if req > 0 else 0
            decisions.append(Decision(
                zone=z.name, litres_allocated=litres, required_litres=req_rounded,
                reason=(f"Requires {req:.1f}L to close its deficit; received {litres:.1f}L "
                        f"({pct_met:.0f}% of requirement met).{rain_note}")
            ))

    return decisions


# ---------------------------------------------------------------------------
# STRATEGY 2 — Fair-share
# ---------------------------------------------------------------------------

def fair_share_allocate(zones: List[Zone], tank_litres: float) -> List[Decision]:
    """Equal proportional split among all needy zones."""
    return _iterative_allocate(zones, usable_supply=tank_litres, score_fn=lambda z: 1.0)


# ---------------------------------------------------------------------------
# STRATEGY 3 — AquaGrow
# ---------------------------------------------------------------------------

def smart_allocate(
    zones: List[Zone],
    tank_litres: float,
    rain_signal_expected: bool = False,
    rain_reserve_fraction: float = 0.30,
) -> List[Decision]:
    """Priority-weighted proportional allocation with simulated rain signal."""
    usable_supply = max(0.0, tank_litres)
    rain_note = ""
    if rain_signal_expected:
        reserve = tank_litres * rain_reserve_fraction
        usable_supply = max(0.0, tank_litres - reserve)
        rain_note = f" Rain signal active this cycle: {reserve:.0f}L reserved rather than spent now."

    return _iterative_allocate(
        zones,
        usable_supply=usable_supply,
        score_fn=lambda z: z.deficit_pct() * z.priority_weight,
        rain_note=rain_note,
    )


# ---------------------------------------------------------------------------
# Evaluation metrics (Fully Grounded)
# ---------------------------------------------------------------------------

def evaluate(decisions: List[Decision], zones: List[Zone] = None) -> Dict:
    total_required = sum(d.required_litres for d in decisions)
    total_used = sum(d.litres_allocated for d in decisions)
    useful_used = sum(min(d.litres_allocated, d.required_litres) for d in decisions)

    # True unmet demand summing each zone's deficit
    unmet_demand = sum(max(0.0, d.required_litres - d.litres_allocated) for d in decisions)
    demand_satisfaction_pct = (useful_used / total_required * 100) if total_required > 0 else 100.0
    demand_satisfaction_pct = min(100.0, demand_satisfaction_pct)
    water_use_efficiency_pct = (useful_used / total_used * 100) if total_used > 0 else 0.0

    # Per-zone satisfaction ratios
    per_zone_satisfaction = []
    for d in decisions:
        if d.required_litres > 0.01:
            per_zone_satisfaction.append(min(1.0, d.litres_allocated / d.required_litres))

    fairness_min_satisfaction_pct = round(min(per_zone_satisfaction) * 100, 1) if per_zone_satisfaction else 100.0

    # Priority-weighted satisfaction
    priority_satisfaction_pct = None
    if zones:
        zone_map = {z.name: z for z in zones}
        weighted_num, weighted_den = 0.0, 0.0
        for d in decisions:
            if d.required_litres > 0.01:
                z = zone_map.get(d.zone)
                w = z.priority_weight if z else 1.0
                sat = min(1.0, d.litres_allocated / d.required_litres)
                weighted_num += sat * w
                weighted_den += w
        if weighted_den > 0:
            priority_satisfaction_pct = round(weighted_num / weighted_den * 100, 1)

    return {
        "total_water_required_litres": round(total_required, 1),
        "total_water_used_litres": round(total_used, 1),
        "unmet_demand_litres": round(unmet_demand, 1),
        "demand_satisfaction_pct": round(demand_satisfaction_pct, 1),
        "water_use_efficiency_pct": round(water_use_efficiency_pct, 1),
        "fairness_min_zone_satisfaction_pct": fairness_min_satisfaction_pct,
        "priority_weighted_satisfaction_pct": priority_satisfaction_pct,
        "zones_served": sum(1 for d in decisions if d.litres_allocated > 0),
    }


def per_zone_table(decisions: List[Decision]) -> List[Dict]:
    rows = []
    for d in decisions:
        pct = (d.litres_allocated / d.required_litres * 100) if d.required_litres > 0.01 else 100.0
        rows.append({
            "zone": d.zone,
            "required_litres": round(d.required_litres, 1),
            "allocated_litres": round(d.litres_allocated, 1),
            "pct_satisfied": round(pct, 1),
        })
    return rows
