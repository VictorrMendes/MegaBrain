"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type InboxItem } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Button, Spinner } from "@/components/ui";
import {
  CheckIcon,
  InboxIcon,
  PlusIcon,
  SendIcon,
  XIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, BadgeVariant> = {
  pending:    "warning",
  processing: "info",
  processed:  "success",
  dismissed:  "muted",
  failed:     "error",
};

type StatusFilter = "all" | "pending" | "processed" | "dismissed";

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function InboxPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [items,      setItems]      = useState<InboxItem[]>([]);
  const [loading,    setLoading]    = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [showNew,    setShowNew]    = useState(false);
  const [actionId,   setActionId]   = useState<string | null>(null);
  const [filter,     setFilter]     = useState<StatusFilter>("all");

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

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((i) => i.status === filter);
  }, [items, filter]);

  const pending = items.filter((i) => i.status === "pending").length;

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 py-6 sm:py-8">

        {/* ── Header ── */}
        <div className="mb-6 flex items-center gap-2">
          <InboxIcon size={14} className="text-content-muted" />
          <h1 className="text-md font-semibold text-content-primary">Inbox</h1>
          {pending > 0 && <Badge variant="warning" size="sm">{pending} pendente{pending !== 1 ? "s" : ""}</Badge>}
          <span className="ml-auto text-xs text-content-muted">{items.length} itens</span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowNew((v) => !v)}
          >
            <PlusIcon size={12} className="mr-1.5" />
            Novo
          </Button>
        </div>

        {/* ── New item form ── */}
        {showNew && (
          <div
            className={cn(
              "mb-5 rounded-lg border border-[var(--border-default)]",
              "bg-[var(--surface-raised)] p-4 animate-fade-in",
            )}
          >
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
              }}
              placeholder="Cole um texto, link, nota, ou qualquer conteúdo para processar…"
              rows={4}
              className={cn(
                "w-full resize-none rounded bg-transparent text-sm",
                "text-content-primary placeholder:text-content-placeholder",
                "focus:outline-none",
              )}
            />
            <div className="mt-3 flex items-center justify-between">
              <span className="text-[11px] text-content-muted">Ctrl+Enter para enviar</span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowNew(false)}
                >
                  Cancelar
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={submit}
                  disabled={!newContent.trim() || submitting}
                >
                  {submitting
                    ? <Spinner size="sm" className="text-white mr-1.5" />
                    : <SendIcon size={12} className="mr-1.5" />}
                  Enviar
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* ── Filter chips ── */}
        {items.length > 0 && (
          <div className="mb-5 flex flex-wrap gap-1.5">
            {([
              { key: "all",       label: "Todos",       count: items.length },
              { key: "pending",   label: "Pendente",    count: items.filter((i) => i.status === "pending").length },
              { key: "processed", label: "Processado",  count: items.filter((i) => i.status === "processed").length },
              { key: "dismissed", label: "Dispensado",  count: items.filter((i) => i.status === "dismissed").length },
            ] as { key: StatusFilter; label: string; count: number }[]).map(({ key, label, count }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={cn(
                  "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
                  "border transition-colors",
                  filter === key
                    ? "border-accent-subtle bg-accent-dim text-accent"
                    : "border-[var(--border-subtle)] text-content-secondary hover:border-[var(--border-default)] hover:text-content-primary",
                )}
              >
                {label}
                <span
                  className={cn(
                    "rounded px-1 text-[10px]",
                    filter === key ? "bg-accent/20 text-accent" : "text-content-muted",
                  )}
                >
                  {count}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* ── Items ── */}
        {filtered.length === 0 ? (
          <p className="py-16 text-center text-sm text-content-muted">
            {items.length === 0 ? "Inbox vazio." : "Nenhum item neste filtro."}
          </p>
        ) : (
          <div className="space-y-2 animate-fade-in">
            {filtered.map((item) => (
              <InboxCard
                key={item.id}
                item={item}
                actionId={actionId}
                onProcess={processItem}
                onDismiss={dismissItem}
              />
            ))}
          </div>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Sub-component
// ─────────────────────────────────────────────────────────────

function InboxCard({
  item, actionId, onProcess, onDismiss,
}: {
  item:      InboxItem;
  actionId:  string | null;
  onProcess: (id: string) => void;
  onDismiss: (id: string) => void;
}) {
  const busy = actionId === item.id;

  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4",
        "transition-colors hover:border-[var(--border-default)]",
        item.status === "dismissed" && "opacity-50",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {item.title && (
            <p className="mb-1 text-sm font-medium text-content-primary">{item.title}</p>
          )}
          <p className="text-sm text-content-secondary line-clamp-3">{item.raw_content}</p>
          {item.routing_notes && (
            <p className="mt-2 text-[11px] italic text-content-muted">{item.routing_notes}</p>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant={STATUS_BADGE[item.status] ?? "default"} size="sm">
              {item.status}
            </Badge>
            <span className="text-[11px] text-content-muted">fonte: {item.source}</span>
            <span className="text-[11px] text-content-muted">tipo: {item.type}</span>
            {item.mission_id && (
              <span className="text-[11px] text-content-muted">
                missão: {item.mission_id.slice(0, 8)}…
              </span>
            )}
            <span className="ml-auto text-[11px] text-content-muted tabular-nums">
              {formatDate(item.created_at)}
            </span>
          </div>
        </div>

        {/* Actions */}
        {item.status === "pending" && (
          <div className="flex shrink-0 gap-1">
            <button
              onClick={() => onProcess(item.id)}
              disabled={busy}
              title="Processar"
              className={cn(
                "rounded p-1.5 transition-colors",
                "text-status-success hover:bg-[var(--surface-subtle)]",
                "disabled:opacity-30",
              )}
            >
              {busy ? <Spinner size="sm" className="text-status-success" /> : <CheckIcon size={13} />}
            </button>
            <button
              onClick={() => onDismiss(item.id)}
              disabled={busy}
              title="Dispensar"
              className={cn(
                "rounded p-1.5 transition-colors",
                "text-content-muted hover:text-status-error hover:bg-[var(--surface-subtle)]",
                "disabled:opacity-30",
              )}
            >
              <XIcon size={13} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
