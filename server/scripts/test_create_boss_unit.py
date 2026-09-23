"""Unit tests for create_staff allowing BOSS (no MySQL required)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402


class CreateBossTests(unittest.TestCase):
    def test_rejects_invalid_role(self):
        with self.assertRaisesRegex(ValueError, "角色无效"):
            L.create_staff(MagicMock(), {"phone": "13800138000", "role": "GOD"}, {"role": "BOSS"})

    def test_manager_cannot_add_boss(self):
        with self.assertRaisesRegex(ValueError, "仅老板可添加老板"):
            L.create_staff(
                MagicMock(),
                {"phone": "13800138000", "role": "BOSS", "password": "abcdef"},
                {"role": "MANAGER"},
            )

    def test_boss_requires_password(self):
        with self.assertRaisesRegex(ValueError, "老板需设置"):
            L.create_staff(
                MagicMock(),
                {"phone": "13800138000", "role": "BOSS", "password": "123"},
                {"role": "BOSS", "id": 1},
            )

    @patch("logic.bind_wx_phone")
    @patch("logic.log")
    @patch("logic.users_by_phone", return_value=[])
    @patch("logic.new_id", return_value=9001)
    @patch("logic.alloc_staff_no", return_value="S9001")
    @patch("logic.hash_pwd", return_value="hashed")
    @patch("logic.public_user", side_effect=lambda sess, u: {"id": u.id, "role": u.role, "nick": u.nick})
    def test_boss_creates_boss(self, *_mocks):
        sess = MagicMock()
        out = L.create_staff(
            sess,
            {"phone": "18810801830", "nick": "新老板", "role": "BOSS", "password": "secret12"},
            {"role": "BOSS", "id": 1, "nick": "老板"},
        )
        self.assertEqual(out["role"], "BOSS")
        self.assertEqual(out["nick"], "新老板")
        sess.add.assert_called_once()
        added = sess.add.call_args[0][0]
        self.assertEqual(added.role, "BOSS")
        self.assertEqual(added.pwd, "hashed")
        self.assertEqual(added.tail, "1830")


if __name__ == "__main__":
    raise SystemExit(0 if unittest.main(verbosity=2) is None else 0)
