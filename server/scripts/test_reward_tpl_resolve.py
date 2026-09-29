"""Unit tests for settlement reward cardTpl resolution."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logic as L  # noqa: E402


def _tpl(**kwargs):
    return SimpleNamespace(
        id=kwargs.get("id", 6),
        name=kwargs.get("name", "黄金宝箱卡"),
        sub=kwargs.get("sub", "TREASURE_GOLD"),
        cat=kwargs.get("cat", "OTHER"),
    )


class RewardTplResolveTests(unittest.TestCase):
    def test_resolve_by_id(self):
        tm = _tpl(id=6)
        sess = MagicMock()
        sess.get.return_value = tm
        self.assertIs(L.resolve_reward_card_tpl(sess, "6"), tm)
        self.assertIs(L.resolve_reward_card_tpl(sess, 6), tm)

    def test_resolve_by_legacy_sub(self):
        tm = _tpl(id=6, sub="TREASURE_GOLD")
        sess = MagicMock()
        sess.query.return_value.filter.return_value.first.return_value = tm
        self.assertIs(L.resolve_reward_card_tpl(sess, "TREASURE_GOLD"), tm)

    def test_resolve_missing_returns_none(self):
        sess = MagicMock()
        sess.get.return_value = None
        sess.query.return_value.filter.return_value.first.return_value = None
        self.assertIsNone(L.resolve_reward_card_tpl(sess, "TREASURE_GONE"))
        self.assertIsNone(L.resolve_reward_card_tpl(sess, "9999"))

    def test_normalize_rewrites_sub_to_id_and_drops_deleted(self):
        gold = _tpl(id=6, sub="TREASURE_GOLD")
        team = _tpl(id=8, sub="TREASURE_TEAM", name="战队宝箱卡")

        def resolve(_sess, ref):
            raw = str(ref or "")
            if raw in ("6", "TREASURE_GOLD"):
                return gold
            if raw in ("8", "TREASURE_TEAM"):
                return team
            return None

        from unittest.mock import patch

        sess = MagicMock()
        cfg = {
            "prizeMap": {"1": "TREASURE_GOLD", "2": "TREASURE_GONE", "3": "6"},
            "teamCard": "TREASURE_TEAM",
        }
        with patch.object(L, "resolve_reward_card_tpl", side_effect=resolve):
            out = L.normalize_settlement_cfg_refs(sess, cfg)
        self.assertEqual(out["prizeMap"], {"1": "6", "3": "6"})
        self.assertEqual(out["teamCard"], "8")
        self.assertNotIn("2", out["prizeMap"])


if __name__ == "__main__":
    unittest.main()
