from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    no: Mapped[str] = mapped_column(String(32), unique=True)
    nick: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(32), default="")
    tail: Mapped[str] = mapped_column(String(8), default="")
    gender: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String(16), default="CUSTOMER")
    team_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE")
    deact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    agreed_version: Mapped[int] = mapped_column(Integer, default=0)
    pwd: Mapped[str] = mapped_column(String(128), default="")
    wx_openid: Mapped[str] = mapped_column(String(64), default="", index=True)

    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")

    def to_public(self, wallet: "Wallet | None" = None, team_name: str | None = None) -> dict:
        w = wallet or self.wallet
        c = {"p": w.coin_p if w else 0, "b": w.coin_b if w else 0}
        p = {
            "av": w.point_av if w else 0,
            "wg": w.point_wg if w else 0,
            "mg": w.point_mg if w else 0,
            "pd": w.point_pd if w else 0,
            "wd": w.point_wd if w else 0,
            "fz": w.point_fz if w else 0,
        }
        sh = {"w": w.shard_w if w else 0, "t": w.shard_t if w else 0}
        nick = self.nick or "玩咖"
        phone = self.phone or ""
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) == 11:
            phone = f"{digits[:3]}****{digits[-4:]}"
        return {
            "id": self.id, "no": self.no, "nick": self.nick,
            "phone": phone, "tail": self.tail,
            "gender": self.gender, "role": self.role, "teamId": self.team_id, "status": self.status,
            "deact": self.deact, "av": nick.strip()[:2], "teamName": team_name,
            "coin": {**c, "total": c["p"] + c["b"]}, "point": p, "shard": sh,
            "agreedVersion": self.agreed_version, "signStreak": w.sign_streak if w else 0,
        }


class Wallet(Base):
    __tablename__ = "wallets"
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    coin_p: Mapped[int] = mapped_column(Integer, default=0)
    coin_b: Mapped[int] = mapped_column(Integer, default=0)
    point_av: Mapped[int] = mapped_column(Integer, default=0)
    point_wg: Mapped[int] = mapped_column(Integer, default=0)
    point_mg: Mapped[int] = mapped_column(Integer, default=0)
    point_pd: Mapped[int] = mapped_column(Integer, default=0)
    point_wd: Mapped[int] = mapped_column(Integer, default=0)
    point_fz: Mapped[int] = mapped_column(Integer, default=0)
    shard_w: Mapped[int] = mapped_column(Integer, default=0)
    shard_t: Mapped[int] = mapped_column(Integer, default=0)
    sign_streak: Mapped[int] = mapped_column(Integer, default=0)
    user: Mapped[User] = relationship(back_populates="wallet")


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))


class Champ(Base):
    __tablename__ = "champs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[int] = mapped_column(Integer, index=True)
    event: Mapped[str] = mapped_column(String(128), default="")
    date: Mapped[str] = mapped_column(String(16), default="")
    n: Mapped[int] = mapped_column(Integer, default=0)
    team_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_name: Mapped[str] = mapped_column(String(64), default="")
    op: Mapped[str] = mapped_column(String(32), default="")

    def to_dict(self):
        return {"uid": self.uid, "event": self.event, "date": self.date, "n": self.n,
                "teamId": self.team_id, "teamName": self.team_name, "op": self.op}


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    min: Mapped[int] = mapped_column(Integer, default=0)
    max: Mapped[int] = mapped_column(Integer, default=0)
    shard: Mapped[int] = mapped_column(Integer, default=0)
    recent: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=99)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "min": self.min, "max": self.max,
                "shard": self.shard, "recent": self.recent, "sort": self.sort, "disabled": self.disabled}


