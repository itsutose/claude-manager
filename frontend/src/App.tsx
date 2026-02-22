import { useCallback, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  pointerWithin,
  useDroppable,
  useSensors,
  useSensor,
  MouseSensor,
  TouchSensor,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import { GroupBar } from "./components/GroupBar";
import { Sidebar } from "./components/Sidebar";
import { MessageArea } from "./components/MessageArea";
import { ProjectOverview } from "./components/ProjectOverview";
import { Dashboard } from "./components/Dashboard";
import { SearchModal } from "./components/SearchModal";
import { SplitView } from "./components/SplitView";
import { useGroups } from "./hooks/useGroups";
import { useSSE } from "./hooks/useSSE";
import { useResizable } from "./hooks/useResizable";
import { useSplitView } from "./hooks/useSplitView";
import { createSession } from "./api";
import type { SessionEntry } from "./types";

/** ドラッグ中にメインエリア全体をドロップ可能にするオーバーレイ */
function MainDropOverlay({ isDragging }: { isDragging: boolean }) {
  const { isOver, setNodeRef } = useDroppable({ id: "split-drop-zone" });

  if (!isDragging) return null;

  return (
    <div
      ref={setNodeRef}
      className={`absolute inset-0 z-40 flex items-center justify-center border-2 border-dashed rounded-lg transition-colors ${
        isOver
          ? "border-slack-accent bg-slack-accent/10"
          : "border-slack-border/50 bg-slack-bg/50"
      }`}
    >
      <div
        className={`text-lg font-bold ${
          isOver ? "text-slack-accent" : "text-slack-muted/60"
        }`}
      >
        ここにドロップしてペインを追加
      </div>
    </div>
  );
}

export default function App() {
  const {
    groups,
    selectedGroupId,
    groupDetail,
    selectedSessionId,
    selectedSession,
    messages,
    messagesLoading,
    selectHome,
    selectGroup,
    openSession,
    refresh,
    setSelectedSession,
    clearSession,
    appendMessages,
    refreshGroupDetail,
  } = useGroups();

  const splitView = useSplitView();

  const [searchOpen, setSearchOpen] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [creatingCloneId, setCreatingCloneId] = useState<string | null>(null);
  const draftMap = useRef<Map<string, string>>(new Map());
  const [draggedSession, setDraggedSession] = useState<SessionEntry | null>(
    null,
  );

  // DnD sensors: 8px distance to distinguish click from drag
  const sensors = useSensors(
    useSensor(MouseSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(TouchSensor, {
      activationConstraint: { distance: 8 },
    }),
  );

  // SSE: refresh both groups and split view panes
  const handleSSERefresh = useCallback(async () => {
    await refresh();
    if (!splitView.isEmpty) {
      await splitView.refreshAllPanes();
    }
  }, [refresh, splitView]);

  useSSE(handleSSERefresh);
  const { width: sidebarWidth, onMouseDown: onResizeStart } = useResizable();

  // --- Session open logic ---
  // サイドバークリック時: スプリットビューにペインがあればアクティブペインで開く
  const handleOpenSession = useCallback(
    async (sessionId: string) => {
      if (!splitView.isEmpty) {
        await splitView.openInActivePane(sessionId);
        // useGroupsのselectedSessionはクリア（SplitView側で管理）
        clearSession();
      } else {
        await openSession(sessionId);
      }
    },
    [splitView, clearSession, openSession],
  );

  // --- DnD handlers ---
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const session = event.active.data.current?.session as
      | SessionEntry
      | undefined;
    setDraggedSession(session ?? null);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setDraggedSession(null);
      if (!over) return;

      const session = active.data.current?.session as
        | SessionEntry
        | undefined;
      if (!session) return;
      const sessionId = session.session_id;

      if (over.id === "split-drop-zone") {
        // 新しいペインを追加
        splitView.openPane(sessionId);
        clearSession();
      } else if (
        typeof over.id === "string" &&
        over.id.startsWith("pane-replace-")
      ) {
        // 既存ペインのセッションを入れ替え
        const targetPaneId = over.id.replace("pane-replace-", "");
        splitView.replacePaneSession(targetPaneId, sessionId);
        clearSession();
      }
    },
    [splitView, clearSession],
  );

  const handleDragCancel = useCallback(() => {
    setDraggedSession(null);
  }, []);

  // --- Other handlers ---
  const handleSearchResult = useCallback(
    async (groupId: string, sessionId: string) => {
      if (selectedGroupId !== groupId) {
        await selectGroup(groupId);
        splitView.clearPanes();
      }
      if (!splitView.isEmpty) {
        await splitView.openInActivePane(sessionId);
      } else {
        await openSession(sessionId);
      }
    },
    [selectedGroupId, selectGroup, openSession, splitView],
  );

  const handleRefreshGroup = useCallback(async () => {
    await refreshGroupDetail();
  }, [refreshGroupDetail]);

  const handleSelectGroup = useCallback(
    async (groupId: string) => {
      await selectGroup(groupId);
      splitView.clearPanes();
    },
    [selectGroup, splitView],
  );

  const handleSelectHome = useCallback(() => {
    selectHome();
    splitView.clearPanes();
  }, [selectHome, splitView]);

  const handleNewSession = useCallback(
    (cloneId: string) => {
      setIsCreatingSession(true);
      setCreatingCloneId(cloneId);
      clearSession();
    },
    [clearSession],
  );

  const handleCreateSession = useCallback(
    async (message: string, images?: string[]) => {
      if (!selectedGroupId || !creatingCloneId) return;
      const result = await createSession(
        selectedGroupId,
        creatingCloneId,
        message,
        images,
      );
      if (!result.success) {
        throw new Error(result.error ?? "セッション作成に失敗しました");
      }
      setIsCreatingSession(false);
      setCreatingCloneId(null);
      await refreshGroupDetail();
      if (result.session_id) {
        if (!splitView.isEmpty) {
          await splitView.openInActivePane(result.session_id);
        } else {
          await openSession(result.session_id);
        }
      }
    },
    [
      selectedGroupId,
      creatingCloneId,
      refreshGroupDetail,
      openSession,
      splitView,
    ],
  );

  const handleCancelCreate = useCallback(() => {
    setIsCreatingSession(false);
    setCreatingCloneId(null);
  }, []);

  // アクティブペインのsessionIdをSidebarのselectedに反映
  const sidebarSelectedId = !splitView.isEmpty
    ? splitView.panes.find((p) => p.paneId === splitView.activePaneId)
        ?.sessionId ?? null
    : selectedSessionId;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={pointerWithin}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div className="h-screen flex overflow-hidden bg-slack-bg text-slack-text font-sans">
        <GroupBar
          groups={groups}
          selectedGroupId={selectedGroupId}
          onSelectGroup={handleSelectGroup}
          onSelectHome={handleSelectHome}
          onSearchOpen={() => setSearchOpen(true)}
        />

        {selectedGroupId && (
          <>
            <Sidebar
              groupDetail={groupDetail}
              selectedSessionId={sidebarSelectedId}
              onOpenSession={handleOpenSession}
              onRefreshGroup={handleRefreshGroup}
              onNewSession={handleNewSession}
              width={sidebarWidth}
            />
            {/* Resize handle */}
            <div
              onMouseDown={onResizeStart}
              className="w-1.5 shrink-0 cursor-col-resize hover:bg-slack-accent/40 active:bg-slack-accent/60 transition-colors"
            />
          </>
        )}

        {/* Main area */}
        {!splitView.isEmpty ? (
          <SplitView
            panes={splitView.panes}
            activePaneId={splitView.activePaneId}
            canAddPane={splitView.canAddPane}
            isDragging={draggedSession !== null}
            onActivate={splitView.setActivePaneId}
            onClose={splitView.closePane}
            onSessionUpdate={splitView.updatePaneSession}
            onRefreshGroup={handleRefreshGroup}
            onInputChange={splitView.setPaneInput}
            onSend={splitView.sendPaneMessage}
            onPasteImages={splitView.setPanePastedImages}
          />
        ) : (
          <div className="flex-1 flex flex-col min-w-0 min-h-0 relative">
            {/* ドラッグ中のドロップオーバーレイ */}
            {selectedGroupId && (
              <MainDropOverlay isDragging={draggedSession !== null} />
            )}

            {selectedSession ? (
              <MessageArea
                key={selectedSession.session_id}
                session={selectedSession}
                messages={messages}
                loading={messagesLoading}
                onSessionUpdate={setSelectedSession}
                onRefreshGroup={handleRefreshGroup}
                onAppendMessages={appendMessages}
                initialInputValue={
                  draftMap.current.get(selectedSession.session_id) ?? ""
                }
                onInputValueChange={(v) => {
                  if (v) {
                    draftMap.current.set(selectedSession.session_id, v);
                  } else {
                    draftMap.current.delete(selectedSession.session_id);
                  }
                }}
              />
            ) : groupDetail ? (
              <ProjectOverview
                group={groupDetail}
                onOpenSession={handleOpenSession}
                isCreatingSession={isCreatingSession}
                creatingCloneName={
                  creatingCloneId
                    ? groupDetail.clones.find((c) => c.clone_id === creatingCloneId)?.clone_name ?? null
                    : null
                }
                onCreateSession={handleCreateSession}
                onCancelCreate={handleCancelCreate}
              />
            ) : selectedGroupId === null ? (
              <Dashboard />
            ) : (
              <div className="flex-1 flex items-center justify-center text-slack-muted">
                プロジェクトを選択してください
              </div>
            )}
          </div>
        )}
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {draggedSession && (
          <div className="bg-slack-sidebar border border-slack-accent rounded px-3 py-2 text-sm text-white shadow-lg opacity-90 max-w-[200px] truncate">
            # {draggedSession.display_name}
          </div>
        )}
      </DragOverlay>

      <SearchModal
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelectResult={handleSearchResult}
      />
    </DndContext>
  );
}
