"""
🧭 Wayfarer — build_world_dataset.py  (PHASE 2 STARTER ✨)

Downloads the official UNESCO World Heritage Sites export (~1200+ iconic places
across the whole world, each with GPS coordinates) and converts it into a CSV
that matches Wayfarer's standard places format.

No Kaggle login needed — UNESCO publishes this list openly.

Run:
    .venv\\Scripts\\python src\\build_world_dataset.py

NOTE ON DISTANCES:
    We do NOT store "km from every place to every other place" — with N places
    that's N^2 rows (10,000 places = 100 million distances! 😱).
    Instead we store lat/lon and compute km on demand with the haversine
    formula (see haversine_km in data_loader.py). The router in Week 3 only
    builds a distance matrix for the ~10-15 places of ONE trip.
"""

import re
import ssl
import sys
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
XML_PATH = RAW_DIR / "unesco_world_heritage.xml"
CSV_PATH = RAW_DIR / "places_world_heritage.csv"

UNESCO_XML_URL = "https://whc.unesco.org/en/list/xml/"


# ---------------------------------------------------------------- #
#  1. DOWNLOAD                                                     #
# ---------------------------------------------------------------- #
def download_xml() -> Path:
    """Download the UNESCO list once; skip if we already have it."""
    if XML_PATH.exists() and XML_PATH.stat().st_size > 100_000:
        print(f"📄 Already downloaded: {XML_PATH.name}")
        return XML_PATH

    print("🌐 Downloading UNESCO World Heritage Sites list ...")
    req = Request(UNESCO_XML_URL, headers={"User-Agent": "Mozilla/5.0 (Wayfarer project)"})

    # Try verified SSL first; some networks (college/office proxies) break it,
    # so fall back to skipping verification for this public data file.
    # NOTE: urllib wraps SSL failures inside URLError, so catch both.
    try:
        with urlopen(req, timeout=120) as resp:
            content = resp.read()
    except (ssl.SSLError, urllib.error.URLError) as e:
        print(f"⚠️  SSL check failed ({e.reason if isinstance(e, urllib.error.URLError) else e}) — retrying without verification ...")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(req, timeout=120, context=ctx) as resp:
            content = resp.read()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    XML_PATH.write_bytes(content)
    print(f"✅ Saved {XML_PATH.stat().st_size / 1e6:.1f} MB -> {XML_PATH.name}")
    return XML_PATH


# ---------------------------------------------------------------- #
#  2. PARSE + CONVERT                                              #
# ---------------------------------------------------------------- #
def strip_html(text: str) -> str:
    """Remove embedded HTML tags from description text."""
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def parse_xml(path: Path) -> pd.DataFrame:
    """
    Extract every site into our standard columns.

    XML structure (learned by inspecting the file):
        <row>
          <site>Taj Mahal</site>
          <states>India</states>            ← country/countries
          <regions>Asia and the Pacific</regions>
          <category>Cultural</category>
          <geolocations><poi><latitude>...</latitude><longitude>...</longitude></poi></geolocations>
          <short_description>&lt;p&gt;...&lt;/p&gt;</short_description>  ← HTML-escaped!
        </row>

    A site can have MANY <poi> points — we keep the first (main) one.
    """
    tree = ET.parse(path)
    rows = []
    for row in tree.iter("row"):
        name = (row.findtext("site") or "").strip()
        if not name:
            continue

        # Coordinates live inside <geolocations><poi> — not on <row> directly!
        poi = row.find("./geolocations/poi")
        lat = (poi.findtext("latitude") or "").strip() if poi is not None else ""
        lon = (poi.findtext("longitude") or "").strip() if poi is not None else ""
        if not lat or not lon:
            continue  # skip sites without coordinates

        countries = (row.findtext("states") or "").split(",")
        cat = (row.findtext("category") or "").strip()

        rows.append({
            "name": name,
            "city": countries[0].strip() if countries and countries[0] else "",  # primary country
            "state": (row.findtext("regions") or "").strip(),     # world region
            "category": f"{cat};UNESCO".strip(";"),
            "rating": "",                                         # UNESCO list has no ratings
            "lat": lat,
            "lon": lon,
            "avg_time_hours": 2.0,                                # safe default
            "entry_fee_inr": 0,
            "best_time": "",
            "description": strip_html(row.findtext("short_description") or "")[:500],
            "location_hint": (row.findtext("location") or "").strip()[:120],
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- #
#  3. DEMO — km distances computed ON DEMAND                       #
# ---------------------------------------------------------------- #
def demo_distances(df: pd.DataFrame) -> None:
    """Show the 'km to other places' idea working the smart way."""
    try:
        from src.data_loader import distance_matrix
    except ImportError:  # when run directly as: python src\build_world_dataset.py
        from data_loader import distance_matrix

    wanted = ["Taj Mahal", "Great Wall", "Machu Picchu", "Petra", "Statue of Liberty"]
    found = pd.DataFrame()
    for w in wanted:
        hit = df[df["name"].str.contains(w, case=False, na=False)].head(1)
        found = pd.concat([found, hit])

    if len(found) < 2:
        print("\n(skip distance demo — famous sites not found in the data)")
        return

    print(f"\n🗺️  Distance matrix — computed on demand, just for these {len(found)} places:")
    print(distance_matrix(found.reset_index(drop=True)).round(0).to_string())


# ---------------------------------------------------------------- #
if __name__ == "__main__":
    xml_file = download_xml()
    df = parse_xml(xml_file)

    before = len(df)
    df = df.drop_duplicates(subset=["name", "city"]).reset_index(drop=True)
    df.to_csv(CSV_PATH, index=False)

    print(f"\n🌍 Converted {before} rows -> {len(df)} unique places")
    print(f"💾 Saved: {CSV_PATH.relative_to(ROOT)}")

    if "city" in df.columns:
        print("\n🏆 Top 10 countries by number of sites:")
        print(df["city"].value_counts().head(10).to_string())

    demo_distances(df)
    print("\n➡️  Next: run 'python src/data_loader.py' to see Wayfarer use this data!")
