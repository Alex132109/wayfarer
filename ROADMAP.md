# 🧭 Wayfarer — Product Roadmap

> Status: **PLAN ONLY** (approved by user to draft — nothing built yet)
> Built so far (committed): data pipeline, worldwide + curated datasets, ML recommender,
> route optimizer (round trips), corridor filter, day/stay allocation, Streamlit website.

---

## 1. Your feature list — captured & organized

### A. Accounts & Groups
| # | Feature | Notes |
|---|---------|-------|
| A1 | User database | Sign-up/login, profiles, trip history |
| A2 | Groups with invite links | Solo · duo · group of 3–10; link-join like WhatsApp |

### B. Trip Planning Core
| # | Feature | Notes |
|---|---------|-------|
| B1 | Start point, end point, actual destination | separate inputs |
| B2 | Total trip days · **travel days vs stay days** | "3 days to reach + 5 days at destination" split |
| B3 | Mode of transportation | flight / train / car / bike / bus / mixed |
| B4 | Trip style tiers | budget · economy · comfort · premium · luxury · super-luxury |
| B5 | Itinerary recommender | ✅ already built (recommender + router + days) — needs upgrade into B9 guide |
| B6 | Suggestion & recommendation for everything | one unified recommender engine |

### C. Money & Budget
| # | Feature | Notes |
|---|---------|-------|
| C1 | Budget estimator (before trip) | by style tier + group size |
| C2 | Actual budget calculator + emergency fund | live tracking + ~10% buffer |
| C3 | Per-day / per-meal / per-person / per-transport budget | "how much to spend at lunch" guidance |

### D. Food System
| # | Feature | Notes |
|---|---------|-------|
| D1 | Food recommender with daily options | "in Osaka, try this dish at that place near your stay" |
| D2 | Diet filters | veg · non-veg · vegan · eggetarian · jain · halal etc. |
| D3 | Food budget per trip + per day | integrated into C |

### E. Daily Guide (the killer feature ⭐)
| # | Feature | Notes |
|---|---------|-------|
| E1 | Time + budget boxed daily schedule | "Day 1: breakfast ₹600 → 7-Eleven/mochi café; pagoda ₹300/person, max 1h15m, else next item skipped; lunch…" |
| E2 | Essentials list — trip level | passport, Aadhaar, visa, meds (domestic vs foreign aware) |
| E3 | Essentials list — day level, real-time climate | sunscreen/umbrella/raincoat from live weather |

### F. User Control
| # | Feature | Notes |
|---|---------|-------|
| F1 | Edit everything after planning | change meal budget, drop a shrine, food pref switch → whole budget & itinerary recompute |
| F2 | Phobia filters | fear of heights/dark/water/crowds → warn or skip places |

### G. Social & Fun
| # | Feature | Notes |
|---|---------|-------|
| G1 | Leaderboard per destination | "5 groups traveled Japan — ranked by budget-fit & execution" |
| G2 | Group photo/video sharing | stored on Drive, group album |
| G3 | Real-time location sharing | live map of all members |
| G4 | Battery alerts | <20% → "don't wander alone, buddy rule" |
| G5 | Basic language crash course | 1–2 hr pack per destination |

### H. Commerce
| # | Feature | Notes |
|---|---------|-------|
| H1 | In-site payments + booking confirmation | stays/bookings at shown price |
| H2 | Group payments | admin pays 25k×5 at once OR each member pays 25k |
| H3 | eSIM store | international plans purchasable in-site |
| H4 | Cab recommendation system | airport/station transfers + local rides |

---

## 2. How each feature gets built (tech mapping)

| Feature group | Tech / data source | Difficulty |
|---|---|---|
| A1–A2 accounts & groups | SQLite + hashed passwords + invite-link tokens (pure Python) | M |
| B1–B4 trip params & styles | extend existing planner + style multipliers | S |
| C1–C3 budget engine | pure computation on the trip-plan object | S–M |
| D food recommender | city food dataset (name, dish, diet tags, price, rating) + same TF-IDF matching we already use | M |
| E1 daily guide | rule engine over itinerary: opening hours + travel time + budget caps | M–L |
| E2 essentials | curated checklist rules (domestic vs international) | S |
| E3 weather day-cards | OpenWeather API (free key) | S–M |
| F1 edit-everything | single "TripPlan" object = source of truth; edits → recompute budget & days | M |
| F2 phobia filters | tag places (heights/dark/water/crowds) + warning logic | S |
| G1 leaderboard | scoring model + demo seed data | M |
| G2 media sharing | Google Drive API per-group folder | M |
| G3–G4 live location & battery | needs WebSocket/mobile GPS infra | **L (infra)** |
| G5 language course | curated content packs + mini quizzes | M |
| H1–H2 payments | Razorpay **test mode** first (real money = real compliance) | M–L |
| H3 eSIM | partner API (e.g., Airalo) — or demo catalog first | L |
| H4 cab recs | rule-based + ratings data first; Maps API later | S–M |

