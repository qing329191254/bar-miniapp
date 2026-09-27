"""Offline unit checks for member quick-adjust helpers (no MySQL)."""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import logic as L


def test_today_active_start_is_midnight():
    ts = L._today_active_start()
    now = L.business_now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    assert abs(ts - start.timestamp()) < 1


def test_stamp_today_active_members():
    sess = MagicMock()
    users = [
        SimpleNamespace(id=1, role="CUSTOMER", status="ACTIVE", last_active_at=0),
        SimpleNamespace(id=2, role="CUSTOMER", status="ACTIVE", last_active_at=0),
    ]
    q = MagicMock()
    sess.query.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.all.return_value = users
    n = L.stamp_today_active_members(sess, 8)
    assert n == 2
    assert users[0].last_active_at > users[1].last_active_at > 0
    sess.flush.assert_called()


def test_staff_adjust_roles():
    assert "STAFF" in L.STAFF_ADJUST_ROLES
    assert "BOSS" in L.STAFF_ADJUST_ROLES


def test_revoke_cards_validates_qty():
    sess = MagicMock()
    try:
        L.member_revoke_cards(sess, 1, 1, 0, "原因够长", {"role": "BOSS", "id": 1})
        assert False, "should raise"
    except ValueError as e:
        assert "数量" in str(e)


def test_revoke_cards_permission():
    sess = MagicMock()
    try:
        L.member_revoke_cards(sess, 1, 1, 1, "原因够长", {"role": "STAFF", "id": 1})
        assert False, "should raise"
    except ValueError as e:
        assert "无权" in str(e)


def test_revoke_with_staff_roles_allowed_path():
    """STAFF can revoke when roles=STAFF_ADJUST_ROLES; fails later on missing user."""
    sess = MagicMock()
    sess.get.return_value = None
    try:
        L.member_revoke_cards(
            sess, 1, 1, 1, "原因够长", {"role": "STAFF", "id": 51},
            roles=L.STAFF_ADJUST_ROLES,
        )
        assert False
    except ValueError as e:
        assert "会员不存在" in str(e)


if __name__ == "__main__":
    test_today_active_start_is_midnight()
    test_stamp_today_active_members()
    test_staff_adjust_roles()
    test_revoke_cards_validates_qty()
    test_revoke_cards_permission()
    test_revoke_with_staff_roles_allowed_path()
    print("UNIT TESTS PASSED")
