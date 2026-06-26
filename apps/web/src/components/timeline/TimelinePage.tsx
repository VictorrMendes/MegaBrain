"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type InboxItem, type Mission, type Memory } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Spinner } from "@/components/ui";
import {
  ActivityIcon,
  BrainIcon,
  InboxIcon,
  RefreshCwIcon,
  TargetIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type EventKind = "inbox" | "mission" | "memory";

interface TimelineEvent {
  id:     string;
  kind:   EventKind;
  title:  string;
  sub:    string;
  badge?: string;
  badgeVariant?: BadgeVariant;
  href:   string;
  ts:     Date;
}

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function rel(date: Date): string {
  const diff = Date.now() - date.getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)  return "agora";
  if (m < 60) return `${m}m atrás`;
  const h = Math.floor(m / 60);
  if (h < 24) return `há ${h}h`;
  const d = Math.floor(h / 24);
  return d === 1 ? "ontem" : `há ${d}d`;
}

function absoluteDate(date: Date): string {
  return date.toLocaleString("pt-BR", {
    day:    "2-digit",
    month:  "2-digit",
    hour:   "2-digit",
    minute: "2-digit",
  });
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
  processed:        "success",
  deferred:         "warning",
};

const KIND_ICON: Record<EventKind, React.ReactNode> = {
  inbox:   <InboxIcon   size={13} />,
  mission: <TargetIcon  size={13} />,
  memory:  <BrainIcon   size={13} />,
};

const KIND_ACCENT: Record<EventKind, string> = {
  inbox:   "text-status-info",
  mission: "text-status-active",
  memory:  "text-status-success",
};

const KIND_DOT: Record<EventKind, string> = {
  inbox:   "bg-status-info",
  mission: "bg-accent",
  memory:  "bg-status-success",
};

