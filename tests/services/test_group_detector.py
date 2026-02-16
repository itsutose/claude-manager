"""group_detector.py のテスト."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.services.group_detector import (
    _compute_group_name,
    _generate_initials,
    detect_groups,
)
from tests.conftest import write_jsonl, make_user_record
from tests.factories import make_session


class TestComputeGroupName:
    def test_single_path(self):
        assert _compute_group_name(["/Users/test/my-project"]) == "my-project"

    def test_multiple_same_base(self):
        paths = ["/home/user/app-1", "/home/user/app-2"]
        assert _compute_group_name(paths) == "app"

    def test_multiple_different(self):
        paths = ["/home/user/frontend", "/home/user/backend"]
        # 最も多いbase_nameを返す（この場合同数なのでCounter順）
        result = _compute_group_name(paths)
        assert result in ("frontend", "backend")


class TestGenerateInitials:
    def test_hyphenated_name(self):
        assert _generate_initials("my-project") == "MP"

    def test_underscored_name(self):
        assert _generate_initials("hello_world") == "HW"

    def test_single_word(self):
        assert _generate_initials("frontend") == "FR"

    def test_dot_prefix(self):
        assert _generate_initials(".config") == "CO"

    def test_single_char(self):
        assert _generate_initials("x") == "X"


class TestDetectGroups:
    def _setup_project(self, tmp_config, clone_id: str, project_path: str):
        """テスト用プロジェクトディレクトリとindex.jsonを作成."""
        project_dir = tmp_config.projects_dir / clone_id
        project_dir.mkdir(exist_ok=True)
        index_data = {
            "entries": [{
                "sessionId": f"s-{clone_id}",
                "firstPrompt": "test",
                "projectPath": project_path,
            }],
            "originalPath": project_path,
        }
        (project_dir / "sessions-index.json").write_text(json.dumps(index_data))
        write_jsonl(project_dir / f"s-{clone_id}.jsonl", [
            make_user_record("test"),
        ])
        return f"s-{clone_id}"

    def test_single_project(self, tmp_config):
        now = datetime.now(timezone.utc)
        sid = self._setup_project(tmp_config, "-Users-test-proj", "/Users/test/proj")
        sessions = [
            make_session(
                session_id=sid,
                clone_id="-Users-test-proj",
                modified=now,
            ),
        ]
        groups = detect_groups(sessions, tmp_config)
        assert len(groups) == 1
        assert groups[0].total_sessions == 1

    def test_hidden_sessions_excluded(self, tmp_config):
        now = datetime.now(timezone.utc)
        sid = self._setup_project(tmp_config, "-Users-test-proj", "/Users/test/proj")
        sessions = [
            make_session(session_id=sid, clone_id="-Users-test-proj", modified=now),
        ]
        # hidden.jsonに追加
        tmp_config.hidden_file.write_text(json.dumps({"hidden": [sid]}))
        groups = detect_groups(sessions, tmp_config)
        # 非表示セッションは除外される
        total = sum(g.total_sessions for g in groups)
        assert total == 0

    def test_subdirectory_absorption(self, tmp_config):
        now = datetime.now(timezone.utc)
        sid_parent = self._setup_project(
            tmp_config, "-Users-test-myapp", "/Users/test/myapp",
        )
        sid_child = self._setup_project(
            tmp_config, "-Users-test-myapp-backend", "/Users/test/myapp/backend",
        )
        sessions = [
            make_session(session_id=sid_parent, clone_id="-Users-test-myapp", modified=now),
            make_session(session_id=sid_child, clone_id="-Users-test-myapp-backend", modified=now),
        ]
        groups = detect_groups(sessions, tmp_config)
        # 子ディレクトリは親に吸収されるので1グループ
        assert len(groups) == 1
        assert groups[0].total_sessions == 2

    def test_groups_sorted_by_modified(self, tmp_config):
        old = datetime(2024, 1, 1, tzinfo=timezone.utc)
        new = datetime(2024, 6, 1, tzinfo=timezone.utc)

        # 異なる親ディレクトリにすることで別グループにする
        # Desktop直下 → standaloneになるので確実に別グループ
        import os
        home = os.path.expanduser("~")
        sid1 = self._setup_project(
            tmp_config, "-old-proj", f"{home}/Desktop/old-proj",
        )
        sid2 = self._setup_project(
            tmp_config, "-new-proj", f"{home}/Desktop/new-proj",
        )

        sessions = [
            make_session(session_id=sid1, clone_id="-old-proj", modified=old),
            make_session(session_id=sid2, clone_id="-new-proj", modified=new),
        ]
        groups = detect_groups(sessions, tmp_config)
        assert len(groups) == 2
        # 最新のmodifiedが先
        assert groups[0].latest_modified > groups[1].latest_modified
