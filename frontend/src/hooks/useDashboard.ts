import { useCallback, useEffect, useRef, useState } from "react";
import type {
  SessionEntry,
  SessionMessage,
  ProjectGroup,
} from "../types";
import {
  fetchGroups,
  fetchGroupDetail,
  fetchSession,
  fetchMessages,
  sendMessage,
} from "../api";

const STORAGE_KEY = "dashboard_columns";
const MAX_COLUMNS = 4;

export interface ColumnState {
  sessionId: string;
  session: SessionEntry | null;
  messages: SessionMessage[];
  loading: boolean;
  sending: boolean;
  sendError: string | null;
  inputValue: string;
}

function loadSavedColumnIds(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return [];
}

function saveColumnIds(ids: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}

export function useDashboard() {
  const [columns, setColumns] = useState<ColumnState[]>([]);
  const [allSessions, setAllSessions] = useState<SessionEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const initializedRef = useRef(false);
  const columnsRef = useRef<ColumnState[]>([]);
  columnsRef.current = columns;

  // Fetch all sessions across all groups
  const loadAllSessions = useCallback(async (): Promise<SessionEntry[]> => {
    const groups: ProjectGroup[] = await fetchGroups();
    const details = await Promise.all(
      groups.map((g) => fetchGroupDetail(g.group_id)),
    );
    const sessions: SessionEntry[] = [];
    for (const detail of details) {
      for (const clone of detail.clones) {
        for (const s of clone.sessions) {
          sessions.push(s);
        }
      }
    }
    sessions.sort(
      (a, b) =>
        new Date(b.modified).getTime() - new Date(a.modified).getTime(),
    );
    setAllSessions(sessions);
    return sessions;
  }, []);

  // Load a single column's data
  const loadColumnData = useCallback(
    async (sessionId: string): Promise<ColumnState> => {
      try {
        const [session, msgData] = await Promise.all([
          fetchSession(sessionId),
          fetchMessages(sessionId),
        ]);
        return {
          sessionId,
          session,
          messages: msgData.messages,
          loading: false,
          sending: false,
          sendError: null,
          inputValue: "",
        };
      } catch {
        return {
          sessionId,
          session: null,
          messages: [],
          loading: false,
          sending: false,
          sendError: "読み込み失敗",
          inputValue: "",
        };
      }
    },
    [],
  );

  // Initialize dashboard
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    (async () => {
      setIsLoading(true);
      const sessions = await loadAllSessions();

      let columnIds = loadSavedColumnIds().filter((id) =>
        sessions.some((s) => s.session_id === id),
      );
      if (columnIds.length === 0) {
        columnIds = sessions.slice(0, MAX_COLUMNS).map((s) => s.session_id);
      }
      columnIds = columnIds.slice(0, MAX_COLUMNS);

      // Set placeholder columns immediately (loading state)
      setColumns(
        columnIds.map((id) => ({
          sessionId: id,
          session: null,
          messages: [],
          loading: true,
          sending: false,
          sendError: null,
          inputValue: "",
        })),
      );

      // Load all column data in parallel
      const loaded = await Promise.all(columnIds.map(loadColumnData));
      setColumns(loaded);
      saveColumnIds(columnIds);
      setIsLoading(false);
    })();
  }, [loadAllSessions, loadColumnData]);

  // Switch a column's session
  const switchColumn = useCallback(
    async (columnIndex: number, newSessionId: string) => {
      setColumns((prev) => {
        const next = [...prev];
        next[columnIndex] = {
          sessionId: newSessionId,
          session: null,
          messages: [],
          loading: true,
          sending: false,
          sendError: null,
          inputValue: "",
        };
        saveColumnIds(next.map((c) => c.sessionId));
        return next;
      });

      const data = await loadColumnData(newSessionId);
      setColumns((prev) => {
        const next = [...prev];
        if (next[columnIndex]?.sessionId === newSessionId) {
          next[columnIndex] = data;
        }
        return next;
      });
    },
    [loadColumnData],
  );

  // Remove a column and auto-fill from recent sessions
  const removeColumn = useCallback(
    async (columnIndex: number) => {
      setColumns((prev) => {
        const removed = prev[columnIndex];
        const next = prev.filter((_, i) => i !== columnIndex);
        // Find a session not already in columns to replace it
        const usedIds = new Set(next.map((c) => c.sessionId));
        const replacement = allSessions.find(
          (s) => !usedIds.has(s.session_id) && s.session_id !== removed?.sessionId,
        );
        if (replacement) {
          next.push({
            sessionId: replacement.session_id,
            session: null,
            messages: [],
            loading: true,
            sending: false,
            sendError: null,
            inputValue: "",
          });
        }
        saveColumnIds(next.map((c) => c.sessionId));
        return next;
      });

      // Load the replacement column if it was added
      setColumns((prev) => {
        const lastCol = prev[prev.length - 1];
        if (lastCol?.loading && lastCol.session === null) {
          loadColumnData(lastCol.sessionId).then((data) => {
            setColumns((p) => {
              const n = [...p];
              const idx = n.findIndex((c) => c.sessionId === data.sessionId);
              if (idx >= 0) n[idx] = data;
              return n;
            });
          });
        }
        return prev;
      });
    },
    [allSessions, loadColumnData],
  );

  // Set input value for a column
  const setColumnInput = useCallback(
    (sessionId: string, value: string) => {
      setColumns((prev) =>
        prev.map((c) =>
          c.sessionId === sessionId ? { ...c, inputValue: value } : c,
        ),
      );
    },
    [],
  );

  // Send message in a column
  const sendColumnMessage = useCallback(async (sessionId: string) => {
    const col = columnsRef.current.find((c) => c.sessionId === sessionId);
    if (!col) return;

    const inputValue = col.inputValue.trim();
    const session = col.session;
    if (!inputValue || !session) return;

    // Optimistic: add user message, clear input, set sending
    const userMsg: SessionMessage = {
      message_id: `temp-${Date.now()}`,
      role: "user",
      content: inputValue,
      timestamp: new Date().toISOString(),
      tool_uses: [],
    };

    setColumns((prev) =>
      prev.map((c) =>
        c.sessionId === sessionId
          ? {
              ...c,
              inputValue: "",
              sending: true,
              sendError: null,
              messages: [...c.messages, userMsg],
            }
          : c,
      ),
    );

    try {
      const result = await sendMessage(sessionId, inputValue);
      if (result.success && result.result) {
        const assistantMsg: SessionMessage = {
          message_id: `temp-${Date.now()}-resp`,
          role: "assistant",
          content: result.result,
          timestamp: new Date().toISOString(),
          tool_uses: [],
        };
        setColumns((prev) =>
          prev.map((c) =>
            c.sessionId === sessionId
              ? {
                  ...c,
                  sending: false,
                  messages: [...c.messages, assistantMsg],
                  session: c.session
                    ? { ...c.session, message_count: c.session.message_count + 2 }
                    : c.session,
                }
              : c,
          ),
        );
      } else {
        setColumns((prev) =>
          prev.map((c) =>
            c.sessionId === sessionId
              ? { ...c, sending: false, sendError: result.error ?? "送信失敗" }
              : c,
          ),
        );
      }
    } catch {
      setColumns((prev) =>
        prev.map((c) =>
          c.sessionId === sessionId
            ? { ...c, sending: false, sendError: "通信エラー" }
            : c,
        ),
      );
    }
  }, []);

  // Refresh all columns' session metadata (called on SSE)
  const refreshDashboard = useCallback(async () => {
    const sessions = await loadAllSessions();

    // Refresh each non-sending column's messages
    setColumns((prev) => {
      for (const col of prev) {
        if (!col.sending) {
          loadColumnData(col.sessionId).then((data) => {
            setColumns((p) =>
              p.map((c) =>
                c.sessionId === data.sessionId && !c.sending
                  ? { ...data, inputValue: c.inputValue }
                  : c,
              ),
            );
          });
        }
      }
      // Update session metadata from fresh allSessions
      return prev.map((col) => {
        const fresh = sessions.find((s) => s.session_id === col.sessionId);
        if (fresh && col.session) {
          return { ...col, session: { ...col.session, ...fresh } };
        }
        return col;
      });
    });
  }, [loadAllSessions, loadColumnData]);

  return {
    columns,
    allSessions,
    isLoading,
    switchColumn,
    removeColumn,
    setColumnInput,
    sendColumnMessage,
    refreshDashboard,
  };
}
