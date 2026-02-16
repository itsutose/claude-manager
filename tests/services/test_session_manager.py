"""SessionManager の仕様.

SessionManager はセッションのタイトルを管理する。

## タイトル生成
- first_prompt から20文字以内の短いタイトルを自動生成する
- XML, URL, ファイルパス等のノイズを除去する
- 句読点で区切り、最初の意味のある部分を抽出する

## タイトル保存（デュアルストレージ）
- titles.json に保存（マネージャの正、読み込み最優先）
- JSONL 末尾に custom-title レコードを追記（CLI resume picker 互換）
- JSONL への追記は best-effort（失敗しても titles.json があればOK）

## 自動命名
- first_prompt からルールベースでタイトルを生成し、デュアルストレージに保存する
"""
from __future__ import annotations

import json

import pytest

from claude_manager.config import Config
from claude_manager.services.session_manager import SessionManager
from tests.conftest import make_assistant_record, make_user_record, write_jsonl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mgr_without_config():
    """Config 不要のテスト用（タイトル生成のみ）."""
    return SessionManager(config=None)  # type: ignore[arg-type]


@pytest.fixture
def mgr_with_config(tmp_path):
    """ファイルI/Oを伴うテスト用."""
    config = Config(
        claude_dir=tmp_path / ".claude",
        manager_dir=tmp_path / ".claude-manager",
    )
    config.ensure_manager_dir()
    (config.claude_dir / "projects").mkdir(parents=True, exist_ok=True)
    return SessionManager(config), config


# ===========================================================================
# タイトル生成
# ===========================================================================

class DescribeTitleGeneration:
    """first_prompt から20文字以内の短いタイトルを生成する."""

    class DescribeBasicBehavior:
        def test_short_text_is_returned_as_is(self, mgr_without_config):
            assert mgr_without_config._generate_title("fizzbuzzを書いて") == "fizzbuzzを書いて"

        def test_empty_string_returns_nameless(self, mgr_without_config):
            assert mgr_without_config._generate_title("") == "(名前なし)"

        def test_none_returns_nameless(self, mgr_without_config):
            assert mgr_without_config._generate_title(None) == "(名前なし)"  # type: ignore[arg-type]

    class DescribeNoiseRemoval:
        """タイトルに不要なノイズを除去する."""

        def test_removes_xml_tag_blocks(self, mgr_without_config):
            title = mgr_without_config._generate_title("<context>長い文脈</context>本題はこれ")
            assert "<" not in title
            assert "本題" in title

        def test_keeps_text_part_of_markdown_links(self, mgr_without_config):
            title = mgr_without_config._generate_title("[リンクテキスト](https://example.com)を修正")
            assert "リンクテキスト" in title
            assert "https" not in title

        def test_removes_http_urls(self, mgr_without_config):
            title = mgr_without_config._generate_title("https://example.com/foo/bar を開いて")
            assert "https" not in title
            assert "開いて" in title

        def test_removes_file_urls(self, mgr_without_config):
            title = mgr_without_config._generate_title("file:///Users/test/foo.txt を確認")
            assert "file:///" not in title

        def test_removes_unix_file_paths(self, mgr_without_config):
            title = mgr_without_config._generate_title("/Users/test/my-project/src/main.py を修正")
            assert "/Users" not in title
            assert "修正" in title

        def test_removes_at_signs(self, mgr_without_config):
            title = mgr_without_config._generate_title("@user に聞いて")
            assert "@" not in title

    class DescribeLengthConstraints:
        """生成されるタイトルは20文字以内."""

        def test_truncates_long_text_to_20_chars(self, mgr_without_config):
            title = mgr_without_config._generate_title("あ" * 30)
            assert len(title) <= 20

        def test_cuts_at_sentence_boundary(self, mgr_without_config):
            title = mgr_without_config._generate_title("修正して。あとテスト")
            assert title == "修正して"

        def test_normalizes_newlines_to_spaces(self, mgr_without_config):
            title = mgr_without_config._generate_title("修正して\nあとテスト")
            assert title == "修正して あとテスト"

    class DescribeEdgeCases:
        def test_noise_only_input_returns_nameless(self, mgr_without_config):
            assert mgr_without_config._generate_title("< >") == "(名前なし)"

        def test_xml_only_input_returns_nameless(self, mgr_without_config):
            assert mgr_without_config._generate_title("<tag>content</tag>") == "(名前なし)"


# ===========================================================================
# セッション名変更（デュアルストレージ）
# ===========================================================================

class DescribeRenameSession:
    """デュアルストレージでセッションタイトルを保存する."""

    class DescribeTitlesJson:
        """titles.json はマネージャの正."""

        def test_saves_session_title(self, mgr_with_config):
            mgr, config = mgr_with_config

            result = mgr.rename_session("sess-001", "My Title")

            assert result is True
            titles = json.loads(config.titles_file.read_text())
            assert titles["sess-001"] == "My Title"

        def test_overwrites_on_same_session_id(self, mgr_with_config):
            mgr, config = mgr_with_config

            mgr.rename_session("sess-001", "First Title")
            mgr.rename_session("sess-001", "Second Title")

            titles = json.loads(config.titles_file.read_text())
            assert titles["sess-001"] == "Second Title"

        def test_manages_multiple_sessions(self, mgr_with_config):
            mgr, config = mgr_with_config

            mgr.rename_session("sess-001", "Title A")
            mgr.rename_session("sess-002", "Title B")

            titles = json.loads(config.titles_file.read_text())
            assert titles["sess-001"] == "Title A"
            assert titles["sess-002"] == "Title B"

    class DescribeJsonlAppend:
        """JSONL 末尾に custom-title レコードを追記する（CLI resume picker 互換）."""

        def test_appends_custom_title_record(self, mgr_with_config):
            mgr, config = mgr_with_config
            project_dir = config.projects_dir / "-Users-test-proj"
            project_dir.mkdir()
            jsonl = project_dir / "sess-001.jsonl"
            write_jsonl(jsonl, [
                make_user_record("test"),
                make_assistant_record("ok"),
            ])

            mgr.rename_session("sess-001", "My Title")

            lines = jsonl.read_text().strip().split("\n")
            last_record = json.loads(lines[-1])
            assert last_record["type"] == "custom-title"
            assert last_record["customTitle"] == "My Title"
            assert last_record["sessionId"] == "sess-001"

        def test_succeeds_even_without_jsonl_file(self, mgr_with_config):
            """JSONL ファイルがなくても titles.json への保存は成功する."""
            mgr, config = mgr_with_config

            result = mgr.rename_session("nonexistent", "Title")

            assert result is True
            titles = json.loads(config.titles_file.read_text())
            assert titles["nonexistent"] == "Title"


# ===========================================================================
# 自動命名
# ===========================================================================

class DescribeAutoRename:
    """first_prompt からタイトルを生成してデュアルストレージに保存する."""

    def test_generates_title_and_saves(self, mgr_with_config):
        mgr, config = mgr_with_config

        title = mgr.auto_rename_session("sess-001", "fizzbuzzを書いて")

        assert title == "fizzbuzzを書いて"
        titles = json.loads(config.titles_file.read_text())
        assert titles["sess-001"] == "fizzbuzzを書いて"

    def test_generates_nameless_for_empty_prompt(self, mgr_with_config):
        mgr, _ = mgr_with_config

        title = mgr.auto_rename_session("sess-001", "")

        assert title == "(名前なし)"
