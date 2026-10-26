"""
🧭 Wayfarer — commerce.py  (PHASE 3 — bookings & payments 💳)  ✅ demo-mode

THE WISHLIST (H1–H4 from the roadmap):
    • In-site payments + booking confirmation   → demo Razorpay-shaped flow
    • Group payments: admin pays 25k×5 ONCE, or each pays 25k   → pay_group()
    • eSIM store: international plans purchasable in-site        → esim_catalog()
    • Cab recommendation (airport transfers + local rides)       → cab_recommend()

DEMO-MODE HONESTY (read this twice — it's the most important lesson here):
    Real payments are NOT code — they're a licensed gateway (Razorpay/Stripe)
    plus legal compliance. What we CAN learn and build is the exact FLOW:

        create_order()  →  user pays  →  capture()  →  booking confirmed

    We simulate that flow in TEST MODE (no real money moves). Because our
    website code speaks the same shape (order id, paise amounts, status),
    swapping in the real gateway later = one function, not a redesign.

LEARNING POINTS:
    • Gateways count money in the SMALLEST unit (paise) — ₹25,000 = 2,500,000.
      Floats round badly with money; integers never do.
    • An order can only be captured ONCE (double-capture = real-world bug).
    • secrets.token_hex() generates unpredictable ids — never use counters
      for anything payment-related (guessable ids = someone else pays).
"""

import secrets
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEMO_KEYS = {"key_id": "rzp_test_WAYFARER", "mode": "test"}

_ORDERS: dict[str, dict] = {}   # order_id → order (demo store; real = gateway DB)
_BOOKINGS: list[dict] = []      # confirmed bookings (demo store)


# ---------------------------------------------------------------- #
#  1. PAYMENTS — the gateway-shaped flow, in test mode                #
# ---------------------------------------------------------------- #
def create_order(amount_inr: float, description: str,
                 notes: dict | None = None) -> dict:
    """₹ → paise, then mint an order exactly like Razorpay's API would."""
    amount_paise = int(round(float(amount_inr) * 100))
    order_id = "order_" + secrets.token_hex(8)
    order = {"id": order_id, "amount": amount_paise, "currency": "INR",
             "description": description, "notes": notes or {},
             "status": "created", "key_id": DEMO_KEYS["key_id"]}
    _ORDERS[order_id] = order
    return order


def capture(order_id: str, method: str = "upi") -> dict:
    """The gateway callback: order goes created → paid. One-way door."""
    order = _ORDERS.get(order_id)
    if order is None:
        raise KeyError(f"Unknown order: {order_id}")
    if order["status"] == "paid":
        raise ValueError("Order already captured — double-capture blocked!")
    order["status"] = "paid"
    order["method"] = method
    order["captured_at"] = "test-mode (simulated timestamp)"
    return order


def pay_group(per_person: float, n_people: int, how: str = "admin_all") -> list[dict]:
    """
    THE USER'S EXACT SCENARIO — per_person=25,000, n=5:
        admin_all → ONE order of ₹1,25,000 (admin pays, settles offline)
        each_own  → FIVE orders of ₹25,000 each (everyone pays in-site)
    Both collect the same ₹1,25,000 — different UX, zero money difference.
    """
    if n_people < 1:
        raise ValueError("Group needs at least 1 person.")
    if how == "admin_all":
        order = create_order(per_person * n_people,
                             f"group payment — admin pays for {n_people}")
        return [capture(order["id"], method="upi")]
    if how == "each_own":
        orders = []
        for _ in range(n_people):
            o = create_order(per_person, "group payment — each pays own")
            orders.append(capture(o["id"], method="upi"))
        return orders
    raise ValueError(f"Unknown payment style: {how!r} (use 'admin_all' or 'each_own')")


# ---------------------------------------------------------------- #
#  2. BOOKINGS — pay → confirmation code (demo)                       #
# ---------------------------------------------------------------- #
def book_hotel(hotel_name: str, city: str, nights: int, rooms: int,
               price_per_night: float, guest: str = "guest") -> dict:
    """Book at the shown price: one order → capture → confirmation code."""
    nights, rooms = int(nights), int(rooms)
    total = rooms * nights * float(price_per_night)
    order = create_order(total, f"hotel booking: {hotel_name}")
    capture(order["id"], method="card")
    booking = {
        "confirmation": "BK-" + secrets.token_hex(3).upper(),
        "hotel": hotel_name, "city": city, "guest": guest,
        "rooms": rooms, "nights": nights,
        "total_inr": round(total, 2), "order_id": order["id"],
        "status": "confirmed (test mode)",
    }
    _BOOKINGS.append(booking)
    return booking


