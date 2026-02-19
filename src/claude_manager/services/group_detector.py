"""プロジェクトグループの自動検出.

同一プロジェクトの複数クローンを自動グルーピングする。

グルーピング戦略:
1. sessions-index.json または jsonlファイルのメタデータからプロジェクトパスを取得
2. サブディレクトリの吸収: パスAがパスBの子孫で、パスBも登録済み → Aの
   セッションをBのクローンに統合
3. 親ディレクトリでグルーピング（汎用ディレクトリは除外、個別グループ化）
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from claude_manager.config import Config
from claude_manager.models import ProjectClone, ProjectGroup, SessionEntry

logger = logging.getLogger(__name__)

# グルーピングに使わない汎用ディレクトリ
_EXCLUDED_PARENTS = set()


def _init_excluded_parents():
    global _EXCLUDED_PARENTS
    home = os.path.expanduser("~")
    _EXCLUDED_PARENTS = {
        home,
        os.path.join(home, "Desktop"),
        os.path.join(home, ".config"),
        "/Users",
        "/",
    }


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
                        session_id = record.get("sessionId", "")
                        project = record.get("project", "")
                        if project:
                            # clone_idのエンコード形式と照合
                            encoded = project.replace("/", "-")
                            if encoded == clone_id or clone_id.endswith(encoded):
                                return project
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    # 4. フォールバック: clone_idをパスにデコード
    # -Users-yamaguchi-Desktop-xxx → 実際のパスを推測
    # これは不完全だが最後の手段
    parts = clone_id.split("-")
    # 先頭の空文字を除去（-Usersの場合）
    if parts and parts[0] == "":
        parts = parts[1:]

    # 既知のパス構造から推測
    home = os.path.expanduser("~")
    home_parts = Path(home).parts  # ('/', 'Users', 'yamaguchi')

    # パスの最初がhomeのpartsと一致するか確認
    if len(parts) >= len(home_parts) - 1:  # -1 because '/' is not in encoded
        return home + "/" + "/".join(parts[len(home_parts) - 1:])

    return "/" + "/".join(parts)


def _compute_group_name(paths: list[str]) -> str:
    """クローンパス群からグループ名を算出."""
    names = [Path(p).name for p in paths]
    if len(names) == 1:
        return names[0]

    # 数字サフィックスを除去して共通ベースを見つける
    base_names = []
    for name in names:
        base = re.sub(r"[-_]\d+$", "", name)
        base_names.append(base)

    counter = Counter(base_names)
    most_common = counter.most_common(1)[0][0]
    return most_common


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


def detect_groups(
    sessions: list[SessionEntry],
    config: Config,
) -> list[ProjectGroup]:
    """セッション一覧からプロジェクトグループを自動検出する."""
    _init_excluded_parents()

    # 非表示セッションをフィルタリング
    hidden_ids = _load_hidden_sessions(config)
    if hidden_ids:
        sessions = [s for s in sessions if s.session_id not in hidden_ids]

    # Step 1: clone_id → project_path のマッピングを構築
    clone_paths: dict[str, str] = {}
    clone_ids_set: set[str] = set()
    for s in sessions:
        clone_ids_set.add(s.clone_id)

    for clone_id in clone_ids_set:
        path = _resolve_project_path(clone_id, config)
        clone_paths[clone_id] = path

    # # Step 2: サブディレクトリの吸収
    # # パスAがパスBの直接の子ディレクトリ（深さ1-2）で、パスBが汎用ディレクトリでなければ
    # # AのセッションをBのクローンに統合する
    # # 例: dotfiles/nvim → dotfiles に吸収
    # # 例: hyogo-medical-1/backend → hyogo-medical-1 に吸収
    # # 反例: ~/Desktop/xxx → ~ には吸収しない
    # absorbed: dict[str, str] = {}  # clone_id → 吸収先のclone_id

    # for cid_child, path_child in clone_paths.items():
    #     best_parent = None
    #     best_parent_len = 0
    #     for cid_parent, path_parent in clone_paths.items():
    #         if cid_child == cid_parent:
    #             continue
    #         # 汎用ディレクトリには吸収しない
    #         if path_parent in _EXCLUDED_PARENTS:
    #             continue
    #         if path_child.startswith(path_parent + "/"):
    #             # 最も近い（最も長い）親パスを選ぶ
    #             if len(path_parent) > best_parent_len:
    #                 # 深さが2以内かチェック
    #                 relative = path_child[len(path_parent):].strip("/")
    #                 depth = len(relative.split("/"))
    #                 if depth <= 2:
    #                     best_parent = cid_parent
    #                     best_parent_len = len(path_parent)
    #     if best_parent:
    #         absorbed[cid_child] = best_parent

    # # 吸収されたclone_idのセッションを親に統合
    # # （サイドバーでは親クローンの下に表示する）
    # # ただし、吸収先のclone_nameにサブパス名を含める
    # for child_cid, parent_cid in absorbed.items():
    #     child_path = clone_paths[child_cid]
    #     parent_path = clone_paths[parent_cid]
    #     relative = child_path[len(parent_path):].strip("/")
    #     # セッションのclone_idを親に変更
    #     for s in sessions:
    #         if s.clone_id == child_cid:
    #             s.clone_id = parent_cid

    # # 吸収されたclone_idを除去
    # for cid in absorbed:
    #     if cid in clone_paths:
    #         del clone_paths[cid]

    # Step 3: 親ディレクトリでグルーピング
    manual_mappings: dict[str, str] = {}
    custom_groups: dict[str, dict] = {}
    if config.group_config_file.exists():
        try:
            gc = json.loads(config.group_config_file.read_text())
            manual_mappings = gc.get("manual_mappings", {})
            custom_groups = gc.get("custom_groups", {})
        except (json.JSONDecodeError, OSError):
            pass

    manual_assigned: dict[str, list[str]] = defaultdict(list)
    parent_groups: dict[str, list[str]] = defaultdict(list)
    standalone: list[str] = []

    for clone_id, path in clone_paths.items():
        mapped_group = manual_mappings.get(path)
        if mapped_group:
            manual_assigned[mapped_group].append(clone_id)
            continue

        parent = str(Path(path).parent)
        if parent in _EXCLUDED_PARENTS:
            standalone.append(clone_id)
        else:
            parent_groups[parent].append(clone_id)

    # Step 4: ピン・未読情報
    pinned_sessions = set()
    if config.pins_file.exists():
        try:
            pins_data = json.loads(config.pins_file.read_text())
            pinned_sessions = set(pins_data.get("pinned", []))
        except (json.JSONDecodeError, OSError):
            pass

    read_states = {}
    if config.read_state_file.exists():
        try:
            read_states = json.loads(config.read_state_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Step 5: グループ構築
    groups: list[ProjectGroup] = []
    used_initials: set[str] = set()

    def _build_group(group_name: str, clone_ids: list[str]) -> ProjectGroup:
        custom = custom_groups.get(group_name, {})
        display_name = custom.get("display_name", group_name)
        initials = custom.get("initials", _generate_initials(group_name))

        base_initials = initials
        suffix = 2
        while initials in used_initials:
            initials = "%s%d" % (base_initials[0], suffix)
            suffix += 1
        used_initials.add(initials)

        seen_ids = set()
        unique_ids = []
        for cid in clone_ids:
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique_ids.append(cid)

        clones = []
        for clone_id in sorted(unique_ids, key=lambda cid: clone_paths.get(cid, "")):
            clone_sessions = [s for s in sessions if s.clone_id == clone_id]

            for s in clone_sessions:
                s.group_id = group_name
                s.is_pinned = s.session_id in pinned_sessions
                last_read = read_states.get(s.session_id)
                s.has_unread = bool(last_read and s.modified.isoformat() > last_read)

            clone_name = Path(clone_paths.get(clone_id, clone_id)).name
            clones.append(ProjectClone(
                clone_id=clone_id,
                clone_name=clone_name,
                project_path=clone_paths.get(clone_id, ""),
                sessions=clone_sessions,
            ))

        return ProjectGroup(
            group_id=group_name,
            display_name=display_name,
            initials=initials,
            clones=clones,
        )

    # (a) 手動マッピング
    for group_key, clone_ids in manual_assigned.items():
        groups.append(_build_group(group_key, clone_ids))

    # (b) 親ディレクトリグループ
    for parent, clone_ids in parent_groups.items():
        project_paths = [clone_paths[cid] for cid in clone_ids]
        group_name = _compute_group_name(project_paths)
        groups.append(_build_group(group_name, clone_ids))

    # (c) 個別グループ
    for clone_id in standalone:
        path = clone_paths[clone_id]
        group_name = Path(path).name
        groups.append(_build_group(group_name, [clone_id]))

    # ソート: latest_modified降順
    groups.sort(
        key=lambda g: g.latest_modified.isoformat() if g.latest_modified else "1970-01-01",
        reverse=True,
    )

    return groups


def detect_groups_from_config(
    sessions: list[SessionEntry],
    config: Config,
) -> list[ProjectGroup]:
    """group_config.json に基づいてプロジェクトグループを構築する.

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

    # 非表示セッションをフィルタリング
    hidden_ids = _load_hidden_sessions(config)
    if hidden_ids:
        sessions = [s for s in sessions if s.session_id not in hidden_ids]

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

            clone_name = Path(path).name
            clones.append(ProjectClone(
                clone_id=clone_id,
                clone_name=clone_name,
                project_path=path,
                sessions=clone_sessions,
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
