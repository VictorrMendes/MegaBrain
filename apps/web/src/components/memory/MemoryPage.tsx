"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Memory } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Spinner } from "@/components/ui";
import {
  ArrowDownUpIcon,
  BrainIcon,
  SearchIcon,
  XIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const TYPE_BADGE: Record<string, BadgeVariant> = {
  semantic:    "active",
  episodic:    "info",
  procedural:  "default",
  declarative: "success",
};

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function rel(s: string): string {
  const diff = Date.now() - new Date(s).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)  return "agora";
  if (m < 60) return `${m}m atrás`;
  const h = Math.floor(m / 60);
  if (h < 24) return `há ${h}h`;
  return `há ${Math.floor(h / 24)}d`;
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function MemoryPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [allMemories,  setAllMemories]  = useState<Memory[]>([]);
  const [memories,     setMemories]     = useState<Memory[]>([]);
  const [loading,      setLoading]      = useState(false);
  const [query,        setQuery]        = useState("");
  const [searching,    setSearching]    = useState(false);
  const [isRecall,     setIsRecall]     = useState(false);
  const [typeFilter,   setTypeFilter]   = useState<string>("all");
  const [sortBy,       setSortBy]       = useState<"importance" | "date">("importance");

  // ─── load ───
  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    api.listMemories(workspace.id, 200)
      .then((mems) => { setAllMemories(mems); setMemories(mems); })
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  // ─── semantic recall ───
  async function recall() {
    if (!workspace || !query.trim()) return;
    setSearching(true);
    setIsRecall(true);
    try {
      const results = await api.recallMemories(workspace.id, query);
      setMemories(results);
      setTypeFilter("all");
    } finally {
      setSearching(false);
    }
  }

  async function reset() {
    if (!workspace) return;
    setSearching(true);
    setQuery("");
    setIsRecall(false);
    try {
      const mems = await api.listMemories(workspace.id, 200);
      setAllMemories(mems);
      setMemories(mems);
    } finally {
      setSearching(false);
    }
  }

  // ─── derived ───
  const allTypes = useMemo(
    () => [...new Set(allMemories.map((m) => m.type))].sort(),
    [allMemories],
  );

  const filtered = useMemo(() => {
    let list = typeFilter === "all" ? memories : memories.filter((m) => m.type === typeFilter);
    list = [...list];
    if (sortBy === "importance") list.sort((a, b) => b.importance - a.importance);
    else list.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    return list;
  }, [memories, typeFilter, sortBy]);

  const avgImportance = allMemories.length > 0
    ? Math.round(allMemories.reduce((s, m) => s + m.importance, 0) / allMemories.length * 100)
    : 0;

  // ─── loading ───
  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-6 py-8">

        {/* ── Header ── */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BrainIcon size={14} className="text-content-muted" />
              <h1 className="text-md font-semibold text-content-primary">Memórias</h1>
            </div>
            <p className="text-xs text-content-muted">
              {allMemories.length} registros · importância média {avgImportance}%
            </p>
          </div>

          {/* Sort toggle */}
          <button
            onClick={() => setSortBy((v) => v === "importance" ? "date" : "importance")}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs",
              "border border-[var(--border-default)] text-content-secondary",
              "hover:border-[var(--border-strong)] hover:text-content-primary transition-colors",
            )}
          >
            <ArrowDownUpIcon size={12} />
            {sortBy === "importance" ? "Por importância" : "Por data"}
          </button>
        </div>

        {/* ── Recall search ── */}
        <div className="mb-5 flex gap-2">
          <div className="relative flex-1">
            <SearchIcon size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-content-muted" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && recall()}
              placeholder="Busca semântica por relevância…"
              className={cn(
                "w-full rounded-lg border py-2 pl-9 pr-3 text-sm",
                "border-[var(--border-default)] bg-[var(--surface-raised)]",
                "text-content-primary placeholder:text-content-placeholder",
                "focus:outline-none focus:border-[var(--border-accent)]",
                "transition-colors",
              )}
            />
          </div>
          {query.trim() ? (
            <button
              onClick={recall}
              disabled={searching}
              className={cn(
                "rounded-lg border px-3 py-2 text-sm",
                "border-accent bg-accent-dim text-accent",
                "hover:bg-accent-subtle transition-colors disabled:opacity-40",
              )}
            >
              {searching ? <Spinner size="sm" className="text-accent" /> : "Buscar"}
            </button>
          ) : isRecall ? (
            <button
              onClick={reset}
              disabled={searching}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm",
                "border-[var(--border-default)] text-content-secondary",
                "hover:border-[var(--border-strong)] transition-colors disabled:opacity-40",
              )}
            >
              <XIcon size={13} /> Limpar
            </button>
          ) : null}
        </div>

        {/* ── Recall context banner ── */}
        {isRecall && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-accent-subtle bg-accent-subtle px-3 py-2">
            <span className="text-xs text-accent">
              Mostrando {filtered.length} memórias relevantes para "{query}"
            </span>
            <button onClick={reset} className="ml-auto text-content-muted hover:text-content-secondary">
              <XIcon size={12} />
            </button>
          </div>
        )}

        {/* ── Type filter chips ── */}
        {!isRecall && allTypes.length > 1 && (
          <div className="mb-5 flex flex-wrap gap-1.5">
            <TypeChip active={typeFilter === "all"} onClick={() => setTypeFilter("all")}>
              Todos <span className="text-content-muted">({allMemories.length})</span>
            </TypeChip>
            {allTypes.map((t) => (
              <TypeChip key={t} active={typeFilter === t} onClick={() => setTypeFilter(t)}>
                {t}
                <span className="text-content-muted">
                  ({allMemories.filter((m) => m.type === t).length})
                </span>
              </TypeChip>
            ))}
          </div>
        )}

        {/* ── Memory list ── */}
        {filtered.length === 0 ? (
          <p className="py-16 text-center text-sm text-content-muted">
            Nenhuma memória encontrada.
          </p>
        ) : (
          <div className="space-y-2 animate-fade-in">
            {filtered.map((m) => (
              <MemoryCard key={m.id} memory={m} />
            ))}
          </div>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

function TypeChip({
  active, onClick, children,
}: {
  active:   boolean;
  onClick:  () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium",
        "border transition-colors",
        active
          ? "border-accent-subtle bg-accent-dim text-accent"
          : "border-[var(--border-subtle)] text-content-secondary hover:border-[var(--border-default)] hover:text-content-primary",
      )}
    >
      {children}
    </button>
  );
}

function MemoryCard({ memory: m }: { memory: Memory }) {
  const pct    = Math.round(m.importance * 100);
  const variant = TYPE_BADGE[m.type] ?? "default";

  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "p-4 transition-colors hover:border-[var(--border-default)]",
      )}
    >
      {/* Content */}
      <p className="text-sm text-content-primary leading-relaxed">{m.content}</p>

      {/* Importance bar */}
      <div className="mt-3 flex items-center gap-2">
        <div className="flex-1 h-1 rounded-full bg-[var(--surface-subtle)] overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all",
              pct >= 80 ? "bg-status-error" :
              pct >= 60 ? "bg-status-warning" :
              pct >= 40 ? "bg-status-success" :
              "bg-content-muted",
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[11px] text-content-muted tabular-nums w-7 text-right">
          {pct}%
        </span>
      </div>

      {/* Meta */}
      <div className="mt-2.5 flex items-center gap-2 flex-wrap">
        <Badge variant={variant} size="sm">{m.type}</Badge>
        {m.source && (
          <span className="text-[11px] text-content-muted">{m.source}</span>
        )}
        <span className="ml-auto text-[11px] text-content-muted">
          {rel(m.updated_at)}
        </span>
      </div>
    </div>
  );
}
