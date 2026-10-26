"""
🧭 Wayfarer — exports.py  (15/10 sprint — take your plan with you 📤)  ✅

Three zero-cost, zero-dependency exports:
    1. google_maps_url() — opens the optimized route in Google Maps with
       lat/lon waypoints → real navigation, one click.
    2. ics_calendar()    — the itinerary as calendar events (Google/Apple/
       Outlook all import .ics).
    3. save_trip_html()  — a self-contained, print-friendly HTML itinerary
       (route + budget + day guide + essentials). Send it on WhatsApp,
       print it, or read it offline with zero internet.

Educational note: all three are just STRING BUILDING — no libraries needed.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent   # the "wayfarer" folder

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- #
#  1. GOOGLE MAPS — optimized route → turn-by-turn navigation        #
# ---------------------------------------------------------------- #
def google_maps_url(route_df, places, max_waypoints: int = 9) -> str:
    """Route as a Google Maps directions link (lat,lon precision beats names)."""
    loc = dict(zip(places["name"].astype(str),
                   zip(places["lat"].astype(float), places["lon"].astype(float))))
    stops = [n for n in route_df["name"].astype(str) if not n.startswith("↩️")]
    if len(stops) < 2:
        return "https://www.google.com/maps"

    def ll(name):
        lat, lon = loc.get(name, (0.0, 0.0))
        return f"{lat:.6f},{lon:.6f}"

    origin, destination = ll(stops[0]), ll(stops[-1])
    mid = [ll(n) for n in stops[1:-1]][:max_waypoints]
    url = (f"https://www.google.com/maps/dir/?api=1&origin={quote(origin)}"
           f"&destination={quote(destination)}&travelmode=driving")
    if mid:
        url += "&waypoints=" + quote("|".join(mid))
    if len(stops) - 2 > max_waypoints:
        print(f"ℹ️  Google Maps fits {max_waypoints} waypoints — the rest are straight legs")
    return url


# ---------------------------------------------------------------- #
#  2. ICS CALENDAR — each day = one event                            #
# ---------------------------------------------------------------- #
def ics_calendar(stay_plan, trip_date: str = "20270101",
                 title: str = "Wayfarer Trip") -> str:
    """Build .ics text. trip_date = 'YYYYMMDD' when the trip starts."""
    out = ["BEGIN:VCALENDAR", "VERSION:2.0",
           "PRODID:-//Wayfarer//Trip Planner//EN"]
    day = 1
    base = datetime.strptime(trip_date, "%Y%m%d")
    for seg in stay_plan:
        for _ in range(max(int(seg["days"]), 1)):
            start = base + timedelta(days=day - 1)
            end = start + timedelta(days=1)
            out += [
                "BEGIN:VEVENT",
                f"UID:wayfarer-day{day}-{start.strftime('%Y%m%d')}@wayfarer.app",
                f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
                f"SUMMARY:Day {day} — {seg['place']}",
                f"LOCATION:{seg.get('stay_town') or seg['place']}",
                "END:VEVENT",
            ]
            day += 1
    out.append("END:VCALENDAR")
    return "\r\n".join(out)


# ---------------------------------------------------------------- #
#  3. OFFLINE HTML ITINERARY — print / WhatsApp / no internet        #
# ---------------------------------------------------------------- #
HTML_CSS = """
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #1F2937;
         max-width: 820px; margin: 24px auto; padding: 0 16px; }
  h1 { color: #0F172A; }
  .meta { color: #64748B; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th, td { border: 1px solid #E2E8F0; padding: 7px 10px; font-size: .92rem; text-align: left; }
  th { background: #F1F5F9; }
  .box { border: 1px solid #E2E8F0; border-left: 5px solid #FF5A5F;
         border-radius: 10px; padding: 10px 14px; margin: 10px 0; }
  .box b { color: #0F172A; }
  .muted { color: #64748B; font-size: .88rem; }
  .warn { color: #B91C1C; font-weight: 600; }
  @media print { body { margin: 0; } }
</style>
"""


def save_trip_html(summary: dict, inputs: dict, path: Path) -> Path:
    """Self-contained printable itinerary from a TripPlan.summary() dict."""
    money = summary["money"]
    parts = [
        "<html><head><meta charset='utf-8'><title>Wayfarer itinerary</title>",
        HTML_CSS, "</head><body>",
        f"<h1>🧭 {inputs.get('origin')} → {inputs.get('destination')}</h1>",
        f"<p class='meta'>{inputs.get('days')} days · {inputs.get('travellers')} travellers · "
        f"{money['label']} · 🛣️ {summary['total_km']:,.0f} km</p>",
        "<h2>🗺️ Route</h2><table><tr><th>#</th><th>Stop</th><th>City</th><th>km to next</th></tr>",
    ]
    for _, r in summary["route_df"].iterrows():
        parts.append(f"<tr><td>{r['stop']}</td><td>{r['name']}</td>"
                     f"<td>{r.get('city', '')}</td><td>{r['km_to_next']}</td></tr>")
    parts.append("</table>")

    parts.append(f"<h2>💰 Budget</h2><div class='box'>"
                 f"Trip per person <b>₹{money['trip_pp']:,}</b> · "
                 f"emergency fund <b>₹{money['emergency_pp']:,}</b> · "
                 f"group total <b>₹{money['trip_group'] + money['emergency_group']:,}</b><br>"
                 f"<span class='muted'>meals pp: breakfast ₹{money['per_meal']['breakfast']:,} · "
                 f"lunch ₹{money['per_meal']['lunch']:,} · dinner ₹{money['per_meal']['dinner']:,}"
                 f" · intercity: {money['intercity']['note']}</span></div>")

    if summary.get("guide"):
        parts.append("<h2>📅 Day-wise guide</h2>")
        for d in summary["guide"]:
            parts.append(f"<div class='box'><b>Day {d['day']} — {d['town']}</b>")
            for i in d["items"]:
                extra = f" · ⏱ {i['max_time']}" if i.get("max_time") else ""
                tip = f" · try: {i['try']}" if i.get("try") else ""
                parts.append(f"<br><span class='muted'>{i['time']}</span> {i['label']}{extra}{tip}")
            parts.append("</div>")

    ess = summary["essentials"]
    parts.append("<h2>🎒 Essentials</h2><div class='box'>"
                 + " · ".join(ess["documents"])
                 + "<br>" + "<br>".join(ess["per_day"]) + "</div>")

    parts.append("<p class='muted'>Generated by Wayfarer — distances are real road km "
                 "where OSRM data was available.</p></body></html>")
    path = Path(path)
    path.write_text("".join(parts), encoding="utf-8")
    return path


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        from src.data_loader import clean_places, find_data_file, load_places
        from src.itinerary import TripPlanner
        from src.trip_plan import TripPlan
    except ImportError:  # running directly: python src\exports.py
        from data_loader import clean_places, find_data_file, load_places
        from itinerary import TripPlanner
        from trip_plan import TripPlan

    df_m = clean_places(load_places(find_data_file("meghalaya")))
    planner = TripPlanner(df_m)
    plan = TripPlan(planner, origin="Berhampur", destination="Berhampur",
                    stops=["Shillong (Police Bazar & Ward's Lake)",
                           "Cherrapunji (Sohra) Waterfalls & Caves",
                           "Dawki (Umngot River Boating)"],
                    days=5, travellers=5, mode="car")
    plan.recompute()
    s = plan.summary()

    url = google_maps_url(s["route_df"], planner.places)
    assert url.startswith("https://www.google.com/maps/dir/?api=1")
    print("🗺️ Google Maps link:", url[:95], "…")

    ics = ics_calendar(s["stay_plan"])
    assert ics.count("BEGIN:VEVENT") == 5 and ics.endswith("END:VCALENDAR")
    print("📅 ICS: 5 day-events generated")

    out = ROOT / "exports" / "meghalaya_trip.html"
    out.parent.mkdir(parents=True, exist_ok=True)   # exports/ may not exist yet
    save_trip_html(s, plan.inputs, out)
    assert out.exists() and out.stat().st_size > 4000
    print(f"🖨️ Offline itinerary saved: {out.relative_to(ROOT)} "
          f"({out.stat().st_size / 1024:.1f} KB) — open it in any browser")

    print("\n🎉 ALL EXPORT TESTS PASSED")
