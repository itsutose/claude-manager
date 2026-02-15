"""プロジェクトアセット（CLAUDE.md, rules, skills）の読み取りサービス."""
from __future__ import annotations

import logging
from pathlib import Path

from claude_manager.config import Config

logger = logging.getLogger(__name__)


def _read_file_content(path: Path) -> str | None:
    """ファイルが存在すれば内容を返し、なければ None."""
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning("Failed to read %s: %s", path, e)
        return None


def _read_dir_files(dir_path: Path) -> list[dict]:
    """ディレクトリ内のファイル一覧と内容を返す.

    Returns:
        [{"name": "filename.md", "path": "/abs/path", "content": "..."}]
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    results = []
    try:
        for item in sorted(dir_path.iterdir()):
            if item.is_file() and not item.name.startswith("."):
                content = _read_file_content(item)
                if content is not None:
                    results.append({
                        "name": item.name,
                        "path": str(item),
                        "content": content,
                    })
    except OSError as e:
        logger.warning("Failed to read directory %s: %s", dir_path, e)

    return results


def read_project_assets(project_path: str, config: Config) -> dict:
    """プロジェクトの設定ファイル（CLAUDE.md, rules, skills）を読み取る.

    Args:
        project_path: プロジェクトのルートパス
        config: アプリ設定

    Returns:
        各アセットの内容を含む辞書
    """
    project = Path(project_path)

    # プロジェクトローカルのアセット
    claude_md = _read_file_content(project / "CLAUDE.md")
    local_rules = _read_dir_files(project / ".claude" / "rules")
    local_skills = _read_dir_files(project / ".claude" / "skills")

    # グローバルアセット
    claude_dir = config.claude_dir
    global_claude_md = _read_file_content(claude_dir / "CLAUDE.md")
    global_rules = _read_dir_files(claude_dir / "rules")

    return {
        "project_path": project_path,
        "claude_md": claude_md,
        "local_rules": local_rules,
        "local_skills": local_skills,
        "global_claude_md": global_claude_md,
        "global_rules": global_rules,
    }
