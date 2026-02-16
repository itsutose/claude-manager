"""user_data.py のテスト."""
from __future__ import annotations

from claude_manager.services.user_data import UserDataStore


class TestPinManagement:
    def test_initial_pinned_empty(self, tmp_config):
        store = UserDataStore(tmp_config)
        assert store.get_pinned_sessions() == set()

    def test_toggle_pin_on(self, tmp_config):
        store = UserDataStore(tmp_config)
        result = store.toggle_pin("sess-1")
        assert result is True
        assert "sess-1" in store.get_pinned_sessions()

    def test_toggle_pin_off(self, tmp_config):
        store = UserDataStore(tmp_config)
        store.toggle_pin("sess-1")  # on
        result = store.toggle_pin("sess-1")  # off
        assert result is False
        assert "sess-1" not in store.get_pinned_sessions()

    def test_multiple_pins(self, tmp_config):
        store = UserDataStore(tmp_config)
        store.toggle_pin("s1")
        store.toggle_pin("s2")
        pinned = store.get_pinned_sessions()
        assert "s1" in pinned
        assert "s2" in pinned


class TestReadManagement:
    def test_mark_read(self, tmp_config):
        store = UserDataStore(tmp_config)
        store.mark_read("sess-1")
        states = store.get_read_states()
        assert "sess-1" in states

    def test_mark_read_overwrites(self, tmp_config):
        store = UserDataStore(tmp_config)
        store.mark_read("sess-1")
        old_ts = store.get_read_states()["sess-1"]
        store.mark_read("sess-1")
        new_ts = store.get_read_states()["sess-1"]
        # 新しいタイムスタンプに更新される（同一秒内だと同じ可能性あり）
        assert new_ts >= old_ts

    def test_initial_read_empty(self, tmp_config):
        store = UserDataStore(tmp_config)
        assert store.get_read_states() == {}


class TestHiddenManagement:
    def test_initial_hidden_empty(self, tmp_config):
        store = UserDataStore(tmp_config)
        assert store.get_hidden_sessions() == set()

    def test_hide_session(self, tmp_config):
        store = UserDataStore(tmp_config)
        result = store.hide_session("sess-1")
        assert result is True
        assert "sess-1" in store.get_hidden_sessions()

    def test_unhide_session(self, tmp_config):
        store = UserDataStore(tmp_config)
        store.hide_session("sess-1")
        result = store.unhide_session("sess-1")
        assert result is True
        assert "sess-1" not in store.get_hidden_sessions()

    def test_list_hidden(self, tmp_config):
        store = UserDataStore(tmp_config)
        store.hide_session("s1")
        store.hide_session("s2")
        hidden = store.list_hidden_sessions()
        assert len(hidden) == 2

    def test_hide_idempotent(self, tmp_config):
        store = UserDataStore(tmp_config)
        store.hide_session("s1")
        store.hide_session("s1")
        assert len(store.get_hidden_sessions()) == 1
