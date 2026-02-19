import type { ProjectGroupDetail } from "../types";
import { timeAgo, statusColor } from "../helpers";
import { AssetsPanel } from "./AssetsPanel";

interface Props {
  group: ProjectGroupDetail;
  onOpenSession: (sessionId: string) => void;
}

export function ProjectOverview({ group, onOpenSession }: Props) {
  const recentSessions = group.clones
    .flatMap((c) => c.sessions.map((s) => ({ ...s, clone_name: c.clone_name })))
    .sort(
      (a, b) =>
        new Date(b.modified).getTime() - new Date(a.modified).getTime(),
    )
    .slice(0, 10);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h2 className="text-2xl font-bold text-white mb-6">
        {group.display_name}
      </h2>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="border border-slack-border/50 rounded-lg p-4">
          <div className="text-slack-muted text-xs mb-1">総セッション</div>
          <div className="text-2xl font-bold text-white">
            {group.total_sessions}
          </div>
        </div>
        <div className="border border-slack-border/50 rounded-lg p-4">
          <div className="text-slack-muted text-xs mb-1">アクティブ</div>
          <div className="text-2xl font-bold text-green-400">
            {group.active_sessions}
          </div>
        </div>
        <div className="border border-slack-border/50 rounded-lg p-4">
          <div className="text-slack-muted text-xs mb-1">総メッセージ</div>
          <div className="text-2xl font-bold text-white">
            {group.total_messages}
          </div>
        </div>
      </div>

      {/* Clones */}
      <h3 className="text-lg font-bold text-white mb-3">クローン別状況</h3>
      <div className="space-y-2 mb-8">
        {group.clones.map((clone) => (
          <div
            key={clone.clone_id}
            className="flex items-center justify-between border border-slack-border/50 rounded-lg px-4 py-3"
          >
            <div>
              <div className="text-white font-medium">{clone.clone_name}</div>
              <div className="text-xs text-slack-muted">
                {clone.session_count} sessions
                {clone.current_branch
                  ? ` | branch: ${clone.current_branch}`
                  : ""}
              </div>
            </div>
            <div className="text-xs text-slack-muted">
              {timeAgo(clone.latest_modified)}
            </div>
          </div>
        ))}
      </div>

      {/* Assets */}
      <h3 className="text-lg font-bold text-white mb-3">プロジェクト設定</h3>
      <div className="mb-8">
        <AssetsPanel groupId={group.group_id} />
      </div>

      {/* Recent */}
      <h3 className="text-lg font-bold text-white mb-3">最近のセッション</h3>
      <div className="space-y-1">
        {recentSessions.map((s) => (
          <button
            key={s.session_id}
            onClick={() => onOpenSession(s.session_id)}
            className="w-full flex items-center gap-3 px-4 py-2 rounded-lg hover:bg-slack-hover text-left"
          >
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${statusColor(s.status)}`}
            />
            <div className="min-w-0 flex-1">
              <div className="text-sm text-white truncate">
                {s.display_name}
              </div>
              <div className="text-xs text-slack-muted">{s.clone_name}</div>
            </div>
            <div className="text-xs text-slack-muted shrink-0">
              {timeAgo(s.modified)}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
