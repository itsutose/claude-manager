"""ピン、未読状態等のユーザーデータ永続化."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from claude_manager.config import Config

logger = logging.getLogger(__name__)


class UserDataStore:
    def __init__(self, config: Config) -> None:
        self.config = config
        config.ensure_manager_dir()

    def _read_json(self, path) -> dict:
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError, FileNotFoundError):
            return {}

    def _write_json(self, path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # --- ピン管理 ---

    def get_pinned_sessions(self) -> set[str]:
        data = self._read_json(self.config.pins_file)
        return set(data.get("pinned", []))

    def toggle_pin(self, session_id: str) -> bool:
        """ピン留めをトグルし、新しいピン状態を返す."""
        data = self._read_json(self.config.pins_file)
        pinned = set(data.get("pinned", []))
        if session_id in pinned:
            pinned.discard(session_id)
            is_pinned = False
        else:
            pinned.add(session_id)
            is_pinned = True
        data["pinned"] = list(pinned)
        self._write_json(self.config.pins_file, data)
        return is_pinned

    # --- 未読管理 ---

    def mark_read(self, session_id: str) -> None:
        data = self._read_json(self.config.read_state_file)
        data[session_id] = datetime.now(timezone.utc).isoformat()
        self._write_json(self.config.read_state_file, data)

    def get_read_states(self) -> dict[str, str]:
        return self._read_json(self.config.read_state_file)
