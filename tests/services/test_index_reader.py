"""index_reader.py のテスト."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.services.index_reader import (
    _from_jsonl_file,
    _load_titles,
    _parse_datetime,
    read_all_sessions,
)
from tests.conftest import make_assistant_record, make_user_record, write_jsonl


class TestParseDatetime:
    def test_unix_ms(self):
        dt = _parse_datetime(1700000000000)
        assert dt.year == 2023
        assert dt.tzinfo is not None

    def test_iso_string(self):
        dt = _parse_datetime("2024-06-15T12:00:00Z")
        assert dt.year == 2024
        assert dt.month == 6

    def test_none_returns_now(self):
        dt = _parse_datetime(None)
        assert (datetime.now(timezone.utc) - dt).total_seconds() < 2

    def test_invalid_string_returns_now(self):
        dt = _parse_datetime("invalid")
        assert (datetime.now(timezone.utc) - dt).total_seconds() < 2

    def test_float_ms(self):
        dt = _parse_datetime(1700000000000.0)
        assert dt.year == 2023


class TestLoadTitles:
    def test_reads_titles(self, tmp_config):
        tmp_config.titles_file.write_text(json.dumps({"s1": "My Title"}))
        result = _load_titles(tmp_config)
        assert result == {"s1": "My Title"}

    def test_no_file_returns_empty(self, tmp_config):
        result = _load_titles(tmp_config)
        assert result == {}

    def test_invalid_json_returns_empty(self, tmp_config):
        tmp_config.titles_file.write_text("not json")
        result = _load_titles(tmp_config)
        assert result == {}


class TestFromJsonlFile:
    def test_basic_session(self, tmp_path: Path):
        jsonl = tmp_path / "sess-abc.jsonl"
        write_jsonl(jsonl, [
            make_user_record("テストプロンプト", uuid="u1"),
            make_assistant_record("回答", uuid="a1"),
        ])
        session = _from_jsonl_file(jsonl, tmp_path)
        assert session is not None
        assert session.session_id == "sess-abc"
        assert session.first_prompt == "テストプロンプト"
        assert session.message_count == 2
        assert session.git_branch == "main"

    def test_empty_file_returns_none(self, tmp_path: Path):
        jsonl = tmp_path / "empty.jsonl"
        jsonl.write_text("")
        assert _from_jsonl_file(jsonl, tmp_path) is None

    def test_no_messages_returns_none(self, tmp_path: Path):
        jsonl = tmp_path / "meta-only.jsonl"
        write_jsonl(jsonl, [
            {"type": "tool_result", "content": "ok", "tool_use_id": "t1"},
        ])
        assert _from_jsonl_file(jsonl, tmp_path) is None

    def test_git_branch_extracted(self, tmp_path: Path):
        jsonl = tmp_path / "branch.jsonl"
        write_jsonl(jsonl, [
            make_user_record("test", git_branch="feature/foo"),
            make_assistant_record("ok"),
        ])
        session = _from_jsonl_file(jsonl, tmp_path)
        assert session is not None
        assert session.git_branch == "feature/foo"

    def test_no_git_branch(self, tmp_path: Path):
        jsonl = tmp_path / "nobranch.jsonl"
        write_jsonl(jsonl, [
            make_user_record("test", git_branch=None),
            make_assistant_record("ok"),
        ])
        session = _from_jsonl_file(jsonl, tmp_path)
        assert session is not None
        assert session.git_branch is None

    def test_custom_title_from_jsonl(self, tmp_path: Path):
        """JSONL 内の custom-title レコードが読み取れる."""
        jsonl = tmp_path / "titled.jsonl"
        write_jsonl(jsonl, [
            make_user_record("long prompt text here"),
            make_assistant_record("response"),
            {"type": "custom-title", "customTitle": "My Custom Title", "sessionId": "titled"},
        ])
        session = _from_jsonl_file(jsonl, tmp_path)
        assert session is not None
        assert session.custom_title == "My Custom Title"

    def test_last_custom_title_wins(self, tmp_path: Path):
        """複数の custom-title がある場合、最後のものが採用される."""
        jsonl = tmp_path / "multi.jsonl"
        write_jsonl(jsonl, [
            make_user_record("test"),
            {"type": "custom-title", "customTitle": "First Title", "sessionId": "multi"},
            make_assistant_record("ok"),
            {"type": "custom-title", "customTitle": "Second Title", "sessionId": "multi"},
        ])
        session = _from_jsonl_file(jsonl, tmp_path)
        assert session is not None
        assert session.custom_title == "Second Title"

    def test_no_custom_title_returns_none(self, tmp_path: Path):
        """custom-title レコードがなければ custom_title は None."""
        jsonl = tmp_path / "notitle.jsonl"
        write_jsonl(jsonl, [
            make_user_record("test"),
            make_assistant_record("ok"),
        ])
        session = _from_jsonl_file(jsonl, tmp_path)
        assert session is not None
        assert session.custom_title is None


class TestReadAllSessions:
    def test_basic_read(self, tmp_config):
        """JSONL のみでセッションが読める（sessions-index.json 不要）."""
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        write_jsonl(project_dir / "s1.jsonl", [
            make_user_record("hello"),
            make_assistant_record("world"),
        ])

        sessions = read_all_sessions(tmp_config)
        assert len(sessions) == 1
        assert sessions[0].session_id == "s1"
        assert sessions[0].first_prompt == "hello"

    def test_titles_json_overrides_jsonl_custom_title(self, tmp_config):
        """titles.json のタイトルが JSONL の custom-title より優先される."""
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        write_jsonl(project_dir / "s1.jsonl", [
            make_user_record("hello"),
            make_assistant_record("world"),
            {"type": "custom-title", "customTitle": "JSONL Title", "sessionId": "s1"},
        ])
        # titles.json に別タイトル
        tmp_config.titles_file.write_text(json.dumps({"s1": "Manager Title"}))

        sessions = read_all_sessions(tmp_config)
        assert len(sessions) == 1
        assert sessions[0].custom_title == "Manager Title"

    def test_jsonl_custom_title_used_when_no_titles_json(self, tmp_config):
        """titles.json がなければ JSONL の custom-title が使われる."""
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        write_jsonl(project_dir / "s1.jsonl", [
            make_user_record("hello"),
            make_assistant_record("world"),
            {"type": "custom-title", "customTitle": "JSONL Title", "sessionId": "s1"},
        ])

        sessions = read_all_sessions(tmp_config)
        assert len(sessions) == 1
        assert sessions[0].custom_title == "JSONL Title"

    def test_empty_projects_dir(self, tmp_config):
        sessions = read_all_sessions(tmp_config)
        assert sessions == []

    def test_skips_non_jsonl_files(self, tmp_config):
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        (project_dir / "readme.txt").write_text("not a session")
        sessions = read_all_sessions(tmp_config)
        assert sessions == []

    def test_ignores_sessions_index_json(self, tmp_config):
        """sessions-index.json があっても無視し、JSONL のみから読む."""
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        # sessions-index.json にだけ存在するエントリ → 読まれないことを確認
        index_data = {
            "entries": [{
                "sessionId": "ghost",
                "firstPrompt": "should not appear",
                "messageCount": 5,
            }],
        }
        (project_dir / "sessions-index.json").write_text(json.dumps(index_data))
        # JSONL は別のセッション
        write_jsonl(project_dir / "real.jsonl", [
            make_user_record("real session"),
            make_assistant_record("ok"),
        ])

        sessions = read_all_sessions(tmp_config)
        assert len(sessions) == 1
        assert sessions[0].session_id == "real"