> ⚠️ Honest note: real payments, real bookings, and live GPS tracking are **business/compliance
> features**, not just code. We build working **demo/test-mode** versions for the project.

---

## 3. Build phases (approve one at a time)

### 🟢 Phase 1 — "Planner Pro" (pure Python, no new infra) — RECOMMENDED FIRST
1. Trip-input upgrade: start/end/destination + travel-vs-stay days + transport mode (B1–B3)
2. Trip style tiers with cost multipliers (B4)
3. Budget engine: estimator + emergency fund + per-day/person/meal split (C1–C3)
4. Daily guide: time-boxed + budget-boxed schedule (E1)
5. Food recommender + diet filters + food budget (D1–D3)
6. Edit-everything recompute (F1)
7. Phobia filters (F2)
8. Essentials list (E2) + weather day-cards if you get a free OpenWeather key (E3)

### 🟡 Phase 2 — "Accounts & Squads"
User DB + login (A1), groups + invite links (A2), per-person budget split,
split-expense tracker, leaderboard with demo data (G1)

### 🟠 Phase 3 — "Live Travel Companion"
Cab recs (H4), language crash course (G5), offline PDF itinerary export,
photo/video group album on Drive (G2), live location + battery buddy (G3–G4)

### 🔴 Phase 4 — "Commerce" (demo/test-mode)
Payments + group payments (H1–H2), booking confirmations (H1), eSIM catalog (H3)

### 🔵 Phase 5 — "Scale & Polish" (when project becomes product)
FastAPI backend + React/mobile frontend, collaborative-filtering recommender
(learns from real users), public template-trips feed, ML price prediction

---

## 4. My extra suggestions (your menu — pick what you like)

| Idea | Effort | Why it's great |
|---|---|---|
| 💸 Splitwise-style group expense tracker | M | perfect fit with your group payments |
| 🗳️ Group voting on itinerary changes | S | "3 of 5 agree → shrine removed" |
| 🆘 SOS button + embassy/112 info card | S | safety = credibility |
| 💱 Currency converter + daily forex allowance | S | pairs with international trips |
| 🛂 Visa & document checklist (international) | S | pairs with essentials list |
| 🎒 Auto packing list (weather + activities) | S | "rain in Osaka → pack umbrella" |
| 📄 Offline PDF / print itinerary export | S | share on WhatsApp |
| 💬 AI chat concierge ("make day 3 a beach day") | M | modern wow-factor |
| 🏆 Badges & trip gamification | S | student demo gold |
| ♿ Accessibility & medical filters | S | wheelchair routes, motion-sickness warnings |
| ✈️ Flight/train price alerts | M | needs external API |
| 📔 Auto trip journal from group photos | M | emotional payoff post-trip |

---

## 5. What I need from you (decisions, not code)

