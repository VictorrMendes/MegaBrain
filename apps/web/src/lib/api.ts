const API_URL = "/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface Workspace {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface Document {
  id: string;
  workspace_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: DocumentStatus;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface AvailablePlugin {
  name: string;
  description: string;
}

export interface WorkspacePlugin {
  id: string;
  workspace_id: string;
  plugin_name: string;
  is_enabled: boolean;
  config: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export type MissionStatus =
  | "pending"
  | "planning"
  | "waiting_approval"
  | "ready"
  | "running"
  | "paused"
  | "retrying"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface Mission {
  id: string;
  workspace_id: string;
  intent: string;
  status: MissionStatus;
  planner: string | null;
  executor: string | null;
  trigger: string;
  requires_approval: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface MissionStep {
  id: string;
  mission_id: string;
  order: number;
  type: string;
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  retry_count: number;
}

export interface MissionArtifact {
  id: string;
  mission_id: string;
  step_id: string | null;
  type: string;
  mime: string;
  name: string;
  uri: string;
  created_at: string;
}

export interface MissionLog {
  id: string;
  mission_id: string;
  step_id: string | null;
  level: string;
  message: string;
  occurred_at: string;
}

export interface MissionDetail extends Mission {
  steps: MissionStep[];
  artifacts: MissionArtifact[];
  logs: MissionLog[];
}

export interface Memory {
  id: string;
  workspace_id: string;
  type: string;
  content: string;
  source: string | null;
  importance: number;
  created_at: string;
  updated_at: string;
}

export interface Fact {
  id: string;
  workspace_id: string;
  statement: string;
  source_type: string;
  source_id: string | null;
  entity_id: string | null;
  confidence: number;
  created_at: string;
}

export interface Observation {
  id: string;
  workspace_id: string;
  statement: string;
  derived_from: string;
  confidence: number;
  reinforcement_count: number;
  expired: boolean;
  created_at: string;
}

export interface InboxItem {
  id: string;
  workspace_id: string;
  type: string;
  raw_content: string;
  title: string | null;
  source: string;
  status: string;
  routing_notes: string | null;
  mission_id: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface ComponentHealth {
  name: string;
  status: "ready" | "degraded" | "failed";
  latency_ms: number | null;
  detail: string | null;
  checked_at: string;
}

export interface CapabilityInfo {
  name: string;
  description: string;
  plugin: string;
  risk_level: string;
  tags: string[];
  tool_count: number;
  requires_network: boolean;
  requires_confirmation: boolean;
  confidence_score: number;
}

export interface SchedulerInfo {
  active_triggers: number;
  paused_triggers: number;
  total_triggers: number;
}

export interface RuntimeStatus {
  status: string;
  checked_at: string;
  provider: {
    name: string;
    model: string;
    embed_model: string | null;
    base_url: string;
  };
  health: ComponentHealth[];
  capabilities: CapabilityInfo[];
  scheduler: SchedulerInfo;
  active_missions: Mission[];
}

// SSE streaming event types
export type StreamEvent =
  | { event: "thinking" }
  | { event: "reading_memory"; memory: number; knowledge: number; chunks: number }
  | { event: "text"; content: string }
  | { event: "done" }
  | { event: "error"; message: string };

// Obsidian types
export interface ObsidianNoteInput {
  path: string;
  content: string;
  last_modified?: string;
}
export interface ObsidianSyncResponse {
  added: number;
  updated: number;
  unchanged: number;
  errors: string[];
}
export interface ObsidianNote {
  id: string;
  path: string;
  title: string;
  tags: string[];
  frontmatter: Record<string, string>;
  last_modified: string | null;
  document_id: string | null;
}
export interface GraphNode { id: string; title: string; tags: string[]; path: string; }
export interface GraphEdge { source: string; target: string; link_text: string | null; }
export interface ObsidianGraph { nodes: GraphNode[]; edges: GraphEdge[]; }

// ── API client ───────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`);
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PATCH ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  // ── Workspaces ────────────────────────────────────────────────────────
  listWorkspaces: () => get<Workspace[]>("/workspaces/"),
  createWorkspace: (name: string, description?: string) =>
    post<Workspace>("/workspaces/", { name, description }),

  // ── Conversations ─────────────────────────────────────────────────────
  listConversations: (wsId: string) =>
    get<Conversation[]>(`/workspaces/${wsId}/conversations/`),
  createConversation: (wsId: string, title: string) =>
    post<Conversation>(`/workspaces/${wsId}/conversations/`, { title }),
  getMessages: (wsId: string, convId: string) =>
    get<Message[]>(`/workspaces/${wsId}/conversations/${convId}/messages`),

  async streamMessage(
    wsId: string,
    convId: string,
    content: string,
    onEvent: (e: StreamEvent) => void,
    onDone: () => void,
    onError: (err: Error) => void
  ): Promise<void> {
    let res: Response;
    try {
      res = await fetch(
        `${API_URL}/workspaces/${wsId}/conversations/${convId}/messages/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
        }
      );
    } catch (e) {
      onError(e instanceof Error ? e : new Error("Network error"));
      return;
    }
    if (!res.ok) { onError(new Error(`HTTP ${res.status}`)); return; }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let currentEvent = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6).trim();
            if (!raw) continue;
            try {
              const payload = JSON.parse(raw);
              const eventType = currentEvent || payload.event;
              if (eventType === "done" || payload.done) {
                onDone();
              } else if (eventType === "text" || typeof payload.content === "string") {
                onEvent({ event: "text", content: payload.content ?? "" });
              } else if (eventType === "thinking") {
                onEvent({ event: "thinking" });
              } else if (eventType === "reading_memory") {
                onEvent({
                  event: "reading_memory",
                  memory: payload.memory ?? 0,
                  knowledge: payload.knowledge ?? 0,
                  chunks: payload.chunks ?? 0,
                });
              } else if (eventType === "error") {
                onEvent({ event: "error", message: payload.message ?? "Erro" });
              }
              currentEvent = "";
            } catch { /* ignore malformed */ }
          }
        }
      }
    } catch (e) {
      onError(e instanceof Error ? e : new Error("Stream error"));
    }
  },

  // ── Documents ─────────────────────────────────────────────────────────
  listDocuments: (wsId: string) =>
    get<Document[]>(`/workspaces/${wsId}/documents/`),
  async uploadDocument(wsId: string, file: File): Promise<Document> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/workspaces/${wsId}/documents/`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  },
  deleteDocument: (wsId: string, docId: string) =>
    del(`/workspaces/${wsId}/documents/${docId}`),

  // ── Plugins ───────────────────────────────────────────────────────────
  listAvailablePlugins: (wsId: string) =>
    get<AvailablePlugin[]>(`/workspaces/${wsId}/plugins/available`),
  listWorkspacePlugins: (wsId: string) =>
    get<WorkspacePlugin[]>(`/workspaces/${wsId}/plugins/`),
  upsertPlugin: (wsId: string, name: string, config: Record<string, string>, enabled = true) =>
    post<WorkspacePlugin>(`/workspaces/${wsId}/plugins/`, {
      plugin_name: name, config, is_enabled: enabled,
    }),
  togglePlugin: (wsId: string, pluginId: string, enabled: boolean) =>
    patch<WorkspacePlugin>(`/workspaces/${wsId}/plugins/${pluginId}`, {
      is_enabled: enabled,
    }),
  deletePlugin: (wsId: string, pluginId: string) =>
    del(`/workspaces/${wsId}/plugins/${pluginId}`),

  // ── Missions ──────────────────────────────────────────────────────────
  listMissions: (wsId: string, status?: MissionStatus) =>
    get<Mission[]>(
      `/workspaces/${wsId}/missions${status ? `?status=${status}` : ""}`
    ),
  getMission: (wsId: string, missionId: string) =>
    get<MissionDetail>(`/workspaces/${wsId}/missions/${missionId}`),
  createMission: (wsId: string, intent: string, requiresApproval = false) =>
    post<Mission>(`/workspaces/${wsId}/missions`, {
      intent,
      requires_approval: requiresApproval,
    }),
  planMission: (wsId: string, missionId: string) =>
    post<Mission>(`/workspaces/${wsId}/missions/${missionId}/plan`),
  approveMission: (wsId: string, missionId: string) =>
    post<Mission>(`/workspaces/${wsId}/missions/${missionId}/approve`),
  rejectMission: (wsId: string, missionId: string) =>
    post<Mission>(`/workspaces/${wsId}/missions/${missionId}/reject`),
  runMission: (wsId: string, missionId: string) =>
    post<Mission>(`/workspaces/${wsId}/missions/${missionId}/run`),
  cancelMission: (wsId: string, missionId: string) =>
    post<Mission>(`/workspaces/${wsId}/missions/${missionId}/cancel`),

  // ── Artifacts ─────────────────────────────────────────────────────────
  listArtifacts: (wsId: string, missionId?: string) =>
    get<MissionArtifact[]>(
      `/workspaces/${wsId}/artifacts${missionId ? `?mission_id=${missionId}` : ""}`
    ),

  // ── Memory ────────────────────────────────────────────────────────────
  listMemories: (wsId: string, limit = 50) =>
    get<Memory[]>(`/workspaces/${wsId}/memories?limit=${limit}`),
  recallMemories: (wsId: string, query: string) =>
    get<Memory[]>(`/workspaces/${wsId}/memories/recall?q=${encodeURIComponent(query)}`),

  // ── Knowledge ─────────────────────────────────────────────────────────
  listFacts: (wsId: string, limit = 50) =>
    get<Fact[]>(`/workspaces/${wsId}/knowledge/facts?limit=${limit}`),
  listObservations: (wsId: string, limit = 50) =>
    get<Observation[]>(
      `/workspaces/${wsId}/knowledge/observations?limit=${limit}`
    ),

  // ── Inbox ─────────────────────────────────────────────────────────────
  listInbox: (wsId: string, status?: string, limit = 50) =>
    get<InboxItem[]>(
      `/workspaces/${wsId}/inbox${status ? `?status=${status}` : `?limit=${limit}`}`
    ),
  submitInbox: (wsId: string, content: string, source = "web") =>
    post<InboxItem>(`/workspaces/${wsId}/inbox`, {
      raw_content: content,
      source,
      process_now: true,
    }),
  processInboxItem: (wsId: string, itemId: string) =>
    post<InboxItem>(`/workspaces/${wsId}/inbox/${itemId}/process`),
  dismissInboxItem: (wsId: string, itemId: string) =>
    post<InboxItem>(`/workspaces/${wsId}/inbox/${itemId}/dismiss`),

  // ── Runtime ───────────────────────────────────────────────────────────
  getRuntimeStatus: () => get<RuntimeStatus>("/runtime"),

  // ── Obsidian ──────────────────────────────────────────────────────────
  syncObsidian: (wsId: string, notes: ObsidianNoteInput[]) =>
    post<ObsidianSyncResponse>(`/workspaces/${wsId}/obsidian/sync`, { notes }),
  getObsidianGraph: (wsId: string) =>
    get<ObsidianGraph>(`/workspaces/${wsId}/obsidian/graph`),
  listObsidianNotes: (wsId: string) =>
    get<ObsidianNote[]>(`/workspaces/${wsId}/obsidian/notes`),
};
