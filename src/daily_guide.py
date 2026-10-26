"""
🧭 Wayfarer — daily_guide.py  (PHASE 1 — the daily guide ⭐)  ✅

THE WISHLIST FEATURE: turns a finished itinerary into a time-boxed +
budget-boxed day schedule:

    Day 1 — Sohra:
      07:30  🍽 breakfast — cap ₹200 — try: Tungrymbai
      09:30  🎫 main sight: Cherrapunji — entry ₹0 — ~2h — max 2h15
      13:30  🍽 lunch — cap ₹300 — try: Tungrymbai
      15:00  🚶 en-route sights
      19:00  🍽 dinner — cap ₹300
      📦 DAY BOX: ~₹530/pp · ~4h of sights

Rule from the wishlist: every sight gets a MAX stay time (entry time +
25% buffer) — "spend 1 hour there, max 1h15, otherwise the next itinerary
item gets skipped". Overshoot and your plan slips — that's the rule.

Also ships: phobia filters (rule-based) + trip/day essentials checklist.
"""

import math
import sys

import pandas as pd

try:
    from src.food_recommender import FoodRecommender, load_side
except ImportError:  # running directly: python src\daily_guide.py
    from food_recommender import FoodRecommender, load_side

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- #
#  1. PHOBIA FILTER — rule-based tags from category/name text        #
# ---------------------------------------------------------------- #
PHOBIA_KEYWORDS = {
    "heights": ["canyon", "peak", "ropeway", "sky", "observatory", "climb", "viewpoint", "gion"],
    "dark":    ["cave", "dungeon", "tunnel", "mine"],
    "water":   ["waterfall", "river", "boating", "diving", "beach", "lake", "oyster", "falls", "onsen"],
    "crowds":  ["bazar", "bazaar", "market", "shopping", "nightlife", "crossing", "bazar"],
}


def has_phobia(row, phobias) -> bool:
    """True if a place should be SKIPPED given the user's phobia filters."""
    if not phobias:
        return False
    blob = f"{row.get('name', '')} {row.get('category', '')}".lower()
    for phobia in phobias:
        for kw in PHOBIA_KEYWORDS.get(phobia.lower(), []):
            if kw in blob:
                return True
    return False


