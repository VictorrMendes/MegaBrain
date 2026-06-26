"use client";

import { useEffect, useState } from "react";
import { api, type RuntimeStatus, type ComponentHealth } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  MonitorIcon, LoaderIcon, RefreshCwIcon, CheckCircleIcon,
  AlertCircleIcon, XCircleIcon, ZapIcon, NetworkIcon, ShieldIcon,
} from "lucide-react";

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

const HEALTH_ICON: Record<string, React.ReactNode> = {
  ready:    <CheckCircleIcon size={14} className="text-emerald-400" />,
  degraded: <AlertCircleIcon size={14} className="text-yellow-400" />,
  failed:   <XCircleIcon size={14} className="text-red-400" />,
};

const HEALTH_COLOR: Record<string, string> = {
  ready:    "text-emerald-400",
  degraded: "text-yellow-400",
  failed:   "text-red-400",
};

function HealthBadge({ status }: { status: ComponentHealth["status"] }) {
  return (
    <span className={cn("flex items-center gap-1 text-xs", HEALTH_COLOR[status])}>
      {HEALTH_ICON[status]}
      {status}
    </span>
  );
}

export function RuntimeDashboard() {
  const [data, setData] = useState<RuntimeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function load(refresh = false) {
    if (refresh) setRefreshing(true);
    try {
      const status = await api.getRuntimeStatus();
      setData(status);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoaderIcon size={20} className="animate-spin text-neutral-500" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-xs text-red-400">Falha ao carregar status do runtime.</p>
      </div>
    );
  }

  const overallOk = data.health.every((h) => h.status === "ready");
  const overallDegraded = !overallOk && data.health.some((h) => h.status !== "failed");

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <MonitorIcon size={16} className="text-neutral-400" />
          <h1 className="text-sm font-semibold text-neutral-300">Runtime</h1>
          <span
            className={cn(
              "ml-1 rounded px-2 py-0.5 text-[10px] font-medium",
              overallOk ? "bg-emerald-950 text-emerald-400" :
              overallDegraded ? "bg-yellow-950 text-yellow-400" :
              "bg-red-950 text-red-400"
            )}
          >
            {overallOk ? "operacional" : overallDegraded ? "degradado" : "falha"}
          </span>
          <p className="ml-auto text-[10px] text-neutral-600">
            checado em {formatDate(data.checked_at)}
          </p>
          <button
            onClick={() => load(true)}
            className="rounded p-1 text-neutral-600 hover:text-neutral-400 transition-colors"
          >
            <RefreshCwIcon size={13} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Provider */}
          <Card title="Provider LLM" icon={<ZapIcon size={13} />}>
            <Row label="Nome" value={data.provider.name} />
            <Row label="Modelo" value={data.provider.model} />
            {data.provider.embed_model && (
              <Row label="Embedding" value={data.provider.embed_model} />
            )}
            <Row label="Base URL" value={data.provider.base_url} mono />
          </Card>

          {/* Scheduler */}
          <Card title="Scheduler" icon={<NetworkIcon size={13} />}>
            <Row label="Triggers ativos" value={String(data.scheduler.active_triggers)} />
            <Row label="Pausados" value={String(data.scheduler.paused_triggers)} />
            <Row label="Total" value={String(data.scheduler.total_triggers)} />
          </Card>
        </div>

        {/* Health components */}
        <Section title="Saúde dos componentes">
          <div className="grid grid-cols-1 gap-2">
            {data.health.map((h) => (
              <div
                key={h.name}
                className="flex items-center gap-4 rounded-lg border border-neutral-800 px-4 py-3"
              >
                <HealthBadge status={h.status} />
                <span className="text-xs font-medium text-neutral-300 w-36 shrink-0">{h.name}</span>
                {h.latency_ms !== null && (
                  <span className="text-[10px] text-neutral-600">{h.latency_ms}ms</span>
                )}
                {h.detail && (
                  <span className="ml-auto text-[10px] text-neutral-600 truncate max-w-xs">{h.detail}</span>
                )}
              </div>
            ))}
          </div>
        </Section>

        {/* Capabilities */}
        <Section title={`Capabilities (${data.capabilities.length})`}>
          <div className="grid grid-cols-1 gap-2">
            {data.capabilities.map((cap) => (
              <div
                key={cap.name}
                className="flex items-start gap-3 rounded-lg border border-neutral-800 px-4 py-3"
              >
                <ShieldIcon size={13} className="mt-0.5 shrink-0 text-neutral-600" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-neutral-200">{cap.name}</span>
                    <span className="text-[10px] text-neutral-600">{cap.plugin}</span>
                    <span
                      className={cn(
                        "rounded px-1.5 py-0.5 text-[10px] font-medium",
                        cap.risk_level === "high" ? "bg-red-950 text-red-400" :
                        cap.risk_level === "medium" ? "bg-yellow-950 text-yellow-400" :
                        "bg-neutral-800 text-neutral-500"
                      )}
                    >
                      {cap.risk_level}
                    </span>
                    {cap.requires_confirmation && (
                      <span className="rounded px-1.5 py-0.5 text-[10px] bg-orange-950 text-orange-400">
                        aprovação
                      </span>
                    )}
                    {cap.requires_network && (
                      <span className="rounded px-1.5 py-0.5 text-[10px] bg-blue-950 text-blue-400">
                        rede
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-[11px] text-neutral-500 truncate">{cap.description}</p>
                  {cap.tags.length > 0 && (
                    <div className="mt-1 flex gap-1 flex-wrap">
                      {cap.tags.map((t) => (
                        <span key={t} className="rounded px-1 text-[9px] bg-neutral-800 text-neutral-500">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[10px] text-neutral-600">{cap.tool_count} tools</p>
                  <p className="text-[10px] text-neutral-600">conf {(cap.confidence_score * 100).toFixed(0)}%</p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Active missions */}
        {data.active_missions.length > 0 && (
          <Section title={`Missões ativas (${data.active_missions.length})`}>
            <div className="space-y-2">
              {data.active_missions.map((m) => (
                <div key={m.id} className="flex items-center gap-3 rounded-lg border border-neutral-800 px-4 py-3">
                  <span className="text-xs text-neutral-200 flex-1 truncate">{m.intent}</span>
                  <span className="text-[10px] text-blue-400 bg-blue-950 rounded px-1.5 py-0.5">{m.status}</span>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}

function Card({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-neutral-800 p-4">
      <div className="mb-3 flex items-center gap-2 text-neutral-500">
        {icon}
        <span className="text-xs font-semibold uppercase tracking-widest">{title}</span>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[11px] text-neutral-500 shrink-0">{label}</span>
      <span className={cn("text-[11px] text-neutral-300 truncate max-w-[200px]", mono && "font-mono")}>{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-widest text-neutral-500">{title}</h2>
      {children}
    </div>
  );
}
