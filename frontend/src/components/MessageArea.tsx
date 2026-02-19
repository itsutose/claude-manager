import { useEffect, useRef, useState } from "react";
import type { SessionEntry, SessionMessage } from "../types";
import { formatDate, formatDateFull, formatTime, renderContent } from "../helpers";
import {
  togglePin,
  resumeSession,
  sendMessage,
  renameSession,
  autoRenameSession,
  hideSession,
} from "../api";

interface Props {
  session: SessionEntry;
  messages: SessionMessage[];
  loading: boolean;
  onSessionUpdate: (session: SessionEntry) => void;
  onRefreshGroup: () => void;
  onAppendMessages: (...msgs: SessionMessage[]) => void;
}

function dateDiffersFrom(
  msg: SessionMessage,
  prev: SessionMessage | null,
): boolean {
  if (!prev || !msg.timestamp || !prev.timestamp) return false;
  return (
    new Date(msg.timestamp).toDateString() !==
    new Date(prev.timestamp).toDateString()
  );
}

/** テキストなし・ツールのみのアシスタントメッセージかどうか */
function isToolOnlyMessage(msg: SessionMessage): boolean {
  return msg.role === "assistant" && !msg.content.trim() && msg.tool_uses.length > 0;
}

interface ToolEntry { tool_name: string; input_summary: string; output_summary: string }

type DisplayItem =
  | { kind: "message"; msg: SessionMessage }
  | { kind: "tool-group"; tools: ToolEntry[] };

/** 連続するツール専用メッセージをグループ化 */
function groupMessages(messages: SessionMessage[]): DisplayItem[] {
  const items: DisplayItem[] = [];
  let pendingTools: ToolEntry[] = [];

  const flushTools = () => {
    if (pendingTools.length > 0) {
      items.push({ kind: "tool-group", tools: [...pendingTools] });
      pendingTools = [];
    }
  };

  for (const msg of messages) {
    if (isToolOnlyMessage(msg)) {
      for (const t of msg.tool_uses) {
        pendingTools.push({ tool_name: t.tool_name, input_summary: t.input_summary, output_summary: t.output_summary });
      }
    } else {
      flushTools();
      items.push({ kind: "message", msg });
    }
  }
  flushTools();
  return items;
}

