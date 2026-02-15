import { useCallback, useState } from "react";
import { GroupBar } from "./components/GroupBar";
import { Sidebar } from "./components/Sidebar";
import { MessageArea } from "./components/MessageArea";
import { ProjectOverview } from "./components/ProjectOverview";
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
    selectGroup,
    openSession,
    refresh,
    setSelectedSession,
  } = useGroups();

  const [searchOpen, setSearchOpen] = useState(false);

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
    if (selectedGroupId) {
      await selectGroup(selectedGroupId);
    }
  }, [selectedGroupId, selectGroup]);

  return (
    <div className="h-screen flex overflow-hidden bg-slack-bg text-slack-text font-sans">
      <GroupBar
        groups={groups}
        selectedGroupId={selectedGroupId}
        onSelectGroup={selectGroup}
        onSearchOpen={() => setSearchOpen(true)}
      />

      <Sidebar
        groupDetail={groupDetail}
        selectedSessionId={selectedSessionId}
        onOpenSession={openSession}
      />

      {/* Main area */}
      {selectedSession ? (
        <MessageArea
          session={selectedSession}
          messages={messages}
          loading={messagesLoading}
          onSessionUpdate={setSelectedSession}
          onRefreshGroup={handleRefreshGroup}
        />
      ) : groupDetail ? (
        <ProjectOverview group={groupDetail} onOpenSession={openSession} />
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
