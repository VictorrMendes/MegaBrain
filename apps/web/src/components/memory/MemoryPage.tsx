"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Memory } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Button, Spinner } from "@/components/ui";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/Dialog";
import {
  BrainIcon,
  CalendarIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ClockIcon,
  PlusIcon,
  SearchIcon,
  ShieldCheckIcon,
  SlidersHorizontalIcon,
  XIcon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const TYPE_BADGE: Record<string, BadgeVariant> = {
  long:      "active",
  working:   "info",
  episodic:  "default",
  semantic:  "success",
};

const TYPE_LABEL: Record<string, string> = {
  long:     "Longa duração",
  working:  "Working",
  episodic: "Episódica",
  semantic: "Semântica",
};

const SOURCE_LABEL: Record<string, string> = {
  conversation:   "Conversa",
  mission:        "Missão",
  user_explicit:  "Explícita",
  agent:          "Agente",
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
  const d = Math.floor(h / 24);
  if (d < 7)  return `há ${d}d`;
  if (d < 30) return `há ${Math.floor(d / 7)}sem`;
  return `há ${Math.floor(d / 30)}m`;
}

function absDate(s: string): string {
  return new Date(s).toLocaleDateString("pt-BR", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function groupByDate(memories: Memory[]): { label: string; items: Memory[] }[] {
  const now = new Date();
  const today     = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86_400_000);
  const weekAgo   = new Date(today.getTime() - 7 * 86_400_000);
  const monthAgo  = new Date(today.getTime() - 30 * 86_400_000);

  const groups: Record<string, Memory[]> = {
    "Hoje":         [],
    "Ontem":        [],
    "Esta semana":  [],
    "Este mês":     [],
    "Mais antigo":  [],
  };

  for (const m of memories) {
    const d = new Date(m.created_at);
    if (d >= today)         groups["Hoje"].push(m);
    else if (d >= yesterday) groups["Ontem"].push(m);
    else if (d >= weekAgo)   groups["Esta semana"].push(m);
    else if (d >= monthAgo)  groups["Este mês"].push(m);
    else                     groups["Mais antigo"].push(m);
  }

  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }));
}

function ImportanceBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-1 rounded-full bg-[var(--surface-subtle)] overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            pct >= 80 ? "bg-status-error" :
            pct >= 60 ? "bg-status-warning" :
            pct >= 40 ? "bg-accent" :
            "bg-content-muted",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-content-muted tabular-nums w-6 text-right">{pct}%</span>
    </div>
  );
}

function ConfidenceBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-1 rounded-full bg-[var(--surface-subtle)] overflow-hidden">
        <div
          className="h-full rounded-full bg-status-success transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-content-muted tabular-nums w-6 text-right">{pct}%</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Add Memory Dialog
// ─────────────────────────────────────────────────────────────

