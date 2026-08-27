from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

import cache
import logic as L
from database import get_db
from models import (
    AgreeLog, Card, CardTpl, Category, Champ, CoinAdjust, DailyBiz, Deactivation,
    GameRecord, OpLog, Order, Product, Project, Recharge, SettleLog, SignRule,
    TableSeat, Team, Tier, User, VerifyLog, Withdrawal,
)
from seed_db import seed_all

app = FastAPI(title="玩咖桌游酒吧 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_IMG = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def uid_from_headers(authorization: Optional[str], x_user_id: Optional[int]) -> int | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            found = cache.session_get(token)
            if found:
                return found
        except Exception:
            pass
        if token.isdigit():
            return int(token)
    if x_user_id:
        return int(x_user_id)
    return None


def current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[int] = Header(default=None),
):
    uid = uid_from_headers(authorization, x_user_id)
    if not uid:
        raise HTTPException(401, "未登录")
    L.expire_timeouts(db)
    user = L.u(db, uid)
    if not user or user.status == "DEACTIVATED":
        raise HTTPException(401, "账号不可用")
    return L.public_user(db, user)


def staff_user(user: dict = Depends(current_user)):
    if user["role"] not in ("STAFF", "MANAGER", "BOSS"):
        raise HTTPException(403, "需要店员权限")
    return user


def admin_user(user: dict = Depends(current_user)):
    if user["role"] not in ("MANAGER", "BOSS"):
        raise HTTPException(403, "需要店长或老板权限")
    return user


def fail(e: Exception):
    raise HTTPException(400, str(e))


class LoginIn(BaseModel):
    userId: int


class RegisterIn(BaseModel):
    nick: str = "玩咖用户"
    agreed: bool = False


class OrderIn(BaseModel):
    items: list
    payType: str = "COIN"
    tableId: Optional[int] = None
    remark: str = ""


class RechargeIn(BaseModel):
    tierId: int


class WithdrawIn(BaseModel):
    pts: int


class ExchangeIn(BaseModel):
    tplId: int
    qty: int = 1


class VerifyIn(BaseModel):
    cardIds: list[int]


class ReasonIn(BaseModel):
    reason: str = ""


class GameIn(BaseModel):
    projectId: int
    tableId: Optional[int] = None
    players: list
    winners: list[int] = []
    event: str = ""


class ProfileIn(BaseModel):
    nick: Optional[str] = None
    gender: Optional[int] = None


class PatchIn(BaseModel):
    data: dict


@app.on_event("startup")
def on_startup():
    seed_all(reset=False)


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = L.u(db, body.userId)
    if not user:
        raise HTTPException(404, "用户不存在")
    try:
        token = cache.session_create(user.id)
    except Exception:
        token = str(user.id)
    return {"token": token, "user": L.public_user(db, user)}


@app.get("/api/dev/accounts")
def accounts(db: Session = Depends(get_db)):
    customers = [L.public_user(db, x) for x in db.query(User).filter_by(role="CUSTOMER", status="ACTIVE").limit(8)]
    staff = [L.public_user(db, x) for x in db.query(User).filter(User.role != "CUSTOMER")]
    return {"customers": customers, "staff": staff}


@app.post("/api/dev/reset")
def dev_reset():
    seed_all(reset=True)
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    cards = db.query(Card).filter_by(uid=user["id"], status="UNUSED").all()
    days = L.signed_days(db, user["id"])
    return {
        "user": user,
        "signedToday": 25 in days,
        "signDays": len(days),
        "streak": user.get("signStreak") or 0,
        "usableCards": len(cards),
        "newRewardCards": sum(1 for c in cards if c.src == "SETTLE_REWARD" and (c.days_left or 0) > 5),
        "expiring": sum(1 for c in cards if (c.days_left or 0) <= 3),
        "config": L.setting(db, "config"),
        "cfg": L.setting(db, "cfg"),
        "shop": (L.setting(db, "content") or {}).get("shopInfo"),
        "agreements": L.setting(db, "agreements"),
        "push": L.setting(db, "push"),
        "content": L.setting(db, "content"),
    }