1. **Approve Phase 1** (or edit it) — then we build task by task, one at a time
2. **Weather API**: create a free OpenWeather key when we reach E3 (I'll guide you)
3. **Payments**: demo (test-mode) only, right? (real payments = later business talk)
4. **Design commit**: the website redesign from last session is still uncommitted — say "commit design" when you're happy with it

---

## 6. Scaling Plan — Go All Out 🚀

> Saved (plan-only) on user request. Each direction is independent — pick any in any order.

### 6.1 Scale the DATA (more places, richer info)
| Upgrade | What it unlocks | Effort |
|---------|----------------|--------|
| More curated datasets (Kerala, Ladakh, Golden Triangle, Goa, Bali, Thailand, Vietnam…) | every new region works like the demos do | S–M |
| Rich tags per place: **opening hours**, phobia tags, accessibility, activity type | powers the daily guide (E1) + phobia filters (F2) | M |
| Hotels dataset (town, price/night, rating, style tier) | real stays, bookable | M |
| Food dataset (dish, restaurant, city, diet tags, price, rating) | full food recommender (D1–D2) | M |
| Community dataset — users add places via a form | dataset grows by itself | M |

### 6.2 Scale the ML (the learning ladder)
1. ✅ TF-IDF content-based (done — first model)
2. **Hybrid recommender**: weighted blend of interest-match + rating + best-season + detour (pure logic, big quality jump)
3. **Semantic embeddings** (sentence-transformers): understands "romantic old town" ≈ "heritage village" — TF-IDF can't
4. **Collaborative filtering**: "travellers like you also loved…" (Phase 5, needs user data)
5. **Price-prediction ML** (sklearn regression): predicts trip cost from past trips — second model!
6. **Graph routing** (networkx): per-transport-mode speeds & costs, smarter search on big datasets

### 6.3 Scale the TECH (demo → product)
| Now | Scale to | Why |
|-----|----------|-----|
| Straight-line km (haversine) | **OSRM / OpenRouteService — real road km + turn-by-turn** (free) | biggest accuracy win |
| Basic `st.map` | **folium/pydeck with drawn route lines** | wow-factor |
| Streamlit only | **FastAPI backend** (engine is already separate) | real product architecture |
| No login | SQLite → **PostgreSQL** | accounts (A1) |
| Manual testing | **pytest suite + GitHub Actions CI** | professional habit |
| Localhost | **Deploy free**: Streamlit Community Cloud / HF Spaces | shareable link |
| Desktop only | Docker container | deploy anywhere |

### 6.4 Scale the REACH (users & community)
- 🌐 Deploy free → share on LinkedIn / Reddit / student groups
- 📸 README upgrade: screenshots, demo GIF, badges
- 📔 Template-trips feed: travellers publish itineraries, others clone them
- 🏆 Real leaderboard entries once groups use it
- 📖 "How I built Wayfarer" blog/LinkedIn series — doubles as portfolio

### 6.5 Scale the VALUE (if it becomes a product)
- 💰 Affiliate revenue: hotels, cabs, eSIMs (Airalo partner), insurance
- 🆓 Freemium: free planner + premium (PDF export, live tracking, AI concierge)
- 🏢 B2B: white-label for travel agencies

### 6.6 NEW ideas found during scaling review ✨
| Idea | Why it scales Wayfarer up | Effort |
|------|--------------------------|--------|
| 🧭 "Open in Google Maps" button | zero-cost: exports the optimized route for real navigation | S |
| 📅 ICS calendar export | itinerary → Google/Apple Calendar in one click | S |
| 💬 WhatsApp share link | share the trip link where Indian groups actually live | S |
| 🗣️ Multi-language UI (i18n) | Hindi/Tamil/etc. = massive India-first reach | M |
| 🤖 LLM trip parser | "5 days Japan under ₹1L, veg food" → fills the whole form | M |
| 🏷️ Trip themes (clustering ML) | auto-label trips "Spiritual", "Adventure" for better feeds | M |
| 🌦️ Seasonal price trends | pick cheapest month to visit — pairs with best_time column | M |
| 📊 Usage analytics + monitoring | know what travellers actually use before scaling further | M |
| ⚡ Search-in-place (filter as you type) | scale UX for 1,270+ worldwide places | S |
| 🔒 `st.secrets` for API keys | keys never live in code or git — ready for OpenWeather | S |

### 6.7 Top 5 highest-impact next steps
1. **Deploy free** (30 min, instant shareable link)
2. **Real road km via OSRM** (10× accuracy)
3. **Phase 1 build** (Planner Pro features)
4. **Hybrid recommender** (quality jump + learning)
5. **One more curated region** (proves the pattern scales)

---

## 7. Security & Robustness Audit Log

> Done 2026-10-26 (fixes committed): see commit "fix: security & robustness audit".
> - ✅ Website crash on round trips fixed (↩️ row had `""` rating/fee → `float("")` crash)
> - ✅ Data layer hardened: standard columns guaranteed, coordinates force-converted + range-clipped
> - ✅ Corridor fallback now computes detour km for rescue candidates
> - ✅ HTML-escaped rendering everywhere (XSS-safe for future user-submitted places)
> - ✅ SSL fallback scoped correctly (HTTP errors no longer misreported as SSL failures)
> - ✅ `.streamlit/secrets.toml` ignored in git — future API keys never leak
>
> Planned for later phases: rate limiting + input validation when the FastAPI
> backend exists, password hashing for accounts (A1), dataset content checks
> for community submissions.

---

*Last updated: 2026-10-26 · Wayfarer v0.5*
