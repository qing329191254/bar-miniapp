"""Update BOSS login phone (and reset staff passwords to default).

Usage:
  cd server
  python scripts/set_boss_phone.py
  python scripts/set_boss_phone.py --phone 13121309366
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database import SessionLocal  # noqa: E402
from logic import DEFAULT_PWD, bind_wx_phone, hash_pwd  # noqa: E402
from models import User  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phone", default="13121309366")
    p.add_argument("--reset-all-staff-pwd", action="store_true", help="Also reset MANAGER/STAFF to default pwd")
    args = p.parse_args()
    phone = "".join(ch for ch in args.phone if ch.isdigit())
    if len(phone) != 11 or not phone.startswith("1"):
        print("invalid phone", phone)
        return 1

    hashed = hash_pwd(DEFAULT_PWD)
    db = SessionLocal()
    try:
        bosses = db.query(User).filter(User.role == "BOSS").all()
        if not bosses:
            print("no BOSS user found")
            return 1
        for boss in bosses:
            bind_wx_phone(db, boss, phone)
            boss.pwd = hashed
            print(f"boss id={boss.id} no={boss.no} -> {boss.phone} tail={boss.tail}")
        if args.reset_all_staff_pwd:
            n = (
                db.query(User)
                .filter(User.role.in_(["MANAGER", "STAFF"]))
                .update({User.pwd: hashed}, synchronize_session=False)
            )
            print(f"reset pwd for {n} manager/staff to {DEFAULT_PWD}")
        db.commit()
        print("ok")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
