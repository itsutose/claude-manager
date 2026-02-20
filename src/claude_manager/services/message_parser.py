"""セッションの.jsonlファイルからメッセージを抽出するパーサー."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from claude_manager.models import SessionMessage, ToolUse

logger = logging.getLogger(__name__)

MAX_USER_MESSAGES_FOR_TITLE = 10


def extract_user_messages(jsonl_path: str, max_count: int = MAX_USER_MESSAGES_FOR_TITLE) -> list[str]:
    """JSONLからユーザーメッセージのテキストだけを軽量に抽出する."""
    path = Path(jsonl_path)
    if not path.exists():
        return []

    messages: list[str] = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if record.get("type") != "user":
                    continue
                msg = record.get("message", {})
                text = _extract_text_content(msg.get("content", ""))
                if text.strip():
                    messages.append(text.strip())
                    if len(messages) >= max_count:
                        break
    except OSError:
        pass
    return messages


def _parse_timestamp(value: str | int | float | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Unix timestamp (ms)
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _extract_text_content(content: str | list) -> str:
    """message.contentからテキスト部分を抽出."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return ""


def _extract_tool_uses(content: list) -> list[ToolUse]:
    """message.contentからツール使用情報を抽出."""
    tools: list[ToolUse] = []
    if not isinstance(content, list):
        return tools

    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "tool_use":
            continue

        tool_name = item.get("name", "unknown")
        tool_input = item.get("input", {})

        # 入力の要約を生成
        if isinstance(tool_input, dict):
            if "command" in tool_input:
                input_summary = str(tool_input["command"])[:200]
            elif "file_path" in tool_input:
                input_summary = str(tool_input["file_path"])
            elif "pattern" in tool_input:
                input_summary = str(tool_input["pattern"])
            elif "query" in tool_input:
                input_summary = str(tool_input["query"])[:200]
            else:
                input_summary = json.dumps(tool_input, ensure_ascii=False)[:200]
        else:
            input_summary = str(tool_input)[:200]

        tools.append(ToolUse(
            tool_name=tool_name,
            input_summary=input_summary,
            output_summary="",  # tool_resultから後で補完
        ))

    return tools


def parse_session_messages(
    jsonl_path: str,
    limit: int | None = None,
    offset: int = 0,
) -> list[SessionMessage]:
    """セッションの.jsonlファイルからメッセージを抽出.

    Args:
        jsonl_path: jsonlファイルのパス
        limit: 最大取得メッセージ数（Noneで全件）
        offset: スキップするメッセージ数
    """
    path = Path(jsonl_path)
    if not path.exists():
        logger.warning("Session file not found: %s", jsonl_path)
        return []

    messages: list[SessionMessage] = []
    tool_results: dict[str, str] = {}  # tool_use_id → output summary

    # まずtool_resultを収集
    try:
        with open(path) as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                if record.get("type") == "tool_result":
                    tool_use_id = record.get("tool_use_id", "")
                    content = record.get("content", "")
                    if isinstance(content, str):
                        tool_results[tool_use_id] = content[:500]
                    elif isinstance(content, list):
                        parts = []
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "text":
                                parts.append(c.get("text", ""))
                        tool_results[tool_use_id] = "\n".join(parts)[:500]
    except OSError as e:
        logger.warning("Failed to read %s: %s", path, e)
        return []

    # メッセージの抽出
    msg_index = 0
    try:
        with open(path) as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                record_type = record.get("type")
                if record_type not in ("user", "assistant"):
                    continue

                msg = record.get("message", {})
                content_raw = msg.get("content", "")
                text = _extract_text_content(content_raw)

                # thinkingブロックは除外
                if isinstance(content_raw, list):
                    has_real_content = any(
                        item.get("type") in ("text", "tool_use")
                        for item in content_raw
                        if isinstance(item, dict)
                    )
                    if not has_real_content and record_type == "assistant":
                        continue

                # ツール使用情報
                tool_uses = _extract_tool_uses(content_raw) if record_type == "assistant" else []

                # tool_resultの紐付け
                if isinstance(content_raw, list):
                    for item in content_raw:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_id = item.get("id", "")
                            if tool_id in tool_results:
                                for tu in tool_uses:
                                    if tu.tool_name == item.get("name"):
                                        tu.output_summary = tool_results[tool_id]
                                        break

                timestamp = _parse_timestamp(record.get("timestamp"))

                # テキストもツールも無い場合はスキップ
                if not text.strip() and not tool_uses:
                    continue

                # ページネーション
                if msg_index < offset:
                    msg_index += 1
                    continue

                messages.append(SessionMessage(
                    message_id=record.get("uuid", ""),
                    role="user" if record_type == "user" else "assistant",
                    content=text,
                    timestamp=timestamp,
                    tool_uses=tool_uses,
                ))

                msg_index += 1
                if limit and len(messages) >= limit:
                    break

    except OSError as e:
        logger.warning("Failed to read %s: %s", path, e)

    return messages
