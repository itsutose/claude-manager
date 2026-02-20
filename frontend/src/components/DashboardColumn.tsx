import { useEffect, useRef, useState } from "react";
import type { ColumnState } from "../hooks/useDashboard";
import type { SessionEntry, SessionMessage } from "../types";
import {
  statusColor,
  timeAgo,
  formatTime,
  renderContent,
} from "../helpers";

// --- Message grouping (compact version from MessageArea) ---

interface ToolEntry {
  tool_name: string;
  input_summary: string;
  output_summary: string;
}

type DisplayItem =
  | { kind: "message"; msg: SessionMessage }
  | { kind: "tool-group"; tools: ToolEntry[] };

function isToolOnlyMessage(msg: SessionMessage): boolean {
  return (
    msg.role === "assistant" && !msg.content.trim() && msg.tool_uses.length > 0
  );
}

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
        pendingTools.push(t);
      }
    } else {
      flushTools();
      items.push({ kind: "message", msg });
    }
  }
  flushTools();
  return items;
}

// --- Session Picker Dropdown ---

function SessionPicker({
  allSessions,
  excludeIds,
  onSelect,
  onClose,
}: {
  allSessions: SessionEntry[];
  excludeIds: Set<string>;
  onSelect: (sessionId: string) => void;
  onClose: () => void;
}) {
  const [filter, setFilter] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [onClose]);

  const filtered = allSessions.filter((s) => {
    if (excludeIds.has(s.session_id)) return false;
    if (!filter) return true;
    const q = filter.toLowerCase();
    return (
      s.display_name.toLowerCase().includes(q) ||
      (s.first_prompt ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div
      ref={ref}
      className="absolute top-full left-0 right-0 mt-1 z-50 bg-[#2b2d31] border border-slack-border/50 rounded-lg shadow-xl max-h-[300px] overflow-hidden flex flex-col"
    >
      <div className="p-2 border-b border-slack-border/30">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="セッションを検索..."
          autoFocus
          className="w-full bg-[#35373b] text-white text-xs px-2 py-1.5 rounded border border-transparent focus:outline-none focus:border-slack-accent/50"
        />
      </div>
      <div className="overflow-y-auto flex-1">
        {filtered.length === 0 ? (
          <div className="px-3 py-4 text-xs text-slack-muted text-center">
            該当なし
          </div>
        ) : (
          filtered.slice(0, 20).map((s) => (
            <button
              key={s.session_id}
              onClick={() => {
                onSelect(s.session_id);
                onClose();
              }}
              className="w-full text-left px-3 py-2 hover:bg-slack-hover flex items-center gap-2"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${statusColor(s.status)}`}
              />
              <div className="min-w-0 flex-1">
                <div className="text-xs text-white truncate">
                  {s.display_name}
                </div>
                <div className="text-[10px] text-slack-muted">
                  {s.message_count} msgs · {timeAgo(s.modified)}
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

// --- Column Component ---

interface Props {
  column: ColumnState;
  columnIndex: number;
  allSessions: SessionEntry[];
  otherColumnIds: Set<string>;
  onSwitch: (columnIndex: number, sessionId: string) => void;
  onRemove: (columnIndex: number) => void;
  onInputChange: (sessionId: string, value: string) => void;
  onSend: (sessionId: string) => void;
}

export function DashboardColumn({
  column,
  columnIndex,
  allSessions,
  otherColumnIds,
  onSwitch,
  onRemove,
  onInputChange,
  onSend,
}: Props) {
  const areaRef = useRef<HTMLDivElement>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (areaRef.current) {
      areaRef.current.scrollTop = areaRef.current.scrollHeight;
    }
  }, [column.messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSend(column.sessionId);
    }
  };

  const items = groupMessages(column.messages);

  return (
    <div className="w-[340px] shrink-0 flex flex-col bg-slack-sidebar rounded-lg border border-slack-border/50 overflow-hidden">
      {/* Header */}
      <div className="relative px-3 py-2 border-b border-slack-border/50 shrink-0">
        <div className="flex items-center gap-2">
          {column.session && (
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${statusColor(column.session.status)}`}
            />
          )}
          <button
            onClick={() => setPickerOpen(!pickerOpen)}
            className="min-w-0 flex-1 text-left group"
            title="セッションを切り替え"
          >
            <div className="text-sm text-white font-bold truncate group-hover:text-slack-accent transition-colors">
              {column.session?.display_name ?? "読み込み中..."}
            </div>
            {column.session && (
              <div className="text-[10px] text-slack-muted truncate">
                {column.session.message_count} msgs · {timeAgo(column.session.modified)}
                {column.session.git_branch && ` · ${column.session.git_branch}`}
              </div>
            )}
          </button>
          {/* Swap icon */}
          <button
            onClick={() => setPickerOpen(!pickerOpen)}
            className="p-1 rounded text-slack-muted hover:text-white hover:bg-slack-hover transition-colors shrink-0"
            title="セッション切替"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
          </button>
          {/* Close */}
          <button
            onClick={() => onRemove(columnIndex)}
            className="p-1 rounded text-slack-muted hover:text-red-400 hover:bg-slack-hover transition-colors shrink-0"
            title="カラムを閉じる"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Session Picker */}
        {pickerOpen && (
          <SessionPicker
            allSessions={allSessions}
            excludeIds={otherColumnIds}
            onSelect={(id) => onSwitch(columnIndex, id)}
            onClose={() => setPickerOpen(false)}
          />
        )}
      </div>

      {/* Messages */}
      <div ref={areaRef} className="flex-1 overflow-y-auto px-3 py-2 min-h-0">
        {column.loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-xs text-slack-muted animate-pulse">
              読み込み中...
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((item, i) => {
              if (item.kind === "tool-group") {
                const counts = new Map<string, number>();
                for (const t of item.tools) {
                  counts.set(
                    t.tool_name,
                    (counts.get(t.tool_name) ?? 0) + 1,
                  );
                }
                const summary = [...counts.entries()]
                  .map(([name, count]) =>
                    count > 1 ? `${name} x${count}` : name,
                  )
                  .join(", ");
                return (
                  <details
                    key={`tg-${i}`}
                    className="ml-6 border border-slack-border/30 rounded"
                  >
                    <summary className="px-2 py-0.5 text-[10px] text-slack-muted cursor-pointer hover:text-white">
                      {summary}
                    </summary>
                    <div className="px-2 py-1 space-y-0.5 bg-[#16181c] border-t border-slack-border/30">
                      {item.tools.map((tool, j) => (
                        <div key={j} className="text-[10px] text-slack-muted truncate">
                          <span className="text-slack-text">{tool.tool_name}</span>
                          {tool.input_summary && (
                            <span className="ml-1">{tool.input_summary}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </details>
                );
              }

              const msg = item.msg;
              return (
                <div key={msg.message_id} className="flex gap-2">
                  <div
                    className={`w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold shrink-0 mt-0.5 ${
                      msg.role === "user"
                        ? "bg-green-600 text-white"
                        : "bg-orange-600 text-white"
                    }`}
                  >
                    {msg.role === "user" ? "U" : "C"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1 mb-0.5">
                      <span className="text-[11px] font-bold text-white">
                        {msg.role === "user" ? "You" : "Claude"}
                      </span>
                      {msg.timestamp && (
                        <span className="text-[10px] text-slack-muted">
                          {formatTime(msg.timestamp)}
                        </span>
                      )}
                    </div>
                    {msg.content && (
                      <div
                        className="message-content text-xs text-slack-text leading-relaxed break-words"
                        dangerouslySetInnerHTML={{
                          __html: renderContent(msg.content),
                        }}
                      />
                    )}
                    {msg.tool_uses.length > 0 && (
                      <div className="mt-1 space-y-0.5">
                        {msg.tool_uses.map((tool, j) => (
                          <details
                            key={j}
                            className="border border-slack-border/30 rounded"
                          >
                            <summary className="px-2 py-0.5 text-[10px] text-slack-muted cursor-pointer hover:text-white">
                              {tool.tool_name}
                            </summary>
                            <div className="px-2 py-1 text-[10px] text-slack-muted bg-[#16181c] border-t border-slack-border/30">
                              <div className="truncate">{tool.input_summary}</div>
                            </div>
                          </details>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Sending indicator */}
            {column.sending && (
              <div className="flex gap-2">
                <div className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold shrink-0 mt-0.5 bg-orange-600 text-white">
                  C
                </div>
                <span className="text-xs text-slack-muted animate-pulse">
                  考え中...
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slack-border/50 px-3 py-2 shrink-0">
        {column.sendError && (
          <div className="text-[10px] text-red-400 mb-1">{column.sendError}</div>
        )}
        <div className="flex items-end gap-1.5">
          <textarea
            value={column.inputValue}
            onChange={(e) => onInputChange(column.sessionId, e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Cmd+Enter で送信"
            disabled={column.sending}
            rows={1}
            className="flex-1 bg-[#35373b] text-white text-xs px-2 py-1.5 rounded border border-slack-border focus:outline-none focus:border-slack-accent/50 resize-none disabled:opacity-50"
            style={{ minHeight: "30px", maxHeight: "80px" }}
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 80) + "px";
            }}
          />
          <button
            onClick={() => onSend(column.sessionId)}
            disabled={!column.inputValue.trim() || column.sending}
            className="px-2 py-1.5 bg-slack-accent text-white text-[10px] rounded hover:bg-slack-accent/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            送信
          </button>
        </div>
      </div>
    </div>
  );
}
