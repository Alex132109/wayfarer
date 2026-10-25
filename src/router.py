"""
🧭 Wayfarer — router.py  (WEEK 3 — route optimization 🗺️)  ✅

PROBLEM: given a START, an END and a list of places to visit — in what order
should we visit them to travel the least total km? (The famous "Traveling
Salesman Problem" — NP-hard, so we use smart heuristics.)

TWO MODES:
    • One-way trip (start ≠ end):
        1. GREEDY DETOUR RULE — always visit the remaining place that keeps
           us closest to the final destination:
               cost(place) = km(current → place) + km(place → destination)
        2. 2-OPT — repeatedly "uncross" the route while endpoints stay fixed.

    • Round trip (start == end):
        1. CHEAPEST INSERTION — build a loop: insert each place at the
           position that adds the fewest extra km.
        2. 2-OPT for loops — same uncrossing trick, origin stays fixed.

Distances are computed ON DEMAND with haversine (see data_loader.py) —
never stored pairwise (N² explosion!).
"""

try:
    from src.data_loader import haversine_km
except ImportError:  # running directly: python src\router.py
    from data_loader import haversine_km

import pandas as pd


class RouteOptimizer:
    """Orders a set of places between a fixed origin and destination."""

    def __init__(self, places: pd.DataFrame):
        self.places = places.reset_index(drop=True)
        self.names = self.places["name"].astype(str).tolist()
        self._lat = self.places["lat"].to_numpy(dtype=float)
        self._lon = self.places["lon"].to_numpy(dtype=float)

    # ------------------------------------------------------------ #
    #  Helpers                                                     #
    # ------------------------------------------------------------ #
    def _km(self, i: int, j: int) -> float:
        """Straight-line km between place index i and j (computed on demand)."""
        return haversine_km(self._lat[i], self._lon[i], self._lat[j], self._lon[j])

    def find_place(self, query: str) -> int:
        """Find a place by exact or partial name (case-insensitive)."""
        q = query.strip().lower()
        for i, name in enumerate(self.names):
            if name.lower() == q:
                return i
        for i, name in enumerate(self.names):
            if q in name.lower():
                return i
        examples = ", ".join(self.names[:5])
        raise ValueError(f"❌ Place '{query}' not found. Try one of: {examples} ...")

    # ------------------------------------------------------------ #
    #  One-way: greedy detour rule                                 #
    # ------------------------------------------------------------ #
    def greedy_route(self, origin: int, dest: int, candidates: list[int] | None = None) -> list[int]:
        pool = list(candidates) if candidates is not None else [
            i for i in range(len(self.names)) if i not in (origin, dest)
        ]
        pool = [i for i in pool if i not in (origin, dest)]

        route, current = [origin], origin
        while pool:
            best = min(pool, key=lambda j: self._km(current, j) + self._km(j, dest))
            route.append(best)
            pool.remove(best)
            current = best
        route.append(dest)
        return route

    # ------------------------------------------------------------ #
    #  Round trip: cheapest insertion                              #
    # ------------------------------------------------------------ #
    def circular_route(self, origin: int, candidates: list[int]) -> list[int]:
        """Build a loop from origin: insert each place where it adds least km."""
        route = [origin]
        for p in candidates:
            best_cost, best_pos = float("inf"), 0
            for k in range(len(route)):
                nxt = route[(k + 1) % len(route)]          # loop closes back to origin
                cost = self._km(route[k], p) + self._km(p, nxt) - self._km(route[k], nxt)
                if cost < best_cost:
                    best_cost, best_pos = cost, k
            route.insert(best_pos + 1, p)
        return route

    # ------------------------------------------------------------ #
    #  2-opt improvement (both modes)                              #
    # ------------------------------------------------------------ #
    def two_opt(self, route: list[int], circular: bool = False, max_passes: int = 50) -> list[int]:
        route = list(route)
        n = len(route)
        for _ in range(max_passes):
            improved = False
            if circular:
                # loop legs: consecutive pairs + closing leg (last → origin)
                for i in range(1, n - 1):
                    for j in range(i + 1, n):
                        a, b, c, e = route[i - 1], route[i], route[j], route[(j + 1) % n]
                        if self._km(a, c) + self._km(b, e) + 1e-9 < self._km(a, b) + self._km(c, e):
                            route[i:j + 1] = route[i:j + 1][::-1]
                            improved = True
            else:
                for i in range(1, n - 2):
                    for j in range(i + 1, n - 1):
                        a, b, c, d = route[i - 1], route[i], route[j], route[j + 1]
                        if self._km(a, c) + self._km(b, d) + 1e-9 < self._km(a, b) + self._km(c, d):
                            route[i:j + 1] = route[i:j + 1][::-1]
                            improved = True
            if not improved:
                break
        return route

    # ------------------------------------------------------------ #
    #  Public API                                                  #
    # ------------------------------------------------------------ #
    def build_route(self, origin_name: str, dest_name: str, candidate_names: list[str]):
        """
        Full pipeline: find places → greedy/insertion → 2-opt → summary.
        If origin == destination, a ROUND TRIP (loop) is planned automatically.
        Returns (summary_df, total_km).
        """
        origin = self.find_place(origin_name)
        dest = self.find_place(dest_name)
        cand_idx = []
        for name in candidate_names:
            i = self.find_place(name)
            if i not in cand_idx and i not in (origin, dest):
                cand_idx.append(i)

        round_trip = origin == dest
        if round_trip:
            route = self.circular_route(origin, cand_idx)
            route = self.two_opt(route, circular=True)
        else:
            route = self.greedy_route(origin, dest, cand_idx)
            route = self.two_opt(route)
        return self.summarize(route, round_trip=round_trip)

    def summarize(self, route: list[int], round_trip: bool = False):
        """Route as a DataFrame with km to the next stop + total km."""
        legs = [self._km(route[k], route[k + 1]) for k in range(len(route) - 1)]
        if round_trip and len(route) > 1:
            legs.append(self._km(route[-1], route[0]))       # closing leg of the loop

        rows = []
        for k, idx in enumerate(route):
            p = self.places.iloc[idx]
            rows.append({
                "stop": k + 1,
                "name": self.names[idx],
                "city": p.get("city", ""),
                "rating": p.get("rating", ""),
                "entry_fee_inr": p.get("entry_fee_inr", ""),
                "km_to_next": round(legs[k], 1) if k < len(legs) else 0.0,
            })
        if round_trip:
            rows.append({
                "stop": len(rows) + 1,
                "name": f"↩️ Back to {self.names[route[0]]}",
                "city": self.places.iloc[route[0]].get("city", ""),
                "rating": "", "entry_fee_inr": "", "km_to_next": 0.0,
            })
        return pd.DataFrame(rows), float(sum(legs))


# ---------------------------------------------------------------- #
#  Test drive                                                      #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        from src.data_loader import clean_places, find_data_file, load_places
    except ImportError:
        from data_loader import clean_places, find_data_file, load_places

    df = clean_places(load_places(find_data_file("india")))
    router = RouteOptimizer(df)

    # One-way: Delhi → Agra (mini Golden Triangle, Jaipur side-trip included)
    route_df, total = router.build_route(
        origin_name="India Gate",
        dest_name="Taj Mahal",
        candidate_names=["Red Fort", "Qutub Minar", "Amber Fort", "Agra Fort", "Hawa Mahal"],
    )
    print(route_df.to_string(index=False))
    print(f"\n🛣️  Total one-way route: {total:.0f} km")

    # Round trip: Jaipur loop (start = end)
    route_df, total = router.build_route(
        origin_name="Amber Fort",
        dest_name="Amber Fort",
        candidate_names=["Hawa Mahal", "Jantar Mantar", "Ranthambore National Park"],
    )
    print("\n" + route_df.to_string(index=False))
    print(f"\n🛣️  Total round trip: {total:.0f} km")
