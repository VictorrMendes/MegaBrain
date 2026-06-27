"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  type BriefingResponse,
  type DashboardSummary,
  type LifeContextSnapshot,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Spinner } from "@/components/ui";
import {
  ActivityIcon,
  AlertTriangleIcon,
  ArrowRightIcon,
  BookOpenIcon,
  BrainIcon,
  CheckCircle2Icon,
  ChevronDownIcon,
  ChevronUpIcon,
  ClockIcon,
  CommandIcon,
  GlobeIcon,
  InboxIcon,
  MessageSquareIcon,
  PackageIcon,
  PlusIcon,
  RefreshCwIcon,
  SparklesIcon,
  TargetIcon,
  XCircleIcon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const ACTIVE_STATUSES = new Set(["running", "planning", "waiting_approval", "ready"]);

const STATUS_BADGE: Record<string, BadgeVariant> = {
  pending:          "default",
  planning:         "info",
  waiting_approval: "warning",
  ready:            "info",
  running:          "active",
  succeeded:        "success",
  failed:           "error",
  cancelled:        "muted",
};

const MISSION_BAR: Record<string, string> = {
  running:          "bg-status-active",
  planning:         "bg-status-info",
  waiting_approval: "bg-status-warning",
  ready:            "bg-status-success",
};

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5)  return "Boa madrugada";
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

function longDate(): string {
  return new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day:     "numeric",
    month:   "long",
  });
}

function rel(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)  return "agora";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  return d === 1 ? "ontem" : `${d}d`;
}

type DashMission = DashboardSummary["recent_missions"][0];
type FeedKind    = "mission" | "memory" | "fact" | "artifact";

interface FeedItem {
  id:   string;
  kind: FeedKind;
  text: string;
  sub:  string;
  at:   Date;
  href: string;
}

interface Briefing {
  headline: string;
  context:  string;
  signal:   "clear" | "active" | "attention" | "critical";
}

function deriveBriefing(data: DashboardSummary): Briefing {
  const active = data.recent_missions.filter((m) => ACTIVE_STATUSES.has(m.status));
  const allOk  = data.health.every((h) => h.status === "ready");

  // Signal
  let signal: Briefing["signal"] = "clear";
  if (data.missions.failed > 0 || !allOk) signal = "critical";
  else if (data.missions.waiting_approval > 0 || data.inbox_pending > 0) signal = "attention";
  else if (active.length > 0) signal = "active";

  // Headline
  let headline: string;
  if (signal === "critical") {
    if (data.missions.failed > 0)
      headline = `${data.missions.failed} missão${data.missions.failed > 1 ? "ões falharam" : " falhou"} — ação necessária`;
    else
      headline = "Sistema com atenção — verificar runtime";
  } else if (active.length > 0) {
    headline = `${active.length} missão${active.length > 1 ? "ões ativas" : " ativa"} em andamento`;
  } else if (data.missions.waiting_approval > 0) {
    headline = `${data.missions.waiting_approval} missão${data.missions.waiting_approval > 1 ? "ões aguardam" : " aguarda"} aprovação`;
  } else if (data.inbox_pending > 0) {
    headline = `${data.inbox_pending} item${data.inbox_pending > 1 ? "s" : ""} no inbox aguardam processamento`;
  } else {
    headline = "Tudo em ordem — sem pendências críticas";
  }

  // Context
  const parts: string[] = [];
  if (data.missions.total > 0)
    parts.push(`${data.missions.total} missões total`);
  if (data.recent_memories.length > 0)
    parts.push(`${data.recent_memories.length} memórias`);
  if (data.recent_facts.length > 0)
    parts.push(`${data.recent_facts.length} fatos`);
  if (data.scheduler.active_triggers > 0)
    parts.push(`${data.scheduler.active_triggers} triggers ativos`);
  parts.push(allOk ? "sistema operacional" : "sistema degradado");

  return { headline, context: parts.join(" · "), signal };
}

const SIGNAL_STYLE: Record<Briefing["signal"], string> = {
  clear:     "border-[var(--border-default)] bg-surface-raised",
  active:    "border-accent-subtle bg-gradient-to-br from-accent-subtle to-transparent",
  attention: "border-amber-900/40 bg-gradient-to-br from-amber-950/30 to-transparent",
  critical:  "border-red-900/40 bg-gradient-to-br from-red-950/30 to-transparent",
};

