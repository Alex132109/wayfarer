"""
🧭 Wayfarer — weather.py  (E3 — REAL-time climate day-cards 🌦️)  ✅ live!

THE WISHLIST (E3): "essentials list — day level, REAL-TIME climate:
sunscreen/umbrella/raincoat from live weather."

The free OpenWeather endpoints (no credit card needed):
    /data/2.5/weather   → current conditions, one call per town
    /data/2.5/forecast  → 5 days / 3-hour steps → we aggregate per day

KEY MANAGEMENT (learn this pattern!): the key lives in
`.streamlit/secrets.toml` — which is GITIGNORED — or the `OPENWEATHER_KEY`
environment variable. Code NEVER contains secrets, so this repo can be
public while the key stays private.

GRACEFUL DEGRADATION (same rule as OSRM): no key / no network → every
function returns None and the features stay quiet. The app never crashes
because the weather server is down.
"""

import json
import os
import ssl
import sys
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".streamlit" / "secrets.toml"
API = "https://api.openweathermap.org/data/2.5"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _fetch_json(url: str, timeout: int = 20):
    """GET → JSON dict, with the standard verified→unverified SSL fallback."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read())
        except Exception:
            return None


def api_key() -> str | None:
    """secrets.toml first (Streamlit convention), env var second."""
    if SECRETS.exists():
        try:
            k = tomllib.loads(SECRETS.read_text(encoding="utf-8")).get("OPENWEATHER_API_KEY")
            if k:
                return str(k)
        except Exception:
            pass
    return os.environ.get("OPENWEATHER_KEY")


# ---------------------------------------------------------------- #
#  Current weather — one call per town                                #
# ---------------------------------------------------------------- #
def current(lat: float, lon: float, timeout: int = 20) -> dict | None:
    """Temp °C, feels-like, condition, rain chance %, wind km/h."""
    key = api_key()
    if key is None:
        return None
    url = (f"{API}/weather?lat={lat:.4f}&lon={lon:.4f}"
           f"&units=metric&appid={urllib.parse.quote(key)}")
    data = _fetch_json(url, timeout=timeout)
    if not data or "main" not in data:
        return None
    w = (data.get("weather") or [{}])[0]
    wind = data.get("wind", {})
    return {
        "temp_c": round(data["main"].get("temp", 0.0), 1),
        "feels_c": round(data["main"].get("feels_like", 0.0), 1),
        "condition": str(w.get("description", "")).title(),
        "rain_chance_pct": int(round(100 * data.get("pop", 0.0))),
        "wind_kmh": round(3.6 * wind.get("speed", 0.0)),
        "humidity": data["main"].get("humidity"),
    }


# ---------------------------------------------------------------- #
#  Daily forecast — aggregate 3-hourly rows per day                   #
# ---------------------------------------------------------------- #
def forecast_daily(lat: float, lon: float, days: int = 5, timeout: int = 20
                   ) -> pd.DataFrame | None:
    """Free forecast = 40 × 3-hourly entries → min/max temp + rain per day."""
    key = api_key()
    if key is None:
        return None
    url = (f"{API}/forecast?lat={lat:.4f}&lon={lon:.4f}"
           f"&units=metric&appid={urllib.parse.quote(key)}")
    data = _fetch_json(url, timeout=timeout)
    if not data or "list" not in data:
        return None
    rows: dict[str, dict] = {}
    for e in data["list"]:
        date = str(e["dt_txt"])[:10]              # "YYYY-MM-DD"
        r = rows.setdefault(date, {"min": 999.0, "max": -999.0, "rain_mm": 0.0,
                                   "pop": 0.0, "conditions": set()})
        t = e.get("main", {})
        r["min"] = min(r["min"], t.get("temp_min", t.get("temp", 0)))
        r["max"] = max(r["max"], t.get("temp_max", t.get("temp", 0)))
        r["rain_mm"] += (e.get("rain") or {}).get("3h", 0.0)
        r["pop"] = max(r["pop"], e.get("pop", 0.0))
        r["conditions"].add((e.get("weather") or [{}])[0].get("description", ""))
    out = []
    for date in sorted(rows)[:days]:
        r = rows[date]
        out.append({"date": date,
                    "min_c": round(r["min"], 1), "max_c": round(r["max"], 1),
                    "rain_mm": round(r["rain_mm"], 1),
                    "rain_chance_pct": int(round(100 * r["pop"])),
                    "condition": " / ".join(sorted(r["conditions"]))[:40] or "clear"})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- #
#  Weather → what to CARRY (the actual wishlist line)                 #
# ---------------------------------------------------------------- #
def day_essentials(temp_c: float, rain_chance_pct: int, condition: str = "") -> list[str]:
    """Rule engine: weather numbers → items. Demo-simple, easy to extend."""
    items = []
    if rain_chance_pct >= 40 or any(w in condition.lower()
                                    for w in ("rain", "drizzle", "thunder")):
        items += ["☔ umbrella", "🧥 raincoat"]
    if temp_c >= 30:
        items += ["🧴 sunscreen (SPF 50)", "🧢 cap", "💧 extra water"]
    elif temp_c <= 10:
        items += ["🧥 warm jacket", "🧣 layers"]
    elif temp_c <= 18:
        items += ["🧥 light jacket for evenings"]
    if "snow" in condition.lower():
        items += ["🧤 gloves", "❄️ snow boots"]
    if "haze" in condition.lower() or "smoke" in condition.lower():
        items += ["😷 N95 mask"]
    return items


def trip_weather(towns: list[dict], timeout: int = 20) -> pd.DataFrame | None:
    """
    towns = [{"town": name, "lat": .., "lon": ..}, ...]  (stay towns).
    One row per town: current weather + what to carry for those conditions.
    """
    rows = []
    for t in towns:
        c = current(t["lat"], t["lon"], timeout=timeout)
        if c is None:
            return None                       # first failure → stay quiet entirely
        rows.append({"town": t["town"], **c,
                     "carry": ", ".join(day_essentials(c["temp_c"],
                                                     c["rain_chance_pct"],
                                                     c["condition"])) or "—"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- #
#  Test drive (REAL network — the key is free)                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    print("=== current — Delhi ===")
    c = current(28.6139, 77.2090)
    print(c)
    assert c and "temp_c" in c

    print("\n=== 5-day forecast — Cherrapunji (rainiest town in India!) ===")
    fc = forecast_daily(25.2989, 91.5820)
    print(fc.to_string(index=False) if fc is not None else "unavailable")
    assert fc is not None and len(fc) >= 3

    print("\n=== essentials rules ===")
    assert "umbrella" in " ".join(day_essentials(24, 80)).lower()
    assert "sunscreen" in " ".join(day_essentials(34, 0)).lower()
    assert "jacket" in " ".join(day_essentials(5, 0)).lower()
    assert day_essentials(24, 0) == []

    print("\n=== trip weather — three stay towns ===")
    tw = trip_weather([{"town": "Delhi", "lat": 28.6139, "lon": 77.2090},
                       {"town": "Agra", "lat": 27.1739, "lon": 78.0399},
                       {"town": "Tokyo", "lat": 35.6895, "lon": 139.6917}])
    print(tw.to_string(index=False))
    assert len(tw) == 3 and tw["carry"].notna().all()

    print("\n🎉 ALL WEATHER TESTS PASSED — E3 is LIVE")
