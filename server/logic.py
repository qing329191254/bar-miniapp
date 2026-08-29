"""Business rules for 玩咖. MySQL stores all persistent business data."""
from __future__ import annotations

import hashlib
import random
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

import cache
from models import (
    AgreeLog, Card, CardTpl, Category, Champ, CoinAdjust, DailyBiz, Deactivation,
    GameRecord, OpLog, Order, Product, Project, Recharge, Setting, SettleLog,
    SignRecord, SignRule, TableSeat, Team, Tier, User, VerifyCode, VerifyLog, Wallet, Withdrawal,
)

MIN_MS = 60_000
WDR_BAN = 3
BUSINESS_TZ = ZoneInfo("Asia/Shanghai")


def business_now() -> datetime:
    """All customer-facing dates use the shop's business timezone, not the container's UTC clock."""
    return datetime.now(BUSINESS_TZ)


def business_today() -> date:
    return business_now().date()


def today_str() -> str:
    return business_today().isoformat()


def current_month() -> str:
    return business_today().strftime("%Y-%m")


def today_day() -> int:
    return business_today().day


def point_period() -> dict:
    today = business_today()
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)
    return {
        "clearLabel": f"{month_end.month} 月 {month_end.day} 日 24:00 清零",
        "daysLeft": (month_end - today).days,
    }


def now_ms() -> int:
    return int(time.time() * 1000)


def fmt_hm(ts: float | None = None) -> str:
    return datetime.fromtimestamp((ts or time.time()), BUSINESS_TZ).strftime("%m-%d %H:%M")


def clock() -> str:
    return business_now().strftime("%H:%M")


def yyMMdd() -> str:
    return business_today().strftime("%y%m%d")


def rand_digits(n: int) -> str:
    lo = 10 ** (n - 1)
    return str(random.randint(lo, 10**n - 1))


def err(msg: str):
    raise ValueError(msg)


def setting(sess: Session, key: str, default=None):
    row = sess.get(Setting, key)
    if not row:
        return {} if default is None else default
    return row.v


def save_setting(sess: Session, key: str, value):
    row = sess.get(Setting, key)
    if not row:
        sess.add(Setting(k=key, v=value))
        return
    row.v = value
    flag_modified(row, "v")


def next_seq(sess: Session, key: str) -> int:
    seq = dict(setting(sess, "seq") or {})
    seq[key] = int(seq.get(key) or 100) + 1
    save_setting(sess, "seq", seq)
    return seq[key]


def new_id(sess: Session, model) -> int:
    m = sess.query(func.max(model.id)).scalar() or 0
    return int(m) + 1


def u(sess: Session, uid: int) -> User | None:
    return sess.get(User, uid)


DEFAULT_PWD = "123456"


def hash_pwd(raw: str) -> str:
    return hashlib.sha256(("wanka:" + (raw or "")).encode("utf-8")).hexdigest()


def check_pwd(user: User, raw: str) -> bool:
    if not raw:
        return False
    stored = (user.pwd or "").strip()
    if not stored:
        return raw == DEFAULT_PWD
    return stored == hash_pwd(raw) or stored == raw


def team(sess: Session, tid) -> Team | None:
    return sess.get(Team, tid) if tid else None


def wallet_of(sess: Session, uid: int) -> Wallet:
    w = sess.get(Wallet, uid)
    if not w:
        w = Wallet(user_id=uid)
        sess.add(w)
        sess.flush()
    return w


def coin_of(sess: Session, uid: int) -> dict:
    w = wallet_of(sess, uid)
    return {"p" : w.coin_p, "b": w.coin_b}


def point_of(sess: Session, uid: int) -> dict:
    w = wallet_of(sess, uid)
    return {"av": w.point_av, "wg": w.point_wg, "mg": w.point_mg, "pd": w.point_pd, "wd": w.point_wd, "fz": w.point_fz}


def shard_of(sess: Session, uid: int) -> dict:
    w = wallet_of(sess, uid)
    return {"w": w.shard_w, "t": w.shard_t}


def custs(sess: Session) -> list[User]:
    return sess.query(User).filter(User.role == "CUSTOMER", User.status == "ACTIVE").all()


def tpl(sess: Session, tid: int) -> CardTpl | None:
    return sess.get(CardTpl, tid)


def prod(sess: Session, pid: int) -> Product | None:
    return sess.get(Product, pid)


def public_user(sess: Session, user: User | dict | None) -> dict | None:
    if user is None:
        return None
    if isinstance(user, dict):
        user = sess.get(User, user["id"])
        if not user:
            return None
    tm = team(sess, user.team_id)
    return user.to_public(user.wallet, tm.name if tm else None)


def log(sess: Session, action: str, detail: str, uid=None, op=None):
    staff = op or {"nick": "系统", "role": "—"}
    nick = staff.get("nick") if isinstance(staff, dict) else str(staff)
    role = staff.get("role") if isinstance(staff, dict) else ""
    sess.add(OpLog(
        t=fmt_hm(), op=nick,
        role={"STAFF": "店员", "MANAGER": "店长", "BOSS": "老板"}.get(role, "—"),
        action=action, detail=detail, uid=uid,
    ))


