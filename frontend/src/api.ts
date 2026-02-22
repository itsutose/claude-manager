import type {
  ProjectGroup,
  ProjectGroupDetail,
  SessionEntry,
  SessionMessage,
  SearchResult,
  SendMessageResult,
  ProjectAssets,
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
  limit?: number,
): Promise<{ messages: SessionMessage[]; has_more: boolean }> {
  const url = limit
    ? `/api/sessions/${sessionId}/messages?limit=${limit}`
    : `/api/sessions/${sessionId}/messages`;
  const res = await fetch(url);
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

export async function sendMessage(
  sessionId: string,
  message: string,
  images?: string[],
): Promise<SendMessageResult> {
  const payload: { message: string; images?: string[] } = { message };
  if (images && images.length > 0) {
    payload.images = images;
  }
  const res = await fetch(`/api/sessions/${sessionId}/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function createSession(
  groupId: string,
  cloneId: string,
  message: string,
  images?: string[],
): Promise<SendMessageResult> {
  const payload: { group_id: string; clone_id: string; message: string; images?: string[] } = {
    group_id: groupId,
    clone_id: cloneId,
    message,
  };
  if (images && images.length > 0) {
    payload.images = images;
  }
  const res = await fetch("/api/sessions/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function renameSession(
  sessionId: string,
  title: string,
): Promise<{ session_id: string; title: string }> {
  const res = await fetch(`/api/sessions/${sessionId}/rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function autoRenameSession(
  sessionId: string,
): Promise<{ session_id: string; title: string }> {
  const res = await fetch(`/api/sessions/${sessionId}/auto-rename`, {
    method: "POST",
  });
  return res.json();
}

export async function hideSession(
  sessionId: string,
): Promise<{ hidden: boolean }> {
  const res = await fetch(`/api/sessions/${sessionId}/hide`, {
    method: "POST",
  });
  return res.json();
}

export async function fetchGroupAssets(
  groupId: string,
): Promise<ProjectAssets> {
  const res = await fetch(`/api/groups/${encodeURIComponent(groupId)}/assets`);
  return res.json();
}
