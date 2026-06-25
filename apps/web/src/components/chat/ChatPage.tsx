"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  PlusIcon,
  MessageSquareIcon,
  LoaderIcon,
  PaperclipIcon,
  FileTextIcon,
  Trash2Icon,
} from "lucide-react";
import { api, type Conversation, type Document, type Workspace } from "@/lib/api";
import { cn } from "@/lib/cn";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import type { ChatMessageData } from "./ChatMessage";

type AppState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; workspace: Workspace };

export function ChatPage() {
  const [appState, setAppState] = useState<AppState>({ status: "loading" });
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const streamingIdRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    async function init() {
      try {
        let workspaces = await api.listWorkspaces();
        if (workspaces.length === 0) {
          const ws = await api.createWorkspace("Personal", "Workspace pessoal");
          workspaces = [ws];
        }
        const workspace = workspaces[0];
        setAppState({ status: "ready", workspace });

        const [convs, docs] = await Promise.all([
          api.listConversations(workspace.id),
          api.listDocuments(workspace.id),
        ]);
        setConversations(convs);
        setDocuments(docs);

        if (convs.length > 0) {
          await loadConversation(workspace.id, convs[0].id);
        }
      } catch (e) {
        setAppState({
          status: "error",
          message: e instanceof Error ? e.message : "Erro ao conectar na API",
        });
      }
    }
    init();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadConversation(workspaceId: string, conversationId: string) {
    setActiveConversationId(conversationId);
    const msgs = await api.getMessages(workspaceId, conversationId);
    setMessages(
      msgs
        .filter((m) => m.role !== "system")
        .map((m) => ({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
        }))
    );
  }

  async function handleNewConversation() {
    if (appState.status !== "ready") return;
    const title = `Conversa ${conversations.length + 1}`;
    const conv = await api.createConversation(appState.workspace.id, title);
    setConversations((prev) => [conv, ...prev]);
    setActiveConversationId(conv.id);
    setMessages([]);
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (appState.status !== "ready") return;
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const doc = await api.uploadDocument(appState.workspace.id, file);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDeleteDocument(docId: string) {
    if (appState.status !== "ready") return;
    await api.deleteDocument(appState.workspace.id, docId);
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
  }

  const handleSend = useCallback(
    async (content: string) => {
      if (appState.status !== "ready" || isStreaming) return;

      let conversationId = activeConversationId;

      if (!conversationId) {
        const title = content.slice(0, 40) + (content.length > 40 ? "…" : "");
        const conv = await api.createConversation(appState.workspace.id, title);
        setConversations((prev) => [conv, ...prev]);
        setActiveConversationId(conv.id);
        conversationId = conv.id;
      }

      const userMsg: ChatMessageData = {
        id: crypto.randomUUID(),
        role: "user",
        content,
      };
      const streamingId = crypto.randomUUID();
      streamingIdRef.current = streamingId;

      const assistantMsg: ChatMessageData = {
        id: streamingId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      await api.streamMessage(
        appState.workspace.id,
        conversationId,
        content,
        (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingId ? { ...m, content: m.content + chunk } : m
            )
          );
        },
        () => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingId ? { ...m, streaming: false } : m
            )
          );
          setIsStreaming(false);
        },
        (err) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingId
                ? { ...m, content: `Erro: ${err.message}`, streaming: false }
                : m
            )
          );
          setIsStreaming(false);
        }
      );
    },
    [appState, activeConversationId, isStreaming]
  );

  if (appState.status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoaderIcon size={20} className="animate-spin text-neutral-500" />
      </div>
    );
  }

  if (appState.status === "error") {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-sm text-red-400">{appState.message}</p>
          <p className="text-xs text-neutral-600">
            Verifique se a API está rodando em localhost:8100
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-neutral-950 text-neutral-100">
      {/* Sidebar */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-neutral-800 bg-neutral-900">
        <div className="flex items-center justify-between px-4 py-4 border-b border-neutral-800">
          <span className="text-xs font-semibold tracking-widest text-neutral-400 uppercase">
            Khonshu
          </span>
          <button
            onClick={handleNewConversation}
            className="flex h-7 w-7 items-center justify-center rounded-md text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
            title="Nova conversa"
          >
            <PlusIcon size={15} />
          </button>
        </div>

        {/* Conversations */}
        <nav className="flex-1 overflow-y-auto py-2 min-h-0">
          {conversations.length === 0 ? (
            <p className="px-4 py-3 text-xs text-neutral-600">Nenhuma conversa</p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => loadConversation(appState.workspace.id, conv.id)}
                className={cn(
                  "flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs transition-colors",
                  activeConversationId === conv.id
                    ? "bg-neutral-800 text-neutral-100"
                    : "text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200"
                )}
              >
                <MessageSquareIcon size={13} className="shrink-0" />
                <span className="truncate">{conv.title}</span>
              </button>
            ))
          )}
        </nav>

        {/* Documents */}
        <div className="border-t border-neutral-800 flex flex-col max-h-48">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-xs font-semibold tracking-widest text-neutral-500 uppercase">
              Documentos
            </span>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex h-7 w-7 items-center justify-center rounded-md text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100 transition-colors disabled:opacity-40"
              title="Adicionar documento"
            >
              {isUploading ? (
                <LoaderIcon size={13} className="animate-spin" />
              ) : (
                <PaperclipIcon size={13} />
              )}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              className="hidden"
              onChange={handleUpload}
            />
          </div>

          <div className="overflow-y-auto pb-2">
            {documents.length === 0 ? (
              <p className="px-4 pb-2 text-xs text-neutral-600">Nenhum documento</p>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  className="group flex items-center gap-2 px-4 py-1.5 text-xs text-neutral-400"
                >
                  {doc.status === "ready" ? (
                    <FileTextIcon size={12} className="shrink-0 text-emerald-500" />
                  ) : doc.status === "failed" ? (
                    <FileTextIcon size={12} className="shrink-0 text-red-500" />
                  ) : (
                    <LoaderIcon size={12} className="shrink-0 animate-spin" />
                  )}
                  <span className="truncate flex-1">{doc.filename}</span>
                  <button
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="hidden group-hover:flex h-5 w-5 items-center justify-center rounded text-neutral-600 hover:text-red-400 transition-colors"
                  >
                    <Trash2Icon size={11} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-12 items-center border-b border-neutral-800 px-6 shrink-0">
          <span className="text-sm text-neutral-400">
            {conversations.find((c) => c.id === activeConversationId)?.title ?? "Nova conversa"}
          </span>
        </header>

        <MessageList messages={messages} />

        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </main>
    </div>
  );
}
