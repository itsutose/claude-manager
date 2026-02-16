import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchGroups,
  fetchGroupDetail,
  fetchSession,
  fetchMessages,
  searchSessions,
  togglePin,
  renameSession,
  hideSession,
} from "./api";

// fetch をモック
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function mockJsonResponse(data: unknown) {
  return {
    json: () => Promise.resolve(data),
    ok: true,
    status: 200,
  };
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("fetchGroups", () => {
  it("returns groups array", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ groups: [{ group_id: "g1" }] }),
    );
    const result = await fetchGroups();
    expect(result).toEqual([{ group_id: "g1" }]);
    expect(mockFetch).toHaveBeenCalledWith("/api/groups");
  });

  it("returns empty array when no groups", async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({}));
    const result = await fetchGroups();
    expect(result).toEqual([]);
  });
});

describe("fetchGroupDetail", () => {
  it("calls correct URL with encoding", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ group_id: "my project" }),
    );
    await fetchGroupDetail("my project");
    expect(mockFetch).toHaveBeenCalledWith("/api/groups/my%20project");
  });
});

describe("fetchSession", () => {
  it("returns session data", async () => {
    const session = { session_id: "s1", display_name: "テスト" };
    mockFetch.mockResolvedValue(mockJsonResponse(session));
    const result = await fetchSession("s1");
    expect(result.session_id).toBe("s1");
  });
});

describe("fetchMessages", () => {
  it("passes limit parameter", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ messages: [], has_more: false }),
    );
    await fetchMessages("s1", 50);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/sessions/s1/messages?limit=50",
    );
  });

  it("uses default limit of 100", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ messages: [], has_more: false }),
    );
    await fetchMessages("s1");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/sessions/s1/messages?limit=100",
    );
  });
});

describe("searchSessions", () => {
  it("encodes query parameter", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ results: [{ session_id: "s1" }] }),
    );
    const results = await searchSessions("fizz buzz");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/search?q=fizz%20buzz",
    );
    expect(results).toHaveLength(1);
  });

  it("returns empty array when no results", async () => {
    mockFetch.mockResolvedValue(mockJsonResponse({}));
    const results = await searchSessions("nothing");
    expect(results).toEqual([]);
  });
});

describe("togglePin", () => {
  it("sends PUT request", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ is_pinned: true }),
    );
    const result = await togglePin("s1");
    expect(result.is_pinned).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith("/api/sessions/s1/pin", {
      method: "PUT",
    });
  });
});

describe("renameSession", () => {
  it("sends POST with title", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ session_id: "s1", title: "new title" }),
    );
    const result = await renameSession("s1", "new title");
    expect(result.title).toBe("new title");
    expect(mockFetch).toHaveBeenCalledWith("/api/sessions/s1/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "new title" }),
    });
  });
});

describe("hideSession", () => {
  it("sends POST request", async () => {
    mockFetch.mockResolvedValue(
      mockJsonResponse({ hidden: true }),
    );
    const result = await hideSession("s1");
    expect(result.hidden).toBe(true);
  });
});
