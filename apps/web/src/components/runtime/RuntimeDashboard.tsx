"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ComponentHealth, type RuntimeStatus, type Trigger } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Spinner } from "@/components/ui";
import {
  AlertCircleIcon,
  CalendarClockIcon,
  CheckCircle2Icon,
  ClockIcon,
  MonitorIcon,
  NetworkIcon,
  PauseIcon,
  PlayIcon,
  RefreshCwIcon,
  ShieldIcon,
  XCircleIcon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const AUTO_REFRESH_SECS = 30;

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function fmt(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function relShort(s: string | null): string {
  if (!s) return "—";
  const diff = Date.now() - new Date(s).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1)  return "agora";
  if (m < 60) return `${m}m atrás`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}

function relFuture(s: string | null): string {
  if (!s) return "—";
  const diff = new Date(s).getTime() - Date.now();
  if (diff < 0) return "atrasado";
  const m = Math.floor(diff / 60_000);
  if (m < 1)  return "< 1min";
  if (m < 60) return `em ${m}min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `em ${h}h`;
  return `em ${Math.floor(h / 24)}d`;
}

function healthBadge(status: ComponentHealth["status"]): BadgeVariant {
  if (status === "ready")    return "success";
  if (status === "degraded") return "warning";
  return "error";
}

function riskBadge(level: string): BadgeVariant {
  if (level === "high")   return "error";
  if (level === "medium") return "warning";
  return "muted";
}

function triggerBadge(status: string): BadgeVariant {
  if (status === "active")  return "success";
  if (status === "paused")  return "warning";
  if (status === "error")   return "error";
  return "muted";
}

function latencyColor(ms: number | null): string {
  if (ms === null) return "bg-content-muted";
  if (ms < 100)   return "bg-status-success";
  if (ms < 500)   return "bg-status-warning";
  return "bg-status-error";
}

const HEALTH_ICON: Record<string, React.ReactNode> = {
  ready:    <CheckCircle2Icon size={14} className="text-status-success" />,
  degraded: <AlertCircleIcon  size={14} className="text-status-warning" />,
  failed:   <XCircleIcon      size={14} className="text-status-error"   />,
};

const TRIGGER_TYPE_LABEL: Record<string, string> = {
  temporal: "Cron",
  event:    "Evento",
  rule:     "Regra",
};

// ─────────────────────────────────────────────────────────────
// Trigger row
// ─────────────────────────────────────────────────────────────

function TriggerRow({
  trigger,
  onToggle,
  toggling,
}: {
  trigger:  Trigger;
  onToggle: (t: Trigger) => void;
  toggling: boolean;
}) {
  const isActive = trigger.status === "active";
  return (
    <div className={cn(
      "flex items-start gap-3 rounded-lg border px-4 py-3",
      "border-[var(--border-subtle)] bg-[var(--surface-raised)]",
    )}>
      <CalendarClockIcon size={13} className="mt-0.5 shrink-0 text-content-muted" />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-content-primary">{trigger.name}</span>
          <Badge variant={triggerBadge(trigger.status)} size="sm">{trigger.status}</Badge>
          <Badge variant="muted" size="sm">{TRIGGER_TYPE_LABEL[trigger.type] ?? trigger.type}</Badge>
          {trigger.requires_approval && (
            <Badge variant="warning" size="sm">aprovação</Badge>
          )}
        </div>

        {trigger.cron_expression && (
          <p className="mt-0.5 font-mono text-[11px] text-content-muted">
            {trigger.cron_expression}
          </p>
        )}
        {trigger.event_type && (
          <p className="mt-0.5 text-[11px] text-content-muted">
            evento: <span className="font-mono">{trigger.event_type}</span>
          </p>
        )}
        {trigger.rule_expression && (
          <p className="mt-0.5 font-mono text-[11px] text-content-muted truncate max-w-xs">
            {trigger.rule_expression}
          </p>
        )}

        <div className="mt-1.5 flex items-center gap-4 text-[11px] text-content-muted">
          <span className="flex items-center gap-1">
            <ClockIcon size={10} />
            último: {relShort(trigger.last_fired_at)}
          </span>
          {trigger.next_fire_at && (
            <span className="flex items-center gap-1">
              próximo: {relFuture(trigger.next_fire_at)}
            </span>
          )}
          <span>{trigger.fire_count} execução{trigger.fire_count !== 1 ? "ões" : ""}</span>
        </div>
      </div>

      <button
        onClick={() => onToggle(trigger)}
        disabled={toggling}
        title={isActive ? "Pausar" : "Retomar"}
        className={cn(
          "rounded-md p-1.5 transition-colors disabled:opacity-40",
          isActive
            ? "text-content-muted hover:text-status-warning hover:bg-status-warning/10"
            : "text-content-muted hover:text-status-success hover:bg-status-success/10",
        )}
      >
        {toggling
          ? <Spinner size="sm" />
          : isActive
          ? <PauseIcon size={13} />
          : <PlayIcon  size={13} />}
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────

export function RuntimeDashboard() {
  const { current: workspace } = useWorkspace();
  const [data,       setData]       = useState<RuntimeStatus | null>(null);
  const [triggers,   setTriggers]   = useState<Trigger[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown,  setCountdown]  = useState(AUTO_REFRESH_SECS);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [status, trigs] = await Promise.all([
        api.getRuntimeStatus(),
        workspace ? api.listTriggers(workspace.id) : Promise.resolve([]),
      ]);
      setData(status);
      setTriggers(trigs);
      setCountdown(AUTO_REFRESH_SECS);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [workspace?.id]);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh countdown
  useEffect(() => {
    if (!autoRefresh) {
      if (countdownRef.current) clearInterval(countdownRef.current);
      return;
    }
    countdownRef.current = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) { load(true); return AUTO_REFRESH_SECS; }
        return c - 1;
      });
    }, 1000);
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [autoRefresh, load]);

  async function toggleTrigger(t: Trigger) {
    if (!workspace) return;
    setTogglingId(t.id);
    try {
      const updated = t.status === "active"
        ? await api.pauseTrigger(workspace.id, t.id)
        : await api.resumeTrigger(workspace.id, t.id);
      setTriggers((prev) => prev.map((x) => x.id === updated.id ? updated : x));
    } finally {
      setTogglingId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-status-error">Falha ao carregar status do runtime.</p>
      </div>
    );
  }

  const allOk  = data.health.every((h) => h.status === "ready");
  const anyFail = data.health.some((h) => h.status === "failed");
  const overallVariant: BadgeVariant = allOk ? "success" : anyFail ? "error" : "warning";
  const overallLabel = allOk ? "operacional" : anyFail ? "falha" : "degradado";

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 py-8">

        {/* ── Header ── */}
        <div className="mb-6 flex items-center gap-2 flex-wrap">
          <MonitorIcon size={14} className="text-content-muted" />
          <h1 className="text-md font-semibold text-content-primary">Runtime</h1>
          <Badge variant={overallVariant} size="md">{overallLabel}</Badge>

          <span className="ml-auto text-xs text-content-muted">{fmt(data.checked_at)}</span>

          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh((v) => !v)}
            title={autoRefresh ? "Desativar auto-refresh" : "Ativar auto-refresh"}
            className={cn(
              "rounded-md px-2 py-1.5 text-[11px] border transition-colors",
              autoRefresh
                ? "border-accent-subtle bg-accent-dim text-accent"
                : "border-[var(--border-default)] text-content-muted hover:text-content-secondary",
            )}
          >
            {autoRefresh ? `${countdown}s` : "auto"}
          </button>

          <button
            onClick={() => load(true)}
            disabled={refreshing}
            className="rounded-md p-1.5 text-content-muted hover:text-content-secondary hover:bg-surface-subtle transition-colors disabled:opacity-30"
          >
            <RefreshCwIcon size={13} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>

        {/* ── Provider + Scheduler ── */}
        <div className="mb-6 grid grid-cols-2 gap-4">
          <InfoCard title="Provider LLM" icon={<ZapIcon size={13} />}>
            <Row label="Nome"      value={data.provider.name} />
            <Row label="Modelo"    value={data.provider.model} />
            {data.provider.embed_model && (
              <Row label="Embedding" value={data.provider.embed_model} />
            )}
            <Row label="Base URL" value={data.provider.base_url} mono />
          </InfoCard>

          <InfoCard title="Scheduler" icon={<NetworkIcon size={13} />}>
            <Row label="Triggers ativos"  value={String(data.scheduler.active_triggers)} />
            <Row label="Pausados"         value={String(data.scheduler.paused_triggers)} />
            <Row label="Total"            value={String(data.scheduler.total_triggers)} />
            {data.active_missions.length > 0 && (
              <Row label="Missões ativas" value={String(data.active_missions.length)} />
            )}
          </InfoCard>
        </div>

        {/* ── Health ── */}
        <DetailSection title="Saúde dos componentes">
          <div className="space-y-1.5">
            {data.health.map((h) => (
              <div
                key={h.name}
                className={cn(
                  "flex items-center gap-3 rounded-lg border px-4 py-3",
                  h.status === "ready"
                    ? "border-[var(--border-subtle)] bg-[var(--surface-raised)]"
                    : "border-amber-900/30 bg-amber-950/20",
                )}
              >
                {HEALTH_ICON[h.status]}
                <span className="w-32 shrink-0 text-sm text-content-primary">{h.name}</span>
                <Badge variant={healthBadge(h.status)} size="sm">{h.status}</Badge>

                {/* Latency indicator */}
                {h.latency_ms !== null && (
                  <div className="flex items-center gap-1.5 ml-1">
                    <span
                      className={cn(
                        "inline-block h-2 w-2 rounded-full",
                        latencyColor(h.latency_ms),
                      )}
                    />
                    <span className="text-[11px] text-content-muted tabular-nums">
                      {h.latency_ms}ms
                    </span>
                  </div>
                )}

                {h.detail && (
                  <span className="ml-auto text-xs text-content-muted truncate max-w-xs">
                    {h.detail}
                  </span>
                )}
              </div>
            ))}
          </div>
        </DetailSection>

        {/* ── Triggers ── */}
        {triggers.length > 0 && (
          <DetailSection title={`Triggers · ${triggers.length}`}>
            <div className="space-y-1.5">
              {triggers.map((t) => (
                <TriggerRow
                  key={t.id}
                  trigger={t}
                  onToggle={toggleTrigger}
                  toggling={togglingId === t.id}
                />
              ))}
            </div>
          </DetailSection>
        )}

        {/* ── Capabilities ── */}
        {data.capabilities.length > 0 && (
          <DetailSection title={`Capabilities · ${data.capabilities.length}`}>
            <div className="space-y-1.5">
              {data.capabilities.map((cap) => (
                <div
                  key={cap.name}
                  className={cn(
                    "flex items-start gap-3 rounded-lg border border-[var(--border-subtle)]",
                    "bg-[var(--surface-raised)] px-4 py-3",
                  )}
                >
                  <ShieldIcon size={13} className="mt-0.5 shrink-0 text-content-muted" />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-content-primary">{cap.name}</span>
                      <span className="text-xs text-content-muted">{cap.plugin}</span>
                      <Badge variant={riskBadge(cap.risk_level)} size="sm">{cap.risk_level}</Badge>
                      {cap.requires_confirmation && (
                        <Badge variant="warning" size="sm">aprovação</Badge>
                      )}
                      {cap.requires_network && (
                        <Badge variant="info" size="sm">rede</Badge>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-content-muted truncate">{cap.description}</p>
                    {cap.tags.length > 0 && (
                      <div className="mt-1.5 flex gap-1 flex-wrap">
                        {cap.tags.map((t) => (
                          <span
                            key={t}
                            className="rounded px-1.5 text-[10px] border border-[var(--border-subtle)] text-content-muted"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="shrink-0 text-right">
                    <p className="text-xs text-content-muted">{cap.tool_count} tools</p>
                    <p className="text-xs text-content-muted">
                      {(cap.confidence_score * 100).toFixed(0)}% conf
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </DetailSection>
        )}

        {/* ── Active missions ── */}
        {data.active_missions.length > 0 && (
          <DetailSection title={`Missões ativas · ${data.active_missions.length}`}>
            <div className="space-y-1.5">
              {data.active_missions.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "flex items-center gap-3 rounded-lg border border-[var(--border-subtle)]",
                    "bg-[var(--surface-raised)] px-4 py-3",
                  )}
                >
                  <span className="h-2 w-2 rounded-full bg-accent animate-pulse-dot shrink-0" />
                  <span className="flex-1 truncate text-sm text-content-primary">{m.intent}</span>
                  <Badge variant="active" size="sm">{m.status}</Badge>
                </div>
              ))}
            </div>
          </DetailSection>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

function InfoCard({
  title, icon, children,
}: {
  title:    string;
  icon:     React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-4">
      <div className="mb-3 flex items-center gap-2 text-content-muted">
        {icon}
        <span className="text-[11px] font-semibold uppercase tracking-widest">{title}</span>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Row({
  label, value, mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="shrink-0 text-xs text-content-muted">{label}</span>
      <span className={cn("truncate text-xs text-content-primary max-w-[180px]", mono && "font-mono text-[11px]")}>
        {value}
      </span>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-content-muted">
        {title}
      </h2>
      {children}
    </div>
  );
}