class Category(Base):
    __tablename__ = "cats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    sort: Mapped[int] = mapped_column(Integer, default=99)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "sort": self.sort, "disabled": self.disabled}


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cid: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(64))
    desc: Mapped[str] = mapped_column(String(128), default="")
    price: Mapped[int] = mapped_column(Integer, default=0)
    has_spec: Mapped[bool] = mapped_column(Boolean, default=False)
    spec_multi: Mapped[bool] = mapped_column(Boolean, default=False)
    specs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sold_out: Mapped[bool] = mapped_column(Boolean, default=False)
    img: Mapped[str | None] = mapped_column(String(512), nullable=True)
    type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    combo: Mapped[list | None] = mapped_column(JSON, nullable=True)
    offline: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self):
        d = {"id": self.id, "cid": self.cid, "name": self.name, "desc": self.desc, "price": self.price,
             "hasSpec": self.has_spec, "soldOut": self.sold_out, "offline": self.offline}
        if self.spec_multi:
            d["specMulti"] = True
        if self.specs:
            d["specs"] = self.specs
        if self.img:
            d["img"] = self.img
        if self.type:
            d["type"] = self.type
        if self.combo:
            d["combo"] = self.combo
        return d


class TableSeat(Base):
    __tablename__ = "shop_tables"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    area: Mapped[str] = mapped_column(String(32), default="")
    seats: Mapped[int] = mapped_column(Integer, default=4)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "area": self.area, "seats": self.seats}


class CardTpl(Base):
    __tablename__ = "card_tpls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    cat: Mapped[str] = mapped_column(String(16))
    sub: Mapped[str | None] = mapped_column(String(32), nullable=True)
    desc: Mapped[str] = mapped_column(String(128), default="")
    cost: Mapped[int] = mapped_column(Integer, default=0)
    days: Mapped[int] = mapped_column(Integer, default=30)
    use: Mapped[str] = mapped_column(String(64), default="")
    per_limit: Mapped[int] = mapped_column(Integer, default=-1)
    stock: Mapped[int] = mapped_column(Integer, default=-1)
    exch: Mapped[bool] = mapped_column(Boolean, default=True)
    prize: Mapped[str | None] = mapped_column(String(128), nullable=True)

    def to_dict(self):
        d = {"id": self.id, "name": self.name, "cat": self.cat, "desc": self.desc, "cost": self.cost,
             "days": self.days, "use": self.use, "perLimit": self.per_limit, "stock": self.stock}
        if self.sub:
            d["sub"] = self.sub
        if not self.exch:
            d["exch"] = False
        if self.prize:
            d["prize"] = self.prize
        return d


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[int] = mapped_column(Integer, index=True)
    tpl: Mapped[int] = mapped_column(Integer)
    no: Mapped[str] = mapped_column(String(32))
    src: Mapped[str] = mapped_column(String(32), default="")
    src_desc: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="UNUSED")
    days_left: Mapped[int] = mapped_column(Integer, default=30)
    expire: Mapped[str] = mapped_column(String(16), default="")
    void_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def to_dict(self):
        d = {"id": self.id, "uid": self.uid, "tpl": self.tpl, "no": self.no, "src": self.src,
             "srcDesc": self.src_desc, "status": self.status, "daysLeft": self.days_left, "expire": self.expire}
        if self.void_reason:
            d["voidReason"] = self.void_reason
        return d


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    no: Mapped[str] = mapped_column(String(32), unique=True)
    uid: Mapped[int] = mapped_column(Integer, index=True)
    nick: Mapped[str] = mapped_column(String(64), default="")
    table_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    table_name: Mapped[str] = mapped_column(String(32), default="")
    total: Mapped[int] = mapped_column(Integer, default=0)
    pay_type: Mapped[str] = mapped_column(String(16), default="COIN")
    status: Mapped[str] = mapped_column(String(24), index=True)
    remark: Mapped[str] = mapped_column(String(80), default="")
    ago: Mapped[str] = mapped_column(String(24), default="")
    at: Mapped[str] = mapped_column(String(24), default="")
    op_uid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items: Mapped[list] = mapped_column(JSON, default=list)
    expire_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    paid_principal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paid_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accepted_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self):
        d = {
            "id": self.id, "no": self.no, "uid": self.uid, "nick": self.nick, "tableId": self.table_id,
            "tableName": self.table_name, "total": self.total, "payType": self.pay_type, "status": self.status,
            "remark": self.remark, "ago": self.ago, "at": self.at, "opUid": self.op_uid, "items": self.items or [],
            "expireAt": self.expire_at,
        }
        if self.paid_principal is not None:
            d["paidPrincipal"] = self.paid_principal
        if self.paid_bonus is not None:
            d["paidBonus"] = self.paid_bonus
        if self.cancel_reason:
            d["cancelReason"] = self.cancel_reason
        return d


