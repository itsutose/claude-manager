"""group_detector の仕様.

detect_groups_from_config（手動グルーピング）のテスト。

  ~/.claude-manager/group_config.json:
  {
    "groups": {
      "sony-sonpo": {
        "display_name": "sony-sonpo-infra",
        "paths": [
          "/Users/.../sony-sonpo-infra-project",
          "/Users/.../sony-sonpo-infra-project/sony-sonpo-infra-1"
        ]
      }
    }
  }

ルール:
  - paths の中で最も浅いパスが「親クローン」、深いものが「子クローン」
  - 子クローンはサイドバーで折りたたみ表示される
  - config に定義されていないクローンは表示しない
  - display_name は省略可（省略時はグループキー名を使う）
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pytest

from claude_manager.config import Config
from claude_manager.services.group_detector import (
    _generate_initials,
    detect_groups_from_config,
)
from tests.conftest import make_user_record, write_jsonl
from tests.factories import make_session

logger = logging.getLogger(__name__)


# ============================================================
# ヘルパー
# ============================================================

def setup_clone(config: Config, clone_id: str, project_path: str) -> str:
    """テスト用クローンを作成し、session_id を返す."""
    project_dir = config.projects_dir / clone_id
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


def dump_groups(groups, label: str = "") -> None:
    """グルーピング結果をログ出力する."""
    header = f"=== {label} ===" if label else "=== グルーピング結果 ==="
    logger.info(header)
    logger.info("グループ数: %d", len(groups))
    for g in groups:
        logger.info(
            "  [%s] %s (%dクローン, %dセッション)",
            g.initials, g.group_id, len(g.clones), g.total_sessions,
        )
        for c in g.clones:
            logger.info(
                "    clone: %s → %s (%dセッション)",
                c.clone_name, c.project_path, len(c.sessions),
            )
            for s in c.sessions:
                logger.info("      session: %s", s.session_id)


def write_group_config(config: Config, groups_def: dict) -> None:
    """group_config.json を書き込む."""
    config.group_config_file.write_text(
        json.dumps({"groups": groups_def}, ensure_ascii=False, indent=2)
    )


@pytest.fixture
def config(tmp_path):
    config = Config(
        claude_dir=tmp_path / ".claude",
        manager_dir=tmp_path / ".claude-manager",
    )
    config.ensure_manager_dir()
    (config.claude_dir / "projects").mkdir(parents=True)
    return config


# ============================================================
# ユーティリティ関数のテスト
# ============================================================

class TestGenerateInitials:
    """プロジェクト名からイニシャル2文字を生成する."""

    def test_hyphen(self):
        assert _generate_initials("my-project") == "MP"

    def test_underscore(self):
        assert _generate_initials("hello_world") == "HW"

    def test_single_word(self):
        assert _generate_initials("frontend") == "FR"

    def test_dot_prefix(self):
        assert _generate_initials(".config") == "CO"

    def test_single_char(self):
        assert _generate_initials("x") == "X"


# ============================================================
# detect_groups_from_config のシナリオテスト
# ============================================================

class TestConfigBasicGrouping:
    """group_config.json による基本的なグルーピング.

    group_config.json:
      {
        "groups": {
          "my-project": {
            "paths": ["/Users/yamaguchi/Desktop/my-project"]
          }
        }
      }

    ~/.claude/projects/
      -Users-yamaguchi-Desktop-my-project/
        sess-001.jsonl

    → 1グループ「my-project」、1クローン、1セッション
    """

    def test_single_group_single_clone(self, config):
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-my-project", "/Users/yamaguchi/Desktop/my-project")
        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-my-project", modified=now),
        ]

        write_group_config(config, {
            "my-project": {
                "paths": ["/Users/yamaguchi/Desktop/my-project"],
            },
        })

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "基本: 単一グループ")

        assert len(groups) == 1
        assert groups[0].group_id == "my-project"
        assert len(groups[0].clones) == 1
        assert groups[0].total_sessions == 1

    def test_display_name_used_when_provided(self, config):
        """display_name が指定されていればそれを使う."""
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-my-project", "/Users/yamaguchi/Desktop/my-project")
        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-my-project", modified=now),
        ]

        write_group_config(config, {
            "my-project": {
                "display_name": "マイプロジェクト",
                "paths": ["/Users/yamaguchi/Desktop/my-project"],
            },
        })

        groups = detect_groups_from_config(sessions, config)

        assert groups[0].display_name == "マイプロジェクト"

    def test_display_name_defaults_to_group_key(self, config):
        """display_name が省略されたらグループキー名を使う."""
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-my-project", "/Users/yamaguchi/Desktop/my-project")
        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-my-project", modified=now),
        ]

        write_group_config(config, {
            "my-project": {
                "paths": ["/Users/yamaguchi/Desktop/my-project"],
            },
        })

        groups = detect_groups_from_config(sessions, config)

        assert groups[0].display_name == "my-project"


class TestConfigExcludesUndefined:
    """config に定義されていないクローンは表示しない.

    group_config.json:
      "my-project" だけ定義

    ~/.claude/projects/
      -Users-yamaguchi-Desktop-my-project/     ← 定義あり
      -Users-yamaguchi-Desktop-other-project/  ← 定義なし

    → other-project は表示されない
    """

    def test_undefined_clone_excluded(self, config):
        now = datetime.now(timezone.utc)
        sid1 = setup_clone(config, "-Users-yamaguchi-Desktop-my-project", "/Users/yamaguchi/Desktop/my-project")
        sid2 = setup_clone(config, "-Users-yamaguchi-Desktop-other-project", "/Users/yamaguchi/Desktop/other-project")
        sessions = [
            make_session(session_id=sid1, clone_id="-Users-yamaguchi-Desktop-my-project", modified=now),
            make_session(session_id=sid2, clone_id="-Users-yamaguchi-Desktop-other-project", modified=now),
        ]

        write_group_config(config, {
            "my-project": {
                "paths": ["/Users/yamaguchi/Desktop/my-project"],
            },
        })

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "未定義クローンの除外")

        assert len(groups) == 1
        assert groups[0].group_id == "my-project"


class TestConfigParentChild:
    """親子クローンのグルーピング（sony-sonpo パターン）.

    group_config.json:
      {
        "groups": {
          "sony-sonpo": {
            "paths": [
              "/Users/.../sony-sonpo-infra-project",
              "/Users/.../sony-sonpo-infra-project/sony-sonpo-infra-1"
            ]
          }
        }
      }

    → 1グループ「sony-sonpo」
    → paths の最も浅いパスが親クローン
    → 深いパスが子クローン（折りたたみ表示用）
    """

    def test_parent_and_child_in_one_group(self, config):
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project")
        s2 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project/sony-sonpo-infra-1")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", modified=now),
        ]

        write_group_config(config, {
            "sony-sonpo": {
                "paths": [
                    "/Users/yamaguchi/Desktop/sony-sonpo-infra-project",
                    "/Users/yamaguchi/Desktop/sony-sonpo-infra-project/sony-sonpo-infra-1",
                ],
            },
        })

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "親子クローン: sony-sonpo (config)")

        assert len(groups) == 1
        assert groups[0].group_id == "sony-sonpo"
        assert len(groups[0].clones) == 2

    def test_shallowest_path_is_first_clone(self, config):
        """最も浅いパスのクローンがクローン一覧の先頭に来る."""
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project")
        s2 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project/sony-sonpo-infra-1")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", modified=now),
        ]

        write_group_config(config, {
            "sony-sonpo": {
                "paths": [
                    "/Users/yamaguchi/Desktop/sony-sonpo-infra-project/sony-sonpo-infra-1",
                    "/Users/yamaguchi/Desktop/sony-sonpo-infra-project",
                ],
            },
        })

        groups = detect_groups_from_config(sessions, config)

        # paths の記述順に関係なく、浅い方が先
        assert groups[0].clones[0].project_path == "/Users/yamaguchi/Desktop/sony-sonpo-infra-project"
        assert groups[0].clones[1].project_path == "/Users/yamaguchi/Desktop/sony-sonpo-infra-project/sony-sonpo-infra-1"


class TestConfigDotfiles:
    """dotfiles パターン（親 + 複数子）.

    group_config.json:
      {
        "groups": {
          "dotfiles": {
            "paths": [
              "/Users/yamaguchi/dotfiles",
              "/Users/yamaguchi/dotfiles/nvim",
              "/Users/yamaguchi/dotfiles/zsh"
            ]
          }
        }
      }

    → 1グループ「dotfiles」、3クローン
    → dotfiles が親、nvim/zsh が子
    """

    def test_parent_and_multiple_children(self, config):
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-dotfiles", "/Users/yamaguchi/dotfiles")
        s2 = setup_clone(config, "-Users-yamaguchi-dotfiles-nvim", "/Users/yamaguchi/dotfiles/nvim")
        s3 = setup_clone(config, "-Users-yamaguchi-dotfiles-zsh", "/Users/yamaguchi/dotfiles/zsh")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-dotfiles", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-dotfiles-nvim", modified=now),
            make_session(session_id=s3, clone_id="-Users-yamaguchi-dotfiles-zsh", modified=now),
        ]

        write_group_config(config, {
            "dotfiles": {
                "paths": [
                    "/Users/yamaguchi/dotfiles",
                    "/Users/yamaguchi/dotfiles/nvim",
                    "/Users/yamaguchi/dotfiles/zsh",
                ],
            },
        })

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "dotfiles (config)")

        assert len(groups) == 1
        assert groups[0].group_id == "dotfiles"
        assert len(groups[0].clones) == 3
        assert groups[0].clones[0].clone_name == "dotfiles"


class TestConfigMultipleGroups:
    """複数グループの定義.

    group_config.json に2つのグループ:
      sony-sonpo: 2パス
      dotfiles:   1パス

    → 2グループ、latest_modified 降順でソート
    """

    def test_two_groups(self, config):
        old = datetime(2024, 1, 1, tzinfo=timezone.utc)
        new = datetime(2024, 6, 1, tzinfo=timezone.utc)

        s1 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo", "/Users/yamaguchi/Desktop/sony-sonpo")
        s2 = setup_clone(config, "-Users-yamaguchi-dotfiles", "/Users/yamaguchi/dotfiles")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-Desktop-sony-sonpo", modified=old),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-dotfiles", modified=new),
        ]

        write_group_config(config, {
            "sony-sonpo": {
                "paths": ["/Users/yamaguchi/Desktop/sony-sonpo"],
            },
            "dotfiles": {
                "paths": ["/Users/yamaguchi/dotfiles"],
            },
        })

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "複数グループ")

        assert len(groups) == 2
        # 最新が先
        assert groups[0].group_id == "dotfiles"
        assert groups[1].group_id == "sony-sonpo"


class TestConfigHiddenSessions:
    """非表示セッションは config グルーピングでも除外される."""

    def test_hidden_excluded(self, config):
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-proj", "/Users/yamaguchi/Desktop/proj")

        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-proj", modified=now),
        ]
        config.hidden_file.write_text(json.dumps({"hidden": [sid]}))

        write_group_config(config, {
            "proj": {
                "paths": ["/Users/yamaguchi/Desktop/proj"],
            },
        })

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "非表示セッション (config)")

        total = sum(g.total_sessions for g in groups)
        assert total == 0


class TestConfigNoFile:
    """group_config.json が存在しない場合は空を返す."""

    def test_returns_empty(self, config):
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-proj", "/Users/yamaguchi/Desktop/proj")
        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-proj", modified=now),
        ]

        # group_config.json を書かない
        groups = detect_groups_from_config(sessions, config)

        assert len(groups) == 0


class TestConfigPathWithNoSessions:
    """config に定義されたパスにセッションがない場合.

    group_config.json にパスを定義したが、そのパスにセッションが存在しない。
    → そのクローンはスキップされる（エラーにならない）
    """

    def test_missing_sessions_skipped(self, config):
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-proj", "/Users/yamaguchi/Desktop/proj")
        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-proj", modified=now),
        ]

        write_group_config(config, {
            "my-group": {
                "paths": [
                    "/Users/yamaguchi/Desktop/proj",
                    "/Users/yamaguchi/Desktop/proj/sub",  # セッションなし
                ],
            },
        })

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "セッションなしパス")

        assert len(groups) == 1
        # セッションがあるクローンだけ表示
        assert len(groups[0].clones) == 1
