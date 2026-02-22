import { useCallback, useRef, useState } from "react";
import { GroupBar } from "./components/GroupBar";
import { Sidebar } from "./components/Sidebar";
import { MessageArea } from "./components/MessageArea";
import { ProjectOverview } from "./components/ProjectOverview";
import { Dashboard } from "./components/Dashboard";
import { SearchModal } from "./components/SearchModal";
import { useGroups } from "./hooks/useGroups";
import { useSSE } from "./hooks/useSSE";
import { createSession } from "./api";

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

  const [searchOpen, setSearchOpen] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [creatingCloneId, setCreatingCloneId] = useState<string | null>(null);
  const draftMap = useRef<Map<string, string>>(new Map());

  useSSE(refresh);

  const handleSearchResult = useCallback(
    async (groupId: string, sessionId: string) => {
      if (selectedGroupId !== groupId) {
        await selectGroup(groupId);
      }
      await openSession(sessionId);
    },
    [selectedGroupId, selectGroup, openSession],
  );

  const handleRefreshGroup = useCallback(async () => {
    await refreshGroupDetail();
  }, [refreshGroupDetail]);

  const handleNewSession = useCallback((cloneId: string) => {
    setIsCreatingSession(true);
    setCreatingCloneId(cloneId);
    // セッション選択を解除して ProjectOverview を表示
    clearSession();
  }, [clearSession]);

  const handleCreateSession = useCallback(
    async (message: string, images?: string[]) => {
      if (!selectedGroupId || !creatingCloneId) return;
      const result = await createSession(selectedGroupId, creatingCloneId, message, images);
      if (!result.success) {
        throw new Error(result.error ?? "セッション作成に失敗しました");
      }
      setIsCreatingSession(false);
      setCreatingCloneId(null);
      // グループデータ再読み込み → 新セッションを開く
      await refreshGroupDetail();
      if (result.session_id) {
        await openSession(result.session_id);
      }
    },
    [selectedGroupId, creatingCloneId, refreshGroupDetail, openSession],
  );

  const handleCancelCreate = useCallback(() => {
    setIsCreatingSession(false);
    setCreatingCloneId(null);
  }, []);

  return (
    <div className="h-screen flex overflow-hidden bg-slack-bg text-slack-text font-sans">
      <GroupBar
        groups={groups}
        selectedGroupId={selectedGroupId}
        onSelectGroup={selectGroup}
        onSelectHome={selectHome}
        onSearchOpen={() => setSearchOpen(true)}
      />

      {selectedGroupId && (
        <Sidebar
          groupDetail={groupDetail}
          selectedSessionId={selectedSessionId}
          onOpenSession={openSession}
          onRefreshGroup={handleRefreshGroup}
          onNewSession={handleNewSession}
        />
      )}

      {/* Main area */}
      {selectedSession ? (
        <MessageArea
          key={selectedSession.session_id}
          session={selectedSession}
          messages={messages}
          loading={messagesLoading}
          onSessionUpdate={setSelectedSession}
          onRefreshGroup={handleRefreshGroup}
          onAppendMessages={appendMessages}
          initialInputValue={draftMap.current.get(selectedSession.session_id) ?? ""}
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
          onOpenSession={openSession}
          isCreatingSession={isCreatingSession}
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

      <SearchModal
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelectResult={handleSearchResult}
      />
    </div>
  );
}
