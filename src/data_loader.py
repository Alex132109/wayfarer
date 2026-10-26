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
#  REAL ROAD KM (OSRM) — the 10× accuracy upgrade 🛣️                #
# ---------------------------------------------------------------- #
# Straight-line km UNDER-estimates by 20–30%. The free OSRM demo server
# gives TRUE road distances. Design decisions (learn these!):
#   • ONE request per trip: the /table endpoint returns the whole N×N
#     matrix at once — no request-per-pair spamming.
#   • DISK CACHE: every matrix is saved, so re-plans are instant and we
#     never re-ask the network for the same trip.
#   • GRACEFUL FALLBACK: any network problem → None → the router quietly
#     uses straight-line estimates. The app NEVER crashes on the network.
import hashlib
import json as _json
import ssl
import urllib.request

OSRM_URL = "https://router.project-osrm.org"
CACHE_DIR = ROOT / "data" / "cache"


def road_distance_matrix(df: pd.DataFrame, timeout: int = 20) -> pd.DataFrame | None:
    """
    Real road km between all places in `df` (one HTTP call).
    Returns a DataFrame of km (row → column), or None if offline/failed.
    """
    n = len(df)
    if n < 2:
        return None
    names = df["name"].astype(str).tolist()

    # 1. disk cache — keyed by the exact set of place names
    key = hashlib.md5("|".join(sorted(names)).encode()).hexdigest()
    cache_file = CACHE_DIR / f"osrm_{key}.json"
    if cache_file.exists():
        try:
            cached = _json.loads(cache_file.read_text())
            if set(cached["names"]) == set(names):
                m = cached["meters"]
                return pd.DataFrame([[v / 1000.0 for v in row] for row in m],
                                    index=names, columns=names)
        except Exception:
            pass  # corrupt cache → just refetch

    # 2. build the request (OSRM wants lon,lat order!)
    coords = ";".join(f"{float(r['lon']):.6f},{float(r['lat']):.6f}"
                      for _, r in df.iterrows())
    url = f"{OSRM_URL}/table/v1/driving/{coords}?annotations=distance"
    req = urllib.request.Request(url, headers={"User-Agent": "Wayfarer/1.0 (student project)"})

    # 3. verified SSL first — same proxy-friendly fallback as the UNESCO loader
    raw = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception as e:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read()
        except Exception as e2:
            print(f"⚠️  OSRM road data unavailable ({e2.__class__.__name__}) — "
                  f"using straight-line × 1.25 estimates instead")
            return None

    # 4. validate → km DataFrame → cache
    try:
        data = _json.loads(raw)
        m = data.get("distances")
        complete = m and len(m) == n and all(v is not None for row in m for v in row)
        if not complete:
            print("⚠️  OSRM returned incomplete road data — using straight-line fallback")
            return None
    except Exception:
        print("⚠️  Could not parse OSRM response — using straight-line fallback")
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(_json.dumps({"names": names, "meters": m}))
    print(f"🛣️  REAL road km loaded via OSRM for {n} places (cached for next time)")
    return pd.DataFrame([[v / 1000.0 for v in row] for row in m],
                        index=names, columns=names)


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
        # Core trip files start with "places_" — they WIN over side datasets
        # (food_*, hotels_*) that also mention the token in their name.
        places_matches = [p for p in matches if p.name.lower().startswith("places_")]
        return (places_matches or matches)[0] if matches else None

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

    # GUARANTEE the standard columns exist — everything downstream (recommender,
    # router, website) can then index them safely without KeyError crashes.
    # Real Kaggle exports love dropping whole columns; missing ≠ broken now.
    defaults = {
        "name": "", "city": "", "state": "", "category": "",
        "rating": float("nan"), "lat": float("nan"), "lon": float("nan"),
        "avg_time_hours": 2.0, "entry_fee_inr": 0, "best_time": "",
    }
    for col, fill in defaults.items():
        if col not in df.columns:
            df[col] = fill

    # Strip whitespace from text columns
    for col in ["name", "city", "state", "category"]:
        df[col] = df[col].astype(str).str.strip()

    # Remove exact duplicate places
    before = len(df)
    df = df.drop_duplicates(subset=["name", "city"]).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"🧹 Removed {dropped} duplicate place(s)")

    # Fix numbers (ratings can't exceed 5, coordinates can't be zero-text)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").clip(0, 5)
    df["rating"] = df["rating"].fillna(df["rating"].median())
    df["entry_fee_inr"] = pd.to_numeric(df["entry_fee_inr"], errors="coerce").fillna(0)
    df["avg_time_hours"] = pd.to_numeric(df["avg_time_hours"], errors="coerce").fillna(2.0)

    # Coordinates: force-convert to numbers and keep only SANE values.
    # (A stray lat="abc" or lon=9314 would poison EVERY distance in the trip!
    # Out-of-range values become NaN and the row is dropped — NOT clipped,
    # because clip(9314 → 180) would mint a fake point at the antimeridian.)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["lat"] = df["lat"].where(df["lat"].between(-90, 90))
    df["lon"] = df["lon"].where(df["lon"].between(-180, 180))
    df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)

    # Fail loudly if the dataset can't be routed at all.
    if df.empty:
        raise ValueError(
            "❌ No places with usable coordinates in this dataset — "
            "Wayfarer needs 'lat'/'lon' (or 'latitude'/'longitude') GPS columns."
        )

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
