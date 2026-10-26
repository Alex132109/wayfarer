"""
🧭 Wayfarer — squads.py  (PHASE 2 — groups & money together 👥💸)  ✅ demo-mode

THE WISHLIST, VERBATIM:
    • "have a link for making group — 5 people, duo, or solo traveller"
    • "if per-person budget is 25k: admin can pay 25×5 directly as group
      payment, OR 5 people pay 25k each inside the website"
    • (bonus) Splitwise-style expense tracker with net balances

LEARNING POINTS:
    • Invite codes via secrets.token_hex — short, unpredictable, easy to tap in.
    • Split-the-bill math: track what each member PAID vs what each member
      OWES; the difference is the net balance. Settle = pay net, not total!
"""

import secrets
import sqlite3
import sys
from pathlib import Path

import pandas as pd

try:
    from src.accounts import _connect as _base_connect
except ImportError:  # running directly: python src\squads.py
    from accounts import _connect as _base_connect

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_schema = """
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, owner_id INTEGER NOT NULL,
    invite_code TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER, user_id INTEGER,
    username TEXT NOT NULL, role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER, payer TEXT NOT NULL, amount REAL NOT NULL,
    description TEXT, created TEXT DEFAULT (datetime('now'))
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Accounts' tables + our own squad tables (layered schema)."""
    conn = _base_connect(db_path)
    conn.executescript(_schema)
    return conn


# ---------------------------------------------------------------- #
#  Groups + invite links                                             #
# ---------------------------------------------------------------- #
def create_group(name: str, owner_id: int, owner_name: str,
                 db_path: Path | None = None) -> dict:
    code = "WF-" + secrets.token_hex(3).upper()      # e.g. WF-4A2B9C
    with _connect(db_path) as conn:
        cur = conn.execute("INSERT INTO groups (name, owner_id, invite_code) VALUES (?,?,?)",
                           (name, owner_id, code))
        gid = cur.lastrowid
        conn.execute("INSERT INTO members (group_id, user_id, username, role) "
                     "VALUES (?,?,?,'admin')", (gid, owner_id, owner_name))
    return {"group_id": gid, "invite_code": code}


def join_group(invite_code: str, user_id: int, username: str,
               db_path: Path | None = None) -> dict:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT id FROM groups WHERE invite_code=?",
                           (invite_code.strip().upper(),)).fetchone()
        if not row:
            return {"ok": False, "error": "Invalid invite code."}
        gid = row[0]
        dup = conn.execute("SELECT 1 FROM members WHERE group_id=? AND user_id=?",
                           (gid, user_id)).fetchone()
        if dup:
            return {"ok": False, "error": "Already in this group."}
        conn.execute("INSERT INTO members (group_id, user_id, username, role) "
                     "VALUES (?,?,?,'member')", (gid, user_id, username))
    return {"ok": True, "group_id": gid}


def members(group_id: int, db_path: Path | None = None) -> pd.DataFrame:
    with _connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT username, role FROM members WHERE group_id=? ORDER BY id",
            conn, params=(group_id,))


