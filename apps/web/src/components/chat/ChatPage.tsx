"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  PlusIcon,
  MessageSquareIcon,
  PaperclipIcon,
  FileTextIcon,
  FlaskConicalIcon,
  Trash2Icon,
  PuzzleIcon,
  CheckIcon,
  XIcon,
} from "lucide-react";
import {
  api,
  type AvailablePlugin,
  type Conversation,
  type Document,
  type StreamEvent,
  type WorkspacePlugin,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import { Dialog, DialogContent, DialogFooter, Input, Spinner } from "@/components/ui";
import { useWorkspace } from "@/context/WorkspaceContext";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { ContextPanel, type ContextPanelCapability } from "./ContextPanel";
import type { ChatMessageData, ContextUsed } from "./ChatMessage";

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

const PLUGIN_LABELS: Record<string, string> = {
  ntfy:             "ntfy",
  weather:          "Clima",
  web_search:       "Web Search",
  home_assistant:   "Home Assistant",
  notion:           "Notion",
  google_calendar:  "Google Calendar",
};

const PLUGIN_CONFIG_FIELDS: Record<
  string,
  { key: string; label: string; placeholder: string }[]
> = {
  ntfy: [
    { key: "url",   label: "URL do servidor", placeholder: "http://192.168.1.26:2586" },
    { key: "topic", label: "Tópico",          placeholder: "khonshu"                  },
  ],
  weather: [
    { key: "default_location", label: "Cidade padrão", placeholder: "São Paulo" },
  ],
  web_search: [],
  home_assistant: [
    { key: "url",   label: "URL do HA",          placeholder: "http://homeassistant.local:8123" },
    { key: "token", label: "Long-lived token",    placeholder: "eyJ..."                         },
  ],
  notion: [
    { key: "token",           label: "Integration token",    placeholder: "secret_..." },
    { key: "default_page_id", label: "ID da página padrão",  placeholder: "..."        },
  ],
  google_calendar: [
    { key: "access_token", label: "Access token OAuth2", placeholder: "ya29..."               },
    { key: "calendar_id",  label: "Calendar ID",         placeholder: "primary"               },
    { key: "timezone",     label: "Fuso horário",        placeholder: "America/Sao_Paulo"     },
  ],
};

type ConfigModal = {
  plugin:   AvailablePlugin;
  existing: WorkspacePlugin | null;
};

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function ChatPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();

  const [conversations,    setConversations]    = useState<Conversation[]>([]);
  const [activeConvId,     setActiveConvId]     = useState<string | null>(null);
  const [messages,         setMessages]         = useState<ChatMessageData[]>([]);
  const [isStreaming,      setIsStreaming]       = useState(false);

  const [documents,        setDocuments]        = useState<Document[]>([]);
  const [isUploading,      setIsUploading]      = useState(false);

  const [availablePlugins, setAvailablePlugins] = useState<AvailablePlugin[]>([]);
  const [workspacePlugins, setWorkspacePlugins] = useState<WorkspacePlugin[]>([]);
  const [configModal,      setConfigModal]      = useState<ConfigModal | null>(null);
  const [configValues,     setConfigValues]     = useState<Record<string, string>>({});

  // Context panel
  const [activeContextMsgId, setActiveContextMsgId] = useState<string | null>(null);

  const fileInputRef   = useRef<HTMLInputElement>(null);
  const streamingIdRef = useRef<string | null>(null);

  // ─── init on workspace change ───
  useEffect(() => {
    if (!workspace) return;
    setConversations([]);
    setMessages([]);
    setActiveConvId(null);
    setActiveContextMsgId(null);

    (async () => {
      const [convs, docs, available, wPlugins] = await Promise.all([
        api.listConversations(workspace.id),
        api.listDocuments(workspace.id),
        api.listAvailablePlugins(workspace.id),
        api.listWorkspacePlugins(workspace.id),
      ]);
      setConversations(convs);
      setDocuments(docs);
      setAvailablePlugins(available);
      setWorkspacePlugins(wPlugins);

      if (convs.length > 0) {
        await loadConversation(workspace.id, convs[0].id);
      }
    })();
  }, [workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── load conversation ───
  async function loadConversation(workspaceId: string, conversationId: string) {
    setActiveConvId(conversationId);
    setActiveContextMsgId(null);
    const msgs = await api.getMessages(workspaceId, conversationId);
    setMessages(
      msgs
        .filter((m) => m.role !== "system")
        .map((m) => ({
          id:      m.id,
          role:    m.role as "user" | "assistant",
          content: m.content,
        })),
    );
  }

  // ─── new conversation ───
  async function handleNewConversation() {
    if (!workspace) return;
    const title = `Conversa ${conversations.length + 1}`;
    const conv  = await api.createConversation(workspace.id, title);
    setConversations((prev) => [conv, ...prev]);
    setActiveConvId(conv.id);
    setMessages([]);
    setActiveContextMsgId(null);
  }

  // ─── document upload ───
  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!workspace) return;
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    try {
      const doc = await api.uploadDocument(workspace.id, file);
      setDocuments((prev) => [doc, ...prev]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDeleteDocument(docId: string) {
    if (!workspace) return;
    await api.deleteDocument(workspace.id, docId);
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
  }

  // ─── plugin management ───
  function openPluginConfig(plugin: AvailablePlugin) {
    if (!workspace) return;
    const existing = workspacePlugins.find((p) => p.plugin_name === plugin.name) ?? null;
    setConfigModal({ plugin, existing });
    setConfigValues(existing?.config ?? {});
  }

  async function handleSavePlugin() {
    if (!configModal || !workspace) return;
    const saved = await api.upsertPlugin(
      workspace.id,
      configModal.plugin.name,
      configValues,
      true,
    );
    setWorkspacePlugins((prev) => {
      const idx = prev.findIndex((p) => p.plugin_name === saved.plugin_name);
      return idx >= 0 ? prev.map((p, i) => (i === idx ? saved : p)) : [...prev, saved];
    });
    setConfigModal(null);
  }

  async function handleTogglePlugin(wp: WorkspacePlugin) {
    if (!workspace) return;
    const updated = await api.togglePlugin(workspace.id, wp.id, !wp.is_enabled);
    setWorkspacePlugins((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  }

  async function handleRemovePlugin(wp: WorkspacePlugin) {
    if (!workspace) return;
    await api.deletePlugin(workspace.id, wp.id);
    setWorkspacePlugins((prev) => prev.filter((p) => p.id !== wp.id));
  }

  // ─── send message ───
  const handleSend = useCallback(
    async (content: string) => {
      if (!workspace || isStreaming) return;

      let conversationId = activeConvId;
      if (!conversationId) {
        const title = content.slice(0, 40) + (content.length > 40 ? "…" : "");
        const conv  = await api.createConversation(workspace.id, title);
        setConversations((prev) => [conv, ...prev]);
        setActiveConvId(conv.id);
        conversationId = conv.id;
      }

      const userMsg: ChatMessageData = { id: uuid(), role: "user", content };
      const streamingId              = uuid();
      streamingIdRef.current         = streamingId;
      const assistantMsg: ChatMessageData = {
        id:          streamingId,
        role:        "assistant",
        content:     "",
        streaming:   true,
        streamPhase: "thinking",
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      // Close context panel while user waits
      setActiveContextMsgId(null);

      let capturedContext: ContextUsed | undefined;

      await api.streamMessage(
        workspace.id,
        conversationId,
        content,
        (evt: StreamEvent) => {
          if (evt.event === "thinking") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingId ? { ...m, streamPhase: "thinking" } : m,
              ),
            );
          } else if (evt.event === "reading_memory") {
            capturedContext = {
              memory:    evt.memory,
              knowledge: evt.knowledge,
              chunks:    evt.chunks,
            };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingId
                  ? { ...m, streamPhase: "reading", contextUsed: capturedContext }
                  : m,
              ),
            );
          } else if (evt.event === "text") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingId
                  ? { ...m, content: m.content + evt.content, streamPhase: "writing" }
                  : m,
              ),
            );
          } else if (evt.event === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingId
                  ? { ...m, content: `Erro: ${evt.message}`, streaming: false, streamPhase: null }
                  : m,
              ),
            );
            setIsStreaming(false);
          }
        },
        () => {
          // done
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingId
                ? { ...m, streaming: false, streamPhase: null, contextUsed: capturedContext }
                : m,
            ),
          );
          setIsStreaming(false);
          // Auto-open context panel if there's context
          if (
            capturedContext &&
            (capturedContext.memory > 0 || capturedContext.knowledge > 0 || capturedContext.chunks > 0)
          ) {
            setActiveContextMsgId(streamingId);
          }
        },
        (err) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingId
                ? { ...m, content: `Erro: ${err.message}`, streaming: false, streamPhase: null }
                : m,
            ),
          );
          setIsStreaming(false);
        },
      );
    },
    [workspace, activeConvId, isStreaming],
  );

  // ─── context panel ───
  const activeContextMsg = messages.find((m) => m.id === activeContextMsgId);
  const showContextPanel = Boolean(activeContextMsg?.contextUsed);

  const capabilities: ContextPanelCapability[] = availablePlugins.map((ap) => {
    const wp = workspacePlugins.find((p) => p.plugin_name === ap.name);
    return {
      name:        PLUGIN_LABELS[ap.name] ?? ap.name,
      description: ap.description,
      enabled:     wp?.is_enabled ?? false,
    };
  });

  // ─── loading state ───
  if (wsLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  // ─── render ───
  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Sidebar ── */}
      <aside
        className={cn(
          "flex w-52 shrink-0 flex-col",
          "border-r border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
            Conversas
          </span>
          <button
            onClick={handleNewConversation}
            className="flex h-6 w-6 items-center justify-center rounded-md text-content-muted hover:bg-[var(--surface-subtle)] hover:text-content-secondary transition-colors"
            title="Nova conversa"
          >
            <PlusIcon size={14} />
          </button>
        </div>

        {/* Conversation list */}
        <nav className="flex-1 overflow-y-auto py-1.5 min-h-0">
          {conversations.length === 0 ? (
            <p className="px-4 py-3 text-xs text-content-muted">Nenhuma conversa</p>
          ) : (
            conversations.map((conv) => {
              const isActive = activeConvId === conv.id;
              return (
                <button
                  key={conv.id}
                  onClick={() => workspace && loadConversation(workspace.id, conv.id)}
                  className={cn(
                    "flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors",
                    isActive
                      ? "bg-[var(--surface-overlay)] text-content-primary"
                      : "text-content-secondary hover:bg-[var(--surface-subtle)] hover:text-content-primary",
                  )}
                >
                  <MessageSquareIcon
                    size={12}
                    className={cn("shrink-0", isActive ? "text-accent" : "text-content-muted")}
                  />
                  <span className="truncate">{conv.title}</span>
                </button>
              );
            })
          )}
        </nav>

        {/* Documents */}
        <div className="border-t border-[var(--border-subtle)] flex flex-col max-h-40">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
              Documentos
            </span>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex h-5 w-5 items-center justify-center rounded text-content-muted hover:bg-[var(--surface-subtle)] hover:text-content-secondary transition-colors disabled:opacity-40"
              title="Adicionar documento"
            >
              {isUploading ? <Spinner size="sm" /> : <PaperclipIcon size={12} />}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              className="hidden"
              onChange={handleUpload}
            />
          </div>
          <div className="overflow-y-auto pb-1.5">
            {documents.length === 0 ? (
              <p className="px-4 pb-2 text-xs text-content-placeholder">Nenhum documento</p>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  className="group flex items-center gap-2 px-3 py-1.5 text-xs"
                >
                  <FileTextIcon
                    size={11}
                    className={cn(
                      "shrink-0",
                      doc.status === "ready"  && "text-status-success",
                      doc.status === "failed" && "text-status-error",
                      doc.status === "processing" && "text-content-muted",
                    )}
                  />
                  <span className="truncate flex-1 text-content-secondary">{doc.filename}</span>
                  <button
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="hidden group-hover:flex items-center justify-center text-content-muted hover:text-status-error transition-colors"
                  >
                    <Trash2Icon size={11} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Plugins */}
        <div className="border-t border-[var(--border-subtle)] flex flex-col max-h-52">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
              Plugins
            </span>
            <PuzzleIcon size={12} className="text-content-muted" />
          </div>
          <div className="overflow-y-auto pb-1.5">
            {availablePlugins.length === 0 ? (
              <p className="px-4 pb-2 text-xs text-content-placeholder">Carregando…</p>
            ) : (
              availablePlugins.map((ap) => {
                const wp       = workspacePlugins.find((p) => p.plugin_name === ap.name);
                const isActive = wp?.is_enabled ?? false;
                return (
                  <div key={ap.name} className="group flex items-center gap-2 px-3 py-1.5 text-xs">
                    <button
                      onClick={() => wp && handleTogglePlugin(wp)}
                      disabled={!wp}
                      className={cn(
                        "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
                        isActive
                          ? "border-status-success bg-status-success text-surface-base"
                          : "border-[var(--border-strong)] text-transparent",
                      )}
                      title={isActive ? "Desativar" : "Ativar"}
                    >
                      <CheckIcon size={9} />
                    </button>
                    <span
                      className={cn(
                        "flex-1 truncate cursor-pointer",
                        isActive ? "text-content-primary" : "text-content-muted",
                      )}
                      onClick={() => openPluginConfig(ap)}
                    >
                      {PLUGIN_LABELS[ap.name] ?? ap.name}
                    </span>
                    {wp ? (
                      <button
                        onClick={() => handleRemovePlugin(wp)}
                        className="hidden group-hover:flex items-center justify-center text-content-muted hover:text-status-error transition-colors"
                      >
                        <XIcon size={10} />
                      </button>
                    ) : (
                      <button
                        onClick={() => openPluginConfig(ap)}
                        className="text-[10px] text-content-muted hover:text-content-secondary transition-colors"
                      >
                        config
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </aside>

      {/* ── Main chat area ── */}
      <main className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Header */}
        <header
          className={cn(
            "flex h-11 shrink-0 items-center justify-between border-b border-[var(--border-subtle)]",
            "px-5",
          )}
        >
          <span className="text-sm text-content-secondary truncate">
            {conversations.find((c) => c.id === activeConvId)?.title ?? "Nova conversa"}
          </span>
          <div className="flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-2 py-1">
            <FlaskConicalIcon size={10} className="text-accent" />
            <span className="text-[10px] font-medium text-content-muted">Intelligence Lab</span>
          </div>
        </header>

        <MessageList
          messages={messages}
          onContextClick={(msgId) =>
            setActiveContextMsgId((prev) => (prev === msgId ? null : msgId))
          }
        />

        <ChatInput onSend={handleSend} disabled={isStreaming} streaming={isStreaming} />
      </main>

      {/* ── Context panel ── */}
      {showContextPanel && activeContextMsg?.contextUsed && (
        <ContextPanel
          context={activeContextMsg.contextUsed}
          capabilities={capabilities}
          onClose={() => setActiveContextMsgId(null)}
        />
      )}

      {/* ── Plugin config modal ── */}
      <Dialog open={Boolean(configModal)} onOpenChange={(open) => !open && setConfigModal(null)}>
        <DialogContent size="sm" title={PLUGIN_LABELS[configModal?.plugin.name ?? ""] ?? configModal?.plugin.name ?? ""} onClose={() => setConfigModal(null)}>
          {configModal && (
            <>
              <p className="mb-4 text-xs text-content-muted">{configModal.plugin.description}</p>

              <div className="space-y-3">
                {(PLUGIN_CONFIG_FIELDS[configModal.plugin.name] ?? []).map((field) => (
                  <div key={field.key}>
                    <label className="mb-1.5 block text-xs font-medium text-content-secondary">
                      {field.label}
                    </label>
                    <Input
                      value={configValues[field.key] ?? ""}
                      onChange={(e) =>
                        setConfigValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                      }
                      placeholder={field.placeholder}
                    />
                  </div>
                ))}
                {(PLUGIN_CONFIG_FIELDS[configModal.plugin.name] ?? []).length === 0 && (
                  <p className="text-xs text-content-muted">Nenhuma configuração necessária.</p>
                )}
              </div>

              <DialogFooter>
                <button
                  onClick={() => setConfigModal(null)}
                  className="rounded-lg px-4 py-2 text-xs text-content-muted hover:text-content-primary transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSavePlugin}
                  className="rounded-lg bg-accent px-4 py-2 text-xs text-white hover:bg-accent-hover transition-colors"
                >
                  Salvar
                </button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
