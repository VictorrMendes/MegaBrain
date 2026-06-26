"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Fact, type Observation } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Spinner } from "@/components/ui";
import {
  BookOpenIcon,
  DatabaseIcon,
  LightbulbIcon,
  SearchIcon,
  XIcon,
} from "lucide-react";

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

function confidenceBadge(v: number): BadgeVariant {
  if (v >= 0.8) return "success";
  if (v >= 0.5) return "warning";
  return "error";
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function KnowledgePage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [facts,        setFacts]        = useState<Fact[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading,      setLoading]      = useState(false);
  const [tab,          setTab]          = useState<"facts" | "observations">("facts");
  const [search,       setSearch]       = useState("");

  // ─── load ───
  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    Promise.all([api.listFacts(workspace.id), api.listObservations(workspace.id)])
      .then(([fs, obs]) => { setFacts(fs); setObservations(obs); })
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  // ─── derived ───
  const filteredFacts = useMemo(() => {
    const q = search.toLowerCase();
    return q
      ? facts.filter((f) => f.statement.toLowerCase().includes(q))
      : facts;
  }, [facts, search]);

  const filteredObs = useMemo(() => {
    const q = search.toLowerCase();
    return q
      ? observations.filter((o) => o.statement.toLowerCase().includes(q))
      : observations;
  }, [observations, search]);

  const avgConfidence = facts.length > 0
    ? Math.round(facts.reduce((s, f) => s + f.confidence, 0) / facts.length * 100)
    : 0;

  const activeObs = observations.filter((o) => !o.expired);

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
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-1">
            <BookOpenIcon size={14} className="text-content-muted" />
            <h1 className="text-md font-semibold text-content-primary">Base de Conhecimento</h1>
          </div>
          <p className="text-xs text-content-muted">
            {facts.length} fatos · {avgConfidence}% confiança média
            {activeObs.length > 0 && ` · ${activeObs.length} observações ativas`}
          </p>
        </div>

        {/* ── Search ── */}
        <div className="relative mb-5">
          <SearchIcon size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-content-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Filtrar ${tab === "facts" ? "fatos" : "observações"}…`}
            className={cn(
              "w-full rounded-lg border py-2 pl-9 pr-9 text-sm",
              "border-[var(--border-default)] bg-[var(--surface-raised)]",
              "text-content-primary placeholder:text-content-placeholder",
              "focus:outline-none focus:border-[var(--border-accent)] transition-colors",
            )}
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-content-muted hover:text-content-secondary"
            >
              <XIcon size={13} />
            </button>
          )}
        </div>

        {/* ── Tab selector ── */}
        <div className="mb-6 flex gap-1.5">
          <TabChip
            active={tab === "facts"}
            onClick={() => setTab("facts")}
            icon={<DatabaseIcon size={12} />}
            count={search ? filteredFacts.length : facts.length}
          >
            Fatos
          </TabChip>
          <TabChip
            active={tab === "observations"}
            onClick={() => setTab("observations")}
            icon={<LightbulbIcon size={12} />}
            count={search ? filteredObs.length : observations.length}
          >
            Observações
          </TabChip>
        </div>

        {/* ── Facts ── */}
        {tab === "facts" && (
          <>
            {filteredFacts.length === 0 ? (
              <EmptyState tab="facts" hasSearch={Boolean(search)} />
            ) : (
              <div className="space-y-2 animate-fade-in">
                {filteredFacts.map((f) => (
                  <FactCard key={f.id} fact={f} searchQuery={search} />
                ))}
              </div>
            )}
          </>
        )}

        {/* ── Observations ── */}
        {tab === "observations" && (
          <>
            {filteredObs.length === 0 ? (
              <EmptyState tab="observations" hasSearch={Boolean(search)} />
            ) : (
              <div className="space-y-2 animate-fade-in">
                {filteredObs.map((o) => (
                  <ObservationCard key={o.id} obs={o} searchQuery={search} />
                ))}
              </div>
            )}
          </>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

function TabChip({
  active, onClick, icon, count, children,
}: {
  active:   boolean;
  onClick:  () => void;
  icon:     React.ReactNode;
  count:    number;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
        "transition-colors",
        active
          ? "border-accent-subtle bg-accent-dim text-accent"
          : "border-[var(--border-subtle)] text-content-secondary hover:border-[var(--border-default)] hover:text-content-primary",
      )}
    >
      <span className={active ? "text-accent" : "text-content-muted"}>{icon}</span>
      {children}
      <span className={cn("rounded px-1 text-[10px]", active ? "bg-accent/20 text-accent" : "text-content-muted")}>
        {count}
      </span>
    </button>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct     = Math.round(value * 100);
  const variant = confidenceBadge(value);
  const barColor = {
    success: "bg-status-success",
    warning: "bg-status-warning",
    error:   "bg-status-error",
  }[variant] ?? "bg-content-muted";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-20 rounded-full bg-[var(--surface-subtle)] overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <Badge variant={variant} size="sm">{pct}%</Badge>
    </div>
  );
}

function HighlightText({
  text, query,
}: {
  text:  string;
  query: string;
}) {
  if (!query) return <>{text}</>;
  const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase() ? (
          <mark key={i} className="bg-accent-dim text-accent rounded px-0.5">{part}</mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

function FactCard({ fact: f, searchQuery }: { fact: Fact; searchQuery: string }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "p-4 transition-colors hover:border-[var(--border-default)]",
      )}
    >
      <p className="text-sm text-content-primary leading-relaxed">
        <HighlightText text={f.statement} query={searchQuery} />
      </p>

      <div className="mt-3 flex items-center gap-3 flex-wrap">
        <ConfidenceBar value={f.confidence} />
        <Badge variant="default" size="sm">{f.source_type}</Badge>
        {f.entity_id && (
          <span className="text-[11px] text-content-muted truncate max-w-32">
            entidade: {f.entity_id}
          </span>
        )}
        <span className="ml-auto text-[11px] text-content-muted">{rel(f.created_at)}</span>
      </div>
    </div>
  );
}

function ObservationCard({ obs: o, searchQuery }: { obs: Observation; searchQuery: string }) {
  const reinforcementW = Math.min(100, o.reinforcement_count * 20);

  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        o.expired
          ? "border-[var(--border-subtle)] bg-[var(--surface-inset)] opacity-50"
          : "border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-[var(--border-default)]",
      )}
    >
      <div className="flex items-start gap-2">
        <p className="flex-1 text-sm text-content-primary leading-relaxed">
          <HighlightText text={o.statement} query={searchQuery} />
        </p>
        {o.expired && (
          <Badge variant="muted" size="sm">expirado</Badge>
        )}
      </div>

      <div className="mt-3 space-y-2">
        {/* Confidence */}
        <ConfidenceBar value={o.confidence} />

        {/* Reinforcement */}
        {o.reinforcement_count > 0 && (
          <div className="flex items-center gap-2">
            <div className="h-1 w-20 rounded-full bg-[var(--surface-subtle)] overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{ width: `${reinforcementW}%` }}
              />
            </div>
            <span className="text-[11px] text-content-muted">
              {o.reinforcement_count} reforço{o.reinforcement_count !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>

      <div className="mt-2.5 flex items-center gap-2 flex-wrap">
        <Badge variant="default" size="sm">{o.derived_from}</Badge>
        <span className="ml-auto text-[11px] text-content-muted">{rel(o.created_at)}</span>
      </div>
    </div>
  );
}

function EmptyState({ tab, hasSearch }: { tab: "facts" | "observations"; hasSearch: boolean }) {
  return (
    <p className="py-16 text-center text-sm text-content-muted">
      {hasSearch
        ? `Nenhum${tab === "facts" ? " fato" : "a observação"} corresponde à busca.`
        : tab === "facts"
          ? "Nenhum fato registrado ainda."
          : "Nenhuma observação registrada ainda."}
    </p>
  );
}