export function MessageArea({
  session,
  messages,
  loading,
  onSessionUpdate,
  onRefreshGroup,
  onAppendMessages,
}: Props) {
  const areaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputValue, setInputValue] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");

  useEffect(() => {
    if (areaRef.current) {
      areaRef.current.scrollTop = areaRef.current.scrollHeight;
    }
  }, [messages]);

  // --- Actions ---

  const handleTogglePin = async () => {
    const result = await togglePin(session.session_id);
    onSessionUpdate({ ...session, is_pinned: result.is_pinned });
    onRefreshGroup();
  };

  const handleResume = async () => {
    const result = await resumeSession(session.session_id);
    if (!result.success && result.command) {
      await navigator.clipboard.writeText(result.command);
    }
  };

  const handleSend = async () => {
    const msg = inputValue.trim();
    if (!msg || sending) return;

    setSending(true);
    setSendError(null);
    setInputValue("");

    // ユーザーメッセージを即座に表示
    const userMsg: SessionMessage = {
      message_id: `temp-${Date.now()}`,
      role: "user",
      content: msg,
      timestamp: new Date().toISOString(),
      tool_uses: [],
    };
    onAppendMessages(userMsg);

    try {
      const result = await sendMessage(session.session_id, msg);
      if (result.success && result.result) {
        const assistantMsg: SessionMessage = {
          message_id: `temp-${Date.now()}-response`,
          role: "assistant",
          content: result.result,
          timestamp: new Date().toISOString(),
          tool_uses: [],
        };
        onAppendMessages(assistantMsg);
        // メッセージ数を更新
        onSessionUpdate({
          ...session,
          message_count: session.message_count + 2,
        });
      } else {
        setSendError(result.error ?? "送信に失敗しました");
      }
    } catch {
      setSendError("通信エラーが発生しました");
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStartRename = () => {
    setRenameValue(session.display_name);
    setRenaming(true);
  };

  const handleRename = async () => {
    const title = renameValue.trim();
    if (!title) return;
    await renameSession(session.session_id, title);
    onSessionUpdate({ ...session, custom_title: title, display_name: title });
    onRefreshGroup();
    setRenaming(false);
  };

  const handleAutoRename = async () => {
    const result = await autoRenameSession(session.session_id);
    if (result.title) {
      onSessionUpdate({
        ...session,
        custom_title: result.title,
        display_name: result.title,
      });
      onRefreshGroup();
    }
  };

  const handleHide = async () => {
    await hideSession(session.session_id);
    onRefreshGroup();
    // セッション選択を解除（非表示にしたので）
    onSessionUpdate(null as unknown as SessionEntry);
  };

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <div className="border-b border-slack-border/50 px-6 py-3 shrink-0">
        <div className="flex items-center justify-between">
          <div className="min-w-0 flex-1">
            {renaming ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleRename();
                    if (e.key === "Escape") setRenaming(false);
                  }}
                  autoFocus
                  className="bg-[#35373b] text-white text-[15px] font-bold px-2 py-1 rounded border border-slack-accent focus:outline-none"
                />
                <button
                  onClick={handleRename}
                  className="text-xs text-slack-accent hover:underline"
                >
                  保存
                </button>
                <button
                  onClick={() => setRenaming(false)}
                  className="text-xs text-slack-muted hover:underline"
                >
                  取消
                </button>
              </div>
            ) : (
              <h3 className="text-white font-bold text-[15px] truncate">
                # {session.display_name}
              </h3>
            )}
            <div className="flex items-center gap-3 text-xs text-slack-muted mt-0.5">
              {session.git_branch && (
                <span>
                  branch:{" "}
                  <span className="text-slack-text">{session.git_branch}</span>
                </span>
              )}
              <span>{session.message_count} msgs</span>
              <span>
                {formatDate(session.created)} - {formatDate(session.modified)}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {/* Rename */}
            <button
              onClick={handleStartRename}
              className="p-1.5 rounded text-slack-muted hover:text-white hover:bg-slack-hover transition-colors"
              title="リネーム"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
              </svg>
            </button>
            {/* Auto rename */}
            <button
              onClick={handleAutoRename}
              className="p-1.5 rounded text-slack-muted hover:text-white hover:bg-slack-hover transition-colors"
              title="自動命名"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </button>
            {/* Pin */}
            <button
              onClick={handleTogglePin}
              className={`p-1.5 rounded hover:bg-slack-hover transition-colors ${
                session.is_pinned
                  ? "text-yellow-400"
                  : "text-slack-muted hover:text-white"
              }`}
              title="ピン留め"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.789l1.599.799L9 4.323V3a1 1 0 011-1z" />
              </svg>
            </button>
            {/* Hide */}
            <button
              onClick={handleHide}
              className="p-1.5 rounded text-slack-muted hover:text-red-400 hover:bg-slack-hover transition-colors"
              title="非表示にする"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div ref={areaRef} className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center h-full text-slack-muted">
            読み込み中...
          </div>
        ) : (
          <div className="space-y-4">
            {(() => {
              const items = groupMessages(messages);
              let lastMsg: SessionMessage | null = null;
              return items.map((item, i) => {
                if (item.kind === "tool-group") {
                  // ツールグループ: ツール名をカウントして1行にまとめる
                  const counts = new Map<string, number>();
                  for (const t of item.tools) {
                    counts.set(t.tool_name, (counts.get(t.tool_name) ?? 0) + 1);
                  }
                  const summary = [...counts.entries()]
                    .map(([name, count]) => count > 1 ? `${name} ×${count}` : name)
                    .join(", ");
                  return (
                    <details key={`tg-${i}`} className="ml-11 border border-slack-border/30 rounded">
                      <summary className="px-3 py-1 text-xs text-slack-muted cursor-pointer hover:text-white">
                        🔧 {summary}
                      </summary>
                      <div className="px-3 py-2 space-y-1 bg-[#16181c] border-t border-slack-border/30">
                        {item.tools.map((tool, j) => (
                          <div key={j} className="text-xs text-slack-muted">
                            <span className="text-slack-text">{tool.tool_name}</span>
                            {tool.input_summary && <span className="ml-2">{tool.input_summary}</span>}
                          </div>
                        ))}
                      </div>
                    </details>
                  );
                }

                const msg = item.msg;
                const showDate = !lastMsg || dateDiffersFrom(msg, lastMsg);
                lastMsg = msg;
                return (
                  <div key={msg.message_id}>
                    {showDate && msg.timestamp && (
                      <div className="flex items-center gap-3 my-4">
                        <div className="flex-1 h-px bg-slack-border/50" />
                        <span className="text-xs text-slack-muted font-medium">
                          {formatDateFull(msg.timestamp)}
                        </span>
                        <div className="flex-1 h-px bg-slack-border/50" />
                      </div>
                    )}
                    <div className="flex gap-3">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 ${
                          msg.role === "user"
                            ? "bg-green-600 text-white"
                            : "bg-orange-600 text-white"
                        }`}
                      >
                        {msg.role === "user" ? "U" : "C"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-white font-bold text-sm">
                            {msg.role === "user" ? "You" : "Claude"}
                          </span>
                          {msg.timestamp && (
                            <span className="text-xs text-slack-muted">
                              {formatTime(msg.timestamp)}
                            </span>
                          )}
                        </div>
                        {msg.content && (
                          <div
                            className="message-content text-sm text-slack-text leading-relaxed"
                            dangerouslySetInnerHTML={{
                              __html: renderContent(msg.content),
                            }}
                          />
                        )}
                        {msg.tool_uses.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {msg.tool_uses.map((tool, j) => (
                              <details
                                key={j}
                                className="border border-slack-border/30 rounded"
                              >
                                <summary className="px-3 py-1.5 text-xs text-slack-muted cursor-pointer hover:text-white">
                                  🔧 {tool.tool_name}
                                </summary>
                                <div className="px-3 py-2 text-xs text-slack-muted bg-[#16181c] border-t border-slack-border/30">
                                  <div>{tool.input_summary}</div>
                                  {tool.output_summary && (
                                    <div className="mt-1 text-slack-text">
                                      {tool.output_summary}
                                    </div>
                                  )}
                                </div>
                              </details>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              });
            })()}

            {/* Sending indicator */}
            {sending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 bg-orange-600 text-white">
                  C
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-white font-bold text-sm">Claude</span>
                  <span className="text-sm text-slack-muted animate-pulse">
                    考え中...
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer: input + actions */}
      <div className="border-t border-slack-border/50 px-6 py-3 shrink-0">
        {sendError && (
          <div className="text-xs text-red-400 mb-2">{sendError}</div>
        )}
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="メッセージを送信（Cmd+Enterで送信）"
              disabled={sending}
              rows={1}
              className="w-full bg-[#35373b] text-white text-sm px-4 py-2.5 rounded-lg border border-slack-border focus:outline-none focus:border-slack-accent resize-none disabled:opacity-50"
              style={{ minHeight: "40px", maxHeight: "120px" }}
              onInput={(e) => {
                const t = e.currentTarget;
                t.style.height = "auto";
                t.style.height = Math.min(t.scrollHeight, 120) + "px";
              }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || sending}
            className="px-4 py-2.5 bg-slack-accent text-white text-sm rounded-lg hover:bg-slack-accent/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            送信
          </button>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <button
            onClick={handleResume}
            className="px-3 py-1 bg-[#35373b] text-slack-text text-xs rounded hover:bg-slack-hover transition-colors"
          >
            ターミナルで再開
          </button>
        </div>
      </div>
    </div>
  );
}
