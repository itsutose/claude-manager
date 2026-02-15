"""セッションデータ読み取りサービス.

JSONLファイルを正とし、sessions-index.json はメタデータキャッシュとして使う。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.config import Config
from claude_manager.models import SessionEntry

logger = logging.getLogger(__name__)

# orphanセッションのJSONL読み取り上限
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


def _load_index_entries(project_dir: Path) -> dict[str, dict]:
    """sessions-index.json を読み、session_id → entry のマップを返す."""
    index_file = project_dir / "sessions-index.json"
    if not index_file.exists():
        return {}
    try:
        data = json.loads(index_file.read_text())
        return {
            e["sessionId"]: e
            for e in data.get("entries", [])
            if e.get("sessionId")
        }
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read %s: %s", index_file, e)
        return {}


def _from_index_entry(
    entry: dict, project_dir: Path, jsonl_path: Path,
) -> SessionEntry:
    """sessions-index.json のエントリから SessionEntry を作る."""
    session_id = entry["sessionId"]
    created = _parse_datetime(entry.get("created"))
    modified = _parse_datetime(entry.get("modified"))
    if not entry.get("modified") and entry.get("fileMtime"):
        modified = _parse_datetime(entry["fileMtime"])

    return SessionEntry(
        session_id=session_id,
        clone_id=project_dir.name,
        group_id="",
        custom_title=entry.get("customTitle"),
        first_prompt=entry.get("firstPrompt", ""),
        message_count=entry.get("messageCount", 0),
        created=created,
        modified=modified,
        git_branch=entry.get("gitBranch"),
        is_sidechain=entry.get("isSidechain", False),
        full_path=str(jsonl_path),
    )


def _from_jsonl_file(jsonl_path: Path, project_dir: Path) -> SessionEntry | None:
    """JSONLファイルから直接メタデータを読み取る（orphanセッション用）.

    先頭32KBを読んで first_prompt / git_branch を取得し、
    ファイル全体を軽量スキャンしてメッセージ数を数える。
    """
    session_id = jsonl_path.stem
    first_prompt = ""
    git_branch = None
    message_count = 0

    try:
        stat = jsonl_path.stat()
        file_size = stat.st_size
    except OSError:
        return None

    if file_size == 0:
        return None

    # 先頭からメタデータ取得 + メッセージカウント
    try:
        with open(jsonl_path) as f:
            # 先頭32KBでメタデータを収集
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
                    # メタデータ収集完了後もメッセージカウントは続ける
                    # ただし大きすぎるファイルはファイルサイズから推定
                    if file_size > 1_000_000:
                        # 平均行サイズから推定
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
        custom_title=None,
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

    JSONLファイルの存在を正とし、sessions-index.json はメタデータキャッシュとして使う。
    """
    sessions: list[SessionEntry] = []
    projects_dir = config.projects_dir

    if not projects_dir.exists():
        logger.warning("projects dir not found: %s", projects_dir)
        return sessions

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # 1. JSONLファイルをスキャン（正）
        jsonl_files: dict[str, Path] = {}
        for f in project_dir.iterdir():
            if f.suffix == ".jsonl" and f.is_file():
                jsonl_files[f.stem] = f

        if not jsonl_files:
            continue

        # 2. sessions-index.json をメタデータキャッシュとして読む
        index_entries = _load_index_entries(project_dir)

        # 3. 各JSONLファイルからセッションを構築
        indexed_count = 0
        orphan_count = 0

        for session_id, jsonl_path in jsonl_files.items():
            if session_id in index_entries:
                # indexにメタデータあり → 高速パス
                session = _from_index_entry(
                    index_entries[session_id], project_dir, jsonl_path,
                )
                sessions.append(session)
                indexed_count += 1
            else:
                # orphan → JSONLから直接読み取り
                session = _from_jsonl_file(jsonl_path, project_dir)
                if session:
                    sessions.append(session)
                    orphan_count += 1

        if orphan_count > 0:
            logger.debug(
                "%s: %d indexed, %d orphan sessions",
                project_dir.name, indexed_count, orphan_count,
            )

    return sessions
