import { useEffect, useRef, useState } from "react";
import type { SearchResult } from "../types";
import { searchSessions } from "../api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSelectResult: (groupId: string, sessionId: string) => void;
}

export function SearchModal({ open, onClose, onSelectResult }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
      setQuery("");
      setResults([]);
    }
  }, [open]);

  const handleInput = (value: string) => {
    setQuery(value);
    clearTimeout(timerRef.current);
    if (!value.trim()) {
      setResults([]);
      return;
    }
    timerRef.current = setTimeout(async () => {
      const data = await searchSessions(value);
      setResults(data);
    }, 300);
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (open) onClose();
        else {
          // will be triggered from parent
        }
      }
      if (e.key === "Escape" && open) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20">
      <div className="fixed inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-[#222529] rounded-lg shadow-2xl w-[600px] max-h-[500px] border border-slack-border">
        <div className="p-4">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => handleInput(e.target.value)}
            placeholder="セッションを検索..."
            className="w-full bg-[#35373b] text-white px-4 py-2.5 rounded-lg border border-slack-border focus:outline-none focus:border-slack-accent text-sm"
          />
        </div>
        {results.length > 0 && (
          <div className="border-t border-slack-border max-h-[380px] overflow-y-auto">
            {results.map((r) => (
              <button
                key={r.session_id}
                onClick={() => {
                  onSelectResult(r.group_id, r.session_id);
                  onClose();
                }}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slack-hover text-left"
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-white truncate">
                    {r.display_name}
                  </div>
                  <div className="text-xs text-slack-muted truncate">
                    {r.group_name} / {r.clone_name}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
        {query && results.length === 0 && (
          <div className="border-t border-slack-border p-8 text-center text-slack-muted text-sm">
            結果なし
          </div>
        )}
      </div>
    </div>
  );
}
