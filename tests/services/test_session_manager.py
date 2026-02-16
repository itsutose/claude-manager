"""SessionManager の仕様.

SessionManager はセッションのタイトルを管理する。

## タイトル保存（デュアルストレージ）
- titles.json に保存（マネージャの正、読み込み最優先）
- JSONL 末尾に custom-title レコードを追記（CLI resume picker 互換）
- JSONL への追記は best-effort（失敗しても titles.json があればOK）

## タイトル生成
- Haiku による自動命名（session_interactor.py 経由）
- ルールベース生成は廃止済み
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
