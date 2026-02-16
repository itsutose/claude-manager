"""テスト用ファクトリ関数."""
from __future__ import annotations

from datetime import datetime, timezone

from claude_manager.models import (
    ProjectClone,
    ProjectGroup,
    SessionEntry,
)


def make_session(
    session_id: str = "sess-001",
    clone_id: str = "-Users-test-my-project",
    group_id: str = "my-project",
    custom_title: str | None = None,
    first_prompt: str = "テスト用プロンプト",
    message_count: int = 10,
    created: datetime | None = None,
    modified: datetime | None = None,
    git_branch: str | None = "main",
    is_sidechain: bool = False,
    full_path: str = "/tmp/test/sess-001.jsonl",
    is_pinned: bool = False,
    has_unread: bool = False,
) -> SessionEntry:
    now = datetime.now(timezone.utc)
    return SessionEntry(
        session_id=session_id,
        clone_id=clone_id,
        group_id=group_id,
        custom_title=custom_title,
        first_prompt=first_prompt,
        message_count=message_count,
        created=created or now,
        modified=modified or now,
        git_branch=git_branch,
        is_sidechain=is_sidechain,
        full_path=full_path,
        is_pinned=is_pinned,
        has_unread=has_unread,
    )


def make_clone(
    clone_id: str = "-Users-test-my-project",
    clone_name: str = "my-project",
    project_path: str = "/Users/test/my-project",
    sessions: list[SessionEntry] | None = None,
) -> ProjectClone:
    return ProjectClone(
        clone_id=clone_id,
        clone_name=clone_name,
        project_path=project_path,
        sessions=sessions if sessions is not None else [],
    )


def make_group(
    group_id: str = "my-project",
    display_name: str = "my-project",
    initials: str = "MP",
    clones: list[ProjectClone] | None = None,
) -> ProjectGroup:
    return ProjectGroup(
        group_id=group_id,
        display_name=display_name,
        initials=initials,
        clones=clones if clones is not None else [],
    )
