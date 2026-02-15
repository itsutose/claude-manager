"""sessions-index.json の customTitle 読み書きサービス."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from claude_manager.config import Config

logger = logging.getLogger(__name__)

# タイトル生成時に除去するパターン
_TAG_BLOCK_RE = re.compile(r"<(\w+)[^>]*>.*?</\1>", re.DOTALL)  # <tag>...</tag> ブロック
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]+\)")  # [text](url) → text
_FILE_URL_RE = re.compile(r"file:///\S+")
_URL_RE = re.compile(r"https?://\S+")
_FILE_PATH_RE = re.compile(r"(?:/[\w./-]+){2,}")  # /foo/bar/baz 形式のパス
_LINE_REF_RE = re.compile(r"#L\d+[:\-]\d+")  # #L123:456 形式の行参照
_FILE_EXT_RE = re.compile(r"\.\w{1,5}\b")  # .md, .json 等の拡張子


class SessionManager:
    """sessions-index.json の customTitle を管理する."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def _find_index_file(self, session_id: str) -> Path | None:
        """session_id が含まれる sessions-index.json を見つける."""
        projects_dir = self.config.projects_dir
        if not projects_dir.exists():
            return None

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            index_file = project_dir / "sessions-index.json"
            if not index_file.exists():
                continue
            try:
                data = json.loads(index_file.read_text())
                entries = data.get("entries", [])
                for entry in entries:
                    if entry.get("sessionId") == session_id:
                        return index_file
            except (json.JSONDecodeError, OSError):
                continue
        return None

    def rename_session(self, session_id: str, title: str) -> bool:
        """sessions-index.json の customTitle を書き換える.

        Returns:
            成功したら True
        """
        index_file = self._find_index_file(session_id)
        if not index_file:
            logger.warning("sessions-index.json not found for session %s", session_id)
            return False

        try:
            data = json.loads(index_file.read_text())
            entries = data.get("entries", [])
            found = False
            for entry in entries:
                if entry.get("sessionId") == session_id:
                    entry["customTitle"] = title
                    found = True
                    break
            if not found:
                return False
            index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to write sessions-index.json: %s", e)
            return False

    def auto_rename_session(self, session_id: str) -> str | None:
        """firstPrompt からルールベースでタイトルを自動生成し、customTitle に設定する.

        Returns:
            生成されたタイトル。失敗時は None。
        """
        index_file = self._find_index_file(session_id)
        if not index_file:
            logger.warning("sessions-index.json not found for session %s", session_id)
            return None

        try:
            data = json.loads(index_file.read_text())
            entries = data.get("entries", [])
            target_entry = None
            for entry in entries:
                if entry.get("sessionId") == session_id:
                    target_entry = entry
                    break
            if not target_entry:
                return None

            first_prompt = target_entry.get("firstPrompt", "")
            title = self._generate_title(first_prompt)

            target_entry["customTitle"] = title
            index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            return title
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to auto-rename session: %s", e)
            return None

    def _generate_title(self, first_prompt: str) -> str:
        """firstPrompt からルールベースで短いタイトル（20文字以内）を生成する."""
        if not first_prompt:
            return "(名前なし)"

        # Markdownリンク [text](url) → テキスト部分を残す
        text = _MD_LINK_RE.sub(r"\1", first_prompt)
        # XMLタグブロックを除去（<tag>...</tag> 全体）
        text = _TAG_BLOCK_RE.sub(" ", text)
        # 残った単独タグを除去
        text = _TAG_RE.sub(" ", text)
        # URL・ファイルパスを除去
        text = _FILE_URL_RE.sub("", text)
        text = _URL_RE.sub("", text)
        text = _FILE_PATH_RE.sub("", text)
        # 行参照・拡張子を除去
        text = _LINE_REF_RE.sub("", text)
        text = _FILE_EXT_RE.sub("", text)
        # 残ったノイズ文字を除去
        text = text.replace("@", "").replace("[", "").replace("]", "")
        # 連続する空白を1つにまとめる
        text = _WHITESPACE_RE.sub(" ", text).strip()

        if not text or len(text) < 2:
            return "(名前なし)"

        # 先頭30文字を取得し、20文字以内に整形
        snippet = text[:30]

        # 句読点・改行で区切って最初の意味のある部分を取得
        for sep in ["\n", "。", ".", "、", ",", "！", "!", "？", "?"]:
            idx = snippet.find(sep)
            if 0 < idx <= 20:
                snippet = snippet[:idx]
                break

        # 20文字以内にトリム
        if len(snippet) > 20:
            snippet = snippet[:18] + ".."

        return snippet.strip() or "(名前なし)"
