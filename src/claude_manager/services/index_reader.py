"""セッションデータ読み取りサービス.

JSONLファイルのみを正とする。タイトルは titles.json > JSONL custom-title > first_prompt の優先順で決定。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.config import Config
from claude_manager.models import SessionEntry

logger = logging.getLogger(__name__)

# JSONL先頭の読み取り上限
_HEADER_BYTES = 32 * 1024  # 先頭32KB


def _parse_datetime(value: str | int | float | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _load_titles(config: Config) -> dict[str, str]:
    """titles.json から session_id → title のマップを読む."""
    try:
        if config.titles_file.exists():
            return json.loads(config.titles_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read titles.json: %s", e)
    return {}


def _from_jsonl_file(jsonl_path: Path, project_dir: Path) -> SessionEntry | None:
    """JSONLファイルからメタデータを読み取る.

    先頭32KBで first_prompt / git_branch を取得し、
    全レコードスキャンで custom-title とメッセージ数を収集する。
    """
    session_id = jsonl_path.stem
    first_prompt = ""
    git_branch = None
    custom_title = None
    message_count = 0

    try:
        stat = jsonl_path.stat()
        file_size = stat.st_size
    except OSError:
        return None

    if file_size == 0:
        return None

    try:
        with open(jsonl_path) as f:
            header_read = 0
            header_done = False
            for line in f:
                line = line.strip()
                if not line:
                    continue
                header_read += len(line)

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                record_type = record.get("type")

                # custom-title レコードは位置に関係なく最後のものを採用
                if record_type == "custom-title":
                    ct = record.get("customTitle")
                    if ct:
                        custom_title = ct
                    continue

                if record_type in ("user", "assistant"):
                    message_count += 1

                    if not header_done:
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

                if header_read > _HEADER_BYTES:
                    header_done = True
                    if file_size > 1_000_000:
                        avg_line = header_read / max(message_count, 1)
                        message_count = int(file_size / avg_line * (message_count / max(header_read / avg_line, 1)))
                        break

    except OSError:
        return None

    if message_count == 0:
        return None

    birthtime = getattr(stat, "st_birthtime", None) or stat.st_ctime
    created = datetime.fromtimestamp(birthtime, tz=timezone.utc)
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    return SessionEntry(
        session_id=session_id,
        clone_id=project_dir.name,
        group_id="",
        custom_title=custom_title,
        first_prompt=first_prompt,
        message_count=message_count,
        created=created,
        modified=modified,
        git_branch=git_branch,
        is_sidechain=False,
        full_path=str(jsonl_path),
    )


def read_all_sessions(config: Config) -> list[SessionEntry]:
    """全プロジェクトのセッションを読み取る.

    JSONLファイルのみを正とする。タイトルは titles.json を最優先で適用する。
    """
    sessions: list[SessionEntry] = []
    projects_dir = config.projects_dir

    if not projects_dir.exists():
        logger.warning("projects dir not found: %s", projects_dir)
        return sessions

    # titles.json を先に読み込み
    titles = _load_titles(config)

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        for f in project_dir.iterdir():
            if f.suffix == ".jsonl" and f.is_file():
                session = _from_jsonl_file(f, project_dir)
                if session:
                    # titles.json のタイトルを最優先で適用
                    if session.session_id in titles:
                        session.custom_title = titles[session.session_id]
                    sessions.append(session)

    return sessions
