const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100";

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
};
