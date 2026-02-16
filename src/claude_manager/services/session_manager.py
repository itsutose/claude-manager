"""セッションタイトル管理サービス.

タイトルは titles.json（マネージャ管理）と JSONL custom-title レコード（CLI互換）の
デュアルストレージで管理する。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from claude_manager.config import Config

logger = logging.getLogger(__name__)


class SessionManager:
    """セッションタイトルを管理する.

    書き込み時:
      1. ~/.claude-manager/titles.json に保存（マネージャの正）
      2. JSONL 末尾に custom-title レコードを追記（CLI resume picker 互換）

    読み込み優先順位:
      1. titles.json
      2. JSONL の custom-title レコード
      3. first_prompt からの自動生成
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    def _find_jsonl_file(self, session_id: str) -> Path | None:
        """session_id に対応する JSONL ファイルを見つける."""
        projects_dir = self.config.projects_dir
        if not projects_dir.exists():
            return None

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            jsonl = project_dir / f"{session_id}.jsonl"
            if jsonl.exists():
                return jsonl
        return None

    def _save_to_titles_json(self, session_id: str, title: str) -> bool:
        """titles.json にタイトルを保存する."""
        try:
            self.config.ensure_manager_dir()
            titles: dict[str, str] = {}
            if self.config.titles_file.exists():
                titles = json.loads(self.config.titles_file.read_text())
            titles[session_id] = title
            self.config.titles_file.write_text(
                json.dumps(titles, indent=2, ensure_ascii=False),
            )
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to write titles.json: %s", e)
            return False

    def _append_to_jsonl(self, session_id: str, title: str) -> bool:
        """JSONL 末尾に custom-title レコードを追記する（CLI互換）."""
        jsonl_path = self._find_jsonl_file(session_id)
        if not jsonl_path:
            logger.warning("JSONL file not found for session %s", session_id)
            return False

        record = {
            "type": "custom-title",
            "customTitle": title,
            "sessionId": session_id,
        }
        try:
            with open(jsonl_path, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            return True
        except OSError as e:
            logger.error("Failed to append custom-title to JSONL: %s", e)
            return False

    def rename_session(self, session_id: str, title: str) -> bool:
        """セッションタイトルを設定する（デュアルストレージ）.

        Returns:
            titles.json への保存が成功したら True
        """
        saved = self._save_to_titles_json(session_id, title)
        # JSONL への追記は best-effort（失敗しても titles.json があればOK）
        self._append_to_jsonl(session_id, title)
        return saved

