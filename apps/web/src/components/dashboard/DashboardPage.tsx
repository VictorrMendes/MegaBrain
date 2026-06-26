"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type DashboardSummary } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import {
  LoaderIcon,
  RefreshCwIcon,
  TargetIcon,
  InboxIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  XCircleIcon,
  BrainIcon,
  BookOpenIcon,
  PackageIcon,
  CalendarIcon,
} from "lucide-react";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

const STATUS_COLOR: Record<string, string> = {
  pending:          "text-neutral-400",
  planning:         "text-blue-400",
  waiting_approval: "text-yellow-400",
  ready:            "text-emerald-400",
  running:          "text-blue-300",
  paused:           "text-orange-400",
  succeeded:        "text-emerald-400",
  failed:           "text-red-400",
  cancelled:        "text-neutral-600",
};

export function DashboardPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  async function load(ws = workspace, refresh = false) {
    if (!ws) return;
    if (refresh) setRefreshing(true); else setLoading(true);
    try {
      const summary = await api.getDashboard(ws.id);
      setData(summary);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    if (workspace) load(workspace);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace?.id]);

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoaderIcon size={20} className="animate-spin text-neutral-500" />
      </div>
    );
  }

  const now = new Date().toLocaleDateString("pt-BR", {
    weekday: "long", day: "2-digit", month: "long", year: "numeric",
  });

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-6 py-8">
        {/* Header greeting */}
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-light text-neutral-100 tracking-tight">
              {greeting()}.
            </h1>
            <p className="mt-1 text-sm text-neutral-500 capitalize">{now}</p>
            {workspace && (
              <p className="mt-0.5 text-xs text-neutral-600">
                Workspace: <span className="text-neutral-400">{workspace.name}</span>
              </p>
            )}
          </div>
          <button
            onClick={() => load(workspace ?? undefined, true)}
            disabled={refreshing}
            className="rounded-lg p-2 text-neutral-600 hover:text-neutral-400 hover:bg-neutral-800 transition-colors"
          >
            <RefreshCwIcon size={15} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>

        {!data ? (
          <p className="text-center text-xs text-neutral-600 py-10">
            Nenhum dado disponível.
          </p>
        ) : (
          <>
            {/* KPI row */}
            <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <KpiCard
                icon={<TargetIcon size={14} />}
                label="Missões"
                value={String(data.missions.total)}
                sub={`${data.missions.running} em execução`}
                href="/missions"
                accent={data.missions.running > 0 ? "blue" : "default"}
              />
              <KpiCard
                icon={<InboxIcon size={14} />}
                label="Inbox"
                value={String(data.inbox_pending)}
                sub="pendentes"
                href="/inbox"
                accent={data.inbox_pending > 0 ? "yellow" : "default"}
              />
              <KpiCard
                icon={<SystemIcon health={data.health} />}
                label="Sistema"
                value={data.health.every((h) => h.status === "ready") ? "OK" : "Atenção"}
                sub={`${data.health.filter((h) => h.status === "ready").length}/${data.health.length} componentes`}
                href="/runtime"
                accent={data.health.every((h) => h.status === "ready") ? "green" : "red"}
              />
              <KpiCard
                icon={<CalendarIcon size={14} />}
                label="Scheduler"
                value={String(data.scheduler.total_triggers)}
                sub={`${data.scheduler.active_triggers} ativos`}
                href="/runtime"
                accent="default"
              />
            </div>

            {/* Missions + Memories */}
            <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Section
                title="Missões recentes"
                href="/missions"
                icon={<TargetIcon size={12} />}
              >
                {data.recent_missions.length === 0 ? (
                  <Empty text="Nenhuma missão ainda." />
                ) : (
                  data.recent_missions.map((m) => (
                    <Link
                      key={String(m.id)}
                      href="/missions"
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-neutral-800/60 transition-colors"
                    >
                      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full bg-current", STATUS_COLOR[m.status])} />
                      <span className="flex-1 truncate text-xs text-neutral-300">{m.intent}</span>
                      <span className={cn("shrink-0 text-[10px]", STATUS_COLOR[m.status])}>{m.status}</span>
                    </Link>
                  ))
                )}
              </Section>

              <Section
                title="Memórias recentes"
                href="/memory"
                icon={<BrainIcon size={12} />}
              >
                {data.recent_memories.length === 0 ? (
                  <Empty text="Nenhuma memória ainda." />
                ) : (
                  data.recent_memories.map((m) => (
                    <div
                      key={String(m.id)}
                      className="flex items-start gap-2 rounded-md px-2 py-1.5"
                    >
                      <span className="shrink-0 rounded px-1 text-[9px] bg-neutral-800 text-neutral-500 mt-0.5">
                        {m.type}
                      </span>
                      <span className="flex-1 text-xs text-neutral-400 line-clamp-2">{m.content}</span>
                    </div>
                  ))
                )}
              </Section>
            </div>

            {/* Knowledge + Artifacts */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Section
                title="Conhecimento recente"
                href="/knowledge"
                icon={<BookOpenIcon size={12} />}
              >
                {data.recent_facts.length === 0 ? (
                  <Empty text="Nenhum fato ainda." />
                ) : (
                  data.recent_facts.map((f) => (
                    <div
                      key={String(f.id)}
                      className="flex items-start gap-2 rounded-md px-2 py-1.5"
                    >
                      <span className={cn(
                        "mt-0.5 shrink-0 rounded px-1 text-[9px]",
                        f.confidence >= 0.8 ? "bg-emerald-950 text-emerald-500" : "bg-yellow-950 text-yellow-500"
                      )}>
                        {Math.round(f.confidence * 100)}%
                      </span>
                      <span className="text-xs text-neutral-400 line-clamp-2">{f.statement}</span>
                    </div>
                  ))
                )}
              </Section>

              <Section
                title="Artifacts produzidos"
                href="/artifacts"
                icon={<PackageIcon size={12} />}
              >
                {data.recent_artifacts.length === 0 ? (
                  <Empty text="Nenhum artifact ainda." />
                ) : (
                  data.recent_artifacts.map((a) => (
                    <div
                      key={String(a.id)}
                      className="flex items-center gap-2 rounded-md px-2 py-1.5"
                    >
                      <span className="shrink-0 rounded px-1 text-[9px] bg-neutral-800 text-neutral-500">
                        {a.type}
                      </span>
                      <span className="flex-1 truncate text-xs text-neutral-400">{a.name}</span>
                      <span className="shrink-0 text-[10px] text-neutral-600">{formatDate(a.created_at)}</span>
                    </div>
                  ))
                )}
              </Section>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function KpiCard({
  icon, label, value, sub, href, accent = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  href: string;
  accent?: "default" | "blue" | "yellow" | "green" | "red";
}) {
  const accentClass = {
    default: "text-neutral-400",
    blue:    "text-blue-400",
    yellow:  "text-yellow-400",
    green:   "text-emerald-400",
    red:     "text-red-400",
  }[accent];

  return (
    <Link
      href={href}
      className="group flex flex-col gap-1 rounded-xl border border-neutral-800 bg-neutral-900 p-4 hover:border-neutral-700 transition-colors"
    >
      <div className={cn("flex items-center gap-1.5", accentClass)}>
        {icon}
        <span className="text-xs text-neutral-500">{label}</span>
      </div>
      <p className={cn("text-2xl font-semibold tracking-tight", accentClass)}>{value}</p>
      <p className="text-[11px] text-neutral-600">{sub}</p>
    </Link>
  );
}

function SystemIcon({ health }: { health: DashboardSummary["health"] }) {
  const allOk = health.every((h) => h.status === "ready");
  const anyFail = health.some((h) => h.status === "failed");
  if (anyFail) return <XCircleIcon size={14} />;
  if (!allOk) return <AlertCircleIcon size={14} />;
  return <CheckCircleIcon size={14} />;
}

function Section({
  title, href, icon, children,
}: {
  title: string;
  href: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-4">
      <div className="mb-3 flex items-center gap-1.5">
        <span className="text-neutral-500">{icon}</span>
        <Link href={href} className="text-xs font-semibold uppercase tracking-widest text-neutral-500 hover:text-neutral-400">
          {title}
        </Link>
      </div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <p className="py-3 text-center text-xs text-neutral-700">{text}</p>
  );
}
