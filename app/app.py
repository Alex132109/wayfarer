"""
🧭 Wayfarer — the website  (WEEK 4 ✅ · redesigned ✨)

A Streamlit web app that wires the whole ML pipeline into a styled UI:

    pick a country → interests OR your own stops → start/end + days
        → optimal route (km per leg) → day-wise plan with stays → map

Run it:
    .venv\\Scripts\\streamlit run app\\app.py
"""

import html
import sys
from pathlib import Path

import pandas as pd
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
#  Design system (CSS — kept in a plain string: no f-string braces) #
# ---------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

html, body, .stApp, [data-testid="stSidebar"] { font-family: 'Poppins', sans-serif; }
.block-container { padding-top: 1.2rem; max-width: 1180px; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

/* hero banner */
.hero {
  background: linear-gradient(120deg, #0F172A 0%, #155E75 55%, #FF5A5F 140%);
  border-radius: 22px; padding: 34px 40px; color: #fff; margin-bottom: 18px;
}
.hero h1 { font-size: 2.5rem; font-weight: 800; margin: 0; letter-spacing: .5px; }
.hero p  { margin: 6px 0 0; opacity: .92; font-size: 1.05rem; }
.hero .tag {
  display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.25);
  border-radius: 999px; padding: 2px 12px; font-size: .78rem; margin-right: 6px; margin-top: 12px;
}

/* metric cards */
.metrics { display: flex; gap: 14px; margin: 6px 0 14px; }
.mcard {
  flex: 1; background: #fff; border-radius: 16px; padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(15,23,42,.08), 0 8px 24px rgba(15,23,42,.05);
}
.mcard .ico { font-size: 1.2rem; }
.mcard .val { font-size: 1.65rem; font-weight: 800; color: #0F172A; line-height: 1.15; }
.mcard .lab { font-size: .78rem; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: .4px; }

/* journey steps */
.journey { margin: 4px 0 8px; }
.stop {
  display: flex; align-items: center; gap: 14px; background: #fff;
  border-radius: 14px; padding: 12px 16px; margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(15,23,42,.07);
}
.num {
  width: 34px; height: 34px; min-width: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #FF5A5F, #FF8A65);
  color: #fff; font-weight: 700; display: flex; align-items: center; justify-content: center;
  font-size: .95rem;
}
.num.ret { background: linear-gradient(135deg, #0E7490, #155E75); }
.who { flex: 1; min-width: 0; }
.nm  { font-weight: 700; color: #0F172A; font-size: 1rem; }
.meta { color: #64748B; font-size: .82rem; }
.km {
  background: #EEF2F7; color: #0E7490; font-weight: 700; font-size: .82rem;
  border-radius: 999px; padding: 5px 12px; white-space: nowrap;
}

/* day cards */
.day {
  display: flex; gap: 14px; align-items: flex-start; background: #fff;
  border-left: 5px solid #FF5A5F; border-radius: 14px; padding: 14px 18px; margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(15,23,42,.07);
}
.daychip {
  background: #0F172A; color: #fff; font-weight: 700; font-size: .78rem;
  border-radius: 999px; padding: 6px 12px; white-space: nowrap; margin-top: 2px;
}
.daybody b { color: #0F172A; }
.sub { color: #64748B; font-size: .85rem; margin-top: 4px; }
.sub.warn { color: #B91C1C; font-weight: 600; }

/* buttons + headers */
.stButton > button {
  background: linear-gradient(90deg, #FF5A5F, #FF8A65); color: #fff; border: none;
  border-radius: 999px; padding: .55rem 2.1rem; font-weight: 700; font-size: 1.02rem;
  box-shadow: 0 6px 16px rgba(255,90,95,.30);
}
.stButton > button:hover { filter: brightness(1.06); transform: translateY(-1px); }
h2 { font-weight: 700; color: #0F172A; }
[data-testid="stSidebar"] label { font-weight: 600; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

HERO = """
<div class="hero">
  <h1>🧭 Wayfarer</h1>
  <p>Your AI trip planner — optimal routes, km for every leg, and day-wise stays.</p>
  <span class="tag">🤖 ML recommender</span><span class="tag">🗺️ route optimizer</span>
  <span class="tag">🏨 stay planner</span><span class="tag">🇮🇳 India first → 🌍 worldwide</span>
</div>
"""


# ---------------------------------------------------------------- #
#  Data & model (cached — built once per session)                  #
# ---------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def get_places(key: str):
    path = find_data_file(key)
    return clean_places(load_places(path)) if path else None


@st.cache_resource(show_spinner=False)
def get_planner(key: str):
    return TripPlanner(get_places(key))


def short(name: str, width: int = 58) -> str:
    return name if len(name) <= width else name[: width - 1] + "…"


def _num(val) -> float | None:
    """Safely read any cell as a number — returns None instead of crashing.

    Datasets carry messy values ("" empty strings, NaN, stray text). This
    helper is the website's seatbelt: numeric columns stay numeric.
    """
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if pd.notna(f) else None


# ---------------------------------------------------------------- #
#  Renderers (styled HTML)                                         #
# ---------------------------------------------------------------- #
def metrics_html(total_km: float, n_stops: int, days: int, is_round: bool) -> str:
    cards = [
        ("🛣️", f"{total_km:,.0f}", "KM TOTAL"),
        ("📍", str(n_stops), "STOPS"),
        ("📅", str(days), "DAYS"),
        ("🔁" if is_round else "➡️", "Round trip" if is_round else "One-way", "ROUTE TYPE"),
    ]
    body = "".join(
        f'<div class="mcard"><div class="ico">{ico}</div>'
        f'<div class="val">{html.escape(val)}</div><div class="lab">{lab}</div></div>'
        for ico, val, lab in cards
    )
    return f'<div class="metrics">{body}</div>'


def journey_html(route_df: pd.DataFrame) -> str:
    rows = []
    for _, r in route_df.iterrows():
        nm = str(r["name"])
        is_ret = nm.startswith("↩️")
        num_cls = "num ret" if is_ret else "num"
        num = "↩" if is_ret else str(int(r["stop"]))
        rating = _num(r.get("rating"))
        rate = f"⭐ {rating:.1f} · " if rating is not None else ""
        fee = _num(r.get("entry_fee_inr")) or 0.0
        fee_chip = f"🎟 ₹{int(fee):,}" if fee > 0 else "🎟 free"
        kmn = _num(r.get("km_to_next")) or 0.0
        km_chip = "" if (is_ret or kmn == 0) else f"→ {kmn:,.0f} km"
        rows.append(
            f'<div class="stop"><div class="{num_cls}">{num}</div>'
            f'<div class="who"><div class="nm">{html.escape(nm)}</div>'
            f'<div class="meta">{html.escape(str(r.get("city", "")))} · {rate}{fee_chip}</div></div>'
            f'<div class="km">{km_chip}</div></div>'
        )
    return '<div class="journey">' + "".join(rows) + "</div>"


def render_day_cards(stay_plan: list, cityof: dict) -> None:
    day = 1
    for seg in stay_plan:
        label = f"DAY {day}" if seg["days"] == 1 else f"DAY {day}–{day + seg['days'] - 1}"
        day += seg["days"]
        place = seg["place"]
        town = seg.get("stay_town") or cityof.get(place, place)
        subs = []
        if seg.get("en_route"):
            subs.append("🚶 en-route: " + ", ".join(short(x, 38) for x in seg["en_route"]))
        warn = ""
        if seg.get("drive_km", 0) > LONG_DRIVE_KM:
            line = f"🚗 long drive ~{seg['drive_km']:,.0f} km — add buffer day(s)!"
            subs.append(line)
            warn = " warn"
        sub_html = "".join(f'<div class="sub{warn if "🚗" in s else ""}">{html.escape(s)}</div>' for s in subs)
        st.markdown(
            f'<div class="day"><div class="daychip">{label}</div>'
            f'<div class="daybody"><b>{html.escape(short(place, 70))}</b> · 🏨 stay: <b>{html.escape(town)}</b>{sub_html}</div></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------- #
#  Page                                                            #
# ---------------------------------------------------------------- #
st.markdown(HERO, unsafe_allow_html=True)

with st.sidebar:
    st.header("🧳 Trip settings")
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

    berhampur = names.index("Berhampur") if "Berhampur" in names else 0
    origin = st.selectbox("🅰️ Start point", names, index=berhampur, format_func=short)
    destination = st.selectbox("🅱️ End point", names, index=berhampur, format_func=short)
    if origin == destination:
        st.info("🔁 Start = End → planning a ROUND TRIP loop!")

    days = st.number_input("📅 Trip length (days)", 1, 30, 5)

    interests, stops = [], []
    if mode.startswith("🎯"):
        tokens = set()
        for cats in places["category"].fillna("").astype(str).str.split(";"):
            tokens.update(t.strip().title() for t in cats if t.strip() and t.strip() != "UNESCO")
        interests = st.multiselect("🎯 Your interests", sorted(tokens),
                                   default=sorted(tokens)[:2])
        n_places = st.slider("Max places to include", 3, 12, 6)
    else:
        stops = st.multiselect("🗺️ Places to visit (order optimized for you)",
                               names, format_func=short)

ready = bool(interests) if mode.startswith("🎯") else len(stops) >= 1
if not ready:
    st.warning("Pick at least one interest / stop in the sidebar to continue 🙂")
    st.stop()

if st.button("Plan my trip 🧭", type="primary"):
    with st.spinner("Recommending places → optimizing route → splitting days..."):
        try:
            if mode.startswith("🎯"):
                route_df, total_km, stay_plan = planner.plan(
                    origin, destination, interests, n_places=n_places, days=int(days))
            else:
                route_df, total_km, stay_plan = planner.plan_explicit(
                    origin, destination, stops, days=int(days))
        except (ValueError, KeyError, IndexError) as e:
            st.error(f"Couldn't plan that trip: {e}")
            st.stop()

    # Remember the plan — Streamlit re-runs this script on EVERY widget change,
    # so without this the itinerary would vanish as soon as the user edits
    # anything in the sidebar.
    st.session_state["last_plan"] = {
        "key": key, "route_df": route_df, "total_km": total_km,
        "stay_plan": stay_plan, "days": int(days),
    }

plan = st.session_state.get("last_plan")
if plan and plan["key"] == key:
    route_df, total_km, stay_plan = plan["route_df"], plan["total_km"], plan["stay_plan"]

    is_round = str(route_df.iloc[-1]["name"]).startswith("↩️")
    cityof = dict(zip(route_df["name"].astype(str), route_df["city"]))

    st.markdown(metrics_html(total_km, len(route_df), int(plan["days"]), is_round),
                unsafe_allow_html=True)

    # map (points of the journey)
    loc = planner.places.set_index(planner.places["name"].astype(str))[["lat", "lon"]]
    pts = route_df.assign(
        lat=route_df["name"].map(loc["lat"]).astype(float),
        lon=route_df["name"].map(loc["lon"]).astype(float),
    ).dropna(subset=["lat", "lon"])
    if not pts.empty:
        with st.container(height=430):
            st.map(pts, latitude="lat", longitude="lon", use_container_width=True)

    st.subheader("🗺️ Your route, stop by stop")
    st.markdown(journey_html(route_df), unsafe_allow_html=True)

    if stay_plan:
        st.subheader("📅 Day-wise plan with stays")
        render_day_cards(stay_plan, cityof)
        if is_round:
            ret = _num(route_df.iloc[-2]["km_to_next"]) or 0.0
            if ret > LONG_DRIVE_KM:
                st.warning(f"🚗 Return drive ≈ {ret:,.0f} km — add buffer days or consider flying back!")

    with st.expander("🗂️ View raw data table"):
        st.dataframe(route_df, use_container_width=True, hide_index=True)

    st.caption("ℹ️ Distances are straight-line (great-circle); road km are usually 20–30% more.")
elif plan:
    st.info("The sidebar changed — click **Plan my trip** to refresh your itinerary.")
else:
    st.info("👆 Set your trip in the sidebar, then click **Plan my trip**!")
