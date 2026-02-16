"""message_parser.py のテスト."""
from __future__ import annotations

import json
from pathlib import Path

from claude_manager.services.message_parser import (
    _extract_text_content,
    _extract_tool_uses,
    parse_session_messages,
)
from tests.conftest import make_assistant_record, make_user_record, write_jsonl


class TestExtractTextContent:
    def test_string_content(self):
        assert _extract_text_content("hello") == "hello"

    def test_list_content(self):
        content = [
            {"type": "text", "text": "part1"},
            {"type": "text", "text": "part2"},
        ]
        assert _extract_text_content(content) == "part1\npart2"

    def test_list_with_non_text(self):
        content = [
            {"type": "thinking", "thinking": "hmm"},
            {"type": "text", "text": "visible"},
        ]
        assert _extract_text_content(content) == "visible"

    def test_empty_list(self):
        assert _extract_text_content([]) == ""

    def test_non_string_non_list(self):
        assert _extract_text_content(42) == ""  # type: ignore[arg-type]


class TestExtractToolUses:
    def test_single_tool_use(self):
        content = [
            {"type": "tool_use", "name": "Bash", "id": "t1", "input": {"command": "ls"}},
        ]
        tools = _extract_tool_uses(content)
        assert len(tools) == 1
        assert tools[0].tool_name == "Bash"
        assert "ls" in tools[0].input_summary

    def test_file_path_tool(self):
        content = [
            {"type": "tool_use", "name": "Read", "id": "t1", "input": {"file_path": "/foo/bar.py"}},
        ]
        tools = _extract_tool_uses(content)
        assert tools[0].input_summary == "/foo/bar.py"

    def test_no_tool_use(self):
        content = [{"type": "text", "text": "hello"}]
        tools = _extract_tool_uses(content)
        assert tools == []

    def test_non_list_returns_empty(self):
        assert _extract_tool_uses("not a list") == []  # type: ignore[arg-type]


class TestParseSessionMessages:
    def test_basic_conversation(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        write_jsonl(jsonl, [
            make_user_record("質問"),
            make_assistant_record("回答"),
        ])
        msgs = parse_session_messages(str(jsonl))
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[0].content == "質問"
        assert msgs[1].role == "assistant"
        assert msgs[1].content == "回答"

    def test_with_limit(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        write_jsonl(jsonl, [
            make_user_record("q1", uuid="u1", ts=1000),
            make_assistant_record("a1", uuid="a1", ts=2000),
            make_user_record("q2", uuid="u2", ts=3000),
        ])
        msgs = parse_session_messages(str(jsonl), limit=2)
        assert len(msgs) == 2

    def test_with_offset(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        write_jsonl(jsonl, [
            make_user_record("q1", uuid="u1", ts=1000),
            make_assistant_record("a1", uuid="a1", ts=2000),
            make_user_record("q2", uuid="u2", ts=3000),
        ])
        msgs = parse_session_messages(str(jsonl), offset=1)
        assert len(msgs) == 2
        assert msgs[0].role == "assistant"

    def test_nonexistent_file(self):
        msgs = parse_session_messages("/nonexistent/path.jsonl")
        assert msgs == []

    def test_tool_result_linked(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        records = [
            make_user_record("ファイルを読んで"),
            make_assistant_record(
                "ファイルを読みます",
                tools=[{"type": "tool_use", "name": "Read", "id": "tu-1", "input": {"file_path": "/x.py"}}],
            ),
            {"type": "tool_result", "tool_use_id": "tu-1", "content": "file content here", "timestamp": 3000},
        ]
        write_jsonl(jsonl, records)
        msgs = parse_session_messages(str(jsonl))
        assert len(msgs) == 2
        assistant_msg = msgs[1]
        assert len(assistant_msg.tool_uses) == 1
        assert assistant_msg.tool_uses[0].output_summary == "file content here"

    def test_thinking_only_skipped(self, tmp_path: Path):
        jsonl = tmp_path / "test.jsonl"
        write_jsonl(jsonl, [
            make_user_record("質問"),
            {
                "type": "assistant",
                "message": {"content": [{"type": "thinking", "thinking": "考え中..."}]},
                "timestamp": 2000,
                "uuid": "a1",
                "sessionId": "s1",
                "parentUuid": "u1",
                "isSidechain": False,
                "userType": "external",
                "cwd": "/tmp",
            },
        ])
        msgs = parse_session_messages(str(jsonl))
        # thinking-onlyのassistantメッセージはスキップされる
        assert len(msgs) == 1
        assert msgs[0].role == "user"
