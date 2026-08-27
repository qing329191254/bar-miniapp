"""Load prototype seed.json into MySQL (idempotent)."""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import inspect, text

from database import SessionLocal, engine
from logic import DEFAULT_PWD, grant_demo_coins, grant_demo_points, grant_demo_sign, hash_pwd
from models import (
    AgreeLog, Base, Card, CardTpl, Category, Champ, CoinAdjust, DailyBiz,
    Deactivation, GameRecord, OpLog, Order, Product, Project, Recharge,
    Setting, SettleLog, SignRecord, SignRule, TableSeat, Team, Tier, User,
    VerifyLog, Wallet, Withdrawal,
)

SEED = json.loads((Path(__file__).parent / "seed.json").read_text(encoding="utf-8"))
TODAY = "2026-08-25"


def _wallet(uid: int, seed: dict) -> Wallet:
    c = seed["coin"].get(str(uid)) or seed["coin"].get(uid) or {"p": 0, "b": 0}
    p = seed["point"].get(str(uid)) or seed["point"].get(uid) or {}
    sh = seed["shard"].get(str(uid)) or seed["shard"].get(uid) or {}
    st = seed.get("signStreak") or {}
    streak = st.get(str(uid)) or st.get(uid) or 0
    return Wallet(
        user_id=uid,
        coin_p=int(c.get("p") or 0), coin_b=int(c.get("b") or 0),
        point_av=int(p.get("av") or 0), point_wg=int(p.get("wg") or 0),
        point_mg=int(p.get("mg") or 0), point_pd=int(p.get("pd") or 0),
        point_wd=int(p.get("wd") or 0), point_fz=int(p.get("fz") or 0),
        shard_w=int(sh.get("w") or 0), shard_t=int(sh.get("t") or 0),
        sign_streak=int(streak),
    )


