import type {
  ProjectGroup,
  ProjectGroupDetail,
  SessionEntry,
  SessionMessage,
  SearchResult,
} from "./types";

export async function fetchGroups(): Promise<ProjectGroup[]> {
  const res = await fetch("/api/groups");
  const data = await res.json();
  return data.groups ?? [];
}

export async function fetchGroupDetail(
  groupId: string,
): Promise<ProjectGroupDetail> {
  const res = await fetch(`/api/groups/${encodeURIComponent(groupId)}`);
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<SessionEntry> {
  const res = await fetch(`/api/sessions/${sessionId}`);
  return res.json();
}

export async function fetchMessages(
  sessionId: string,
  limit = 100,
): Promise<{ messages: SessionMessage[]; has_more: boolean }> {
  const res = await fetch(
    `/api/sessions/${sessionId}/messages?limit=${limit}`,
  );
  return res.json();
}

export async function searchSessions(
  query: string,
): Promise<SearchResult[]> {
  const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
  const data = await res.json();
  return data.results ?? [];
}

export async function togglePin(
  sessionId: string,
): Promise<{ is_pinned: boolean }> {
  const res = await fetch(`/api/sessions/${sessionId}/pin`, {
    method: "PUT",
  });
  return res.json();
}

export async function resumeSession(
  sessionId: string,
): Promise<{ success: boolean; command?: string }> {
  const res = await fetch(`/api/sessions/${sessionId}/resume`, {
    method: "POST",
  });
  return res.json();
}
