"""
🧭 Wayfarer — osm_places.py  (REAL stays & sights ANYWHERE on Earth 🏨)

THE WISHLIST: "stays places all over the world — tiny city to capitals."

WHY NOT ONE GIANT HOTELS FILE? "Every hotel on Earth" is gigabytes that no
free API serves — and 99% would be for cities you'll never visit. The smart
pattern is the SAME one we use for km distances: fetch ONLY what a trip
needs (hotels/sights around the places actually visited) from OpenStreetMap's
free **Overpass API**, and cache each query on disk forever.

    fetch-on-demand → cache → never pay twice

WHAT OSM GIVES (honest limits): names + coordinates + kinds (hotel /
guest_house / hostel / castle / monument …) are REAL mapped data. Prices
and ratings are NOT in OSM — the UI shows them as "ask at desk" instead
of inventing numbers.
"""

import hashlib
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
# Public Overpass servers rate-limit aggressively — try mirrors in order.
# (Standard practice for Overpass apps; each result is disk-cached anyway.)
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _fetch(query: str, timeout: int = 90, budget_s: int = 60) -> dict | None:
    """POST a query to Overpass → parsed JSON.

    Two safety nets, learned the hard way:
      • verified SSL first, proxy-friendly unverified fallback (campus/corporate
        proxies often serve expired certs — never crash on it)
      • a TOTAL time budget across all mirrors (deadline pattern): a
        rate-limited public server must not freeze a UI click for minutes.
    """
    deadline = time.monotonic() + budget_s
    body = urllib.parse.urlencode({"data": query}).encode()
    for url in ENDPOINTS:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        t_out = min(timeout, max(int(remaining), 1))
        req = urllib.request.Request(url, data=body, headers={
            "User-Agent": "Wayfarer/1.0 (student project)"})
        try:
            with urllib.request.urlopen(req, timeout=t_out) as resp:
                return json.loads(resp.read())
        except Exception:
            pass
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(req, timeout=t_out, context=ctx) as resp:
                return json.loads(resp.read())
        except Exception:
            continue
    return None


def _cached(kind: str, lat: float, lon: float, radius_m: int, limit: int,
            timeout: int = 90, budget_s: int = 60):
    """Cache key = kind + location rounded to ~110 m (3 decimals)."""
    key = f"{kind}|{lat:.3f}|{lon:.3f}|{radius_m}|{limit}"
    cache_file = CACHE_DIR / f"osm_{hashlib.md5(key.encode()).hexdigest()}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text()), "cache"
    q = None
    if kind == "hotels":
        q = (f'[out:json][timeout:90];('
             f'node["tourism"~"^(hotel|guest_house|hostel|motel|apartment)$"]'
             f'(around:{radius_m},{lat:.6f},{lon:.6f});'
             f'way["tourism"~"^(hotel|guest_house|hostel|motel|apartment)$"]'
             f'(around:{radius_m},{lat:.6f},{lon:.6f}););'
             f'out tags center {limit};')
    else:  # sights: attractions + historic landmarks
        q = (f'[out:json][timeout:90];('
             f'node["tourism"="attraction"](around:{radius_m},{lat:.6f},{lon:.6f});'
             f'node["historic"](around:{radius_m},{lat:.6f},{lon:.6f});'
             f'way["tourism"="attraction"](around:{radius_m},{lat:.6f},{lon:.6f});'
             f'way["historic"](around:{radius_m},{lat:.6f},{lon:.6f}););'
             f'out tags center {limit};')
    data = _fetch(q, timeout=timeout, budget_s=budget_s)
    elements = (data or {}).get("elements")
    if elements is None:
        return None, "offline"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(elements))
    return elements, "live"


def _to_df(elements: list) -> pd.DataFrame:
    """Overpass elements → tidy DataFrame (nodes carry lat/lon directly,
    ways carry a `center` object — handle both). Unnamed OSM objects are
    skipped: an unnamed 'node' is useless for a traveller."""
    rows = []
    for el in elements:
        c = el.get("center") or el
        lat, lon = c.get("lat"), c.get("lon")
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        if name is None or lat is None:
            continue
        kind = tags.get("tourism") or tags.get("historic") or "place"
        rows.append({"name": str(name), "kind": kind,
                     "lat": float(lat), "lon": float(lon)})
    df = pd.DataFrame(rows).drop_duplicates(subset=["name"])
    return df.reset_index(drop=True)


def hotels_near(lat: float, lon: float, radius_km: float = 15,
                limit: int = 40, timeout: int = 90, budget_s: int = 60
                ) -> pd.DataFrame | None:
    """REAL stays around a point. None = no network (feature stays quiet)."""
    elements, _src = _cached("hotels", lat, lon, int(radius_km * 1000), limit,
                             timeout=timeout, budget_s=budget_s)
    if elements is None:
        return None
    return _to_df(elements)


def sights_near(lat: float, lon: float, radius_km: float = 15,
                limit: int = 40, timeout: int = 90, budget_s: int = 60
                ) -> pd.DataFrame | None:
    """REAL sights (attractions + historic) around a point."""
    elements, _src = _cached("sights", lat, lon, int(radius_km * 1000), limit,
                             timeout=timeout, budget_s=budget_s)
    if elements is None:
        return None
    return _to_df(elements)


# ---------------------------------------------------------------- #
#  Test drive (real network — Overpass is free, results get cached)   #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    print("=== 🏨 REAL hotels near Shillong, Meghalaya ===")
    h = hotels_near(25.5788, 91.8933)
    print("found:", 0 if h is None else len(h))
    assert h is not None and len(h) > 3
    print(h.head(6)[["name", "kind"]].to_string(index=False))

    print("\n=== 🏛️ REAL sights near Delhi ===")
    s = sights_near(28.6139, 77.2090)
    print("found:", 0 if s is None else len(s))
    assert s is not None and len(s) > 3
    print(s.head(6)[["name", "kind"]].to_string(index=False))

    print("\n=== ⚡ second call = INSTANT (disk cache) ===")
    h2 = hotels_near(25.5788, 91.8933)
    assert h2 is not None and len(h2) == len(h)
    print("same", len(h2), "hotels served from cache — no network")

    print("\n🎉 ALL OSM TESTS PASSED — real worldwide stays & sights work")