def group_info(group_id: int, db_path: Path | None = None) -> dict | None:
    """Name + invite code for display (used after joining via a code)."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT name, invite_code FROM groups WHERE id=?",
                           (group_id,)).fetchone()
    return {"group_id": group_id, "name": row[0],
            "invite_code": row[1]} if row else None


# ---------------------------------------------------------------- #
#  💸 GROUP PAYMENT — the user's exact 25k×5 example                  #
# ---------------------------------------------------------------- #
def split_payment(per_person: float, n_people: int) -> dict:
    """
    Two ways to collect the SAME money:
      each_own   → n_people × per_person transactions
      admin_all  → admin pays one transaction of per_person × n_people
    """
    return {
        "per_person": round(per_person, 2),
        "n_people": n_people,
        "each_own": {"transactions": n_people,
                     "amount_each": round(per_person, 2),
                     "total": round(per_person * n_people, 2)},
        "admin_all": {"transactions": 1,
                      "amount": round(per_person * n_people, 2),
                      "total": round(per_person * n_people, 2)},
    }


# ---------------------------------------------------------------- #
#  💸 SPLITWISE-STYLE EXPENSES — who owes whom                        #
# ---------------------------------------------------------------- #
def add_expense(group_id: int, payer: str, amount: float, description: str,
                split_among: list[str], db_path: Path | None = None) -> dict:
    """One expense, split EQUALLY among the listed members."""
    n = len(split_among)
    if n == 0:
        return {"ok": False, "error": "Nobody to split with!"}
    with _connect(db_path) as conn:
        conn.execute("INSERT INTO expenses (group_id, payer, amount, description) "
                     "VALUES (?,?,?,?)", (group_id, payer, float(amount), description))
    share = float(amount) / n
    return {"ok": True, "share_each": round(share, 2), "split_among": split_among}


def balances(group_id: int, db_path: Path | None = None) -> pd.DataFrame:
    """
    Net balance per member: paid − owed.
      positive → the group owes THEM money
      negative → they owe the group
    """
    with _connect(db_path) as conn:
        names = [r[0] for r in conn.execute(
            "SELECT DISTINCT username FROM members WHERE group_id=?", (group_id,))]
        paid = {r[0]: r[1] for r in conn.execute(
            "SELECT payer, SUM(amount) FROM expenses WHERE group_id=? GROUP BY payer",
            (group_id,))}
        total = sum(paid.values())
        owed_each = total / len(names) if names else 0.0
    rows = [{"member": n, "paid": round(paid.get(n, 0.0), 2),
             "owed_share": round(owed_each, 2),
             "net": round(paid.get(n, 0.0) - owed_each, 2)} for n in names]
    return pd.DataFrame(rows).sort_values("net", ascending=False)


def print_split(split: dict, group_name: str = "") -> None:
    """Pretty-print the two ways to collect the group payment."""
    print(f"\n👥 GROUP PAYMENT — {group_name}  ({split['n_people']} people × ₹{split['per_person']:,.0f})")
    eo, aa = split["each_own"], split["admin_all"]
    print(f"   Option A — each pays own: {eo['transactions']} transactions × ₹{eo['amount_each']:,.0f} = ₹{eo['total']:,.0f}")
    print(f"   Option B — admin pays all: {aa['transactions']} transaction × ₹{aa['amount']:,.0f} = ₹{aa['total']:,.0f}")
    print("   (same money, different UX — user's exact wishlist!)")


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    from accounts import signup

    print("=== 5-person Japan squad (the user's exact scenario) ===")
    ids = [signup(f"member{i}", "pass1234", tmp) for i in range(1, 6)]
    g = create_group("Japan Squad", ids[0]["user_id"], "member1", tmp)
    print("invite code:", g["invite_code"])
    for m in ids[1:]:
        assert join_group(g["invite_code"], m["user_id"], f"member{m['user_id']}", tmp)["ok"]
    assert len(members(g["group_id"], tmp)) == 5

    split = split_payment(25000, 5)
    print_split(split, "Japan Squad")
    assert split["admin_all"]["amount"] == 125000 and split["each_own"]["total"] == 125000

    print("\n=== Splitwise: meals ₹8,000 split by all 5 ===")
    r = add_expense(g["group_id"], "member1", 8000, "team dinner", ["member1", "member2", "member3", "member4", "member5"], tmp)
    print("share each:", r["share_each"])
    b = balances(g["group_id"], tmp)
    print(b.to_string(index=False))
    assert abs(b["net"].sum()) < 0.01, "balances must cancel to zero!"
    assert b.iloc[0]["member"] == "member1" and b.iloc[0]["net"] > 0

    print("\n🎉 ALL SQUAD TESTS PASSED")
