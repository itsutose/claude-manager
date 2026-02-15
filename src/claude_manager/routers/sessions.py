"""セッション API."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from claude_manager.services.message_parser import parse_session_messages
from claude_manager.services.session_manager import SessionManager
from claude_manager.services.session_interactor import send_message, generate_title
from claude_manager.services.terminal import build_resume_command, resume_in_tmux

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _find_session(groups, session_id: str):
    for g in groups:
        for c in g.clones:
            for s in c.sessions:
                if s.session_id == session_id:
                    return s, c, g
    return None, None, None


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    """セッション詳細."""
    session, clone, group = _find_session(request.app.state.groups, session_id)
    if not session:
        return {"error": "Session not found"}

    # 既読マーク
    request.app.state.user_data.mark_read(session_id)
    session.has_unread = False

    return {
        **session.to_dict(),
        "group_name": group.display_name,
        "group_initials": group.initials,
        "clone_name": clone.clone_name,
        "project_path": clone.project_path,
    }


@router.get("/{session_id}/messages")
async def get_messages(
    session_id: str,
    request: Request,
    limit: int = 50,
    offset: int = 0,
):
    """セッションのメッセージ一覧."""
    session, _, _ = _find_session(request.app.state.groups, session_id)
    if not session:
        return {"error": "Session not found"}

    messages = parse_session_messages(session.full_path, limit=limit, offset=offset)

    return {
        "session_id": session_id,
        "messages": [
            {
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "tool_uses": [
                    {
                        "tool_name": t.tool_name,
                        "input_summary": t.input_summary,
                        "output_summary": t.output_summary,
                    }
                    for t in m.tool_uses
                ],
            }
            for m in messages
        ],
        "has_more": len(messages) == limit,
    }


@router.post("/{session_id}/resume")
async def resume_session(session_id: str, request: Request):
    """セッション再開."""
    session, clone, _ = _find_session(request.app.state.groups, session_id)
    if not session:
        return {"error": "Session not found"}

    result = resume_in_tmux(
        session_id=session_id,
        project_path=clone.project_path,
        window_name=session.display_name[:20],
    )
    if not result["success"]:
        result["command"] = build_resume_command(session_id, clone.project_path)
    return result


@router.put("/{session_id}/pin")
async def toggle_pin(session_id: str, request: Request):
    """ピン留めトグル."""
    is_pinned = request.app.state.user_data.toggle_pin(session_id)

    # メモリ上の状態も更新
    session, _, _ = _find_session(request.app.state.groups, session_id)
    if session:
        session.is_pinned = is_pinned

    return {"session_id": session_id, "is_pinned": is_pinned}


class RenameBody(BaseModel):
    title: str


@router.put("/{session_id}/title")
async def rename_session(session_id: str, body: RenameBody, request: Request):
    """セッション名の変更（メモリ上のみ。~/.claude/は書き換えない）."""
    session, _, _ = _find_session(request.app.state.groups, session_id)
    if not session:
        return {"error": "Session not found"}

    session.custom_title = body.title
    return {"session_id": session_id, "title": body.title}


@router.post("/{session_id}/rename")
async def rename_session_persistent(session_id: str, body: RenameBody, request: Request):
    """セッション名の変更."""
    session, _, _ = _find_session(request.app.state.groups, session_id)
    if not session:
        return {"error": "Session not found"}

    # sessions-index.json への書き込みを試みる（orphanの場合は失敗してもOK）
    config = request.app.state.config
    mgr = SessionManager(config)
    mgr.rename_session(session_id, body.title)

    # メモリ上の状態を更新（こちらが確実に反映される）
    session.custom_title = body.title

    return {"session_id": session_id, "title": body.title}


@router.post("/{session_id}/auto-rename")
async def auto_rename_session(session_id: str, request: Request):
    """firstPrompt から Haiku でタイトルを自動生成し、customTitle に設定する."""
    session, _, _ = _find_session(request.app.state.groups, session_id)
    if not session:
        return {"error": "Session not found"}

    # Haiku でタイトル生成
    title = await generate_title(session.first_prompt)
    if not title:
        return {"error": "タイトル生成に失敗しました"}

    # sessions-index.json への書き込みを試みる（orphanの場合は失敗してもOK）
    config = request.app.state.config
    mgr = SessionManager(config)
    mgr.rename_session(session_id, title)

    # メモリ上の状態を更新
    session.custom_title = title

    return {"session_id": session_id, "title": title}


class SendMessageBody(BaseModel):
    message: str


@router.post("/{session_id}/send")
async def send_to_session(session_id: str, body: SendMessageBody, request: Request):
    """セッションにメッセージを送信（claude -p --resume）."""
    session, clone, _ = _find_session(request.app.state.groups, session_id)
    if not session:
        return {"error": "Session not found"}

    result = await send_message(
        session_id=session_id,
        message=body.message,
        project_path=clone.project_path,
    )
    return result


@router.post("/{session_id}/hide")
async def hide_session(session_id: str, request: Request):
    """セッションを非表示にする."""
    user_data = request.app.state.user_data
    user_data.hide_session(session_id)

    # メモリ上のグループからセッションを除去
    for g in request.app.state.groups:
        for c in g.clones:
            c.sessions = [s for s in c.sessions if s.session_id != session_id]

    return {"session_id": session_id, "hidden": True}


@router.post("/{session_id}/unhide")
async def unhide_session(session_id: str, request: Request):
    """非表示セッションを復元する."""
    user_data = request.app.state.user_data
    user_data.unhide_session(session_id)
    return {"session_id": session_id, "hidden": False}


