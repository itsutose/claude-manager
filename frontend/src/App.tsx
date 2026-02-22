import { useCallback, useRef, useState } from "react";
import { GroupBar } from "./components/GroupBar";
import { Sidebar } from "./components/Sidebar";
import { MessageArea } from "./components/MessageArea";
import { ProjectOverview } from "./components/ProjectOverview";
import { Dashboard } from "./components/Dashboard";
import { SearchModal } from "./components/SearchModal";
import { useGroups } from "./hooks/useGroups";
import { useSSE } from "./hooks/useSSE";

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
    appendMessages,
    refreshGroupDetail,
  } = useGroups();

  const [searchOpen, setSearchOpen] = useState(false);
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
        />
      ) : groupDetail ? (
        <ProjectOverview group={groupDetail} onOpenSession={openSession} />
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
