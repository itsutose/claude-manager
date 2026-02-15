"""プロジェクトグループ API."""
from __future__ import annotations

from fastapi import APIRouter, Request

from claude_manager.services.asset_reader import read_project_assets

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("")
async def list_groups(request: Request):
    """全プロジェクトグループの一覧."""
    app_state = request.app.state
    groups = app_state.groups
    return {
        "groups": [g.to_dict(include_sessions=False) for g in groups],
    }


@router.get("/{group_id}/assets")
async def get_group_assets(group_id: str, request: Request):
    """プロジェクトグループの設定ファイル（CLAUDE.md, rules, skills）を返す."""
    groups = request.app.state.groups
    target_group = None
    for g in groups:
        if g.group_id == group_id:
            target_group = g
            break

    if not target_group:
        return {"error": "Group not found"}

    if not target_group.clones:
        return {"error": "No clones found in group"}

    project_path = target_group.clones[0].project_path
    if not project_path:
        return {"error": "Project path not found"}

    config = request.app.state.config
    return read_project_assets(project_path, config)


@router.get("/{group_id}")
async def get_group(group_id: str, request: Request):
    """プロジェクトグループの詳細（クローン+セッション含む）."""
    groups = request.app.state.groups
    for g in groups:
        if g.group_id == group_id:
            return g.to_dict(include_sessions=True)
    return {"error": "Group not found"}, 404
