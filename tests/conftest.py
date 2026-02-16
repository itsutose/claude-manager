"""共通テストfixtures."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from claude_manager.config import Config

TESTDATA_DIR = Path(__file__).parent / "testdata"


@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    """tmp_pathベースのConfig。実ファイルシステムに触らない。"""
    claude_dir = tmp_path / ".claude"
    manager_dir = tmp_path / ".claude-manager"
    claude_dir.mkdir()
    manager_dir.mkdir()
    (claude_dir / "projects").mkdir()
    config = Config(claude_dir=claude_dir, manager_dir=manager_dir)
    config.ensure_manager_dir()
    return config


@pytest.fixture
def sample_project(tmp_config: Config) -> Path:
    """1セッション入りのテストプロジェクトをtmp_path内に作る。"""
    project_dir = tmp_config.projects_dir / "-Users-test-my-project"
    project_dir.mkdir()
    shutil.copy(
        TESTDATA_DIR / "sample_session.jsonl",
        project_dir / "sess-001.jsonl",
    )
    shutil.copy(
        TESTDATA_DIR / "sample_index.json",
        project_dir / "sessions-index.json",
    )
    return project_dir


# --- JONLレコード生成ヘルパー ---


def write_jsonl(path: Path, records: list[dict]) -> None:
    """レコード群をJSONLファイルに書き出す。"""
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def make_user_record(
    content: str,
    uuid: str = "msg-001",
    ts: int = 1700000000000,
    git_branch: str | None = "main",
) -> dict:
    record = {
        "type": "user",
        "message": {"content": content},
        "timestamp": ts,
        "uuid": uuid,
        "sessionId": "test-session",
        "parentUuid": "root",
        "isSidechain": False,
        "userType": "external",
        "cwd": "/Users/test/my-project",
    }
    if git_branch:
        record["gitBranch"] = git_branch
    return record


def make_assistant_record(
    text: str,
    uuid: str = "msg-002",
    ts: int = 1700000060000,
    tools: list[dict] | None = None,
) -> dict:
    content: list[dict] = [{"type": "text", "text": text}]
    if tools:
        content.extend(tools)
    return {
        "type": "assistant",
        "message": {"content": content},
        "timestamp": ts,
        "uuid": uuid,
        "sessionId": "test-session",
        "parentUuid": "msg-001",
        "isSidechain": False,
        "userType": "external",
        "cwd": "/Users/test/my-project",
    }
