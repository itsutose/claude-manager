"""asset_reader.py のテスト."""
from __future__ import annotations

from pathlib import Path

from claude_manager.services.asset_reader import (
    _read_dir_files,
    _read_file_content,
    read_project_assets,
)


class TestReadFileContent:
    def test_reads_existing_file(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("# Hello")
        assert _read_file_content(f) == "# Hello"

    def test_nonexistent_returns_none(self, tmp_path: Path):
        assert _read_file_content(tmp_path / "missing.md") is None

    def test_directory_returns_none(self, tmp_path: Path):
        d = tmp_path / "subdir"
        d.mkdir()
        assert _read_file_content(d) is None


class TestReadDirFiles:
    def test_reads_directory(self, tmp_path: Path):
        (tmp_path / "a.md").write_text("AAA")
        (tmp_path / "b.md").write_text("BBB")
        result = _read_dir_files(tmp_path)
        assert len(result) == 2
        names = [r["name"] for r in result]
        assert "a.md" in names
        assert "b.md" in names

    def test_skips_dotfiles(self, tmp_path: Path):
        (tmp_path / ".hidden").write_text("secret")
        (tmp_path / "visible.md").write_text("ok")
        result = _read_dir_files(tmp_path)
        assert len(result) == 1
        assert result[0]["name"] == "visible.md"

    def test_nonexistent_dir(self, tmp_path: Path):
        assert _read_dir_files(tmp_path / "missing") == []

    def test_empty_dir(self, tmp_path: Path):
        d = tmp_path / "empty"
        d.mkdir()
        assert _read_dir_files(d) == []


class TestReadProjectAssets:
    def test_reads_all_assets(self, tmp_config):
        project = tmp_config.claude_dir.parent / "my-project"
        project.mkdir()
        (project / "CLAUDE.md").write_text("# Project Rules")
        (project / ".claude").mkdir()
        (project / ".claude" / "rules").mkdir()
        (project / ".claude" / "rules" / "rule1.md").write_text("rule one")

        result = read_project_assets(str(project), tmp_config)
        assert result["claude_md"] == "# Project Rules"
        assert len(result["local_rules"]) == 1
        assert result["local_rules"][0]["name"] == "rule1.md"

    def test_missing_project_returns_nones(self, tmp_config):
        result = read_project_assets("/nonexistent/path", tmp_config)
        assert result["claude_md"] is None
        assert result["local_rules"] == []
        assert result["local_skills"] == []