# ---------------------------------------------------------------- #
#  3. eSIM STORE — plans for the destination (demo catalog)           #
# ---------------------------------------------------------------- #
ESIM_PLANS = {
    "japan": [
        {"plan": "Sakura 5", "data": "1 GB/day", "valid_days": 5, "price_inr": 499},
        {"plan": "Sakura 15", "data": "10 GB total", "valid_days": 15, "price_inr": 999},
        {"plan": "Sakura Max", "data": "unlimited", "valid_days": 21, "price_inr": 1999},
    ],
    "india": [
        {"plan": "Monsoon 7", "data": "1.5 GB/day", "valid_days": 7, "price_inr": 199},
        {"plan": "Monsoon 28", "data": "2 GB/day", "valid_days": 28, "price_inr": 499},
    ],
    "world": [
        {"plan": "Globe 10", "data": "10 GB total", "valid_days": 30, "price_inr": 1499},
        {"plan": "Globe 50", "data": "50 GB total", "valid_days": 60, "price_inr": 2999},
    ],
}


def esim_catalog(destination: str = "japan") -> pd.DataFrame:
    """Plans for a destination, cheapest first."""
    plans = pd.DataFrame(ESIM_PLANS.get(destination, ESIM_PLANS["world"]))
    return plans.sort_values("price_inr").reset_index(drop=True)


def buy_esim(destination: str, plan_name: str, guest: str = "guest") -> dict:
    """Demo purchase: find the plan → order → capture → activation code."""
    cat = esim_catalog(destination)
    row = cat[cat["plan"] == plan_name]
    if row.empty:
        raise ValueError(f"No eSIM plan '{plan_name}' for {destination}.")
    plan = row.iloc[0]
    order = create_order(plan["price_inr"], f"eSIM {plan_name} ({destination})")
    capture(order["id"], method="upi")
    return {"activation_code": "ESIM-" + secrets.token_hex(4).upper(),
            "plan": plan_name, "destination": destination,
            "paid_inr": float(plan["price_inr"]), "order_id": order["id"],
            "status": "purchased (test mode)"}


# ---------------------------------------------------------------- #
#  4. CAB RECOMMENDER — cheapest vehicle that FITS the group          #
# ---------------------------------------------------------------- #
CABS = [
    {"type": "Hatchback (WagonR/i10)", "max_people": 3, "rate_per_km": 10, "comfort": 3},
    {"type": "Sedan (Dzire/Etios)", "max_people": 4, "rate_per_km": 12, "comfort": 4},
    {"type": "SUV (Ertiga/Innova)", "max_people": 7, "rate_per_km": 18, "comfort": 5},
    {"type": "Tempo Traveller", "max_people": 12, "rate_per_km": 26, "comfort": 4},
]
LONG_DAY_KM = 450   # matches the route planner's long-drive warning


def cab_recommend(travellers: int, day_km: float = 0) -> pd.DataFrame:
    """
    Cabs that FIT the group, cheapest first, with an estimated day cost.
    day_km > 450 → flagged: split the day or hire two vehicles.
    """
    travellers = int(travellers)
    fits = [c for c in CABS if c["max_people"] >= travellers] or [CABS[-1]]
    rows = []
    for c in sorted(fits, key=lambda c: c["rate_per_km"]):
        rows.append({
            "cab": c["type"], "fits": c["max_people"], "rate/km": c["rate_per_km"],
            "est. day cost": round(c["rate_per_km"] * float(day_km)),
            "note": ("🚗 long day — split into 2 days or add buffer"
                     if day_km > LONG_DAY_KM else
                     f"comfort {c['comfort']}/5"),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    print("=== 💳 THE 25k×5 GROUP PAYMENT (admin_all vs each_own) ===")
    admin = pay_group(25000, 5, how="admin_all")
    each = pay_group(25000, 5, how="each_own")
    print(f"admin_all → {len(admin)} order of ₹{admin[0]['amount'] / 100:,.0f}")
    print(f"each_own  → {len(each)} orders of ₹{each[0]['amount'] / 100:,.0f}")
    assert len(admin) == 1 and admin[0]["amount"] == 125000 * 100
    assert len(each) == 5 and sum(o["amount"] for o in each) == 125000 * 100
    print("   same money, different UX — wishlist delivered ✅")

    print("\n=== double-capture is impossible ===")
    try:
        capture(admin[0]["id"])
        raise AssertionError("should have raised!")
    except ValueError as e:
        print("   blocked:", e)

    print("\n=== 🏨 hotel booking ===")
    b = book_hotel("Sakura Ryokan", "Kyoto", nights=3, rooms=2, price_per_night=4500, guest="member1")
    print(b)
    assert b["total_inr"] == 3 * 2 * 4500 and b["status"].startswith("confirmed")

    print("\n=== 📶 eSIM store ===")
    print(esim_catalog("japan").to_string(index=False))
    e = buy_esim("japan", "Sakura 5")
    assert e["paid_inr"] == 499 and e["activation_code"].startswith("ESIM-")
    print("   bought:", e["plan"], "→", e["activation_code"])

    print("\n=== 🚺 cab recommendation (5 travellers, 200 km day) ===")
    print(cab_recommend(5, day_km=200).to_string(index=False))
    assert (cab_recommend(5)["fits"] >= 5).all()

    print("\n🎉 ALL COMMERCE TESTS PASSED (demo-mode, no real money moved)")
