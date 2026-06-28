"use client";

import { useEffect, useRef, useState } from "react";
import {
  PlusIcon,
  MessageSquareIcon,
  MenuIcon,
  PaperclipIcon,
  FileTextIcon,
  FlaskConicalIcon,
  Trash2Icon,
  PuzzleIcon,
  CheckIcon,
  XIcon,
} from "lucide-react";
import { api, type AvailablePlugin, type Document, type WorkspacePlugin } from "@/lib/api";
import { cn } from "@/lib/cn";
import { Dialog, DialogContent, DialogFooter, Input, Spinner } from "@/components/ui";
import { useWorkspace } from "@/context/WorkspaceContext";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { ContextPanel } from "./ContextPanel";
import { ReasoningPanel } from "./ReasoningPanel";
import { useChatStore } from "@/store/useChatStore";

const PLUGIN_LABELS: Record<string, string> = {
  ntfy: "ntfy",
  weather: "Clima",
  web_search: "Web Search",
  home_assistant: "Home Assistant",
  notion: "Notion",
  google_calendar: "Google Calendar",
};

const PLUGIN_CONFIG_FIELDS: Record<string, { key: string; label: string; placeholder: string }[]> = {
  ntfy: [
    { key: "url", label: "URL do servidor", placeholder: "http://192.168.1.26:2586" },
    { key: "topic", label: "Tópico", placeholder: "khonshu" },
  ],
  weather: [
    { key: "default_location", label: "Cidade padrão", placeholder: "São Paulo" },
  ],
  web_search: [],
  home_assistant: [
    { key: "url", label: "URL do HA", placeholder: "http://homeassistant.local:8123" },
    { key: "token", label: "Long-lived token", placeholder: "eyJ..." },
  ],
  notion: [
    { key: "token", label: "Integration token", placeholder: "secret_..." },
    { key: "default_page_id", label: "ID da página padrão", placeholder: "..." },
  ],
  google_calendar: [
    { key: "access_token", label: "Access token OAuth2", placeholder: "ya29..." },
    { key: "calendar_id", label: "Calendar ID", placeholder: "primary" },
    { key: "timezone", label: "Fuso horário", placeholder: "America/Sao_Paulo" },
  ],
};

type ConfigModal = {
  plugin: AvailablePlugin;
  existing: WorkspacePlugin | null;
};

