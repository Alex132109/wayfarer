"""
🧭 Wayfarer — trip_money.py  (PHASE 1 — the money engine 💰)  ✅

WHAT THIS DOES:
    1. TRIP STYLES  — 6 tiers from budget to super-luxury; each has a cost
       multiplier that scales every daily spend (food, cabs, misc, stays).
    2. ESTIMATOR    — a total trip budget BEFORE you go: per-person + group.
    3. ACTUAL CALC  — a real per-day plan: meal caps, transport, stays, PLUS a
       10% emergency fund ("some extra emergency funds" from the wishlist).

Everything is INR (₹) and pure computation — no APIs needed. The numbers are
honest planning approximations, not exact quotes (real prices vary).
"""

import math
import sys

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- #
#  1. TRIP STYLES — how premium is this trip?                        #
# ---------------------------------------------------------------- #
STYLES = {
    "budget":       {"label": "🪙 Budget",       "multiplier": 0.60},
    "economy":      {"label": "💵 Economy",      "multiplier": 0.85},
    "comfort":      {"label": "🛏️ Comfort",      "multiplier": 1.00},
    "premium":      {"label": "✨ Premium",      "multiplier": 1.60},
    "luxury":       {"label": "💎 Luxury",       "multiplier": 2.60},
    "super-luxury": {"label": "👑 Super-luxury", "multiplier": 4.50},
}

# Per-person-per-day baseline at "comfort" style (INR) — the local-expert numbers
BASE_SPEND = {
    "breakfast": 200, "lunch": 300, "dinner": 300,     # 800 food/day (wishlist example)
    "local_transport": 400,                            # autos/cabs/metro for sightseeing
    "misc": 300,                                       # snacks, souvenirs, tea breaks
}
STAY_PER_ROOM_NIGHT = 2500                              # per room/night at comfort
PER_ROOM = 2                                            # travellers sharing a room
EMERGENCY_RATIO = 0.10                                  # 10% buffer fund per person

# ---------------------------------------------------------------- #
#  2. TRANSPORT MODES — planning rates (₹/km)                        #
# ---------------------------------------------------------------- #
# Group-pay rates for road modes (fuel/tolls for the whole vehicle),
# per-person rates for public modes (tickets per traveller).
TRANSPORT_MODES = {
    "car":    {"per_km_group": 8.0,  "note": "own car — fuel + tolls"},
    "cab":    {"per_km_group": 16.0, "note": "hired cab with driver"},
    "bike":   {"per_km_group": 3.0,  "note": "bike — fuel"},
    "bus":    {"per_km_pp": 1.1,     "note": "public bus"},
    "train":  {"per_km_pp": 1.2,     "note": "train — sleeper/2S class"},
    "flight": {"per_km_pp": 5.5,     "note": "economy flight — short-haul approx"},
    "mixed":  None,                                    # handled by rule below
}
# "mixed" rule: trains as the backbone; for long loops (>2000 km) the biggest
# 30% of km are usually flown (e.g. Japan golden route hops).
MIXED_RAIL_SHARE = 0.7


# ---------------------------------------------------------------- #
#  3. MEAL CAPS — "₹600 breakfast / ₹300 pagoda" style boxes         #
# ---------------------------------------------------------------- #
def per_meal_budget(style: str = "comfort") -> dict:
    """How much ONE person can spend on each meal, scaled by style tier."""
    mult = STYLES[style]["multiplier"]
    return {k: round(v * mult) for k, v in BASE_SPEND.items()
            if k in ("breakfast", "lunch", "dinner")}


