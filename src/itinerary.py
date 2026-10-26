"""
🧭 Wayfarer — itinerary.py  (WEEK 3 — the trip planner brain 🧳)  ✅

Everything connects here:

    user's interests ──▶ RECOMMENDER ──▶ candidate places
                                           │  (corridor filter: no huge detours)
    start point ──┐                        ▼
                  └───────▶ ROUTER ──▶ optimal order + km for every leg
    end point  ───┘                        │
                                           ▼
                              day-wise ITINERARY with stays

TWO WAYS TO PLAN:
    1. plan()          — "I like forts & history, take me Delhi → Agra"
    2. plan_explicit() — "I want EXACTLY these places: Shillong, Sohra, Dawki..."
                         Round trips supported (start = end) ✅

STAY ALLOCATION (when the dataset has a `suggested_days` column):
    Places carry a local-expert suggestion, e.g. Sohra = 2 days, Dawki = 1.
    Your total trip length is distributed across stops by weight
    (largest-remainder method → days always add up exactly).
    Example: 5 days → Shillong 1 · Sohra 2 · Dawki 1 · caves 1.

Test with:
    python src/itinerary.py
"""

import math
import sys

import pandas as pd

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from src.data_loader import clean_places, find_data_file, load_places, road_distance_matrix
    from src.recommender import PlaceRecommender
    from src.router import RouteOptimizer
except ImportError:  # running directly: python src\itinerary.py
    from data_loader import clean_places, find_data_file, load_places, road_distance_matrix
    from recommender import PlaceRecommender
    from router import RouteOptimizer

LONG_DRIVE_KM = 450  # legs longer than this get a "long drive" warning

# HYBRID RECOMMENDER WEIGHTS (feature engineering — the 15/10 upgrade):
#   score = w1·interest-match + w2·rating + w3·in-season + w4·proximity
HYBRID_WEIGHTS = {"interest": 0.55, "rating": 0.20, "season": 0.15, "proximity": 0.10}


