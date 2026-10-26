"""
🧭 Wayfarer — build_india_dataset.py  (REAL-data upgrade 📦)  ✅

Turns the Kaggle dataset "Top Indian Places to Visit" (325 real places,
33 states, real Google ratings + entry fees) into our standard places
schema — including REAL GPS coordinates geocoded from the free
OpenStreetMap **Nominatim** API.

WHY GEOCODING? The dataset has name/city/rating/fees but NO lat/lon, and
routing is impossible without coordinates. So we look each place up ONCE,
cache it on disk forever (data/cache/geocode.json), and never pay that
cost again. This is the standard enrichment-pipeline pattern:

    download → clean → enrich (geocode) → save

Run:  .venv\\Scripts\\python src\\build_india_dataset.py
Credentials: ~/.kaggle/kaggle.json  ({"username": "...", "key": "..."})
"""

import base64
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = ROOT / "data" / "cache"
GEOCACHE = CACHE_DIR / "geocode.json"          # geocode results never expire

KAGGLE_SLUG = "dhrubangtalukdar/top-indian-places-to-visit-indian-tourism"
OUT_FILE = RAW_DIR / "places_india.csv"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- #
#  Helpers                                                          #
# ---------------------------------------------------------------- #
def _fetch(req: urllib.request.Request, timeout: int = 25) -> bytes:
    """Verified SSL first, proxy-friendly unverified fallback — the same
    pattern as the OSRM/UNESCO loaders so the app never dies on SSL."""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()


def download_dataset(slug: str) -> pd.DataFrame:
    """Kaggle API v1: Basic auth with kaggle.json → zip → biggest CSV."""
    cfg = Path.home() / ".kaggle" / "kaggle.json"
    if not cfg.exists():
        raise FileNotFoundError(
            "Missing ~/.kaggle/kaggle.json — download it from "
            "kaggle.com → Settings → API → Create New Token")
    d = json.loads(cfg.read_text())
    token = base64.b64encode(f"{d['username']}:{d['key']}".encode()).decode()
    url = f"https://www.kaggle.com/api/v1/datasets/download/{slug}"
    print(f"⬇️  Downloading '{slug}' from Kaggle …")
    zbytes = _fetch(urllib.request.Request(
        url, headers={"Authorization": f"Basic {token}"}), timeout=180)
    zf = zipfile.ZipFile(BytesIO(zbytes))
    csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csvs:
        raise ValueError("No CSV inside the dataset zip?")
    biggest = max(csvs, key=lambda n: zf.getinfo(n).file_size)
    print(f"📄 Using {biggest} ({zf.getinfo(biggest).file_size / 1024:.0f} KB)")
    return pd.read_csv(zf.open(biggest))


def geocode_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    lat/lon for every place via Nominatim (free, no key).
    Politeness rules: ≤1 request/second + a custom User-Agent.
    Every result is cached to disk, so re-running this script is INSTANT
    and we only ever ask the network once per place.
    """
    cache = json.loads(GEOCACHE.read_text()) if GEOCACHE.exists() else {}
    queries = [f"{name}, {city}, India"
               for name, city in zip(df["name"], df["city"])]
    missing = [q for q in dict.fromkeys(queries) if q not in cache]
    print(f"🗺️  Geocoding {len(missing)} place(s) via OpenStreetMap "
          f"({len(queries) - len(missing)} already cached) — ~1/sec, please wait")
    for i, q in enumerate(missing, 1):
        # try "Place, City, India" first; fall back to "Place, India"
        lat, lon = None, None
        for attempt in (q, q.split(",")[-3].strip() + ", India"
                        if q.count(",") >= 2 else None):
            if attempt is None:
                continue
            try:
                url = ("https://nominatim.openstreetmap.org/search?format=json"
                       "&limit=1&countrycodes=in&q=" + urllib.parse.quote(attempt))
                hits = json.loads(_fetch(urllib.request.Request(
                    url, headers={"User-Agent": "Wayfarer/1.0 (student project)"})))
                if hits:
                    lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
                    break
            except Exception:
                pass
            time.sleep(1.1)                       # one attempt rate is still 1/s
        cache[q] = [lat, lon]
        GEOCACHE.parent.mkdir(parents=True, exist_ok=True)
        GEOCACHE.write_text(json.dumps(cache))    # save progress AS WE GO
        time.sleep(1.1)                           # Nominatim politeness: ≤1 req/s
        if i % 25 == 0:
            print(f"   … {i}/{len(missing)} geocoded")
    lookups = [cache.get(q, [None, None]) for q in queries]
    df["lat"] = [x[0] for x in lookups]
    df["lon"] = [x[1] for x in lookups]
    return df


# ---------------------------------------------------------------- #
#  Build                                                            #
# ---------------------------------------------------------------- #
def build() -> pd.DataFrame:
    df = download_dataset(KAGGLE_SLUG)

    # Kaggle column names → our standard schema
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns={
        "google_review_rating": "rating",
        "entrance_fee_in_inr": "entry_fee_inr",
        "time_needed_to_visit_in_hrs": "avg_time_hours",
        "best_time_to_visit": "best_time",
    })

    df["name"] = df["name"].astype(str).str.strip()
    df["city"] = df["city"].astype(str).str.strip()
    df["state"] = df.get("state", pd.Series("", index=df.index)).astype(str).str.strip()

    # Recommender FUEL: Type + Significance become semicolon tags,
    # e.g. "Tomb;Historical" — richer tokens = better interest matching
    df["category"] = (df.get("type", pd.Series("", index=df.index)).fillna("").astype(str)
                      + ";" + df.get("significance", pd.Series("", index=df.index))
                      .fillna("").astype(str)).str.strip(";")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["entry_fee_inr"] = pd.to_numeric(df["entry_fee_inr"], errors="coerce").fillna(0)
    df["avg_time_hours"] = pd.to_numeric(df["avg_time_hours"], errors="coerce")

    df = geocode_all(df)
    df = df.drop_duplicates(subset=["name", "city"])

    out = df[["name", "city", "state", "category", "rating", "lat", "lon",
              "avg_time_hours", "entry_fee_inr", "best_time"]]
    out.to_csv(OUT_FILE, index=False)
    hits = int(out["lat"].notna().sum())
    print(f"💾 Saved {len(out)} real places ({hits} geocoded) → data/raw/places_india.csv")
    return out


# ---------------------------------------------------------------- #
#  Test drive                                                       #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        from src.data_loader import clean_places, find_data_file, load_places
        from src.recommender import PlaceRecommender
    except ImportError:  # running directly: python src\build_india_dataset.py
        from data_loader import clean_places, find_data_file, load_places
        from recommender import PlaceRecommender

    build()

    chosen = find_data_file("india")
    assert chosen.name == "places_india.csv", f"expected the REAL file, got {chosen}"
    clean = clean_places(load_places(chosen))
    print(f"✅ find_data_file('india') now serves {chosen.name} — "
          f"{len(clean)} clean REAL places")
    assert len(clean) > 80, "too few geocoded — check the network/cache"

    rec = PlaceRecommender().fit(clean)
    picks = rec.recommend(["temples"], top_n=5)
    print(picks[["name", "city", "rating"]].to_string(index=False))
    assert not picks.empty, "real-data recommender must match 'temples'"

    print("\n🎉 REAL-DATA UPGRADE COMPLETE — the site now plans with real data!")