# ---------------------------------------------------------------- #
#  2. DAY SCHEDULE BUILDER                                           #
# ---------------------------------------------------------------- #
def build_daily_guide(places, route_df, stay_plan, money,
                      foods=None, overrides=None, diet=None, phobias=None) -> list:
    """
    Build one boxed schedule per day.
      foods:     dish tips dataset (food_*.csv) — optional
      overrides: {day: {'breakfast': ₹}} — user edits a meal cap
      diet:      preferred diet for the food tips (Veg/Vegan/...)
      phobias:   ['heights', 'dark', ...] — flagged sights get skipped
    """
    overrides = overrides or {}
    rec = None
    if foods is not None and not foods.empty:
        rec = FoodRecommender().fit(foods)   # dish tips from the food dataset

    def cityof(name):
        row = places[places["name"].astype(str) == str(name)]
        return str(row.iloc[0]["city"]) if len(row) else str(name)

    def meal(town, kind, cap):
        """A meal box with an optional dish suggestion near the stay town."""
        dish = ""
        if rec is not None:
            hits = rec.recommend(town, diet=diet, interests=["food"], top_n=5)
            pick = hits[hits["best_meal"].astype(str).str.contains(kind, case=False, na=False)]
            if pick.empty:
                pick = hits[hits["best_meal"].astype(str).str.contains("snack", na=False)]
            if not pick.empty:
                dish = f"{pick.iloc[0]['dish']} @ {pick.iloc[0]['restaurant']}"
        return {"time": {"breakfast": "07:30", "lunch": "13:30",
                         "dinner": "19:00", "snack": "16:30"}[kind],
                "kind": "meal", "label": f"{kind} — cap ₹{cap}", "cost_pp": 0,
                "max_time": "", "stay_h": 0.0, "try": dish}

    def max_stay(avg_h):
        """MAX stay = visit time + 25% buffer. Returns (label, hours)."""
        m = avg_h + 0.25
        h, frac = int(m), m - int(m)
        label = f"max {h}h{int(round(frac * 60)):02d}" if frac else f"max {h}h"
        return label, float(m)

    days_out = []
    # expand the stay plan: every segment carries a place + its day count
    day_n = 1

    for si, seg in enumerate(stay_plan):
        seg_days = max(int(seg["days"]), 1)
        place = seg["place"]
        info_rows = places[places["name"].astype(str) == str(place)]
        info = info_rows.iloc[0] if len(info_rows) else None
        if info is not None and has_phobia(info, phobias):
            print(f"⚠️  Phobia filter: skipping {place} ({'/'.join(phobias)})")
            day_n += seg_days
            continue

        # ---- arrival day (also visits en-route sights) -------------- #
        town = (seg.get("stay_town") or cityof(place)) if info is not None else str(place)
        items = []
        drive = float(seg.get("drive_km", 0.0) or 0.0)
        if drive > 0:
            items.append({"time": "06:30", "kind": "drive",
                          "label": f"drive ~{drive:,.0f} km", "cost_pp": 0,
                          "max_time": "", "stay_h": 0.0, "try": ""})
        avg = float(info["avg_time_hours"]) if info is not None else 1.0
        for en in seg.get("en_route", []):
            lab, hrs = max_stay(0.75)
            items.append({"time": "10:30", "kind": "sight", "label": str(en),
                          "cost_pp": 0, "max_time": lab, "stay_h": hrs, "try": ""})
        mlab, mhrs = max_stay(avg)
        items.append({"time": "09:30", "kind": "sight", "label": str(place),
                      "cost_pp": 0, "max_time": mlab, "stay_h": mhrs,
                      "try": ""})
        caps = dict(money["per_meal"])
        if overrides and str(day_n) in overrides:
            caps.update({k: v for k, v in overrides[str(day_n)].items()})
        items.append(meal(town, "breakfast", caps["breakfast"]))
        items.append(meal(town, "lunch", caps["lunch"]))
        items.append(meal(town, "dinner", caps["dinner"]))
        items.append({"time": "21:00", "kind": "checkin",
                      "label": f"back at stay: {town}", "cost_pp": 0,
                      "max_time": "", "stay_h": 0.0, "try": ""})
        days_out.append({"day": day_n, "town": town, "items": items,
                         "budget_pp": 0, "hours": 0.0})
        day_n += 1
        for extra in range(seg_days - 1):    # extra days at the same overnight stay
            items = [
                {"time": "08:00", "kind": "sight",
                 "label": f"explore more of {place}", "cost_pp": 0,
                 "max_time": "", "try": ""},
                meal(town, "lunch", caps["lunch"]),
                meal(town, "snack", caps.get("snack", 200)),
                meal(town, "dinner", caps["dinner"]),
                {"time": "21:00", "kind": "checkin",
                 "label": f"back at stay: {town}", "cost_pp": 0,
                 "max_time": "", "try": ""},
            ]
            days_out.append({"day": day_n, "town": town, "items": items,
                             "budget_pp": 0, "hours": 0.0})
            day_n += 1

    # tally each day's money + time boxes (numeric field — never parse strings)
    for d in days_out:
        d["budget_pp"] = sum(int(i["cost_pp"]) for i in d["items"])
        d["hours"] = round(sum(float(i.get("stay_h", 0.0)) for i in d["items"]), 1)
    return days_out


# ---------------------------------------------------------------- #
#  3. ESSENTIALS CHECKLIST — trip level + day level                  #
# ---------------------------------------------------------------- #
DOMESTIC = ["Aadhaar", "driving licence", "trip cash + UPI", "power bank",
            "basic meds", "offline maps", "emergency: 112"]
