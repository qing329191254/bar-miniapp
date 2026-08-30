from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

import cache
import logic as L
from database import get_db
from models import (
    AgreeLog, Card, CardTpl, Category, Champ, CoinAdjust, DailyBiz, Deactivation,
    GameRecord, OpLog, Order, Product, Project, Recharge, SettleLog, SignRule,
    TableSeat, Team, Tier, User, VerifyLog, Wallet, Withdrawal,
)
from seed_db import seed_all
from settings import cloud_env_id, cos_public_base, host_for_log, in_cloud, is_loopback, mysql_url, redis_url
import weixin

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


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


def uid_from_headers(authorization: Optional[str]) -> int | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            found = cache.session_get(token)
            if found:
                return found
        except Exception:
            return None
    return None


def current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    uid = uid_from_headers(authorization)
    if not uid:
        raise HTTPException(401, "未登录")
    L.expire_timeouts(db)
    user = L.u(db, uid)
    if not user or user.status == "DEACTIVATED":
        raise HTTPException(401, "账号不可用")
    if user.status == "DISABLED":
        raise HTTPException(401, "账号已停用")
    if user.role == "CUSTOMER" and L.agreement_reconsent_required(db, user.id):
        raise HTTPException(401, "协议已重大更新，请重新阅读并同意")
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
    account: str = ""
    password: str = ""
    code: str = ""
    phoneCode: str = ""
    agreed: bool = False
    termsVersion: int = 0
    privacyVersion: int = 0


class WxLoginIn(BaseModel):
    code: str = ""
    phoneCode: str = ""
    agreed: bool = False
    termsVersion: int = 0
    privacyVersion: int = 0


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


class VoidGameIn(BaseModel):
    reason: str = ""
    voidCards: bool = True


class GameIn(BaseModel):
    projectId: int
    tableId: Optional[int] = None
    players: list
    winners: list[int] = []
    event: str = ""
    round: str = ""
    time: str = ""


class ProfileIn(BaseModel):
    nick: Optional[str] = None
    gender: Optional[int] = None


class PatchIn(BaseModel):
    data: dict


@app.on_event("startup")
def on_startup():
    import time

    db_url = mysql_url()
    if in_cloud() and is_loopback(db_url):
        raise RuntimeError(
            "云托管未配置数据库：容器里没有 127.0.0.1 的 MySQL。"
            "请在 api 服务「环境变量」填写 MYSQL_ADDRESS（内网地址，形如 10.x.x.x:3306）、"
            "MYSQL_USERNAME、MYSQL_PASSWORD、MYSQL_DATABASE=wanka。"
        )
    print("MySQL ->", host_for_log(db_url))
    print("Redis ->", host_for_log(redis_url()))
    last = None
    for i in range(12):
        try:
            seed_all(reset=False)
            return
        except Exception as e:
            last = e
            print(f"MySQL not ready ({i + 1}/12): {e}")
            time.sleep(5)
    raise last


def session_payload(db: Session, user: User) -> dict:
    token = cache.session_create(user.id)
    return {"token": token, "user": L.public_user(db, user)}


