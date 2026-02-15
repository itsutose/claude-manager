"""検索 API."""
from __future__ import annotations

from fastapi import APIRouter, Request

from claude_manager.services.search import search_sessions

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def global_search(q: str, request: Request, max_results: int = 30):
    """グローバル検索."""
    groups = request.app.state.groups
    results = search_sessions(groups, q, max_results=max_results)
    return {"query": q, "results": results, "count": len(results)}
