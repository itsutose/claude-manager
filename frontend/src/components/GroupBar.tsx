import type { ProjectGroup } from "../types";

interface Props {
  groups: ProjectGroup[];
  selectedGroupId: string | null;
  onSelectGroup: (groupId: string) => void;
  onSelectHome: () => void;
  onSearchOpen: () => void;
}

export function GroupBar({
  groups,
  selectedGroupId,
  onSelectGroup,
  onSelectHome,
  onSearchOpen,
}: Props) {
  const isHome = selectedGroupId === null;

  return (
    <div className="w-[52px] bg-[#0f0e11] flex flex-col items-center py-2 gap-1 border-r border-slack-border/50 shrink-0">
      {/* Home button */}
      <button
        onClick={onSelectHome}
        className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold cursor-pointer transition-colors ${
          isHome
            ? "bg-slack-accent text-white"
            : "bg-[#35373b] text-slack-muted hover:bg-slack-hover hover:text-white"
        }`}
        title="ホーム"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
          />
        </svg>
      </button>

      <div className="w-6 h-px bg-slack-border/50 my-0.5" />

      {groups.map((g) => (
        <button
          key={g.group_id}
          onClick={() => onSelectGroup(g.group_id)}
          className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold cursor-pointer transition-colors relative ${
            selectedGroupId === g.group_id
              ? "bg-slack-accent text-white"
              : "bg-[#35373b] text-slack-muted hover:bg-slack-hover hover:text-white"
          }`}
          title={g.display_name}
        >
          {g.initials}
          {g.active_sessions > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-[#0f0e11]" />
          )}
        </button>
      ))}

      <div className="flex-1" />

      <button
        onClick={onSearchOpen}
        className="w-9 h-9 rounded-lg flex items-center justify-center text-slack-muted hover:bg-slack-hover hover:text-white cursor-pointer transition-colors"
        title="検索 (Cmd+K)"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </button>
    </div>
  );
}
