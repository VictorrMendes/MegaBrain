"use client";

import { useEffect, useMemo, useState } from "react";
import {
  api,
  type Fact,
  type KnowledgeEntity,
  type KnowledgeRelation,
  type Observation,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Spinner } from "@/components/ui";
import {
  ArrowRightIcon,
  BookOpenIcon,
  BoxIcon,
  BuildingIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CpuIcon,
  DatabaseIcon,
  FileTextIcon,
  GitBranchIcon,
  LightbulbIcon,
  MapPinIcon,
  NetworkIcon,
  SearchIcon,
  UserIcon,
  XIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Entity type metadata
// ─────────────────────────────────────────────────────────────

type EntityType =
  | "person" | "service" | "device" | "concept"
  | "place" | "organization" | "document" | "other";

const ENTITY_ICON: Record<EntityType, React.ReactNode> = {
  person:       <UserIcon size={12} />,
  service:      <NetworkIcon size={12} />,
  device:       <CpuIcon size={12} />,
  concept:      <LightbulbIcon size={12} />,
  place:        <MapPinIcon size={12} />,
  organization: <BuildingIcon size={12} />,
  document:     <FileTextIcon size={12} />,
  other:        <BoxIcon size={12} />,
};

const ENTITY_COLOR: Record<EntityType, string> = {
  person:       "text-blue-400 bg-blue-400/10",
  service:      "text-purple-400 bg-purple-400/10",
  device:       "text-green-400 bg-green-400/10",
  concept:      "text-yellow-400 bg-yellow-400/10",
  place:        "text-orange-400 bg-orange-400/10",
  organization: "text-pink-400 bg-pink-400/10",
  document:     "text-content-muted bg-[var(--surface-subtle)]",
  other:        "text-content-muted bg-[var(--surface-subtle)]",
};

const ENTITY_TYPE_LABEL: Record<EntityType, string> = {
  person:       "Pessoa",
  service:      "Serviço",
  device:       "Dispositivo",
  concept:      "Conceito",
  place:        "Local",
  organization: "Organização",
  document:     "Documento",
  other:        "Outro",
};

function entityIcon(type: string) {
  return ENTITY_ICON[type as EntityType] ?? <BoxIcon size={12} />;
}
function entityColor(type: string) {
  return ENTITY_COLOR[type as EntityType] ?? "text-content-muted bg-[var(--surface-subtle)]";
}
function entityTypeLabel(type: string) {
  return ENTITY_TYPE_LABEL[type as EntityType] ?? type;
}

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

function ConfidenceBar({ value }: { value: number }) {
  const pct     = Math.round(value * 100);
  const variant = confidenceBadge(value);
  const barColor = ({
    success: "bg-status-success",
    warning: "bg-status-warning",
    error:   "bg-status-error",
    active:  "bg-accent",
    info:    "bg-blue-400",
    default: "bg-content-muted",
    muted:   "bg-content-muted",
  } satisfies Record<BadgeVariant, string>)[variant];

  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 rounded-full bg-[var(--surface-subtle)] overflow-hidden">
        <div className={cn("h-full rounded-full", barColor)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-content-muted tabular-nums">{pct}%</span>
    </div>
  );
}

function HighlightText({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>;
  const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
  return (
    <>
      {parts.map((p, i) =>
        p.toLowerCase() === query.toLowerCase()
          ? <mark key={i} className="bg-accent-dim text-accent rounded px-0.5">{p}</mark>
          : p
      )}
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// Entity pill (small chip used in relation cards)
// ─────────────────────────────────────────────────────────────

function EntityChip({
  entity,
  onClick,
  highlight,
}: {
  entity:    KnowledgeEntity;
  onClick?:  () => void;
  highlight?: boolean;
}) {
  const color = entityColor(entity.type);
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md border px-2 py-1",
        "text-xs font-medium transition-colors",
        highlight
          ? "border-accent bg-accent-dim text-accent"
          : "border-[var(--border-default)] bg-[var(--surface-raised)] text-content-secondary hover:text-content-primary hover:border-accent",
      )}
    >
      <span className={cn("flex items-center rounded p-0.5", color)}>
        {entityIcon(entity.type)}
      </span>
      {entity.name}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Relation card
// ─────────────────────────────────────────────────────────────

function RelationCard({
  relation,
  entities,
  selectedId,
  onSelectEntity,
}: {
  relation:       KnowledgeRelation;
  entities:       Map<string, KnowledgeEntity>;
  selectedId:     string;
  onSelectEntity: (id: string) => void;
}) {
  const source = entities.get(relation.source_entity_id);
  const target = entities.get(relation.target_entity_id);
  if (!source || !target) return null;

  const isOutgoing = relation.source_entity_id === selectedId;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border border-[var(--border-subtle)]",
        "bg-[var(--surface-raised)] px-3 py-2.5",
        "hover:border-[var(--border-default)] transition-colors",
      )}
    >
      <EntityChip
        entity={source}
        highlight={!isOutgoing}
        onClick={!isOutgoing ? () => onSelectEntity(source.id) : undefined}
      />

      <div className="flex items-center gap-1 shrink-0">
        <div className="h-px w-4 bg-[var(--border-default)]" />
        <span
          className={cn(
            "rounded border px-1.5 py-0.5 text-[10px] font-mono",
            "border-[var(--border-subtle)] bg-[var(--surface-inset)] text-content-muted",
          )}
        >
          {relation.relation}
        </span>
        <ArrowRightIcon size={10} className="text-content-muted" />
        <div className="h-px w-4 bg-[var(--border-default)]" />
      </div>

      <EntityChip
        entity={target}
        highlight={isOutgoing}
        onClick={isOutgoing ? () => onSelectEntity(target.id) : undefined}
      />

      <span className="ml-auto text-[10px] text-content-muted tabular-nums">
        {Math.round(relation.confidence * 100)}%
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Entity detail panel
// ─────────────────────────────────────────────────────────────

function EntityDetailPanel({
  entity,
  allEntities,
  allRelations,
  facts,
  onSelectEntity,
  onBack,
}: {
  entity:         KnowledgeEntity;
  allEntities:    Map<string, KnowledgeEntity>;
  allRelations:   KnowledgeRelation[];
  facts:          Fact[];
  onSelectEntity: (id: string) => void;
  onBack?:        () => void;
}) {
  const entityRelations = allRelations.filter(
    (r) => r.source_entity_id === entity.id || r.target_entity_id === entity.id,
  );
  const entityFacts = facts.filter((f) => f.entity_id === entity.id);
  const color = entityColor(entity.type);

  return (
    <div className="flex h-full flex-col overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="shrink-0 border-b border-[var(--border-subtle)] px-4 sm:px-6 py-4 sm:py-5">
        {onBack && (
          <button
            onClick={onBack}
            className="md:hidden mb-3 flex items-center gap-1 text-xs text-content-muted hover:text-content-secondary transition-colors"
          >
            <ChevronLeftIcon size={14} />
            Entidades
          </button>
        )}
        <div className="flex items-start gap-3">
          <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", color)}>
            {entityIcon(entity.type)}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-content-primary">{entity.name}</h2>
            <div className="mt-1 flex items-center gap-2 flex-wrap">
              <Badge variant="default" size="sm">{entityTypeLabel(entity.type)}</Badge>
              <span className="text-[11px] text-content-muted">{rel(entity.created_at)}</span>
            </div>
          </div>
        </div>

        {entity.aliases.length > 0 && (
          <div className="mt-3 flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-content-muted">também conhecido como:</span>
            {entity.aliases.map((a) => (
              <span
                key={a}
                className="rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-1.5 py-0.5 text-[10px] text-content-secondary"
              >
                {a}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-8">

        {/* Relations */}
        <div>
          <div className="flex items-center gap-1.5 mb-3">
            <GitBranchIcon size={12} className="text-content-muted" />
            <h3 className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
              Relações
              {entityRelations.length > 0 && (
                <span className="ml-1.5 rounded bg-accent-dim px-1 text-accent">
                  {entityRelations.length}
                </span>
              )}
            </h3>
          </div>

          {entityRelations.length === 0 ? (
            <p className="text-xs text-content-muted italic">Nenhuma relação mapeada para esta entidade.</p>
          ) : (
            <div className="space-y-2">
              {entityRelations.map((r) => (
                <RelationCard
                  key={r.id}
                  relation={r}
                  entities={allEntities}
                  selectedId={entity.id}
                  onSelectEntity={onSelectEntity}
                />
              ))}
            </div>
          )}
        </div>

        {/* Facts */}
        {entityFacts.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-3">
              <DatabaseIcon size={12} className="text-content-muted" />
              <h3 className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
                Fatos
                <span className="ml-1.5 rounded bg-accent-dim px-1 text-accent">
                  {entityFacts.length}
                </span>
              </h3>
            </div>
            <div className="space-y-2">
              {entityFacts.map((f) => (
                <div
                  key={f.id}
                  className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-3"
                >
                  <p className="text-xs text-content-primary leading-relaxed">{f.statement}</p>
                  <div className="mt-2 flex items-center gap-3">
                    <ConfidenceBar value={f.confidence} />
                    <Badge variant="default" size="sm">{f.source_type}</Badge>
                    <span className="ml-auto text-[10px] text-content-muted">{rel(f.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Entity list sidebar
// ─────────────────────────────────────────────────────────────

function EntityList({
  entities,
  selectedId,
  search,
  onSelect,
}: {
  entities:   KnowledgeEntity[];
  selectedId: string | null;
  search:     string;
  onSelect:   (e: KnowledgeEntity) => void;
}) {
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return q
      ? entities.filter((e) => e.name.toLowerCase().includes(q) || e.aliases.some((a) => a.toLowerCase().includes(q)))
      : entities;
  }, [entities, search]);

  // Group by type
  const grouped = useMemo(() => {
    const m = new Map<string, KnowledgeEntity[]>();
    for (const e of filtered) {
      const arr = m.get(e.type) ?? [];
      arr.push(e);
      m.set(e.type, arr);
    }
    return m;
  }, [filtered]);

  if (entities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-12 px-4 text-center">
        <NetworkIcon size={20} className="text-content-muted" />
        <p className="text-xs text-content-muted">Nenhuma entidade mapeada ainda.</p>
        <p className="text-[11px] text-content-placeholder">
          As entidades são extraídas automaticamente das conversas.
        </p>
      </div>
    );
  }

  if (filtered.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-xs text-content-muted">
        Nenhuma entidade corresponde à busca.
      </p>
    );
  }

  return (
    <div className="py-1">
      {Array.from(grouped.entries()).map(([type, items]) => (
        <div key={type}>
          <div className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 sticky top-0",
            "bg-[var(--surface-raised)] z-10",
          )}>
            <span className={cn("flex items-center rounded p-0.5", entityColor(type))}>
              {entityIcon(type)}
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-content-muted">
              {entityTypeLabel(type)}
            </span>
            <span className="ml-auto text-[10px] text-content-muted">{items.length}</span>
          </div>

          {items.map((entity) => (
            <button
              key={entity.id}
              onClick={() => onSelect(entity)}
              className={cn(
                "flex w-full items-center gap-2 px-3 py-2 text-left transition-colors",
                selectedId === entity.id
                  ? "bg-[var(--surface-overlay)] text-content-primary"
                  : "text-content-secondary hover:bg-[var(--surface-subtle)] hover:text-content-primary",
              )}
            >
              <span className="flex-1 truncate text-xs">{entity.name}</span>
              <ChevronRightIcon
                size={11}
                className={cn("shrink-0", selectedId === entity.id ? "text-accent" : "text-content-muted opacity-50")}
              />
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Fact card (standalone)
// ─────────────────────────────────────────────────────────────

function FactCard({ fact: f, searchQuery }: { fact: Fact; searchQuery: string }) {
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4 hover:border-[var(--border-default)] transition-colors">
      <p className="text-sm text-content-primary leading-relaxed">
        <HighlightText text={f.statement} query={searchQuery} />
      </p>
      <div className="mt-3 flex items-center gap-3 flex-wrap">
        <ConfidenceBar value={f.confidence} />
        <Badge variant="default" size="sm">{f.source_type}</Badge>
        <span className="ml-auto text-[11px] text-content-muted">{rel(f.created_at)}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Observation card (standalone)
// ─────────────────────────────────────────────────────────────

function ObservationCard({ obs: o, searchQuery }: { obs: Observation; searchQuery: string }) {
  const w = Math.min(100, o.reinforcement_count * 20);
  return (
    <div className={cn(
      "rounded-lg border p-4 transition-colors",
      o.expired
        ? "border-[var(--border-subtle)] bg-[var(--surface-inset)] opacity-50"
        : "border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-[var(--border-default)]",
    )}>
      <div className="flex items-start gap-2">
        <p className="flex-1 text-sm text-content-primary leading-relaxed">
          <HighlightText text={o.statement} query={searchQuery} />
        </p>
        {o.expired && <Badge variant="muted" size="sm">expirado</Badge>}
      </div>
      <div className="mt-3 space-y-1.5">
        <ConfidenceBar value={o.confidence} />
        {o.reinforcement_count > 0 && (
          <div className="flex items-center gap-2">
            <div className="h-1 w-16 rounded-full bg-[var(--surface-subtle)] overflow-hidden">
              <div className="h-full rounded-full bg-accent" style={{ width: `${w}%` }} />
            </div>
            <span className="text-[10px] text-content-muted">
              {o.reinforcement_count} reforço{o.reinforcement_count !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <Badge variant="default" size="sm">{o.derived_from}</Badge>
        <span className="ml-auto text-[11px] text-content-muted">{rel(o.created_at)}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────

type Tab = "graph" | "facts" | "observations";

export function KnowledgePage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();

  const [entities,     setEntities]     = useState<KnowledgeEntity[]>([]);
  const [relations,    setRelations]    = useState<KnowledgeRelation[]>([]);
  const [facts,        setFacts]        = useState<Fact[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading,      setLoading]      = useState(false);
  const [tab,          setTab]          = useState<Tab>("graph");
  const [search,       setSearch]       = useState("");
  const [selectedEntity, setSelectedEntity] = useState<KnowledgeEntity | null>(null);

  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    Promise.all([
      api.listEntities(workspace.id),
      api.listRelations(workspace.id),
      api.listFacts(workspace.id),
      api.listObservations(workspace.id),
    ])
      .then(([ent, rel, fs, obs]) => {
        setEntities(ent);
        setRelations(rel);
        setFacts(fs);
        setObservations(obs);
        if (ent.length > 0) setSelectedEntity(ent[0]);
      })
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  const entityMap = useMemo(
    () => new Map(entities.map((e) => [e.id, e])),
    [entities],
  );

  const filteredFacts = useMemo(() => {
    const q = search.toLowerCase();
    return q ? facts.filter((f) => f.statement.toLowerCase().includes(q)) : facts;
  }, [facts, search]);

  const filteredObs = useMemo(() => {
    const q = search.toLowerCase();
    return q ? observations.filter((o) => o.statement.toLowerCase().includes(q)) : observations;
  }, [observations, search]);

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode; count: number }[] = [
    { id: "graph",        label: "Grafo",       icon: <NetworkIcon size={12} />,   count: entities.length },
    { id: "facts",        label: "Fatos",        icon: <DatabaseIcon size={12} />,  count: facts.length },
    { id: "observations", label: "Observações",  icon: <LightbulbIcon size={12} />, count: observations.length },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden">

      {/* ── Top bar ── */}
      <div className="flex shrink-0 items-center gap-4 border-b border-[var(--border-subtle)] bg-[var(--surface-base)] px-5 py-2.5">
        <div className="flex items-center gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); setSearch(""); }}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                tab === t.id
                  ? "bg-accent-dim text-accent"
                  : "text-content-muted hover:text-content-secondary hover:bg-[var(--surface-subtle)]",
              )}
            >
              <span>{t.icon}</span>
              {t.label}
              <span className={cn(
                "rounded px-1 text-[10px]",
                tab === t.id ? "bg-accent/20 text-accent" : "text-content-muted",
              )}>
                {t.count}
              </span>
            </button>
          ))}
        </div>

        <div className="relative ml-auto w-56">
          <SearchIcon size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-content-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={tab === "graph" ? "Filtrar entidades…" : tab === "facts" ? "Filtrar fatos…" : "Filtrar observações…"}
            className={cn(
              "w-full rounded-lg border py-1.5 pl-7 pr-7 text-xs",
              "border-[var(--border-default)] bg-[var(--surface-raised)]",
              "text-content-primary placeholder:text-content-placeholder",
              "focus:outline-none focus:border-[var(--border-accent)] transition-colors",
            )}
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-content-muted hover:text-content-secondary">
              <XIcon size={11} />
            </button>
          )}
        </div>
      </div>

      {/* ── Tab content ── */}

      {/* Graph tab — two-panel entity explorer */}
      {tab === "graph" && (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: entity list */}
          <aside className={cn(
            "flex flex-col overflow-y-auto border-r border-[var(--border-subtle)] bg-[var(--surface-raised)]",
            selectedEntity
              ? "hidden md:flex md:w-60 md:shrink-0"
              : "flex-1 md:flex-none md:w-60 md:shrink-0",
          )}>
            <div className="flex items-center gap-1.5 border-b border-[var(--border-subtle)] px-3 py-2">
              <BookOpenIcon size={11} className="text-content-muted" />
              <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
                Entidades
              </span>
              <span className="ml-auto text-[10px] text-content-muted tabular-nums">
                {entities.length}
              </span>
            </div>
            <EntityList
              entities={entities}
              selectedId={selectedEntity?.id ?? null}
              search={search}
              onSelect={(e) => setSelectedEntity(e)}
            />
          </aside>

          {/* Right: entity detail */}
          <main className={cn(
            "overflow-hidden bg-[var(--surface-base)]",
            selectedEntity ? "flex flex-1 flex-col" : "hidden md:flex md:flex-1 md:flex-col",
          )}>
            {!selectedEntity ? (
              <div className="flex h-full flex-col items-center justify-center gap-3">
                <NetworkIcon size={28} className="text-content-muted" />
                <div className="text-center">
                  <p className="text-sm font-medium text-content-secondary">Grafo de Conhecimento</p>
                  <p className="mt-1 text-xs text-content-muted">
                    Selecione uma entidade para explorar suas relações e fatos.
                  </p>
                </div>
              </div>
            ) : (
              <EntityDetailPanel
                entity={selectedEntity}
                allEntities={entityMap}
                allRelations={relations}
                facts={facts}
                onSelectEntity={(id) => {
                  const e = entityMap.get(id);
                  if (e) setSelectedEntity(e);
                }}
                onBack={() => setSelectedEntity(null)}
              />
            )}
          </main>
        </div>
      )}

      {/* Facts tab */}
      {tab === "facts" && (
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-2xl px-4 sm:px-6 py-4 sm:py-6 space-y-2">
            {filteredFacts.length === 0 ? (
              <p className="py-16 text-center text-sm text-content-muted">
                {search ? "Nenhum fato corresponde à busca." : "Nenhum fato registrado ainda."}
              </p>
            ) : (
              filteredFacts.map((f) => (
                <FactCard key={f.id} fact={f} searchQuery={search} />
              ))
            )}
          </div>
        </div>
      )}

      {/* Observations tab */}
      {tab === "observations" && (
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-2xl px-4 sm:px-6 py-4 sm:py-6 space-y-2">
            {filteredObs.length === 0 ? (
              <p className="py-16 text-center text-sm text-content-muted">
                {search ? "Nenhuma observação corresponde à busca." : "Nenhuma observação registrada ainda."}
              </p>
            ) : (
              filteredObs.map((o) => (
                <ObservationCard key={o.id} obs={o} searchQuery={search} />
              ))
            )}
          </div>
        </div>
      )}

    </div>
  );
}
