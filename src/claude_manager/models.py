from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

# セッション名に含まれるXML風タグを除去するパターン
_TAG_RE = re.compile(r"<[^>]+>")


class SessionStatus(str, Enum):
    ACTIVE = "active"      # modified within 1 hour
    RECENT = "recent"      # modified within 24 hours
    IDLE = "idle"          # modified within 7 days
    ARCHIVED = "archived"  # older than 7 days


@dataclass
class ToolUse:
    tool_name: str
    input_summary: str
    output_summary: str


@dataclass
class SessionMessage:
    message_id: str
    role: str  # "user" / "assistant"
    content: str
    timestamp: datetime | None = None
    tool_uses: list[ToolUse] = field(default_factory=list)


@dataclass
class SessionEntry:
    session_id: str
    clone_id: str
    group_id: str
    custom_title: str | None
    first_prompt: str
    message_count: int
    created: datetime
    modified: datetime
    git_branch: str | None
    is_sidechain: bool
    full_path: str
    is_pinned: bool = False
    has_unread: bool = False

    @property
    def display_name(self) -> str:
        if self.custom_title:
            return self.custom_title
        if self.first_prompt:
            text = _TAG_RE.sub("", self.first_prompt).strip()
            if not text:
                return "(名前なし)"
            return text[:50] + ("..." if len(text) > 50 else "")
        return "(名前なし)"

    @property
    def status(self) -> SessionStatus:
        now = datetime.now(timezone.utc)
        delta = now - self.modified
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return SessionStatus.ACTIVE
        if hours < 24:
            return SessionStatus.RECENT
        if hours < 24 * 7:
            return SessionStatus.IDLE
        return SessionStatus.ARCHIVED

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "clone_id": self.clone_id,
            "group_id": self.group_id,
            "display_name": self.display_name,
            "custom_title": self.custom_title,
            "first_prompt": self.first_prompt[:100] if self.first_prompt else "",
            "message_count": self.message_count,
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat(),
            "git_branch": self.git_branch,
            "is_sidechain": self.is_sidechain,
            "is_pinned": self.is_pinned,
            "has_unread": self.has_unread,
            "status": self.status.value,
        }


@dataclass
class ProjectClone:
    clone_id: str
    clone_name: str
    project_path: str
    sessions: list[SessionEntry] = field(default_factory=list)
    trash_sessions: list[SessionEntry] = field(default_factory=list)

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    @property
    def latest_modified(self) -> datetime | None:
        if not self.sessions:
            return None
        return max(s.modified for s in self.sessions)

    @property
    def current_branch(self) -> str | None:
        if not self.sessions:
            return None
        latest = max(self.sessions, key=lambda s: s.modified)
        return latest.git_branch

    def to_dict(self) -> dict:
        return {
            "clone_id": self.clone_id,
            "clone_name": self.clone_name,
            "project_path": self.project_path,
            "session_count": self.session_count,
            "latest_modified": self.latest_modified.isoformat() if self.latest_modified else None,
            "current_branch": self.current_branch,
            "sessions": [s.to_dict() for s in sorted(
                self.sessions, key=lambda s: s.modified, reverse=True
            )],
            "trash_sessions": [s.to_dict() for s in sorted(
                self.trash_sessions, key=lambda s: s.modified, reverse=True
            )],
        }


@dataclass
class ProjectGroup:
    group_id: str
    display_name: str
    initials: str
    clones: list[ProjectClone] = field(default_factory=list)

    @property
    def total_sessions(self) -> int:
        return sum(c.session_count for c in self.clones)

    @property
    def active_sessions(self) -> int:
        return sum(
            1 for c in self.clones for s in c.sessions
            if s.status == SessionStatus.ACTIVE
        )

    @property
    def latest_modified(self) -> datetime | None:
        dates = [c.latest_modified for c in self.clones if c.latest_modified]
        return max(dates) if dates else None

    @property
    def total_messages(self) -> int:
        return sum(s.message_count for c in self.clones for s in c.sessions)

    def to_dict(self, include_sessions: bool = False) -> dict:
        result = {
            "group_id": self.group_id,
            "display_name": self.display_name,
            "initials": self.initials,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "latest_modified": self.latest_modified.isoformat() if self.latest_modified else None,
            "total_messages": self.total_messages,
            "clone_count": len(self.clones),
        }
        if include_sessions:
            result["clones"] = [c.to_dict() for c in self.clones]
        return result
