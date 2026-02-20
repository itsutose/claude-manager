import { useDashboard } from "../hooks/useDashboard";
import { useSSE } from "../hooks/useSSE";
import { DashboardColumn } from "./DashboardColumn";

export function Dashboard() {
  const {
    columns,
    allSessions,
    isLoading,
    switchColumn,
    removeColumn,
    setColumnInput,
    sendColumnMessage,
    refreshDashboard,
  } = useDashboard();

  useSSE(refreshDashboard);

  // Skeleton columns during initial load
  if (isLoading && columns.length === 0) {
    return (
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-5 py-3 border-b border-slack-border/50 shrink-0">
          <h2 className="text-white font-bold text-[15px]">ダッシュボード</h2>
          <div className="text-xs text-slack-muted mt-0.5">読み込み中...</div>
        </div>
        <div className="flex-1 flex gap-3 p-3 overflow-x-auto">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="w-[340px] shrink-0 bg-slack-sidebar rounded-lg border border-slack-border/50 animate-pulse"
            >
              <div className="px-3 py-3 border-b border-slack-border/50">
                <div className="h-4 bg-[#35373b] rounded w-3/4" />
                <div className="h-2.5 bg-[#35373b] rounded w-1/2 mt-1.5" />
              </div>
              <div className="p-3 space-y-3">
                {[0, 1, 2].map((j) => (
                  <div key={j} className="flex gap-2">
                    <div className="w-5 h-5 bg-[#35373b] rounded" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-2.5 bg-[#35373b] rounded w-1/3" />
                      <div className="h-2.5 bg-[#35373b] rounded w-full" />
                      <div className="h-2.5 bg-[#35373b] rounded w-2/3" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (allSessions.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slack-muted">
        セッションがありません
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slack-border/50 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-white font-bold text-[15px]">ダッシュボード</h2>
            <div className="text-xs text-slack-muted mt-0.5">
              {columns.filter((c) => c.session?.status === "active").length} アクティブ
              {" / "}
              {columns.length} カラム
            </div>
          </div>
        </div>
      </div>

      {/* Columns */}
      <div className="flex-1 flex gap-3 p-3 overflow-x-auto min-h-0">
        {columns.map((col, i) => {
          const otherIds = new Set(
            columns
              .filter((_, j) => j !== i)
              .map((c) => c.sessionId),
          );
          return (
            <DashboardColumn
              key={col.sessionId}
              column={col}
              columnIndex={i}
              allSessions={allSessions}
              otherColumnIds={otherIds}
              onSwitch={switchColumn}
              onRemove={removeColumn}
              onInputChange={setColumnInput}
              onSend={sendColumnMessage}
            />
          );
        })}
      </div>
    </div>
  );
}
