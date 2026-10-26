"""
🧭 Wayfarer — food_recommender.py  (PHASE 1 — food & stays 🍜🏨)  ✅

TWO RECOMMENDERS IN ONE FILE — both reuse the same ML trick we learned
in Task 1 (TF-IDF + cosine similarity), which is exactly how a beginner
should think: one good idea, applied everywhere.

    FoodRecommender   — "you're in Osaka? try THIS dish at THAT place"
                        with diet filters (veg / vegan / eggetarian / ...)
    HotelRecommender  — "this stay fits your budget — spend a little more
                        and this rated-up pick is worth it"

Data comes from data/sample/food_*.csv and hotels_*.csv (community Kaggle
data can replace them later — same columns, automatic).
"""

import sys

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from src.data_loader import RAW_DIR, SAMPLE_DIR
except ImportError:  # running directly: python src\food_recommender.py
    from data_loader import RAW_DIR, SAMPLE_DIR

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SIDE_DIRS = [SAMPLE_DIR, RAW_DIR]


# ---------------------------------------------------------------- #
#  Helpers — find side datasets for a main trip dataset              #
# ---------------------------------------------------------------- #
def load_side(kind: str, dataset: str) -> pd.DataFrame | None:
    """
    kind="food" | "hotels"; dataset="india" | "japan".
    Looks for files named like food_india_sample.csv in sample/ then raw/.
    Returns None when nothing found (features just stay quiet).
    """
    for d in SIDE_DIRS:
        for p in sorted(d.glob(f"{kind}_*.csv")):
            if dataset.lower() in p.name.lower():
                return pd.read_csv(p)
    return None


# ---------------------------------------------------------------- #
#  1. FOOD RECOMMENDER — TF-IDF dish matching (second ML model!)      #
# ---------------------------------------------------------------- #
class FoodRecommender:
    """Content-based dish recommender with hard diet filters."""

    def __init__(self) -> None:
        self.foods = None
        self.vectorizer = None
        self.matrix = None

    def fit(self, foods: pd.DataFrame) -> "FoodRecommender":
        self.foods = foods.reset_index(drop=True)
        # Same pattern as places: mix structured tags + free text.
        text = (self.foods["dish"].astype(str) + " " +
                self.foods["special"].fillna("").astype(str) + " " +
                self.foods["best_meal"].fillna("").astype(str) + " " +
                self.foods["diet"].fillna("").astype(str).str.replace(";", " "))
        self.vectorizer = TfidfVectorizer(lowercase=True)
        self.matrix = self.vectorizer.fit_transform(text)
        return self

    def recommend(self, town: str, diet: str | None = None,
                  interests: list[str] | None = None, top_n: int = 5) -> pd.DataFrame:
        """
        Best dishes NEAR an overnight town, optionally diet-filtered.

        Diet rule (hard filter, not a score):
            Vegan        → dish must be tagged Vegan
            Veg          → dish tagged Veg OR Vegan
            Eggetarian   → Veg OR Vegan OR Eggetarian (egg is OK)
            NonVeg       → anything goes
        """
        if self.foods.empty:
            return self.foods

        df = self.foods.copy()

        # 1. stay-town filter (case-insensitive, partial match)
        mask = df["near_town"].astype(str).str.lower().str.contains(town.lower(), na=False)
        df = df[mask]
        if df.empty:
            return df

        # 2. HARD diet filter — a non-veg dish never shows for a vegan trip
        if diet:
            d = diet.lower()
            if d == "vegan":
                ok = df["diet"].astype(str).str.contains("Vegan", case=False)
            elif d == "veg":
                ok = df["diet"].astype(str).str.contains("Vegan|Veg", case=False)
            elif d == "eggetarian":
                ok = df["diet"].astype(str).str.contains("Vegan|Veg|Eggetarian", case=False)
            else:  # nonveg — no restriction
                ok = pd.Series(True, index=df.index)
            df = df[ok]
            if df.empty:
                return df

        # 3. ML score: cosine similarity between interest words and dish text
        interests = interests or ["street", "food"]
        vec = self.vectorizer.transform([" ".join(interests)])
        scores = cosine_similarity(vec, self.matrix[df.index]).flatten()

        # small quality bonus so great dishes surface at near-ties
        bonus = 0.01 * pd.to_numeric(df["rating"], errors="coerce").fillna(4.0).to_numpy()
        df = df.assign(match_score=np.round(scores + bonus, 3)).sort_values(
            "match_score", ascending=False)
        return df.head(top_n).reset_index(drop=True)


