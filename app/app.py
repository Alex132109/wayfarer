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
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# Make "src" importable no matter where streamlit is launched from
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.accounts import login, save_trip, signup, trip_history
from src.companion import (LANGUAGE_PACKS, battery_buddy, language_quiz,
                           leaderboard, location_share, sos_card)
from src.commerce import (ESIM_PLANS, book_hotel, buy_esim, cab_recommend,
                          esim_catalog, pay_group)
from src.data_loader import clean_places, find_data_file, haversine_km, load_places
from src.daily_guide import build_daily_guide, essentials_list
from src.exports import booking_links, google_maps_url, ics_calendar, save_trip_html
from src.food_recommender import HotelRecommender, load_side
from src.itinerary import LONG_DRIVE_KM, TripPlanner
from src import osm_places, weather
from src.squads import (add_expense, balances, create_group, group_info,
                        join_group, members as squad_members, split_payment)
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
  <span class="tag">👥 squads & split money</span><span class="tag">💳 demo payments (test mode)</span>
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


@st.cache_data(show_spinner="Loading 236k world cities (one-time)…")
def get_world_cities():
    """GeoNames cities500 — EVERY city on Earth ≥500 people, villages to
    capitals, with alternate names (Bombay→Mumbai, Cherrapunji→Sohra).
    Built by src/build_world_cities.py (free, no key). File is gitignored."""
    p = ROOT / "data" / "raw" / "cities_world.csv"
    return pd.read_csv(p) if p.exists() else None


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
    transport_mode = st.selectbox("🛺 Transport mode",
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
                            mode=transport_mode, style=style)
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

        # unique stay towns in visit order (used by weather + hotel picks below)
        towns = []
        for d in guide:
            if d["town"] and d["town"] not in towns:
                towns.append(d["town"])

        if is_round:
            ret = _num(route_df.iloc[-2]["km_to_next"]) or 0.0
            if ret > LONG_DRIVE_KM:
                st.warning(f"🚗 Return drive ≈ {ret:,.0f} km — add buffer days or consider flying back!")

        # --- 🌦️ LIVE weather at each stay town (E3 — the wishlist!) --- #
        tw_in = []
        for t in towns:
            m = planner.places[planner.places["city"].astype(str) == t]
            if len(m):
                r0 = m.iloc[0]
                tw_in.append({"town": t, "lat": float(r0["lat"]), "lon": float(r0["lon"])})
        tw = weather.trip_weather(tw_in[:6], timeout=6)
        if tw is not None:
            st.subheader("🌦️ Live weather at your stays (OpenWeather)")
            st.dataframe(tw, use_container_width=True, hide_index=True)
            st.caption("'Carry' = weather-driven essentials: rain → umbrella/raincoat, "
                       "heat → sunscreen/water, cold → layers.")

        # --- 🏨 hotel picks near each stay town --------------------- #
        hotels = load_side("hotels", key)
        if hotels is not None and not hotels.empty:
            hr = HotelRecommender().fit(hotels)
            per_night = money["stays"]["pp"] / max(money["stays"]["nights"], 1)
            st.subheader("🏨 Stay picks (budget-fit + one upgrade)")
            # 💰 prices change BY DATE — pick your dates once, every link below
            # opens the platform with them pre-filled → LIVE current prices.
            dc1, dc2 = st.columns(2)
            ci = dc1.date_input("Check-in", date.today() + timedelta(days=7),
                                key="ci")
            co = dc2.date_input("Check-out", date.today() + timedelta(days=9),
                                key="co")
            st.caption("Sample ₹ = our static budget estimate. Real hotel prices "
                       "change by date — tap a link to see LIVE prices & ratings "
                       "on the platform for your exact dates.")
            for t in towns:
                picks = hr.recommend(t, budget_pp_night=per_night, travellers=int(travellers))
                if not picks.empty:
                    with st.expander(f"🏨 {t} — room budget ≈ ₹{per_night * 2:,.0f} / night"):
                        for _, h in picks.iterrows():
                            bl = booking_links(h["name"], t, str(ci), str(co))
                            st.markdown(f"**{h['name']}** · {h['style']} · "
                                        f"sample ₹{h['price_per_night_inr']:,}/night · "
                                        f"⭐ {h['rating']} — {h['notes']}")
                            st.markdown(f"[💰 live price — Booking]({bl['booking']}) · "
                                        f"[🔍 compare — Google Hotels]({bl['google']}) · "
                                        f"[GoIbibo]({bl['goibibo']})")

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

    st.caption("ℹ️ Distances = REAL road km via OSRM when online (disk-cached); "
               "otherwise straight-line × 1.25 estimates.")