@app.post("/api/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    try:
        user = L.register(db, body.nick, body.agreed)
        try:
            token = cache.session_create(user.id)
        except Exception:
            token = str(user.id)
        return {"token": token, "user": L.public_user(db, user)}
    except ValueError as e:
        fail(e)


@app.post("/api/signin")
def signin(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.do_sign(db, user["id"])
    except ValueError as e:
        fail(e)


@app.get("/api/home")
def home(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[int] = Header(default=None),
):
    uid = uid_from_headers(authorization, x_user_id)
    user = L.public_user(db, L.u(db, uid)) if uid else None
    content = L.setting(db, "content") or {}
    days = L.signed_days(db, uid) if uid else []
    return {
        "user": user,
        "gallery": content.get("gallery") or [],
        "shop": content.get("shopInfo") or {},
        "howToPlay": content.get("howToPlay") or [],
        "signed": days,
        "signPoints": (L.setting(db, "config") or {}).get("signPoints"),
        "signedToday": 25 in days,
    }


@app.get("/api/content")
def content(db: Session = Depends(get_db)):
    return L.setting(db, "content")


@app.get("/api/products")
def products(db: Session = Depends(get_db)):
    cats = [c.to_dict() for c in db.query(Category).filter_by(disabled=False).order_by(Category.sort)]
    plist = [p.to_dict() for p in db.query(Product).filter_by(offline=False)]
    tables = [t.to_dict() for t in db.query(TableSeat).all()]
    return {"cats": cats, "products": plist, "tables": tables}


@app.post("/api/orders")
def create_order(body: OrderIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.create_order(db, user["id"], body.items, body.payType, body.tableId, body.remark)
    except ValueError as e:
        fail(e)


@app.get("/api/orders")
def list_orders(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    L.expire_timeouts(db)
    return [o.to_dict() for o in db.query(Order).filter_by(uid=user["id"]).order_by(Order.id.desc())]


@app.post("/api/orders/{oid}/cancel")
def cancel_order(oid: int, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.cancel_order(db, user["id"], oid)
    except ValueError as e:
        fail(e)


@app.get("/api/recharges")
def list_recharges(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    L.expire_timeouts(db)
    pending = db.query(Recharge).filter_by(uid=user["id"], status="PENDING_PAY").first()
    latest = db.query(Recharge).filter_by(uid=user["id"]).order_by(Recharge.id.desc()).first()
    return {
        "tiers": [t.to_dict() for t in db.query(Tier).all()],
        "pending": pending.to_dict() if pending else None,
        "latest": latest.to_dict() if latest else None,
        "remain": L.remain(pending.expire_at) if pending else None,
    }


@app.post("/api/recharges")
def create_recharge(body: RechargeIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.create_recharge(db, user["id"], body.tierId)
    except ValueError as e:
        fail(e)


@app.post("/api/recharges/{rid}/cancel")
def cancel_recharge(rid: int, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.cancel_recharge(db, user["id"], rid)
    except ValueError as e:
        fail(e)


@app.get("/api/points")
def points(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    p = L.point_of(db, user["id"])
    pw = db.query(Withdrawal).filter_by(uid=user["id"], status="PENDING_CONFIRM").first()
    his = [w.to_dict() for w in db.query(Withdrawal).filter_by(uid=user["id"]).order_by(Withdrawal.id.desc()).limit(8)]
    tpls = [t.to_dict() for t in db.query(CardTpl).all() if t.exch is not False and (t.cost or 0) > 0]
    return {"point": p, "pending": pw.to_dict() if pw else None, "history": his, "tpls": tpls,
            "remain": L.remain(pw.expire_at) if pw else None}


@app.post("/api/withdrawals")
def create_wdr(body: WithdrawIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.create_withdraw(db, user["id"], body.pts)
    except ValueError as e:
        fail(e)


@app.post("/api/withdrawals/cancel")
def cancel_wdr(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.cancel_withdraw(db, user["id"])
    except ValueError as e:
        fail(e)


@app.post("/api/exchange")
def exchange(body: ExchangeIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        L.do_exchange(db, user["id"], body.tplId, body.qty)
        return {"ok": True}
    except ValueError as e:
        fail(e)


@app.get("/api/cards")
def cards(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    lst = []
    for c in db.query(Card).filter_by(uid=user["id"]).all():
        tm = L.tpl(db, c.tpl)
        lst.append({**c.to_dict(), "tplInfo": tm.to_dict() if tm else None})
    return lst


@app.post("/api/cards/verify-code")
def gen_code(body: VerifyIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        vc = L.gen_verify(db, user["id"], body.cardIds)
        return {**vc, "remain": L.remain(vc["expireAt"])}
    except ValueError as e:
        fail(e)


@app.get("/api/cards/verify-code/{code}")
def get_code(code: str, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    L.expire_timeouts(db)
    full, vc = cache.verify_find(code)
    if not vc or vc.get("uid") != user["id"]:
        raise HTTPException(404, "核销码不存在")
    cards = []
    for cid in vc["cardIds"]:
        c = db.get(Card, cid)
        cards.append({**c.to_dict(), "tplInfo": L.tpl(db, c.tpl).to_dict()} if c else None)
    return {**vc, "code": full or vc["code"], "cards": cards, "remain": L.remain(vc.get("expireAt"))}


@app.get("/api/rank")
def rank(kind: str = "SHARD", dim: str = "WEEK", subject: str = "TEAM",
         db: Session = Depends(get_db),
         authorization: Optional[str] = Header(default=None),
         x_user_id: Optional[int] = Header(default=None)):
    uid = uid_from_headers(authorization, x_user_id)
    me = L.u(db, uid) if uid else None
    rows = L.rank_rows(db, kind, dim, subject)
    mine = None
    if me:
        if subject == "USER":
            mine = next((r for r in rows if r.get("user") and r["user"]["id"] == me.id), None)
        else:
            mine = next((r for r in rows if r.get("team") and r["team"]["id"] == me.team_id), None)
    return {"rows": rows[:20], "mine": mine, "cfg": L.setting(db, "cfg")}


@app.get("/api/champions")
def champions(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    list_ = [c.to_dict() for c in db.query(Champ).filter_by(uid=user["id"]).all()]
    return {"list": list_, "total": len(list_), "month": sum(1 for c in list_ if str(c.get("date")).startswith("2026-08"))}


@app.get("/api/shards")
def shards(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    recs = []
    for g in db.query(GameRecord).order_by(GameRecord.id.desc()).all():
        p = next((x for x in (g.players or []) if x["uid"] == user["id"]), None)
        if p:
            recs.append({**g.to_dict(), "my": p})
    return {"shard": L.shard_of(db, user["id"]), "records": recs[:30]}


@app.get("/api/teams/{tid}")
def team_detail(tid: int, db: Session = Depends(get_db)):
    t = L.team(db, tid)
    if not t:
        raise HTTPException(404, "战队不存在")
    ms = [L.public_user(db, x) for x in L.custs(db) if x.team_id == tid]
    return {"team": {"id": t.id, "name": t.name}, "members": ms,
            "champs": sum(L.champ_count(db, x.id) for x in L.custs(db) if x.team_id == tid)}


@app.put("/api/profile")
def profile(body: ProfileIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    usr = L.u(db, user["id"])
    if body.nick:
        usr.nick = body.nick.strip()[:12]
    if body.gender is not None:
        usr.gender = body.gender
    return L.public_user(db, usr)


@app.post("/api/deactivate")
def deactivate(body: ReasonIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    try:
        return L.deactivate(db, user["id"], body.reason)
    except ValueError as e:
        fail(e)


def enrich_order(db: Session, o: Order) -> dict:
    usr = L.u(db, o.uid)
    c = L.coin_of(db, o.uid)
    bal = c["p"] + c["b"]
    lack = max(0, o.total - bal) if o.pay_type == "COIN" else 0
    return {**o.to_dict(), "user": L.public_user(db, usr), "balance": bal, "lack": lack, "remain": L.remain(o.expire_at)}


def today_amt(db: Session) -> int:
    t = db.get(DailyBiz, L.TODAY)
    return (t.coin + t.offline) if t else 0


@app.get("/api/staff/todo")
def staff_todo(staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    L.expire_timeouts(db)
    pa = [enrich_order(db, o) for o in db.query(Order).filter_by(status="PENDING_ACCEPT")]
    pp_re = [{**r.to_dict(), "user": L.public_user(db, L.u(db, r.uid)), "remain": L.remain(r.expire_at)}
             for r in db.query(Recharge).filter_by(status="PENDING_PAY")]
    pp_od = [enrich_order(db, o) for o in db.query(Order).filter_by(status="PENDING_PAY")]
    pp_wd = [{**w.to_dict(), "user": L.public_user(db, L.u(db, w.uid)), "remain": L.remain(w.expire_at)}
             for w in db.query(Withdrawal).filter_by(status="PENDING_CONFIRM")]
    mk = [enrich_order(db, o) for o in db.query(Order).filter_by(status="MAKING")]
    st = L.job_stat(db, staff["id"], "today")
    shop = today_amt(db) if staff["role"] in ("MANAGER", "BOSS") else None
    return {
        "accept": pa, "recharges": pp_re, "payOrders": pp_od, "withdrawals": pp_wd, "making": mk,
        "stat": {k: st[k] for k in ("amount", "orders", "verifies", "games", "wds", "rcAmt", "odAmt")},
        "shopAmt": shop, "role": staff["role"], "codes": [],
    }


@app.post("/api/staff/orders/{oid}/accept")
def api_accept(oid: int, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.accept_order(db, oid, staff)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/orders/{oid}/reject")
def api_reject(oid: int, body: ReasonIn, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.reject_order(db, oid, body.reason or "拒单", staff)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/orders/{oid}/confirm-pay")
def api_pay(oid: int, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.confirm_pay_order(db, oid, staff)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/orders/{oid}/finish")
def api_finish(oid: int, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.finish_order(db, oid)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/recharges/{rid}/confirm")
def api_rc_ok(rid: int, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        if not cache.idem_begin(f"rc:{rid}"):
            raise HTTPException(400, "请勿重复提交")
    except HTTPException:
        raise
    except Exception:
        pass
    try:
        return L.confirm_recharge(db, rid, staff)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/recharges/{rid}/reject")
def api_rc_no(rid: int, body: ReasonIn, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.reject_recharge(db, rid, body.reason or "拒绝", staff)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/withdrawals/{wid}/grant")
def api_wd_ok(wid: int, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        if not cache.idem_begin(f"wd:{wid}"):
            raise HTTPException(400, "请勿重复提交")
    except HTTPException:
        raise
    except Exception:
        pass
    try:
        return L.confirm_withdraw(db, wid, staff)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/withdrawals/{wid}/reject")
def api_wd_no(wid: int, body: ReasonIn, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.reject_withdraw(db, wid, body.reason or "驳回", staff)
    except ValueError as e:
        fail(e)


@app.get("/api/staff/verify/{code}")
def api_vprev(code: str, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.verify_preview(db, code)
    except ValueError as e:
        fail(e)


@app.post("/api/staff/verify/{code}/confirm")
def api_vok(code: str, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.verify_confirm(db, code, staff)
    except ValueError as e:
        fail(e)


@app.get("/api/staff/members")
def staff_members(q: str = "", staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    lst = L.custs(db)
    if q:
        lst = [x for x in lst if q in x.nick or q in x.tail or q in x.no]
    today_ids = {o.uid for o in db.query(Order).all()}
    lst = sorted(lst, key=lambda x: (0 if x.id in today_ids else 1, x.id))
    return [L.public_user(db, x) for x in lst]


@app.get("/api/staff/projects")
def staff_projects(staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    busy = {
        o.table_id
        for o in db.query(Order).filter(Order.status.in_(("PENDING_PAY", "PENDING_ACCEPT", "MAKING"))).all()
        if o.table_id
    }
    return {
        "projects": [p.to_dict() for p in db.query(Project).filter_by(disabled=False)],
        "tables": [t.to_dict() for t in db.query(TableSeat).all()],
        "busy": list(busy),
    }


@app.post("/api/staff/games")
def api_game(body: GameIn, staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    try:
        return L.submit_game(db, staff, body.projectId, body.tableId, body.players, body.winners, body.event)
    except ValueError as e:
        fail(e)


@app.get("/api/staff/jobs")
def staff_jobs(preset: str = "today", staff: dict = Depends(staff_user), db: Session = Depends(get_db)):
    return L.job_stat(db, staff["id"], preset)


@app.get("/api/admin/dashboard")
def admin_dash(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    return L.dashboard(db, admin["role"])


@app.get("/api/admin/jobs")
def admin_jobs(preset: str = "7d", admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    staff = db.query(User).filter(User.role != "CUSTOMER").all()
    keys = ("amount", "orders", "verifies", "games", "wds", "rcAmt", "odAmt")
    return [{"user": L.public_user(db, s), **{k: L.job_stat(db, s.id, preset)[k] for k in keys}} for s in staff]


COLL_MAP = {
    "orders": (Order, "to_dict"),
    "recharges": (Recharge, "to_dict"),
    "withdrawals": (Withdrawal, "to_dict"),
    "teams": (Team, None),
    "products": (Product, "to_dict"),
    "cats": (Category, "to_dict"),
    "cardTpls": (CardTpl, "to_dict"),
    "cards": (Card, "to_dict"),
    "tiers": (Tier, "to_dict"),
    "projects": (Project, "to_dict"),
    "gameRecords": (GameRecord, "to_dict"),
    "champs": (Champ, "to_dict"),
    "logs": (OpLog, "to_dict"),
    "settleLogs": (SettleLog, "to_dict"),
    "deactivations": (Deactivation, "to_dict"),
    "coinAdjusts": (CoinAdjust, "to_dict"),
    "dailyBiz": (DailyBiz, "to_dict"),
    "signRules": (SignRule, "to_dict"),
    "verifyLogs": (VerifyLog, "to_dict"),
}


@app.post("/api/admin/upload")
async def admin_upload(admin: dict = Depends(admin_user), file: UploadFile = File(...)):
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_IMG.get(ctype)
    if not ext:
        suf = Path(file.filename or "").suffix.lower()
        if suf == ".jpeg":
            suf = ".jpg"
        if suf in {".jpg", ".png", ".webp", ".gif"}:
            ext = suf
    if not ext:
        raise HTTPException(400, "仅支持 jpg / png / webp / gif")
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(400, "图片需 ≤ 2MB")
    name = uuid4().hex + ext
    (UPLOAD_DIR / name).write_bytes(raw)
    return {"url": f"/uploads/{name}"}


@app.get("/api/admin/{coll}")
def admin_list(coll: str, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if coll == "members":
        return [L.public_user(db, x) for x in db.query(User).all()]
    if coll == "staff":
        return [L.public_user(db, x) for x in db.query(User).filter(User.role != "CUSTOMER")]
    if coll in ("agreements", "content", "config", "cfg", "push"):
        return L.setting(db, coll)
    if coll not in COLL_MAP:
        raise HTTPException(404, "unknown collection")
    model, meth = COLL_MAP[coll]
    rows = db.query(model).all()
    if meth:
        return [getattr(x, meth)() for x in rows]
    return [{"id": x.id, "name": x.name} for x in rows]


@app.put("/api/admin/{coll}")
def admin_put(coll: str, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if coll in ("tiers", "cfg", "staff", "config") and admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    if coll in ("config", "cfg", "content", "push"):
        cur = dict(L.setting(db, coll) or {})
        cur.update(body.data)
        L.save_setting(db, coll, cur)
        return {"ok": True}
    raise HTTPException(400, "不支持整表覆盖，请用 item 接口")


@app.post("/api/admin/products")
def save_product(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    item = body.data
    if item.get("id"):
        p = db.get(Product, item["id"])
        if not p:
            raise HTTPException(404, "商品不存在")
        for k, attr in (("name", "name"), ("cid", "cid"), ("desc", "desc"), ("price", "price"),
                        ("hasSpec", "has_spec"), ("specMulti", "spec_multi"), ("specs", "specs"),
                        ("soldOut", "sold_out"), ("img", "img"), ("type", "type"), ("combo", "combo"),
                        ("offline", "offline")):
            if k in item:
                setattr(p, attr, item[k])
        return p.to_dict()
    p = Product(
        id=L.new_id(db, Product), cid=item.get("cid") or 0, name=item.get("name") or "",
        desc=item.get("desc") or "", price=item.get("price") or 0,
        has_spec=bool(item.get("hasSpec")), spec_multi=bool(item.get("specMulti")),
        specs=item.get("specs"), sold_out=bool(item.get("soldOut")), img=item.get("img"),
        type=item.get("type"), combo=item.get("combo"), offline=bool(item.get("offline")),
    )
    db.add(p)
    db.flush()
    return p.to_dict()


@app.post("/api/admin/coin-adjust/{aid}/{action}")
def coin_adjust(aid: int, action: str, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板审批")
    try:
        return L.approve_coin_adjust(db, aid, action)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/deactivations/{did}/{action}")
def deact_act(did: int, action: str, body: ReasonIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.exec_deactivation(db, did, action, body.reason, admin)
    except ValueError as e:
        fail(e)


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

ADMIN_DIR = Path(__file__).resolve().parent / "admin"
if (ADMIN_DIR / "index.html").is_file():
    app.mount("/", StaticFiles(directory=str(ADMIN_DIR), html=True), name="admin")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