const KIND_LABEL: Record<EventKind, string> = {
  inbox:   "Inbox",
  mission: "Missão",
  memory:  "Memória",
};

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function TimelinePage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [events,    setEvents]    = useState<TimelineEvent[]>([]);
  const [loading,   setLoading]   = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [filter,    setFilter]    = useState<EventKind | "all">("all");

  const load = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    try {
      const [inbox, missions, memories] = await Promise.allSettled([
        api.listInbox(workspace.id),
        api.listMissions(workspace.id),
        api.listMemories(workspace.id, 100),
      ]);

      const evts: TimelineEvent[] = [];

      if (inbox.status === "fulfilled") {
        for (const item of inbox.value as InboxItem[]) {
          evts.push({
            id:          `inbox-${item.id}`,
            kind:        "inbox",
            title:       item.title ?? item.raw_content.slice(0, 70) + (item.raw_content.length > 70 ? "…" : ""),
            sub:         `${item.source} · ${item.type}`,
            badge:       item.status,
            badgeVariant: STATUS_BADGE[item.status] ?? "default",
            href:        "/inbox",
            ts:          new Date(item.created_at),
          });
        }
      }

      if (missions.status === "fulfilled") {
        for (const m of missions.value as Mission[]) {
          evts.push({
            id:          `mission-${m.id}`,
            kind:        "mission",
            title:       m.intent,
            sub:         m.trigger,
            badge:       m.status,
            badgeVariant: STATUS_BADGE[m.status] ?? "default",
            href:        "/missions",
            ts:          new Date(m.updated_at),
          });
        }
      }

      if (memories.status === "fulfilled") {
        for (const mem of memories.value as Memory[]) {
          evts.push({
            id:    `memory-${mem.id}`,
            kind:  "memory",
            title: mem.content.slice(0, 80) + (mem.content.length > 80 ? "…" : ""),
            sub:   `${mem.type} · ${(mem.importance * 100).toFixed(0)}% importância`,
            href:  "/memory",
            ts:    new Date(mem.created_at),
          });
        }
      }

      evts.sort((a, b) => b.ts.getTime() - a.ts.getTime());
      setEvents(evts);
      setLastRefresh(new Date());
    } finally {
      setLoading(false);
    }
  }, [workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load();
  }, [workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── derived ───
  const counts = events.reduce<Record<EventKind | "all", number>>(
    (acc, e) => { acc[e.kind]++; acc.all++; return acc; },
    { all: 0, inbox: 0, mission: 0, memory: 0 },
  );

  const visible = filter === "all" ? events : events.filter((e) => e.kind === filter);

  // ─── group by relative date ───
  const grouped = groupByDay(visible);

  if (wsLoading) {
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
        <div className="mb-6 flex items-center gap-2">
          <ActivityIcon size={14} className="text-content-muted" />
          <h1 className="text-md font-semibold text-content-primary">Timeline</h1>

          {lastRefresh && (
            <span className="ml-2 text-xs text-content-muted">
              atualizado {rel(lastRefresh)}
            </span>
          )}

          <button
            onClick={() => load()}
            disabled={loading}
            className={cn(
              "ml-auto flex items-center gap-1.5 rounded-md px-2 py-1 text-xs",
              "text-content-muted hover:text-content-secondary hover:bg-surface-subtle",
              "transition-colors disabled:opacity-30",
            )}
          >
            <RefreshCwIcon size={12} className={loading ? "animate-spin" : ""} />
            Atualizar
          </button>
        </div>

        {/* ── Filter chips ── */}
        <div className="mb-8 flex flex-wrap gap-1.5">
          <FilterChip
            active={filter === "all"}
            onClick={() => setFilter("all")}
            count={counts.all}
          >
            Todos
          </FilterChip>
          {(["inbox", "mission", "memory"] as EventKind[]).map((k) => (
            <FilterChip
              key={k}
              active={filter === k}
              onClick={() => setFilter(k)}
              count={counts[k]}
              icon={KIND_ICON[k]}
              iconClass={KIND_ACCENT[k]}
            >
              {KIND_LABEL[k]}
            </FilterChip>
          ))}
        </div>

        {/* ── Timeline ── */}
        {loading && events.length === 0 ? (
          <div className="flex justify-center py-16">
            <Spinner size="md" />
          </div>
        ) : visible.length === 0 ? (
          <p className="text-center text-sm text-content-muted py-16">
            Nenhum evento encontrado.
          </p>
        ) : (
          <div className="space-y-8">
            {grouped.map(({ label, items }) => (
              <DayGroup key={label} label={label} items={items} />
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

function FilterChip({
  active, onClick, count, icon, iconClass, children,
}: {
  active:     boolean;
  onClick:    () => void;
  count:      number;
  icon?:      React.ReactNode;
  iconClass?: string;
  children:   React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
        "border transition-colors",
        active
          ? "bg-accent-dim border-accent-subtle text-accent"
          : "border-[var(--border-subtle)] text-content-secondary hover:border-[var(--border-default)] hover:text-content-primary",
      )}
    >
      {icon && (
        <span className={cn("opacity-80", active ? "text-accent" : iconClass)}>
          {icon}
        </span>
      )}
      {children}
      <span
        className={cn(
          "rounded px-1 text-[10px]",
          active ? "bg-accent/20 text-accent" : "text-content-muted",
        )}
      >
        {count}
      </span>
    </button>
  );
}

function DayGroup({ label, items }: { label: string; items: TimelineEvent[] }) {
  return (
    <div>
      {/* Day label */}
      <div className="mb-3 flex items-center gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
          {label}
        </span>
        <div className="flex-1 h-px bg-[var(--border-subtle)]" />
      </div>

      {/* Events */}
      <div className="relative space-y-1">
        {/* Timeline line */}
        <div className="absolute left-[7px] top-3 bottom-3 w-px bg-[var(--border-subtle)]" />

        {items.map((evt) => (
          <EventRow key={evt.id} evt={evt} />
        ))}
      </div>
    </div>
  );
}

function EventRow({ evt }: { evt: TimelineEvent }) {
  return (
    <Link
      href={evt.href}
      className={cn(
        "group relative flex items-start gap-3 rounded-lg py-2.5 pl-7 pr-3",
        "hover:bg-[var(--surface-raised)] transition-colors",
      )}
    >
      {/* Timeline dot */}
      <span
        className={cn(
          "absolute left-0 top-4 flex h-3.5 w-3.5 items-center justify-center",
          "rounded-full border border-[var(--border-default)] bg-[var(--surface-base)]",
        )}
      >
        <span className={cn("h-1.5 w-1.5 rounded-full", KIND_DOT[evt.kind])} />
      </span>

      {/* Icon */}
      <span className={cn("mt-0.5 shrink-0", KIND_ACCENT[evt.kind])}>
        {KIND_ICON[evt.kind]}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-content-primary truncate group-hover:text-content-primary">
          {evt.title}
        </p>
        <p className="mt-0.5 text-[11px] text-content-muted">{evt.sub}</p>
      </div>

      {/* Right side */}
      <div className="shrink-0 flex flex-col items-end gap-1">
        {evt.badge && evt.badgeVariant && (
          <Badge variant={evt.badgeVariant} size="sm">{evt.badge}</Badge>
        )}
        <span
          className="text-[11px] text-content-muted tabular-nums"
          title={absoluteDate(evt.ts)}
        >
          {rel(evt.ts)}
        </span>
      </div>
    </Link>
  );
}

// ─────────────────────────────────────────────────────────────
// Grouping
// ─────────────────────────────────────────────────────────────

function dayLabel(date: Date): string {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const fmt = (d: Date) =>
    d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });

  if (fmt(date) === fmt(today))     return "Hoje";
  if (fmt(date) === fmt(yesterday)) return "Ontem";
  return date.toLocaleDateString("pt-BR", {
    weekday: "long", day: "numeric", month: "long",
  });
}

function groupByDay(events: TimelineEvent[]): { label: string; items: TimelineEvent[] }[] {
  const map = new Map<string, TimelineEvent[]>();
  for (const evt of events) {
    const label = dayLabel(evt.ts);
    const group = map.get(label) ?? [];
    group.push(evt);
    map.set(label, group);
  }
  return Array.from(map.entries()).map(([label, items]) => ({ label, items }));
}