# ---------------------------------------------------------------- #
#  4. THE BUDGET ENGINE                                              #
# ---------------------------------------------------------------- #
def estimate_budget(days, travellers, total_km, mode: str = "mixed",
                    style: str = "comfort", stay_nights: int | None = None) -> dict:
    """
    Full budget: per-meal caps, per-day lines, intercity travel, stays,
    per-person trip total, and the emergency fund. Returns a plain dict.
    """
    days = max(int(days), 1)
    travellers = max(int(travellers), 1)
    total_km = max(float(total_km), 0.0)
    style = style.lower()
    if style not in STYLES:
        raise ValueError(f"Unknown style '{style}' — try one of {list(STYLES)}")

    mult = STYLES[style]["multiplier"]

    # per-person per-day lines (style-scaled)
    daily_pp = {k: round(v * mult) for k, v in BASE_SPEND.items()}

    # intercity travel cost — HOW the group moves between towns
    if mode == "mixed":
        # long loops usually fly their biggest hops
        rail_share = MIXED_RAIL_SHARE if total_km > 2000 else 1.0
        rail_km, air_km = total_km * rail_share, total_km * (1 - rail_share)
        pp = rail_km * TRANSPORT_MODES["train"]["per_km_pp"] \
            + air_km * TRANSPORT_MODES["flight"]["per_km_pp"]
        note = f"train {rail_share:.0%} + flight {1 - rail_share:.0%} (planning approx)"
    else:
        info = TRANSPORT_MODES[mode]
        if "per_km_group" in info:
            pp = info["per_km_group"] * total_km / travellers
        else:
            pp = info["per_km_pp"] * total_km
        note = info["note"]

    intercity_pp = round(pp)
    intercity_group = intercity_pp * travellers

    # stays — rooms = ceil(travellers / travellers-per-room)
    rooms = math.ceil(travellers / PER_ROOM)
    nights = max(int(stay_nights if stay_nights is not None else days - 1), 1)
    stay_group = round(STAY_PER_ROOM_NIGHT * mult * rooms * nights)
    stay_pp = round(stay_group / travellers)

    # per-person trip total
    food_pp = sum(daily_pp[k] for k in ("breakfast", "lunch", "dinner")) * days
    daily_lines_pp = (daily_pp["local_transport"] + daily_pp["misc"]) * days
    trip_pp = food_pp + daily_lines_pp + stay_pp + intercity_pp
    trip_group = trip_pp * travellers

    # emergency fund — per person AND group, on the trip total
    emergency_pp = round(trip_pp * EMERGENCY_RATIO)
    emergency_group = emergency_pp * travellers

    return {
        "label": STYLES[style]["label"], "multiplier": mult,
        "per_meal": per_meal_budget(style),          # meal caps for the guide
        "per_day_pp": daily_pp,
        "intercity": {"mode": mode, "note": note, "total_km": round(total_km),
                      "group": intercity_group, "pp": intercity_pp},
        "stays": {"rooms": rooms, "nights": nights,
                  "group": stay_group, "pp": stay_pp},
        "trip_pp": round(trip_pp), "trip_group": round(trip_group),
        "emergency_pp": emergency_pp, "emergency_group": emergency_group,
    }


# ---------------------------------------------------------------- #
#  5. Pretty printing                                                #
# ---------------------------------------------------------------- #
def print_budget(money: dict, origin: str, destination: str) -> None:
    """Human-readable budget report (₹, grouped per person)."""
    print("\n" + "=" * 66)
    print(f"💰 TRIP BUDGET — {money['label']}  ({origin} → {destination})")
    print("=" * 66)
    meals = money["per_meal"]
    print(f"🍽️  Meal caps per person:  breakfast ₹{meals['breakfast']:,} · "
          f"lunch ₹{meals['lunch']:,} · dinner ₹{meals['dinner']:,}")
    day = money["per_day_pp"]
    print(f"🛺  Daily per person:      local transport ₹{day['local_transport']:,} · "
          f"misc ₹{day['misc']:,}")
    ic = money["intercity"]
    print(f"🛫  Intercity ({ic['mode']}) over {ic['total_km']:,} km — "
          f"group ₹{ic['group']:,} · pp ₹{ic['pp']:,}")
    st = money["stays"]
    print(f"🏨  Stays: {st['rooms']} room(s) × {st['nights']} night(s) — "
          f"group ₹{st['group']:,} · pp ₹{st['pp']:,}")
    print("-" * 66)
    print(f"🧳  Trip per person:       ₹{money['trip_pp']:,}")
    print(f"🆘  Emergency fund pp:     ₹{money['emergency_pp']:,}")
    print(f"👥  Group total (+fund):   ₹{money['trip_group'] + money['emergency_group']:,}")
    print("=" * 66)


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    print("=== Scenario A: Meghalaya, 5 days, 2 travellers, comfort ===")
    a = estimate_budget(days=5, travellers=2, total_km=2104, mode="car", style="comfort")
    print_budget(a, "Berhampur", "Berhampur")
    assert a["trip_pp"] > 0 and a["emergency_pp"] > 0
    assert a["emergency_pp"] == round(a["trip_pp"] * 0.10)

    print("\n=== Scenario B: Japan golden route, 12 days, 4 travellers, luxury ===")
    b = estimate_budget(days=12, travellers=4, total_km=1642, mode="mixed", style="luxury")
    print_budget(b, "Tokyo", "Tokyo")
    assert b["stays"]["rooms"] == 2, "rooms should be ceil(4/2)=2"

    print("\n=== Scenario C: style tiers scale every line ===")
    budget_pp = estimate_budget(5, 2, 2104, "car", "budget")["trip_pp"]
    lux_pp = estimate_budget(5, 2, 2104, "car", "luxury")["trip_pp"]
    assert lux_pp > budget_pp, "luxury must cost more than budget!"
    print(f"✔ budget ₹{budget_pp:,} < luxury ₹{lux_pp:,}")

    print("\n🎉 ALL MONEY TESTS PASSED")
