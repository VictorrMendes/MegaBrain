import { create } from "zustand";
import { api, type Conversation, type CognitiveStreamEvent } from "@/lib/api";
import type { ChatMessageData, LiveTraceStep, CognitiveData } from "@/components/chat/ChatMessage";
import type { ContextPanelData } from "@/components/chat/ContextPanel";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export type SidePanel =
  | { type: "context"; msgId: string; data: ContextPanelData }
  | { type: "reasoning"; msgId: string; data: CognitiveData };

export interface ChatStore {
  conversations: Conversation[];
  activeConvId: string | null;
  messages: ChatMessageData[];
  isStreaming: boolean;
  sidePanel: SidePanel | null;
  drawerOpen: boolean;

  setConversations: (convs: Conversation[]) => void;
  setActiveConvId: (id: string | null) => void;
  setMessages: (msgs: ChatMessageData[] | ((prev: ChatMessageData[]) => ChatMessageData[])) => void;
  setSidePanel: (panel: SidePanel | null) => void;
  setDrawerOpen: (open: boolean) => void;

  initWorkspace: (workspaceId: string) => Promise<void>;
  loadConversation: (workspaceId: string, convId: string) => Promise<void>;
  startNewConversation: (workspaceId: string) => Promise<void>;
  sendMessage: (workspaceId: string, content: string) => Promise<void>;
}

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function uuid(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (crypto as any).randomUUID?.() ??
    "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
}

// ─────────────────────────────────────────────────────────────
// Store
// ─────────────────────────────────────────────────────────────

export const useChatStore = create<ChatStore>((set, get) => ({
  conversations: [],
  activeConvId: null,
  messages: [],
  isStreaming: false,
  sidePanel: null,
  drawerOpen: false,

  setConversations: (convs) => set({ conversations: convs }),
  setActiveConvId: (id) => set({ activeConvId: id }),
  setMessages: (msgs) => 
    set((state) => ({ 
      messages: typeof msgs === "function" ? msgs(state.messages) : msgs 
    })),
  setSidePanel: (panel) => set({ sidePanel: panel }),
  setDrawerOpen: (open) => set({ drawerOpen: open }),

  initWorkspace: async (workspaceId: string) => {
    set({ conversations: [], messages: [], activeConvId: null, sidePanel: null, drawerOpen: false });
    
    const [convs, session] = await Promise.all([
      api.listConversations(workspaceId),
      api.getWorkspaceSession(workspaceId).catch(() => null),
    ]);
    
    set({ conversations: convs });
    
    if (convs.length > 0) {
      const restoredId = session?.active_conversation_id;
      const targetId = (restoredId && convs.some((c) => c.id === restoredId))
        ? restoredId
        : convs[0].id;
      await get().loadConversation(workspaceId, targetId);
    }
  },

  loadConversation: async (workspaceId: string, convId: string) => {
    set({ activeConvId: convId, sidePanel: null, drawerOpen: false });
    
    api.updateWorkspaceSession(workspaceId, {
      active_conversation_id: convId,
    }).catch(() => {});
    
    const msgs = await api.getMessages(workspaceId, convId);
    set({
      messages: msgs
        .filter((m) => m.role !== "system")
        .map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
        })),
    });
  },

  startNewConversation: async (workspaceId: string) => {
    const title = `Conversa ${get().conversations.length + 1}`;
    const conv = await api.createConversation(workspaceId, title);
    
    set((state) => ({
      conversations: [conv, ...state.conversations],
      activeConvId: conv.id,
      messages: [],
      sidePanel: null,
    }));
    
    api.updateWorkspaceSession(workspaceId, {
      active_conversation_id: conv.id,
    }).catch(() => {});
  },

  sendMessage: async (workspaceId: string, content: string) => {
    const state = get();
    if (state.isStreaming) return;

    let conversationId = state.activeConvId;
    if (!conversationId) {
      const title = content.slice(0, 40) + (content.length > 40 ? "…" : "");
      const conv = await api.createConversation(workspaceId, title);
      
      set((s) => ({
        conversations: [conv, ...s.conversations],
        activeConvId: conv.id,
      }));
      conversationId = conv.id;
    }

    const userMsg: ChatMessageData = { id: uuid(), role: "user", content };
    const streamingId = uuid();
    const assistantMsg: ChatMessageData = {
      id: streamingId,
      role: "assistant",
      content: "",
      streaming: true,
      streamPhase: "routing",
      liveSteps: [],
    };

    set((s) => ({
      messages: [...s.messages, userMsg, assistantMsg],
      isStreaming: true,
      sidePanel: null,
    }));

    await api.streamOrchestratorExecute(
      workspaceId,
      content,
      conversationId,
      (evt: CognitiveStreamEvent) => {
        if (evt.event === "trace_step") {
          const step: LiveTraceStep = {
            step: evt.step,
            engine: evt.engine,
            status: evt.status,
            output: evt.output,
            duration_ms: evt.duration_ms,
          };

          const nextPhase: Record<string, ChatMessageData["streamPhase"]> = {
            build_context: "routing",
            decide: "searching",
            search: "generating",
            create_mission: "generating",
            generate: "learning",
            learn: null,
          };

          set((s) => ({
            messages: s.messages.map((m) => {
              if (m.id !== streamingId) return m;
              return {
                ...m,
                streamPhase: nextPhase[evt.step] ?? null,
                liveSteps: [...(m.liveSteps ?? []), step],
              };
            }),
          }));
        } else if (evt.event === "llm_token") {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === streamingId
                ? { ...m, content: (m.content ?? "") + evt.token, streamPhase: "generating" }
                : m
            ),
          }));
        } else if (evt.event === "done") {
          const r = evt.response;
          const cognitiveData: CognitiveData = {
            confidence: r.confidence,
            risk: r.risk,
            memory_used: r.memory_used,
            knowledge_used: r.knowledge_used,
            internet_sources: r.internet_sources,
            missions_created: r.missions_created,
            decision: r.decision,
            trace: r.trace,
            thinking_steps: r.thinking_steps,
            estimated_time: r.estimated_time,
            learning_actions: r.learning_actions.length,
          };
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === streamingId
                ? {
                    ...m,
                    content: m.content || r.response,
                    streaming: false,
                    streamPhase: null,
                    cognitiveData,
                  }
                : m
            ),
            isStreaming: false,
          }));
        } else if (evt.event === "error") {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === streamingId
                ? {
                    ...m,
                    content: `Erro: ${evt.message}`,
                    streaming: false,
                    streamPhase: null,
                  }
                : m
            ),
            isStreaming: false,
          }));
        }
      },
      (err) => {
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === streamingId
              ? {
                  ...m,
                  content: `Erro: ${err.message}`,
                  streaming: false,
                  streamPhase: null,
                }
              : m
          ),
          isStreaming: false,
        }));
      }
    );
  },
}));
