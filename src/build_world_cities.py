"""
🧭 Wayfarer — build_world_cities.py  (FULL-WORLD city database 🌍)  ✅

THE WISHLIST: "full information all over the world — small tiny city to
big capitals — all data."

THE SOURCE: GeoNames cities500 — EVERY city/town on Earth with ≥500
people (plus admin capitals, even tiny ones). ~200,000+ rows:
villages, hill towns, islands, every capital. Free + CC-BY 4.0 licensed,
NO API KEY NEEDED.

THE SCALE PATTERN (read this!): 200k cities is too much to pretend they're
"attractions" — a city is a START/END point and CONTEXT, not a POI. So we
keep one clean city file for search/explorer features while attractions
keep coming from the UNESCO dataset + on-demand OpenStreetMap.

Data columns we keep (name, admin, country, lat, lon, population, timezone).

Run:  .venv\\Scripts\\python src\\build_world_cities.py   (~1 min, ~20 MB zip)
"""

import sys
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_FILE = RAW_DIR / "cities_world.csv"

GEONAMES_URL = "https://download.geonames.org/export/dump/cities500.zip"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build() -> pd.DataFrame:
    print("⬇️  Downloading GeoNames cities500 (every city on Earth ≥500 people) …")
    with urllib.request.urlopen(GEONAMES_URL, timeout=300) as resp:
        zbytes = resp.read()
    zf = zipfile.ZipFile(BytesIO(zbytes))
    txt = zf.read("cities500.txt").decode("utf-8")

    # GeoNames dump format: TAB-separated, FIXED column order (their spec —
    # all 19 columns, no header). LESSON: one missing column name poisons
    # every field after it (population silently became admin codes!).
    # quoting=3 (QUOTE_NONE) because GeoNames fields may contain quotes.
    cols = ["geonameid", "name", "asciiname", "alternatenames", "lat", "lon",
            "feature_class", "feature_code", "country", "cc2", "admin1",
            "admin2", "admin3", "admin4", "population", "elevation", "dem",
            "timezone", "modified"]
    df = pd.read_csv(BytesIO(txt.encode()), sep="\t", names=cols,
                     low_memory=False, quoting=3)

    out = (df[["name", "asciiname", "admin1", "country", "lat", "lon",
               "population", "timezone", "alternatenames"]]
           .drop_duplicates(subset=["name", "lat", "lon"])
           .reset_index(drop=True))
    # Searchable surface = ASCII name + alternate names: "Reykjavík" must be
    # findable when the user types plain "reykjavik", "Bombay" → Mumbai etc.
    # (asciiname is GeoNames' own accent-free form; commas → semicolons)
    out["alt_names"] = (out["asciiname"].fillna("").astype(str) + ";"
                        + out["alternatenames"].fillna("").astype(str)
                        ).str.replace(",", ";", regex=False).str.slice(0, 240)
    out = out.drop(columns=["asciiname", "alternatenames"])
    # Some rows carry blank/text coordinates — coerce and drop them
    # (a city without coordinates can't be routed to).
    out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
    out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
    out = out.dropna(subset=["lat", "lon"])
    out = out[out["lat"].between(-90, 90) & out["lon"].between(-180, 180)]
    out["country"] = out["country"].fillna("").astype(str).str.upper()
    out["admin1"] = out["admin1"].fillna("").astype(str)
    out["population"] = pd.to_numeric(out["population"], errors="coerce").fillna(0).astype(int)

    out = out[["name", "admin1", "country", "lat", "lon", "population",
               "timezone", "alt_names"]]
    out.to_csv(OUT_FILE, index=False)
    print(f"💾 Saved {len(out):,} cities → data/raw/cities_world.csv "
          f"({OUT_FILE.stat().st_size / 1e6:.1f} MB)")
    return out


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        from src.data_loader import haversine_km
    except ImportError:
        from data_loader import haversine_km

    world = build()

    assert len(world) > 150_000, "GeoNames cities file unexpectedly small"
    assert world["lat"].between(-90, 90).all() and world["lon"].between(-180, 180).all()

    # every famous capital + some TINY towns must be present — searched by
    # official name OR alternate names ("Berhampur" lives under Brahmapur,
    # "Cherrapunji" under Sohra — India loves colonial→official renames!)
    names = set(world["name"].astype(str).str.lower())
    alts = world["alt_names"].fillna("").astype(str).str.lower()
    for must in ("delhi", "tokyo", "london", "paris", "berhampur",
                 "shillong", "ulaanbaatar", "reykjavik", "cherrapunji"):
        found = (must in names) | alts.str.contains(must, regex=False).any()
        assert found, f"missing city: {must}"
    print("✅ capitals, tiny towns AND alternate names all present")

    # distance sanity with OUR haversine: Delhi→London is ≈ 6,700 km.
    # DUPLICATE-NAME LESSON: there are Delhi/London towns in Canada & the USA
    # — pick the row with the LARGEST population (16M wins over 1,600).
    def biggest(rows: pd.DataFrame) -> pd.Series:
        return rows.sort_values("population", ascending=False).iloc[0]

    d = biggest(world[world["name"].str.lower() == "delhi"])
    l = biggest(world[world["name"].str.lower() == "london"])
    assert d["country"] == "IN" and l["country"] == "GB", "population pick failed"
    km = haversine_km(float(d["lat"]), float(d["lon"]), float(l["lat"]), float(l["lon"]))
    assert 6000 < km < 7500, km
    print(f"✅ Delhi(IN)→London(GB) via our haversine: {km:,.0f} km (sane)")

    big = world.nlargest(5, "population")[["name", "country", "population"]]
    print("\nTop 5 cities by population:")
    print(big.to_string(index=False))

    print("\n🎉 WORLDWIDE CITY DATABASE COMPLETE")
