"""プロジェクトグループ API."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("")
async def list_groups(request: Request):
    """全プロジェクトグループの一覧."""
    app_state = request.app.state
    groups = app_state.groups
    return {
        "groups": [g.to_dict(include_sessions=False) for g in groups],
    }


@router.get("/{group_id}")
async def get_group(group_id: str, request: Request):
    """プロジェクトグループの詳細（クローン+セッション含む）."""
    groups = request.app.state.groups
    for g in groups:
        if g.group_id == group_id:
            return g.to_dict(include_sessions=True)
    return {"error": "Group not found"}, 404
