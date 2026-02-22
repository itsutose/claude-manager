import { useRef, useState } from "react";
import type { ProjectGroupDetail } from "../types";
import { timeAgo, statusColor } from "../helpers";
import { AssetsPanel } from "./AssetsPanel";

interface Props {
  group: ProjectGroupDetail;
  onOpenSession: (sessionId: string) => void;
  isCreatingSession?: boolean;
  onCreateSession?: (message: string, images?: string[]) => Promise<void>;
  onCancelCreate?: () => void;
}

function NewSessionForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (message: string, images?: string[]) => Promise<void>;
  onCancel: () => void;
}) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pastedImages, setPastedImages] = useState<
    { data: string; preview: string }[]
  >([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handlePaste = (e: React.ClipboardEvent) => {
    if (sending) return;

    const files = e.clipboardData.files;
    if (files.length > 0) {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!file.type.startsWith("image/")) continue;
        e.preventDefault();
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = reader.result as string;
          setPastedImages((prev) => [
            ...prev,
            { data: dataUrl, preview: dataUrl },
          ]);
        };
        reader.readAsDataURL(file);
      }
      return;
    }

    const items = Array.from(e.clipboardData.items);
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (!file) continue;
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = reader.result as string;
          setPastedImages((prev) => [
            ...prev,
            { data: dataUrl, preview: dataUrl },
          ]);
        };
        reader.readAsDataURL(file);
      }
    }
  };

  const removeImage = (index: number) => {
    setPastedImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    const trimmed = message.trim();
    const hasImages = pastedImages.length > 0;
    if ((!trimmed && !hasImages) || sending) return;
    setSending(true);
    setError(null);
    try {
      const images = hasImages
        ? pastedImages.map((img) => img.data)
        : undefined;
      await onSubmit(trimmed, images);
    } catch (e) {
      setError(e instanceof Error ? e.message : "送信に失敗しました");
      setSending(false);
    }
  };

  return (
    <div className="border border-slack-accent/50 rounded-lg p-4 mb-6 bg-[#2b2d31]">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-white font-bold text-sm">新規セッション</h3>
        <button
          onClick={onCancel}
          className="text-slack-muted hover:text-white text-xs"
        >
          キャンセル
        </button>
      </div>
      {pastedImages.length > 0 && (
        <div className="flex gap-2 mb-2 flex-wrap">
          {pastedImages.map((img, i) => (
            <div key={i} className="relative group">
              <img
                src={img.preview}
                alt={`添付画像 ${i + 1}`}
                className="w-16 h-16 object-cover rounded border border-slack-border/50"
              />
              <button
                onClick={() => removeImage(i)}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}
      <textarea
        ref={textareaRef}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            handleSubmit();
          }
          if (e.key === "Escape") {
            onCancel();
          }
        }}
        onPaste={handlePaste}
        placeholder="メッセージを入力...（画像ペースト可）"
        className="w-full bg-[#35373b] text-white text-sm px-3 py-2 rounded border border-transparent focus:outline-none focus:border-slack-accent/50 resize-none"
        rows={4}
        autoFocus
        disabled={sending}
      />
      {error && (
        <div className="text-red-400 text-xs mt-2">{error}</div>
      )}
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-slack-muted">
          Cmd+Enter で送信 / 画像はペーストで添付
        </span>
        <button
          onClick={handleSubmit}
          disabled={!message.trim() && pastedImages.length === 0 || sending}
          className="px-4 py-1.5 bg-slack-accent text-white text-sm rounded font-medium hover:bg-slack-accent/80 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {sending && (
            <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
          {sending ? "送信中..." : "送信"}
        </button>
      </div>
    </div>
  );
}

export function ProjectOverview({
  group,
  onOpenSession,
  isCreatingSession,
  onCreateSession,
  onCancelCreate,
}: Props) {
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

      {/* New Session Form */}
      {isCreatingSession && onCreateSession && onCancelCreate && (
        <NewSessionForm
          onSubmit={onCreateSession}
          onCancel={onCancelCreate}
        />
      )}

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