def seed_all(reset: bool = False):
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("users")]
    if "pwd" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN pwd VARCHAR(128) NOT NULL DEFAULT ''"))
    if "wx_openid" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN wx_openid VARCHAR(64) NOT NULL DEFAULT ''"))
    db = SessionLocal()
    try:
        if reset:
            for t in reversed(Base.metadata.sorted_tables):
                db.execute(t.delete())
            db.commit()
        hashed = hash_pwd(DEFAULT_PWD)
        if db.query(User).count():
            db.query(User).filter(
                User.role != "CUSTOMER",
                (User.pwd == None) | (User.pwd == ""),
            ).update({User.pwd: hashed}, synchronize_session=False)
            for u in db.query(User).all():
                if (u.no or "").startswith("WK"):
                    u.no = u.no[2:]
            have = {c.id for c in db.query(Card).all()}
            for c in SEED.get("cards") or []:
                if c["id"] in have:
                    continue
                db.add(Card(
                    id=c["id"], uid=c["uid"], tpl=c["tpl"], no=c["no"], src=c.get("src") or "",
                    src_desc=c.get("srcDesc") or "", status=c["status"], days_left=c.get("daysLeft") or 30,
                    expire=c.get("expire") or "", void_reason=c.get("voidReason"),
                ))
            for w in db.query(Wallet).all():
                grant_demo_points(db, w.user_id)
                grant_demo_coins(db, w.user_id)
                grant_demo_sign(db, w.user_id)
            db.commit()
            return {"ok": True, "skipped": True}
        s = SEED
        for x in s["users"]:
            db.add(User(
                id=x["id"], no=x["no"], nick=x["nick"], phone=x.get("phone") or "",
                tail=x.get("tail") or "", gender=x.get("gender") or 0, role=x["role"],
                team_id=x.get("teamId"), status=x.get("status") or "ACTIVE",
                deact=x.get("deact"), agreed_version=x.get("agreedVersion") or 0,
                pwd=hash_pwd(DEFAULT_PWD),
            ))
            db.add(_wallet(x["id"], s))
        for t in s["teams"]:
            db.add(Team(id=t["id"], name=t["name"]))
        for i, c in enumerate(s["champs"], 1):
            db.add(Champ(id=i, uid=c["uid"], event=c["event"], date=c["date"], n=c.get("n") or 0,
                         team_id=c.get("teamId"), team_name=c.get("teamName") or "", op=c.get("op") or ""))
        for p in s["projects"]:
            db.add(Project(id=p["id"], name=p["name"], min=p.get("min") or 0, max=p.get("max") or 0,
                           shard=p.get("shard") or 0, recent=p.get("recent") or 0, sort=p.get("sort") or 99,
                           disabled=bool(p.get("disabled"))))
        for c in s["cats"]:
            db.add(Category(id=c["id"], name=c["name"], sort=c.get("sort") or 99, disabled=bool(c.get("disabled"))))
        for p in s["products"]:
            db.add(Product(
                id=p["id"], cid=p["cid"], name=p["name"], desc=p.get("desc") or "", price=p["price"],
                has_spec=bool(p.get("hasSpec")), spec_multi=bool(p.get("specMulti")), specs=p.get("specs"),
                sold_out=bool(p.get("soldOut")), img=p.get("img"), type=p.get("type"), combo=p.get("combo"),
                offline=bool(p.get("offline")),
            ))
        for t in s["tables"]:
            db.add(TableSeat(id=t["id"], name=t["name"], area=t.get("area") or "", seats=t.get("seats") or 4))
        for t in s["cardTpls"]:
            db.add(CardTpl(
                id=t["id"], name=t["name"], cat=t["cat"], sub=t.get("sub"), desc=t.get("desc") or "",
                cost=t.get("cost") or 0, days=t.get("days") or 30, use=t.get("use") or "",
                per_limit=-1 if t.get("perLimit") is None else t["perLimit"],
                stock=-1 if t.get("stock") is None else t["stock"],
                exch=False if t.get("exch") is False else True, prize=t.get("prize"),
            ))
        for c in s["cards"]:
            db.add(Card(
                id=c["id"], uid=c["uid"], tpl=c["tpl"], no=c["no"], src=c.get("src") or "",
                src_desc=c.get("srcDesc") or "", status=c["status"], days_left=c.get("daysLeft") or 30,
                expire=c.get("expire") or "", void_reason=c.get("voidReason"),
            ))
        for o in s["orders"]:
            db.add(Order(
                id=o["id"], no=o["no"], uid=o["uid"], nick=o.get("nick") or "", table_id=o.get("tableId"),
                table_name=o.get("tableName") or "", total=o["total"], pay_type=o["payType"], status=o["status"],
                remark=o.get("remark") or "", ago=o.get("ago") or "", at=o.get("at") or "",
                op_uid=o.get("opUid"), items=o.get("items") or [], expire_at=o.get("expireAt"),
                paid_principal=o.get("paidPrincipal"), paid_bonus=o.get("paidBonus"),
                cancel_reason=o.get("cancelReason") or o.get("refundReason"),
            ))
        for r in s["recharges"]:
            db.add(Recharge(
                id=r["id"], no=r["no"], uid=r["uid"], amount=r["amount"], bonus=r.get("bonus") or 0,
                status=r["status"], expire_at=r.get("expireAt"), created=r.get("created") or "",
                at=r.get("at") or "", op_uid=r.get("opUid"), close_reason=r.get("closeReason"),
                reject_remark=r.get("rejectRemark"),
                pending_uid=r["uid"] if r["status"] == "PENDING_PAY" else None,
            ))
        for w in s["withdrawals"]:
            db.add(Withdrawal(
                id=w["id"], no=w["no"], uid=w["uid"], pts=w["pts"], status=w["status"],
                created=w.get("created") or "", at=w.get("at") or "", expire_at=w.get("expireAt"),
                grant_by=w.get("grantBy"), grant_at=w.get("grantAt"), reject_by=w.get("rejectBy"),
                reject_remark=w.get("rejectRemark"), closed_at=w.get("closedAt"),
                pending_uid=w["uid"] if w["status"] == "PENDING_CONFIRM" else None,
            ))
        for d in s["deactivations"]:
            db.add(Deactivation(
                id=d["id"], no=d["no"], uid=d["uid"], status=d["status"], created=d.get("created") or "",
                reason=d.get("reason") or "", snap=d.get("snap") or {}, audit_by=d.get("auditBy"),
                audit_at=d.get("auditAt"), audit_remark=d.get("auditRemark"), refund_ok=d.get("refundOk"),
                refunded=d.get("refunded"), void_cards=d.get("voidCards"),
            ))
        for a in s["coinAdjusts"]:
            db.add(CoinAdjust(
                id=a["id"], uid=a["uid"], delta=a["delta"], type=a["type"],
                reason=a.get("reason") or "", adjust_by=a.get("by") or 0,
                at=a.get("at") or "", status=a.get("status") or "PENDING",
            ))
        for t in s["tiers"]:
            db.add(Tier(id=t["id"], amount=t["amount"], bonus=t.get("bonus") or 0, rec=bool(t.get("rec"))))
        for r in s["signRules"]:
            db.add(SignRule(id=r["id"], days=r["days"], pts=r.get("pts") or 0, cards=r.get("cards") or [], enabled=r.get("enabled") is not False))
        for day in s.get("signed") or []:
            db.add(SignRecord(uid=1, day=int(day), month="2026-08"))
        for g in s["gameRecords"]:
            db.add(GameRecord(
                id=g["id"], pid=g.get("pid") or 0, pname=g.get("pname") or "", table=g.get("table") or "",
                round=g.get("round") or "", time=g.get("time") or "", op=g.get("op") or "",
                op_uid=g.get("opUid") or 0, players=g.get("players") or [], status=g.get("status"),
            ))
        for d in s["dailyBiz"]:
            db.add(DailyBiz(**d))
        for v in s["verifyLogs"]:
            db.add(VerifyLog(id=v["id"], card_no=v["cardNo"], tpl_name=v["tplName"], uid=v["uid"], op_uid=v["opUid"], at=v["at"]))
        for x in s["settleLogs"]:
            db.add(SettleLog(
                id=x["id"], week=x.get("week") or "", type=x.get("type") or "", sub=x.get("sub") or "",
                target=x.get("target") or "", nick=x.get("nick") or "", sh=x.get("sh") or 0,
                status=x.get("status") or "", card_id=x.get("cardId"), desc=x.get("desc") or "",
            ))
        for i, x in enumerate(s["logs"], 1):
            db.add(OpLog(id=i, t=x.get("t") or "", op=x.get("op") or "", role=x.get("role") or "",
                         action=x.get("action") or "", detail=x.get("detail") or "", uid=x.get("uid")))
        for i, x in enumerate(s["agreeLogs"], 1):
            db.add(AgreeLog(id=i, doc=x["doc"], ver=x["ver"], uid=x["uid"], at=x.get("at") or ""))
        db.add(Setting(k="content", v=s["content"]))
        db.add(Setting(k="config", v=s["config"]))
        db.add(Setting(k="cfg", v=s["cfg"]))
        db.add(Setting(k="push", v=s["push"]))
        db.add(Setting(k="agreements", v=s["agreements"]))
        db.add(Setting(k="seq", v=s["seq"]))
        db.add(Setting(k="ledger", v=s.get("ledger") or {}))
        db.add(Setting(k="settleWeek", v=s.get("settleWeek") or {}))
        db.add(Setting(k="staff", v=s.get("staff") or {}))
        db.flush()
        # Keep demo pending tickets alive regardless of wall-clock vs prototype date.
        import time
        live = int(time.time() * 1000) + 30 * 60 * 1000
        for r in db.query(Recharge).filter(Recharge.status == "PENDING_PAY"):
            r.expire_at = live
        for o in db.query(Order).filter(Order.status == "PENDING_PAY"):
            o.expire_at = live
        for w in db.query(Withdrawal).filter(Withdrawal.status == "PENDING_CONFIRM"):
            w.expire_at = live
        db.commit()
        return {"ok": True, "skipped": False}
    finally:
        db.close()


if __name__ == "__main__":
    print(seed_all(reset=True))
