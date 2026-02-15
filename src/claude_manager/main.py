"""Claude Session Manager - FastAPI application."""
from __future__ import annotations

import asyncio
import logging
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from claude_manager.config import Config
from claude_manager.services.index_reader import read_all_sessions
from claude_manager.services.group_detector import detect_groups
from claude_manager.services.user_data import UserDataStore
from claude_manager.services.watcher import FileWatcher
from claude_manager.routers import groups, sessions, search, events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def build_groups(config: Config):
    """セッションを読み取り、グループ化して返す."""
    all_sessions = read_all_sessions(config)
    return detect_groups(all_sessions, config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリのライフサイクル管理."""
    config = app.state.config

    # 初回データ読み込み
    logger.info("Loading session data from %s", config.claude_dir)
    app.state.groups = build_groups(config)
    logger.info(
        "Loaded %d groups, %d total sessions",
        len(app.state.groups),
        sum(g.total_sessions for g in app.state.groups),
    )

    # ファイル監視開始
    watcher = FileWatcher(config)
    app.state.watcher = watcher
    watcher_task = asyncio.create_task(watcher.start())

    yield

    # シャットダウン
    watcher.stop()
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass


def create_app(config: Config | None = None) -> FastAPI:
    if config is None:
        config = Config.load()

    app = FastAPI(
        title="Claude Session Manager",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.config = config
    app.state.user_data = UserDataStore(config)
    app.state.groups = []

    # ルーターの登録
    app.include_router(groups.router)
    app.include_router(sessions.router)
    app.include_router(search.router)
    app.include_router(events.router)

    # データ再読み込みAPI
    @app.post("/api/reload")
    async def reload_data():
        app.state.groups = build_groups(config)
        return {"status": "ok", "groups": len(app.state.groups)}

    # 非表示セッション一覧API
    @app.get("/api/hidden")
    async def list_hidden():
        return {"hidden": app.state.user_data.list_hidden_sessions()}

    # 静的ファイル配信（Viteビルド出力の /assets/ を配信）
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA: 全ルートをindex.htmlに
    @app.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    return app


def cli():
    """CLIエントリポイント."""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Session Manager")
    sub = parser.add_subparsers(dest="command")

    serve_parser = sub.add_parser("serve", help="Start the web server")
    serve_parser.add_argument("--port", type=int, default=8420)
    serve_parser.add_argument("--no-browser", action="store_true")
    serve_parser.add_argument("--host", default="127.0.0.1")

    args = parser.parse_args()

    if args.command == "serve" or args.command is None:
        import uvicorn

        port = getattr(args, "port", 8420)
        host = getattr(args, "host", "127.0.0.1")
        no_browser = getattr(args, "no_browser", False)

        config = Config.load()
        config.port = port
        app = create_app(config)

        if not no_browser:
            # サーバー起動後にブラウザを開く
            import threading
            def open_browser():
                import time
                time.sleep(1.5)
                webbrowser.open(f"http://{host}:{port}")
            threading.Thread(target=open_browser, daemon=True).start()

        logger.info("Starting Claude Session Manager on http://%s:%d", host, port)
        uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli()
