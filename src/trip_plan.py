"""
🧭 Wayfarer — trip_plan.py  (PHASE 1 — the editable trip 🧩)  ✅

THE WISHLIST FEATURE (F1): "edit everything after planning — change a meal
budget, drop a shrine, switch diet → whole budget & itinerary recompute".

HOW: ONE object is the source of truth. Edit anything on it, and it
RECOMPUTES the route, km, day split, budget, daily guide and essentials
from scratch — no stale numbers, no manual math:

    plan = TripPlan(planner, origin="Berhampur", destination="Berhampur",
                    stops=[...], days=5, travellers=5, style="comfort",
                    mode="car", foods=foods)
    plan.edit("style", "premium")            # every cost line rescales
    plan.edit("skip_places", ["Dawki (...)"])  # removed from the route
    plan.show()

    # and yes — "don't want to eat veg today" is a one-line edit:
    plan.edit("diet", "NonVeg")

Planner mode: pass `stops` to route exactly those places, or pass
`interests` to let the recommender pick. Edit-everything recompute works
the same in both.
"""

import sys

try:
    from src.trip_money import estimate_budget, print_budget
    from src.daily_guide import (build_daily_guide, essentials_list,
                                 print_essentials, print_guide)
except ImportError:  # running directly: python src\trip_plan.py
    from trip_money import estimate_budget, print_budget
    from daily_guide import (build_daily_guide, essentials_list,
                             print_essentials, print_guide)

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class TripPlan:
    """Holds ALL trip inputs; edit anything → recompute() → a fresh plan."""

    DEFAULTS = {
        "origin": None, "destination": None,
        "stops": None, "interests": None, "n_places": 6,
        "days": 1, "travellers": 1, "style": "comfort", "mode": "car",
        "foods": None, "diet": None,
        "meal_caps": None,          # {day: {'breakfast': ₹}} user edits
        "skip_places": None,        # names to remove from the route
        "is_international": False,  # aware of domestic vs foreign trips
        "month": None,              # travel month → in-season signal in hybrid scoring
    }

    def __init__(self, planner, **inputs):
        self.planner = planner
        self.inputs = dict(self.DEFAULTS)
        unknown = [k for k in inputs if k not in self.DEFAULTS]
        if unknown:
            raise ValueError(
                f"Unknown trip input(s) {unknown} — try one of {list(self.DEFAULTS)}")
        self.inputs.update({k: v for k, v in inputs.items() if v is not None})
        self.plan = None                 # built by recompute()

    # ------------------------------------------------------------ #
    #  EDITS — "user can edit things"                               #
    # ------------------------------------------------------------ #
    def edit(self, key, value):
        """Edit any input (style, days, travellers, diet, ...) and recompute."""
        if key not in self.inputs:
            raise ValueError(
                f"Unknown input '{key}' — try one of {list(self.inputs)}")
        if key == "skip_places":
            # skipping REMOVES from the current stop list (not replaces)
            removed = set(value or [])
            self.inputs["skip_places"] = list(removed)
            self.inputs["stops"] = [
                s for s in (self.inputs.get("stops") or []) if s not in removed]
        else:
            self.inputs[key] = value
        return self.recompute()

    # ------------------------------------------------------------ #
    #  RECOMPUTE — the whole pipeline, every time                   #
    # ------------------------------------------------------------ #
    def recompute(self) -> "TripPlan":
        planner, inp = self.planner, self.inputs
        o, d = inp["origin"], inp["destination"]

        if not o or not d:
            raise ValueError("Trip needs an origin and a destination.")

        # 1. ROUTE — explicit stops? or recommender picks?
        if inp["stops"]:
            route_df, total_km, stay_plan = planner.plan_explicit(
                o, d, inp["stops"], days=inp["days"])
        else:
            route_df, total_km, stay_plan = planner.plan(
                o, d, inp["interests"], n_places=inp["n_places"],
                days=inp["days"], month=inp["month"])

        # 2. MONEY — style tier scales every daily line
        money = estimate_budget(days=inp["days"], travellers=inp["travellers"],
                                total_km=total_km, mode=inp["mode"],
                                style=inp["style"])

        # 3. DAILY GUIDE — time-boxed + budget-boxed, user-caps applied
        guide = build_daily_guide(planner.places, route_df, stay_plan, money,
                                  overrides=inp["meal_caps"],
                                  diet=inp["diet"], phobias=inp["skip_places"]) \
            if stay_plan else None

        # 4. ESSENTIALS — documents + climate packing hints
        best_season = ""
        src = planner.places[planner.places["name"].astype(str) == str(o)]
        if not src.empty and "best_time" in src.columns:
            best_season = str(src.iloc[0]["best_time"])
        ess = essentials_list(is_international=bool(inp["is_international"]),
                              trip_days=inp["days"], best_season=best_season)

        self.plan = {"route_df": route_df, "total_km": total_km,
                     "stay_plan": stay_plan, "money": money,
                     "guide": guide, "essentials": ess}
        return self

    # ------------------------------------------------------------ #
    #  Pretty printing                                              #
    # ------------------------------------------------------------ #
    def print_summary(self) -> None:
        if not self.plan:
            self.recompute()
        inp = self.inputs
        route_df, total_km = self.plan["route_df"], self.plan["total_km"]

        print("\n" + "=" * 66)
        print(f"🧳 TRIP: {inp['origin']} → {inp['destination']} · "
              f"{inp['days']} days · {inp['travellers']} travellers")
        print("=" * 66)
        print(route_df.to_string(index=False))
        print(f"\n🛣️  Total distance: {total_km:,.0f} km")

        print_budget(self.plan["money"], inp["origin"], inp["destination"])

        if self.plan["guide"]:
            print_guide(self.plan["guide"])

        print_essentials(self.plan["essentials"])
        print("\n✏️  Edit anything: plan.edit('style', 'premium'), "
              "plan.edit('skip_places', ['...']), plan.edit('diet', 'Vegan')…")

    def summary(self) -> dict:
        if not self.plan:
            self.recompute()
        return dict(self.plan)


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        from src.data_loader import clean_places, find_data_file, load_places
        from src.food_recommender import load_side
        from src.itinerary import TripPlanner
    except ImportError:  # running directly: python src\trip_plan.py
        from data_loader import clean_places, find_data_file, load_places
        from food_recommender import load_side
        from itinerary import TripPlanner

    print("=== Plan A: THE flagship — Meghalaya loop, 5 travellers, 5 days ===")
    df_m = clean_places(load_places(find_data_file("meghalaya")))
    df_i = clean_places(load_places(find_data_file("india")))
    foods = load_side("food", "india")

    planner_m = TripPlanner(df_m)
    plan = TripPlan(planner_m,
                    origin="Berhampur", destination="Berhampur",
                    stops=["Umiam Lake", "Shillong (Police Bazar & Ward's Lake)",
                           "Cherrapunji (Sohra) Waterfalls & Caves",
                           "Dawki (Umngot River Boating)", "Krem Chympe Cave"],
                    days=5, travellers=5, style="comfort", mode="car")
    money_before = plan.summary()["money"]["trip_group"]
    plan.edit("style", "premium")
    money_after = plan.summary()["money"]["trip_group"]
    assert money_after > money_before, "premium must cost more than comfort!"
    print(f"✔ edit-everything: group ₹{money_before:,} → premium ₹{money_after:,}")

    print("\n=== Plan B: drop a place and re-plan ===")
    before = len(plan.summary()["route_df"])
    plan.edit("skip_places", ["Krem Chympe Cave"])
    after = len(plan.summary()["route_df"])
    assert after < before, "skipping should shrink the route!"
    print(f"✔ dropped Krem Chympe: stops {before} → {after}")

    print("\n=== Plan C: interests mode + one-line day change ===")
    planner_i = TripPlanner(df_i)
    plan_i = TripPlan(planner_i, origin="India Gate", destination="Taj Mahal",
                      interests=["fort", "history"], n_places=4,
                      days=2, travellers=2, mode="car", foods=foods)
    plan_i.edit("days", 3)          # "then the site will change its whole budget"
    assert sum(s["days"] for s in plan_i.summary()["stay_plan"]) == 3
    plan_i.show = plan_i.print_summary()

    print("\n🎉 ALL TRIP PLAN TESTS PASSED")
