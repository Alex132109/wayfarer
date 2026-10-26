"""
🧭 Wayfarer — pytest suite  (the 15/10 bar: every module is PROVEN, not hoped)

Run:  .venv\\Scripts\\python -m pytest tests -q
CI runs this on every push (see .github/workflows/ci.yml).

NOTE: tests never touch the network — OSRM gets a monkeypatched offline
fallback so CI is deterministic and fast.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.itinerary as it
from src import osm_places, weather
from src.data_loader import clean_places, find_data_file, haversine_km, load_places
from src.daily_guide import build_daily_guide, essentials_list
from src.exports import booking_links
from src.food_recommender import FoodRecommender, HotelRecommender, load_side
from src.itinerary import TripPlanner
from src.recommender import PlaceRecommender
from src.router import RouteOptimizer
from src.trip_money import estimate_budget
from src.trip_plan import TripPlan

MEGHALAYA_STOPS = ["Umiam Lake", "Shillong (Police Bazar & Ward's Lake)",
                   "Cherrapunji (Sohra) Waterfalls & Caves",
                   "Dawki (Umngot River Boating)", "Krem Chympe Cave"]


@pytest.fixture(scope="session", autouse=True)
def offline_osrm():
    """Force the offline fallback path so no test ever waits on the network.
    Patch the name itinerary.py actually USES (it binds the import), and
    restore it afterwards."""
    original = it.road_distance_matrix
    it.road_distance_matrix = lambda df, timeout=20: None
    yield
    it.road_distance_matrix = original


@pytest.fixture(scope="session")
def meghalaya():
    return clean_places(load_places(find_data_file("meghalaya")))


@pytest.fixture(scope="session")
def planner(meghalaya):
    return TripPlanner(meghalaya)


@pytest.fixture(scope="session")
def india():
    return clean_places(load_places(find_data_file("india")))


# ---------------------------------------------------------------- #
#  Data layer                                                        #
# ---------------------------------------------------------------- #
def test_haversine_known_distance():
    """Delhi (28.61, 77.21) → Agra (27.17, 78.04) is ≈ 180 km — the formula
    must land within ±25 km or every route in the project is wrong."""
    km = haversine_km(28.6139, 77.2090, 27.1739, 78.0399)
    assert 150 <= km <= 210


def test_find_data_file_prefers_core_places_files():
    """food_/hotels_ CSVs also mention 'india' — the finder must still
    return the CORE places dataset."""
    p = find_data_file("india")
    assert p.name.lower().startswith("places_")


def test_clean_places_guarantees_standard_columns():
    """A dataset missing rating/fees must load — never crash downstream."""
    raw = pd.DataFrame([
        {"name": "A", "lat": 21.0, "lon": 71.0},
        {"name": "B", "lat": 22.0, "lon": 72.0},
    ])
    out = clean_places(raw)
    for col in ("name", "city", "category", "rating", "entry_fee_inr",
                "avg_time_hours", "best_time"):
        assert col in out.columns


def test_clean_places_drops_garbage_coordinates():
    """Text lats, invalid ranges → those rows gone, valid rows survive."""
    messy = pd.DataFrame([
        {"name": "bad-lat", "lat": "not-a-number", "lon": 78.0},
        {"name": "bad-range", "lat": 20.2, "lon": 9314.0},
        {"name": "valid", "lat": 21.0, "lon": 71.0},
    ])
    out = clean_places(messy)
    assert list(out["name"]) == ["valid"]


def test_clean_places_empty_raises_clear_error():
    with pytest.raises(ValueError, match="coordinates"):
        clean_places(pd.DataFrame([{"name": "x", "lat": "abc", "lon": "def"}]))


# ---------------------------------------------------------------- #
#  Recommender                                                       #
# ---------------------------------------------------------------- #
def test_recommender_plural_matching(india):
    """'temples' (plural) must find Meenakshi/Golden Temple (singular tags)."""
    rec = PlaceRecommender().fit(india)
    out = rec.recommend(["temples"], top_n=5)
    assert not out.empty
    assert out["category"].str.contains("Temple").any()


def test_recommender_zero_score_filter(india):
    """Gibberish interests → EMPTY result (never irrelevant noise)."""
    rec = PlaceRecommender().fit(india)
    assert rec.recommend(["quantum", "chromodynamics"]).empty


def test_corridor_filter_scales_to_real_data(india):
    """REAL-data regression (325-place dataset): Delhi→Agra with temple/history
    interests MUST stay in the corridor. Widened-search bug it pins: the old
    rescue re-picked by match score and produced a 4,614 km Delhi→Karnataka→
    Odisha→Agra 'route'."""
    planner = TripPlanner(india)
    route, total, _ = planner.plan("India Gate", "Taj Mahal",
                                   ["Temple", "Historical"], n_places=5, days=3)
    assert total < 1000, f"corridor filter failed: {total:.0f} km"
    assert len(route) >= 3


# ---------------------------------------------------------------- #
#  Router                                                            #
# ---------------------------------------------------------------- #
def test_round_trip_closes_loop(planner, offline_osrm):
    route_df, total, _ = planner.plan_explicit(
        "Berhampur", "Berhampur", MEGHALAYA_STOPS, days=5)
    assert str(route_df.iloc[-1]["name"]).startswith("↩️")
    assert total > 0


def test_two_opt_never_worsens(planner):
    """2-opt is an IMPROVER: result km ≤ greedy km, always."""
    router = RouteOptimizer(planner.places)
    o, d = router.find_place("Berhampur"), router.find_place("Umiam Lake")
    cand = [router.find_place(s) for s in MEGHALAYA_STOPS[1:]]
    greedy = router.greedy_route(o, d, cand)
    improved = router.two_opt(list(greedy))
    legs_g = sum(router._km(greedy[k], greedy[k + 1]) for k in range(len(greedy) - 1))
    legs_i = sum(router._km(improved[k], improved[k + 1]) for k in range(len(improved) - 1))
    assert legs_i <= legs_g + 1e-6


# ---------------------------------------------------------------- #
#  Money                                                             #
# ---------------------------------------------------------------- #
def test_styles_are_monotonic():
    pps = [estimate_budget(5, 2, 2104, "car", s)["trip_pp"]
           for s in ("budget", "economy", "comfort", "premium", "luxury", "super-luxury")]
    assert pps == sorted(pps), "each style tier must cost ≥ the tier below"


def test_emergency_fund_is_10_percent():
    m = estimate_budget(days=5, travellers=2, total_km=2104, mode="car")
    assert m["emergency_pp"] == round(m["trip_pp"] * 0.10)


# ---------------------------------------------------------------- #
#  Food & hotels                                                     #
# ---------------------------------------------------------------- #
def test_food_diet_filter_is_hard():
    """Vegan requests must NEVER surface a NonVeg dish."""
    f = FoodRecommender().fit(load_side("food", "japan"))
    out = f.recommend("Tokyo", diet="Vegan", interests=["food"])
    assert not out.empty
    assert out["diet"].str.contains("Vegan").all()
    assert not out["diet"].str.contains("NonVeg").any()


def test_hotel_upsell_is_within_130pct():
    """The 'a little more' pick must not blow the budget by 30%+."""
    h = HotelRecommender().fit(load_side("hotels", "japan"))
    picks = h.recommend("Tokyo", budget_pp_night=3100, travellers=2)
    room_budget = 3100 * 2
    assert (picks["price_per_night_inr"] <= room_budget * 1.3).all()


# ---------------------------------------------------------------- #
#  Daily guide + plan editor                                         #
# ---------------------------------------------------------------- #
def test_guide_days_and_override(planner):
    money = {"per_meal": {"breakfast": 200, "lunch": 300, "dinner": 300}}
    _, _, stay = planner.plan_explicit("Berhampur", "Berhampur", MEGHALAYA_STOPS, days=5)
    days = build_daily_guide(planner.places, planner.places.head(0),
                             stay, money, overrides={"1": {"breakfast": 600}})
    assert len(days) == 5
    b = [i for i in days[0]["items"] if "breakfast" in i["label"]][0]
    assert "600" in b["label"]


def test_essentials_international_vs_domestic():
    intl = essentials_list(is_international=True)["documents"]
    dom = essentials_list(is_international=False)["documents"]
    assert any("passport" in d for d in intl)
    assert not any("passport" in d for d in dom)


def test_tripplan_edit_recomputes_everything(planner):
    plan = TripPlan(planner, origin="Berhampur", destination="Berhampur",
                    stops=MEGHALAYA_STOPS, days=5, travellers=5, mode="car")
    before = plan.summary()["money"]["trip_group"]
    plan.edit("style", "super-luxury")
    after = plan.summary()["money"]["trip_group"]
    assert after > before, "style edit must rescale the whole budget"


def test_tripplan_skip_shrinks_route(planner):
    plan = TripPlan(planner, origin="Berhampur", destination="Berhampur",
                    stops=MEGHALAYA_STOPS, days=5, travellers=2, mode="car")
    before = len(plan.summary()["route_df"])
    plan.edit("skip_places", ["Krem Chympe Cave"])
    assert len(plan.summary()["route_df"]) < before


def test_tripplan_rejects_unknown_input(planner):
    with pytest.raises(ValueError):
        TripPlan(planner, not_a_real_key=1)


# ---------------------------------------------------------------- #
#  Phase 2–3: accounts · squads · companion · commerce (demo-mode)   #
# ---------------------------------------------------------------- #
def test_signup_login_roundtrip(tmp_path):
    """Accounts: signup → duplicate refused → login ok → wrong pw refused."""
    from src.accounts import login, signup
    db = tmp_path / "acct.db"
    assert signup("aditi", "trip123", db)["ok"] is True
    assert signup("aditi", "again1", db)["ok"] is False
    assert login("aditi", "trip123", db)["ok"] is True
    assert login("aditi", "WRONG", db)["ok"] is False


def test_squad_invite_split_and_balances(tmp_path):
    """Squads: invite-code join + the 25k×5 math + Splitwise cancellation."""
    from src.accounts import signup
    from src.squads import (add_expense, balances, create_group, join_group,
                            split_payment)
    db = tmp_path / "squad.db"
    ids = [signup(f"member{i}", "pass1234", db)["user_id"] for i in range(1, 3)]
    g = create_group("Japan Squad", ids[0], "member1", db)
    assert join_group(g["invite_code"], ids[1], "member2", db)["ok"] is True
    s = split_payment(25000, 5)
    assert s["admin_all"]["amount"] == 125000 == s["each_own"]["total"]
    add_expense(g["group_id"], "member1", 6000, "dinner", ["member1", "member2"], db)
    b = balances(g["group_id"], db)
    assert abs(b["net"].sum()) < 0.01, "balances must cancel to zero"


def test_leaderboard_sorted_by_score():
    from src.companion import leaderboard
    lb = leaderboard("japan")
    assert not lb.empty and lb["score"].is_monotonic_decreasing


def test_battery_buddy_flags_low_power():
    from src.companion import battery_buddy
    alerts = battery_buddy({"a": 15, "b": 85})
    assert len(alerts) == 1 and "a" in alerts[0]


def test_demo_payment_blocks_double_capture():
    from src.commerce import capture, create_order
    o = create_order(25000, "test")
    assert o["amount"] == 2_500_000, "gateways count money in paise"
    assert capture(o["id"])["status"] == "paid"
    with pytest.raises(ValueError):
        capture(o["id"])                      # second capture must fail


def test_pay_group_25k_x5_both_ways():
    from src.commerce import pay_group
    admin = pay_group(25000, 5, how="admin_all")
    each = pay_group(25000, 5, how="each_own")
    assert len(admin) == 1 and admin[0]["amount"] == 125000 * 100
    assert len(each) == 5 and sum(o["amount"] for o in each) == 125000 * 100


def test_cab_recommend_fits_group_cheapest_first():
    from src.commerce import cab_recommend
    cabs = cab_recommend(5, day_km=200)
    assert (cabs["fits"] >= 5).all()
    assert cabs["rate/km"].is_monotonic_increasing


def test_esim_catalog_and_demo_buy():
    from src.commerce import buy_esim, esim_catalog
    cat = esim_catalog("japan")
    assert not cat.empty
    bought = buy_esim("japan", cat.iloc[0]["plan"])
    assert bought["activation_code"].startswith("ESIM-")


def test_website_runs_end_to_end():
    """Streamlit's official AppTest — runs app.py exactly like a browser
    would, then drives the signup widget. Catches any runtime error in the
    site script (a plain HTTP-200 check can NOT do that)."""
    import uuid
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app" / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception, f"app.py raised: {at.exception}"

    uname = "smoke_" + uuid.uuid4().hex[:6]
    at.text_input(key="su_name").set_value(uname)
    at.text_input(key="su_pass").set_value("trip123")
    at.button(key="btn_signup").click()
    at.run()
    assert not at.exception
    assert any("created" in s.value for s in at.success), list(at.success)


# ================================================================ #
#  E3 weather — offline tests (monkeypatch the network call)        #
# ================================================================ #
def test_weather_day_essentials_rules():
    """The carry-item rule engine, pinned without any network."""
    assert "umbrella" in " ".join(weather.day_essentials(24, 80)).lower()
    assert "sunscreen" in " ".join(weather.day_essentials(34, 0)).lower()
    assert "jacket" in " ".join(weather.day_essentials(5, 0)).lower()
    assert "gloves" in " ".join(weather.day_essentials(-2, 0, "snow")).lower()
    assert weather.day_essentials(24, 0) == []          # pleasant & dry → nothing


def test_weather_offline_stays_quiet(monkeypatch):
    """No key / no network → every function returns None. The app must
    NEVER crash because a weather server is down (graceful degradation)."""
    monkeypatch.setattr(weather, "api_key", lambda: None)
    assert weather.current(28.6, 77.2) is None
    assert weather.forecast_daily(28.6, 77.2) is None
    assert weather.trip_weather(
        [{"town": "Delhi", "lat": 28.6, "lon": 77.2}]) is None


def test_weather_current_parses_canned(monkeypatch):
    canned = {"main": {"temp": 28.04, "feels_like": 30.0, "humidity": 40},
              "weather": [{"description": "clear sky"}],
              "wind": {"speed": 3.5}}                     # km/h = 3.6 × m/s
    monkeypatch.setattr(weather, "api_key", lambda: "test-key")
    monkeypatch.setattr(weather, "_fetch_json", lambda url, timeout=20: canned)
    w = weather.current(28.6, 77.2)
    assert w["temp_c"] == 28.0 and w["feels_c"] == 30.0
    assert w["condition"] == "Clear Sky"
    assert w["rain_chance_pct"] == 0 and w["wind_kmh"] == 13
    assert w["humidity"] == 40


def test_weather_forecast_aggregates_3h_into_days(monkeypatch):
    """The free forecast = 40 × 3-hourly rows → we MIN/MAX/SUM them per day."""
    canned = {"list": [
        {"dt_txt": "2027-01-01 03:00:00",
         "main": {"temp": 20, "temp_min": 18, "temp_max": 22},
         "pop": 0.4, "rain": {"3h": 1.0},
         "weather": [{"description": "light rain"}]},
        {"dt_txt": "2027-01-01 12:00:00",
         "main": {"temp": 26, "temp_min": 24, "temp_max": 28},
         "pop": 0.0, "weather": [{"description": "clear sky"}]},
        {"dt_txt": "2027-01-02 09:00:00",
         "main": {"temp": 15, "temp_min": 12, "temp_max": 17},
         "pop": 0.9, "rain": {"3h": 5.0},
         "weather": [{"description": "moderate rain"}]},
    ]}
    monkeypatch.setattr(weather, "api_key", lambda: "test-key")
    monkeypatch.setattr(weather, "_fetch_json", lambda url, timeout=20: canned)
    fc = weather.forecast_daily(25.3, 91.6, days=5)
    assert fc is not None and len(fc) == 2
    r1 = fc.iloc[0]
    assert r1["min_c"] == 18.0 and r1["max_c"] == 28.0     # min/max across entries
    assert r1["rain_mm"] == 1.0 and r1["rain_chance_pct"] == 40
    assert fc.iloc[1]["rain_mm"] == 5.0 and fc.iloc[1]["rain_chance_pct"] == 90


# ================================================================ #
#  OSM stays/sights — offline parsing of canned Overpass elements    #
# ================================================================ #
def test_osm_to_df_skips_unnamed_and_reads_ways():
    """Nodes carry lat/lon directly; ways carry a `center` object; unnamed
    objects are useless for a traveller and must be dropped."""
    elements = [
        {"lat": 25.5, "lon": 91.8,
         "tags": {"name": "Ri Kynjai", "tourism": "hotel"}},
        {"center": {"lat": 25.6, "lon": 91.9},
         "tags": {"name": "Old Fort", "historic": "castle"}},
        {"lat": 25.7, "lon": 91.8, "tags": {"tourism": "hotel"}},  # unnamed → skip
    ]
    df = osm_places._to_df(elements)
    assert len(df) == 2
    assert "Ri Kynjai" in set(df["name"]) and "Old Fort" in set(df["name"])
    assert set(df["kind"]) == {"hotel", "castle"}
    assert df["lat"].between(-90, 90).all() and df["lon"].between(-180, 180).all()


def test_osm_offline_stays_quiet(monkeypatch):
    """No network → hotels_near/sights_near return None (feature stays quiet)."""
    monkeypatch.setattr(osm_places, "_fetch",
                        lambda q, timeout=90, budget_s=60: None)
    assert osm_places.hotels_near(25.58, 91.89) is None
    assert osm_places.sights_near(28.61, 77.21) is None


# ================================================================ #
#  💰 Live-price booking links (the anti-frozen-price rule)          #
# ================================================================ #
def test_booking_links_carry_dates_and_platforms():
    bl = booking_links("Ri Kynjai", "Shillong", "2027-01-10", "2027-01-12")
    assert bl["booking"].startswith("https://www.booking.com/searchresults.html")
    assert "checkin=2027-01-10" in bl["booking"]
    assert "checkout=2027-01-12" in bl["booking"]
    assert bl["google"].startswith("https://www.google.com/travel/search?q=")
    assert bl["goibibo"].startswith("https://www.goibibo.com/search?q=")
    # without dates → plain search link, no stale date params
    assert "checkin=" not in booking_links("Ri Kynjai")["booking"]
    # names get URL-encoded (spaces → %20 etc.)
    encoded = booking_links("Hotel Anand", "Guwahati")["google"]
    assert "Hotel%20Anand" in encoded


# ================================================================ #
#  🌍 Worldwide city database — runs ONLY if the file was built locally   #
# ================================================================ #
@pytest.mark.skipif(not (ROOT / "data" / "raw" / "cities_world.csv").exists(),
                    reason="30 MB GeoNames file is gitignored — "
                           "build it via src/build_world_cities.py")
def test_world_cities_database():
    w = pd.read_csv(ROOT / "data" / "raw" / "cities_world.csv")
    assert len(w) > 150_000                      # every city ≥500 people
    assert w["lat"].between(-90, 90).all() and w["lon"].between(-180, 180).all()
    names = set(w["name"].astype(str).str.lower())
    assert "shanghai" in names and "london" in names and "tokyo" in names
    # alt-name search: "Cherrapunji" must be findable under Sohra
    alts = w["alt_names"].fillna("").astype(str).str.lower()
    assert alts.str.contains("cherrapunji", regex=False).any()
