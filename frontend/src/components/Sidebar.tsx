import { useState } from "react";
import type {
  ProjectGroupDetail,
  ProjectClone,
  SessionEntry,
} from "../types";
import { statusColor } from "../helpers";

interface Props {
  groupDetail: ProjectGroupDetail | null;
  selectedSessionId: string | null;
  onOpenSession: (sessionId: string) => void;
}

function SessionItem({
  session,
  selected,
  onClick,
}: {
  session: SessionEntry;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-2 py-1 rounded cursor-pointer text-sm text-left ${
        selected
          ? "bg-slack-active text-white"
          : "hover:bg-slack-hover"
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full shrink-0 ${statusColor(session.status)}`}
      />
      <span
        className={`truncate ${
          session.has_unread ? "font-bold text-white" : ""
        } ${!session.custom_title ? "text-slack-muted italic" : ""}`}
      >
        {session.display_name}
      </span>
    </button>
  );
}

function CloneSection({
  clone,
  selectedSessionId,
  onOpenSession,
}: {
  clone: ProjectClone;
  selectedSessionId: string | null;
  onOpenSession: (sessionId: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="mb-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1 px-2 py-1 text-slack-muted text-xs font-medium cursor-pointer hover:text-white"
      >
        <svg
          className={`w-3 h-3 transition-transform ${expanded ? "" : "-rotate-90"}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
          />
        </svg>
        <span>{clone.clone_name}</span>
        <span className="text-[10px] text-slack-muted/60">
          {clone.session_count}
        </span>
      </button>
      {expanded && (
        <div className="ml-2">
          {clone.sessions.map((s) => (
            <SessionItem
              key={s.session_id}
              session={s}
              selected={selectedSessionId === s.session_id}
              onClick={() => onOpenSession(s.session_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function Sidebar({
  groupDetail,
  selectedSessionId,
  onOpenSession,
}: Props) {
  const [filter, setFilter] = useState("");

  const pinnedSessions: SessionEntry[] = [];
  if (groupDetail) {
    for (const clone of groupDetail.clones) {
      for (const s of clone.sessions) {
        if (s.is_pinned) pinnedSessions.push(s);
      }
    }
  }

  return (
    <div className="w-[260px] bg-slack-sidebar flex flex-col border-r border-slack-border/50 shrink-0">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slack-border/50">
        <h2 className="text-white font-bold text-[15px] truncate">
          {groupDetail?.display_name ?? "Claude Manager"}
        </h2>
        <div className="text-xs text-slack-muted mt-0.5">
          {groupDetail ? `${groupDetail.total_sessions} sessions` : ""}
        </div>
      </div>

      {/* Filter */}
      <div className="px-3 py-2">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="フィルタ..."
          className="w-full bg-[#35373b] text-slack-text text-xs px-3 py-1.5 rounded border border-transparent focus:outline-none focus:border-slack-accent/50"
        />
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto px-2">
        {pinnedSessions.length > 0 && (
          <div className="mb-2">
            <div className="flex items-center gap-1 px-2 py-1 text-slack-muted text-xs font-medium">
              <svg
                className="w-3 h-3"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.789l1.599.799L9 4.323V3a1 1 0 011-1z" />
              </svg>
              ピン留め
            </div>
            {pinnedSessions.map((s) => (
              <SessionItem
                key={s.session_id}
                session={s}
                selected={selectedSessionId === s.session_id}
                onClick={() => onOpenSession(s.session_id)}
              />
            ))}
          </div>
        )}

        {groupDetail?.clones
          .filter((clone) => {
            if (!filter) return true;
            const q = filter.toLowerCase();
            return clone.sessions.some(
              (s) =>
                s.display_name.toLowerCase().includes(q) ||
                (s.first_prompt ?? "").toLowerCase().includes(q) ||
                (s.git_branch ?? "").toLowerCase().includes(q),
            );
          })
          .map((clone) => (
            <CloneSection
              key={clone.clone_id}
              clone={clone}
              selectedSessionId={selectedSessionId}
              onOpenSession={onOpenSession}
            />
          ))}
      </div>
    </div>
  );
}