const SIGNAL_LABEL_COLOR: Record<Briefing["signal"], string> = {
  clear:     "text-status-success",
  active:    "text-accent",
  attention: "text-status-warning",
  critical:  "text-status-error",
};

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────

export function DashboardPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [data,       setData]       = useState<DashboardSummary | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async (ws = workspace, isRefresh = false) => {
      if (!ws) return;
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      try {
        setData(await api.getDashboard(ws.id));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [workspace?.id], // eslint-disable-line react-hooks/exhaustive-deps
  );

  useEffect(() => {
    if (workspace) load(workspace);
  }, [workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  const activeMissions = data?.recent_missions.filter((m) =>
    ACTIVE_STATUSES.has(m.status),
  ) ?? [];

  const briefing = data ? deriveBriefing(data) : null;

  const attentionItems = buildAttentionItems(data);

  const feed = buildFeed(data);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 py-6 sm:py-8 animate-fade-in">

        {/* ══════════════════════════════════════════════
            HERO — Greeting + Quick Actions
        ═══════════════════════════════════════════════ */}
        <div className="mb-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-light tracking-tight text-content-primary">
                {greeting()}.
              </h1>
              <p className="mt-1 capitalize text-sm text-content-muted">
                {longDate()}
                {workspace && (
                  <span className="text-content-muted"> · {workspace.name}</span>
                )}
              </p>
            </div>

            <button
              onClick={() => load(workspace ?? undefined, true)}
              disabled={refreshing}
              className={cn(
                "mt-1 rounded-md p-1.5 transition-colors duration-fast",
                "text-content-muted hover:text-content-secondary hover:bg-surface-subtle",
                "disabled:opacity-30",
              )}
            >
              <RefreshCwIcon size={13} className={refreshing ? "animate-spin-slow" : ""} />
            </button>
          </div>

          {/* Quick actions */}
          <div className="mt-5 flex flex-wrap gap-2">
            {[
              {
                icon: <MessageSquareIcon size={12} />,
                label: "Nova conversa",
                href: "/chat",
              },
              {
                icon: <PlusIcon size={12} />,
                label: "Nova missão",
                href: "/missions",
              },
              {
                icon: <ActivityIcon size={12} />,
                label: "Timeline",
                href: "/timeline",
              },
              {
                icon: <CommandIcon size={12} />,
                label: "Buscar",
                onClick: () => {
                  const e = new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true });
                  window.dispatchEvent(e);
                },
              },
            ].map((action, i) => (
              action.href ? (
                <Link
                  key={i}
                  href={action.href}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs",
                    "border-[var(--border-subtle)] bg-surface-raised",
                    "text-content-secondary hover:text-content-primary",
                    "hover:border-[var(--border-default)] hover:bg-surface-overlay",
                    "transition-colors duration-fast",
                  )}
                >
                  <span className="text-content-muted">{action.icon}</span>
                  {action.label}
                </Link>
              ) : (
                <button
                  key={i}
                  onClick={action.onClick}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs",
                    "border-[var(--border-subtle)] bg-surface-raised",
                    "text-content-secondary hover:text-content-primary",
                    "hover:border-[var(--border-default)] hover:bg-surface-overlay",
                    "transition-colors duration-fast",
                  )}
                >
                  <span className="text-content-muted">{action.icon}</span>
                  {action.label}
                </button>
              )
            ))}
          </div>
        </div>

        {!data ? (
          <p className="py-20 text-center text-sm text-content-muted">
            Nenhum dado disponível.
          </p>
        ) : (
          <div className="space-y-8">

            {/* ══════════════════════════════════════════════
                ATENÇÃO — strip condicional
            ═══════════════════════════════════════════════ */}
            {attentionItems.length > 0 && (
              <section className="flex flex-wrap gap-2">
                {attentionItems.map((item, i) => (
                  <Link
                    key={i}
                    href={item.href}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5",
                      "text-xs font-medium transition-colors duration-fast",
                      item.kind === "warning"
                        ? "border-amber-900/40 bg-amber-950/20 text-amber-400 hover:bg-amber-950/40"
                        : "border-red-900/40 bg-red-950/20 text-red-400 hover:bg-red-950/40",
                    )}
                  >
                    <item.icon size={11} />
                    {item.label}
                  </Link>
                ))}
              </section>
            )}

            {/* ══════════════════════════════════════════════
                BRIEFING — status inteligente do sistema
            ═══════════════════════════════════════════════ */}
            {briefing && (
              <section
                className={cn(
                  "rounded-xl border p-4",
                  SIGNAL_STYLE[briefing.signal],
                )}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      briefing.signal === "active" && "bg-accent animate-pulse-dot",
                      briefing.signal === "clear"  && "bg-status-success",
                      briefing.signal === "attention" && "bg-status-warning animate-pulse-dot",
                      briefing.signal === "critical"  && "bg-status-error animate-pulse-dot",
                    )}
                  />
                  <span
                    className={cn(
                      "text-[10px] font-semibold uppercase tracking-widest",
                      SIGNAL_LABEL_COLOR[briefing.signal],
                    )}
                  >
                    Status do sistema
                  </span>
                </div>

                <p className="text-sm font-medium text-content-primary">
                  {briefing.headline}
                </p>
                <p className="mt-1 text-xs text-content-muted">
                  {briefing.context}
                </p>

                {/* Stats strip */}
                <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-[var(--border-subtle)] pt-3">
                  <StatCount
                    label="missões"
                    value={data.missions.total}
                    detail={`${data.missions.running} ativas`}
                  />
                  <StatCount
                    label="memórias"
                    value={data.recent_memories.length}
                  />
                  <StatCount
                    label="fatos"
                    value={data.recent_facts.length}
                  />
                  <StatCount
                    label="inbox"
                    value={data.inbox_pending}
                    detail={data.inbox_pending > 0 ? "pendente" : "vazio"}
                    highlight={data.inbox_pending > 0}
                  />
                  <StatCount
                    label="artifacts"
                    value={data.recent_artifacts.length}
                  />
                </div>
              </section>
            )}

            {/* ══════════════════════════════════════════════
                BRIEFING COGNITIVO — resumo inteligente
            ═══════════════════════════════════════════════ */}
            {workspace && (
              <CognitiveBriefingWidget workspaceId={workspace.id} />
            )}

            {/* ══════════════════════════════════════════════
                CONTEXTO DE VIDA — integrações externas
            ═══════════════════════════════════════════════ */}
            {workspace && (
              <LifeContextWidget workspaceId={workspace.id} />
            )}

            {/* ══════════════════════════════════════════════
                EM ANDAMENTO — missões ativas
            ═══════════════════════════════════════════════ */}
            <section>
              <SectionLabel
                icon={<ZapIcon size={11} />}
                title={
                  activeMissions.length > 0
                    ? `Em andamento · ${activeMissions.length}`
                    : "Em andamento"
                }
                href="/missions"
              />

              <div className="mt-3">
                {activeMissions.length === 0 ? (
                  <EmptySlot
                    icon={<TargetIcon size={16} />}
                    label="Nenhuma missão ativa"
                    action={{ label: "Criar missão", href: "/missions" }}
                  />
                ) : (
                  <div className="space-y-2">
                    {activeMissions.map((m) => (
                      <ActiveMissionCard key={m.id} mission={m} />
                    ))}
                    {data.missions.running + data.missions.planning > activeMissions.length && (
                      <Link
                        href="/missions"
                        className="flex items-center gap-1.5 py-1 text-xs text-content-muted hover:text-content-secondary transition-colors"
                      >
                        <span>Ver todas as missões</span>
                        <ArrowRightIcon size={11} />
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </section>

            {/* ══════════════════════════════════════════════
                ATIVIDADE RECENTE — feed unificado
            ═══════════════════════════════════════════════ */}
            {feed.length > 0 && (
              <section>
                <SectionLabel
                  icon={<ClockIcon size={11} />}
                  title="Atividade recente"
                  href="/timeline"
                />
                <div className="relative mt-3">
                  {/* timeline line */}
                  <div className="absolute left-[7px] top-2 bottom-2 w-px bg-[var(--border-subtle)]" />
                  <div className="space-y-0.5">
                    {feed.map((item) => (
                      <FeedRow key={item.id} item={item} />
                    ))}
                  </div>
                </div>
                <Link
                  href="/timeline"
                  className="mt-3 flex items-center gap-1.5 text-xs text-content-muted hover:text-content-secondary transition-colors"
                >
                  Ver timeline completa
                  <ArrowRightIcon size={11} />
                </Link>
              </section>
            )}

            {/* ══════════════════════════════════════════════
                SISTEMA — health footer
            ═══════════════════════════════════════════════ */}
            <SystemFooter health={data.health} scheduler={data.scheduler} />

          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Data builders
// ─────────────────────────────────────────────────────────────

function buildAttentionItems(data: DashboardSummary | null) {
  if (!data) return [];
  const items: { icon: React.ElementType; label: string; href: string; kind: "warning" | "error" }[] = [];
  if (data.inbox_pending > 0)
    items.push({ icon: InboxIcon, label: `${data.inbox_pending} inbox`, href: "/inbox", kind: "warning" });
  if (data.missions.waiting_approval > 0)
    items.push({ icon: AlertTriangleIcon, label: `${data.missions.waiting_approval} aguardando aprovação`, href: "/missions", kind: "warning" });
  if (data.missions.failed > 0)
    items.push({ icon: XCircleIcon, label: `${data.missions.failed} falhou`, href: "/missions", kind: "error" });
  if (!data.health.every((h) => h.status === "ready"))
    items.push({ icon: AlertTriangleIcon, label: "sistema degradado", href: "/runtime", kind: "error" });
  return items;
}

function buildFeed(data: DashboardSummary | null): FeedItem[] {
  if (!data) return [];
  const feed: FeedItem[] = [];
  for (const m of data.recent_missions)
    feed.push({ id: `m-${m.id}`, kind: "mission", text: m.intent, sub: m.status, at: new Date(m.updated_at), href: "/missions" });
  for (const m of data.recent_memories)
    feed.push({ id: `mm-${m.id}`, kind: "memory", text: m.content, sub: m.type, at: new Date(m.created_at), href: "/memory" });
  for (const f of data.recent_facts)
    feed.push({ id: `f-${f.id}`, kind: "fact", text: f.statement, sub: `${Math.round(f.confidence * 100)}%`, at: new Date(f.created_at), href: "/knowledge" });
  for (const a of data.recent_artifacts)
    feed.push({ id: `a-${a.id}`, kind: "artifact", text: a.name, sub: a.type, at: new Date(a.created_at), href: "/artifacts" });
  return feed.sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, 12);
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

function SectionLabel({
  icon, title, href,
}: {
  icon:  React.ReactNode;
  title: string;
  href:  string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-content-muted">{icon}</span>
      <Link
        href={href}
        className={cn(
          "text-[10px] font-semibold uppercase tracking-widest",
          "text-content-muted hover:text-content-secondary transition-colors duration-fast",
        )}
      >
        {title}
      </Link>
    </div>
  );
}

function StatCount({
  label, value, detail, highlight,
}: {
  label:     string;
  value:     number;
  detail?:   string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-1">
      <span
        className={cn(
          "text-lg font-semibold tabular-nums",
          highlight ? "text-status-warning" : "text-content-primary",
        )}
      >
        {value}
      </span>
      <span className="text-xs text-content-muted">{label}</span>
      {detail && (
        <span className="text-2xs text-content-muted">({detail})</span>
      )}
    </div>
  );
}

function ActiveMissionCard({ mission }: { mission: DashMission }) {
  const variant  = STATUS_BADGE[mission.status] ?? "default";
  const barColor = MISSION_BAR[mission.status]  ?? "bg-content-muted";
  const isLive   = mission.status === "running";

  return (
    <Link
      href="/missions"
      className={cn(
        "group flex items-center gap-3 rounded-lg",
        "border border-[var(--border-subtle)] bg-surface-raised",
        "overflow-hidden",
        "hover:border-[var(--border-default)] hover:bg-surface-overlay",
        "transition-colors duration-fast",
      )}
    >
      {/* Status bar — colored left edge */}
      <span className={cn("w-0.5 self-stretch shrink-0", barColor)} />

      {/* Live pulse */}
      {isLive && (
        <span className="ml-2 h-2 w-2 shrink-0 rounded-full bg-status-active animate-pulse-dot" />
      )}

      <div className={cn("flex flex-1 items-center gap-3 px-3 py-3", !isLive && "ml-2")}>
        <p className="flex-1 truncate text-sm text-content-primary">
          {mission.intent}
        </p>

        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={variant} size="sm">
            {mission.status.replace(/_/g, " ")}
          </Badge>
          <span className="w-8 text-right text-xs text-content-muted tabular-nums">
            {rel(mission.updated_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}

const FEED_ICON: Record<FeedKind, React.ElementType> = {
  mission:  TargetIcon,
  memory:   BrainIcon,
  fact:     BookOpenIcon,
  artifact: PackageIcon,
};

const FEED_DOT: Record<FeedKind, string> = {
  mission:  "bg-status-active",
  memory:   "bg-status-success",
  fact:     "bg-status-info",
  artifact: "bg-content-muted",
};

const FEED_BADGE: Record<FeedKind, BadgeVariant> = {
  mission:  "default",
  memory:   "active",
  fact:     "info",
  artifact: "muted",
};

function FeedRow({ item }: { item: FeedItem }) {
  const Icon    = FEED_ICON[item.kind];
  const variant = FEED_BADGE[item.kind];
  const dot     = FEED_DOT[item.kind];

  return (
    <Link
      href={item.href}
      className={cn(
        "group relative flex items-center gap-3",
        "rounded-md py-1.5 pl-6 pr-3",
        "hover:bg-surface-raised transition-colors duration-fast",
      )}
    >
      {/* Timeline dot */}
      <span
        className={cn(
          "absolute left-0 top-1/2 -translate-y-1/2",
          "flex h-3.5 w-3.5 items-center justify-center",
          "rounded-full border border-[var(--border-default)] bg-surface-base",
        )}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      </span>

      <Icon size={11} className="shrink-0 text-content-muted" />

      <p className="flex-1 truncate text-sm text-content-secondary group-hover:text-content-primary transition-colors">
        {item.text}
      </p>

      <div className="flex shrink-0 items-center gap-2">
        <Badge variant={variant} size="sm">{item.kind}</Badge>
        <span className="w-8 text-right text-xs text-content-muted tabular-nums">
          {rel(item.at.toISOString())}
        </span>
      </div>
    </Link>
  );
}

function EmptySlot({
  icon, label, action,
}: {
  icon:   React.ReactNode;
  label:  string;
  action: { label: string; href: string };
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-dashed border-[var(--border-subtle)] px-4 py-3">
      <div className="flex items-center gap-2 text-content-muted">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <Link
        href={action.href}
        className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover transition-colors"
      >
        <PlusIcon size={11} />
        {action.label}
      </Link>
    </div>
  );
}

function CognitiveBriefingWidget({ workspaceId }: { workspaceId: string }) {
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    api.listBriefings(workspaceId, 1)
      .then((list) => { if (list.length > 0) setBriefing(list[0]); })
      .catch(() => {});
  }, [workspaceId]);

  const generate = async () => {
    setGenerating(true);
    try {
      const b = await api.generateBriefing(workspaceId);
      setBriefing(b);
      setExpanded(true);
    } catch { /* silent */ } finally {
      setGenerating(false);
    }
  };

  return (
    <section className="rounded-xl border border-[var(--border-subtle)] bg-surface-raised p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <SparklesIcon size={11} className="text-content-muted" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
            Briefing Cognitivo
          </span>
          {briefing && (
            <span className="text-[10px] text-content-muted">
              · {rel(briefing.created_at)}
            </span>
          )}
        </div>
        <button
          onClick={generate}
          disabled={generating}
          className={cn(
            "flex items-center gap-1 rounded-md border px-2 py-1 text-xs",
            "border-[var(--border-subtle)] text-content-secondary",
            "hover:border-[var(--border-default)] hover:text-content-primary",
            "hover:bg-surface-overlay transition-colors disabled:opacity-40",
          )}
        >
          <SparklesIcon size={10} className={generating ? "animate-spin" : ""} />
          {generating ? "Gerando…" : "Gerar"}
        </button>
      </div>

      {briefing ? (
        <div>
          <p className="text-sm font-medium text-content-primary">
            {briefing.title}
          </p>
          {expanded ? (
            <>
              <p className="mt-2 text-xs text-content-secondary whitespace-pre-wrap leading-relaxed">
                {briefing.content}
              </p>
              <button
                onClick={() => setExpanded(false)}
                className="mt-2 flex items-center gap-1 text-xs text-content-muted hover:text-content-secondary transition-colors"
              >
                <ChevronUpIcon size={11} /> Recolher
              </button>
            </>
          ) : (
            <p className="mt-1 text-xs text-content-muted">
              {briefing.content.slice(0, 120)}
              {briefing.content.length > 120 && (
                <>
                  {"… "}
                  <button
                    onClick={() => setExpanded(true)}
                    className="inline-flex items-center gap-0.5 text-accent hover:text-accent-hover transition-colors"
                  >
                    <ChevronDownIcon size={10} /> ver mais
                  </button>
                </>
              )}
            </p>
          )}
        </div>
      ) : (
        <p className="text-xs text-content-muted">
          Nenhum briefing gerado. Clique em "Gerar" para criar um resumo inteligente do sistema.
        </p>
      )}
    </section>
  );
}

function LifeContextWidget({ workspaceId }: { workspaceId: string }) {
  const [snapshot, setSnapshot] = useState<LifeContextSnapshot | null>(null);

  useEffect(() => {
    api.getLifeContextSnapshot(workspaceId).then(setSnapshot).catch(() => {});
  }, [workspaceId]);

  if (!snapshot || snapshot.lines.length === 0) return null;

  return (
    <section className="rounded-xl border border-[var(--border-subtle)] bg-surface-raised p-4">
      <div className="mb-3 flex items-center gap-1.5">
        <GlobeIcon size={11} className="text-content-muted" />
        <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
          Contexto de Vida
        </span>
        <span className="text-[10px] text-content-muted">
          · {snapshot.integration_count} integração{snapshot.integration_count !== 1 ? "ões" : ""}
        </span>
      </div>
      <ul className="space-y-1.5">
        {snapshot.lines.slice(0, 6).map((line, i) => (
          <li key={i} className="flex items-start gap-1.5 text-xs text-content-secondary">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-content-muted" />
            {line}
          </li>
        ))}
        {snapshot.lines.length > 6 && (
          <li className="text-xs text-content-muted">
            +{snapshot.lines.length - 6} mais…
          </li>
        )}
      </ul>
    </section>
  );
}

function SystemFooter({
  health,
  scheduler,
}: {
  health:    DashboardSummary["health"];
  scheduler: DashboardSummary["scheduler"];
}) {
  const allOk = health.every((h) => h.status === "ready");

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-[var(--border-subtle)] pt-5">
      {/* Overall health */}
      <Link
        href="/runtime"
        className="flex items-center gap-1.5 group"
      >
        {allOk
          ? <CheckCircle2Icon size={12} className="text-status-success" />
          : <AlertTriangleIcon size={12} className="text-status-warning" />
        }
        <span className="text-xs text-content-muted group-hover:text-content-secondary transition-colors">
          {allOk ? "sistema operacional" : "sistema com atenção"}
        </span>
      </Link>

      {/* Individual components */}
      {health.map((h) => (
        <span key={h.name} className="flex items-center gap-1">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              h.status === "ready"    && "bg-status-success",
              h.status === "degraded" && "bg-status-warning",
              h.status === "failed"   && "bg-status-error",
            )}
          />
          <span className="text-xs text-content-muted">{h.name}</span>
        </span>
      ))}

      <span className="ml-auto flex items-center gap-1.5 text-xs text-content-muted">
        <ZapIcon size={10} />
        {scheduler.active_triggers} trigger{scheduler.active_triggers !== 1 ? "s" : ""}
      </span>
    </div>
  );
}