function AddMemoryDialog({
  open,
  onClose,
  onAdded,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: (m: Memory) => void;
}) {
  const { current: workspace } = useWorkspace();
  const [content, setContent]     = useState("");
  const [type, setType]           = useState("long");
  const [importance, setImportance] = useState("0.5");
  const [saving, setSaving]       = useState(false);

  async function submit() {
    if (!workspace || !content.trim()) return;
    setSaving(true);
    try {
      const m = await api.createMemory(workspace.id, {
        content: content.trim(),
        type,
        importance: parseFloat(importance),
      });
      onAdded(m);
      setContent("");
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent title="Nova Memória">
        <div className="space-y-4">
          <div>
            <label className="text-xs text-content-secondary mb-1.5 block">Conteúdo</label>
            <textarea
              autoFocus
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="O que o sistema deve lembrar…"
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm resize-none",
                "border-[var(--border-default)] bg-[var(--surface-base)]",
                "text-content-primary placeholder:text-content-placeholder",
                "focus:outline-none focus:border-[var(--border-accent)]",
              )}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-content-secondary mb-1.5 block">Tipo</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className={cn(
                  "w-full rounded-lg border px-3 py-2 text-sm",
                  "border-[var(--border-default)] bg-[var(--surface-base)]",
                  "text-content-primary focus:outline-none focus:border-[var(--border-accent)]",
                )}
              >
                {Object.entries(TYPE_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-content-secondary mb-1.5 block">
                Importância: {Math.round(parseFloat(importance) * 100)}%
              </label>
              <input
                type="range" min="0" max="1" step="0.05"
                value={importance}
                onChange={(e) => setImportance(e.target.value)}
                className="w-full accent-accent"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button onClick={submit} disabled={saving || !content.trim()}>
            {saving ? <Spinner size="sm" className="mr-2" /> : <PlusIcon size={14} className="mr-2" />}
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─────────────────────────────────────────────────────────────
// Detail Panel
// ─────────────────────────────────────────────────────────────

function MemoryDetail({ memory: m, onClose }: { memory: Memory; onClose: () => void }) {
  const daysLeft = m.expires_at
    ? Math.max(0, Math.ceil((new Date(m.expires_at).getTime() - Date.now()) / 86_400_000))
    : null;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="flex items-center gap-2">
          <button
            onClick={onClose}
            className="md:hidden flex items-center gap-1 text-xs text-content-muted hover:text-content-secondary transition-colors mr-1"
          >
            <ChevronLeftIcon size={14} />
            Voltar
          </button>
          <Badge variant={TYPE_BADGE[m.type] ?? "default"} size="sm">
            {TYPE_LABEL[m.type] ?? m.type}
          </Badge>
        </div>
        <button
          onClick={onClose}
          className="hidden md:flex rounded p-1 text-content-muted hover:text-content-primary transition-colors"
        >
          <XIcon size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Content */}
        <p className="text-sm text-content-primary leading-relaxed whitespace-pre-wrap">
          {m.content}
        </p>

        {/* Metrics */}
        <div className="space-y-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-subtle)] p-3">
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <ZapIcon size={11} className="text-content-muted" />
              <span className="text-[11px] text-content-muted">Importância</span>
            </div>
            <ImportanceBar value={m.importance} />
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <ShieldCheckIcon size={11} className="text-content-muted" />
              <span className="text-[11px] text-content-muted">Confiança</span>
            </div>
            <ConfidenceBar value={m.confidence} />
          </div>
        </div>

        {/* Meta rows */}
        <div className="space-y-2 text-xs">
          {m.source && (
            <div className="flex items-center justify-between">
              <span className="text-content-muted">Origem</span>
              <span className="text-content-secondary">
                {SOURCE_LABEL[m.source] ?? m.source}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-content-muted">Criada</span>
            <span className="text-content-secondary">{absDate(m.created_at)}</span>
          </div>
          {m.expires_at && (
            <div className="flex items-center justify-between">
              <span className="text-content-muted">Expira</span>
              <span className={cn(
                "text-content-secondary",
                daysLeft !== null && daysLeft <= 7 && "text-status-warning",
                daysLeft === 0 && "text-status-error",
              )}>
                {daysLeft === 0
                  ? "hoje"
                  : daysLeft !== null && daysLeft <= 30
                  ? `em ${daysLeft}d`
                  : absDate(m.expires_at)}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Memory card (list item)
// ─────────────────────────────────────────────────────────────

function MemoryCard({
  memory: m,
  selected,
  onClick,
}: {
  memory: Memory;
  selected: boolean;
  onClick: () => void;
}) {
  const expiringDays = m.expires_at
    ? Math.ceil((new Date(m.expires_at).getTime() - Date.now()) / 86_400_000)
    : null;
  const expiringSoon = expiringDays !== null && expiringDays <= 7;

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-lg border px-3 py-2.5 text-left transition-colors",
        "group flex items-start gap-2",
        selected
          ? "border-accent-subtle bg-accent-dim"
          : "border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-[var(--border-default)]",
      )}
    >
      <div className="flex-1 min-w-0">
        <p className="text-xs text-content-primary leading-relaxed line-clamp-2">
          {m.content}
        </p>
        <div className="mt-1.5 flex items-center gap-2">
          <ImportanceBar value={m.importance} className="flex-1" />
          <span className="text-[10px] text-content-muted shrink-0">{rel(m.created_at)}</span>
        </div>
        <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
          <Badge variant={TYPE_BADGE[m.type] ?? "default"} size="sm">
            {m.type}
          </Badge>
          {expiringSoon && (
            <span className="flex items-center gap-0.5 text-[10px] text-status-warning">
              <ClockIcon size={9} />
              expira em {expiringDays}d
            </span>
          )}
        </div>
      </div>
      <ChevronRightIcon
        size={13}
        className={cn(
          "mt-0.5 shrink-0 text-content-muted transition-opacity",
          selected ? "opacity-100 text-accent" : "opacity-0 group-hover:opacity-60",
        )}
      />
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Stats row
// ─────────────────────────────────────────────────────────────

function StatsRow({ memories }: { memories: Memory[] }) {
  const expiringSoon = memories.filter((m) => {
    if (!m.expires_at) return false;
    const d = Math.ceil((new Date(m.expires_at).getTime() - Date.now()) / 86_400_000);
    return d >= 0 && d <= 7;
  }).length;
  const avgConf = memories.length
    ? Math.round(memories.reduce((s, m) => s + m.confidence, 0) / memories.length * 100)
    : 0;
  const avgImp  = memories.length
    ? Math.round(memories.reduce((s, m) => s + m.importance, 0) / memories.length * 100)
    : 0;

  return (
    <div className="grid grid-cols-3 gap-2 mb-4">
      {[
        { icon: BrainIcon,        label: "Total",      value: memories.length.toString() },
        { icon: ShieldCheckIcon,  label: "Conf. média", value: `${avgConf}%` },
        { icon: ZapIcon,          label: "Imp. média",  value: `${avgImp}%` },
      ].map(({ icon: Icon, label, value }) => (
        <div
          key={label}
          className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-3 py-2"
        >
          <div className="flex items-center gap-1 mb-0.5">
            <Icon size={11} className="text-content-muted" />
            <span className="text-[10px] text-content-muted">{label}</span>
          </div>
          <p className="text-sm font-semibold text-content-primary tabular-nums">{value}</p>
        </div>
      ))}
      {expiringSoon > 0 && (
        <div className="col-span-3 flex items-center gap-1.5 rounded-lg border border-status-warning/30 bg-status-warning/10 px-3 py-1.5">
          <ClockIcon size={11} className="text-status-warning" />
          <span className="text-[11px] text-status-warning">
            {expiringSoon} memória{expiringSoon > 1 ? "s" : ""} expira{expiringSoon > 1 ? "m" : ""} em 7 dias
          </span>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────

export function MemoryPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [allMemories, setAllMemories] = useState<Memory[]>([]);
  const [memories,    setMemories]    = useState<Memory[]>([]);
  const [loading,     setLoading]     = useState(false);
  const [query,       setQuery]       = useState("");
  const [searching,   setSearching]   = useState(false);
  const [isRecall,    setIsRecall]    = useState(false);
  const [typeFilter,  setTypeFilter]  = useState<string>("all");
  const [sortBy,      setSortBy]      = useState<"importance" | "date">("date");
  const [selected,    setSelected]    = useState<Memory | null>(null);
  const [addOpen,     setAddOpen]     = useState(false);

  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    api.listMemories(workspace.id, 200)
      .then((mems) => { setAllMemories(mems); setMemories(mems); })
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  async function recall() {
    if (!workspace || !query.trim()) return;
    setSearching(true);
    setIsRecall(true);
    setSelected(null);
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
    setSelected(null);
    try {
      const mems = await api.listMemories(workspace.id, 200);
      setAllMemories(mems);
      setMemories(mems);
    } finally {
      setSearching(false);
    }
  }

  function handleAdded(m: Memory) {
    setAllMemories((prev) => [m, ...prev]);
    setMemories((prev) => [m, ...prev]);
    setSelected(m);
  }

  const allTypes = useMemo(
    () => [...new Set(allMemories.map((m) => m.type))].sort(),
    [allMemories],
  );

  const filtered = useMemo(() => {
    let list = typeFilter === "all" ? memories : memories.filter((m) => m.type === typeFilter);
    list = [...list];
    if (sortBy === "importance") list.sort((a, b) => b.importance - a.importance);
    else list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return list;
  }, [memories, typeFilter, sortBy]);

  const groups = useMemo(
    () => sortBy === "date" && !isRecall ? groupByDate(filtered) : [{ label: "", items: filtered }],
    [filtered, sortBy, isRecall],
  );

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <>
      <div className="flex h-full overflow-hidden">
        {/* ── Left panel ── */}
        <div className={cn(
          "flex flex-col border-r border-[var(--border-subtle)]",
          "transition-all duration-200",
          selected ? "hidden md:flex md:w-72 md:shrink-0" : "flex-1",
        )}>
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
            <div className="flex items-center gap-2">
              <BrainIcon size={14} className="text-content-muted" />
              <h1 className="text-sm font-semibold text-content-primary">Memórias</h1>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setSortBy((v) => v === "importance" ? "date" : "importance")}
                title={sortBy === "importance" ? "Ordenar por data" : "Ordenar por importância"}
                className={cn(
                  "rounded p-1.5 text-content-muted hover:text-content-primary transition-colors",
                  "hover:bg-[var(--surface-raised)]",
                )}
              >
                <SlidersHorizontalIcon size={13} />
              </button>
              <Button size="sm" onClick={() => setAddOpen(true)}>
                <PlusIcon size={13} className="mr-1" /> Nova
              </Button>
            </div>
          </div>

          {/* Search */}
          <div className="p-3 border-b border-[var(--border-subtle)]">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <SearchIcon size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-content-muted" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && recall()}
                  placeholder="Busca semântica…"
                  className={cn(
                    "w-full rounded-md border py-1.5 pl-7 pr-2 text-xs",
                    "border-[var(--border-default)] bg-[var(--surface-base)]",
                    "text-content-primary placeholder:text-content-placeholder",
                    "focus:outline-none focus:border-[var(--border-accent)]",
                  )}
                />
              </div>
              {query.trim() ? (
                <button
                  onClick={recall}
                  disabled={searching}
                  className="rounded-md border border-accent bg-accent-dim px-2.5 text-xs text-accent hover:bg-accent-subtle disabled:opacity-40"
                >
                  {searching ? <Spinner size="sm" className="text-accent" /> : "Buscar"}
                </button>
              ) : isRecall ? (
                <button
                  onClick={reset}
                  disabled={searching}
                  className="rounded-md border border-[var(--border-default)] px-2 text-content-secondary hover:border-[var(--border-strong)]"
                >
                  <XIcon size={12} />
                </button>
              ) : null}
            </div>
          </div>

          {/* Stats (only when not searching / not filtered) */}
          {!isRecall && typeFilter === "all" && allMemories.length > 0 && !selected && (
            <div className="px-3 pt-3">
              <StatsRow memories={allMemories} />
            </div>
          )}

          {/* Type filter chips */}
          {!isRecall && allTypes.length > 1 && (
            <div className="flex flex-wrap gap-1.5 px-3 pt-2">
              <TypeChip active={typeFilter === "all"} onClick={() => setTypeFilter("all")}>
                Todos ({allMemories.length})
              </TypeChip>
              {allTypes.map((t) => (
                <TypeChip key={t} active={typeFilter === t} onClick={() => setTypeFilter(t)}>
                  {t} ({allMemories.filter((m) => m.type === t).length})
                </TypeChip>
              ))}
            </div>
          )}

          {/* Recall banner */}
          {isRecall && (
            <div className="mx-3 mt-2 flex items-center gap-2 rounded-md border border-accent/30 bg-accent-dim px-2.5 py-1.5">
              <span className="flex-1 text-[11px] text-accent">
                {filtered.length} resultado{filtered.length !== 1 ? "s" : ""} para &ldquo;{query}&rdquo;
              </span>
              <button onClick={reset} className="text-accent/70 hover:text-accent">
                <XIcon size={11} />
              </button>
            </div>
          )}

          {/* Memory list */}
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
            {filtered.length === 0 ? (
              <p className="py-12 text-center text-xs text-content-muted">
                Nenhuma memória.
              </p>
            ) : (
              groups.map((g) => (
                <div key={g.label}>
                  {g.label && (
                    <div className="flex items-center gap-2 py-1.5">
                      <CalendarIcon size={10} className="text-content-muted" />
                      <span className="text-[10px] font-medium text-content-muted uppercase tracking-wider">
                        {g.label}
                      </span>
                    </div>
                  )}
                  <div className="space-y-1">
                    {g.items.map((m) => (
                      <MemoryCard
                        key={m.id}
                        memory={m}
                        selected={selected?.id === m.id}
                        onClick={() => setSelected((prev) => prev?.id === m.id ? null : m)}
                      />
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ── Detail panel ── */}
        {selected && (
          <div className="flex-1 overflow-hidden animate-fade-in">
            <MemoryDetail memory={selected} onClose={() => setSelected(null)} />
          </div>
        )}
      </div>

      <AddMemoryDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onAdded={handleAdded}
      />
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// TypeChip
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
        "rounded-full px-2.5 py-0.5 text-[11px] font-medium border transition-colors",
        active
          ? "border-accent-subtle bg-accent-dim text-accent"
          : "border-[var(--border-subtle)] text-content-secondary hover:border-[var(--border-default)]",
      )}
    >
      {children}
    </button>
  );
}
