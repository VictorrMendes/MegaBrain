"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type DashboardSummary } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Spinner } from "@/components/ui";
import {
  ActivityIcon,
  AlertTriangleIcon,
  BookOpenIcon,
  BrainIcon,
  ClockIcon,
  InboxIcon,
  PackageIcon,
  RefreshCwIcon,
  TargetIcon,
  XCircleIcon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

function longDate() {
  return new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
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

const ACTIVE_STATUSES = new Set(["running", "planning", "waiting_approval", "ready"]);

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type Mission  = DashboardSummary["recent_missions"][0];
type Health   = DashboardSummary["health"][0];

type AttentionItem = {
  icon: React.ElementType;
  label: string;
  href: string;
  kind: "warning" | "error";
};

type FeedItem = {
  id:   string;
  kind: "mission" | "memory" | "fact" | "artifact";
  text: string;
  sub:  string;
  at:   Date;
  href: string;
};

// ─────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────

export function DashboardPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [data,       setData]       = useState<DashboardSummary | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async (ws = workspace, isRefresh = false) => {
      if (!ws) return;
      if (isRefresh) setRefreshing(true); else setLoading(true);
      try {
        setData(await api.getDashboard(ws.id));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [workspace?.id],
  );

  useEffect(() => {
    if (workspace) load(workspace);
  }, [workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── loading state ───
  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  // ─── derived data ───
  const activeMissions = data?.recent_missions.filter((m) =>
    ACTIVE_STATUSES.has(m.status),
  ) ?? [];

  const allHealthy = data?.health.every((h) => h.status === "ready") ?? true;

  const attentionItems: AttentionItem[] = [];
  if (data) {
    if (data.inbox_pending > 0)
      attentionItems.push({
        icon:  InboxIcon,
        label: `${data.inbox_pending} ${data.inbox_pending === 1 ? "item" : "itens"} no inbox`,
        href:  "/inbox",
        kind:  "warning",
      });
    if (data.missions.waiting_approval > 0)
      attentionItems.push({
        icon:  AlertTriangleIcon,
        label: `${data.missions.waiting_approval} aguardando aprovação`,
        href:  "/missions",
        kind:  "warning",
      });
    if (data.missions.failed > 0)
      attentionItems.push({
        icon:  XCircleIcon,
        label: `${data.missions.failed} missão falhou`,
        href:  "/missions",
        kind:  "error",
      });
    if (!allHealthy)
      attentionItems.push({
        icon:  AlertTriangleIcon,
        label: "Sistema com atenção",
        href:  "/runtime",
        kind:  "error",
      });
  }

  // ─── unified feed ───
  const feed: FeedItem[] = [];
  if (data) {
    for (const m of data.recent_missions)
      feed.push({ id: `m-${m.id}`,   kind: "mission",  text: m.intent,    sub: m.status,                          at: new Date(m.updated_at),  href: "/missions"  });
    for (const m of data.recent_memories)
      feed.push({ id: `mm-${m.id}`,  kind: "memory",   text: m.content,   sub: m.type,                            at: new Date(m.created_at),  href: "/memory"    });
    for (const f of data.recent_facts)
      feed.push({ id: `f-${f.id}`,   kind: "fact",     text: f.statement, sub: `${Math.round(f.confidence * 100)}%`, at: new Date(f.created_at), href: "/knowledge" });
    for (const a of data.recent_artifacts)
      feed.push({ id: `a-${a.id}`,   kind: "artifact", text: a.name,      sub: a.type,                            at: new Date(a.created_at),  href: "/artifacts" });
    feed.sort((a, b) => b.at.getTime() - a.at.getTime());
  }
  const recentFeed = feed.slice(0, 14);

  // ─── render ───
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-6 py-10 animate-fade-in">

        {/* ────── HERO ────── */}
        <div className="mb-10 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-light text-content-primary tracking-tight">
              {greeting()}.
            </h1>
            <p className="mt-1.5 text-sm text-content-secondary capitalize">
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
              "mt-1.5 rounded-md p-1.5 transition-colors",
              "text-content-muted hover:text-content-secondary hover:bg-surface-subtle",
              "disabled:opacity-30",
            )}
            title="Atualizar"
          >
            <RefreshCwIcon size={14} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>

        {!data ? (
          <p className="text-center text-xs text-content-muted py-20">
            Nenhum dado disponível.
          </p>
        ) : (
          <div className="space-y-10">

            {/* ────── ATENÇÃO ────── */}
            {attentionItems.length > 0 && (
              <section>
                <div className="flex flex-wrap gap-2">
                  {attentionItems.map((item, i) => (
                    <Link
                      key={i}
                      href={item.href}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5",
                        "text-xs font-medium border transition-colors",
                        item.kind === "warning"
                          ? "bg-amber-950/40 border-amber-900/30 text-amber-400 hover:bg-amber-950/60"
                          : "bg-red-950/40 border-red-900/30 text-red-400 hover:bg-red-950/60",
                      )}
                    >
                      <item.icon size={12} />
                      {item.label}
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* ────── EM ANDAMENTO ────── */}
            <section>
              <SectionHeader
                icon={<ZapIcon size={12} />}
                title={
                  activeMissions.length > 0
                    ? `Em andamento · ${activeMissions.length}`
                    : "Em andamento"
                }
                href="/missions"
              />

              {activeMissions.length === 0 ? (
                <p className="mt-3 text-sm text-content-muted">
                  Nenhuma missão ativa no momento.
                </p>
              ) : (
                <div className="mt-3 space-y-1.5">
                  {activeMissions.map((m) => (
                    <ActiveMissionRow key={String(m.id)} mission={m} />
                  ))}
                </div>
              )}
            </section>

            {/* ────── ATIVIDADE RECENTE ────── */}
            {recentFeed.length > 0 && (
              <section>
                <SectionHeader
                  icon={<ClockIcon size={12} />}
                  title="Atividade recente"
                  href="/timeline"
                />
                <div className="relative mt-3">
                  {/* timeline line */}
                  <div className="absolute left-[6px] top-3 bottom-3 w-px bg-[var(--border-subtle)]" />
                  <div className="space-y-0.5">
                    {recentFeed.map((item) => (
                      <FeedRow key={item.id} item={item} />
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* ────── STATUS DO SISTEMA ────── */}
            <SystemFooter health={data.health} scheduler={data.scheduler} />

          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

function SectionHeader({
  icon, title, href,
}: {
  icon: React.ReactNode;
  title: string;
  href: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-content-muted">{icon}</span>
      <Link
        href={href}
        className="text-[11px] font-semibold uppercase tracking-widest text-content-muted hover:text-content-secondary transition-colors"
      >
        {title}
      </Link>
    </div>
  );
}

const MISSION_DOT: Record<string, string> = {
  running:          "bg-status-active animate-pulse-dot",
  planning:         "bg-status-info",
  waiting_approval: "bg-status-warning",
  ready:            "bg-status-success",
};

function ActiveMissionRow({ mission }: { mission: Mission }) {
  const variant  = STATUS_BADGE[mission.status] ?? "default";
  const dotColor = MISSION_DOT[mission.status]  ?? "bg-content-muted";

  return (
    <Link
      href="/missions"
      className={cn(
        "group flex items-center gap-3 rounded-lg px-3 py-2.5",
        "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "hover:border-[var(--border-default)] hover:bg-[var(--surface-overlay)]",
        "transition-colors",
      )}
    >
      <span className={cn("h-2 w-2 shrink-0 rounded-full", dotColor)} />
      <span className="flex-1 truncate text-sm text-content-primary">
        {mission.intent}
      </span>
      <Badge variant={variant} size="sm">
        {mission.status.replace(/_/g, " ")}
      </Badge>
      <span className="shrink-0 text-xs text-content-muted tabular-nums">
        {rel(mission.updated_at)}
      </span>
    </Link>
  );
}

const FEED_ICON = {
  mission:  TargetIcon,
  memory:   BrainIcon,
  fact:     BookOpenIcon,
  artifact: PackageIcon,
} as const;

const FEED_BADGE: Record<FeedItem["kind"], BadgeVariant> = {
  mission:  "default",
  memory:   "active",
  fact:     "info",
  artifact: "default",
};

function FeedRow({ item }: { item: FeedItem }) {
  const Icon    = FEED_ICON[item.kind] ?? ActivityIcon;
  const variant = FEED_BADGE[item.kind];

  return (
    <Link
      href={item.href}
      className={cn(
        "group relative flex items-center gap-3 rounded-md py-2 pl-6 pr-3",
        "hover:bg-[var(--surface-raised)] transition-colors",
      )}
    >
      {/* timeline dot */}
      <span
        className={cn(
          "absolute left-0 top-1/2 -translate-y-1/2",
          "flex h-3 w-3 items-center justify-center",
          "rounded-full border border-[var(--border-default)] bg-[var(--surface-base)]",
        )}
      >
        <span className="h-1 w-1 rounded-full bg-[var(--border-strong)]" />
      </span>

      <Icon size={12} className="shrink-0 text-content-muted" />

      <p className="flex-1 truncate text-sm text-content-secondary group-hover:text-content-primary transition-colors">
        {item.text}
      </p>

      <div className="flex shrink-0 items-center gap-1.5">
        <Badge variant={variant} size="sm">{item.kind}</Badge>
        <span className="text-xs text-content-muted tabular-nums w-8 text-right">
          {rel(item.at.toISOString())}
        </span>
      </div>
    </Link>
  );
}

function SystemFooter({
  health,
  scheduler,
}: {
  health:    DashboardSummary["health"];
  scheduler: DashboardSummary["scheduler"];
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-[var(--border-subtle)] pt-4">
      {health.map((h) => (
        <HealthDot key={h.name} component={h} />
      ))}
      <span className="ml-auto flex items-center gap-1 text-xs text-content-muted">
        <ZapIcon size={10} />
        {scheduler.active_triggers} trigger{scheduler.active_triggers !== 1 ? "s" : ""}
      </span>
    </div>
  );
}

function HealthDot({ component }: { component: Health }) {
  const ok = component.status === "ready";
  return (
    <span className="flex items-center gap-1 text-xs text-content-muted">
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          ok ? "bg-status-success" : "bg-status-error",
        )}
      />
      {component.name}
    </span>
  );
}