elif plan:
    st.info("The sidebar changed — click **Plan my trip** to refresh your itinerary.")
else:
    st.info("👆 Set your trip in the sidebar, then click **Plan my trip**!")

# ---------------------------------------------------------------- #
#  PHASE 2–3 DEMO — accounts · squads · companion · commerce         #
#  Everything below is demo/test-mode: SQLite accounts, simulated    #
#  payments (NO real money), seed leaderboard, simulated GPS.        #
# ---------------------------------------------------------------- #
st.divider()
st.subheader("🧑‍🤝‍🧑 Accounts · squads · companion · demo commerce")
st.caption("Demo mode — accounts in SQLite, payments captured in TEST mode "
           "(no real money moves), leaderboard seeded, GPS simulated.")

tab_acct, tab_squad, tab_buddy, tab_shop, tab_world = st.tabs(
    ["👤 Account", "👥 Squad & money", "🤝 Companion", "💳 Book & pay",
     "🌍 Any city on Earth"])

# ---------------- 👤 ACCOUNT: signup / login / history ------------- #
with tab_acct:
    user = st.session_state.get("user")
    if user is None:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**New here?**")
            su_name = st.text_input("Choose a username", key="su_name")
            su_pass = st.text_input("Choose a password", type="password", key="su_pass")
            if st.button("Sign up", key="btn_signup"):
                r = signup(su_name, su_pass)
                if r["ok"]:
                    st.success("Account created — now log in on the right!")
                else:
                    st.error(r["error"])
        with c2:
            st.markdown("**Returning?**")
            li_name = st.text_input("Username", key="li_name")
            li_pass = st.text_input("Password", type="password", key="li_pass")
            if st.button("Log in", key="btn_login"):
                r = login(li_name, li_pass)
                if r["ok"]:
                    st.session_state["user"] = r
                    st.rerun()
                else:
                    st.error(r["error"])
    else:
        st.success(f"Logged in as **{user['username']}** — your trip history:")
        if st.button("Log out"):
            st.session_state.pop("user", None)
            st.rerun()
        st.dataframe(trip_history(user["user_id"]), use_container_width=True,
                     hide_index=True)
        plan_now = st.session_state.get("last_plan")
        if plan_now and plan_now["key"] == key:
            if st.button("💾 Save my last planned trip to history"):
                route = plan_now["route_df"]
                last = str(route.iloc[-1]["name"]).replace("↩️ ", "")
                save_trip(user["user_id"], str(route.iloc[0]["name"]), last,
                          int(plan_now["days"]), float(plan_now["total_km"]), style)
                st.rerun()

