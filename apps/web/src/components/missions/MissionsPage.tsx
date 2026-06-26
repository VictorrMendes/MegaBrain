"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  type Mission,
  type MissionDetail,
  type MissionStep,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Button, Spinner } from "@/components/ui";
import {
  CheckCircle2Icon,
  ChevronRightIcon,
  CircleIcon,
  MinusCircleIcon,
  PackageIcon,
  PlayIcon,
  RefreshCwIcon,
  TargetIcon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  XIcon,
  CheckIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, BadgeVariant> = {
  pending:          "default",
  planning:         "info",
  waiting_approval: "warning",
  ready:            "info",
  running:          "active",
  paused:           "warning",
  retrying:         "warning",
  succeeded:        "success",
  failed:           "error",
  cancelled:        "muted",
};

const STATUS_LABEL: Record<string, string> = {
  pending:          "pendente",
  planning:         "planejando",
  waiting_approval: "aprovação",
  ready:            "pronto",
  running:          "executando",
  paused:           "pausado",
  retrying:         "repetindo",
  succeeded:        "concluído",
  failed:           "falhou",
  cancelled:        "cancelado",
};

const STEP_BADGE: Record<string, BadgeVariant> = {
  pending:   "default",
  running:   "active",
  succeeded: "success",
  failed:    "error",
  cancelled: "muted",
  skipped:   "muted",
};

const ACTIVE_STATUSES = new Set(["running", "planning"]);

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function stepDuration(step: MissionStep): string {
  if (!step.started_at) return "";
  const end = step.finished_at ? new Date(step.finished_at) : new Date();
  const ms  = end.getTime() - new Date(step.started_at).getTime();
  if (ms < 1000)  return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

// ─────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────

export function MissionsPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [missions,       setMissions]       = useState<Mission[]>([]);
  const [selected,       setSelected]       = useState<MissionDetail | null>(null);
  const [loading,        setLoading]        = useState(false);
  const [actionLoading,  setActionLoading]  = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ─── load missions list ───
  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    api.listMissions(workspace.id)
      .then(setMissions)
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  // ─── polling when mission is active ───
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (!selected || !workspace) return;
    if (!ACTIVE_STATUSES.has(selected.status)) return;

    pollRef.current = setInterval(async () => {
      const detail = await api.getMission(workspace.id, selected.id);
      setSelected(detail);
      setMissions((prev) =>
        prev.map((m) => (m.id === detail.id ? detail : m)),
      );
      if (!ACTIVE_STATUSES.has(detail.status) && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [selected?.id, selected?.status, workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function selectMission(id: string) {
    if (!workspace) return;
    const detail = await api.getMission(workspace.id, id);
    setSelected(detail);
  }

  async function doAction(fn: () => Promise<Mission>) {
    setActionLoading(true);
    try {
      const updated = await fn();
      setMissions((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
      if (selected?.id === updated.id) {
        const detail = await api.getMission(workspace!.id, updated.id);
        setSelected(detail);
      }
    } finally {
      setActionLoading(false);
    }
  }

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Mission list ── */}
      <aside
        className={cn(
          "flex w-72 shrink-0 flex-col",
          "border-r border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        )}
      >
        <header className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
          <TargetIcon size={14} className="text-content-muted" />
          <span className="text-sm font-medium text-content-primary">Missões</span>
          <span className="ml-auto text-[11px] text-content-muted">{missions.length}</span>
        </header>

        <div className="flex-1 overflow-y-auto py-1">
          {missions.length === 0 ? (
            <p className="px-4 py-8 text-center text-xs text-content-muted">
              Nenhuma missão ainda.
            </p>
          ) : (
            missions.map((m) => {
              const isActive = selected?.id === m.id;
              return (
                <button
                  key={m.id}
                  onClick={() => selectMission(m.id)}
                  className={cn(
                    "flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors",
                    "border-b border-[var(--border-subtle)]",
                    isActive
                      ? "bg-[var(--surface-overlay)]"
                      : "hover:bg-[var(--surface-subtle)]",
                  )}
                >
                  <StatusDot status={m.status} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-content-primary truncate">{m.intent}</p>
                    <p className="mt-0.5 text-[10px] text-content-muted">{formatDate(m.created_at)}</p>
                  </div>
                  <ChevronRightIcon
                    size={12}
                    className={cn("mt-0.5 shrink-0", isActive ? "text-accent" : "text-content-muted")}
                  />
                </button>
              );
            })
          )}
        </div>
      </aside>

      {/* ── Detail panel ── */}
      <main className="flex-1 overflow-y-auto bg-[var(--surface-base)]">
        {!selected ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-content-muted">Selecione uma missão</p>
          </div>
        ) : (
          <div className="p-6 max-w-3xl mx-auto animate-fade-in">

            {/* ── Header ── */}
            <div className="mb-5 flex items-start gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-md font-semibold text-content-primary">{selected.intent}</h1>
                  <Badge variant={STATUS_BADGE[selected.status] ?? "default"} size="md">
                    {STATUS_LABEL[selected.status] ?? selected.status}
                  </Badge>
                  {ACTIVE_STATUSES.has(selected.status) && (
                    <span className="flex items-center gap-1 text-xs text-accent">
                      <Spinner size="sm" className="text-accent" />
                      ao vivo
                    </span>
                  )}
                </div>
                <p className="mt-1.5 text-xs text-content-muted">
                  Criado {formatDate(selected.created_at)}
                  {selected.completed_at && ` · Concluído ${formatDate(selected.completed_at)}`}
                  {" · "}{selected.trigger}
                </p>
              </div>
            </div>

            {/* ── Actions ── */}
            {!actionLoading ? (
              <div className="mb-6 flex gap-2 flex-wrap">
                {selected.status === "pending" && (
                  <Button
                    variant="secondary" size="sm"
                    onClick={() => doAction(() => api.planMission(workspace!.id, selected.id))}
                  >
                    <PlayIcon size={12} /> Planejar
                  </Button>
                )}
                {selected.status === "waiting_approval" && (
                  <>
                    <Button
                      variant="secondary" size="sm"
                      className="text-status-success border-emerald-900/40 hover:bg-emerald-950/40"
                      onClick={() => doAction(() => api.approveMission(workspace!.id, selected.id))}
                    >
                      <CheckIcon size={12} /> Aprovar
                    </Button>
                    <Button
                      variant="danger" size="sm"
                      onClick={() => doAction(() => api.rejectMission(workspace!.id, selected.id))}
                    >
                      <XIcon size={12} /> Rejeitar
                    </Button>
                  </>
                )}
                {selected.status === "ready" && (
                  <Button
                    variant="primary" size="sm"
                    onClick={() => doAction(() => api.runMission(workspace!.id, selected.id))}
                  >
                    <PlayIcon size={12} /> Executar
                  </Button>
                )}
                {["pending","planning","waiting_approval","ready","running","paused"].includes(selected.status) && (
                  <Button
                    variant="danger" size="sm"
                    onClick={() => doAction(() => api.cancelMission(workspace!.id, selected.id))}
                  >
                    <XIcon size={12} /> Cancelar
                  </Button>
                )}
                {selected.status === "failed" && (
                  <Button
                    variant="secondary" size="sm"
                    onClick={() => doAction(() => api.planMission(workspace!.id, selected.id))}
                  >
                    <RefreshCwIcon size={12} /> Replanejar
                  </Button>
                )}
              </div>
            ) : (
              <div className="mb-6">
                <Spinner size="sm" />
              </div>
            )}

            {/* ── Steps pipeline ── */}
            {selected.steps.length > 0 && (
              <DetailSection title="Execução">
                <div className="mt-1">
                  {selected.steps.map((step, i) => (
                    <StepRow
                      key={step.id}
                      step={step}
                      isLast={i === selected.steps.length - 1}
                    />
                  ))}
                </div>
              </DetailSection>
            )}

            {/* ── Artifacts ── */}
            {selected.artifacts.length > 0 && (
              <DetailSection title="Artifacts">
                <div className="mt-2 space-y-1.5">
                  {selected.artifacts.map((a) => (
                    <div
                      key={a.id}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2.5",
                        "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
                      )}
                    >
                      <PackageIcon size={13} className="shrink-0 text-content-muted" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-content-primary truncate">{a.name}</p>
                        <p className="text-[10px] text-content-muted">{a.type} · {a.mime}</p>
                      </div>
                      <span className="text-[10px] text-content-muted shrink-0">
                        {formatDate(a.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              </DetailSection>
            )}

            {/* ── Logs ── */}
            {selected.logs.length > 0 && (
              <DetailSection title="Logs">
                <div
                  className={cn(
                    "mt-2 rounded-lg border border-[var(--border-subtle)]",
                    "bg-[var(--surface-inset)] p-4 font-mono max-h-72 overflow-y-auto",
                  )}
                >
                  {selected.logs.map((log) => (
                    <div key={log.id} className="flex gap-3 text-[11px] leading-relaxed">
                      <span
                        className={cn(
                          "shrink-0 w-10",
                          log.level === "error"   && "text-status-error",
                          log.level === "warning" && "text-status-warning",
                          log.level === "info"    && "text-content-muted",
                          log.level === "debug"   && "text-content-placeholder",
                        )}
                      >
                        [{log.level}]
                      </span>
                      <span className="text-content-secondary">{log.message}</span>
                    </div>
                  ))}
                </div>
              </DetailSection>
            )}

          </div>
        )}
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  const color: Record<string, string> = {
    pending:          "bg-content-muted",
    planning:         "bg-status-info",
    waiting_approval: "bg-status-warning",
    ready:            "bg-status-success",
    running:          "bg-accent animate-pulse-dot",
    paused:           "bg-status-warning",
    retrying:         "bg-status-warning",
    succeeded:        "bg-status-success",
    failed:           "bg-status-error",
    cancelled:        "bg-content-placeholder",
  };
  return (
    <span
      className={cn(
        "mt-1.5 h-2 w-2 shrink-0 rounded-full",
        color[status] ?? "bg-content-muted",
      )}
    />
  );
}

function StepRow({ step, isLast }: { step: MissionStep; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = step.output !== null || Object.keys(step.input ?? {}).length > 0;
  const duration  = stepDuration(step);

  return (
    <div className="relative flex gap-3 pb-0">
      {/* Vertical connector line */}
      {!isLast && (
        <div className="absolute left-[8px] top-5 bottom-0 w-px bg-[var(--border-subtle)]" />
      )}

      {/* Status icon */}
      <div className="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center">
        <StepStatusIcon status={step.status} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-content-primary">{step.tool}</span>
          <Badge variant={STEP_BADGE[step.status] ?? "default"} size="sm">
            {step.status}
          </Badge>
          <span className="text-[11px] text-content-muted">{step.type}</span>
          {duration && (
            <span className="ml-auto text-[11px] text-content-muted tabular-nums">
              {duration}
            </span>
          )}
        </div>

        {/* Expand toggle */}
        {hasDetails && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="mt-1.5 flex items-center gap-1 text-[11px] text-content-muted hover:text-content-secondary transition-colors"
          >
            {expanded ? <ChevronUpIcon size={11} /> : <ChevronDownIcon size={11} />}
            {expanded ? "ocultar" : "detalhes"}
          </button>
        )}

        {/* Expanded: input */}
        {expanded && step.input && Object.keys(step.input).length > 0 && (
          <JsonBlock label="input" data={step.input} />
        )}

        {/* Expanded: output */}
        {expanded && step.output && (
          <JsonBlock label="output" data={step.output} />
        )}
      </div>
    </div>
  );
}

function StepStatusIcon({ status }: { status: string }) {
  if (status === "succeeded")
    return <CheckCircle2Icon size={16} className="text-status-success" />;
  if (status === "failed")
    return <XCircleIcon size={16} className="text-status-error" />;
  if (status === "running")
    return <Spinner size="sm" className="text-accent" />;
  if (status === "cancelled" || status === "skipped")
    return <MinusCircleIcon size={16} className="text-content-muted" />;
  return <CircleIcon size={16} className="text-content-muted" />;
}

function JsonBlock({ label, data }: { label: string; data: unknown }) {
  return (
    <div className="mt-2">
      <p className="text-[10px] font-medium uppercase tracking-widest text-content-muted mb-1">
        {label}
      </p>
      <pre
        className={cn(
          "rounded-lg border border-[var(--border-subtle)]",
          "bg-[var(--surface-inset)] p-3",
          "text-[11px] text-content-secondary font-mono",
          "overflow-x-auto max-h-48",
        )}
      >
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function DetailSection({
  title, children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-8">
      <h2 className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
        {title}
      </h2>
      {children}
    </div>
  );
}
