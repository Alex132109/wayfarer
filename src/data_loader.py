"""
🧭 Wayfarer — data_loader.py
Loads + cleans the travel dataset(s), and gives us distance math for routing later.

Run it directly to see a quick summary of your data:
    python src/data_loader.py

(You'll learn: pandas, DataFrames, data cleaning — the foundation of every ML project.)
"""

import sys
from pathlib import Path

import pandas as pd

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Project root = the "wayfarer" folder (parent of src/)
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"      # your real Kaggle datasets go here
SAMPLE_DIR = ROOT / "data" / "sample"  # starter dataset (runs out of the box)


# ---------------------------------------------------------------- #
#  1. LOADING                                                      #
# ---------------------------------------------------------------- #
def find_data_file(dataset: str | None = None) -> Path | None:
    """
    Return a CSV path to load.
      dataset="india"  → a file with 'india' in its name (raw/ first, sample fallback)
      dataset="world"  → a file with 'world' in its name
      dataset=None     → first CSV in raw/ (real data wins), else sample
    """
    raw = sorted(RAW_DIR.glob("*.csv"))
    sample = sorted(SAMPLE_DIR.glob("*.csv"))

    if dataset:
        matches = [p for p in raw + sample if dataset.lower() in p.name.lower()]
        return matches[0] if matches else None

    return raw[0] if raw else (sample[0] if sample else None)


def load_places(path: Path | None = None) -> pd.DataFrame:
    """
    Load a places CSV into a DataFrame with standardized column names.

    We standardize to:  name, city, state, category, rating, lat, lon,
                        avg_time_hours, entry_fee_inr, best_time
    """
    if path is None:
        path = find_data_file()
    if path is None or not path.exists():
        raise FileNotFoundError(
            "No CSV found in data/raw/ or data/sample/. Download a dataset first!"
        )

    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Common alternate names → our standard names
    renames = {
        "place_name": "name",
        "attraction": "name",
        "latitude": "lat",
        "longitude": "lon",
        "type": "category",
        "types": "category",
        "tags": "category",
        "google_review_rating": "rating",
        "reviews": "rating",
        "entrance_fee": "entry_fee_inr",
    }
    df = df.rename(columns={k: v for k, v in renames.items() if k in df.columns})
    return df


# ---------------------------------------------------------------- #
#  2. CLEANING                                                     #
# ---------------------------------------------------------------- #
def clean_places(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the data — real-world data is ALWAYS messy. This makes it usable."""
    df = df.copy()

    # Strip whitespace from text columns
    for col in ["name", "city", "state", "category"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Remove exact duplicate places
    before = len(df)
    df = df.drop_duplicates(subset=["name", "city"]).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"🧹 Removed {dropped} duplicate place(s)")

    # Fix numbers (ratings can't exceed 5, coordinates can't be zero-text)
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df["rating"] = df["rating"].clip(0, 5)
        df["rating"] = df["rating"].fillna(df["rating"].median())

    if "entry_fee_inr" in df.columns:
        df["entry_fee_inr"] = pd.to_numeric(df["entry_fee_inr"], errors="coerce").fillna(0)

    if "avg_time_hours" in df.columns:
        df["avg_time_hours"] = pd.to_numeric(df["avg_time_hours"], errors="coerce").fillna(2.0)

    # Drop rows without coordinates (we need them for routing)
    if "lat" in df.columns and "lon" in df.columns:
        df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)

    return df


# ---------------------------------------------------------------- #
#  3. DISTANCE MATH (used by the router in Week 3)                 #
# ---------------------------------------------------------------- #
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points on Earth, in kilometers."""
    import numpy as np

    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    r = 6371.0  # Earth's radius in km

    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    )
    return float(2 * r * np.arcsin(np.sqrt(a)))


def distance_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise distance (km) between all places — the router's fuel. 🔥"""
    n = len(df)
    m = [[haversine_km(df.lat[i], df.lon[i], df.lat[j], df.lon[j]) for j in range(n)]
         for i in range(n)]
    return pd.DataFrame(m, index=df["name"], columns=df["name"])


# ---------------------------------------------------------------- #
#  Run this file directly → quick data exploration report          #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    # Optional: python src/data_loader.py --dataset india|world
    args = sys.argv[1:]
    dataset = args[args.index("--dataset") + 1] if "--dataset" in args else None

    path = find_data_file(dataset)
    if path is None:
        print("❌ No dataset found. Check data/raw/README.md for instructions.")
        raise SystemExit(1)

    print(f"📂 Loading: {path.relative_to(ROOT)}\n")
    df = clean_places(load_places(path))

    print(f"✅ {len(df)} places loaded")
    print(f"   Columns: {list(df.columns)}\n")

    if "city" in df.columns:
        print("🏙️  Places per city:")
        print(df["city"].value_counts().head(10).to_string(), "\n")

    if "category" in df.columns:
        print("🏷️  Most common categories (split on ';'):")
        cats = df["category"].str.split(";").explode().str.strip()
        print(cats.value_counts().head(10).to_string(), "\n")

    if "rating" in df.columns:
        print(f"⭐ Average rating: {df['rating'].mean():.2f} / 5")

    print("\n💡 Tip: try df.head(10) in a Jupyter notebook to see the raw rows.")
