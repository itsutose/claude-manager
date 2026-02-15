import { useEffect, useState } from "react";
import type { ProjectAssets, AssetFile } from "../types";
import { fetchGroupAssets } from "../api";
import { renderContent } from "../helpers";

interface Props {
  groupId: string;
}

type Tab = "claude_md" | "rules" | "skills";

export function AssetsPanel({ groupId }: Props) {
  const [assets, setAssets] = useState<ProjectAssets | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("claude_md");
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setAssets(null);
    fetchGroupAssets(groupId)
      .then((data) => {
        // エラーレスポンスの場合はnullのまま
        if ("error" in data) return;
        setAssets(data);
      })
      .finally(() => setLoading(false));
  }, [groupId]);

  if (loading) {
    return <div className="text-slack-muted text-sm p-4">読み込み中...</div>;
  }
  if (!assets) return null;

  // タブごとのデータ構築
  const claudeMdFiles: AssetFile[] = [];
  if (assets.claude_md) {
    claudeMdFiles.push({ name: "CLAUDE.md (local)", path: "CLAUDE.md", content: assets.claude_md });
  }
  if (assets.global_claude_md) {
    claudeMdFiles.push({ name: "CLAUDE.md (global)", path: "~/.claude/CLAUDE.md", content: assets.global_claude_md });
  }

  const ruleFiles = [
    ...assets.local_rules.map((r) => ({ ...r, name: r.name + " (local)" })),
    ...assets.global_rules.map((r) => ({ ...r, name: r.name + " (global)" })),
  ];

  const skillFiles = assets.local_skills;

  const tabs: { key: Tab; label: string; items: AssetFile[] }[] = [
    { key: "claude_md", label: "CLAUDE.md", items: claudeMdFiles },
    { key: "rules", label: "Rules", items: ruleFiles },
    { key: "skills", label: "Skills", items: skillFiles },
  ];

  const currentItems = tabs.find((t) => t.key === activeTab)?.items ?? [];

  return (
    <div className="border border-slack-border/50 rounded-lg overflow-hidden">
      {/* Tabs */}
      <div className="flex border-b border-slack-border/50 bg-[#1e2024]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setActiveTab(tab.key);
              setExpandedFile(null);
            }}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? "text-white border-b-2 border-slack-accent"
                : "text-slack-muted hover:text-white"
            }`}
          >
            {tab.label}
            {tab.items.length > 0 && (
              <span className="ml-1 text-[10px] text-slack-muted">
                ({tab.items.length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="max-h-[400px] overflow-y-auto">
        {currentItems.length === 0 ? (
          <div className="p-4 text-sm text-slack-muted">なし</div>
        ) : (
          currentItems.map((item) => {
            const isExpanded = expandedFile === item.path;
            return (
              <div key={item.path} className="border-b border-slack-border/30 last:border-b-0">
                <button
                  onClick={() =>
                    setExpandedFile(isExpanded ? null : item.path)
                  }
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-left hover:bg-slack-hover transition-colors"
                >
                  <svg
                    className={`w-3 h-3 text-slack-muted transition-transform shrink-0 ${isExpanded ? "" : "-rotate-90"}`}
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                    />
                  </svg>
                  <span className="text-white">{item.name}</span>
                </button>
                {isExpanded && (
                  <div className="px-4 py-3 bg-[#16181c] border-t border-slack-border/30">
                    <div
                      className="message-content text-xs text-slack-text leading-relaxed whitespace-pre-wrap"
                      dangerouslySetInnerHTML={{
                        __html: renderContent(item.content),
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
