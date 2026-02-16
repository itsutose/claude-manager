"""ルーターテスト用fixtures."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from claude_manager.config import Config
from claude_manager.main import create_app
from claude_manager.models import ProjectClone, ProjectGroup, SessionEntry
from claude_manager.services.user_data import UserDataStore


def _make_test_session(
    session_id: str = "sess-001",
    clone_id: str = "-Users-test-proj",
    group_id: str = "test-proj",
    custom_title: str | None = None,
    first_prompt: str = "テスト用プロンプト",
    full_path: str = "/tmp/test/sess-001.jsonl",
) -> SessionEntry:
    now = datetime.now(timezone.utc)
    return SessionEntry(
        session_id=session_id,
        clone_id=clone_id,
        group_id=group_id,
        custom_title=custom_title,
        first_prompt=first_prompt,
        message_count=10,
        created=now,
        modified=now,
        git_branch="main",
        is_sidechain=False,
        full_path=full_path,
    )


def _make_test_groups() -> list[ProjectGroup]:
    s1 = _make_test_session(session_id="sess-001", first_prompt="fizzbuzzを書いて")
    s2 = _make_test_session(session_id="sess-002", first_prompt="テストを追加して")
    clone = ProjectClone(
        clone_id="-Users-test-proj",
        clone_name="test-proj",
        project_path="/Users/test/proj",
        sessions=[s1, s2],
    )
    group = ProjectGroup(
        group_id="test-proj",
        display_name="test-proj",
        initials="TP",
        clones=[clone],
    )
    return [group]


@pytest.fixture
async def client(tmp_path):
    """テスト用 AsyncClient。lifespan を迂回してテストデータを注入."""
    config = Config(
        claude_dir=tmp_path / ".claude",
        manager_dir=tmp_path / ".claude-manager",
    )
    config.ensure_manager_dir()
    (config.claude_dir / "projects").mkdir(parents=True, exist_ok=True)

    app = create_app(config)

    # lifespan を迂回: app.stateに直接テストデータ注入
    app.state.groups = _make_test_groups()
    app.state.user_data = UserDataStore(config)
    app.state.config = config

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