# ---------------------------------------------------------------- #
#  2. HOTEL RECOMMENDER — budget-fit + "a little more" upsell         #
# ---------------------------------------------------------------- #
class HotelRecommender:
    """Recommends stays that fit the nightly budget — plus one upgrade."""

    def __init__(self) -> None:
        self.hotels = None

    def fit(self, hotels: pd.DataFrame) -> "HotelRecommender":
        self.hotels = hotels.reset_index(drop=True)
        return self

    def recommend(self, town: str, budget_pp_night: float,
                  travellers: int = 2, top_n: int = 3) -> pd.DataFrame:
        """
        Trip per-person stay budget (pp) covers HALF the room (2/room):
        so a room fits if price_per_night ≤ budget × 2.
        Returns: best affordable picks + one 'a little more' upgrade.
        """
        if self.hotels is None or self.hotels.empty:
            return self.hotels if self.hotels is not None else pd.DataFrame()

        room_budget = budget_pp_night * PER_ROOM_SHARERS
        df = self.hotels[self.hotels["town"].astype(str).str.lower()
                         .str.contains(town.lower(), na=False)].copy()
        if df.empty:
            return df

        df["price_per_night_inr"] = pd.to_numeric(df["price_per_night_inr"], errors="coerce")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

        # affordable picks, best rating first
        under = df[df["price_per_night_inr"] <= room_budget] \
            .sort_values(["rating", "price_per_night_inr"], ascending=[False, True])

        # ONE honest upsell: ≤1.3× room budget but a real rating jump
        over = df[(df["price_per_night_inr"] > room_budget)
                  & (df["price_per_night_inr"] <= room_budget * 1.3)
                  & (df["rating"] > (under["rating"].max() if not under.empty else 0))]

        picks = pd.concat([under.head(top_n - 1), over.head(1)])
        return picks.sort_values("price_per_night_inr").reset_index(drop=True)


PER_ROOM_SHARERS = 2  # same assumption as trip_money


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    print("=== Food: Osaka street food ===")
    f = FoodRecommender().fit(load_side("food", "japan"))
    print(f.recommend("Osaka", interests=["street", "food"])[
        ["dish", "restaurant", "diet", "price_inr"]].to_string(index=False))
    out = f.recommend("Osaka")
    assert not out.empty and out.iloc[0]["near_town"] == "Osaka"

    print("\n=== Food: VEGAN trip near Tokyo — hot dogs filtered out ===")
    v = f.recommend("Tokyo", diet="Vegan", interests=["food"])
    print(v[["dish", "diet", "price_inr"]].to_string(index=False))
    assert not v.empty and (v["diet"].str.contains("Vegan")).all()

    print("\n=== Food: India — vegan dishes near Shillong/Sohra ===")
    fi = FoodRecommender().fit(load_side("food", "india"))
    ind = fi.recommend("Shillong", diet="Veg", interests=["food"])
    print(ind[["dish", "diet", "price_inr"]].to_string(index=False))
    assert not ind.empty

    print("\n=== Hotels: budget-fit + one upsell ===")
    h = HotelRecommender().fit(load_side("hotels", "japan"))
    picks = h.recommend("Tokyo", budget_pp_night=3100, travellers=2)
    print(picks[["name", "style", "price_per_night_inr", "rating"]].to_string(index=False))
    # pp budget 3100 → room budget 6200: Mustard Hotel should fit
    assert "Mustard Hotel Shibuya" in picks["name"].tolist()

    print("\n🎉 ALL FOOD & HOTEL TESTS PASSED")
