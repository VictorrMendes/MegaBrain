"use client";

import { useEffect, useState } from "react";
import { api, type InboxItem, type Mission, type Memory, type Workspace } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  ActivityIcon, LoaderIcon, InboxIcon, TargetIcon, BrainIcon,
} from "lucide-react";

type EventKind = "inbox" | "mission" | "memory";

interface TimelineEvent {
  id: string;
  kind: EventKind;
  title: string;
  subtitle: string;
  badge?: string;
  badgeColor?: string;
  ts: string;
}

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

const KIND_ICON: Record<EventKind, React.ReactNode> = {
  inbox:   <InboxIcon size={12} className="text-blue-400" />,
  mission: <TargetIcon size={12} className="text-violet-400" />,
  memory:  <BrainIcon size={12} className="text-emerald-400" />,
};

const KIND_COLOR: Record<EventKind, string> = {
  inbox:   "border-blue-800 bg-blue-950/30",
  mission: "border-violet-800 bg-violet-950/30",
  memory:  "border-emerald-800 bg-emerald-950/30",
};

export function TimelinePage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<EventKind | "all">("all");

  useEffect(() => {
    async function load() {
      try {
        let wss = await api.listWorkspaces();
        if (wss.length === 0) {
          const ws = await api.createWorkspace("Personal");
          wss = [ws];
        }
        const ws = wss[0];
        setWorkspace(ws);

        const [inbox, missions, memories] = await Promise.allSettled([
          api.listInbox(ws.id),
          api.listMissions(ws.id),
          api.listMemories(ws.id, 100),
        ]);

        const evts: TimelineEvent[] = [];

        if (inbox.status === "fulfilled") {
          for (const item of inbox.value as InboxItem[]) {
            evts.push({
              id: `inbox-${item.id}`,
              kind: "inbox",
              title: item.title ?? item.raw_content.slice(0, 60) + (item.raw_content.length > 60 ? "…" : ""),
              subtitle: `${item.source} · ${item.type}`,
              badge: item.status,
              ts: item.created_at,
            });
          }
        }

        if (missions.status === "fulfilled") {
          for (const m of missions.value as Mission[]) {
            evts.push({
              id: `mission-${m.id}`,
              kind: "mission",
              title: m.intent,
              subtitle: m.trigger,
              badge: m.status,
              ts: m.updated_at,
            });
          }
        }

        if (memories.status === "fulfilled") {
          for (const mem of memories.value as Memory[]) {
            evts.push({
              id: `memory-${mem.id}`,
              kind: "memory",
              title: mem.content.slice(0, 80) + (mem.content.length > 80 ? "…" : ""),
              subtitle: `${mem.type} · importância ${(mem.importance * 100).toFixed(0)}%`,
              ts: mem.created_at,
            });
          }
        }

        evts.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
        setEvents(evts);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const visible = filter === "all" ? events : events.filter((e) => e.kind === filter);

  const counts = events.reduce<Record<EventKind | "all", number>>(
    (acc, e) => { acc[e.kind]++; acc.all++; return acc; },
    { all: 0, inbox: 0, mission: 0, memory: 0 }
  );

  if (loading) {
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
          <ActivityIcon size={15} className="text-neutral-400" />
          <h1 className="text-sm font-semibold text-neutral-300">Timeline</h1>
          <span className="ml-auto text-xs text-neutral-600">{visible.length} eventos</span>
        </div>

        {/* Filter */}
        <div className="mb-6 flex gap-1 rounded-lg border border-neutral-800 bg-neutral-900 p-1 w-fit flex-wrap">
          {(["all", "inbox", "mission", "memory"] as const).map((k) => (
            <button
              key={k}
              onClick={() => setFilter(k)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors",
                filter === k ? "bg-neutral-700 text-neutral-200" : "text-neutral-500 hover:text-neutral-400"
              )}
            >
              {k !== "all" && KIND_ICON[k as EventKind]}
              {k === "all" ? "Todos" : k} ({counts[k]})
            </button>
          ))}
        </div>

        {/* Events */}
        {visible.length === 0 ? (
          <p className="text-center text-xs text-neutral-600 py-10">Nenhum evento encontrado.</p>
        ) : (
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-px bg-neutral-800" />
            <div className="space-y-2 ml-10">
              {visible.map((evt) => (
                <div
                  key={evt.id}
                  className={cn(
                    "relative rounded-lg border p-3",
                    KIND_COLOR[evt.kind]
                  )}
                >
                  {/* dot */}
                  <div className={cn(
                    "absolute -left-[26px] top-3.5 flex h-4 w-4 items-center justify-center rounded-full border border-neutral-800 bg-neutral-950"
                  )}>
                    {KIND_ICON[evt.kind]}
                  </div>

                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-neutral-200 truncate">{evt.title}</p>
                      <p className="mt-0.5 text-[10px] text-neutral-600">{evt.subtitle}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      {evt.badge && (
                        <p className="text-[9px] text-neutral-500 mb-0.5">{evt.badge}</p>
                      )}
                      <p className="text-[10px] text-neutral-600">{formatDate(evt.ts)}</p>
                    </div>
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
