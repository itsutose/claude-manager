"""グローバル検索エンジン."""
from __future__ import annotations

from claude_manager.models import ProjectGroup, SessionEntry


def search_sessions(
    groups: list[ProjectGroup],
    query: str,
    max_results: int = 30,
) -> list[dict]:
    """全グループのセッションからクエリに一致するものを検索.

    検索対象: display_name, first_prompt, git_branch, group_id, clone_name
    """
    if not query.strip():
        return []

    query_lower = query.lower()
    results: list[tuple[int, SessionEntry, str, str]] = []  # (score, session, group_name, clone_name)

    for group in groups:
        for clone in group.clones:
            for session in clone.sessions:
                score = _calc_score(session, query_lower, group.display_name, clone.clone_name)
                if score > 0:
                    results.append((score, session, group.display_name, clone.clone_name))

    # スコア降順、同スコアならmodified降順
    results.sort(key=lambda r: (r[0], r[1].modified.isoformat()), reverse=True)

    return [
        {
            **r[1].to_dict(),
            "group_name": r[2],
            "group_initials": _find_group_initials(groups, r[1].group_id),
            "clone_name": r[3],
            "score": r[0],
        }
        for r in results[:max_results]
    ]


def _calc_score(
    session: SessionEntry,
    query_lower: str,
    group_name: str,
    clone_name: str,
) -> int:
    """検索スコアを計算. 0=不一致."""
    score = 0

    # セッション名（最高優先度）
    display = session.display_name.lower()
    if query_lower in display:
        score += 10
        if display.startswith(query_lower):
            score += 5

    # customTitle
    if session.custom_title and query_lower in session.custom_title.lower():
        score += 8

    # first_prompt
    if session.first_prompt and query_lower in session.first_prompt.lower():
        score += 3

    # git_branch
    if session.git_branch and query_lower in session.git_branch.lower():
        score += 2

    # グループ名
    if query_lower in group_name.lower():
        score += 1

    # クローン名
    if query_lower in clone_name.lower():
        score += 1

    return score


def _find_group_initials(groups: list[ProjectGroup], group_id: str) -> str:
    for g in groups:
        if g.group_id == group_id:
            return g.initials
    return "??"
