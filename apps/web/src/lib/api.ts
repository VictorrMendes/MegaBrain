const API_URL = "/api";

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

export const api = {
  async listWorkspaces(): Promise<Workspace[]> {
    const res = await fetch(`${API_URL}/workspaces/`);
    if (!res.ok) throw new Error("Failed to list workspaces");
    return res.json();
  },

  async createWorkspace(name: string, description?: string): Promise<Workspace> {
    const res = await fetch(`${API_URL}/workspaces/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) throw new Error("Failed to create workspace");
    return res.json();
  },

  async listConversations(workspaceId: string): Promise<Conversation[]> {
    const res = await fetch(`${API_URL}/workspaces/${workspaceId}/conversations/`);
    if (!res.ok) throw new Error("Failed to list conversations");
    return res.json();
  },

  async createConversation(workspaceId: string, title: string): Promise<Conversation> {
    const res = await fetch(`${API_URL}/workspaces/${workspaceId}/conversations/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to create conversation");
    return res.json();
  },

  async getMessages(workspaceId: string, conversationId: string): Promise<Message[]> {
    const res = await fetch(
      `${API_URL}/workspaces/${workspaceId}/conversations/${conversationId}/messages`
    );
    if (!res.ok) throw new Error("Failed to get messages");
    return res.json();
  },

  async streamMessage(
    workspaceId: string,
    conversationId: string,
    content: string,
    onChunk: (chunk: string) => void,
    onDone: () => void,
    onError: (error: Error) => void
  ): Promise<void> {
    let res: Response;
    try {
      res = await fetch(
        `${API_URL}/workspaces/${workspaceId}/conversations/${conversationId}/messages/stream`,
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

    if (!res.ok) {
      onError(new Error(`HTTP ${res.status}`));
      return;
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const payload = JSON.parse(raw);
            if (payload.done) {
              onDone();
            } else if (typeof payload.content === "string") {
              onChunk(payload.content);
            }
          } catch {
            // ignore malformed lines
          }
        }
      }
    } catch (e) {
      onError(e instanceof Error ? e : new Error("Stream error"));
    }
  },

  async listDocuments(workspaceId: string): Promise<Document[]> {
    const res = await fetch(`${API_URL}/workspaces/${workspaceId}/documents/`);
    if (!res.ok) throw new Error("Failed to list documents");
    return res.json();
  },

  async uploadDocument(workspaceId: string, file: File): Promise<Document> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/workspaces/${workspaceId}/documents/`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error("Failed to upload document");
    return res.json();
  },

  async deleteDocument(workspaceId: string, documentId: string): Promise<void> {
    const res = await fetch(
      `${API_URL}/workspaces/${workspaceId}/documents/${documentId}`,
      { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Failed to delete document");
  },

  async listAvailablePlugins(workspaceId: string): Promise<AvailablePlugin[]> {
    const res = await fetch(
      `${API_URL}/workspaces/${workspaceId}/plugins/available`
    );
    if (!res.ok) throw new Error("Failed to list available plugins");
    return res.json();
  },

  async listWorkspacePlugins(workspaceId: string): Promise<WorkspacePlugin[]> {
    const res = await fetch(`${API_URL}/workspaces/${workspaceId}/plugins/`);
    if (!res.ok) throw new Error("Failed to list plugins");
    return res.json();
  },

  async upsertPlugin(
    workspaceId: string,
    pluginName: string,
    config: Record<string, string>,
    isEnabled: boolean = true
  ): Promise<WorkspacePlugin> {
    const res = await fetch(`${API_URL}/workspaces/${workspaceId}/plugins/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plugin_name: pluginName, config, is_enabled: isEnabled }),
    });
    if (!res.ok) throw new Error("Failed to save plugin");
    return res.json();
  },

  async togglePlugin(
    workspaceId: string,
    pluginId: string,
    isEnabled: boolean
  ): Promise<WorkspacePlugin> {
    const res = await fetch(
      `${API_URL}/workspaces/${workspaceId}/plugins/${pluginId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_enabled: isEnabled }),
      }
    );
    if (!res.ok) throw new Error("Failed to toggle plugin");
    return res.json();
  },

  async deletePlugin(workspaceId: string, pluginId: string): Promise<void> {
    const res = await fetch(
      `${API_URL}/workspaces/${workspaceId}/plugins/${pluginId}`,
      { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Failed to delete plugin");
  },
};
