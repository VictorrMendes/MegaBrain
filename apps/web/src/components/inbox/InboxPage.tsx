"use client";

import { useEffect, useState } from "react";
import { api, type InboxItem } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import {
  InboxIcon, LoaderIcon, CheckIcon, XIcon, PlusIcon, SendIcon,
} from "lucide-react";

const STATUS_COLOR: Record<string, string> = {
  pending:    "text-yellow-400 bg-yellow-950",
  processing: "text-blue-400 bg-blue-950",
  processed:  "text-emerald-400 bg-emerald-950",
  dismissed:  "text-neutral-500 bg-neutral-900",
  failed:     "text-red-400 bg-red-950",
};

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

export function InboxPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    api.listInbox(workspace.id)
      .then(setItems)
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  async function submit() {
    if (!workspace || !newContent.trim()) return;
    setSubmitting(true);
    try {
      const item = await api.submitInbox(workspace.id, newContent.trim());
      setItems((prev) => [item, ...prev]);
      setNewContent("");
      setShowNew(false);
    } finally {
      setSubmitting(false);
    }
  }

  async function processItem(id: string) {
    if (!workspace) return;
    setActionId(id);
    try {
      const updated = await api.processInboxItem(workspace.id, id);
      setItems((prev) => prev.map((i) => i.id === id ? updated : i));
    } finally {
      setActionId(null);
    }
  }

  async function dismissItem(id: string) {
    if (!workspace) return;
    setActionId(id);
    try {
      const updated = await api.dismissInboxItem(workspace.id, id);
      setItems((prev) => prev.map((i) => i.id === id ? updated : i));
    } finally {
      setActionId(null);
    }
  }

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoaderIcon size={20} className="animate-spin text-neutral-500" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-4 flex items-center gap-2">
          <InboxIcon size={15} className="text-neutral-400" />
          <h1 className="text-sm font-semibold text-neutral-300">Inbox</h1>
          <span className="ml-auto text-xs text-neutral-600">{items.length} itens</span>
          <button
            onClick={() => setShowNew((v) => !v)}
            className="flex items-center gap-1 rounded-md bg-neutral-800 px-2 py-1 text-xs text-neutral-300 hover:bg-neutral-700"
          >
            <PlusIcon size={12} />
            Novo
          </button>
        </div>

        {/* New item form */}
        {showNew && (
          <div className="mb-4 rounded-lg border border-neutral-700 p-4 bg-neutral-900">
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Cole um texto, link, nota, ou qualquer conteúdo para processar…"
              rows={4}
              className="w-full resize-none bg-transparent text-xs text-neutral-200 placeholder:text-neutral-600 focus:outline-none"
            />
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => setShowNew(false)}
                className="rounded px-3 py-1.5 text-xs text-neutral-500 hover:text-neutral-400"
              >
                Cancelar
              </button>
              <button
                onClick={submit}
                disabled={!newContent.trim() || submitting}
                className="flex items-center gap-1.5 rounded-md bg-blue-900 px-3 py-1.5 text-xs text-blue-200 hover:bg-blue-800 disabled:opacity-50"
              >
                {submitting ? <LoaderIcon size={12} className="animate-spin" /> : <SendIcon size={12} />}
                Enviar
              </button>
            </div>
          </div>
        )}

        {/* Items */}
        {items.length === 0 ? (
          <p className="text-center text-xs text-neutral-600 py-10">Inbox vazio.</p>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.id}
                className={cn(
                  "rounded-lg border border-neutral-800 p-4",
                  item.status === "dismissed" && "opacity-50"
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    {item.title && (
                      <p className="text-xs font-medium text-neutral-200 mb-1">{item.title}</p>
                    )}
                    <p className="text-xs text-neutral-400 line-clamp-3">{item.raw_content}</p>
                    {item.routing_notes && (
                      <p className="mt-2 text-[10px] text-neutral-600 italic">{item.routing_notes}</p>
                    )}
                    <div className="mt-2 flex items-center gap-2 text-[10px] text-neutral-600 flex-wrap">
                      <span className={cn("rounded px-1.5 py-0.5 font-medium", STATUS_COLOR[item.status] ?? "text-neutral-500 bg-neutral-800")}>
                        {item.status}
                      </span>
                      <span>fonte: {item.source}</span>
                      <span>tipo: {item.type}</span>
                      {item.mission_id && <span>missão: {item.mission_id.slice(0, 8)}…</span>}
                      <span className="ml-auto">{formatDate(item.created_at)}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  {item.status === "pending" && (
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => processItem(item.id)}
                        disabled={actionId === item.id}
                        title="Processar"
                        className="rounded p-1.5 text-emerald-600 hover:text-emerald-400 hover:bg-emerald-950 transition-colors disabled:opacity-50"
                      >
                        {actionId === item.id
                          ? <LoaderIcon size={13} className="animate-spin" />
                          : <CheckIcon size={13} />}
                      </button>
                      <button
                        onClick={() => dismissItem(item.id)}
                        disabled={actionId === item.id}
                        title="Dispensar"
                        className="rounded p-1.5 text-neutral-600 hover:text-red-400 hover:bg-red-950 transition-colors disabled:opacity-50"
                      >
                        <XIcon size={13} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
