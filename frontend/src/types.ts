export type SessionStatus = "active" | "recent" | "idle" | "archived";

export interface SessionEntry {
  session_id: string;
  clone_id: string;
  group_id: string;
  display_name: string;
  custom_title: string | null;
  first_prompt: string;
  message_count: number;
  created: string;
  modified: string;
  git_branch: string | null;
  is_sidechain: boolean;
  is_pinned: boolean;
  has_unread: boolean;
  status: SessionStatus;
}

export interface ProjectClone {
  clone_id: string;
  clone_name: string;
  project_path: string;
  session_count: number;
  latest_modified: string | null;
  current_branch: string | null;
  sessions: SessionEntry[];
  trash_sessions: SessionEntry[];
}

export interface ProjectGroup {
  group_id: string;
  display_name: string;
  initials: string;
  total_sessions: number;
  active_sessions: number;
  latest_modified: string | null;
  total_messages: number;
  clone_count: number;
}

export interface ProjectGroupDetail extends ProjectGroup {
  clones: ProjectClone[];
}

export interface ToolUse {
  tool_name: string;
  input_summary: string;
  output_summary: string;
}

export interface SessionMessage {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string | null;
  tool_uses: ToolUse[];
}

export interface SearchResult {
  session_id: string;
  group_id: string;
  clone_id: string;
  display_name: string;
  first_prompt: string;
  score: number;
  group_name: string;
  clone_name: string;
}

export interface SendMessageResult {
  success: boolean;
  result?: string;
  session_id?: string;
  cost_usd?: number;
  error?: string;
}

export interface AssetFile {
  name: string;
  path: string;
  content: string;
}

export interface ProjectAssets {
  project_path: string;
  claude_md: string | null;
  local_rules: AssetFile[];
  local_skills: AssetFile[];
  global_claude_md: string | null;
  global_rules: AssetFile[];
}
