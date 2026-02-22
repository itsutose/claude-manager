import { useCallback, useRef, useState } from "react";
import type { SplitPane, SessionEntry, SessionMessage } from "../types";
import { fetchSession, fetchMessages, sendMessage } from "../api";

const MAX_PANES = 4;
let paneCounter = 0;
function generatePaneId(): string {
  return `pane-${++paneCounter}-${Date.now()}`;
}

export function useSplitView() {
  const [panes, setPanes] = useState<SplitPane[]>([]);
  const [activePaneId, setActivePaneId] = useState<string | null>(null);
  const panesRef = useRef<SplitPane[]>([]);
  panesRef.current = panes;

  const loadPaneData = useCallback(
    async (paneId: string, sessionId: string) => {
      try {
        const [session, msgData] = await Promise.all([
          fetchSession(sessionId),
          fetchMessages(sessionId),
        ]);
        setPanes((prev) =>
          prev.map((p) =>
            p.paneId === paneId && p.sessionId === sessionId
              ? { ...p, session, messages: msgData.messages, loading: false }
              : p,
          ),
        );
      } catch {
        setPanes((prev) =>
          prev.map((p) =>
            p.paneId === paneId && p.sessionId === sessionId
              ? { ...p, loading: false, sendError: "読み込み失敗" }
              : p,
          ),
        );
      }
    },
    [],
  );

  // 新しいペインを追加（D&D時）
  const openPane = useCallback(
    async (sessionId: string) => {
      // 既に同じセッションが開いていればアクティブにするだけ
      const existing = panesRef.current.find(
        (p) => p.sessionId === sessionId,
      );
      if (existing) {
        setActivePaneId(existing.paneId);
        return;
      }
      if (panesRef.current.length >= MAX_PANES) return;

      const paneId = generatePaneId();
      const newPane: SplitPane = {
        paneId,
        sessionId,
        session: null,
        messages: [],
        loading: true,
        sending: false,
        sendError: null,
        inputValue: "",
        pastedImages: [],
      };
      setPanes((prev) => [...prev, newPane]);
      setActivePaneId(paneId);
      await loadPaneData(paneId, sessionId);
    },
    [loadPaneData],
  );

  // アクティブペインでセッションを切り替え（サイドバークリック時）
  const openInActivePane = useCallback(
    async (sessionId: string) => {
      if (panesRef.current.length === 0) {
        return openPane(sessionId);
      }
      // 既に同じセッションがどこかにあればアクティブにするだけ
      const existing = panesRef.current.find(
        (p) => p.sessionId === sessionId,
      );
      if (existing) {
        setActivePaneId(existing.paneId);
        return;
      }
      const targetId = activePaneId ?? panesRef.current[0].paneId;
      setPanes((prev) =>
        prev.map((p) =>
          p.paneId === targetId
            ? {
                ...p,
                sessionId,
                session: null,
                messages: [],
                loading: true,
                sendError: null,
                inputValue: "",
                pastedImages: [],
              }
            : p,
        ),
      );
      await loadPaneData(targetId, sessionId);
    },
    [activePaneId, openPane, loadPaneData],
  );

  // ペインのセッションを入れ替え（ペインへのD&D時）
  const replacePaneSession = useCallback(
    async (paneId: string, sessionId: string) => {
      // 既に同じセッションが別ペインにあれば何もしない
      const dup = panesRef.current.find(
        (p) => p.sessionId === sessionId && p.paneId !== paneId,
      );
      if (dup) return;

      setPanes((prev) =>
        prev.map((p) =>
          p.paneId === paneId
            ? {
                ...p,
                sessionId,
                session: null,
                messages: [],
                loading: true,
                sendError: null,
                inputValue: "",
                pastedImages: [],
              }
            : p,
        ),
      );
      setActivePaneId(paneId);
      await loadPaneData(paneId, sessionId);
    },
    [loadPaneData],
  );

  const closePane = useCallback((paneId: string) => {
    setPanes((prev) => prev.filter((p) => p.paneId !== paneId));
    setActivePaneId((prev) => {
      if (prev === paneId) {
        const remaining = panesRef.current.filter(
          (p) => p.paneId !== paneId,
        );
        return remaining.length > 0
          ? remaining[remaining.length - 1].paneId
          : null;
      }
      return prev;
    });
  }, []);

  const updatePaneSession = useCallback(
    (paneId: string, session: SessionEntry) => {
      setPanes((prev) =>
        prev.map((p) => (p.paneId === paneId ? { ...p, session } : p)),
      );
    },
    [],
  );

  const appendPaneMessages = useCallback(
    (paneId: string, ...msgs: SessionMessage[]) => {
      setPanes((prev) =>
        prev.map((p) =>
          p.paneId === paneId
            ? { ...p, messages: [...p.messages, ...msgs] }
            : p,
        ),
      );
    },
    [],
  );

  const setPaneInput = useCallback((paneId: string, value: string) => {
    setPanes((prev) =>
      prev.map((p) =>
        p.paneId === paneId ? { ...p, inputValue: value } : p,
      ),
    );
  }, []);

  const setPaneSending = useCallback(
    (paneId: string, sending: boolean, error?: string | null) => {
      setPanes((prev) =>
        prev.map((p) =>
          p.paneId === paneId
            ? { ...p, sending, sendError: error ?? p.sendError }
            : p,
        ),
      );
    },
    [],
  );

  const setPanePastedImages = useCallback(
    (
      paneId: string,
      updater: (
        prev: { data: string; preview: string }[],
      ) => { data: string; preview: string }[],
    ) => {
      setPanes((prev) =>
        prev.map((p) =>
          p.paneId === paneId
            ? { ...p, pastedImages: updater(p.pastedImages) }
            : p,
        ),
      );
    },
    [],
  );

  // メッセージ送信
  const sendPaneMessage = useCallback(
    async (paneId: string) => {
      const pane = panesRef.current.find((p) => p.paneId === paneId);
      if (!pane || !pane.session) return;

      const msg = pane.inputValue.trim();
      const hasImages = pane.pastedImages.length > 0;
      if (!msg && !hasImages) return;

      const imagesToSend = [...pane.pastedImages];

      // Optimistic: ユーザーメッセージを追加、入力クリア
      const displayContent = hasImages
        ? `${msg}${msg ? "\n\n" : ""}[画像 ${imagesToSend.length}枚添付]`
        : msg;
      const userMsg: SessionMessage = {
        message_id: `temp-${Date.now()}`,
        role: "user",
        content: displayContent,
        timestamp: new Date().toISOString(),
        tool_uses: [],
      };

      setPanes((prev) =>
        prev.map((p) =>
          p.paneId === paneId
            ? {
                ...p,
                inputValue: "",
                pastedImages: [],
                sending: true,
                sendError: null,
                messages: [...p.messages, userMsg],
              }
            : p,
        ),
      );

      try {
        const images = hasImages
          ? imagesToSend.map((img) => img.data)
          : undefined;
        const result = await sendMessage(
          pane.sessionId,
          msg,
          images,
        );
        if (result.success && result.result) {
          const assistantMsg: SessionMessage = {
            message_id: `temp-${Date.now()}-resp`,
            role: "assistant",
            content: result.result,
            timestamp: new Date().toISOString(),
            tool_uses: [],
          };
          setPanes((prev) =>
            prev.map((p) =>
              p.paneId === paneId
                ? {
                    ...p,
                    sending: false,
                    messages: [...p.messages, assistantMsg],
                    session: p.session
                      ? {
                          ...p.session,
                          message_count: p.session.message_count + 2,
                        }
                      : p.session,
                  }
                : p,
            ),
          );
        } else {
          setPaneSending(paneId, false, result.error ?? "送信失敗");
        }
      } catch {
        setPaneSending(paneId, false, "通信エラー");
      }
    },
    [setPaneSending],
  );

  // 全ペインのデータ再取得（SSE用）
  const refreshAllPanes = useCallback(async () => {
    const current = panesRef.current;
    await Promise.allSettled(
      current
        .filter((p) => !p.sending)
        .map(async (pane) => {
          try {
            const [session, msgData] = await Promise.all([
              fetchSession(pane.sessionId),
              fetchMessages(pane.sessionId),
            ]);
            setPanes((prev) =>
              prev.map((p) =>
                p.paneId === pane.paneId && !p.sending
                  ? {
                      ...p,
                      session,
                      messages: msgData.messages,
                    }
                  : p,
              ),
            );
          } catch {
            /* ignore */
          }
        }),
    );
  }, []);

  // 全ペインクリア（グループ切り替え時）
  const clearPanes = useCallback(() => {
    setPanes([]);
    setActivePaneId(null);
  }, []);

  return {
    panes,
    activePaneId,
    isEmpty: panes.length === 0,
    canAddPane: panes.length < MAX_PANES,
    openSessionIds: new Set(panes.map((p) => p.sessionId)),
    setActivePaneId,
    openPane,
    openInActivePane,
    replacePaneSession,
    closePane,
    updatePaneSession,
    appendPaneMessages,
    setPaneInput,
    setPaneSending,
    setPanePastedImages,
    sendPaneMessage,
    refreshAllPanes,
    clearPanes,
  };
}
