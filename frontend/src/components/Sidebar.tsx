import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ProjectGroupDetail,
  ProjectClone,
  SessionEntry,
} from "../types";
import { statusColor } from "../helpers";
import { renameSession, togglePin, hideSession, unhideSession } from "../api";

// --- Context Menu ---

interface MenuState {
  sessionId: string;
  x: number;
  y: number;
}

interface RenameState {
  sessionId: string;
  currentName: string;
}

function ContextMenu({
  menu,
  session,
  isTrash,
  onClose,
  onRename,
  onTogglePin,
  onHide,
  onUnhide,
}: {
  menu: MenuState;
  session: SessionEntry | undefined;
  isTrash: boolean;
  onClose: () => void;
  onRename: (sessionId: string, currentName: string) => void;
  onTogglePin: (sessionId: string) => void;
  onHide: (sessionId: string) => void;
  onUnhide: (sessionId: string) => void;
}) {
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

  if (!session) return null;

  // trash内セッションは「復元」のみ表示
  if (isTrash) {
    return (
      <div
        ref={ref}
        className="fixed z-50 bg-[#2b2d31] border border-slack-border/50 rounded-lg shadow-xl py-1 min-w-[160px]"
        style={{ top: menu.y, left: menu.x }}
      >
        <button
          onClick={() => {
            onUnhide(menu.sessionId);
            onClose();
          }}
          className="w-full text-left px-3 py-1.5 text-sm text-slack-text hover:bg-slack-hover flex items-center gap-2"
        >
          <svg className="w-3.5 h-3.5 text-slack-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
          </svg>
          復元
        </button>
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-[#2b2d31] border border-slack-border/50 rounded-lg shadow-xl py-1 min-w-[160px]"
      style={{ top: menu.y, left: menu.x }}
    >
      <button
        onClick={() => {
          onRename(menu.sessionId, session.display_name);
          onClose();
        }}
        className="w-full text-left px-3 py-1.5 text-sm text-slack-text hover:bg-slack-hover flex items-center gap-2"
      >
        <svg className="w-3.5 h-3.5 text-slack-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        名前を変更
      </button>
      <button
        onClick={() => {
          onTogglePin(menu.sessionId);
          onClose();
        }}
        className="w-full text-left px-3 py-1.5 text-sm text-slack-text hover:bg-slack-hover flex items-center gap-2"
      >
        <svg className="w-3.5 h-3.5 text-slack-muted" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.789l1.599.799L9 4.323V3a1 1 0 011-1z" />
        </svg>
        {session.is_pinned ? "ピン解除" : "ピン留め"}
      </button>
      <div className="h-px bg-slack-border/30 my-1" />
      <button
        onClick={() => {
          onHide(menu.sessionId);
          onClose();
        }}
        className="w-full text-left px-3 py-1.5 text-sm text-red-400 hover:bg-slack-hover flex items-center gap-2"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.59 6.59m7.532 7.532l3.29 3.29M3 3l18 18" />
        </svg>
        非表示
      </button>
    </div>
  );
}

// --- Session Item ---

function SessionItem({
  session,
  selected,
  onClick,
  onMenuOpen,
  renaming,
  renameValue,
  onRenameChange,
  onRenameSubmit,
  onRenameCancel,
}: {
  session: SessionEntry;
  selected: boolean;
  onClick: () => void;
  onMenuOpen: (sessionId: string, e: React.MouseEvent) => void;
  renaming: boolean;
  renameValue: string;
  onRenameChange: (v: string) => void;
  onRenameSubmit: () => void;
  onRenameCancel: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (renaming && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [renaming]);

  if (renaming) {
    return (
      <div className="w-full px-2 py-1">
        <input
          ref={inputRef}
          type="text"
          value={renameValue}
          onChange={(e) => onRenameChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onRenameSubmit();
            if (e.key === "Escape") onRenameCancel();
          }}
          onBlur={onRenameCancel}
          className="w-full bg-[#35373b] text-white text-sm px-2 py-0.5 rounded border border-slack-accent/50 focus:outline-none focus:border-slack-accent"
        />
      </div>
    );
  }

  return (
    <div className="group relative">
      <button
        onClick={onClick}
        onContextMenu={(e) => {
          e.preventDefault();
          onMenuOpen(session.session_id, e);
        }}
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
          className={`truncate flex-1 ${
            session.has_unread ? "font-bold text-white" : ""
          } ${!session.custom_title ? "text-slack-muted italic" : ""}`}
        >
          {session.display_name}
        </span>
      </button>
      {/* Three-dot menu on hover */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onMenuOpen(session.session_id, e);
        }}
        className="absolute right-1 top-1/2 -translate-y-1/2 w-5 h-5 rounded flex items-center justify-center text-slack-muted hover:text-white hover:bg-slack-hover opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
        </svg>
      </button>
    </div>
  );
}

// --- Clone Section ---

function CloneSection({
  clone,
  selectedSessionId,
  onOpenSession,
  onMenuOpen,
  onNewSession,
  renamingSessionId,
  renameValue,
  onRenameChange,
  onRenameSubmit,
  onRenameCancel,
}: {
  clone: ProjectClone;
  selectedSessionId: string | null;
  onOpenSession: (sessionId: string) => void;
  onMenuOpen: (sessionId: string, e: React.MouseEvent) => void;
  onNewSession?: (cloneId: string) => void;
  renamingSessionId: string | null;
  renameValue: string;
  onRenameChange: (v: string) => void;
  onRenameSubmit: () => void;
  onRenameCancel: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [trashExpanded, setTrashExpanded] = useState(false);

  const trashCount = clone.trash_sessions?.length ?? 0;

  return (
    <div className="mb-1">
      <div className="group/clone flex items-center">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex-1 flex items-center gap-1 px-2 py-1 text-slack-muted text-xs font-medium cursor-pointer hover:text-white"
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
        {onNewSession && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onNewSession(clone.clone_id);
            }}
            className="w-5 h-5 mr-1 rounded flex items-center justify-center text-slack-muted hover:text-white hover:bg-slack-hover opacity-0 group-hover/clone:opacity-100 transition-opacity shrink-0"
            title="新規セッション"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </div>
      {expanded && (
        <div className="ml-2">
          {clone.sessions.map((s) => (
            <SessionItem
              key={s.session_id}
              session={s}
              selected={selectedSessionId === s.session_id}
              onClick={() => onOpenSession(s.session_id)}
              onMenuOpen={onMenuOpen}
              renaming={renamingSessionId === s.session_id}
              renameValue={renameValue}
              onRenameChange={onRenameChange}
              onRenameSubmit={onRenameSubmit}
              onRenameCancel={onRenameCancel}
            />
          ))}
          {/* Trash section */}
          {trashCount > 0 && (
            <div className="mt-1">
              <button
                onClick={() => setTrashExpanded(!trashExpanded)}
                className="flex items-center gap-1 px-2 py-0.5 text-slack-muted/50 text-[11px] cursor-pointer hover:text-slack-muted"
              >
                <svg
                  className={`w-2.5 h-2.5 transition-transform ${trashExpanded ? "" : "-rotate-90"}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                  />
                </svg>
                <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                <span>trash</span>
                <span className="text-[10px]">{trashCount}</span>
              </button>
              {trashExpanded && (
                <div className="ml-2 opacity-60">
                  {clone.trash_sessions.map((s) => (
                    <SessionItem
                      key={s.session_id}
                      session={s}
                      selected={selectedSessionId === s.session_id}
                      onClick={() => onOpenSession(s.session_id)}
                      onMenuOpen={onMenuOpen}
                      renaming={renamingSessionId === s.session_id}
                      renameValue={renameValue}
                      onRenameChange={onRenameChange}
                      onRenameSubmit={onRenameSubmit}
                      onRenameCancel={onRenameCancel}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// --- Sidebar ---

interface Props {
  groupDetail: ProjectGroupDetail | null;
  selectedSessionId: string | null;
  onOpenSession: (sessionId: string) => void;
  onRefreshGroup?: () => void;
  onNewSession?: (cloneId: string) => void;
  width?: number;
}

export function Sidebar({
  groupDetail,
  selectedSessionId,
  onOpenSession,
  onRefreshGroup,
  onNewSession,
  width,
}: Props) {
  const [filter, setFilter] = useState("");
  const [menu, setMenu] = useState<MenuState | null>(null);
  const [renameState, setRenameState] = useState<RenameState | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // Find a session by ID from all clones (including trash)
  const findSession = useCallback(
    (sessionId: string): { session: SessionEntry; isTrash: boolean } | undefined => {
      if (!groupDetail) return undefined;
      for (const clone of groupDetail.clones) {
        const s = clone.sessions.find((s) => s.session_id === sessionId);
        if (s) return { session: s, isTrash: false };
        const t = clone.trash_sessions?.find((s) => s.session_id === sessionId);
        if (t) return { session: t, isTrash: true };
      }
      return undefined;
    },
    [groupDetail],
  );

  const handleMenuOpen = useCallback(
    (sessionId: string, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      // Position menu near the click, but keep within viewport
      const x = Math.min(e.clientX, window.innerWidth - 180);
      const y = Math.min(e.clientY, window.innerHeight - 150);
      setMenu({ sessionId, x, y });
    },
    [],
  );

  const handleMenuClose = useCallback(() => setMenu(null), []);

  const handleStartRename = useCallback(
    (sessionId: string, currentName: string) => {
      setRenameState({ sessionId, currentName });
      setRenameValue(currentName);
    },
    [],
  );

  const handleRenameSubmit = useCallback(async () => {
    if (!renameState || !renameValue.trim()) {
      setRenameState(null);
      return;
    }
    await renameSession(renameState.sessionId, renameValue.trim());
    setRenameState(null);
    onRefreshGroup?.();
  }, [renameState, renameValue, onRefreshGroup]);

  const handleRenameCancel = useCallback(() => {
    setRenameState(null);
  }, []);

  const handleTogglePin = useCallback(
    async (sessionId: string) => {
      await togglePin(sessionId);
      onRefreshGroup?.();
    },
    [onRefreshGroup],
  );

  const handleHide = useCallback(
    async (sessionId: string) => {
      await hideSession(sessionId);
      onRefreshGroup?.();
    },
    [onRefreshGroup],
  );

  const handleUnhide = useCallback(
    async (sessionId: string) => {
      await unhideSession(sessionId);
      onRefreshGroup?.();
    },
    [onRefreshGroup],
  );

  const pinnedSessions: SessionEntry[] = [];
  if (groupDetail) {
    for (const clone of groupDetail.clones) {
      for (const s of clone.sessions) {
        if (s.is_pinned) pinnedSessions.push(s);
      }
    }
  }

  return (
    <div
      className="bg-slack-sidebar flex flex-col border-r border-slack-border/50 shrink-0"
      style={{ width: width ?? 260 }}
    >
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
                onMenuOpen={handleMenuOpen}
                renaming={renameState?.sessionId === s.session_id}
                renameValue={renameValue}
                onRenameChange={setRenameValue}
                onRenameSubmit={handleRenameSubmit}
                onRenameCancel={handleRenameCancel}
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
              onMenuOpen={handleMenuOpen}
              onNewSession={onNewSession}
              renamingSessionId={renameState?.sessionId ?? null}
              renameValue={renameValue}
              onRenameChange={setRenameValue}
              onRenameSubmit={handleRenameSubmit}
              onRenameCancel={handleRenameCancel}
            />
          ))}
      </div>

      {/* Context Menu */}
      {menu && (() => {
        const found = findSession(menu.sessionId);
        return (
          <ContextMenu
            menu={menu}
            session={found?.session}
            isTrash={found?.isTrash ?? false}
            onClose={handleMenuClose}
            onRename={handleStartRename}
            onTogglePin={handleTogglePin}
            onHide={handleHide}
            onUnhide={handleUnhide}
          />
        );
      })()}
    </div>
  );
}
