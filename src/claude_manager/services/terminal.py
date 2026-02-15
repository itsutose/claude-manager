"""tmux連携: セッション再開コマンドの送信."""
from __future__ import annotations

import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)


def is_tmux_available() -> bool:
    return shutil.which("tmux") is not None


def is_tmux_running() -> bool:
    if not is_tmux_available():
        return False
    result = subprocess.run(
        ["tmux", "list-sessions"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def resume_in_tmux(session_id: str, project_path: str, window_name: str = "claude") -> dict:
    """tmuxの新しいウィンドウでClaude Codeセッションを再開."""
    if not is_tmux_running():
        return {
            "success": False,
            "method": "tmux",
            "error": "tmux is not running",
            "command": build_resume_command(session_id, project_path),
        }

    cmd = f"cd {project_path} && claude --resume {session_id}"
    try:
        subprocess.run(
            ["tmux", "new-window", "-n", window_name, cmd],
            capture_output=True,
            text=True,
            check=True,
        )
        return {"success": True, "method": "tmux"}
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "method": "tmux",
            "error": str(e),
            "command": build_resume_command(session_id, project_path),
        }


def build_resume_command(session_id: str, project_path: str) -> str:
    return f"cd {project_path} && claude --resume {session_id}"
