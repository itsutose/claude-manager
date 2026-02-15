import { useCallback, useEffect, useState } from "react";
import type {
  ProjectGroup,
  ProjectGroupDetail,
  SessionEntry,
  SessionMessage,
} from "../types";
import {
  fetchGroups,
  fetchGroupDetail,
  fetchSession,
  fetchMessages,
} from "../api";

export function useGroups() {
  const [groups, setGroups] = useState<ProjectGroup[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [groupDetail, setGroupDetail] = useState<ProjectGroupDetail | null>(
    null,
  );
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );
  const [selectedSession, setSelectedSession] = useState<SessionEntry | null>(
    null,
  );
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  const loadGroups = useCallback(async () => {
    const data = await fetchGroups();
    setGroups(data);
    return data;
  }, []);

  useEffect(() => {
    loadGroups().then((data) => {
      if (data.length > 0 && !selectedGroupId) {
        selectGroup(data[0].group_id);
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectGroup = useCallback(async (groupId: string) => {
    setSelectedGroupId(groupId);
    setSelectedSessionId(null);
    setSelectedSession(null);
    setMessages([]);
    const detail = await fetchGroupDetail(groupId);
    setGroupDetail(detail);
  }, []);

  const openSession = useCallback(async (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setMessagesLoading(true);
    try {
      const [session, msgData] = await Promise.all([
        fetchSession(sessionId),
        fetchMessages(sessionId),
      ]);
      setSelectedSession(session);
      setMessages(msgData.messages);
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    const data = await loadGroups();
    const currentGroupId = selectedGroupId;
    if (
      currentGroupId &&
      data.some((g: ProjectGroup) => g.group_id === currentGroupId)
    ) {
      const detail = await fetchGroupDetail(currentGroupId);
      setGroupDetail(detail);
    }
  }, [loadGroups, selectedGroupId]);

  return {
    groups,
    selectedGroupId,
    groupDetail,
    selectedSessionId,
    selectedSession,
    messages,
    messagesLoading,
    selectGroup,
    openSession,
    refresh,
    setSelectedSession,
  };
}