class TripPlanner:
    """One-stop API: interests OR exact stops + start + end → day-wise itinerary."""

    def __init__(self, places):
        self.places = places.reset_index(drop=True)
        self.rec = PlaceRecommender().fit(self.places)
        self.router = RouteOptimizer(self.places)   # default: straight-line km
        self._suggested = self._load_suggested_days()

    def _fresh_router(self, node_names) -> tuple[RouteOptimizer, bool]:
        """
        Build a per-trip RouteOptimizer. When the network allows, it carries a
        REAL road-km matrix (OSRM) for exactly the trip's places; otherwise it
        quietly falls back to straight-line. Fresh instance = zero leaks.
        Returns (router, used_road_km).
        """
        nodes = self.places[self.places["name"].astype(str).isin(set(node_names))]
        road = road_distance_matrix(nodes) if len(nodes) >= 2 else None
        return RouteOptimizer(self.places, road_matrix=road), road is not None

    def _load_suggested_days(self) -> dict:
        """name → suggested days (curated column), else {} (chunk mode)."""
        if "suggested_days" in self.places.columns:
            s = pd.to_numeric(self.places["suggested_days"], errors="coerce").fillna(0)
            return dict(zip(self.places["name"].astype(str), s))
        return {}

    # ------------------------------------------------------------ #
    #  Mode 1 — interest-based planning                            #
    # ------------------------------------------------------------ #
    def plan(self, origin, destination, interests, n_places=5, days=0,
             max_extra_ratio=0.6, month=None):
        """
        Pick places by interests, keep only sensible ones, order them, split days.

        max_extra_ratio: a candidate is dropped if visiting it adds MORE than
            (ratio × direct km) — e.g. 0.6 = the place may add up to ~60% extra
            travel compared to going straight origin → destination.
        month:      optional travel month ("Oct") — powers the in-season signal.
        """
        # 1. Which places match the user's vibe? (recommender)
        pool = self.rec.recommend(interests, top_n=n_places + 4).copy()
        if pool.empty:
            raise ValueError("No matching places found for those interests.")

        # 2. Per-trip router — REAL road km (OSRM) when the network allows,
        #    otherwise straight-line. One fresh instance per trip = no leaks.
        nodes = {str(origin), str(destination)} | set(pool["name"].astype(str))
        router, road = self._fresh_router(list(nodes))
        o, d = router.find_place(origin), router.find_place(destination)
        direct_km = router._km(o, d)

        # 2b. CORRIDOR FILTER — a far-off candidate (e.g. Mumbai on a Delhi→Agra
        #     trip) forces a huge detour. Measure the extra km each one adds:
        #         extra = km(origin→place) + km(place→dest) − km(origin→dest)
        def detour_km(name: str) -> float:
            i = router.find_place(name)
            return router._km(o, i) + router._km(i, d) - direct_km

        pool["extra_km"] = pool["name"].map(detour_km)
        before = len(pool)
        pool = pool[pool["extra_km"] <= direct_km * max_extra_ratio]

        if len(pool) < 2:  # too strict? rescue with the 3 closest candidates
            fallback = self.rec.recommend(interests, top_n=3)
            fallback["extra_km"] = fallback["name"].map(detour_km)   # measure them too!
            fallback = fallback[fallback["extra_km"] <= direct_km * max_extra_ratio]
            if fallback.empty:
                # everything is far — better a longer trip than no trip at all:
                # keep the 2 candidates with the SMALLEST detours
                fallback = self.rec.recommend(interests, top_n=2)
                fallback["extra_km"] = fallback["name"].map(detour_km)
                fallback = fallback.sort_values("extra_km")
            pool = pd.concat([pool, fallback]).drop_duplicates(subset=["name"])
            pool = pool.sort_values("extra_km")

        dropped = max(before - len(pool), 0)   # fallback may ADD rows — never negative
        if dropped > 0:
            print(f"✂️  Dropped {dropped} place(s) far off the {origin} → {destination} corridor")

        # 2c. HYBRID SCORING — blend FOUR signals into one final score
        #     (feature engineering: this is how recommenders grow up)
        w = HYBRID_WEIGHTS
        rating = pd.to_numeric(pool["rating"], errors="coerce").fillna(4.0) / 5.0
        if month:
            season = pool["best_time"].fillna("").astype(str).str.contains(
                str(month), case=False).astype(float)
        else:
            season = pd.Series(0.5, index=pool.index)   # unknown month → neutral
        proximity = (1 - pool["extra_km"].clip(lower=0) / max(direct_km, 1)).clip(0, 1)
        pool["final_score"] = (w["interest"] * pool["match_score"]
                               + w["rating"] * rating
                               + w["season"] * season
                               + w["proximity"] * proximity)
        pool = pool.sort_values("final_score", ascending=False).head(n_places)
        print(f"🧠 Hybrid pick: interests {w['interest']:.0%} · rating {w['rating']:.0%}"
              f" · in-season {w['season']:.0%} · road-proximity {w['proximity']:.0%}")

        # 3. Order them (same road-aware router — greedy + 2-opt) and split days
        route_df, total_km = router.build_route(origin, destination, pool["name"].tolist())
        stay_plan = self._split_days(route_df, days, origin, destination) if days and days > 0 else None
        return route_df, total_km, stay_plan

    # ------------------------------------------------------------ #
    #  Mode 2 — explicit stops (user names the places)             #
    # ------------------------------------------------------------ #
    def plan_explicit(self, origin, destination, stops, days=0):
        """Route EXACTLY the stops the user listed (order optimized for them).
        Round trips work: origin == destination (e.g. Berhampur → Berhampur)."""
        nodes = {str(origin), str(destination)} | {str(s) for s in stops}
        router, road = self._fresh_router(list(nodes))
        route_df, total_km = router.build_route(origin, destination, list(stops))
        stay_plan = self._split_days(route_df, days, origin, destination) if days and days > 0 else None
        return route_df, total_km, stay_plan

    # ------------------------------------------------------------ #
    #  Day + stay allocation                                       #
    # ------------------------------------------------------------ #
    def _split_days(self, route_df, total_days, origin, destination):
        round_trip = str(route_df.iloc[-1]["name"]).startswith("↩️")

        names = route_df["name"].astype(str).tolist()
        if round_trip:
            names = names[1:]                      # drop the origin row (start ≠ destination)
        names = [n for n in names if not n.startswith("↩️")]

        if not names:
            return None

        if self._suggested:
            return self._weighted_days(route_df, names, total_days, round_trip)
        return self._chunk_days(route_df, names, total_days, round_trip)

    def _weighted_days(self, route_df, names, total_days, round_trip):
        """Distribute trip days across stops by their suggested_days weight.
        Largest-remainder method → days always add up EXACTLY to total_days."""
        stay = [n for n in names if self._suggested.get(n, 1) >= 1]
        if not stay:                                   # nothing curated → treat all as equal
            stay, weights = names, [1.0] * len(names)
        else:
            weights = [float(self._suggested[n]) for n in stay]

        total_w = sum(weights)
        raw = [w / total_w * total_days for w in weights]
        alloc = [int(math.floor(x)) for x in raw]
        leftover = total_days - sum(alloc)             # always ≥ 0 with floor()

        # hand out leftover days by largest fractional part (ties → bigger weight → route order)
        order = sorted(range(len(alloc)),
                       key=lambda k: (raw[k] - alloc[k], weights[k], -k), reverse=True)
        for k in order[:leftover]:
            alloc[k] += 1

        # arrival leg into each place = km_to_next of the PREVIOUS route row
        arrival, prev_km = {}, 0.0
        for _, row in route_df.iterrows():
            arrival[str(row["name"])] = prev_km
            prev_km = float(row["km_to_next"])

        segments, en_route = [], []
        alloc_map = dict(zip(stay, alloc))
        for n in names:
            if alloc_map.get(n, 0) > 0:
                segments.append({"place": n, "days": alloc_map[n],
                                 "en_route": en_route[:], "drive_km": arrival.get(n, 0.0)})
                en_route = []
            else:
                en_route.append(n)                 # visited on the way / no overnight
        if en_route and segments:
            segments[-1]["en_route"].extend(en_route)
        return segments

    def _chunk_days(self, route_df, names, total_days, round_trip):
        """No curation available → split the ordered stops evenly across days.
        Stay town = city of the LAST stop in each day's chunk."""
        if total_days <= 0 or not names:
            return None
        chunk = math.ceil(len(names) / total_days)
        cityof = dict(zip(route_df["name"].astype(str), route_df["city"]))
        kmof = dict(zip(route_df["name"].astype(str), route_df["km_to_next"]))

        segments, prev = [], None
        for d in range(total_days):
            stops = names[d * chunk: (d + 1) * chunk]
            if not stops:
                break
            last = stops[-1]
            arrival = kmof.get(prev, 0.0) if prev is not None else 0.0
            segments.append({"place": "  →  ".join(stops), "days": 1, "en_route": [],
                             "drive_km": arrival, "stay_town": cityof.get(last, "")})
            prev = last
        return segments