export function ChatPanel() {
  const { current: workspace, loading: wsLoading } = useWorkspace();

  // Zustand Store
  const {
    conversations,
    activeConvId,
    messages,
    isStreaming,
    sidePanel,
    drawerOpen,
    setSidePanel,
    setDrawerOpen,
    initWorkspace,
    loadConversation,
    startNewConversation,
    sendMessage,
  } = useChatStore();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [availablePlugins, setAvailablePlugins] = useState<AvailablePlugin[]>([]);
  const [workspacePlugins, setWorkspacePlugins] = useState<WorkspacePlugin[]>([]);
  const [configModal, setConfigModal] = useState<ConfigModal | null>(null);
  const [configValues, setConfigValues] = useState<Record<string, string>>({});

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!workspace) return;
    initWorkspace(workspace.id);

    (async () => {
      const [docs, available, wPlugins] = await Promise.all([
        api.listDocuments(workspace.id),
        api.listAvailablePlugins(workspace.id),
        api.listWorkspacePlugins(workspace.id),
      ]);
      setDocuments(docs);
      setAvailablePlugins(available);
      setWorkspacePlugins(wPlugins);
    })();
  }, [workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Document Management
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

  // Plugin Management
  function openPluginConfig(plugin: AvailablePlugin) {
    if (!workspace) return;
    const existing = workspacePlugins.find((p) => p.plugin_name === plugin.name) ?? null;
    setConfigModal({ plugin, existing });
    setConfigValues(existing?.config ?? {});
  }

  async function handleSavePlugin() {
    if (!configModal || !workspace) return;
    const saved = await api.upsertPlugin(workspace.id, configModal.plugin.name, configValues, true);
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

  function openReasoningPanel(msgId: string) {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg?.cognitiveData) return;
    setSidePanel(
      sidePanel?.type === "reasoning" && sidePanel.msgId === msgId
        ? null
        : { type: "reasoning", msgId, data: msg.cognitiveData }
    );
  }

  function openContextPanel(msgId: string) {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg?.cognitiveData) return;
    setSidePanel(
      sidePanel?.type === "context" && sidePanel.msgId === msgId
        ? null
        : { 
            type: "context", 
            msgId, 
            data: {
              memory_used: msg.cognitiveData.memory_used,
              knowledge_used: msg.cognitiveData.knowledge_used,
              internet_sources: msg.cognitiveData.internet_sources,
              missions_created: msg.cognitiveData.missions_created,
            }
          }
    );
  }

  if (wsLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <div className="flex h-full w-full overflow-hidden bg-[var(--surface-base)] relative">
      {/* Mobile Backdrop */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-[var(--z-overlay)] bg-black/60 backdrop-blur-sm md:hidden animate-fade-in"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* Sidebar: Conversations, Docs & Plugins */}
      <aside
        className={cn(
          "flex w-64 shrink-0 flex-col",
          "border-r border-[var(--border-subtle)] bg-[var(--surface-raised)]",
          "hidden md:flex",
          drawerOpen && "flex fixed left-0 top-0 bottom-0 z-[var(--z-modal)] animate-slide-in-left md:relative md:inset-auto md:z-auto"
        )}
      >
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">Conversas</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => workspace && startNewConversation(workspace.id)}
              className="flex h-7 w-7 items-center justify-center rounded-md text-content-muted hover:bg-[var(--surface-subtle)] hover:text-content-secondary transition-colors touch-compact"
            >
              <PlusIcon size={14} />
            </button>
            <button
              onClick={() => setDrawerOpen(false)}
              className="flex md:hidden h-7 w-7 items-center justify-center rounded-md text-content-muted hover:bg-[var(--surface-subtle)] hover:text-content-secondary transition-colors touch-compact"
            >
              <XIcon size={14} />
            </button>
          </div>
        </div>

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
                      : "text-content-secondary hover:bg-[var(--surface-subtle)] hover:text-content-primary"
                  )}
                >
                  <MessageSquareIcon size={12} className={cn("shrink-0", isActive ? "text-accent" : "text-content-muted")} />
                  <span className="truncate">{conv.title}</span>
                </button>
              );
            })
          )}
        </nav>

        {/* Documents */}
        <div className="border-t border-[var(--border-subtle)] flex flex-col max-h-40">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">Documentos</span>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex h-5 w-5 items-center justify-center rounded text-content-muted hover:bg-[var(--surface-subtle)] hover:text-content-secondary transition-colors disabled:opacity-40"
            >
              {isUploading ? <Spinner size="sm" /> : <PaperclipIcon size={12} />}
            </button>
            <input ref={fileInputRef} type="file" accept=".txt,.md,text/plain,text/markdown" className="hidden" onChange={handleUpload} />
          </div>
          <div className="overflow-y-auto pb-1.5">
            {documents.length === 0 ? (
              <p className="px-4 pb-2 text-xs text-content-placeholder">Nenhum documento</p>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className="group flex items-center gap-2 px-3 py-1.5 text-xs">
                  <FileTextIcon
                    size={11}
                    className={cn(
                      "shrink-0",
                      doc.status === "ready" && "text-status-success",
                      doc.status === "failed" && "text-status-error",
                      doc.status === "processing" && "text-content-muted"
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

        {/* Plugins (Desabilitados temporariamente a pedido)
        <div className="border-t border-[var(--border-subtle)] flex flex-col max-h-52">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">Plugins</span>
            <PuzzleIcon size={12} className="text-content-muted" />
          </div>
          <div className="overflow-y-auto pb-1.5">
            {availablePlugins.length === 0 ? (
              <p className="px-4 pb-2 text-xs text-content-placeholder">Carregando…</p>
            ) : (
              availablePlugins.map((ap) => {
                const wp = workspacePlugins.find((p) => p.plugin_name === ap.name);
                const isActive = wp?.is_enabled ?? false;
                return (
                  <div key={ap.name} className="group flex items-center gap-2 px-3 py-1.5 text-xs">
                    <button
                      onClick={() => wp && handleTogglePlugin(wp)}
                      disabled={!wp}
                      className={cn(
                        "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
                        isActive ? "border-status-success bg-status-success text-surface-base" : "border-[var(--border-strong)] text-transparent"
                      )}
                    >
                      <CheckIcon size={9} />
                    </button>
                    <span
                      className={cn("flex-1 truncate cursor-pointer", isActive ? "text-content-primary" : "text-content-muted")}
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
                      <button onClick={() => openPluginConfig(ap)} className="text-[10px] text-content-muted hover:text-content-secondary transition-colors">
                        config
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
        */}
      </aside>

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col overflow-hidden min-w-0 bg-transparent">
        <header className="flex h-11 shrink-0 items-center gap-2 border-b border-[var(--border-subtle)] px-3 md:px-5">
          <button
            className="flex md:hidden h-8 w-8 shrink-0 items-center justify-center rounded-lg text-content-muted hover:bg-[var(--surface-subtle)] transition-colors touch-compact"
            onClick={() => setDrawerOpen(true)}
          >
            <MenuIcon size={16} />
          </button>
          <span className="flex-1 text-sm text-content-secondary truncate">
            {conversations.find((c) => c.id === activeConvId)?.title ?? "Nova conversa"}
          </span>
          <div className="flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-2 py-1 shadow-glow-sm">
            <FlaskConicalIcon size={10} className="text-accent animate-pulse" />
            <span className="text-[10px] font-medium text-content-muted hidden sm:inline">Cognitive Core</span>
          </div>
        </header>

        <MessageList
          messages={messages}
          onContextClick={(msgId) => openContextPanel(msgId)}
          onShowReasoning={(msgId) => openReasoningPanel(msgId)}
        />

        <ChatInput onSend={(c) => workspace && sendMessage(workspace.id, c)} disabled={isStreaming} streaming={isStreaming} />
      </main>

      {/* Side Panels */}
      {sidePanel?.type === "reasoning" && (
        <>
          <div className="fixed inset-0 z-[var(--z-overlay)] bg-black/60 md:hidden backdrop-blur-sm" onClick={() => setSidePanel(null)} />
          <div className="fixed inset-x-0 bottom-0 z-[var(--z-modal)] max-h-[85dvh] overflow-y-auto md:relative md:inset-auto md:z-auto md:max-h-none md:overflow-hidden md:h-full shadow-2xl glass-lg rounded-t-xl md:rounded-none">
            <ReasoningPanel data={sidePanel.data} onClose={() => setSidePanel(null)} />
          </div>
        </>
      )}
      {sidePanel?.type === "context" && (
        <>
          <div className="fixed inset-0 z-[var(--z-overlay)] bg-black/60 md:hidden backdrop-blur-sm" onClick={() => setSidePanel(null)} />
          <div className="fixed inset-x-0 bottom-0 z-[var(--z-modal)] max-h-[85dvh] overflow-y-auto md:relative md:inset-auto md:z-auto md:max-h-none md:overflow-hidden md:h-full shadow-2xl glass-lg rounded-t-xl md:rounded-none">
            <ContextPanel data={sidePanel.data} onClose={() => setSidePanel(null)} />
          </div>
        </>
      )}

      {/* Plugin Config Modal */}
      <Dialog open={Boolean(configModal)} onOpenChange={(open) => !open && setConfigModal(null)}>
        <DialogContent size="sm" title={PLUGIN_LABELS[configModal?.plugin.name ?? ""] ?? configModal?.plugin.name ?? ""} onClose={() => setConfigModal(null)}>
          {configModal && (
            <>
              <p className="mb-4 text-xs text-content-muted">{configModal.plugin.description}</p>
              <div className="space-y-3">
                {(PLUGIN_CONFIG_FIELDS[configModal.plugin.name] ?? []).map((field) => (
                  <div key={field.key}>
                    <label className="mb-1.5 block text-xs font-medium text-content-secondary">{field.label}</label>
                    <Input
                      value={configValues[field.key] ?? ""}
                      onChange={(e) => setConfigValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                      placeholder={field.placeholder}
                    />
                  </div>
                ))}
                {(PLUGIN_CONFIG_FIELDS[configModal.plugin.name] ?? []).length === 0 && (
                  <p className="text-xs text-content-muted">Nenhuma configuração necessária.</p>
                )}
              </div>
              <DialogFooter>
                <button onClick={() => setConfigModal(null)} className="rounded-lg px-4 py-2 text-xs text-content-muted hover:text-content-primary transition-colors">Cancelar</button>
                <button onClick={handleSavePlugin} className="rounded-lg bg-accent px-4 py-2 text-xs text-white hover:bg-accent-hover transition-colors shadow-glow-sm">Salvar</button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
