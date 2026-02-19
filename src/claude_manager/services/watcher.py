"""ファイル変更監視 + SSEブロードキャスター."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.config import Config

logger = logging.getLogger(__name__)


class FileWatcher:
    """プロジェクトファイルと設定ファイルの変更を定期ポーリングで監視."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._mtimes: dict[str, float] = {}
        self._subscribers: list[asyncio.Queue] = []
        self._running = False
        self._reload_callback: callable | None = None

    def set_reload_callback(self, callback: callable) -> None:
        """データ再読み込み用コールバックを設定."""
        self._reload_callback = callback

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.remove(queue)

    async def _broadcast(self, event: dict) -> None:
        for queue in self._subscribers:
            await queue.put(event)

    def _scan_mtimes(self) -> dict[str, float]:
        """監視対象ファイルのmtimeを取得."""
        mtimes: dict[str, float] = {}

        # 1. プロジェクトディレクトリ内のJSONLファイル
        projects_dir = self.config.projects_dir
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                for jsonl_file in project_dir.glob("*.jsonl"):
                    try:
                        mtimes[str(jsonl_file)] = jsonl_file.stat().st_mtime
                    except OSError:
                        pass

        # 2. 設定ファイル
        config_files = [
            self.config.group_config_file,
            self.config.titles_file,
            self.config.hidden_file,
            self.config.pins_file,
        ]
        for cf in config_files:
            if cf.exists():
                try:
                    mtimes[str(cf)] = cf.stat().st_mtime
                except OSError:
                    pass

        return mtimes

    async def start(self) -> None:
        """ポーリング開始."""
        self._running = True
        self._mtimes = self._scan_mtimes()
        logger.info("FileWatcher started (interval=%ds)", self.config.poll_interval_sec)

        while self._running:
            await asyncio.sleep(self.config.poll_interval_sec)
            new_mtimes = self._scan_mtimes()

            changed = False
            for path, mtime in new_mtimes.items():
                old_mtime = self._mtimes.get(path)
                if old_mtime is None or mtime > old_mtime:
                    logger.debug("File changed: %s", path)
                    changed = True

            # 削除されたファイルも検知
            if set(self._mtimes.keys()) != set(new_mtimes.keys()):
                changed = True

            if changed:
                # バックエンドのキャッシュを更新
                if self._reload_callback:
                    try:
                        self._reload_callback()
                    except Exception:
                        logger.exception("Reload callback failed")

                await self._broadcast({
                    "type": "index_refreshed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            self._mtimes = new_mtimes

    def stop(self) -> None:
        self._running = False
