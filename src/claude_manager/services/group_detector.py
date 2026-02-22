"""group_config.json によるプロジェクトグルーピング.

group_config.json の形式:
  {
    "groups": {
      "<group_key>": {
        "display_name": "(省略可)",
        "paths": ["/path/to/project", "/path/to/project/sub"]
      }
    }
  }

ルール:
  - config に定義されたパスのみ表示（未定義クローンは除外）
  - paths の中で最も浅いパスが親クローン、深いものが子クローン
  - display_name 省略時はグループキー名を使う
  - config ファイルが存在しない場合は空リストを返す
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from claude_manager.config import Config
from claude_manager.models import ProjectClone, ProjectGroup, SessionEntry

logger = logging.getLogger(__name__)


def _resolve_project_path(clone_id: str, config: Config) -> str:
    """clone_id (encoded dir name) から実際のprojectPathを解決する."""
    # 1. sessions-index.jsonから取得
    index_file = config.projects_dir / clone_id / "sessions-index.json"
    if index_file.exists():
        try:
            data = json.loads(index_file.read_text())
            entries = data.get("entries", [])
            if entries and entries[0].get("projectPath"):
                return entries[0]["projectPath"]
        except (json.JSONDecodeError, OSError):
            pass

    # 2. jsonlファイルから取得
    project_dir = config.projects_dir / clone_id
    for jsonl_file in project_dir.glob("*.jsonl"):
        try:
            with open(jsonl_file) as f:
                for line in f:
                    record = json.loads(line.strip())
                    cwd = record.get("cwd")
                    if cwd:
                        return cwd
        except (json.JSONDecodeError, OSError):
            continue
        break  # 最初のjsonlだけ試す

    # 3. history.jsonlから検索
    history_file = config.history_file
    if history_file.exists():
        try:
            with open(history_file) as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        project = record.get("project", "")
                        if project:
                            encoded = project.replace("/", "-")
                            if encoded == clone_id or clone_id.endswith(encoded):
                                return project
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    # 4. フォールバック: clone_idをパスにデコード（不完全）
    parts = clone_id.split("-")
    if parts and parts[0] == "":
        parts = parts[1:]

    home = os.path.expanduser("~")
    home_parts = Path(home).parts

    if len(parts) >= len(home_parts) - 1:
        return home + "/" + "/".join(parts[len(home_parts) - 1:])

    return "/" + "/".join(parts)


def _generate_initials(name: str) -> str:
    """プロジェクト名からイニシャル(2文字)を生成."""
    # 前方のドットを除去
    clean = name.lstrip(".")
    parts = re.split(r"[-_\s]+", clean)
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if len(clean) >= 2:
        return clean[:2].upper()
    return clean.upper()


def _load_hidden_sessions(config: Config) -> set[str]:
    """hidden.json から非表示セッションIDを読み込む."""
    hidden_file = config.hidden_file
    if not hidden_file.exists():
        return set()
    try:
        data = json.loads(hidden_file.read_text())
        return set(data.get("hidden", []))
    except (json.JSONDecodeError, OSError):
        return set()


def detect_groups_from_config(
    sessions: list[SessionEntry],
    config: Config,
) -> list[ProjectGroup]:
    """group_config.json に基づいてプロジェクトグループを構築する."""
    # config ファイルの読み込み
    if not config.group_config_file.exists():
        return []

    try:
        gc = json.loads(config.group_config_file.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    groups_def = gc.get("groups", {})
    if not groups_def:
        return []

    # 非表示セッションIDを読み込み（フィルタせずtrash_sessionsとして保持）
    hidden_ids = _load_hidden_sessions(config)

    # clone_id → project_path のマッピングを構築
    clone_ids_set: set[str] = set()
    for s in sessions:
        clone_ids_set.add(s.clone_id)

    clone_paths: dict[str, str] = {}
    for clone_id in clone_ids_set:
        path = _resolve_project_path(clone_id, config)
        clone_paths[clone_id] = path

    # project_path → clone_id の逆引きマップ
    path_to_clone: dict[str, str] = {}
    for clone_id, path in clone_paths.items():
        path_to_clone[path] = clone_id

    # ピン・未読情報
    pinned_sessions: set[str] = set()
    if config.pins_file.exists():
        try:
            pins_data = json.loads(config.pins_file.read_text())
            pinned_sessions = set(pins_data.get("pinned", []))
        except (json.JSONDecodeError, OSError):
            pass

    read_states: dict[str, str] = {}
    if config.read_state_file.exists():
        try:
            read_states = json.loads(config.read_state_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # グループ構築
    groups: list[ProjectGroup] = []
    used_initials: set[str] = set()

    for group_key, group_def in groups_def.items():
        display_name = group_def.get("display_name", group_key)
        paths = group_def.get("paths", [])

        # パスを浅い順にソート（浅い＝親）
        paths_sorted = sorted(paths, key=lambda p: p.count("/"))

        # パスに対応するクローンを収集（セッションがあるもののみ）
        clones: list[ProjectClone] = []
        for path in paths_sorted:
            clone_id = path_to_clone.get(path)
            if clone_id is None:
                continue

            clone_sessions = [s for s in sessions if s.clone_id == clone_id]
            if not clone_sessions:
                continue

            for s in clone_sessions:
                s.group_id = group_key
                s.is_pinned = s.session_id in pinned_sessions
                last_read = read_states.get(s.session_id)
                s.has_unread = bool(last_read and s.modified.isoformat() > last_read)

            # 通常セッションとtrashセッションを振り分け
            visible_sessions = [s for s in clone_sessions if s.session_id not in hidden_ids]
            trash_sessions = [s for s in clone_sessions if s.session_id in hidden_ids]

            # セッションもtrashも無い場合はスキップ
            if not visible_sessions and not trash_sessions:
                continue

            clone_name = Path(path).name
            clones.append(ProjectClone(
                clone_id=clone_id,
                clone_name=clone_name,
                project_path=path,
                sessions=visible_sessions,
                trash_sessions=trash_sessions,
            ))

        if not clones:
            continue

        initials = _generate_initials(group_key)
        base_initials = initials
        suffix = 2
        while initials in used_initials:
            initials = "%s%d" % (base_initials[0], suffix)
            suffix += 1
        used_initials.add(initials)

        groups.append(ProjectGroup(
            group_id=group_key,
            display_name=display_name,
            initials=initials,
            clones=clones,
        ))

    # ソート: latest_modified降順
    groups.sort(
        key=lambda g: g.latest_modified.isoformat() if g.latest_modified else "1970-01-01",
        reverse=True,
    )

    return groups