# ---------------------------------------------------------------- #
#  Pretty printing                                                 #
# ---------------------------------------------------------------- #
def print_trip(route_df, total_km, stay_plan=None):
    print("\n" + "=" * 66)
    print("🧳  YOUR WAYFARER ITINERARY")
    print("=" * 66)
    print(route_df.to_string(index=False))
    print(f"\n🛣️   Total distance: {total_km:.0f} km")

    if stay_plan:
        cityof = dict(zip(route_df["name"].astype(str), route_df["city"]))
        day = 1
        print("\n📅 Day-wise plan with stays:")
        long_drives = []
        for seg in stay_plan:
            label = f"Day {day}" if seg["days"] == 1 else f"Day {day}–{day + seg['days'] - 1}"
            day += seg["days"]
            place = seg["place"]
            town = seg.get("stay_town") or cityof.get(place, place)
            extra = f"   (en-route: {', '.join(seg['en_route'])})" if seg.get("en_route") else ""
            print(f"   {label}: {place}   🏨 stay: {town}{extra}")
            if seg.get("drive_km", 0) > LONG_DRIVE_KM:
                long_drives.append(f"drive to {place} ~{seg['drive_km']:.0f} km")
        # round trip? warn about the closing leg back to the start too
        if str(route_df.iloc[-1]["name"]).startswith("↩️"):
            ret = float(route_df.iloc[-2]["km_to_next"])
            if ret > LONG_DRIVE_KM:
                long_drives.append(f"return drive ~{ret:.0f} km")
        if long_drives:
            print(f"\n🚗  Long drives: {'; '.join(long_drives)} — "
                  f"add buffer day(s) if travelling by road!")
    print("=" * 66)


