import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  statusColor,
  timeAgo,
  formatDate,
  formatDateFull,
  formatTime,
  renderContent,
} from "./helpers";

describe("statusColor", () => {
  it("returns green for active", () => {
    expect(statusColor("active")).toBe("bg-green-500");
  });

  it("returns yellow for recent", () => {
    expect(statusColor("recent")).toBe("bg-yellow-500");
  });

  it("returns gray for idle", () => {
    expect(statusColor("idle")).toBe("bg-gray-500");
  });

  it("returns dark gray for archived", () => {
    expect(statusColor("archived")).toBe("bg-gray-700");
  });

  it("returns fallback for unknown status", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(statusColor("unknown" as any)).toBe("bg-gray-600");
  });
});

describe("timeAgo", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-01-15T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns empty for null", () => {
    expect(timeAgo(null)).toBe("");
  });

  it("returns たった今 for just now", () => {
    expect(timeAgo("2025-01-15T12:00:00Z")).toBe("たった今");
  });

  it("returns minutes ago", () => {
    expect(timeAgo("2025-01-15T11:30:00Z")).toBe("30分前");
  });

  it("returns hours ago", () => {
    expect(timeAgo("2025-01-15T07:00:00Z")).toBe("5時間前");
  });

  it("returns days ago", () => {
    expect(timeAgo("2025-01-10T12:00:00Z")).toBe("5日前");
  });

  it("returns months ago", () => {
    expect(timeAgo("2024-10-15T12:00:00Z")).toBe("3ヶ月前");
  });
});

describe("formatDate", () => {
  it("returns empty for null", () => {
    expect(formatDate(null)).toBe("");
  });

  it("formats date correctly", () => {
    // UTC+9 (JST) を考慮
    const result = formatDate("2025-06-15T03:05:00Z");
    // ローカルタイムゾーン依存のため、フォーマットパターンのみ確認
    expect(result).toMatch(/\d{1,2}\/\d{1,2} \d{1,2}:\d{2}/);
  });
});

describe("formatDateFull", () => {
  it("returns empty for null", () => {
    expect(formatDateFull(null)).toBe("");
  });

  it("contains year, month, day and weekday", () => {
    const result = formatDateFull("2025-01-15T00:00:00Z");
    expect(result).toContain("年");
    expect(result).toContain("月");
    expect(result).toContain("日");
    expect(result).toMatch(/[日月火水木金土]/);
  });
});

describe("formatTime", () => {
  it("returns empty for null", () => {
    expect(formatTime(null)).toBe("");
  });

  it("formats time correctly", () => {
    const result = formatTime("2025-01-15T03:05:00Z");
    expect(result).toMatch(/\d{1,2}:\d{2}/);
  });
});

describe("renderContent", () => {
  it("returns empty for empty string", () => {
    expect(renderContent("")).toBe("");
  });

  it("escapes HTML", () => {
    const result = renderContent("<script>alert(1)</script>");
    expect(result).not.toContain("<script>");
  });

  it("converts inline code", () => {
    const result = renderContent("use `npm install`");
    expect(result).toContain("<code");
    expect(result).toContain("npm install");
  });

  it("converts bold text", () => {
    const result = renderContent("this is **bold** text");
    expect(result).toContain("<strong");
    expect(result).toContain("bold");
  });

  it("converts newlines to br", () => {
    const result = renderContent("line1\nline2");
    expect(result).toContain("<br>");
  });
});
