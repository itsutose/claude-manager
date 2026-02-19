"""group_detector の仕様.

## detect_groups_from_config（新・手動グルーピング）

group_config.json でグループを手動定義する。

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

## detect_groups（旧・自動グルーピング）

親ディレクトリベースの自動グルーピング。参考用に残す。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pytest

from claude_manager.config import Config
from claude_manager.services.group_detector import (
    _compute_group_name,
    _generate_initials,
    detect_groups,
    detect_groups_from_config,
)
from tests.conftest import make_user_record, write_jsonl
from tests.factories import make_session

logger = logging.getLogger(__name__)


# ============================================================
# ヘルパー
# ============================================================

def setup_clone(config: Config, clone_id: str, project_path: str) -> str:
    """テスト用クローンを作成し、session_id を返す.

    - projects_dir にクローンディレクトリを作成
    - sessions-index.json にプロジェクトパスを記録
    - ダミーの JSONL を配置
    """
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

class TestComputeGroupName:
    """クローンパス群からグループ名を算出する."""

    def test_single_path(self):
        assert _compute_group_name(["/Users/test/my-project"]) == "my-project"

    def test_strips_number_suffix(self):
        """app-1, app-2 → 共通ベース「app」."""
        paths = ["/home/user/app-1", "/home/user/app-2"]
        assert _compute_group_name(paths) == "app"

    def test_different_names_returns_most_common(self):
        paths = ["/home/user/frontend", "/home/user/backend"]
        result = _compute_group_name(paths)
        assert result in ("frontend", "backend")


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
# detect_groups のシナリオテスト
# ============================================================

class TestSiblingClones:
    """兄弟クローンのグルーピング.

    Desktop/
      hyogo-medical/               ← 親ディレクトリ（クローンではない）
        hyogo-medical/             ← クローン（セッションあり）
        hyogo-medical-1/           ← クローン（セッションあり）
        hyogo-medical-2/           ← クローン（セッションあり）

    → 1グループ「hyogo-medical」、3クローン
    """

    def test_three_siblings_form_one_group(self, config):
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical", "/Users/yamaguchi/Desktop/hyogo-medical/hyogo-medical")
        s2 = setup_clone(config, "-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical-1", "/Users/yamaguchi/Desktop/hyogo-medical/hyogo-medical-1")
        s3 = setup_clone(config, "-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical-2", "/Users/yamaguchi/Desktop/hyogo-medical/hyogo-medical-2")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical-1", modified=now),
            make_session(session_id=s3, clone_id="-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical-2", modified=now),
        ]

        groups = detect_groups(sessions, config)
        dump_groups(groups, "兄弟クローン: hyogo-medical")

        hm_groups = [g for g in groups if "hyogo" in g.group_id]
        assert len(hm_groups) == 1, f"hyogo関連が1グループになるべき: {[g.group_id for g in hm_groups]}"
        assert len(hm_groups[0].clones) == 3

    def test_clone_names_are_directory_names(self, config):
        """各クローンの名前はディレクトリ末尾の名前になる."""
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical", "/Users/yamaguchi/Desktop/hyogo-medical/hyogo-medical")
        s2 = setup_clone(config, "-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical-1", "/Users/yamaguchi/Desktop/hyogo-medical/hyogo-medical-1")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-Desktop-hyogo-medical-hyogo-medical-1", modified=now),
        ]

        groups = detect_groups(sessions, config)
        hm = [g for g in groups if "hyogo" in g.group_id][0]
        clone_names = {c.clone_name for c in hm.clones}

        assert "hyogo-medical" in clone_names
        assert "hyogo-medical-1" in clone_names


class TestParentChildClones:
    """親子クローンのグルーピング.

    Desktop/
      sony-sonpo-infra-project/           ← クローン（セッションあり）かつ親
        sony-sonpo-infra-1/               ← クローン（セッションあり）子

    → 1グループ、2クローンとして表示されるべき
    → 現状バグ: 2つの別グループに分裂する
    """

    @pytest.mark.xfail(reason="バグ: 親子クローンが別グループに分裂する")
    def test_parent_and_child_form_one_group(self, config):
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project")
        s2 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project/sony-sonpo-infra-1")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", modified=now),
        ]

        groups = detect_groups(sessions, config)
        dump_groups(groups, "親子クローン: sony-sonpo")

        sony_groups = [g for g in groups if "sony" in g.group_id or "infra" in g.group_id]
        assert len(sony_groups) == 1, f"sony関連が1グループになるべき: {[g.group_id for g in sony_groups]}"
        assert len(sony_groups[0].clones) == 2

    def test_current_behavior_splits_into_two_groups(self, config):
        """現状の動作: 親は standalone、子は parent_groups に入り、別グループになる."""
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project")
        s2 = setup_clone(config, "-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", "/Users/yamaguchi/Desktop/sony-sonpo-infra-project/sony-sonpo-infra-1")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-Desktop-sony-sonpo-infra-project-sony-sonpo-infra-1", modified=now),
        ]

        groups = detect_groups(sessions, config)
        dump_groups(groups, "現状の動作確認: sony-sonpo")

        sony_groups = [g for g in groups if "sony" in g.group_id or "infra" in g.group_id]
        # 現状は2グループに分裂する（これが問題）
        assert len(sony_groups) == 2, "現状は2グループに分裂する"


class TestStandalone:
    """Desktop直下の単独プロジェクト.

    Desktop/
      obsidian-knowledge/          ← クローン

    → 個別グループ「obsidian-knowledge」、1クローン
    """

    def test_desktop_direct_child_is_standalone_group(self, config):
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-obsidian-knowledge", "/Users/yamaguchi/Desktop/obsidian-knowledge")

        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-obsidian-knowledge", modified=now),
        ]

        groups = detect_groups(sessions, config)
        dump_groups(groups, "standalone: obsidian-knowledge")

        assert len(groups) == 1
        assert groups[0].group_id == "obsidian-knowledge"
        assert len(groups[0].clones) == 1


class TestHomeDirectoryProject:
    """ホームディレクトリ直下のプロジェクトとサブディレクトリ.

    ~/
      dotfiles/                    ← クローン
      dotfiles/nvim/               ← クローン
      dotfiles/zsh/                ← クローン

    → dotfiles は ~ 直下なので standalone
    → dotfiles/nvim, dotfiles/zsh は親が dotfiles（汎用ではない）
    → 現状: dotfiles が standalone、nvim/zsh が別グループになる可能性
    """

    def test_check_current_grouping(self, config):
        """dotfiles パターンの現状の動作を確認."""
        now = datetime.now(timezone.utc)
        s1 = setup_clone(config, "-Users-yamaguchi-dotfiles", "/Users/yamaguchi/dotfiles")
        s2 = setup_clone(config, "-Users-yamaguchi-dotfiles-nvim", "/Users/yamaguchi/dotfiles/nvim")
        s3 = setup_clone(config, "-Users-yamaguchi-dotfiles-zsh", "/Users/yamaguchi/dotfiles/zsh")

        sessions = [
            make_session(session_id=s1, clone_id="-Users-yamaguchi-dotfiles", modified=now),
            make_session(session_id=s2, clone_id="-Users-yamaguchi-dotfiles-nvim", modified=now),
            make_session(session_id=s3, clone_id="-Users-yamaguchi-dotfiles-zsh", modified=now),
        ]

        groups = detect_groups_from_config(sessions, config)
        dump_groups(groups, "ホームディレクトリ直下: dotfiles")

        df_groups = [g for g in groups if "dotfiles" in g.group_id or "nvim" in g.group_id or "zsh" in g.group_id]
        logger.info("dotfiles関連グループ数: %d", len(df_groups))
        for g in df_groups:
            logger.info("  %s: clones=%s", g.group_id, [c.clone_name for c in g.clones])


class TestHiddenSessions:
    """非表示セッションはグルーピングから除外される."""

    def test_hidden_session_excluded(self, config):
        now = datetime.now(timezone.utc)
        sid = setup_clone(config, "-Users-yamaguchi-Desktop-proj", "/Users/yamaguchi/Desktop/proj")

        sessions = [
            make_session(session_id=sid, clone_id="-Users-yamaguchi-Desktop-proj", modified=now),
        ]
        config.hidden_file.write_text(json.dumps({"hidden": [sid]}))

        groups = detect_groups(sessions, config)
        dump_groups(groups, "非表示セッション")

        total = sum(g.total_sessions for g in groups)
        assert total == 0


class TestSortOrder:
    """グループは latest_modified の降順でソートされる."""

    def test_newest_first(self, config):
        import os
        home = os.path.expanduser("~")

        old = datetime(2024, 1, 1, tzinfo=timezone.utc)
        new = datetime(2024, 6, 1, tzinfo=timezone.utc)

        sid1 = setup_clone(config, "-old-proj", f"{home}/Desktop/old-proj")
        sid2 = setup_clone(config, "-new-proj", f"{home}/Desktop/new-proj")

        sessions = [
            make_session(session_id=sid1, clone_id="-old-proj", modified=old),
            make_session(session_id=sid2, clone_id="-new-proj", modified=new),
        ]

        groups = detect_groups(sessions, config)
        dump_groups(groups, "ソート順")

        assert len(groups) == 2
        assert groups[0].latest_modified > groups[1].latest_modified


# ============================================================
# detect_groups_from_config のシナリオテスト（新）
# ============================================================

def write_group_config(config: Config, groups_def: dict) -> None:
    """group_config.json を書き込む."""
    config.group_config_file.write_text(
        json.dumps({"groups": groups_def}, ensure_ascii=False, indent=2)
    )


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