class Recharge(Base):
    __tablename__ = "recharges"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    no: Mapped[str] = mapped_column(String(32), unique=True)
    uid: Mapped[int] = mapped_column(Integer, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    bonus: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), index=True)
    expire_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created: Mapped[str] = mapped_column(String(24), default="")
    at: Mapped[str] = mapped_column(String(24), default="")
    op_uid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reject_remark: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pending_uid: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    def to_dict(self):
        d = {"id": self.id, "no": self.no, "uid": self.uid, "amount": self.amount, "bonus": self.bonus,
             "status": self.status, "expireAt": self.expire_at, "created": self.created, "at": self.at, "opUid": self.op_uid}
        if self.close_reason:
            d["closeReason"] = self.close_reason
        if self.reject_remark:
            d["rejectRemark"] = self.reject_remark
        return d


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    no: Mapped[str] = mapped_column(String(32), unique=True)
    uid: Mapped[int] = mapped_column(Integer, index=True)
    pts: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), index=True)
    created: Mapped[str] = mapped_column(String(24), default="")
    at: Mapped[str] = mapped_column(String(24), default="")
    expire_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    grant_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grant_at: Mapped[str | None] = mapped_column(String(24), nullable=True)
    reject_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reject_remark: Mapped[str | None] = mapped_column(String(128), nullable=True)
    closed_at: Mapped[str | None] = mapped_column(String(24), nullable=True)
    pending_uid: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    def to_dict(self):
        d = {"id": self.id, "no": self.no, "uid": self.uid, "pts": self.pts, "status": self.status,
             "created": self.created, "at": self.at, "expireAt": self.expire_at}
        if self.grant_by:
            d["grantBy"] = self.grant_by
            d["grantAt"] = self.grant_at
        if self.reject_remark:
            d["rejectBy"] = self.reject_by
            d["rejectRemark"] = self.reject_remark
        if self.closed_at:
            d["closedAt"] = self.closed_at
        return d


class Deactivation(Base):
    __tablename__ = "deactivations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    no: Mapped[str] = mapped_column(String(32), unique=True)
    uid: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16))
    created: Mapped[str] = mapped_column(String(24), default="")
    reason: Mapped[str] = mapped_column(String(128), default="")
    snap: Mapped[dict] = mapped_column(JSON, default=dict)
    audit_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audit_at: Mapped[str | None] = mapped_column(String(24), nullable=True)
    audit_remark: Mapped[str | None] = mapped_column(String(128), nullable=True)
    refund_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    refunded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    void_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self):
        d = {"id": self.id, "no": self.no, "uid": self.uid, "status": self.status,
             "created": self.created, "reason": self.reason, "snap": self.snap}
        if self.audit_by:
            d["auditBy"] = self.audit_by
            d["auditAt"] = self.audit_at
            d["auditRemark"] = self.audit_remark
        if self.refunded is not None:
            d["refunded"] = self.refunded
            d["voidCards"] = self.void_cards
        return d


class CoinAdjust(Base):
    __tablename__ = "coin_adjusts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[int] = mapped_column(Integer)
    delta: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(128), default="")
    adjust_by: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[str] = mapped_column(String(24), default="")
    status: Mapped[str] = mapped_column(String(16), default="PENDING")

    def to_dict(self):
        return {"id": self.id, "uid": self.uid, "delta": self.delta, "type": self.type,
                "reason": self.reason, "by": self.adjust_by, "at": self.at, "status": self.status}


class Tier(Base):
    __tablename__ = "tiers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer)
    bonus: Mapped[int] = mapped_column(Integer, default=0)
    rec: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self):
        return {"id": self.id, "amount": self.amount, "bonus": self.bonus, "rec": self.rec}


class SignRule(Base):
    __tablename__ = "sign_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    days: Mapped[int] = mapped_column(Integer)
    pts: Mapped[int] = mapped_column(Integer, default=0)
    cards: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_dict(self):
        return {"id": self.id, "days": self.days, "pts": self.pts, "cards": self.cards or [], "enabled": self.enabled}