INTERNATIONAL = ["passport (6-month validity)", "visa / e-visa", "travel insurance",
                 "forex card + cash", "passport photos", "flight tickets",
                 "eSIM or roaming plan", "offline translator", "embassy + local 112/911"]


def essentials_list(is_international: bool = False, trip_days: int = 1,
                    best_season: str | None = None) -> dict:
    """
    Trip-level documents + day-level packing hints.
    best_season like 'Oct-Nov' or 'Jul-Oct' gets static climate hints —
    live weather upgrades later with a free OpenWeather key.
    """
    docs = INTERNATIONAL if is_international else DOMESTIC
    season = (best_season or "").lower()
    hints = []
    if any(m in season for m in ("dec", "jan", "feb")):
        hints.append("❄️ layers + light jacket")
    if any(m in season for m in ("mar", "apr", "oct", "nov")):
        hints.append("☀️ sunscreen + sunglasses")
    if any(m in season for m in ("jun", "jul", "aug", "sep")):
        hints.append("☔ umbrella / raincoat")
    if not hints:
        hints.append("🌡️ light clothes + refill bottle")
    per_day = [f"day pack: {', '.join(hints)}",
               "💧 water + 🍫 snack", "🔋 charged power bank"]
    return {"documents": docs, "per_day": per_day,
            "trip": [f"trip length: {trip_days} days", "📱 wayfarer link + offline copy"]}


def print_essentials(ess: dict) -> None:
    print("\n🎒 ESSENTIALS")
    print("   documents:", " · ".join(ess["documents"]))
    for e in ess["per_day"]:
        print("   ", e)


# ---------------------------------------------------------------- #
#  Pretty printing of the guide                                      #
# ---------------------------------------------------------------- #
def print_guide(days_out) -> None:
    for d in days_out:
        print(f"\n📅 Day {d['day']} — {d['town']}")
        for i in d["items"]:
            bits = [i["label"]]
            if i.get("max_time"):
                bits.append(f"⏱ {i['max_time']} — beyond this the next itinerary item gets skipped")
            if i.get("try"):
                bits.append(f"try: {i['try']}")
            print(f"   {i['time']}  " + "   ".join(bits))


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    import pandas as pd
    try:
        from src.data_loader import clean_places, find_data_file, load_places
        from src.itinerary import TripPlanner
    except ImportError:
        from data_loader import clean_places, find_data_file, load_places
        from itinerary import TripPlanner

    df_m = clean_places(load_places(find_data_file("meghalaya")))
    planner = TripPlanner(df_m)
    route_df, total, stay = planner.plan_explicit(
        "Berhampur", "Berhampur",
        ["Umiam Lake", "Shillong (Police Bazar & Ward's Lake)", "Laitlum Canyon",
         "Cherrapunji (Sohra) Waterfalls & Caves", "Dawki (Umngot River Boating)",
         "Mawlynnong Village & Sky View", "Krem Chympe Cave"], days=5)
    money = {"per_meal": {"breakfast": 200, "lunch": 300, "dinner": 300}}
    foods = load_side("food", "india")           # dish tips from the food dataset
    days_out = build_daily_guide(planner.places, route_df, stay, money,
                                 foods=foods, overrides={"1": {"breakfast": 600}},
                                 diet="Veg", phobias=None)
    print_guide(days_out)
    assert len(days_out) == 5, f"guide must have exactly {5} days, got {len(days_out)}"
    o1 = [i for i in days_out[0]["items"] if "breakfast" in i["label"]][0]
    assert "600" in o1["label"], "user override not applied!"

    print("\n=== phobia filter skips caves on a dark-fearing trip ===")
    days_p = build_daily_guide(planner.places, route_df, stay, money, phobias=["dark"])
    assert len(days_p) < len(days_out), "phobia filter should skip cave days"

    print("\n=== essentials checklist ===")
    ess = essentials_list(is_international=False, trip_days=5, best_season="Oct-Nov")
    print_essentials(ess)
    assert any("sunscreen" in h for h in ess["per_day"])

    print("\n🎉 ALL GUIDE TESTS PASSED")
