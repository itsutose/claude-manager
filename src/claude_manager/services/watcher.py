"""ファイル変更監視 + SSEブロードキャスター."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.config import Config

logger = logging.getLogger(__name__)


class FileWatcher:
    """sessions-index.jsonの変更を定期ポーリングで監視."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._mtimes: dict[str, float] = {}
        self._subscribers: list[asyncio.Queue] = []
        self._running = False

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
        """全sessions-index.jsonのmtimeを取得."""
        mtimes: dict[str, float] = {}
        projects_dir = self.config.projects_dir
        if not projects_dir.exists():
            return mtimes

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            index_file = project_dir / "sessions-index.json"
            if index_file.exists():
                try:
                    mtimes[str(index_file)] = index_file.stat().st_mtime
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

            for path, mtime in new_mtimes.items():
                old_mtime = self._mtimes.get(path)
                if old_mtime is None or mtime > old_mtime:
                    logger.debug("Index changed: %s", path)
                    await self._broadcast({
                        "type": "index_refreshed",
                        "path": path,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            self._mtimes = new_mtimes

    def stop(self) -> None:
        self._running = False