class SignRecord(Base):
    __tablename__ = "sign_records"
    __table_args__ = (UniqueConstraint("uid", "month", "day", name="uk_sign_uid_month_day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[int] = mapped_column(Integer, index=True)
    day: Mapped[int] = mapped_column(Integer)
    month: Mapped[str] = mapped_column(String(7), default=lambda: date.today().strftime("%Y-%m"))


class GameRecord(Base):
    __tablename__ = "game_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pid: Mapped[int] = mapped_column(Integer, default=0)
    pname: Mapped[str] = mapped_column(String(64), default="")
    table: Mapped[str] = mapped_column(String(32), default="")
    round: Mapped[str] = mapped_column(String(32), default="")
    time: Mapped[str] = mapped_column(String(24), default="")
    op: Mapped[str] = mapped_column(String(32), default="")
    op_uid: Mapped[int] = mapped_column(Integer, default=0)
    players: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    def to_dict(self):
        d = {"id": self.id, "pid": self.pid, "pname": self.pname, "table": self.table, "round": self.round,
             "time": self.time, "op": self.op, "opUid": self.op_uid, "players": self.players or []}
        if self.status:
            d["status"] = self.status
        return d


class DailyBiz(Base):
    __tablename__ = "daily_biz"
    d: Mapped[str] = mapped_column(String(10), primary_key=True)
    coin: Mapped[int] = mapped_column(Integer, default=0)
    offline: Mapped[int] = mapped_column(Integer, default=0)
    recharge: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    guests: Mapped[int] = mapped_column(Integer, default=0)

    def to_dict(self):
        return {"d": self.d, "coin": self.coin, "offline": self.offline, "recharge": self.recharge,
                "orders": self.orders, "guests": self.guests}


class VerifyLog(Base):
    __tablename__ = "verify_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_no: Mapped[str] = mapped_column(String(32), default="")
    tpl_name: Mapped[str] = mapped_column(String(64), default="")
    uid: Mapped[int] = mapped_column(Integer, default=0)
    op_uid: Mapped[int] = mapped_column(Integer, default=0)
    at: Mapped[str] = mapped_column(String(24), default="")

    def to_dict(self):
        return {"id": self.id, "cardNo": self.card_no, "tplName": self.tpl_name, "uid": self.uid, "opUid": self.op_uid, "at": self.at}


class SettleLog(Base):
    __tablename__ = "settle_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[str] = mapped_column(String(32), default="")
    type: Mapped[str] = mapped_column(String(32), default="")
    sub: Mapped[str] = mapped_column(String(32), default="")
    target: Mapped[str] = mapped_column(String(64), default="")
    nick: Mapped[str] = mapped_column(String(64), default="")
    sh: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="")
    card_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    desc: Mapped[str] = mapped_column(String(128), default="")

    def to_dict(self):
        return {"id": self.id, "week": self.week, "type": self.type, "sub": self.sub, "target": self.target,
                "nick": self.nick, "sh": self.sh, "status": self.status, "cardId": self.card_id, "desc": self.desc}


class OpLog(Base):
    __tablename__ = "op_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    t: Mapped[str] = mapped_column(String(24), default="")
    op: Mapped[str] = mapped_column(String(32), default="")
    role: Mapped[str] = mapped_column(String(16), default="")
    action: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    uid: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def to_dict(self):
        return {"t": self.t, "op": self.op, "role": self.role, "action": self.action, "detail": self.detail, "uid": self.uid}


class AgreeLog(Base):
    __tablename__ = "agree_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc: Mapped[str] = mapped_column(String(16))
    ver: Mapped[int] = mapped_column(Integer)
    uid: Mapped[int] = mapped_column(Integer)
    at: Mapped[str] = mapped_column(String(24), default="")

    def to_dict(self):
        return {"doc": self.doc, "ver": self.ver, "uid": self.uid, "at": self.at}


class Setting(Base):
    __tablename__ = "settings"
    k: Mapped[str] = mapped_column(String(32), primary_key=True)
    v: Mapped[dict] = mapped_column(JSON)
