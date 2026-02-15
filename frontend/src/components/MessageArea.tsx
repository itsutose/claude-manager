import { useEffect, useRef } from "react";
import type { SessionEntry, SessionMessage } from "../types";
import { formatDate, formatDateFull, formatTime, renderContent } from "../helpers";
import { togglePin, resumeSession } from "../api";

interface Props {
  session: SessionEntry;
  messages: SessionMessage[];
  loading: boolean;
  onSessionUpdate: (session: SessionEntry) => void;
  onRefreshGroup: () => void;
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

export function MessageArea({
  session,
  messages,
  loading,
  onSessionUpdate,
  onRefreshGroup,
}: Props) {
  const areaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (areaRef.current) {
      areaRef.current.scrollTop = areaRef.current.scrollHeight;
    }
  }, [messages]);

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

  const handleCopyCommand = async () => {
    const cmd = `cd ${session.clone_id.replace(/-/g, "/")} && claude --resume ${session.session_id}`;
    await navigator.clipboard.writeText(cmd);
  };

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <div className="border-b border-slack-border/50 px-6 py-3 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-white font-bold text-[15px]">
              # {session.display_name}
            </h3>
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
          <div className="flex items-center gap-2">
            <button
              onClick={handleTogglePin}
              className={`p-1.5 rounded hover:bg-slack-hover transition-colors ${
                session.is_pinned
                  ? "text-yellow-400"
                  : "text-slack-muted hover:text-white"
              }`}
              title="ピン留め"
            >
              <svg
                className="w-4 h-4"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.789l1.599.799L9 4.323V3a1 1 0 011-1z" />
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
            {messages.map((msg, i) => {
              const prev = i > 0 ? messages[i - 1] : null;
              const showDate = i === 0 || dateDiffersFrom(msg, prev);
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
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-slack-border/50 px-6 py-3 flex items-center gap-3 shrink-0">
        <button
          onClick={handleResume}
          className="px-4 py-1.5 bg-slack-accent text-white text-sm rounded hover:bg-slack-accent/80 transition-colors"
        >
          セッション再開
        </button>
        <button
          onClick={handleCopyCommand}
          className="px-4 py-1.5 bg-[#35373b] text-slack-text text-sm rounded hover:bg-slack-hover transition-colors"
        >
          コマンドコピー
        </button>
      </div>
    </div>
  );
}
