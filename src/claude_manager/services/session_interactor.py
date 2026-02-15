"""セッションへのメッセージ送信（claude -p --resume）."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # 5分


def _find_claude_binary() -> str | None:
    return shutil.which("claude")


async def send_message(
    session_id: str,
    message: str,
    project_path: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """claude -p --resume でメッセージを送り、結果を返す."""
    claude_bin = _find_claude_binary()
    if not claude_bin:
        return {"success": False, "error": "claude binary not found"}

    cmd = [
        claude_bin,
        "-p", message,
        "--resume", session_id,
        "--dangerously-skip-permissions",
        "--output-format", "json",
    ]

    logger.info("Sending message to session %s in %s", session_id, project_path)

    # ネスト検出を回避するため CLAUDECODE 環境変数を除去
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"success": False, "error": f"Timeout after {timeout}s"}
    except OSError as e:
        return {"success": False, "error": str(e)}

    if proc.returncode != 0:
        err = stderr.decode(errors="replace").strip()
        logger.error("claude exited %d: %s", proc.returncode, err)
        return {"success": False, "error": err or f"Exit code {proc.returncode}"}

    raw = stdout.decode(errors="replace").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON from claude", "raw": raw[:500]}

    return {
        "success": True,
        "result": data.get("result", ""),
        "session_id": data.get("session_id", session_id),
        "cost_usd": data.get("total_cost_usd"),
        "usage": data.get("usage"),
    }