# ---------------------------------------------------------------- #
#  Demo trips                                                      #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    # 🇮🇳 Trip 1: history lover, Delhi → Agra (interest-based, 2 days)
    df = clean_places(load_places(find_data_file("india")))
    planner = TripPlanner(df)
    route_df, total_km, stay = planner.plan(
        origin="India Gate", destination="Taj Mahal",
        interests=["fort", "history"], n_places=4, days=2,
    )
    print_trip(route_df, total_km, stay)

    # 🎒 Trip 2: THE REAL SCENARIO — Meghalaya round trip from Berhampur, 5 days
    #    "start Berhampur, end Berhampur, visit Shillong, Cherrapunji, Dawki, Krem Chympe"
    df_m = clean_places(load_places(find_data_file("meghalaya")))
    planner_m = TripPlanner(df_m)
    route_df, total_km, stay = planner_m.plan_explicit(
        origin="Berhampur", destination="Berhampur",
        stops=["Umiam Lake", "Shillong (Police Bazar & Ward's Lake)", "Laitlum Canyon",
               "Cherrapunji (Sohra) Waterfalls & Caves", "Dawki (Umngot River Boating)",
               "Mawlynnong Village & Sky View", "Krem Chympe Cave"],
        days=5,
    )
    print_trip(route_df, total_km, stay)

    # 🎒 Trip 3: same Meghalaya loop with a relaxed 7-day budget
    route_df, total_km, stay = planner_m.plan_explicit(
        origin="Berhampur", destination="Berhampur",
        stops=["Umiam Lake", "Shillong (Police Bazar & Ward's Lake)", "Laitlum Canyon",
               "Cherrapunji (Sohra) Waterfalls & Caves", "Nongriat Double-Decker Root Bridge",
               "Dawki (Umngot River Boating)", "Mawlynnong Village & Sky View", "Krem Chympe Cave"],
        days=7,
    )
    print_trip(route_df, total_km, stay)

    # 🇯🇵 Trip 4: Japan golden route — 12-day round trip from Tokyo
    df_j = clean_places(load_places(find_data_file("japan")))
    planner_j = TripPlanner(df_j)
    route_df, total_km, stay = planner_j.plan_explicit(
        origin="Tokyo (Asakusa & Shibuya)", destination="Tokyo (Asakusa & Shibuya)",
        stops=["Nikko (Toshogu Shrine)", "Mt Fuji (Kawaguchiko)", "Hakone (Onsen & Ropeway)",
               "Kyoto (Fushimi Inari & Gion)", "Nara (Deer Park & Todai-ji)",
               "Osaka (Castle & Dotonbori)", "Himeji Castle", "Hiroshima (Peace Memorial)",
               "Miyajima (Itsukushima Shrine)", "Shirakawa-go Village", "Kanazawa (Kenroku-en)"],
        days=12,
    )
    print_trip(route_df, total_km, stay)
