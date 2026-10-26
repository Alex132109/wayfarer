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
from src.daily_guide import build_daily_guide, essentials_list
from src.exports import google_maps_url, ics_calendar, save_trip_html
from src.food_recommender import HotelRecommender, load_side
from src.itinerary import LONG_DRIVE_KM, TripPlanner
from src.trip_money import estimate_budget

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


def money_html(money: dict) -> str:
    """Budget as metric cards — reuses the same .mcard design system."""
    label = money["label"]
    cards = [
        ("💰", f"₹{money['trip_pp']:,}", "TRIP / PERSON"),
        ("🆘", f"₹{money['emergency_pp']:,}", "EMERGENCY FUND PP"),
        ("👥", f"₹{money['trip_group'] + money['emergency_group']:,}", "GROUP (+FUND)"),
        (label.split()[0], label.split(maxsplit=1)[1], "TRIP STYLE"),
    ]
    body = "".join(
        f'<div class="mcard"><div class="ico">{ico}</div>'
        f'<div class="val">{html.escape(val)}</div><div class="lab">{lab}</div></div>'
        for ico, val, lab in cards
    )
    return f'<div class="metrics">{body}</div>'


def render_guide(days_out: list) -> None:
    """The ⭐ daily guide: time-boxed + budget-boxed schedule cards."""
    for d in days_out:
        with st.container(border=True):
            st.markdown(f"**Day {d['day']} — {d['town']}**  ·  📦 box: ~{d['hours']:.0f}h of sights")
            for i in d["items"]:
                line = f"`{i['time']}` {i['label']}"
                if i.get("max_time"):
                    line += f" · ⏱ {i['max_time']} (beyond this, next item gets skipped)"
                if i.get("try"):
                    line += f" · try: **{i['try']}**"
                st.markdown(line)


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

    # Phase 1 ML inputs — money, styles, transport, diet, phobias
    travellers = st.number_input("👥 Travellers", 1, 20, 2)
    style = st.selectbox("💎 Trip style",
                         ["budget", "economy", "comfort", "premium", "luxury", "super-luxury"], 2)
    mode = st.selectbox("🛺 Transport mode",
                        ["mixed", "car", "cab", "bike", "bus", "train", "flight"], 0)
    month = st.text_input("🗓️ Travel month (season-aware picks)", "Oct")
    diet = st.selectbox("🥗 Diet for food picks",
                        ["No preference", "Veg", "Vegan", "Eggetarian", "NonVeg"], 0)
    phobias = st.multiselect("😨 Phobia filters", ["heights", "dark", "water", "crowds"])

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
                    origin, destination, interests, n_places=n_places,
                    days=int(days), month=month or None)
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

    # --- 💰 budget (styles + emergency fund) ----------------------- #
    money = estimate_budget(int(plan["days"]), int(travellers), float(total_km),
                            mode=mode, style=style)
    st.markdown(money_html(money), unsafe_allow_html=True)

    # --- ⭐ daily guide (supersedes plain day cards) ---------------- #
    if stay_plan:
        foods = load_side("food", key)
        guide = build_daily_guide(
            planner.places, route_df, stay_plan, money,
            foods=foods, diet=None if diet == "No preference" else diet,
            phobias=phobias or None)
        st.subheader("⭐ Daily guide — time & budget boxed")
        render_guide(guide)

        if is_round:
            ret = _num(route_df.iloc[-2]["km_to_next"]) or 0.0
            if ret > LONG_DRIVE_KM:
                st.warning(f"🚗 Return drive ≈ {ret:,.0f} km — add buffer days or consider flying back!")

        # --- 🏨 hotel picks near each stay town --------------------- #
        hotels = load_side("hotels", key)
        if hotels is not None and not hotels.empty:
            hr = HotelRecommender().fit(hotels)
            towns = []
            for d in guide:
                if d["town"] not in towns:
                    towns.append(d["town"])
            per_night = money["stays"]["pp"] / max(money["stays"]["nights"], 1)
            st.subheader("🏨 Stay picks (budget-fit + one upgrade)")
            for t in towns:
                picks = hr.recommend(t, budget_pp_night=per_night, travellers=int(travellers))
                if not picks.empty:
                    with st.expander(f"🏨 {t} — room budget ≈ ₹{per_night * 2:,.0f} / night"):
                        for _, h in picks.iterrows():
                            st.markdown(f"**{h['name']}** · {h['style']} · "
                                        f"₹{h['price_per_night_inr']:,}/night · ⭐ {h['rating']}"
                                        f" — {h['notes']}")

        # --- 📤 take the plan with you ------------------------------ #
        st.subheader("📤 Take your plan with you")
        c1, c2, c3 = st.columns(3)
        c1.link_button("🗺️ Open route in Google Maps",
                       google_maps_url(route_df, planner.places))
        c2.download_button("📅 Download .ics calendar",
                           ics_calendar(stay_plan), "wayfarer_trip.ics", "text/calendar")
        inputs = {"origin": origin, "destination": destination,
                  "days": int(days), "travellers": int(travellers)}
        html_path = ROOT / "exports" / "wayfarer_trip.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        save_trip_html({"route_df": route_df, "total_km": total_km, "money": money,
                        "guide": guide, "essentials": essentials_list(
                            is_international=key in ("world", "japan"),
                            trip_days=int(days))}, inputs, html_path)
        c3.download_button("🖨️ Offline HTML itinerary",
                           html_path.read_text(encoding="utf-8"),
                           "wayfarer_itinerary.html", "text/html")

    with st.expander("🗂️ View raw data table"):
        st.dataframe(route_df, use_container_width=True, hide_index=True)

    st.caption("ℹ️ Distances are straight-line (great-circle); road km are usually 20–30% more.")
elif plan:
    st.info("The sidebar changed — click **Plan my trip** to refresh your itinerary.")
else:
    st.info("👆 Set your trip in the sidebar, then click **Plan my trip**!")
