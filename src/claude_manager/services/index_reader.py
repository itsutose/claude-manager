"""sessions-index.json を読み取り、SessionEntry一覧を返すサービス."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.config import Config
from claude_manager.models import SessionEntry

logger = logging.getLogger(__name__)


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    # ISO 8601 format
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _parse_mtime(value: int | float | None) -> datetime:
    """Unix timestamp (ms) → datetime."""
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def read_all_sessions(config: Config) -> list[SessionEntry]:
    """全プロジェクトのsessions-index.jsonを読み取り、SessionEntryリストを返す."""
    sessions: list[SessionEntry] = []
    projects_dir = config.projects_dir

    if not projects_dir.exists():
        logger.warning("projects dir not found: %s", projects_dir)
        return sessions

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        index_file = project_dir / "sessions-index.json"
        if not index_file.exists():
            # sessions-index.json がないプロジェクトでもjsonlファイルから最低限の情報を取得
            sessions.extend(_read_from_jsonl_files(project_dir))
            continue

        try:
            data = json.loads(index_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read %s: %s", index_file, e)
            continue

        entries = data.get("entries", [])
        for entry in entries:
            session_id = entry.get("sessionId", "")
            if not session_id:
                continue

            project_path = entry.get("projectPath", "")
            created = _parse_datetime(entry.get("created"))
            modified = _parse_datetime(entry.get("modified"))
            # fileMtime も考慮（modifiedが無い場合のフォールバック）
            if not entry.get("modified") and entry.get("fileMtime"):
                modified = _parse_mtime(entry["fileMtime"])

            sessions.append(SessionEntry(
                session_id=session_id,
                clone_id=project_dir.name,
                group_id="",  # group_detectorで後から設定
                custom_title=entry.get("customTitle"),
                first_prompt=entry.get("firstPrompt", ""),
                message_count=entry.get("messageCount", 0),
                created=created,
                modified=modified,
                git_branch=entry.get("gitBranch"),
                is_sidechain=entry.get("isSidechain", False),
                full_path=entry.get("fullPath", str(project_dir / f"{session_id}.jsonl")),
            ))

    return sessions


def _read_from_jsonl_files(project_dir: Path) -> list[SessionEntry]:
    """sessions-index.jsonが無い場合、jsonlファイルから最低限の情報を収集."""
    sessions: list[SessionEntry] = []

    for jsonl_file in project_dir.glob("*.jsonl"):
        session_id = jsonl_file.stem
        # ファイルの最初の行からメタデータを取得
        first_prompt = ""
        message_count = 0
        git_branch = None
        first_timestamp = None
        last_timestamp = None

        try:
            with open(jsonl_file) as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    record_type = record.get("type")
                    ts_str = record.get("timestamp")

                    if record_type in ("user", "assistant"):
                        message_count += 1
                        if ts_str:
                            ts = _parse_datetime(ts_str) if isinstance(ts_str, str) else _parse_mtime(ts_str)
                            if first_timestamp is None:
                                first_timestamp = ts
                            last_timestamp = ts

                        if record_type == "user" and not first_prompt:
                            msg = record.get("message", {})
                            content = msg.get("content", "")
                            if isinstance(content, str):
                                first_prompt = content
                            elif isinstance(content, list):
                                for c in content:
                                    if c.get("type") == "text":
                                        first_prompt = c.get("text", "")
                                        break

                        if not git_branch:
                            git_branch = record.get("gitBranch")

        except OSError:
            continue

        if message_count == 0:
            continue

        stat = jsonl_file.stat()
        created = first_timestamp or datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
        modified = last_timestamp or datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        sessions.append(SessionEntry(
            session_id=session_id,
            clone_id=project_dir.name,
            group_id="",
            custom_title=None,
            first_prompt=first_prompt,
            message_count=message_count,
            created=created,
            modified=modified,
            git_branch=git_branch,
            is_sidechain=False,
            full_path=str(jsonl_file),
        ))

    return sessions