def login_with_wx(code: str, phone_code: str, agreed: bool, terms_version: int,
                  privacy_version: int, db: Session) -> dict:
    agreements = L.setting(db, "agreements") or {}
    current_terms = int((agreements.get("terms") or {}).get("ver") or 1)
    current_privacy = int((agreements.get("privacy") or {}).get("ver") or 1)
    if not agreed:
        raise HTTPException(400, "请先阅读并同意协议")
    if terms_version != current_terms or privacy_version != current_privacy:
        raise HTTPException(409, "协议已更新，请重新阅读并同意")
    if not (phone_code or "").strip():
        raise HTTPException(400, "请授权手机号")
    try:
        openid = weixin.code2openid(code)
        phone_full = weixin.phone_from_code(phone_code)
    except ValueError as e:
        raise HTTPException(401, str(e))
    user = L.register_wx(db, openid, phone_full)
    if user.status == "DEACTIVATED":
        raise HTTPException(401, "账号不可用")
    L.record_agreement(db, user, current_terms, current_privacy)
    return session_payload(db, user)


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    if (body.code or "").strip():
        return login_with_wx(body.code, body.phoneCode, body.agreed, body.termsVersion,
                             body.privacyVersion, db)
    raw = (body.account or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        raise HTTPException(400, "请输入数字账号")
    user = db.query(User).filter(User.no == digits).first()
    if not user:
        user = db.query(User).filter(User.no == digits.zfill(6)).first()
    if not user:
        raise HTTPException(404, "账号或密码错误")
    if user.status == "DEACTIVATED":
        raise HTTPException(401, "账号不可用")
    if user.status == "DISABLED":
        raise HTTPException(401, "账号已停用")
    if user.role == "CUSTOMER":
        raise HTTPException(403, "会员请使用一键登录")
    if not L.check_pwd(user, body.password):
        raise HTTPException(401, "账号或密码错误")
    return session_payload(db, user)


@app.post("/api/auth/wx")
def wx_login(body: WxLoginIn, db: Session = Depends(get_db)):
    return login_with_wx(body.code, body.phoneCode, body.agreed, body.termsVersion,
                         body.privacyVersion, db)


@app.get("/api/dev/accounts")
def accounts(db: Session = Depends(get_db)):
    if in_cloud():
        raise HTTPException(404, "Not found")
    customers = [L.public_user(db, x) for x in db.query(User).filter_by(role="CUSTOMER", status="ACTIVE").limit(8)]
    staff = [L.public_user(db, x) for x in db.query(User).filter(User.role != "CUSTOMER")]
    return {"customers": customers, "staff": staff}


@app.post("/api/dev/reset")
def dev_reset():
    if in_cloud():
        raise HTTPException(404, "Not found")
    seed_all(reset=True)
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    cards = db.query(Card).filter_by(uid=user["id"], status="UNUSED").all()
    days = L.signed_days(db, user["id"])
    return {
        "user": user,
        "signedToday": L.today_day() in days,
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
        return session_payload(db, user)
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
):
    uid = uid_from_headers(authorization)
    user = L.public_user(db, L.u(db, uid)) if uid else None
    content = L.setting(db, "content") or {}
    days = L.signed_days(db, uid) if uid else []
    streak = 0
    if uid:
        w = db.get(Wallet, uid)
        streak = int(w.sign_streak or 0) if w else 0
    return {
        "user": user,
        "gallery": content.get("gallery") or [],
        "shop": content.get("shopInfo") or {},
        "howToPlay": content.get("howToPlay") or {},
        "signed": days,
        "signPoints": (L.setting(db, "config") or {}).get("signPoints"),
        "signedToday": L.today_day() in days,
        "streak": streak,
        "signRules": L.sign_rules_view(db),
        "signMonth": L.current_month(),
        "signToday": L.today_day(),
    }


@app.get("/api/content")
def content(db: Session = Depends(get_db)):
    return L.setting(db, "content")


@app.get("/api/agreements")
def public_agreements(db: Session = Depends(get_db)):
    docs = L.setting(db, "agreements") or {}
    return {"terms": docs.get("terms") or {}, "privacy": docs.get("privacy") or {}}


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
    cfg = L.setting(db, "config") or {}
    return {
        "tiers": [t.to_dict() for t in db.query(Tier).all()],
        "pending": pending.to_dict() if pending else None,
        "latest": latest.to_dict() if latest else None,
        "remain": L.remain(pending.expire_at) if pending else None,
        "coin": L.coin_of(db, user["id"]),
        "singleLimit": int(cfg.get("singleLimit") or 0),
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
            "remain": L.remain(pw.expire_at) if pw else None, **L.point_period()}


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
    vc = L.find_verify(db, code)
    if not vc or vc.uid != user["id"]:
        raise HTTPException(404, "核销码不存在")
    cards = []
    for cid in vc.card_ids or []:
        c = db.get(Card, cid)
        cards.append({**c.to_dict(), "tplInfo": L.tpl(db, c.tpl).to_dict()} if c else None)
    return {**L.verify_code_dict(vc), "cards": cards, "remain": L.remain(vc.expire_at)}


@app.get("/api/rank")
def rank(kind: str = "SHARD", dim: str = "WEEK", subject: str = "TEAM",
         db: Session = Depends(get_db),
         authorization: Optional[str] = Header(default=None)):
    uid = uid_from_headers(authorization)
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
    return {"list": list_, "total": len(list_), "month": sum(1 for c in list_ if str(c.get("date")).startswith(L.current_month()))}


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
    users = [x for x in L.custs(db) if x.team_id == tid]
    members = []
    for x in users:
        wallet = L.wallet_of(db, x.id)
        members.append({
            **L.public_user(db, x), "champions": L.champ_count(db, x.id),
            "shardWeek": int(wallet.shard_w or 0), "shardTotal": int(wallet.shard_t or 0),
        })
    members.sort(key=lambda x: -x["shardWeek"])
    champ_total = sum(x["champions"] for x in members)
    user_ids = {x.id for x in users}
    champ_month = sum(1 for c in db.query(Champ).all() if c.uid in user_ids and str(c.date).startswith(L.current_month()))
    rank_rows = L.rank_rows(db, "SHARD", "WEEK", "TEAM")
    rank = next((r["rank"] for r in rank_rows if r.get("team", {}).get("id") == tid), None)
    records = []
    for c in db.query(Champ).filter(Champ.uid.in_(user_ids)).order_by(Champ.date.desc(), Champ.id.desc()).all():
        winner = L.u(db, c.uid)
        records.append({**c.to_dict(), "nick": winner.nick if winner else "—"})
    return {
        "team": {"id": t.id, "name": t.name}, "members": members,
        "champs": champ_total, "monthChamps": champ_month,
        "shardWeek": sum(x["shardWeek"] for x in members),
        "shardTotal": sum(x["shardTotal"] for x in members),
        "rank": rank, "records": records,
    }


@app.put("/api/profile")
def profile(body: ProfileIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    usr = L.u(db, user["id"])
    if body.nick is not None:
        nick = body.nick.strip()
        if not 2 <= len(nick) <= 12:
            raise HTTPException(400, "昵称长度需为 2-12 个字符")
        usr.nick = nick
    if body.gender is not None:
        if body.gender not in (0, 1, 2):
            raise HTTPException(400, "性别参数不正确")
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
    t = db.get(DailyBiz, L.today_str())
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
        "stat": {k: st[k] for k in ("amount", "orders", "verifies", "games", "heads", "wds", "rcAmt", "odAmt")},
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
        return L.submit_game(db, staff, body.projectId, body.tableId, body.players, body.winners, body.event, body.round, body.time)
    except ValueError as e:
        fail(e)


@app.get("/api/staff/jobs")
def staff_jobs(
    preset: str = "today",
    from_: str = Query("", alias="from"),
    to: str = "",
    staff: dict = Depends(staff_user),
    db: Session = Depends(get_db),
):
    return L.job_stat(db, staff["id"], preset, from_, to)


@app.get("/api/admin/dashboard")
def admin_dash(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    return L.dashboard(db, admin["role"])


@app.get("/api/admin/liab/coin")
def admin_liab_coin(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可见")
    return L.liab_coin_detail(db, page, page_size)


@app.get("/api/admin/liab/point")
def admin_liab_point(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可见")
    return L.liab_point_detail(db, page, page_size)


@app.get("/api/admin/liab/cards")
def admin_liab_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可见")
    return L.liab_card_detail(db, page, page_size)


@app.get("/api/admin/alert/points")
def admin_alert_points(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.point_alert_detail(db, page, page_size)


@app.get("/api/admin/games/{gid}/void-preview")
def admin_void_game_preview(gid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    return L.void_game_preview(db, gid)


@app.post("/api/admin/games/{gid}/void")
def admin_void_game(gid: int, body: VoidGameIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    return L.void_game(db, gid, body.reason, body.voidCards, admin)


@app.get("/api/admin/jobs-page")
def admin_jobs_page(
    preset: str = "7d",
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    op_uid: int = Query(0, alias="opUid"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.jobs_page(db, preset, date_from, date_to, op_uid)


@app.get("/api/admin/jobs")
def admin_jobs(preset: str = "7d", admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    page = L.jobs_page(db, preset)
    return page["rows"]


@app.get("/api/admin/reports-page")
def admin_reports_page(
    preset: str = "7d",
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    tab: str = "biz",
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.reports_page(db, preset, date_from, date_to, tab, admin.get("role") == "BOSS", page, page_size)


@app.get("/api/admin/jobs/{uid}")
def admin_job_detail(
    uid: int,
    preset: str = "today",
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    tab: str = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.job_detail(db, uid, preset, date_from, date_to, page, page_size, tab)


@app.get("/api/admin/orders-page")
def admin_orders_page(
    preset: str = "all",
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    op_uid: int = Query(0, alias="opUid"),
    status: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.orders_page(db, preset, date_from, date_to, op_uid, status, page, page_size)


@app.get("/api/admin/withdrawals-page")
def admin_withdrawals_page(
    preset: str = "all",
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    op_uid: int = Query(0, alias="opUid"),
    status: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.withdrawals_page(db, preset, date_from, date_to, op_uid, status, page, page_size)


@app.get("/api/admin/recharges-page")
def admin_recharges_page(
    preset: str = "all",
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    op_uid: int = Query(0, alias="opUid"),
    member_uid: int = Query(0, alias="uid"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.recharges_page(db, preset, date_from, date_to, op_uid, member_uid, page, page_size)


@app.post("/api/admin/recharges/{rid}/confirm")
def admin_confirm_recharge(rid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        if not cache.idem_begin(f"rc:{rid}"):
            raise HTTPException(400, "请勿重复提交")
    except HTTPException:
        raise
    except Exception:
        pass
    try:
        return L.confirm_recharge(db, rid, admin)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/recharges/{rid}/reject")
def admin_reject_recharge(rid: int, body: ReasonIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    reason = (body.reason or "").strip()
    if len(reason) < 2:
        raise HTTPException(400, "拒绝原因至少 2 个字")
    try:
        return L.reject_recharge(db, rid, reason, admin)
    except ValueError as e:
        fail(e)


@app.get("/api/admin/daily-biz")
def daily_biz_page(
    preset: str = "7d",
    date_from: str = Query("", alias="from"),
    date_to: str = Query("", alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.daily_biz_page(db, preset, date_from, date_to, page, page_size)


@app.get("/api/admin/coin-adjust")
def coin_adjust_page(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.coin_adjust_page(db, page, page_size)


@app.post("/api/admin/coin-adjust/{aid}/{action}")
def coin_adjust(aid: int, action: str, body: ReasonIn = ReasonIn(), admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板审批")
    try:
        return L.approve_coin_adjust(db, aid, action, admin, body.reason or "")
    except ValueError as e:
        fail(e)


@app.get("/api/admin/deactivation")
def deactivation_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=0, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    return L.deactivation_page(db, page, page_size)


@app.get("/api/admin/deactivation/{did}")
def deactivation_one(did: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.deactivation_detail(db, did)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/deactivations/{did}/{action}")
def deact_act(did: int, action: str, body: ReasonIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.exec_deactivation(db, did, action, body.reason, admin)
    except ValueError as e:
        fail(e)


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
    "agreeLogs": (AgreeLog, "to_dict"),
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
    if not raw:
        raise HTTPException(400, "图片内容为空")
    name = uuid4().hex + ext
    cloud_path = f"wanka/uploads/{name}"
    try:
        weixin.upload_cloud_file(cloud_env_id(), cloud_path, raw, ctype or "application/octet-stream")
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"url": f"{cos_public_base()}/{cloud_path}"}


@app.get("/api/admin/team-management")
def team_management(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    teams = []
    for team in db.query(Team).order_by(Team.id).all():
        members = []
        for user in db.query(User).filter(
            User.role == "CUSTOMER", User.status == "ACTIVE", User.team_id == team.id,
        ).order_by(User.id).all():
            wallet = L.wallet_of(db, user.id)
            members.append({
                "id": user.id, "nick": user.nick, "no": user.no,
                "champions": L.champ_count(db, user.id), "shard": int(wallet.shard_w or 0),
            })
        teams.append({
            "id": team.id, "name": team.name, "logo": team.logo or team.name[:1],
            "status": team.status or "ACTIVE", "members": members,
            "champions": sum(x["champions"] for x in members),
            "shard": sum(x["shard"] for x in members),
        })
    return {"teams": teams}


@app.post("/api/admin/teams")
def create_team(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    name = str(data.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "请填写战队名称")
    if db.query(Team).filter(Team.name == name).first():
        raise HTTPException(400, "该战队名称已存在")
    logo_raw = str(data.get("logo") or name[:1] or "队").strip()
    team = Team(id=L.new_id(db, Team), name=name[:32], logo=logo_raw[:1], status="ACTIVE")
    db.add(team)
    L.log(db, "TEAM_CHANGE", f"新增战队 {team.name}", None, admin)
    return {"id": team.id, "name": team.name, "logo": team.logo, "status": team.status}


@app.put("/api/admin/teams/{tid}")
def save_team(tid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    team = db.get(Team, tid)
    data = body.data or {}
    if not team:
        raise HTTPException(404, "战队不存在")
    name = str(data.get("name") or team.name).strip()
    if not name:
        raise HTTPException(400, "请填写战队名称")
    if db.query(Team).filter(Team.name == name, Team.id != tid).first():
        raise HTTPException(400, "该战队名称已存在")
    old_name = team.name
    team.name = name[:32]
    if "logo" in data:
        team.logo = str(data.get("logo") or team.name[:1] or "队")[:1]
    if "status" in data:
        status = str(data.get("status") or "ACTIVE").upper()
        if status not in ("ACTIVE", "DISABLED"):
            raise HTTPException(400, "状态无效")
        team.status = status
    L.log(db, "TEAM_CHANGE", f"编辑战队 {old_name} → {team.name} · 状态 {team.status}", None, admin)
    return {"id": team.id, "name": team.name, "logo": team.logo, "status": team.status}


@app.post("/api/admin/team-members/move")
def move_team_member(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    try:
        uid = int(data.get("uid"))
        target_id = data.get("teamId")
        target_id = int(target_id) if target_id not in (None, "", 0) else None
    except (TypeError, ValueError):
        raise HTTPException(400, "成员或目标战队不正确")
    user = db.get(User, uid)
    if not user or user.role != "CUSTOMER":
        raise HTTPException(404, "会员不存在")
    target = db.get(Team, target_id) if target_id else None
    if target_id and not target:
        raise HTTPException(404, "目标战队不存在")
    if target and (target.status or "ACTIVE") == "DISABLED":
        raise HTTPException(400, "该战队已停用")
    old = db.get(Team, user.team_id)
    if user.team_id == target_id:
        raise HTTPException(400, "成员已在该战队")
    user.team_id = target_id
    L.log(db, "TEAM_MEMBER_MOVE", f"{user.nick}：{old.name if old else '未分配'} → {target.name if target else '未分配'}", None, admin)
    return {"ok": True}


def _settle_dict(row: SettleLog) -> dict:
    return row.to_dict()


def _settlement_week(db: Session) -> str:
    period = L.setting(db, "settleWeek") or {}
    start, end = str(period.get("start") or ""), str(period.get("end") or "")
    return f"{start}~{end}" if start and end else ""


def _settlement_plan(db: Session) -> list[dict]:
    cfg = L.setting(db, "cfg") or {}
    dim = "MONTH" if cfg.get("rankDim") == "MONTH" else "WEEK"
    rank_range = max(1, int(cfg.get("rankRange") or 3))
    prize_map = cfg.get("prizeMap") or {}
    templates = {x.sub: x for x in db.query(CardTpl).filter(CardTpl.cat == "OTHER").all() if x.sub}
    rows: list[dict] = []
    seen: set[int] = set()

    if cfg.get("teamReward"):
        teams = L.rank_rows(db, "SHARD", dim, "TEAM")
        if teams:
            winner = teams[0]
            team = db.get(Team, int(winner["team"]["id"]))
            tm = templates.get(str(cfg.get("teamCard") or ""))
            if team and tm:
                members = db.query(User).filter(User.role == "CUSTOMER", User.status == "ACTIVE", User.team_id == team.id).all()
                for user in members:
                    shard = L.shard_of(db, user.id)["w" if dim == "WEEK" else "t"]
                    allowed = not cfg.get("reqShard") or shard > 0
                    rows.append({"uid": user.id, "target": team.name, "nick": user.nick, "type": "TEAM_CHAMPION",
                                 "sub": tm.sub, "desc": tm.name, "sh": shard, "eligible": allowed,
                                 "reason": "" if allowed else "本周期无碎片"})
                    if allowed:
                        seen.add(user.id)

    for ranked in L.rank_rows(db, "SHARD", dim, "USER"):
        rank = int(ranked.get("rank") or 0)
        if rank > rank_range:
            continue
        user_data = ranked.get("user") or {}
        uid = int(user_data.get("id") or 0)
        tm = templates.get(str(prize_map.get(str(rank)) or ""))
        if not uid or not tm:
            continue
        allowed = bool(cfg.get("stack", True)) or uid not in seen
        rows.append({"uid": uid, "target": "个人榜", "nick": user_data.get("nick") or "", "type": f"PERSONAL_RANK{rank}",
                     "sub": tm.sub, "desc": tm.name, "sh": int(ranked.get("v") or 0), "rank": rank,
                     "eligible": allowed, "reason": "" if allowed else "规则不允许叠加"})
        if allowed:
            seen.add(uid)
    return rows


@app.get("/api/admin/settlement/current")
def settlement_current(page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=50, alias="pageSize"), admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    configured = (L.setting(db, "settleWeek") or {}).get("start", "")
    weeks = sorted({x.week for x in db.query(SettleLog).all() if x.week}, reverse=True)
    week = next((x for x in weeks if configured and configured in x), weeks[0] if weeks else _settlement_week(db))
    query = db.query(SettleLog).filter(SettleLog.week == week).order_by(SettleLog.id)
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    granted = db.query(SettleLog).filter(SettleLog.week == week, SettleLog.status == "GRANTED").count()
    team = db.query(SettleLog).filter(SettleLog.week == week, SettleLog.status == "GRANTED", SettleLog.type == "TEAM_CHAMPION").count()
    personal = db.query(SettleLog).filter(SettleLog.week == week, SettleLog.status == "GRANTED", SettleLog.type.like("PERSONAL%" )).count()
    blocked = db.query(SettleLog).filter(SettleLog.week == week, SettleLog.status == "BLOCKED").count()
    return {"week": week, "rows": [_settle_dict(x) for x in rows], "total": total, "page": page, "pageSize": page_size,
            "executed": total > 0, "summary": {"granted": granted, "team": team, "personal": personal, "blocked": blocked},
            "cfg": L.setting(db, "cfg") or {}}


@app.get("/api/admin/settlement/preview")
def settlement_preview(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    rows = _settlement_plan(db)
    eligible = [x for x in rows if x["eligible"]]
    cfg = L.setting(db, "cfg") or {}
    dim = "MONTH" if cfg.get("rankDim") == "MONTH" else "WEEK"
    rank_range = max(1, int(cfg.get("rankRange") or 3))
    mapped = {int(k) for k, v in (cfg.get("prizeMap") or {}).items() if str(k).isdigit() and v}
    missing = sorted({int(x.get("rank") or 0) for x in L.rank_rows(db, "SHARD", dim, "USER") if int(x.get("rank") or 0) <= rank_range and int(x.get("rank") or 0) not in mapped})
    return {"week": _settlement_week(db), "rows": rows, "count": len(eligible),
            "cap": int(cfg.get("settleCap") or 20), "blocked": len(eligible) > int(cfg.get("settleCap") or 20),
            "cfg": {"rankDim": dim, "rankRange": rank_range, "teamReward": bool(cfg.get("teamReward")),
                    "stack": bool(cfg.get("stack", True)), "reqShard": bool(cfg.get("reqShard"))}, "missingRanks": missing}


@app.post("/api/admin/settlement/rerun")
def settlement_rerun(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    week = _settlement_week(db)
    if not week:
        raise HTTPException(400, "未配置结算周期")
    existing = db.query(SettleLog).filter(SettleLog.week == week).count()
    if existing:
        L.log(db, "SETTLE_RERUN", f"重跑 {week} · 幂等跳过，未重复发放", None, admin)
        return {"ok": True, "skipped": True, "message": "该周期已执行，本次幂等跳过，未重复发放"}
    plan = _settlement_plan(db)
    eligible = [x for x in plan if x["eligible"]]
    cap = int((L.setting(db, "cfg") or {}).get("settleCap") or 20)
    if len(eligible) > cap:
        for item in plan:
            db.add(SettleLog(id=L.next_seq(db, "settle"), uid=item["uid"], week=week, type=item["type"], sub=item["sub"],
                             target=item["target"], nick=item["nick"], sh=item["sh"],
                             status="BLOCKED" if item["eligible"] else "SKIPPED", card_id=None,
                             desc=item["desc"] if item["eligible"] else item["reason"]))
        L.log(db, "SETTLE_BLOCKED", f"{week} · 计划 {len(eligible)} 张超过单次上限 {cap} 张 · 整批拦截", None, admin)
        return {"ok": True, "blocked": True, "message": f"计划发放 {len(eligible)} 张超过单次上限 {cap} 张，已整批拦截，一张未发"}
    for item in plan:
        card_id = None
        status = "SKIPPED"
        desc = item["reason"] or item["desc"]
        if item["eligible"]:
            tm = db.query(CardTpl).filter(CardTpl.sub == item["sub"]).first()
            if tm:
                card = L.issue_card(db, item["uid"], tm, "SETTLE_REWARD", f"{week} · {item['target']}")
                card_id, status, desc = card.id, "GRANTED", tm.name
        db.add(SettleLog(id=L.next_seq(db, "settle"), uid=item["uid"], week=week, type=item["type"], sub=item["sub"],
                         target=item["target"], nick=item["nick"], sh=item["sh"], status=status,
                         card_id=card_id, desc=desc))
    L.log(db, "SETTLE_RUN", f"执行 {week} · 发放 {len(eligible)} 张", None, admin)
    return {"ok": True, "skipped": False, "message": f"结算完成，共发放 {len(eligible)} 张奖励"}


@app.post("/api/admin/settlement/force")
def settlement_force(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可强制发放")
    reason = str((body.data or {}).get("reason") or "").strip()
    if len(reason) < 2:
        raise HTTPException(400, "强制发放原因至少 2 个字")
    week = _settlement_week(db)
    blocked = db.query(SettleLog).filter(SettleLog.week == week, SettleLog.status == "BLOCKED").order_by(SettleLog.id).all()
    if not blocked:
        raise HTTPException(400, "本周期没有待处理的被拦截奖励")
    templates = {x.sub: x for x in db.query(CardTpl).filter(CardTpl.cat == "OTHER").all() if x.sub}
    granted = 0
    for row in blocked:
        tm = templates.get(row.sub)
        user = db.get(User, row.uid) if row.uid else None
        if not tm or not user or user.role != "CUSTOMER" or user.status != "ACTIVE":
            continue
        card = L.issue_card(db, user.id, tm, "SETTLE_REWARD", f"{week} · 强制发放：{reason}")
        row.card_id, row.status, row.force_reason = card.id, "GRANTED", reason[:128]
        granted += 1
    L.log(db, "SETTLE_FORCE", f"{week} · 强制发放 {granted} 张 · 原因：{reason}", None, admin)
    return {"ok": True, "message": f"已强制发放 {granted} 张奖励卡券"}


@app.post("/api/admin/settlement/manual")
def settlement_manual(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    try:
        uid, tpl_id = int(data.get("uid")), int(data.get("tplId"))
    except (TypeError, ValueError):
        raise HTTPException(400, "请选择会员和补发奖励")
    reason = str(data.get("reason") or "").strip()
    if len(reason) < 2:
        raise HTTPException(400, "补发原因至少 2 个字")
    user = db.get(User, uid)
    tm = db.get(CardTpl, tpl_id)
    if not user or user.role != "CUSTOMER" or user.status != "ACTIVE":
        raise HTTPException(400, "会员不存在或状态不可用")
    if not tm or tm.cat != "OTHER":
        raise HTTPException(400, "补发奖励不可用")
    week = _settlement_week(db)
    card = L.issue_card(db, uid, tm, "SETTLE_MANUAL", f"{week} · 手动补发：{reason}")
    row = SettleLog(id=L.next_seq(db, "settle"), uid=uid, week=week, type="MANUAL", sub=tm.sub or "",
                    target="手动补发", nick=user.nick, sh=L.shard_of(db, uid)["w"], status="GRANTED",
                    card_id=card.id, desc=f"{tm.name} · {reason}")
    db.add(row)
    L.log(db, "SETTLE_MANUAL", f"{week} · {user.nick} · {tm.name} · {reason}", None, admin)
    return _settle_dict(row)


@app.get("/api/admin/settlement/history")
def settlement_history(preset: str = "all", admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    rows = [_settle_dict(x) for x in db.query(SettleLog).order_by(SettleLog.id.desc()).all()]
    weeks: dict[str, list] = {}
    for row in rows:
        weeks.setdefault(row["week"] or "未标注周期", []).append(row)
    grouped = []
    for week, group in weeks.items():
        granted = [x for x in group if x["status"] == "GRANTED"]
        revoked = [x for x in group if x["status"] == "REVOKED"]
        grouped.append({"week": week, "rows": group, "winners": len({x["nick"] for x in group if x["nick"]}),
                        "team": sum(1 for x in group if x["type"] == "TEAM_CHAMPION"),
                        "personal": sum(1 for x in group if x["type"].startswith("PERSONAL")),
                        "manual": sum(1 for x in group if x["type"] == "MANUAL"),
                        "granted": len(granted), "revoked": len(revoked), "total": len(group)})
    return {"weeks": grouped, "rows": rows}


@app.post("/api/admin/settlement/{sid}/revoke")
def revoke_settlement(sid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可撤销结算奖励")
    reason = str((body.data or {}).get("reason") or "").strip()
    if len(reason) < 2:
        raise HTTPException(400, "撤销原因至少 2 个字")
    row = db.get(SettleLog, sid)
    if not row or row.status not in ("GRANTED", "BLOCKED"):
        raise HTTPException(400, "该奖励不能撤销")
    if row.card_id:
        card = db.get(Card, row.card_id)
        if card and card.status == "UNUSED":
            card.status = "VOID"
            card.void_reason = f"结算奖励撤销：{reason}"[:64]
    row.status = "REVOKED"
    L.log(db, "SETTLE_REVOKE", f"撤销 {row.week} · {row.nick} · {row.desc} · 原因：{reason}", None, admin)
    return _settle_dict(row)


@app.get("/api/admin/settlement-config")
def settlement_config(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    return {"cfg": L.setting(db, "cfg") or {}, "templates": [x.to_dict() for x in db.query(CardTpl).filter(CardTpl.cat == "OTHER").all()]}


@app.put("/api/admin/settlement-config")
def save_settlement_config(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可修改榜单与奖励规则")
    data = body.data or {}
    cfg = dict(L.setting(db, "cfg") or {})
    cfg["rankDim"] = "MONTH" if data.get("rankDim") == "MONTH" else "WEEK"
    cfg["rankRange"] = max(1, min(20, int(data.get("rankRange") or 3)))
    cfg["prizeMap"] = {str(k): str(v) for k, v in (data.get("prizeMap") or {}).items() if str(k).isdigit()}
    cfg["teamReward"] = bool(data.get("teamReward"))
    cfg["teamCard"] = str(data.get("teamCard") or "")
    cfg["stack"] = bool(data.get("stack"))
    cfg["reqShard"] = bool(data.get("reqShard"))
    cfg["settleCap"] = max(1, min(999, int(data.get("settleCap") or 20)))
    L.save_setting(db, "cfg", cfg)
    L.log(db, "SETTLE_CONFIG_UPDATE", "更新榜单与奖励规则", None, admin)
    return cfg


def _project_values(data: dict) -> tuple[str, int, int, int]:
    name = str(data.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "请填写项目名称")
    min_people = max(0, min(100, int(data.get("min") or 0)))
    max_people = max(0, min(100, int(data.get("max") or 0)))
    if max_people and max_people < min_people:
        raise HTTPException(400, "人数上限不能小于下限")
    shard = max(0, min(100000, int(data.get("shard") or 0)))
    return name[:64], min_people, max_people, shard


@app.post("/api/admin/projects")
def create_project(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    name, min_people, max_people, shard = _project_values(data)
    if db.query(Project).filter(Project.name == name).first():
        raise HTTPException(400, "该项目名称已存在")
    project = Project(id=L.new_id(db, Project), name=name, min=min_people, max=max_people, shard=shard,
                      recent=0, sort=int(data.get("sort") or 99), disabled=False)
    db.add(project)
    L.log(db, "CONFIG_CHANGE", f"新增对局项目 {name}", None, admin)
    db.flush()
    return project.to_dict()


@app.put("/api/admin/projects/{pid}")
def update_project(pid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(404, "对局项目不存在")
    data = body.data or {}
    name, min_people, max_people, shard = _project_values(data)
    same_name = db.query(Project).filter(Project.name == name, Project.id != pid).first()
    if same_name:
        raise HTTPException(400, "该项目名称已存在")
    project.name, project.min, project.max, project.shard = name, min_people, max_people, shard
    L.log(db, "CONFIG_CHANGE", f"更新对局项目 {name}", None, admin)
    db.flush()
    return project.to_dict()


@app.get("/api/admin/{coll}")
def admin_list(
    coll: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=0, le=200, alias="pageSize"),
    status: str = "",
    kw: str = "",
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    if coll in ("agreements", "content", "config", "cfg", "push"):
        return L.setting(db, coll)
    if coll == "members":
        q = db.query(User).filter(User.role == "CUSTOMER", User.status == "ACTIVE")
        total_all = q.count()
        if kw:
            like = f"%{kw}%"
            q = q.filter((User.nick.like(like)) | (User.no.like(like)) | (User.tail.like(like)))
        items = [L.public_user(db, x) for x in q.order_by(User.id.desc()).all()]
        if page_size <= 0:
            return items
        pg = L.paginate(items, page, page_size)
        pg["totalAll"] = total_all
        return pg
    if coll == "staff":
        items = [L.public_user(db, x) for x in db.query(User).filter(User.role != "CUSTOMER").order_by(User.id.desc()).all()]
        if page_size <= 0:
            return items
        return L.paginate(items, page, page_size)
    if coll == "logs":
        if admin["role"] != "BOSS":
            raise HTTPException(403, "仅老板可访问")
    if coll not in COLL_MAP:
        raise HTTPException(404, "unknown collection")
    model, meth = COLL_MAP[coll]
    rows = db.query(model).order_by(model.id.desc()).all()
    if meth:
        items = [getattr(x, meth)() for x in rows]
    else:
        items = [{"id": x.id, "name": x.name} for x in rows]
    if status:
        items = [x for x in items if x.get("status") == status]
    if page_size <= 0:
        return items
    pg = L.paginate(items, page, page_size)
    if coll == "withdrawals":
        all_rows = [getattr(x, meth)() for x in rows] if meth else items
        pg["statusCounts"] = {
            s: sum(1 for x in all_rows if x.get("status") == s)
            for s in ("PENDING_CONFIRM", "GRANTED", "REJECTED", "CANCELLED", "CLOSED_TIMEOUT")
        }
        pg["pendingItems"] = [x for x in all_rows if x.get("status") == "PENDING_CONFIRM"][:30]
    return pg


@app.put("/api/admin/card-templates/{tid}")
def save_card_template(tid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    card_tpl = db.get(CardTpl, tid)
    if not card_tpl:
        raise HTTPException(404, "卡券模板不存在")
    item = body.data or {}
    for key, attr in (
        ("name", "name"), ("cat", "cat"), ("desc", "desc"), ("cost", "cost"), ("days", "days"),
        ("use", "use"), ("perLimit", "per_limit"), ("stock", "stock"), ("exch", "exch"),
        ("prize", "prize"),
    ):
        if key in item:
            setattr(card_tpl, attr, item[key])
    if "rules" in item:
        raw = item.get("rules") or {}
        try:
            duration = max(0, min(24 * 60, int(raw.get("durationMinutes") or 0)))
            weekdays = sorted({int(day) for day in (raw.get("weekdays") or []) if 1 <= int(day) <= 7})
        except (TypeError, ValueError):
            raise HTTPException(400, "卡券限制规则格式不正确")
        card_tpl.rules = {"durationMinutes": duration, "weekdays": weekdays}
    L.log(db, "CARD_TEMPLATE_UPDATE", f"更新卡券模板：{card_tpl.name}", None, admin)
    return card_tpl.to_dict()


@app.post("/api/admin/card-templates")
def create_card_template(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    item = body.data or {}
    name = str(item.get("name") or "").strip()
    cat = str(item.get("cat") or "GAME")
    if not name:
        raise HTTPException(400, "请填写卡券名称")
    if cat not in ("GAME", "FOOD", "OTHER"):
        raise HTTPException(400, "卡券分类不正确")
    cost = max(0, int(item.get("cost") or 0))
    days = max(1, int(item.get("days") or 30))
    per_limit, stock = int(item.get("perLimit", -1)), int(item.get("stock", -1))
    raw_rules = item.get("rules") or {}
    try:
        duration = max(0, min(24 * 60, int(raw_rules.get("durationMinutes") or 0)))
        weekdays = sorted({int(day) for day in (raw_rules.get("weekdays") or []) if 1 <= int(day) <= 7})
    except (TypeError, ValueError):
        raise HTTPException(400, "卡券限制规则格式不正确")
    card_tpl = CardTpl(
        id=L.new_id(db, CardTpl), name=name, cat=cat, desc=str(item.get("desc") or ""), cost=cost,
        days=days, use=str(item.get("use") or ""), per_limit=per_limit, stock=stock,
        exch=bool(item.get("exch")) and cost > 0, prize=str(item.get("prize") or "") or None,
        rules={"durationMinutes": duration, "weekdays": weekdays},
    )
    db.add(card_tpl)
    db.flush()
    L.log(db, "CARD_TEMPLATE_CREATE", f"新增卡券模板：{name}", None, admin)
    return card_tpl.to_dict()


def _sign_rule_item(item: dict, db: Session, ignore_id: int | None = None, allow_empty: bool = False) -> tuple[int, int, list, bool]:
    try:
        days = int(item.get("days") or 0)
        pts = max(0, int(item.get("pts") or 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "签到天数和积分必须是数字")
    if days <= 0:
        raise HTTPException(400, "连续签到天数必须大于 0")
    dup = db.query(SignRule).filter(SignRule.days == days)
    if ignore_id is not None:
        dup = dup.filter(SignRule.id != ignore_id)
    if dup.first():
        raise HTTPException(400, f"已存在连续 {days} 天的奖励档位")
    cards = []
    for card in item.get("cards") or []:
        try:
            tid, qty = int(card.get("tpl")), int(card.get("qty") or 1)
        except (AttributeError, TypeError, ValueError):
            raise HTTPException(400, "卡券奖励格式不正确")
        if qty < 1 or not db.get(CardTpl, tid):
            raise HTTPException(400, "奖励卡券不存在或数量无效")
        cards.append({"tpl": tid, "qty": qty})
    if not allow_empty and not pts and not cards:
        raise HTTPException(400, "至少配置积分或卡券中的一项奖励")
    return days, pts, cards, bool(item.get("enabled", True))


@app.get("/api/admin/signin-overview")
def signin_overview(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200, alias="pageSize"),
    admin: dict = Depends(admin_user),
    db: Session = Depends(get_db),
):
    config = L.setting(db, "config") or {}
    members = []
    for user in db.query(User).filter(User.role == "CUSTOMER").order_by(User.id.desc()).all():
        wallet = L.wallet_of(db, user.id)
        members.append({"id": user.id, "nick": user.nick, "streak": wallet.sign_streak or 0})
    rules = [r.to_dict() for r in db.query(SignRule).order_by(SignRule.days)]
    for rule in rules:
        rule["qualified"] = sum(1 for m in members if m["streak"] >= rule["days"])
    pg = L.paginate(members, page, page_size)
    return {
        "signPoints": int(config.get("signPoints") or 0),
        "rules": rules,
        "members": pg["items"],
        "memberTotal": pg["total"],
        "page": pg["page"],
        "pageSize": pg["pageSize"],
    }


@app.post("/api/admin/sign-rules")
def create_sign_rule(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    days, pts, cards, enabled = _sign_rule_item(body.data or {}, db, allow_empty=True)
    rule = SignRule(id=L.new_id(db, SignRule), days=days, pts=pts, cards=cards, enabled=enabled)
    db.add(rule)
    db.flush()
    L.log(db, "SIGN_RULE_CREATE", f"新增连续签到 {days} 天奖励", None, admin)
    return rule.to_dict()


@app.put("/api/admin/signin-config")
def update_signin_config(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        sign_points = max(0, int((body.data or {}).get("signPoints") or 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "每日签到积分必须是数字")
    config = dict(L.setting(db, "config") or {})
    config["signPoints"] = sign_points
    L.save_setting(db, "config", config)
    L.log(db, "SIGN_DAILY_UPDATE", f"每日签到积分调整为 {sign_points}", None, admin)
    return {"signPoints": sign_points}


@app.put("/api/admin/sign-rules/{rid}")
def update_sign_rule(rid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    rule = db.get(SignRule, rid)
    if not rule:
        raise HTTPException(404, "签到奖励档位不存在")
    days, pts, cards, enabled = _sign_rule_item(body.data or {}, db, rid)
    rule.days, rule.pts, rule.cards, rule.enabled = days, pts, cards, enabled
    L.log(db, "SIGN_RULE_UPDATE", f"更新连续签到 {days} 天奖励", None, admin)
    return rule.to_dict()


@app.post("/api/admin/sign-rules/{rid}/toggle")
def toggle_sign_rule(rid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    rule = db.get(SignRule, rid)
    if not rule:
        raise HTTPException(404, "签到奖励档位不存在")
    rule.enabled = not rule.enabled
    L.log(db, "SIGN_RULE_TOGGLE", f"连续签到 {rule.days} 天奖励{'启用' if rule.enabled else '停用'}", None, admin)
    return rule.to_dict()


@app.delete("/api/admin/sign-rules/{rid}")
def delete_sign_rule(rid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    rule = db.get(SignRule, rid)
    if not rule:
        raise HTTPException(404, "签到奖励档位不存在")
    detail = f"删除连续签到 {rule.days} 天奖励"
    db.delete(rule)
    L.log(db, "SIGN_RULE_DELETE", detail, None, admin)
    return {"ok": True}


@app.put("/api/admin/{coll}")
def admin_put(coll: str, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if coll in ("tiers", "cfg", "staff", "config") and admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    if coll in ("config", "cfg", "content", "push", "agreements"):
        cur = dict(L.setting(db, coll) or {})
        cur.update(body.data)
        L.save_setting(db, coll, cur)
        if coll == "push":
            L.log(db, "CONFIG_CHANGE", "更新消息推送配置", None, admin)
        elif coll == "content" and "shopInfo" in (body.data or {}):
            si = body.data.get("shopInfo") or {}
            L.log(db, "CONFIG_CHANGE", f"更新门店信息 · {si.get('name') or '未命名'}", None, admin)
        elif coll == "config":
            L.log(db, "CONFIG_CHANGE", "更新风控参数", None, admin)
        return {"ok": True}
    raise HTTPException(400, "不支持整表覆盖，请用 item 接口")


@app.post("/api/admin/cats")
def create_category(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.save_category(db, body.data or {}, admin)
    except ValueError as e:
        fail(e)


@app.put("/api/admin/cats/{cid}")
def update_category(cid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.save_category(db, {**(body.data or {}), "id": cid}, admin)
    except ValueError as e:
        fail(e)


@app.delete("/api/admin/cats/{cid}")
def remove_category(cid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.delete_category(db, cid, admin)
    except ValueError as e:
        fail(e)


@app.get("/api/admin/tiers-page")
def tiers_page(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    return L.tiers_page(db)


@app.post("/api/admin/tiers")
def create_tier(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    try:
        return L.save_tier(db, body.data or {}, admin)
    except ValueError as e:
        fail(e)


@app.put("/api/admin/tiers/{tid}")
def update_tier(tid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    try:
        return L.save_tier(db, {**(body.data or {}), "id": tid}, admin)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/tiers/{tid}/recommend")
def recommend_tier(tid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    try:
        return L.toggle_tier_rec(db, tid, admin)
    except ValueError as e:
        fail(e)


@app.delete("/api/admin/tiers/{tid}")
def remove_tier(tid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    try:
        return L.delete_tier(db, tid, admin)
    except ValueError as e:
        fail(e)


@app.get("/api/admin/staff-page")
def staff_page(admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可访问")
    return L.staff_page(db)


@app.post("/api/admin/staff")
def create_staff(body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    try:
        return L.create_staff(db, body.data or {}, admin)
    except ValueError as e:
        fail(e)


@app.put("/api/admin/staff/{uid}/role")
def change_staff_role(uid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    data = body.data or {}
    try:
        return L.change_staff_role(db, uid, str(data.get("role") or ""), str(data.get("reason") or ""), admin)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/staff/{uid}/disable")
def disable_staff(uid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    if admin["role"] != "BOSS":
        raise HTTPException(403, "仅老板可改")
    try:
        return L.disable_staff(db, uid, admin)
    except ValueError as e:
        fail(e)


@app.get("/api/admin/members/{uid}")
def member_detail(uid: int, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.member_detail(db, uid)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/members/{uid}/adjust-coin")
def member_adjust_coin(uid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    try:
        return L.member_adjust_coin(db, uid, int(data.get("delta") or 0), str(data.get("reason") or ""), admin)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/members/{uid}/adjust-point")
def member_adjust_point(uid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    try:
        return L.member_adjust_point(db, uid, int(data.get("delta") or 0), str(data.get("reason") or ""), admin)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/members/{uid}/adjust-shard")
def member_adjust_shard(uid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    try:
        return L.member_adjust_shard(db, uid, int(data.get("delta") or 0), str(data.get("reason") or ""), admin)
    except ValueError as e:
        fail(e)


@app.post("/api/admin/members/{uid}/grant-cards")
def member_grant_cards(uid: int, body: PatchIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    data = body.data or {}
    try:
        return L.member_grant_cards(db, uid, int(data.get("tpl") or 0), int(data.get("qty") or 1), str(data.get("reason") or ""), admin)
    except ValueError as e:
        fail(e)


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


@app.post("/api/admin/orders/{oid}/refund")
def admin_refund_order(oid: int, body: ReasonIn, admin: dict = Depends(admin_user), db: Session = Depends(get_db)):
    try:
        return L.refund_order(db, oid, body.reason, admin)
    except ValueError as e:
        fail(e)


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def missing_api(full_path: str):
    raise HTTPException(404, "接口不存在")


ADMIN_DIR = Path(__file__).resolve().parent / "admin"
if (ADMIN_DIR / "index.html").is_file():
    app.mount("/", SPAStaticFiles(directory=str(ADMIN_DIR), html=True), name="admin")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=True)
