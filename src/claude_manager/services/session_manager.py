"""セッションタイトル管理サービス.

タイトルは titles.json（マネージャ管理）と JSONL custom-title レコード（CLI互換）の
デュアルストレージで管理する。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from claude_manager.config import Config

logger = logging.getLogger(__name__)

# タイトル生成時に除去するパターン
_TAG_BLOCK_RE = re.compile(
    r"<(\w+)[^>]*>.*?</\1>", re.DOTALL
)  # <tag>...</tag> ブロック
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]+\)")  # [text](url) → text
_FILE_URL_RE = re.compile(r"file:///\S+")
_URL_RE = re.compile(r"https?://\S+")
_FILE_PATH_RE = re.compile(r"(?:/[\w./-]+){2,}")  # /foo/bar/baz 形式のパス
_LINE_REF_RE = re.compile(r"#L\d+[:\-]\d+")  # #L123:456 形式の行参照
_FILE_EXT_RE = re.compile(r"\.\w{1,5}\b")  # .md, .json 等の拡張子


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

    def auto_rename_session(self, session_id: str, first_prompt: str) -> str | None:
        """first_prompt からルールベースでタイトルを自動生成し、保存する.

        Returns:
            生成されたタイトル。失敗時は None。
        """
        title = self._generate_title(first_prompt)
        if self.rename_session(session_id, title):
            return title
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
