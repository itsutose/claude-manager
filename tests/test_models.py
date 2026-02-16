"""models.py のテスト."""

from datetime import datetime, timedelta, timezone

from claude_manager.models import SessionStatus
from tests.factories import make_clone, make_group, make_session


class TestSessionEntryDisplayName:
    def test_uses_custom_title(self):
        s = make_session(custom_title="カスタム", first_prompt="長いプロンプト")
        assert s.display_name == "カスタム"

    def test_uses_first_prompt_when_no_title(self):
        s = make_session(custom_title=None, first_prompt="fizzbuzzを書いて")
        assert s.display_name == "fizzbuzzを書いて"

    def test_strips_xml_tags(self):
        s = make_session(
            custom_title=None, first_prompt="<context>除去される</context>本題"
        )
        assert "<" not in s.display_name
        assert "本題" in s.display_name

    def test_truncates_at_50_chars(self):
        long_prompt = "あ" * 60
        s = make_session(custom_title=None, first_prompt=long_prompt)
        assert len(s.display_name) == 53  # 50 + "..."
        assert s.display_name.endswith("...")

    def test_empty_prompt_returns_nameless(self):
        s = make_session(custom_title=None, first_prompt="")
        assert s.display_name == "(名前なし)"

    def test_xml_only_prompt_returns_nameless(self):
        s = make_session(custom_title=None, first_prompt="<tag></tag>")
        assert s.display_name == "(名前なし)"


class TestSessionEntryStatus:
    def test_active_within_one_hour(self):
        s = make_session(modified=datetime.now(timezone.utc) - timedelta(minutes=30))
        assert s.status == SessionStatus.ACTIVE

    def test_recent_within_24_hours(self):
        s = make_session(modified=datetime.now(timezone.utc) - timedelta(hours=5))
        assert s.status == SessionStatus.RECENT

    def test_idle_within_7_days(self):
        s = make_session(modified=datetime.now(timezone.utc) - timedelta(days=3))
        assert s.status == SessionStatus.IDLE

    def test_archived_older_than_7_days(self):
        s = make_session(modified=datetime.now(timezone.utc) - timedelta(days=10))
        assert s.status == SessionStatus.ARCHIVED


class TestSessionEntryToDict:
    def test_has_all_keys(self):
        s = make_session()
        d = s.to_dict()
        expected_keys = {
            "session_id",
            "clone_id",
            "group_id",
            "display_name",
            "custom_title",
            "first_prompt",
            "message_count",
            "created",
            "modified",
            "git_branch",
            "is_sidechain",
            "is_pinned",
            "has_unread",
            "status",
        }
        assert set(d.keys()) == expected_keys

    def test_first_prompt_truncated_to_100(self):
        s = make_session(first_prompt="x" * 200)
        d = s.to_dict()
        assert len(d["first_prompt"]) == 100

    def test_dates_are_iso_format(self):
        s = make_session()
        d = s.to_dict()
        # ISO形式なら"T"を含む
        assert "T" in d["created"]
        assert "T" in d["modified"]


class TestProjectClone:
    def test_session_count(self):
        s1 = make_session(session_id="s1")
        s2 = make_session(session_id="s2")
        clone = make_clone(sessions=[s1, s2])
        assert clone.session_count == 2

    def test_latest_modified(self):
        old = make_session(
            session_id="s1", modified=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        new = make_session(
            session_id="s2", modified=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        clone = make_clone(sessions=[old, new])
        assert clone.latest_modified == datetime(2024, 6, 1, tzinfo=timezone.utc)

    def test_empty_clone(self):
        clone = make_clone(sessions=[])
        assert clone.session_count == 0
        assert clone.latest_modified is None
        assert clone.current_branch is None


class TestProjectGroup:
    def test_total_sessions(self):
        s1 = make_session(session_id="s1")
        s2 = make_session(session_id="s2")
        c1 = make_clone(clone_id="c1", sessions=[s1])
        c2 = make_clone(clone_id="c2", sessions=[s2])
        g = make_group(clones=[c1, c2])
        assert g.total_sessions == 2

    def test_active_sessions(self):
        active = make_session(session_id="s1", modified=datetime.now(timezone.utc))
        old = make_session(
            session_id="s2", modified=datetime.now(timezone.utc) - timedelta(days=2)
        )
        clone = make_clone(sessions=[active, old])
        g = make_group(clones=[clone])
        assert g.active_sessions == 1

    def test_total_messages(self):
        s1 = make_session(session_id="s1", message_count=10)
        s2 = make_session(session_id="s2", message_count=20)
        clone = make_clone(sessions=[s1, s2])
        g = make_group(clones=[clone])
        assert g.total_messages == 30

    def test_to_dict_without_sessions(self):
        g = make_group()
        d = g.to_dict(include_sessions=False)
        assert "clones" not in d
        assert "group_id" in d

    def test_to_dict_with_sessions(self):
        clone = make_clone(sessions=[make_session()])
        g = make_group(clones=[clone])
        d = g.to_dict(include_sessions=True)
        assert "clones" in d
        assert len(d["clones"]) == 1