def remain(expire_at) -> str | None:
    if not expire_at:
        return None
    ms = int(expire_at) - now_ms()
    if ms <= 0:
        return None
    m, s = divmod(ms // 1000, 60)
    return f"{m} 分 {s} 秒"


def expire_timeouts(sess: Session):
    now = now_ms()
    for r in sess.query(Recharge).filter(Recharge.status == "PENDING_PAY").all():
        if r.expire_at and int(r.expire_at) <= now:
            r.status = "CLOSED"
            r.close_reason = "TIMEOUT"
            r.pending_uid = None
            try:
                cache.unlock_pending("recharge", r.uid)
            except Exception:
                pass
    for o in sess.query(Order).filter(Order.status == "PENDING_PAY").all():
        if o.expire_at and int(o.expire_at) <= now:
            o.status = "CLOSED"
            o.cancel_reason = "TIMEOUT"
    for w in sess.query(Withdrawal).filter(Withdrawal.status == "PENDING_CONFIRM").all():
        if w.expire_at and int(w.expire_at) <= now:
            w.status = "CLOSED_TIMEOUT"
            w.closed_at = f"{today_str()} {clock()}"
            w.pending_uid = None
            pt = wallet_of(sess, w.uid)
            pt.point_fz = max(0, pt.point_fz - w.pts)
            pt.point_av += w.pts
            pt.point_pd = 0 if pt.point_av >= 0 else -pt.point_av
            try:
                cache.unlock_pending("withdraw", w.uid)
            except Exception:
                pass
    expired_codes = sess.query(VerifyCode).filter(
        VerifyCode.status == "VALID", VerifyCode.expire_at <= now,
    ).all()
    for vc in expired_codes:
        vc.status = "EXPIRED"
    live = {
        int(cid)
        for vc in sess.query(VerifyCode).filter(
            VerifyCode.status == "VALID", VerifyCode.expire_at > now,
        ).all()
        for cid in (vc.card_ids or [])
    }
    for c in sess.query(Card).filter(Card.status == "LOCKED").all():
        if c.id not in live:
            c.status = "UNUSED"


def spec_name(p: Product | None, sid) -> str:
    if not p:
        return ""
    sp = next((x for x in (p.specs or []) if x["id"] == sid), None)
    return sp["name"] if sp else ""


def unit_price(p: Product, spec_ids: list) -> int:
    extra = 0
    for sid in spec_ids or []:
        sp = next((x for x in (p.specs or []) if x["id"] == sid), None)
        extra += sp["diff"] if sp else 0
    return p.price + extra


def alloc_member_no(sess: Session) -> str:
    rows = [x[0] for x in sess.query(User.no).all()]
    nums = [int(n) for n in rows if n and str(n).isdigit() and int(n) < 900000]
    n = (max(nums) if nums else 100000) + 1
    return f"{n:06d}"


def mask_phone(full: str) -> tuple[str, str]:
    digits = "".join(ch for ch in (full or "") if ch.isdigit())
    if len(digits) >= 11:
        d = digits[-11:]
        return f"{d[:3]}****{d[-4:]}", d[-4:]
    if len(digits) >= 4:
        return f"1******{digits[-4:]}", digits[-4:]
    tail = rand_digits(4)
    return f"1******{tail}", tail


def bind_wx_phone(sess: Session, user: User, phone_full: str) -> None:
    masked, tail = mask_phone(phone_full)
    user.phone = masked
    user.tail = tail


def register_wx(sess: Session, openid: str, phone_full: str | None = None) -> User:
    found = sess.query(User).filter(User.wx_openid == openid).first()
    if found:
        if phone_full:
            bind_wx_phone(sess, found, phone_full)
        return found
    if phone_full:
        digits = "".join(ch for ch in phone_full if ch.isdigit())
        if len(digits) >= 11:
            d11 = digits[-11:]
            masked, tail = mask_phone(d11)
            by_phone = sess.query(User).filter(
                User.role == "CUSTOMER",
                User.tail == tail,
                User.phone.in_([d11, masked, f"{d11[:3]}****{d11[-4:]}"]),
            ).first()
            if by_phone:
                by_phone.wx_openid = openid
                bind_wx_phone(sess, by_phone, d11)
                return by_phone
    if phone_full:
        masked, tail = mask_phone(phone_full)
    else:
        tail = rand_digits(4)
        masked = f"1******{tail}"
    user = User(
        id=new_id(sess, User),
        no=alloc_member_no(sess),
        nick="玩咖用户",
        phone=masked,
        tail=tail,
        gender=0,
        role="CUSTOMER",
        status="ACTIVE",
        agreed_version=0,
        pwd="",
        wx_openid=openid,
    )
    sess.add(user)
    sess.flush()
    sess.add(Wallet(user_id=user.id))
    grant_demo_points(sess, user.id)
    grant_demo_coins(sess, user.id)
    grant_demo_cards(sess, user.id)
    grant_demo_sign(sess, user.id)
    return user


def record_agreement(sess: Session, user: User, terms_ver: int, privacy_ver: int) -> None:
    for doc, ver in (("terms", terms_ver), ("privacy", privacy_ver)):
        exists = sess.query(AgreeLog).filter_by(doc=doc, ver=ver, uid=user.id).first()
        if not exists:
            sess.add(AgreeLog(doc=doc, ver=ver, uid=user.id, at=fmt_hm()))
    user.agreed_version = terms_ver


def agreement_reconsent_required(sess: Session, uid: int) -> bool:
    agreements = setting(sess, "agreements") or {}
    for doc in ("terms", "privacy"):
        current = agreements.get(doc) or {}
        major_versions = [
            int(item.get("v") or 0) for item in (current.get("hist") or [])
            if item.get("type") == "重大变更"
        ]
        if current.get("major"):
            major_versions.append(int(current.get("ver") or 1))
        required_ver = max(major_versions or [0])
        if not required_ver:
            continue
        latest = sess.query(AgreeLog).filter_by(doc=doc, uid=uid).order_by(AgreeLog.ver.desc()).first()
        if not latest or latest.ver < required_ver:
            return True
    return False


STARTER_POINTS = {"av": 8600, "wg": 3200, "mg": 17300, "pd": 0, "wd": 0, "fz": 0}
STARTER_COINS = {"p": 1100, "b": 140}


def grant_demo_points(sess: Session, uid: int):
    w = wallet_of(sess, uid)
    if w.point_av or w.point_mg or w.point_wg:
        return
    w.point_av = STARTER_POINTS["av"]
    w.point_wg = STARTER_POINTS["wg"]
    w.point_mg = STARTER_POINTS["mg"]
    w.point_pd = STARTER_POINTS["pd"]
    w.point_wd = STARTER_POINTS["wd"]
    w.point_fz = STARTER_POINTS["fz"]


def grant_demo_coins(sess: Session, uid: int):
    w = wallet_of(sess, uid)
    if w.coin_p or w.coin_b:
        return
    w.coin_p = STARTER_COINS["p"]
    w.coin_b = STARTER_COINS["b"]


STARTER_CARDS = [
    (1, "UNUSED", 28, "09-23", "EXCHANGE", "积分兑换 · 08-24"),
    (2, "UNUSED", 2, "08-27", "EXCHANGE", "积分兑换 · 08-24"),
    (3, "UNUSED", 30, "09-24", "EXCHANGE", "积分兑换 · 08-25"),
    (4, "UNUSED", 1, "08-26", "EXCHANGE", "积分兑换 · 08-25"),
    (5, "UNUSED", 7, "08-31", "SETTLE_REWARD", "周冠军奖励 · 08-24 发放"),
    (7, "UNUSED", 7, "08-31", "SETTLE_REWARD", "周结算碎片榜第 3 名 · 08-24 发放"),
    (1, "USED", 0, "08-20", "EXCHANGE", "积分兑换 · 08-10"),
    (3, "EXPIRED", 0, "08-19", "EXCHANGE", "积分兑换 · 07-20"),
    (6, "VOID", 0, "08-18", "EXCHANGE", "积分兑换 · 08-01"),
]


def grant_demo_cards(sess: Session, uid: int):
    if sess.query(Card).filter_by(uid=uid).count():
        return
    for tpl_id, status, days, expire, src, desc in STARTER_CARDS:
        tm = sess.get(CardTpl, tpl_id)
        if not tm:
            continue
        sess.add(Card(
            id=next_seq(sess, "card"),
            uid=uid,
            tpl=tpl_id,
            no="KQ" + rand_digits(12),
            src=src,
            src_desc=desc,
            status=status,
            days_left=days,
            expire=expire,
        ))


def register(sess: Session, nick: str, agreed: bool) -> User:
    if not agreed:
        err("请先同意协议")
    agreements = setting(sess, "agreements")
    ver = int((agreements.get("terms") or {}).get("ver") or 1)
    tail = rand_digits(4)
    user = User(
        id=new_id(sess, User),
        no=alloc_member_no(sess),
        nick=nick or "玩咖用户",
        phone=f"1******{tail}",
        tail=tail,
        gender=0,
        role="CUSTOMER",
        status="ACTIVE",
        agreed_version=ver,
        pwd=hash_pwd(DEFAULT_PWD),
    )
    sess.add(user)
    sess.flush()
    sess.add(Wallet(user_id=user.id))
    sess.add(AgreeLog(doc="terms", ver=ver, uid=user.id, at=fmt_hm()))
    sess.add(AgreeLog(doc="privacy", ver=int((agreements.get("privacy") or {}).get("ver") or ver), uid=user.id, at=fmt_hm()))
    return user


def do_sign(sess: Session, uid: int) -> dict:
    today = today_day()
    month = current_month()
    if sess.query(SignRecord).filter_by(uid=uid, day=today, month=month).first():
        err("今日已签到")
    cfg = setting(sess, "config")
    sp = int(cfg.get("signPoints") or 0)
    w = wallet_of(sess, uid)
    w.point_av += sp
    w.point_wg += sp
    w.point_mg += sp
    w.point_pd = 0 if w.point_av >= 0 else -w.point_av
    # 连续签到必须以北京时间的前一天为准，漏签则从 1 天重新开始。
    previous_day = business_today() - timedelta(days=1)
    signed_yesterday = sess.query(SignRecord).filter_by(
        uid=uid, month=previous_day.strftime("%Y-%m"), day=previous_day.day
    ).first()
    w.sign_streak = int(w.sign_streak or 0) + 1 if signed_yesterday else 1
    extra_pts, names = 0, []
    for r in sess.query(SignRule).all():
        if r.enabled is False or r.days != w.sign_streak:
            continue
        if r.pts:
            w.point_av += r.pts
            w.point_wg += r.pts
            w.point_mg += r.pts
            extra_pts += r.pts
        for c in r.cards or []:
            tm = tpl(sess, c["tpl"])
            if not tm:
                continue
            for _ in range(c["qty"]):
                issue_card(sess, uid, tm, "SIGN_IN_REWARD", f"连续签到 {r.days} 天奖励")
            names.append(f"{tm.name}×{c['qty']}")
    sess.add(SignRecord(uid=uid, day=today, month=month))
    return {"points": sp, "extraPts": extra_pts, "cards": names, "streak": w.sign_streak}


def issue_card(sess: Session, uid: int, tm: CardTpl, src: str, src_desc: str) -> Card:
    card = Card(
        id=next_seq(sess, "card"),
        uid=uid,
        tpl=tm.id,
        no="KQ" + rand_digits(12),
        src=src,
        src_desc=src_desc,
        status="UNUSED",
        days_left=tm.days or 30,
        expire="",
    )
    sess.add(card)
    return card


def create_order(sess: Session, uid: int, items: list, pay_type: str, table_id, remark: str) -> dict:
    user = u(sess, uid)
    if not user or user.role != "CUSTOMER":
        err("请先注册会员")
    if not items:
        err("购物车为空")
    if pay_type not in ("COIN", "OFFLINE"):
        err("支付方式无效")
    if len(items) > 50:
        err("购物车商品过多")
    lines = []
    total = 0
    for it in items:
        p = prod(sess, int(it["pid"]))
        if not p or p.offline or p.sold_out:
            err("商品不可售")
        qty = int(it.get("qty") or 0)
        if qty < 1 or qty > 99:
            err("商品数量无效")
        spec_ids = list(dict.fromkeys(it.get("specIds") or []))
        valid_spec_ids = {int(x["id"]) for x in (p.specs or [])}
        if any(int(sid) not in valid_spec_ids for sid in spec_ids):
            err("商品规格已失效")
        if p.has_spec and not spec_ids:
            err("请选择商品规格")
        if not p.spec_multi and len(spec_ids) > 1:
            err("该商品只能选择一个规格")
        price = unit_price(p, spec_ids)
        total += price * qty
        lines.append({
            "pid": p.id, "name": p.name,
            "spec": "、".join(spec_name(p, s) for s in spec_ids if spec_name(p, s)),
            "specIds": spec_ids,
            "qty": qty, "price": price,
        })
    cfg = setting(sess, "config")
    timeout = int(cfg.get("offlineTimeout") or 30)
    tbl = sess.get(TableSeat, table_id) if table_id else None
    if table_id and not tbl:
        err("所选桌台不存在")
    order = Order(
        id=new_id(sess, Order),
        no="DD" + yyMMdd() + rand_digits(6),
        uid=uid, nick=user.nick,
        table_id=table_id, table_name=tbl.name if tbl else "",
        total=total, pay_type=pay_type,
        status="PENDING_ACCEPT" if pay_type == "COIN" else "PENDING_PAY",
        remark=(remark or "")[:50], ago="刚刚", at=f"{today_str()} {clock()}",
        items=lines,
        expire_at=now_ms() + timeout * MIN_MS if pay_type == "OFFLINE" else None,
    )
    sess.add(order)
    sess.flush()
    return order.to_dict()


def create_recharge(sess: Session, uid: int, tier_id: int) -> dict:
    if sess.query(Recharge).filter_by(uid=uid, status="PENDING_PAY").first():
        err("你有一张待付充值单，请先付款或取消")
    t = sess.get(Tier, tier_id)
    if not t:
        err("充值档位不存在")
    cfg = setting(sess, "config")
    lim = int(cfg.get("singleLimit") or 0)
    if lim and t.amount > lim:
        err(f"超出单笔充值上限 ¥{lim}")
    timeout = int(cfg.get("rechargeTimeout") or 30)
    try:
        if not cache.lock_pending("recharge", uid, timeout * 60):
            err("你有一张待付充值单，请先付款或取消")
    except Exception:
        pass
    ro = Recharge(
        id=new_id(sess, Recharge),
        no="CZ" + yyMMdd() + rand_digits(4),
        uid=uid, amount=t.amount, bonus=t.bonus,
        status="PENDING_PAY",
        expire_at=now_ms() + timeout * MIN_MS,
        created=fmt_hm(), at=f"{today_str()} {clock()}",
        pending_uid=uid,
    )
    sess.add(ro)
    sess.flush()
    return ro.to_dict()


def cancel_recharge(sess: Session, uid: int, rid: int) -> dict:
    r = sess.get(Recharge, rid)
    if not r or r.uid != uid or r.status != "PENDING_PAY":
        err("无法取消")
    r.status = "CLOSED"
    r.close_reason = "USER_CANCEL"
    r.pending_uid = None
    try:
        cache.unlock_pending("recharge", uid)
    except Exception:
        pass
    return r.to_dict()


def create_withdraw(sess: Session, uid: int, pts: int) -> dict:
    wlt = wallet_of(sess, uid)
    if pts <= 0:
        err("请输入有效数量")
    if wlt.point_av < 0:
        err("当前积分为负，暂不可提分")
    if pts > wlt.point_av:
        err("提分失败，可用积分不足")
    if sess.query(Withdrawal).filter_by(uid=uid, status="PENDING_CONFIRM").first():
        err("你有一张待确认提分单")
    toc = sess.query(Withdrawal).filter_by(uid=uid, status="CLOSED_TIMEOUT").count()  # demo: count all timeouts
    if toc >= WDR_BAN:
        err(f"近 24 小时内已有 {toc} 张提分单超时未确认，暂停提交")
    try:
        if not cache.lock_pending("withdraw", uid, 30 * 60):
            err("你有一张待确认提分单")
    except Exception:
        pass
    wlt.point_av -= pts
    wlt.point_fz += pts
    wo = Withdrawal(
        id=next_seq(sess, "wdr"),
        no="TF" + yyMMdd() + rand_digits(4),
        uid=uid, pts=pts, status="PENDING_CONFIRM",
        created=fmt_hm(), at=f"{today_str()} {clock()}",
        expire_at=now_ms() + 30 * MIN_MS,
        pending_uid=uid,
    )
    sess.add(wo)
    sess.flush()
    return wo.to_dict()


def cancel_withdraw(sess: Session, uid: int) -> dict:
    w = sess.query(Withdrawal).filter_by(uid=uid, status="PENDING_CONFIRM").first()
    if not w:
        err("无待确认提分单")
    pt = wallet_of(sess, uid)
    w.status = "CANCELLED"
    w.closed_at = f"{today_str()} {clock()}"
    w.pending_uid = None
    pt.point_fz = max(0, pt.point_fz - w.pts)
    pt.point_av += w.pts
    pt.point_pd = 0 if pt.point_av >= 0 else -pt.point_av
    try:
        cache.unlock_pending("withdraw", uid)
    except Exception:
        pass
    return w.to_dict()


def do_exchange(sess: Session, uid: int, tid: int, qty: int) -> bool:
    t = tpl(sess, tid)
    w = wallet_of(sess, uid)
    qty = int(qty)
    if qty < 1 or qty > 99:
        err("兑换数量无效")
    if not t or t.exch is False or not t.cost:
        err("卡券不可兑换")
    if w.point_av < t.cost * qty:
        err("兑换失败，积分不足")
    per = t.per_limit
    if per >= 0:
        got = sess.query(Card).filter_by(uid=uid, tpl=t.id, src="EXCHANGE").count()
        if got + qty > per:
            err("兑换失败，已达每人上限")
    stk = t.stock
    if stk >= 0 and stk < qty:
        err("兑换失败，库存不足")
    w.point_av -= t.cost * qty
    if stk >= 0:
        t.stock = stk - qty
    for _ in range(qty):
        issue_card(sess, uid, t, "EXCHANGE", "积分兑换")
    return True


def gen_verify(sess: Session, uid: int, card_ids: list[int]) -> dict:
    card_ids = list(dict.fromkeys(int(x) for x in card_ids))
    if not card_ids or len(card_ids) > 50:
        err("请选择 1–50 张卡券")
    cards = []
    for cid in card_ids:
        c = sess.get(Card, cid)
        if not c or c.uid != uid or c.status != "UNUSED" or (c.days_left or 0) <= 0:
            err("卡券状态已变化")
        tm = tpl(sess, c.tpl)
        weekdays = (tm.rules or {}).get("weekdays") if tm else []
        allowed = {int(day) for day in weekdays or [] if str(day).isdigit() and 1 <= int(day) <= 7}
        if allowed and business_today().isoweekday() not in allowed:
            err(f"{tm.name} 当前不可核销，请按卡券使用限制到店使用")
        cards.append(c)
    code = rand_digits(12)
    for c in cards:
        c.status = "LOCKED"
    cfg = setting(sess, "config")
    ttl = int(cfg.get("verifyTtl") or 5)
    vc = VerifyCode(
        code=code, uid=uid, card_ids=[c.id for c in cards], status="VALID",
        expire_at=now_ms() + ttl * MIN_MS,
    )
    sess.add(vc)
    return verify_code_dict(vc)


def verify_code_dict(vc: VerifyCode) -> dict:
    return {
        "code": vc.code, "uid": vc.uid, "cardIds": vc.card_ids or [],
        "status": vc.status, "expireAt": vc.expire_at,
    }


def find_verify(sess: Session, code: str) -> VerifyCode | None:
    found = sess.get(VerifyCode, code)
    if found:
        return found
    return sess.query(VerifyCode).filter(VerifyCode.code.like(f"%{code}")).order_by(VerifyCode.expire_at.desc()).first()


def grant_combo(sess: Session, order: Order) -> int:
    n = 0
    for it in order.items or []:
        p = prod(sess, it["pid"]) if it.get("pid") is not None else sess.query(Product).filter_by(name=it["name"]).first()
        if p and p.type == "COMBO" and p.combo:
            for c in p.combo:
                tm = tpl(sess, c["tpl"])
                if not tm:
                    continue
                for _ in range(c["qty"]):
                    issue_card(sess, order.uid, tm, "ORDER_COMBO", f"套餐自动发放 · {order.no}")
                    n += 1
    return n


def accept_order(sess: Session, oid: int, staff: dict) -> dict:
    o = sess.get(Order, oid)
    if not o or o.status != "PENDING_ACCEPT":
        err("订单状态已变更")
    if o.pay_type == "COIN":
        c = wallet_of(sess, o.uid)
        if c.coin_p + c.coin_b < o.total:
            err(f"余额不足，差 {o.total - c.coin_p - c.coin_b} 金币")
        dp = min(c.coin_p, o.total)
        bonus = o.total - dp
        c.coin_p -= dp
        c.coin_b -= bonus
        o.paid_principal = dp
        o.paid_bonus = bonus
    o.status = "MAKING"
    o.accepted_by = staff["id"]
    o.op_uid = staff["id"]
    o.at = o.at or f"{today_str()} {clock()}"
    n = grant_combo(sess, o)
    log(sess, "ORDER_ACCEPT", f"{o.no} · {o.total} 金币", o.uid, staff)
    return {"order": o.to_dict(), "combo": n}


def reject_order(sess: Session, oid: int, reason: str, staff: dict) -> dict:
    o = sess.get(Order, oid)
    if not o or o.status != "PENDING_ACCEPT":
        err("订单状态已变更")
    if o.pay_type == "COIN" and (o.paid_principal or o.paid_bonus):
        c = wallet_of(sess, o.uid)
        c.coin_p += o.paid_principal or 0
        c.coin_b += o.paid_bonus or 0
    o.status = "CANCELLED"
    o.cancel_reason = reason
    log(sess, "ORDER_REJECT", f"{o.no} · {reason}", o.uid, staff)
    return o.to_dict()


def refund_order(sess: Session, oid: int, reason: str, admin: dict) -> dict:
    """处理售后订单退款；金币订单退回原本金/赠送构成，到吧台付款由线下退款。"""
    o = sess.get(Order, oid)
    if not o:
        err("订单不存在")
    if o.status in ("PENDING_PAY", "CLOSED", "CANCELLED", "REFUNDED"):
        err("该订单当前不可退款")
    reason = (reason or "").strip()
    if len(reason) < 2:
        err("请填写退款原因")

    if o.pay_type == "COIN":
        if o.status not in ("MAKING", "FINISHED"):
            err("金币订单须在接单扣款后才能退款")
        principal = int(o.paid_principal or 0)
        bonus = int(o.paid_bonus or 0)
        if principal + bonus <= 0:
            err("该订单没有可退回的金币")
        wallet = wallet_of(sess, o.uid)
        wallet.coin_p += principal
        wallet.coin_b += bonus
        refund_type = "COIN"
    else:
        if o.status not in ("PENDING_ACCEPT", "MAKING", "FINISHED"):
            err("该订单当前不可退款")
        principal = 0
        bonus = 0
        # 到吧台付款不进入会员钱包，现金或收款码退款由门店线下完成；系统只留痕并更新订单状态。
        refund_type = "OFFLINE"

    voided = 0
    for card in sess.query(Card).filter_by(uid=o.uid, src="ORDER_COMBO", status="UNUSED"):
        if o.no in (card.src_desc or ""):
            card.status = "VOID"
            card.void_reason = f"订单退款 · {o.no}"
            voided += 1

    o.status = "REFUNDED"
    o.cancel_reason = f"退款：{reason}"[:128]
    detail = f"{o.no} · "
    if refund_type == "COIN":
        detail += f"退回金币 {principal + bonus}（本金 {principal} / 赠送 {bonus}）"
    else:
        detail += f"线下退款 ¥{o.total}"
    if voided:
        detail += f" · 作废套餐赠卡 {voided} 张"
    detail += f" · 原因：{reason}"
    log(sess, "ORDER_REFUND", detail, o.uid, admin)
    return {**o.to_dict(), "refundType": refund_type, "refundPrincipal": principal, "refundBonus": bonus, "voidedCards": voided}


def confirm_pay_order(sess: Session, oid: int, staff: dict) -> dict:
    o = sess.get(Order, oid)
    if not o or o.status != "PENDING_PAY":
        err("订单状态已变更")
    o.status = "PENDING_ACCEPT"
    o.op_uid = staff["id"]
    log(sess, "ORDER_PAY_CONFIRM", o.no, o.uid, staff)
    return o.to_dict()


def finish_order(sess: Session, oid: int) -> dict:
    o = sess.get(Order, oid)
    if not o or o.status != "MAKING":
        err("订单状态已变更")
    o.status = "FINISHED"
    return o.to_dict()


def confirm_recharge(sess: Session, rid: int, staff: dict) -> dict:
    r = sess.get(Recharge, rid)
    if not r or r.status != "PENDING_PAY":
        err("该充值单已处理")
    c = wallet_of(sess, r.uid)
    r.status = "PAID"
    c.coin_p += r.amount
    c.coin_b += r.bonus
    r.op_uid = staff["id"]
    r.at = r.at or f"{today_str()} {clock()}"
    r.pending_uid = None
    try:
        cache.unlock_pending("recharge", r.uid)
    except Exception:
        pass
    log(sess, "RECHARGE_CONFIRM", f"{r.no} · ¥{r.amount}", r.uid, staff)
    return r.to_dict()


def reject_recharge(sess: Session, rid: int, reason: str, staff: dict) -> dict:
    r = sess.get(Recharge, rid)
    if not r or r.status != "PENDING_PAY":
        err("该充值单已处理")
    r.status = "CLOSED"
    r.close_reason = "STAFF_REJECT"
    r.reject_remark = reason
    r.pending_uid = None
    try:
        cache.unlock_pending("recharge", r.uid)
    except Exception:
        pass
    log(sess, "RECHARGE_REJECT", reason, r.uid, staff)
    return r.to_dict()


def confirm_withdraw(sess: Session, wid: int, staff: dict) -> dict:
    w = sess.get(Withdrawal, wid)
    if not w or w.status != "PENDING_CONFIRM":
        err("该提分单已处理")
    pt = wallet_of(sess, w.uid)
    w.status = "GRANTED"
    w.grant_by = staff["id"]
    w.grant_at = f"{today_str()} {clock()}"
    w.pending_uid = None
    pt.point_fz = max(0, pt.point_fz - w.pts)
    pt.point_wd += w.pts
    try:
        cache.unlock_pending("withdraw", w.uid)
    except Exception:
        pass
    log(sess, "WITHDRAW_GRANT", f"{w.no} · {w.pts} 分", w.uid, staff)
    return w.to_dict()


def reject_withdraw(sess: Session, wid: int, reason: str, staff: dict) -> dict:
    w = sess.get(Withdrawal, wid)
    if not w or w.status != "PENDING_CONFIRM":
        err("该提分单已处理")
    pt = wallet_of(sess, w.uid)
    w.status = "REJECTED"
    w.reject_by = staff["id"]
    w.reject_remark = reason
    w.closed_at = f"{today_str()} {clock()}"
    w.pending_uid = None
    pt.point_fz = max(0, pt.point_fz - w.pts)
    pt.point_av += w.pts
    pt.point_pd = 0 if pt.point_av >= 0 else -pt.point_av
    try:
        cache.unlock_pending("withdraw", w.uid)
    except Exception:
        pass
    log(sess, "WITHDRAW_REJECT", reason, w.uid, staff)
    return w.to_dict()


def verify_preview(sess: Session, code: str) -> dict:
    vc = find_verify(sess, code)
    if not vc or vc.status != "VALID" or vc.expire_at <= now_ms():
        err("无法识别的核销码")
    cards = []
    for cid in vc.card_ids or []:
        c = sess.get(Card, cid)
        tm = tpl(sess, c.tpl) if c else None
        cards.append({"card": c.to_dict() if c else None, "tpl": tm.to_dict() if tm else None})
    return {"code": vc.code, "uid": vc.uid, "user": public_user(sess, u(sess, vc.uid)), "cards": cards}


def verify_confirm(sess: Session, code: str, staff: dict) -> dict:
    vc = find_verify(sess, code)
    if not vc or vc.status != "VALID" or vc.expire_at <= now_ms():
        err("核销码已失效")
    for cid in vc.card_ids or []:
        c = sess.get(Card, cid)
        if c and c.status == "LOCKED":
            c.status = "USED"
            tm = tpl(sess, c.tpl)
            sess.add(VerifyLog(
                card_no=c.no, tpl_name=tm.name if tm else "卡券",
                uid=vc.uid, op_uid=staff["id"], at=f"{today_str()} {clock()}",
            ))
    vc.status = "USED"
    log(sess, "CARD_VERIFY", f"核销 {len(vc.card_ids or [])} 张", vc.uid, staff)
    return verify_code_dict(vc)


def submit_game(sess: Session, staff: dict, pid: int, table_id, players: list, winners: list, event: str, round: str = "") -> dict:
    if not players:
        err("请至少选择 1 位玩家")
    cf = setting(sess, "config")
    if cf.get("pointLimit"):
        lim = int(cf.get("pointVal") or 0)
        bad = next((p for p in players if int(p.get("pts") or 0) > lim), None)
        if bad:
            err(f"超出单笔积分上限 {lim}")
    if cf.get("shardLimit"):
        lim = int(cf.get("shardVal") or 0)
        bad = next((p for p in players if int(p.get("sh") or 0) > lim), None)
        if bad:
            err(f"超出单笔碎片上限 {lim}")
    pj = sess.get(Project, pid)
    tbl = sess.get(TableSeat, table_id) if table_id else None
    rec_players = []
    for p in players:
        usr = u(sess, int(p["uid"]))
        rec_players.append({"uid": usr.id, "nick": usr.nick, "pts": int(p.get("pts") or 0), "sh": int(p.get("sh") or 0)})
        wlt = wallet_of(sess, usr.id)
        if rec_players[-1]["pts"]:
            wlt.point_av += rec_players[-1]["pts"]
            wlt.point_wg += rec_players[-1]["pts"]
            wlt.point_mg += rec_players[-1]["pts"]
            wlt.point_pd = 0 if wlt.point_av >= 0 else -wlt.point_av
        if rec_players[-1]["sh"]:
            wlt.shard_w += rec_players[-1]["sh"]
            wlt.shard_t += rec_players[-1]["sh"]
    rec = GameRecord(
        id=next_seq(sess, "rec"), pid=pid, pname=pj.name if pj else "",
        table=tbl.name if tbl else "", round=(round or "").strip()[:32], time=f"{today_str()} {clock()}",
        op=staff["nick"], op_uid=staff["id"], players=rec_players,
    )
    sess.add(rec)
    win_uids = [int(x) for x in (winners or [])]
    ev = (event or "").strip()
    if ev and win_uids:
        for uid in win_uids:
            x = u(sess, uid)
            tm = team(sess, x.team_id) if x else None
            sess.add(Champ(
                uid=uid, event=ev, date=today_str(), n=len(players),
                team_id=x.team_id if x else None,
                team_name=tm.name if tm else "无战队", op=staff["nick"],
            ))
    log(sess, "GAME_INPUT", rec.pname, None, staff)
    sess.flush()
    return rec.to_dict()


def flt_range(preset: str, date_from: str = "", date_to: str = "") -> tuple[str, str] | None:
    today = business_today()
    t = today.isoformat()
    if preset in ("", "all"):
        return None
    if preset == "today":
        return (t, t)
    if preset == "yday":
        y = (today - timedelta(days=1)).isoformat()
        return (y, y)
    if preset == "7d":
        return ((today - timedelta(days=6)).isoformat(), t)
    if preset == "30d":
        return ((today - timedelta(days=29)).isoformat(), t)
    if preset == "month":
        return (t[:7] + "-01", t)
    if preset == "custom":
        return (date_from or "1970-01-01", date_to or "2999-12-31")
    return None


def range_label(preset: str, date_from: str = "", date_to: str = "") -> str:
    r = flt_range(preset, date_from, date_to)
    if not r:
        return "全部时间"
    return r[0] if r[0] == r[1] else f"{r[0]} ~ {r[1]}"


def in_range(time_str: str, preset: str, date_from: str = "", date_to: str = "") -> bool:
    d = str(time_str or "")[:10]
    r = flt_range(preset, date_from, date_to)
    if not r:
        return True
    return r[0] <= d <= r[1]


def job_stat(sess: Session, uid: int, preset="today", date_from: str = "", date_to: str = "") -> dict:
    ods = [o.to_dict() for o in sess.query(Order).filter(Order.op_uid == uid).all() if in_range(o.at or "", preset, date_from, date_to)]
    rcs = [r.to_dict() for r in sess.query(Recharge).filter(Recharge.op_uid == uid, Recharge.status == "PAID").all() if in_range(r.at or "", preset, date_from, date_to)]
    vfs = [v.to_dict() for v in sess.query(VerifyLog).filter(VerifyLog.op_uid == uid).all() if in_range(v.at or "", preset, date_from, date_to)]
    gms = [g.to_dict() for g in sess.query(GameRecord).filter(GameRecord.op_uid == uid).all() if g.status != "VOID" and in_range(g.time or "", preset, date_from, date_to)]
    paid = [o for o in ods if o["status"] in ("MAKING", "FINISHED")]
    rc_amt = sum(r["amount"] for r in rcs)
    od_amt = sum(o["total"] for o in paid)
    wds = sess.query(Withdrawal).filter(Withdrawal.status == "GRANTED", Withdrawal.grant_by == uid).count()
    wds = sum(1 for w in sess.query(Withdrawal).filter(Withdrawal.status == "GRANTED", Withdrawal.grant_by == uid) if in_range(w.grant_at or "", preset, date_from, date_to))
    heads = sum(len(g.get("players") or []) for g in gms)
    ods.sort(key=lambda o: o.get("at") or "", reverse=True)
    rcs.sort(key=lambda r: r.get("at") or "", reverse=True)
    vfs.sort(key=lambda v: v.get("at") or "", reverse=True)
    gms.sort(key=lambda g: g.get("time") or "", reverse=True)
    r = flt_range(preset, date_from, date_to)
    return {
        "amount": rc_amt + od_amt, "rcAmt": rc_amt, "odAmt": od_amt,
        "orders": len(ods), "verifies": len(vfs), "games": len(gms), "heads": heads, "wds": wds,
        "rcs": rcs, "ods": ods, "vfs": vfs, "gms": gms,
        "range": {"from": r[0], "to": r[1], "label": range_label(preset, date_from, date_to)} if r else {"from": "", "to": "", "label": "全部时间"},
    }


def champ_count(sess: Session, uid, month=False) -> int:
    q = sess.query(Champ).filter(Champ.uid == uid)
    if month:
        q = q.filter(Champ.date.startswith(current_month()))
    return q.count()


def rank_rows(sess: Session, kind: str, dim: str, subject: str):
    people = custs(sess)
    teams = sess.query(Team).all()
    if kind == "SHARD":
        def val(x: User):
            w = wallet_of(sess, x.id)
            return w.shard_w if dim == "WEEK" else w.shard_t
        if subject == "USER":
            rows = [{"x": x, "v": val(x)} for x in people]
        else:
            rows = [{"t": t, "v": sum(val(x) for x in people if x.team_id == t.id),
                     "ms": [x for x in people if x.team_id == t.id]} for t in teams]
    elif kind == "POINT":
        key = "wg" if dim == "WEEK" else "mg"
        def pval(x: User):
            w = wallet_of(sess, x.id)
            return getattr(w, "point_wg" if key == "wg" else "point_mg")
        if subject == "USER":
            rows = [{"x": x, "v": pval(x)} for x in people]
        else:
            rows = [{"t": t, "v": sum(pval(x) for x in people if x.team_id == t.id),
                     "ms": [x for x in people if x.team_id == t.id]} for t in teams]
    else:
        month = dim == "MONTH"
        if subject == "USER":
            rows = [{"x": x, "v": champ_count(sess, x.id, month)} for x in people]
        else:
            rows = [{"t": t, "v": sum(champ_count(sess, x.id, month) for x in people if x.team_id == t.id),
                     "ms": [x for x in people if x.team_id == t.id]} for t in teams]
    rows = [r for r in rows if r["v"] > 0]
    rows.sort(key=lambda r: -r["v"])
    prev = None
    for i, r in enumerate(rows):
        r["rank"] = 1 if i == 0 else (prev["rank"] if r["v"] == prev["v"] else i + 1)
        prev = r
        if "x" in r:
            r["user"] = public_user(sess, r["x"])
            del r["x"]
        if "t" in r:
            r["team"] = {"id": r["t"].id, "name": r["t"].name}
            r["members"] = len(r.get("ms") or [])
            del r["t"]
            r.pop("ms", None)
    return rows


def dashboard(sess: Session, role: str) -> dict:
    today_key = today_str()
    today = sess.get(DailyBiz, today_key)
    today_d = today.to_dict() if today else {"coin": 0, "offline": 0, "recharge": 0, "orders": 0, "guests": 0, "d": today_key}
    pa = sess.query(Order).filter_by(status="PENDING_ACCEPT").count()
    pay_od = sess.query(Order).filter_by(status="PENDING_PAY").count()
    rc_pending = sess.query(Recharge).filter_by(status="PENDING_PAY").count()
    soldout = sess.query(Product).filter_by(sold_out=True).count()
    coin_liab = 0
    point_liab = 0
    for x in custs(sess):
        w = wallet_of(sess, x.id)
        coin_liab += w.coin_p + w.coin_b
        point_liab += w.point_av
    card_liab = sess.query(Card).filter(Card.status.in_(("UNUSED", "LOCKED"))).count()
    tpl_cats = {r.id: r.cat for r in sess.query(CardTpl.id, CardTpl.cat).all()}
    treasure = sum(1 for c in sess.query(Card).filter_by(status="UNUSED").all() if tpl_cats.get(c.tpl) == "OTHER")
    content = setting(sess, "content")
    shop = (content or {}).get("shopInfo") or {}
    block = not (shop.get("name") and shop.get("addr") and shop.get("tel"))
    week = [x.to_dict() for x in sess.query(DailyBiz).order_by(DailyBiz.d.desc()).limit(7).all()]
    pt_alert = point_today_ratio(sess)
    out = {
        "today": today_d,
        "shopAmt": today_d["coin"] + today_d["offline"],
        "todo": {"accept": pa, "pay": pay_od, "recharge": rc_pending, "soldout": soldout},
        "week": week,
        "shop": shop,
        "block": block,
        "alerts": {
            "coinAdjust": [a.to_dict() for a in sess.query(CoinAdjust).filter_by(status="PENDING")],
            "deact": sess.query(Deactivation).filter_by(status="PENDING").count(),
            "pointRatio": pt_alert["ratio"],
            "pointThreshold": pt_alert["threshold"],
            "pointOver": pt_alert["over"],
        },
        "members": len(custs(sess)),
        "orderCount": sess.query(Order).count(),
    }
    if role == "BOSS":
        out["liability"] = {"coin": coin_liab, "point": point_liab, "cards": card_liab, "treasure": treasure}
    return out


def point_today_ratio(sess: Session) -> dict:
    cfg = setting(sess, "config") or {}
    threshold = float(cfg.get("alertRatio") or 3)
    today = today_str()
    by_day: dict[str, int] = {}
    for g in sess.query(GameRecord).all():
        if g.status == "VOID":
            continue
        d = (g.time or "")[:10]
        if not d:
            continue
        pts = sum(int(p.get("pts") or 0) for p in (g.players or []))
        by_day[d] = by_day.get(d, 0) + pts
    today_pts = by_day.get(today, 0)
    hist = [by_day[d] for d in by_day if d != today]
    avg = round(sum(hist) / len(hist)) if hist else 0
    ratio = round(today_pts / avg, 1) if avg else 0.0
    return {"today": today_pts, "avg": avg, "ratio": ratio, "threshold": threshold, "over": ratio >= threshold}


def liab_coin_detail(sess: Session) -> dict:
    rows = []
    for u in custs(sess):
        w = wallet_of(sess, u.id)
        p, b = w.coin_p, w.coin_b
        if p + b <= 0:
            continue
        rows.append({"uid": u.id, "nick": u.nick, "no": u.no, "tail": u.tail or "", "principal": p, "bonus": b, "total": p + b})
    rows.sort(key=lambda x: x["total"], reverse=True)
    tot_p = sum(r["principal"] for r in rows)
    tot_b = sum(r["bonus"] for r in rows)
    tot = tot_p + tot_b
    top5 = sum(r["total"] for r in rows[:5])
    for r in rows:
        r["pct"] = round(r["total"] / tot * 100, 1) if tot else 0
    return {
        "summary": {"total": tot, "principal": tot_p, "bonus": tot_b, "members": len(rows), "top5Pct": round(top5 / tot * 100) if tot else 0},
        "rows": rows,
    }


def liab_point_detail(sess: Session) -> dict:
    rows = []
    neg = []
    for u in custs(sess):
        w = wallet_of(sess, u.id)
        av, fz = w.point_av, w.point_fz or 0
        if av < 0:
            neg.append({"uid": u.id, "nick": u.nick, "no": u.no, "av": av})
        if av > 0 or fz > 0:
            rows.append({"uid": u.id, "nick": u.nick, "no": u.no, "av": av, "fz": fz, "mg": w.point_mg or 0, "wd": w.point_wd or 0})
    rows.sort(key=lambda x: x["av"], reverse=True)
    tot_av = sum(max(r["av"], 0) for r in rows)
    tot_fz = sum(r["fz"] for r in rows)
    costs = [int(r[0] or 0) for r in sess.query(CardTpl.cost).filter(CardTpl.cost > 0).all()]
    min_cost = min(costs) if costs else 0
    return {
        "summary": {"av": tot_av, "fz": tot_fz, "members": len(rows), "maxRedeem": int(tot_av / min_cost) if min_cost else 0, "minCost": min_cost, "negCount": len(neg), "month": current_month()},
        "rows": rows,
        "neg": neg,
    }


def liab_card_detail(sess: Session) -> dict:
    cards = sess.query(Card).filter_by(status="UNUSED").all()
    tpl_map = {r.id: {"name": r.name, "cat": r.cat} for r in sess.query(CardTpl.id, CardTpl.name, CardTpl.cat).all()}
    by_tpl: dict[str, dict] = {}
    by_user: dict[int, int] = {}
    soon = 0
    treasure = 0
    list_rows = []
    for c in cards:
        tm = tpl_map.get(c.tpl) or {}
        name = tm.get("name") or "（模板已删）"
        cat = tm.get("cat") or "—"
        if cat == "OTHER":
            treasure += 1
        if c.days_left <= 3:
            soon += 1
        slot = by_tpl.setdefault(name, {"n": 0, "soon": 0, "cat": cat})
        slot["n"] += 1
        if c.days_left <= 3:
            slot["soon"] += 1
        by_user[c.uid] = by_user.get(c.uid, 0) + 1
        u = sess.get(User, c.uid)
        list_rows.append({**c.to_dict(), "tplName": name, "cat": cat, "nick": u.nick if u else "—", "tail": (u.tail or "") if u else ""})
    list_rows.sort(key=lambda x: x["daysLeft"])
    by_tpl_list = [{"name": k, **v} for k, v in sorted(by_tpl.items(), key=lambda x: -x[1]["n"])]
    return {
        "summary": {"total": len(cards), "soon": soon, "treasure": treasure, "members": len(by_user)},
        "byTpl": by_tpl_list,
        "rows": list_rows,
    }


def point_alert_detail(sess: Session) -> dict:
    base = point_today_ratio(sess)
    today = today_str()
    by_day: dict[str, int] = {}
    for g in sess.query(GameRecord).all():
        if g.status == "VOID":
            continue
        d = (g.time or "")[:10]
        if not d:
            continue
        pts = sum(int(p.get("pts") or 0) for p in (g.players or []))
        by_day[d] = by_day.get(d, 0) + pts
    days = sorted(by_day.keys(), reverse=True)[:10]
    trend = [{"d": d, "pts": by_day[d], "today": d == today} for d in days]
    today_games = []
    by_op: dict[int, dict] = {}
    for g in sess.query(GameRecord).all():
        if g.status == "VOID" or not (g.time or "").startswith(today):
            continue
        gd = g.to_dict()
        today_games.append(gd)
        k = gd.get("opUid") or 0
        slot = by_op.setdefault(k, {"n": 0, "pts": 0, "sh": 0, "op": gd.get("op") or ""})
        slot["n"] += 1
        for p in gd.get("players") or []:
            slot["pts"] += int(p.get("pts") or 0)
            slot["sh"] += int(p.get("sh") or 0)
    today_games.sort(key=lambda x: x.get("time") or "", reverse=True)
    return {
        **base,
        "trend": trend,
        "byOp": [{"opUid": k, **v} for k, v in sorted(by_op.items(), key=lambda x: -x[1]["pts"])],
        "games": today_games,
    }


def signed_days(sess: Session, uid: int) -> list[int]:
    return [r.day for r in sess.query(SignRecord).filter_by(uid=uid, month=current_month()).all()]


DEMO_SIGNED_DAYS = [1, 2, 4, 6, 7, 8, 12, 15, 16, 18, 19, 20, 22, 23, 25]
DEMO_SIGN_STREAK = 6


def grant_demo_sign(sess: Session, uid: int):
    if sess.query(SignRecord).filter_by(uid=uid).count():
        return
    for day in DEMO_SIGNED_DAYS:
        sess.add(SignRecord(uid=uid, day=day, month=current_month()))
    w = wallet_of(sess, uid)
    if not w.sign_streak:
        w.sign_streak = DEMO_SIGN_STREAK


def sign_rules_view(sess: Session) -> list:
    out = []
    for r in sess.query(SignRule).order_by(SignRule.days):
        if r.enabled is False:
            continue
        cards = []
        for c in r.cards or []:
            tm = tpl(sess, c.get("tpl"))
            cards.append({
                "tpl": c.get("tpl"),
                "qty": c.get("qty") or 1,
                "name": tm.name if tm else "卡券",
            })
        out.append({"id": r.id, "days": r.days, "pts": r.pts or 0, "cards": cards})
    return out


def cancel_order(sess: Session, uid: int, oid: int) -> dict:
    o = sess.get(Order, oid)
    if not o or o.uid != uid or o.status != "PENDING_PAY":
        err("无法取消")
    o.status = "CLOSED"
    o.cancel_reason = "USER_CANCEL"
    return o.to_dict()


def deactivate(sess: Session, uid: int, reason: str) -> dict:
    user = u(sess, uid)
    if not user:
        err("用户不存在")
    if user.deact == "DEACTIVATE_PENDING":
        err("已有注销申请")
    w = wallet_of(sess, uid)
    cards = sess.query(Card).filter_by(uid=uid, status="UNUSED").count()
    rec = Deactivation(
        id=next_seq(sess, "deact"),
        no="ZX" + yyMMdd() + rand_digits(4),
        uid=uid, status="PENDING",
        created=f"{today_str()} {clock()}", reason=reason or "",
        snap={"coinP": w.coin_p, "coinB": w.coin_b, "point": w.point_av,
              "pointFz": w.point_fz, "shardW": w.shard_w, "cards": cards},
    )
    sess.add(rec)
    user.deact = "DEACTIVATE_PENDING"
    sess.flush()
    return rec.to_dict()


def exec_deactivation(sess: Session, did: int, action: str, reason: str, admin: dict) -> dict:
    d = sess.get(Deactivation, did)
    if not d or d.status != "PENDING":
        err("已处理")
    usr = u(sess, d.uid)
    if action == "reject":
        d.status = "REJECTED"
        d.audit_remark = reason
        d.audit_by = admin["id"]
        d.audit_at = f"{today_str()} {clock()}"
        if usr:
            usr.deact = None
    else:
        d.status = "DONE"
        d.audit_by = admin["id"]
        d.audit_at = f"{today_str()} {clock()}"
        if usr:
            usr.status = "DEACTIVATED"
            usr.deact = None
            w = wallet_of(sess, usr.id)
            d.refunded = w.coin_p
            d.refund_ok = True
            void_n = 0
            w.coin_p = 0
            w.coin_b = 0
            w.point_av = 0
            for card in sess.query(Card).filter_by(uid=usr.id, status="UNUSED"):
                card.status = "VOID"
                card.void_reason = "账号注销作废"
                void_n += 1
            d.void_cards = void_n
    return d.to_dict()


def approve_coin_adjust(sess: Session, aid: int, action: str) -> dict:
    a = sess.get(CoinAdjust, aid)
    if not a or a.status != "PENDING":
        err("已处理")
    if action == "approve":
        w = wallet_of(sess, a.uid)
        if a.type == "PRINCIPAL":
            w.coin_p += a.delta
        else:
            w.coin_b += a.delta
        a.status = "APPROVED"
    else:
        a.status = "REJECTED"
    return a.to_dict()