# ---------------- 👥 SQUAD: groups + the 25k×5 payment ------------- #
with tab_squad:
    user = st.session_state.get("user")
    if user is None:
        st.info("Log in on the Account tab first — squads belong to users.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            gname = st.text_input("New squad name", "Japan Squad", key="sq_name")
            if st.button("➕ Create squad & get invite code"):
                r = create_group(gname, user["user_id"], user["username"])
                st.session_state["squad"] = r["group_id"]
        with c2:
            code = st.text_input("Or join with an invite code", key="sq_code")
            if st.button("🔗 Join squad"):
                r = join_group(code, user["user_id"], user["username"])
                if r["ok"]:
                    st.session_state["squad"] = r["group_id"]
                else:
                    st.error(r["error"])

        gid = st.session_state.get("squad")
        if gid:
            info = group_info(gid)
            st.success(f"👥 **{info['name']}** — invite code: `{info['invite_code']}` "
                       f"(share it, friends join like a WhatsApp group)")
            mdf = squad_members(gid)
            st.dataframe(mdf, use_container_width=True, hide_index=True)

            # 💸 THE wishlist scenario: admin pays 25k×5 ONCE, or each pays 25k
            st.markdown("**💸 Group payment (test-mode)**")
            p1, p2, p3 = st.columns(3)
            pp = p1.number_input("Per-person budget (₹)", 500, 500000, 25000,
                                 step=500, key="gp_pp")
            how = p2.selectbox("Who pays?",
                               ["admin pays all at once", "each pays their share"])
            ppl = p3.number_input("People", 1, 12, min(len(mdf), 12), key="gp_n")
            if st.button("💳 Capture payment (demo)"):
                style_ = "admin_all" if how.startswith("admin") else "each_own"
                orders = pay_group(pp, int(ppl), style_)
                total = sum(o["amount"] for o in orders) / 100
                st.success(f"Captured {len(orders)} order(s) — ₹{total:,.0f} collected "
                           f"(test mode: no real money moved)")

            # 📒 Splitwise-style expense tracker with net balances
            st.markdown("**📒 Squad expense tracker** (who owes whom)")
            e1, e2, e3 = st.columns([2, 1, 2])
            payer = e1.selectbox("Paid by", mdf["username"].tolist(), key="exp_payer")
            amt = e2.number_input("Amount (₹)", 0, 1000000, 8000, step=100, key="exp_amt")
            desc = e3.text_input("What for", "team dinner", key="exp_desc")
            if st.button("Add expense"):
                all_names = mdf["username"].tolist()
                r = add_expense(gid, payer, amt, desc, all_names)
                st.success(f"₹{amt:,.0f} split — ₹{r['share_each']:,.0f} each among "
                           f"{len(all_names)} members")
            st.dataframe(balances(gid), use_container_width=True, hide_index=True)
            st.caption("Positive net = squad owes them · negative = they owe.")

# ---------------- 🤝 COMPANION: leaderboard · language · safety ---- #
with tab_buddy:
    c1, c2 = st.columns(2)
    with c1:
        dest = st.selectbox("🏆 Leaderboard destination", ["japan", "meghalaya"],
                            key="lb_dest")
        st.dataframe(leaderboard(dest), use_container_width=True, hide_index=True)
        st.caption("Seed data + scoring model: execution 60% + under-budget 40%.")
    with c2:
        lang = st.selectbox("🗣️ Language crash course", list(LANGUAGE_PACKS.keys()),
                            key="lang_dest")
        for word, phrase in LANGUAGE_PACKS[lang].items():
            st.markdown(f"- **{word}** → {phrase}")

    st.markdown("**🧠 Quick quiz** — pick answers, then check")
    qs = language_quiz(lang)
    answers = [st.radio(f"{i + 1}. {q}", opts, key=f"quiz_{lang}_{i}", index=None,
                        horizontal=True)
               for i, (q, opts, _a) in enumerate(qs)]
    if st.button("Check my answers"):
        score = sum(1 for (_q, opts, a), ans in zip(qs, answers) if ans == opts[a])
        st.success(f"Score: {score}/{len(qs)} — "
                   f"{'great!' if score >= 3 else 're-read the pack above 🙂'}")

    st.markdown("**🔋 Battery buddy** — the wishlist rule: <20% → don't wander alone")
    levels = {}
    batt_cols = st.columns(5)
    for i, bc in enumerate(batt_cols, 1):
        levels[f"member{i}"] = bc.slider(f"member{i}", 0, 100, 70, key=f"bat{i}")
    alerts = battery_buddy(levels)
    for a in alerts:
        st.warning(a)
    if not alerts:
        st.success("All batteries ≥20% — everyone can explore today!")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📍 Location share** (simulated snapshot)")
        share_names = (squad_members(gid)["username"].tolist()
                       if st.session_state.get("squad")
                       else ["member1", "member2", "member3"])
        pts = {n: (35.0 + 0.01 * i, 135.0 + 0.02 * i) for i, n in enumerate(share_names)}
        st.dataframe(location_share(pts), use_container_width=True, hide_index=True)
        st.caption("Simulated — real live-sharing needs phone GPS + WebSocket (Phase 5).")
    with c2:
        st.markdown("**🆘 SOS card** — screenshot before the trip")
        st.json(sos_card(lang))

# ---------------- 💳 SHOP: bookings · eSIM · cabs (demo) ----------- #
with tab_shop:
    st.caption("Test-mode commerce — orders captured in demo storage; "
               "NO real money, NO real bookings.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🏨 Book a stay (demo)**")
        hotels = load_side("hotels", key)
        if hotels is None or hotels.empty:
            st.info("No hotels dataset for this destination yet.")
        else:
            hnames = hotels["name"].astype(str).tolist()
            hname = st.selectbox("Hotel from our picks", hnames, key="bk_hotel")
            row = hotels[hotels["name"].astype(str) == hname].iloc[0]
            price = _num(row["price_per_night_inr"]) or 0.0
            st.caption(f"{row.get('city', '')} · ⭐ {_num(row['rating']) or '–'} · "
                       f"₹{price:,.0f}/night")
            b1, b2 = st.columns(2)
            b_nights = b1.number_input("Nights", 1, 30, 3, key="bk_n")
            b_rooms = b2.number_input("Rooms", 1, 10, 2, key="bk_r")
            if price <= 0:
                st.warning("No price data for this hotel — pick another.")
            elif st.button("Book & pay (demo)"):
                guest = (st.session_state.get("user") or {}).get("username", "guest")
                b = book_hotel(hname, str(row.get("city", "")), b_nights, b_rooms,
                               price, guest)
                st.success(f"✅ {b['confirmation']} — {b['hotel']}: {b['rooms']} room(s) "
                           f"× {b['nights']} night(s) = ₹{b['total_inr']:,.0f} (test mode)")

    with c2:
        st.markdown("**📶 eSIM store (demo)**")
        esim_dest = st.selectbox("Where do you need data?", list(ESIM_PLANS.keys()),
                                 key="esim_dest")
        cat = esim_catalog(esim_dest)
        st.dataframe(cat, use_container_width=True, hide_index=True)
        plan_name = st.selectbox("Pick a plan", cat["plan"].tolist(), key="esim_plan")
        if st.button("Buy eSIM (demo)"):
            r = buy_esim(esim_dest, plan_name)
            st.success(f"✅ {r['activation_code']} — {r['plan']} for "
                       f"₹{r['paid_inr']:,.0f} (test mode)")

    st.markdown("**🚕 Cab recommendation** — cheapest vehicle that fits the group")
    c1, c2 = st.columns(2)
    cab_trav = c1.number_input("Travellers", 1, 12, 2, key="cab_trav")
    cab_km = c2.number_input("Km you'll drive today", 0, 2000, 200, key="cab_km")
    st.dataframe(cab_recommend(cab_trav, cab_km), use_container_width=True,
                 hide_index=True)

# ---------------- 🌍 EXPLORER: any city on Earth -------------------- #
with tab_world:
    cities = get_world_cities()
    if cities is None:
        st.info("One-time setup — run `.venv\\Scripts\\python src\\build_world_cities.py` "
                "to download the free GeoNames database: **236,731 cities**, "
                "tiny villages to big capitals (no API key, ~1 minute).")
    else:
        q = st.text_input("Type ANY city on Earth — tiny village or big capital",
                          "Cherrapunji")
        if q.strip():
            ql = q.strip().lower()
            # search official name OR alternate names (Bombay→Mumbai works!)
            hits = cities[(cities["name"].str.lower().str.contains(ql, regex=False))
                          | (cities["alt_names"].fillna("")
                             .str.lower().str.contains(ql, regex=False))]
            hits = hits.sort_values("population", ascending=False).head(12)
            if hits.empty:
                st.warning("No match — try another spelling.")
            else:
                labels = [f"{r['name']} ({r['country']}) · {int(r['population']):,} people"
                          for _, r in hits.iterrows()]
                pick = st.selectbox("Which one?", labels)
                row = hits.iloc[labels.index(pick)]
                lat, lon = float(row["lat"]), float(row["lon"])
                region = str(row["admin1"])
                if region in ("", "nan"):
                    region = "—"

                c1, c2, c3 = st.columns(3)
                c1.metric("📍 City", row["name"])
                c2.metric("🗺️ Region", f"{row['country']} · {region}")
                c3.metric("👥 Population", f"{int(row['population']):,}")
                st.map(pd.DataFrame([{"lat": lat, "lon": lon}]))

                # 🌦️ live weather NOW + 5-day forecast (free OpenWeather)
                w = weather.current(lat, lon, timeout=6)
                if w:
                    wc1, wc2, wc3, wc4 = st.columns(4)
                    wc1.metric("🌡️ Now", f"{w['temp_c']}°C", f"feels {w['feels_c']}°C")
                    wc2.metric("☁️ Condition", w["condition"])
                    wc3.metric("☔ Rain chance", f"{w['rain_chance_pct']}%")
                    wc4.metric("💨 Wind", f"{w['wind_kmh']} km/h")
                    fc = weather.forecast_daily(lat, lon, timeout=6)
                    if fc is not None:
                        st.dataframe(fc, use_container_width=True, hide_index=True)
                    carry = weather.day_essentials(w["temp_c"], w["rain_chance_pct"],
                                                   w["condition"])
                    if carry:
                        st.info("🎒 Carry today: " + " · ".join(carry))

                # 🏛️ nearby UNESCO World Heritage sites (real km, our haversine)
                wp = get_places("world")
                if wp is not None:
                    dists = np.array([haversine_km(lat, lon, float(a), float(b))
                                      for a, b in zip(wp["lat"], wp["lon"])])
                    near = wp.assign(km=dists).query("km <= 250").sort_values("km")
                    if not near.empty:
                        st.markdown("**🏛️ World Heritage sites nearby (real km)**")
                        st.dataframe(near[["name", "city", "km"]].head(8),
                                     use_container_width=True, hide_index=True)

                # 🏨 REAL stays around the city (OpenStreetMap, cached)
                hs = osm_places.hotels_near(lat, lon, radius_km=25,
                                            timeout=20, budget_s=30)
                if hs is not None and not hs.empty:
                    st.markdown(f"**🏨 Real stays mapped around {row['name']}** "
                                f"(OpenStreetMap · {len(hs)} found)")
                    # 💰 same live-price rule as everywhere: OSM has no prices,
                    # so every stay gets a Booking deep-link with YOUR dates.
                    ws1, ws2 = st.columns(2)
                    wci = ws1.date_input("Check-in", date.today() + timedelta(days=7),
                                         key="wci")
                    wco = ws2.date_input("Check-out", date.today() + timedelta(days=9),
                                         key="wco")
                    hs_live = hs.assign(price_link=[
                        booking_links(n, str(row["name"]), str(wci), str(wco))["booking"]
                        for n in hs["name"]])
                    st.dataframe(
                        hs_live[["name", "kind", "price_link"]],
                        use_container_width=True, hide_index=True,
                        column_config={"price_link": st.column_config.LinkColumn(
                            "💰 live price (your dates)")})
                    st.caption("Names/locations are REAL OSM data. Prices aren't in OSM "
                               "— tap 💰 to see LIVE prices & ratings on Booking.com "
                               "with your dates pre-filled (hotel costs change by date, "
                               "so we never freeze them).")
                    st.map(hs, latitude="lat", longitude="lon",
                           use_container_width=True)

                sg = osm_places.sights_near(lat, lon, radius_km=25,
                                            timeout=20, budget_s=30)
                if sg is not None and not sg.empty:
                    with st.expander(f"🏛️ {len(sg)} real sights mapped around "
                                     f"{row['name']}"):
                        st.dataframe(sg[["name", "kind"]], use_container_width=True,
                                     hide_index=True)
