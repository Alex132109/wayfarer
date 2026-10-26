"""
🧭 Wayfarer — recommender.py  (WEEK 2 — your first ML model 🎉)  ✅ COMPLETE

GOAL: recommend places based on the user's interests (e.g. "beach", "food", "history").

THE IDEA (content-based filtering):
    1. Turn each place's text (categories + description) into a numeric "vector"
       using TF-IDF — words that are rare & meaningful (e.g. "heritage") get
       high weight; common words (e.g. "the") get near-zero weight.
    2. Turn the user's interests into a vector too (same vectorizer).
    3. Score every place by COSINE SIMILARITY — the angle between the place
       vector and the interest vector. Angle ~0° = pointing the same way = great match.
    4. Return the top-N matches.

Test with:
    python src/recommender.py                          → default: beach adventure (India)
    python src/recommender.py history food             → your own interests
    python src/recommender.py --dataset world mountain → worldwide data (UNESCO)
"""

import sys

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from src.data_loader import clean_places, find_data_file, load_places
except ImportError:  # running directly: python src\recommender.py
    from data_loader import clean_places, find_data_file, load_places


class PlaceRecommender:
    """Content-based recommender: matches user interests to place text."""

    def __init__(self) -> None:
        self.places = None      # DataFrame of places (set in `fit`)
        self.matrix = None      # TF-IDF matrix: 1 row per place, 1 column per word
        self.vectorizer = None  # the "translator" text → vectors

    # ------------------------------------------------------------ #
    #  STEP 1 — VECTORIZE (learn the vocabulary from our data)     #
    # ------------------------------------------------------------ #
    def fit(self, places) -> "PlaceRecommender":
        """
        Convert each place's text into a TF-IDF vector.

        We combine TWO text sources (when available):
          - `category`  : short, precise tags   ("Beach;Adventure;Food")
          - `description`: longer text with richer words (UNESCO world data)
        """
        self.places = places.reset_index(drop=True)

        # Include the NAME too — many places carry interest words in their
        # name itself (e.g. "Shrines and Temples of Nikko")!
        text = self.places["name"].astype(str) + "; " + self.places["category"].fillna("")
        if "description" in self.places.columns:
            text = text + " " + self.places["description"].fillna("")

        # TfidfVectorizer learns every unique word across all places,
        # then gives each place a vector of word-importance scores.
        self.vectorizer = TfidfVectorizer(lowercase=True)
        self.matrix = self.vectorizer.fit_transform(text)

        print(f"🧠 Recommender trained: {self.matrix.shape[0]} places, "
              f"{self.matrix.shape[1]} unique words learned")
        return self

    # ------------------------------------------------------------ #
    #  STEP 2 — SCORE (interests → similarity to every place)      #
    # ------------------------------------------------------------ #
    def _scores_for(self, interests: list[str]) -> np.ndarray:
        """
        Return one similarity score per place (same order as self.places).

        IMPORTANT: we call .transform (NOT fit_transform) here — the user's
        interests must use the SAME word-vocabulary learned in `fit`.
        """
        # Plural-aware both ways: user may type "temple" while the data says
        # "temples" (or the reverse). Expand each interest into singular +
        # plural so either spelling matches the learned vocabulary.
        forms = set()
        for w in interests:
            forms.add(w)
            forms.add(w + "s")
            if w.endswith("s"):
                forms.add(w[:-1])
        text = " ".join(sorted(forms))
        user_vec = self.vectorizer.transform([text])          # 1 × n_words vector
        scores = cosine_similarity(user_vec, self.matrix)     # 1 × n_places scores
        return scores.flatten()

    # ------------------------------------------------------------ #
    #  STEP 3 — RECOMMEND (pick the winners)                       #
    # ------------------------------------------------------------ #
    def recommend(self, interests: list[str], top_n: int = 10):
        """Return the top_n best-matching places, best first."""
        scores = self._scores_for(interests)

        # Sort best→worst, then keep only places that actually match:
        # a score of 0 means the place shares no meaningful word with
        # the user's interests — showing those would be confusing.
        order = np.argsort(scores)[::-1]
        top_idx = order[scores[order] > 0][:top_n]

        if len(top_idx) == 0:
            print("🤷 No places match those interests in this dataset.")
            return self.places.iloc[0:0]

        result = self.places.iloc[top_idx].copy()
        result["match_score"] = np.round(scores[top_idx], 3)
        return result.reset_index(drop=True)


# ---------------------------------------------------------------- #
#  Test drive                                                      #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    # Optional CLI:  python src/recommender.py beach adventure --dataset world
    args = sys.argv[1:]
    dataset = None
    if "--dataset" in args:
        i = args.index("--dataset")
        dataset = args[i + 1]
        args = args[:i] + args[i + 2:]

    interests = args or ["beach", "adventure"]

    # Phase 1 = India: use the India dataset unless the user asks for world
    dataset = dataset or "india"

    path = find_data_file(dataset)
    if path is None:
        print("❌ No dataset found.")
        raise SystemExit(1)

    print(f"📂 Dataset: {path.name}\n")
    rec = PlaceRecommender().fit(clean_places(load_places(path)))

    print(f"🔍 Interests: {interests}\n")
    result = rec.recommend(interests, top_n=8)
    if result.empty:
        raise SystemExit(0)
    cols = ["name", "city", "category", "match_score"]
    if "rating" in rec.places.columns and rec.places["rating"].notna().any():
        cols.insert(2, "rating")
    print(rec.recommend(interests, top_n=8)[cols].to_string(index=False))
