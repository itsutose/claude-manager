"""index_reader.py のテスト."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.services.index_reader import (
    _from_jsonl_file,
    _load_index_entries,
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


class TestLoadIndexEntries:
    def test_reads_entries(self, tmp_path: Path):
        data = {
            "version": 1,
            "entries": [
                {"sessionId": "s1", "firstPrompt": "hello"},
                {"sessionId": "s2", "firstPrompt": "world"},
            ],
        }
        (tmp_path / "sessions-index.json").write_text(json.dumps(data))
        result = _load_index_entries(tmp_path)
        assert "s1" in result
        assert "s2" in result

    def test_no_file_returns_empty(self, tmp_path: Path):
        result = _load_index_entries(tmp_path)
        assert result == {}

    def test_invalid_json_returns_empty(self, tmp_path: Path):
        (tmp_path / "sessions-index.json").write_text("not json")
        result = _load_index_entries(tmp_path)
        assert result == {}

    def test_skips_entry_without_session_id(self, tmp_path: Path):
        data = {
            "entries": [
                {"firstPrompt": "no id"},
                {"sessionId": "s1", "firstPrompt": "has id"},
            ],
        }
        (tmp_path / "sessions-index.json").write_text(json.dumps(data))
        result = _load_index_entries(tmp_path)
        assert len(result) == 1
        assert "s1" in result


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


class TestReadAllSessions:
    def test_basic_read(self, tmp_config):
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        index_data = {
            "entries": [{
                "sessionId": "s1",
                "firstPrompt": "hello",
                "messageCount": 5,
                "created": 1700000000000,
                "modified": 1700000060000,
            }],
        }
        (project_dir / "sessions-index.json").write_text(json.dumps(index_data))
        write_jsonl(project_dir / "s1.jsonl", [
            make_user_record("hello"),
        ])

        sessions = read_all_sessions(tmp_config)
        assert len(sessions) == 1
        assert sessions[0].session_id == "s1"
        assert sessions[0].first_prompt == "hello"

    def test_orphan_session(self, tmp_config):
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        # indexなし、JSONLのみ
        write_jsonl(project_dir / "orphan.jsonl", [
            make_user_record("orphan prompt"),
            make_assistant_record("response"),
        ])

        sessions = read_all_sessions(tmp_config)
        assert len(sessions) == 1
        assert sessions[0].first_prompt == "orphan prompt"

    def test_empty_projects_dir(self, tmp_config):
        sessions = read_all_sessions(tmp_config)
        assert sessions == []

    def test_skips_non_jsonl_files(self, tmp_config):
        project_dir = tmp_config.projects_dir / "-Users-test-proj"
        project_dir.mkdir()
        (project_dir / "readme.txt").write_text("not a session")
        sessions = read_all_sessions(tmp_config)
        assert sessions == []
