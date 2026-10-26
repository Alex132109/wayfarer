# 🧭 Wayfarer

![Python](https://img.shields.io/badge/python-3.14-blue)
![Tests](https://img.shields.io/badge/tests-28%20passing-brightgreen)
![ML](https://img.shields.io/badge/ML-TF--IDF%20%2B%20hybrid%20scoring-orange)
![Roads](https://img.shields.io/badge/distances-real%20road%20km%20(OSRM)-9cf)

**AI-powered trip planner — India first, then the world.**
Tell Wayfarer *where*, *how many days*, *your budget* and *your vibe* — it plans 2–3 optimized
day-wise itineraries with recommended hotels, food and places, so you travel the smart way.

> **Phase 1 → India. Phase 2 → Worldwide.**

---

## ✨ MVP Features

| Input | Output |
|-------|--------|
| Destination city / region | 2–3 itinerary options |
| Number of days (2–3+) | Day-wise plan: places ordered by shortest travel route |
| Budget (₹) | Hotel recommendations matched to budget |
| Interests (food, adventure, history, beaches...) | Food & local picks near your route |

## 🧠 How it works

```
                    ┌─────────────────────────────────────────┐
   User  ───────▶   │   city · days · budget · interests      │
                    └───────────────┬─────────────────────────┘
                                    │
              ┌─────────────────────┼──────────────────────────┐
              ▼                     ▼                          ▼
   ┌────────────────────┐  ┌───────────────────┐  ┌─────────────────────┐
   │  1. RECOMMENDER    │  │  2. ROUTER        │  │  3. STAY & FOOD     │
   │  Content-based     │  │  Day clustering + │  │  Budget filter +    │
   │  filtering (ML)    │  │  nearest-neighbor │  │  rating-relevance   │
   │  → picks the places│  │  route ordering   │  │  scoring            │
   └─────────┬──────────┘  └─────────┬─────────┘  └──────────┬──────────┘
             └───────────────────────┼───────────────────────┘
                                     ▼
                    ┌─────────────────────────────────────────┐
                    │   2–3 ready-made itineraries (web app)  │
                    └─────────────────────────────────────────┘
```

**What you'll learn while building each module:**

1. **Recommender** → content-based filtering, TF-IDF vectors, cosine similarity (your first ML model!)
2. **Router** → the Traveling Salesman Problem, greedy nearest-neighbor heuristic, 2-opt improvement
3. **Web app** → Streamlit (UI + backend wired together)

---

## 🗓️ 4-Week Roadmap

### Week 1 — Foundations & Data ✅ *you are here*
- [x] Project skeleton created
- [ ] Create Kaggle account → download 1–2 India travel datasets (see **Datasets** below)
- [ ] Put CSVs into `data/raw/`
- [ ] Run `python src/data_loader.py` and explore the data
- [ ] (Refresher) pandas basics: `read_csv`, filtering, `groupby`

### Week 2 — The Recommender (your first ML model 🎉) ✅ DONE
- [x] Fill in the TODOs in `src/recommender.py`
- [x] Convert place text (tags + descriptions) into TF-IDF vectors
- [x] Rank places by cosine similarity to user interests
- [x] Test: `interests = ["beach", "adventure"]` → Goa showed up 🏖️

### Week 3 — Route Optimization 🗺️ ✅ CORE DONE
- [x] Order places origin → destination (greedy detour rule + 2-opt)
- [x] Corridor filter — drops far-off candidates (no Mumbai on a Delhi→Agra trip)
- [x] Round trips (start = end) — e.g. Berhampur → Meghalaya loop → Berhampur
- [x] Day-wise plan with stay allocation (5 days → 1 Shillong · 2 Sohra · 1 Dawki · 1 caves)
- [x] Long-drive warnings (~990 km legs flagged with buffer-day advice)
- [ ] Generate 2–3 itinerary variants ("Relaxed" vs "Packed")
- [ ] Add hotels & food recommendations per itinerary

### Week 4 — Web App & Deploy ✅ APP DONE
- [x] Build the UI in Streamlit (`app/app.py`) — country picker, interests OR own stops,
      start/end + days → route table with km per leg, day-wise stays, map, warnings
- [ ] Deploy free on **Streamlit Community Cloud** or **Hugging Face Spaces**
- [ ] Write a short project report / LinkedIn post with screenshots

### Phase 1 — "Planner Pro" (the ML wishlist) ✅ BUILT
- [x] Budget engine — 6 trip style tiers (budget → super-luxury) with cost multipliers
      + meal caps + intercity planning rates (`src/trip_money.py`)
- [x] Food recommender — second ML model! TF-IDF dish matching with hard diet
      filters (veg / vegan / eggetarian) (`src/food_recommender.py`)
- [x] Hotel recommender — budget-fit stays + ONE honest "a little more" upsell
- [x] Daily guide — time-boxed + budget-boxed schedules: every sight gets a MAX
      stay time ('max 1h15 — beyond this the next itinerary item gets skipped')
      (`src/daily_guide.py`)
- [x] Phobia filters — heights / dark / water / crowds → warn + skip places
- [x] Essentials checklist — documents + climate packing hints,
      domestic vs foreign aware (`essentials_list`)
- [x] Editable `TripPlan` — pass `stops` or `interests`; edit anything
      (`style`, `days`, `travellers`, `diet`, `skip_places`) → everything recomputes
      (`src/trip_plan.py`)
- [x] Real road km via **OSRM** — one free API call per trip, disk-cached,
      graceful offline fallback (`src/data_loader.py`)
- [x] **Hybrid recommender** scoring — interests 55% + rating 20% + in-season 15%
      + road-proximity 10% (`HYBRID_WEIGHTS` in `src/itinerary.py`)
- [x] Exports — Google Maps route link, .ics calendar, offline printable
      HTML itinerary (`src/exports.py`)

### Phase 2 — "Accounts & Squads" ✅ BUILT (demo-mode)
- [x] User database — sign-up/login with salted-hashed passwords, trip history
      (`src/accounts.py`, SQLite in `data/wayfarer.db` — gitignored)
- [x] Groups with invite codes — solo · duo · squads; join like WhatsApp
      (`src/squads.py`)
- [x] **Group payments, both ways** — admin pays 25k×5 = ₹1,25,000 once,
      OR all 5 pay ₹25,000 each in-site (`split_payment` + demo capture)
- [x] Splitwise-style expense tracker — add expenses, net balances per member
- [x] Leaderboard per destination — scoring model: execution 60% +
      under-budget 40% (seed data, `src/companion.py`)

### Phase 3 — "Travel Companion + Commerce" ✅ BUILT (demo-mode)
- [x] Language crash course packs + mini quiz (Japan 🇯🇵, India 🇮🇳)
- [x] Battery buddy — <20% → "don't wander alone, buddy rule" alerts
- [x] Location share — simulated snapshot (real GPS needs Phase 5 infra)
- [x] SOS cards — police/ambulance/tourist helpline per destination
- [x] Demo payments — Razorpay-shaped flow: `create_order` → `capture`
      (test mode, amounts in paise, double-capture blocked) (`src/commerce.py`)
- [x] Hotel bookings with confirmation codes (test mode)
- [x] eSIM store — plans per destination with demo purchase
- [x] Cab recommender — cheapest vehicle that fits the group + long-day flags

> ⚠️ **Demo-mode honesty:** payments/bookings/eSIM purchases are simulated
> test-mode flows (no real money, no real compliance). Live GPS needs phone
> infra. Weather day-cards need your free OpenWeather key. Everything else runs
> for real, offline, today.

---

## 📁 Project Structure

```
wayfarer/
├── README.md                  ← you are here
├── requirements.txt           ← dependencies
├── .gitignore
├── data/
│   ├── raw/                   ← put your Kaggle CSVs here
│   ├── sample/                ← starter datasets (work from Day 1, no downloads)
│   │   ├── places_india_sample.csv
│   │   ├── places_meghalaya_trip.csv
│   │   ├── places_japan_sample.csv
│   │   ├── food_india_sample.csv        ← dish tips: dish, diet, price, rating
│   │   ├── food_japan_sample.csv
│   │   ├── hotels_india_sample.csv      ← stays: price/night, style, rating
│   │   └── hotels_japan_sample.csv
│   └── processed/             ← cleaned data (generated)
├── src/
│   ├── data_loader.py         ← load + clean + distance math (working ✅)
│   ├── build_world_dataset.py ← downloads worldwide UNESCO data (Phase 2 ✨)
│   ├── recommender.py         ← place recommender — first ML model (✅ done)
│   ├── router.py              ← route optimizer: greedy + 2-opt + round trips (✅)
│   ├── itinerary.py           ← trip planner brain: corridor filter, days & stays (✅)
│   ├── trip_money.py          ← budget engine: trip styles, meal caps, emergency fund (✅)
│   ├── food_recommender.py    ← food + hotel recommenders — second ML model (✅)
│   ├── daily_guide.py         ← daily guide builder: phobia filters, essentials (✅)
│   ├── trip_plan.py           ← editable TripPlan: edit anything → recompute (✅)
│   ├── exports.py             ← Google Maps route, ICS calendar, offline HTML (✅)
│   ├── accounts.py            ← user DB: signup/login (salted SHA-256), trip history (✅)
│   ├── squads.py              ← groups, invite codes, 25k×5 payments, Splitwise (✅)
│   ├── companion.py           ← leaderboard, language packs, battery buddy, SOS (✅)
│   └── commerce.py            ← demo payments, bookings, eSIM store, cabs (✅)
├── tests/
│   └── test_wayfarer.py       ← pytest suite, 27 tests incl. end-to-end site test (✅)
└── app/
    └── app.py                 ← Streamlit web app (✅ done)
```

---

## 🚀 Quickstart

```bash
cd wayfarer

# 1. Create a virtual environment (one-time)
python -m venv .venv
.venv\Scripts\activate          # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test the data pipeline with the sample dataset
python src\data_loader.py

# 4. Launch the website! 🌐
.venv\Scripts\streamlit run app\app.py

# 5. Phase 1–3 ML modules (each is runnable + self-checking)
.venv\Scripts\python src\trip_money.py       # budget engine + trip style tiers
.venv\Scripts\python src\food_recommender.py # food + hotel recommenders
.venv\Scripts\python src\daily_guide.py      # daily guide builder
.venv\Scripts\python src\trip_plan.py        # editable TripPlan (the full demo!)
.venv\Scripts\python src\accounts.py         # signup/login + trip history (demo DB)
.venv\Scripts\python src\squads.py           # squads + 25k×5 payments + Splitwise
.venv\Scripts\python src\companion.py        # leaderboard, language packs, SOS
.venv\Scripts\python src\commerce.py         # demo payments, bookings, eSIM, cabs

# 6. Run the test suite
.venv\Scripts\python -m pytest tests -q      # 27 tests, no network needed
```

If that prints a nice table of Indian destinations — you're ready. 🎉

---

## 📊 Datasets (Week 1 goal)

### 🇮🇳 REAL India data — 325 places, 33 states ✅ BUILT

`data/raw/places_india.csv` is generated from the Kaggle dataset
["Top Indian Places to Visit"](https://www.kaggle.com/datasets/dhrubangtalukdar/top-indian-places-to-visit-indian-tourism)
(credit: Kaggle user *dhrubangtalukdar*), with GPS coordinates geocoded via the free
OpenStreetMap **Nominatim** API (results disk-cached forever in `data/cache/`):

```bash
.venv\Scripts\python src\build_india_dataset.py   # needs ~/.kaggle/kaggle.json
```

The pipeline: **download → clean → enrich (geocode) → save** — and `find_data_file`
automatically serves the real file instead of the sample (raw/ wins over sample/).

### Starter sample (works from Day 1, no downloads)

Search on [Kaggle](https://www.kaggle.com/datasets) for:

- `"tourist attractions India csv"`
- `"India travel destinations dataset"`
- `"tripadvisor India attractions"`

**Columns we need** (any dataset close to this works — `data_loader.py` can adapt):

| Column | Example | Needed for |
|--------|---------|-----------|
| `name` | Taj Mahal | everything |
| `city` / `state` | Agra / Uttar Pradesh | filtering |
| `category` or `tags` | Monument;UNESCO;History | recommender ⭐ |
| `rating` | 4.8 | ranking |
| `lat`, `lon` | 27.17, 78.04 | route optimizer ⭐ |
| `avg_time_hours` | 2.5 | day planning |
| `entry_fee_inr` | 1100 | budget filtering |

No perfect dataset? `data/sample/places_india_sample.csv` has ~20 famous spots to start with —
we can always grow it later.

### 🌍 Worldwide data (Phase 2) — DONE ✅

The official **UNESCO World Heritage Sites** list — **1,270 places across the whole world,
each with GPS coordinates** — is auto-downloaded and converted (no login needed):

```bash
.venv\Scripts\python src\build_world_dataset.py
```

→ creates `data/raw/places_world_heritage.csv` (India alone has 44 sites in it!).

> **⚠️ Important design lesson:** we do NOT precompute "km from every place to every other
> place" — with 1,270 places that's 1.6 million pairs, and it grows as N². Instead we store
> `lat`/`lon` and compute distances **on demand** with `haversine_km()` — only for the
> ~10–15 places of a single trip. Same answers, ~0 storage.

---

## 🎓 Learning Outcomes

By finishing Wayfarer you'll have hands-on experience with:
**recommender systems · vectorization (TF-IDF) · similarity metrics · optimization heuristics (TSP) ·
pandas/EDA · building & deploying a full web app** — and a portfolio project that actually *does* something people want.
