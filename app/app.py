"""
🧭 Wayfarer — the website  (WEEK 4 ✅)

A Streamlit web app that wires the whole ML pipeline into a UI:

    pick a country → interests OR your own stops → start/end + days
        → optimal route (km per leg) → day-wise plan with stays → map

Run it:
    .venv\\Scripts\\streamlit run app\\app.py
Then open the URL shown (usually http://localhost:8501).
"""

import sys
from pathlib import Path

import streamlit as st

# Make "src" importable no matter where streamlit is launched from
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_loader import clean_places, find_data_file, load_places
from src.itinerary import LONG_DRIVE_KM, TripPlanner

st.set_page_config(page_title="Wayfarer — AI Trip Planner", page_icon="🧭", layout="wide")

DATASETS = {
    "🇮🇳 India (starter sample)": "india",
    "🎒 Meghalaya round trip": "meghalaya",
    "🇯🇵 Japan (golden route)": "japan",
    "🌍 Worldwide (UNESCO sites)": "world",
}


# ---------------------------------------------------------------- #
#  Data & model (cached — built once per session)                  #
# ---------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def get_places(key: str):
    path = find_data_file(key)
    if path is None:
        return None
    return clean_places(load_places(path))


@st.cache_resource(show_spinner=False)
def get_planner(key: str):
    return TripPlanner(get_places(key))


def short(name: str, width: int = 58) -> str:
    """Trim very long place names (worldwide data has some monsters)."""
    return name if len(name) <= width else name[: width - 1] + "…"


# ---------------------------------------------------------------- #
#  Header                                                          #
# ---------------------------------------------------------------- #
st.title("🧭 Wayfarer")
st.caption("Tell me where, when and what you love — I'll plan the smartest trip.")
st.divider()


# ---------------------------------------------------------------- #
#  Sidebar — inputs                                                #
# ---------------------------------------------------------------- #
with st.sidebar:
    st.header("Trip settings")
    dataset_label = st.selectbox("Where to?", list(DATASETS.keys()), index=1)
    key = DATASETS[dataset_label]

    places = get_places(key)
    if places is None:
        st.error("No dataset found — check data/ folders.")
        st.stop()

    planner = get_planner(key)
    names = sorted(places["name"].astype(str).tolist())

    mode = st.radio("How do you choose places?",
                    ["🎯 By my interests", "🗺️ I already know the stops"])

    origin = st.selectbox("Start point", names,
                          format_func=short,
                          index=names.index("Berhampur") if "Berhampur" in names else 0)
    destination = st.selectbox("End point", names,
                               format_func=short,
                               index=names.index("Berhampur") if "Berhampur" in names else 0)
    if origin == destination:
        st.info("🔁 Start = End → Wayfarer will plan a ROUND TRIP loop!")

    days = st.number_input("Trip length (days)", 1, 30, 5)

    interests, stops = [], []
    if mode.startswith("🎯"):
        tokens = set()
        for cats in places["category"].fillna("").astype(str).str.split(";"):
            tokens.update(t.strip().title() for t in cats if t.strip() and t.strip() != "UNESCO")
        interests = st.multiselect("Your interests", sorted(tokens),
                                   default=sorted(tokens)[:2])
    else:
        stops = st.multiselect("Places to visit (order is optimized for you)",
                               names, format_func=short)


# ---------------------------------------------------------------- #
#  Plan the trip                                                   #
# ---------------------------------------------------------------- #
st.subheader("1. Your request")
if mode.startswith("🎯"):
    st.write(f"**From** {short(origin)} → **to** {short(destination)} · **{days} days** · loves {', '.join(interests) or '—'}")
    ready = bool(interests)
else:
    st.write(f"**From** {short(origin)} → **to** {short(destination)} · **{days} days** · {len(stops)} chosen stops")
    ready = len(stops) >= 1

if not ready:
    st.warning("Pick at least one interest / stop to continue 🙂")
    st.stop()

if st.button("Plan my trip 🧭", type="primary"):
    with st.spinner("Recommending places, optimizing route, splitting days..."):
        try:
            if mode.startswith("🎯"):
                route_df, total_km, stay_plan = planner.plan(
                    origin, destination, interests, n_places=6, days=int(days))
            else:
                route_df, total_km, stay_plan = planner.plan_explicit(
                    origin, destination, stops, days=int(days))
        except ValueError as e:
            st.error(str(e))
            st.stop()

    # --- headline numbers ----------------------------------------- #
    st.subheader("2. Your itinerary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total distance", f"{total_km:,.0f} km")
    m2.metric("Stops", len(route_df))
    m3.metric("Days", int(days))
    m4.metric("Options", "1 route", help="Multiple variants coming soon!")

    # --- map ------------------------------------------------------ #
    loc = planner.places.set_index(planner.places["name"].astype(str))[["lat", "lon"]]
    pts = route_df.assign(
        lat=route_df["name"].map(loc["lat"]).astype(float),
        lon=route_df["name"].map(loc["lon"]).astype(float),
    ).dropna(subset=["lat", "lon"])
    if not pts.empty:
        st.map(pts, latitude="lat", longitude="lon", use_container_width=True)

    # --- route table ---------------------------------------------- #
    st.dataframe(route_df, use_container_width=True, hide_index=True)

    # --- day-wise plan with stays --------------------------------- #
    if stay_plan:
        st.subheader("3. Day-wise plan with stays 🏨")
        cityof = dict(zip(route_df["name"].astype(str), route_df["city"]))
        day = 1
        for seg in stay_plan:
            label = f"Day {day}" if seg["days"] == 1 else f"Day {day}–{day + seg['days'] - 1}"
            day += seg["days"]
            place = seg["place"]
            town = seg.get("stay_town") or cityof.get(place, place)
            with st.container(border=True):
                st.markdown(f"**{label}: {short(place, 70)}**  ·  🏨 stay: **{town}**")
                bits = []
                if seg.get("en_route"):
                    bits.append(".en-route: " + ", ".join(short(x, 40) for x in seg["en_route"]))
                if seg.get("drive_km", 0) > LONG_DRIVE_KM:
                    bits.append(f"🚗 long drive ~{seg['drive_km']:.0f} km — add buffer day(s)!")
                if bits:
                    st.caption("   ·   ".join(bits))

        # return-drive warning for round trips
        if str(route_df.iloc[-1]["name"]).startswith("↩️"):
            ret = float(route_df.iloc[-2]["km_to_next"])
            if ret > LONG_DRIVE_KM:
                st.warning(f"🚗 Return drive ≈ {ret:.0f} km — plan buffer days or consider flying back!")

    st.caption("ℹ️ Distances are straight-line (great-circle). Road km are usually 20–30% more.")
else:
    st.info("👆 Click **Plan my trip** to see your optimized itinerary!")
