"""
🧭 Wayfarer — companion.py  (PHASE 3 — travel companion 🤝)  ✅ demo-mode

THE WISHLIST:
    • Leaderboard per destination: "5 groups traveled Japan — ranked by
      budget-fit & execution" (G1)
    • Basic language class 1–2h per destination, with a mini quiz (G5)
    • Battery alerts: "<20% → don't wander alone, buddy rule" (G4)
    • Real-time location sharing of all group members (G3 — simulated)
    • SOS card with local emergency numbers (my suggested extra)

DEMO-MODE HONESTY:
    • Leaderboard uses SEED data + a scoring model (no live groups yet).
    • Live GPS needs phone apps/WebSockets — we simulate the data shape so
      the real version can slot in later without redesign.
"""

import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- #
#  1. LEADERBOARD — scoring model over seed groups                    #
# ---------------------------------------------------------------- #
# seed rows: (group, destination, spent_pp, budget_pp, executed_pct)
# score = execution × 60% + budget-efficiency × 40% (100 max)
SEED_GROUPS = [
    ("Tokyo Troopers", "japan", 78000, 75000, 100),
    ("Sakura Five", "japan", 72000, 75000, 95),
    ("Bullet Bills", "japan", 88000, 75000, 90),
    ("Sohra Sisters", "meghalaya", 19200, 20000, 100),
    ("Cave Crew", "meghalaya", 21000, 20000, 85),
]


def leaderboard(destination: str = "japan", top_n: int = 5) -> pd.DataFrame:
    """Rank completed trips: execution 60% + staying under budget 40%."""
    rows = [g for g in SEED_GROUPS if g[1] == destination]
    out = []
    for name, dest, spent, budget, executed in rows:
        budget_fit = max(0.0, min(1.0, budget / max(spent, 1)))     # 1.0 = under budget
        score = round(0.6 * executed + 0.4 * budget_fit * 100, 1)
        out.append({"group": name, "spent_pp": spent, "budget_pp": budget,
                    "executed_pct": executed, "score": score})
    df = pd.DataFrame(out).sort_values("score", ascending=False).head(top_n)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- #
#  2. LANGUAGE PACKS — mini crash course + quiz                       #
# ---------------------------------------------------------------- #
LANGUAGE_PACKS = {
    "japan": {
        "greeting": "konnichiwa — hello",
        "thanks": "arigatou gozaimasu — thank you",
        "sorry": "sumimasen — excuse me / sorry",
        "delicious": "oishii — delicious",
        "bill please": "o-kaikei onegaishimasu — the bill please",
        "how much": "ikura desu ka — how much?",
        "where is": "doko desu ka — where is ...?",
        "station": "eki — station",
        "yes/no": "hai / iie — yes / no",
        "cheers": "kanpai — cheers!",
    },
    "india": {
        "hello": "namaste — hello",
        "thanks": "dhanyavaad / shukriya — thank you",
        "how much": "kitna hai? — how much?",
        "too expensive": "bahut mehenga hai — too expensive",
        "where is": "kahan hai? — where is ...?",
        "water": "paani — water",
        "tasty": "swadisht — delicious",
        "right/left": "daayen / baayen — right / left",
        "help": "madad — help",
        "stop here": "yahin rukiye — stop here (cab/auto)",
    },
}


def language_quiz(destination: str = "japan") -> list[tuple]:
    """5 quick questions from the pack (question, options, answer index)."""
    phrases = list(LANGUAGE_PACKS[destination].items())[:5]
    quiz = []
    for i, (key, meaning) in enumerate(phrases):
        meaning_text = meaning.split("—")[-1].strip()
        correct = meaning.split("—")[0].strip()
        wrong = [p.split("—")[0].strip() for k, p in phrases if k != key]
        options = [correct] + wrong[:2]
        options.sort()
        quiz.append((f"What means '{meaning_text}'?", options, options.index(correct)))
    return quiz


# ---------------------------------------------------------------- #
#  3. SAFETY — battery buddy + location share + SOS                  #
# ---------------------------------------------------------------- #
def battery_buddy(levels: dict[str, int], threshold: int = 20) -> list[str]:
    """The wishlist rule: <20% battery → that member must NOT wander alone."""
    alerts = []
    for member, pct in levels.items():
        if pct < threshold:
            buddies = [m for m, p in levels.items() if p >= threshold]
            msg = (f"🔋 {member} at {pct}% — pair up! Stay with "
                   f"{buddies[0] if buddies else 'the group'} and share live location.")
            alerts.append(msg)
    return alerts


def location_share(members: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """SIMULATED live-share snapshot (real version = phone GPS → WebSocket)."""
    return pd.DataFrame(
        [{"member": m, "lat": round(lat, 5), "lon": round(lon, 5),
          "shared": True} for m, (lat, lon) in members.items()])


def sos_card(destination: str = "india") -> dict:
    """One card to screenshot before the trip."""
    cards = {
        "india": {"police": "112 / 100", "ambulance": "108", "tourist helpline": "1800-11-1363",
                  "note": "Save your hotel address in the local language."},
        "japan": {"police": "110", "ambulance/fire": "119",
                  "tourist helpline": "050-3816-2787 (JNTO)",
                  "note": "Convenience stores can call taxis for you."},
    }
    return cards.get(destination, cards["india"])


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    print("=== Leaderboard — Japan ===")
    lb = leaderboard("japan")
    print(lb.to_string(index=False))
    assert lb.iloc[0]["group"] in ("Sakura Five", "Tokyo Troopers")

    print("\n=== Language quiz (japan) ===")
    for q, opts, a in language_quiz("japan")[:2]:
        print(f"  {q}  {opts}  → answer: {opts[a]}")
    assert len(language_quiz("japan")) == 5

    print("\n=== Battery buddy ===")
    for a in battery_buddy({"member1": 85, "member2": 15, "member3": 19}):
        print(" ", a)
    assert len(battery_buddy({"member1": 85, "member2": 15, "member3": 19})) == 2

    print("\n=== Location share snapshot ===")
    print(location_share({"member1": (34.69, 135.50), "member2": (34.70, 135.51)}).to_string(index=False))

    print("\n=== SOS card (japan) ===")
    print(sos_card("japan"))

    print("\n🎉 ALL COMPANION TESTS PASSED")
