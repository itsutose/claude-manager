import type { SessionStatus } from "./types";

export function statusColor(status: SessionStatus): string {
  const map: Record<SessionStatus, string> = {
    active: "bg-green-500",
    recent: "bg-yellow-500",
    idle: "bg-gray-500",
    archived: "bg-gray-700",
  };
  return map[status] ?? "bg-gray-600";
}

export function timeAgo(isoStr: string | null): string {
  if (!isoStr) return "";
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "たった今";
  if (mins < 60) return `${mins}分前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}時間前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}日前`;
  const months = Math.floor(days / 30);
  return `${months}ヶ月前`;
}

export function formatDate(isoStr: string | null): string {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function formatDateFull(isoStr: string | null): string {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日（${weekdays[d.getDay()]}）`;
}

export function formatTime(isoStr: string | null): string {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  return `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/** Markdownテーブル行群をHTMLテーブルに変換 */
function renderTable(lines: string[]): string {
  const parseRow = (line: string): string[] =>
    line.split("|").slice(1, -1).map((c) => c.trim());

  const headers = parseRow(lines[0]);
  // lines[1] はセパレーター (---|---) なのでスキップ
  const bodyRows = lines.slice(2).map(parseRow);

  const thCells = headers
    .map(
      (h) =>
        `<th class="px-3 py-1.5 text-left text-xs font-bold text-white border border-slack-border/30">${h}</th>`,
    )
    .join("");
  const tbodyRows = bodyRows
    .map(
      (cells) =>
        `<tr>${cells.map((c) => `<td class="px-3 py-1.5 text-xs text-slack-text border border-slack-border/30">${c}</td>`).join("")}</tr>`,
    )
    .join("");

  return `<table class="border-collapse border border-slack-border/30 my-2 w-full overflow-x-auto"><thead class="bg-[#16181c]"><tr>${thCells}</tr></thead><tbody>${tbodyRows}</tbody></table>`;
}

export function renderContent(text: string): string {
  if (!text) return "";
  let html = escapeHtml(text);
  // Code blocks
  html = html.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    '<pre class="bg-[#16181c] rounded-md p-3 my-2 text-sm overflow-x-auto border border-slack-border/30"><code>$2</code></pre>',
  );
  // Inline code
  html = html.replace(
    /`([^`]+)`/g,
    '<code class="bg-[#35373b] px-1.5 py-0.5 rounded text-sm text-pink-300">$1</code>',
  );
  // Bold
  html = html.replace(
    /\*\*(.+?)\*\*/g,
    '<strong class="text-white font-bold">$1</strong>',
  );
  // Markdown tables (must be before newline conversion)
  html = html.replace(
    /(?:^|\n)(\|.+\|)\n(\|[\s:|-]+\|)\n((?:\|.+\|\n?)+)/g,
    (_match, headerLine, _sepLine, bodyBlock) => {
      const bodyLines = bodyBlock.trim().split("\n");
      const allLines = [headerLine, _sepLine, ...bodyLines];
      return "\n" + renderTable(allLines);
    },
  );
  // Newlines
  html = html.replace(/\n/g, "<br>");
  return html;
}
