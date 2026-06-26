"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  type Mission,
  type MissionDetail,
  type MissionLog,
  type MissionStep,
  type MissionStatus,
} from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, type BadgeVariant, Button, Dialog, DialogContent, DialogFooter, Progress, Spinner } from "@/components/ui";
import {
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CircleDashedIcon,
  CircleIcon,
  ClockIcon,
  FileTextIcon,
  FilterIcon,
  MinusCircleIcon,
  PackageIcon,
  PlayIcon,
  PlusIcon,
  RefreshCwIcon,
  RotateCcwIcon,
  TargetIcon,
  XCircleIcon,
  XIcon,
  ZapIcon,
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

// Left-border color per status (CI/CD job-block style)
const STATUS_BORDER: Record<string, string> = {
  pending:          "border-l-content-muted",
  planning:         "border-l-blue-500/60",
  waiting_approval: "border-l-status-warning",
  ready:            "border-l-status-success",
  running:          "border-l-accent",
  paused:           "border-l-status-warning",
  retrying:         "border-l-status-warning",
  succeeded:        "border-l-status-success",
  failed:           "border-l-status-error",
  cancelled:        "border-l-content-placeholder",
};

const ACTIVE = new Set<MissionStatus>(["running", "planning", "retrying"]);
const CANCELLABLE = new Set<MissionStatus>(["pending","planning","waiting_approval","ready","running","paused"]);

type FilterTab = "all" | "active" | "pending" | "done";

// ─────────────────────────────────────────────────────────────
// Time helpers
// ─────────────────────────────────────────────────────────────

function fmt(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function relTime(s: string): string {
  const ms = Date.now() - new Date(s).getTime();
  if (ms < 60_000)  return `${Math.floor(ms / 1000)}s atrás`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m atrás`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h atrás`;
  return `${Math.floor(ms / 86_400_000)}d atrás`;
}

function durationMs(start: string, end?: string | null): number {
  return (end ? new Date(end) : new Date()).getTime() - new Date(start).getTime();
}

function fmtDuration(ms: number): string {
  if (ms < 1000)   return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function stepDuration(step: MissionStep): string {
  if (!step.started_at) return "";
  return fmtDuration(durationMs(step.started_at, step.finished_at));
}

// ─────────────────────────────────────────────────────────────
// Progress calculation
// ─────────────────────────────────────────────────────────────

function calcProgress(steps: MissionStep[]): { done: number; total: number; pct: number } {
  if (steps.length === 0) return { done: 0, total: 0, pct: 0 };
  const done = steps.filter((s) => ["succeeded","failed","skipped","cancelled"].includes(s.status)).length;
  return { done, total: steps.length, pct: Math.round((done / steps.length) * 100) };
}

// ─────────────────────────────────────────────────────────────
// Create Mission Dialog
// ─────────────────────────────────────────────────────────────

function CreateMissionDialog({
  open,
  onClose,
  onCreate,
}: {
  open:     boolean;
  onClose:  () => void;
  onCreate: (intent: string, requiresApproval: boolean) => Promise<void>;
}) {
  const [intent,  setIntent]  = useState("");
  const [approval, setApproval] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    if (!intent.trim()) return;
    setLoading(true);
    try {
      await onCreate(intent.trim(), approval);
      setIntent("");
      setApproval(false);
      onClose();
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent size="md" title="Nova missão" onClose={onClose}>
        <p className="mb-4 text-xs text-content-muted">
          Descreva o que o PAIOS deve fazer. Seja específico — o planner vai decompor a tarefa em passos.
        </p>

        <label className="mb-1.5 block text-xs font-medium text-content-secondary">Intenção</label>
        <textarea
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="Ex: Monitorar temperatura do servidor e notificar se passar de 80°C"
          rows={4}
          className={cn(
            "w-full resize-none rounded-lg border border-[var(--border-default)] bg-[var(--surface-raised)]",
            "px-3 py-2.5 text-sm text-content-primary placeholder:text-content-placeholder",
            "focus:outline-none focus:border-[var(--border-accent)] transition-colors",
          )}
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.ctrlKey) handleCreate();
          }}
        />

        <label className="mt-4 flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={approval}
            onChange={(e) => setApproval(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-[var(--border-default)] accent-accent"
          />
          <span className="text-xs text-content-secondary">Requer aprovação antes de executar</span>
        </label>

        <DialogFooter>
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-xs text-content-muted hover:text-content-primary transition-colors"
          >
            Cancelar
          </button>
          <Button
            variant="primary"
            size="sm"
            disabled={!intent.trim() || loading}
            onClick={handleCreate}
          >
            {loading ? <Spinner size="sm" className="text-white mr-1.5" /> : <PlayIcon size={12} className="mr-1.5" />}
            Criar missão
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─────────────────────────────────────────────────────────────
// Sidebar row
// ─────────────────────────────────────────────────────────────

function MissionRow({
  mission,
  active,
  onClick,
}: {
  mission: Mission;
  active:  boolean;
  onClick: () => void;
}) {
  const isLive = ACTIVE.has(mission.status);

  return (
    <button
      onClick={onClick}
      className={cn(
        "group w-full flex items-start gap-3 px-3 py-3 text-left transition-colors",
        "border-b border-[var(--border-subtle)]",
        "border-l-2",
        STATUS_BORDER[mission.status] ?? "border-l-content-muted",
        active ? "bg-[var(--surface-overlay)]" : "hover:bg-[var(--surface-subtle)]",
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          {isLive && (
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent animate-pulse-dot" />
          )}
          <p className="text-xs font-medium text-content-primary truncate leading-snug">
            {mission.intent}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={STATUS_BADGE[mission.status] ?? "default"} size="sm">
            {STATUS_LABEL[mission.status] ?? mission.status}
          </Badge>
          <span className="text-[10px] text-content-muted">{relTime(mission.created_at)}</span>
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Step block (CI/CD job style)
// ─────────────────────────────────────────────────────────────

function StepBlock({
  step,
  stepLogs,
  stepArtifacts,
  isLast,
}: {
  step:          MissionStep;
  stepLogs:      MissionLog[];
  stepArtifacts: import("@/lib/api").MissionArtifact[];
  isLast:        boolean;
}) {
  const [open, setOpen] = useState(false);
  const dur = stepDuration(step);
  const hasContent = step.input && Object.keys(step.input).length > 0
    || step.output
    || stepLogs.length > 0
    || stepArtifacts.length > 0;

  return (
    <div className="relative flex gap-0 group/step">
      {/* Connector line */}
      {!isLast && (
        <div className="absolute left-[19px] top-8 bottom-0 w-px bg-[var(--border-subtle)]" />
      )}

      {/* Status icon column */}
      <div className="flex flex-col items-center pt-3 pl-2.5 pr-3 shrink-0">
        <StepIcon status={step.status} />
      </div>

      {/* Job block */}
      <div
        className={cn(
          "flex-1 mb-2.5 min-w-0 rounded-lg",
          "border border-l-2 border-[var(--border-subtle)]",
          "bg-[var(--surface-raised)]",
          STATUS_BORDER[step.status] ?? "border-l-content-muted",
        )}
      >
        {/* Row header */}
        <div className="flex items-center gap-2 px-3 py-2.5">
          <span className="flex-1 min-w-0 text-xs font-medium text-content-primary truncate">
            {step.tool}
          </span>

          <span className="text-[10px] text-content-muted shrink-0">{step.type}</span>

          <Badge variant={stepBadge(step.status)} size="sm">
            {step.status}
          </Badge>

          {step.retry_count > 0 && (
            <span
              className="flex items-center gap-1 rounded border border-status-warning/40 bg-status-warning/10 px-1.5 py-0.5 text-[10px] text-status-warning"
              title={`${step.retry_count} tentativas`}
            >
              <RotateCcwIcon size={8} />
              {step.retry_count}×
            </span>
          )}

          {dur && (
            <span className="ml-1 text-[11px] text-content-muted tabular-nums shrink-0">
              {dur}
            </span>
          )}

          {step.status === "running" && (
            <Spinner size="sm" className="text-accent shrink-0" />
          )}

          {hasContent && (
            <button
              onClick={() => setOpen((v) => !v)}
              className="ml-1 text-content-muted hover:text-content-secondary transition-colors shrink-0"
            >
              {open ? <ChevronUpIcon size={12} /> : <ChevronDownIcon size={12} />}
            </button>
          )}
        </div>

        {/* Expanded content */}
        {open && (
          <div className="border-t border-[var(--border-subtle)] px-3 py-3 space-y-3">
            {step.input && Object.keys(step.input).length > 0 && (
              <JsonBlock label="Input" data={step.input} />
            )}
            {step.output && (
              <JsonBlock label="Output" data={step.output} />
            )}
            {stepLogs.length > 0 && (
              <StepLogBlock logs={stepLogs} />
            )}
            {stepArtifacts.length > 0 && (
              <StepArtifactBlock artifacts={stepArtifacts} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function stepBadge(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    pending:   "default",
    running:   "active",
    succeeded: "success",
    failed:    "error",
    cancelled: "muted",
    skipped:   "muted",
  };
  return map[status] ?? "default";
}

function StepIcon({ status }: { status: string }) {
  const cls = "h-5 w-5";
  if (status === "succeeded")  return <CheckCircle2Icon className={cn(cls, "text-status-success")} />;
  if (status === "failed")     return <XCircleIcon       className={cn(cls, "text-status-error")} />;
  if (status === "running")    return <ActivityIcon      className={cn(cls, "text-accent animate-pulse")} />;
  if (status === "retrying")   return <RotateCcwIcon     className={cn(cls, "text-status-warning animate-spin")} />;
  if (status === "skipped" || status === "cancelled")
                               return <MinusCircleIcon   className={cn(cls, "text-content-muted")} />;
  if (status === "pending")    return <CircleIcon        className={cn(cls, "text-content-muted")} />;
  return                              <CircleDashedIcon  className={cn(cls, "text-content-muted")} />;
}

// ─────────────────────────────────────────────────────────────
// Step sub-components
// ─────────────────────────────────────────────────────────────

function JsonBlock({ label, data }: { label: string; data: unknown }) {
  const [collapsed, setCollapsed] = useState(true);
  const text = JSON.stringify(data, null, 2);
  const lines = text.split("\n").length;

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
          {label}
        </span>
        {lines > 6 && (
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="text-[10px] text-content-muted hover:text-content-secondary transition-colors"
          >
            {collapsed ? "expandir" : "recolher"}
          </button>
        )}
      </div>
      <pre
        className={cn(
          "overflow-x-auto rounded-md border border-[var(--border-subtle)]",
          "bg-[var(--surface-inset)] px-3 py-2 text-[11px] text-content-secondary font-mono",
          collapsed && lines > 6 && "max-h-28",
        )}
      >
        {text}
      </pre>
    </div>
  );
}

function StepLogBlock({ logs }: { logs: MissionLog[] }) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1.5">
        <FileTextIcon size={10} className="text-content-muted" />
        <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
          Logs ({logs.length})
        </span>
      </div>
      <div className="max-h-36 overflow-y-auto rounded-md border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-3 py-2">
        {logs.map((log) => (
          <div key={log.id} className="flex gap-2 text-[11px] leading-relaxed">
            <span className={cn(
              "shrink-0 w-10 font-mono",
              log.level === "error"   && "text-status-error",
              log.level === "warning" && "text-status-warning",
              log.level === "debug"   && "text-content-placeholder",
              !["error","warning","debug"].includes(log.level) && "text-content-muted",
            )}>
              {log.level.slice(0,4)}
            </span>
            <span className="text-content-secondary">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepArtifactBlock({ artifacts }: { artifacts: import("@/lib/api").MissionArtifact[] }) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1.5">
        <PackageIcon size={10} className="text-content-muted" />
        <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
          Artifacts ({artifacts.length})
        </span>
      </div>
      <div className="space-y-1">
        {artifacts.map((a) => (
          <div
            key={a.id}
            className="flex items-center gap-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-2.5 py-1.5"
          >
            <PackageIcon size={11} className="shrink-0 text-content-muted" />
            <span className="flex-1 truncate text-[11px] text-content-secondary">{a.name}</span>
            <span className="shrink-0 text-[10px] text-content-muted">{a.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Live elapsed timer
// ─────────────────────────────────────────────────────────────

function ElapsedTimer({ since }: { since: string }) {
  const [ms, setMs] = useState(durationMs(since));
  useEffect(() => {
    const t = setInterval(() => setMs(durationMs(since)), 1000);
    return () => clearInterval(t);
  }, [since]);
  return <span className="tabular-nums">{fmtDuration(ms)}</span>;
}

// ─────────────────────────────────────────────────────────────
// Mission detail
// ─────────────────────────────────────────────────────────────

function MissionDetailPanel({
  mission,
  onAction,
  actionLoading,
  workspaceId,
}: {
  mission:       MissionDetail;
  onAction:      (fn: () => Promise<Mission>) => Promise<void>;
  actionLoading: boolean;
  workspaceId:   string;
}) {
  const { done, total, pct } = calcProgress(mission.steps);
  const isLive = ACTIVE.has(mission.status);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* ── Sticky header ── */}
      <div className="shrink-0 border-b border-[var(--border-subtle)] bg-[var(--surface-base)] px-6 py-4">
        <div className="flex items-start gap-3 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <h1 className="text-sm font-semibold text-content-primary leading-snug">
                {mission.intent}
              </h1>
              <Badge variant={STATUS_BADGE[mission.status] ?? "default"} size="md">
                {STATUS_LABEL[mission.status] ?? mission.status}
              </Badge>
              {isLive && (
                <span className="flex items-center gap-1 text-[11px] text-accent">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse-dot" />
                  ao vivo
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 text-[11px] text-content-muted flex-wrap">
              <span className="flex items-center gap-1">
                <ZapIcon size={10} />
                {mission.trigger}
              </span>
              <span className="flex items-center gap-1">
                <ClockIcon size={10} />
                {fmt(mission.created_at)}
              </span>
              {isLive ? (
                <span className="flex items-center gap-1 text-accent">
                  <ActivityIcon size={10} />
                  <ElapsedTimer since={mission.created_at} />
                </span>
              ) : mission.completed_at ? (
                <span className="flex items-center gap-1">
                  <ActivityIcon size={10} />
                  {fmtDuration(durationMs(mission.created_at, mission.completed_at))}
                </span>
              ) : null}
            </div>
          </div>

          {/* Actions */}
          {!actionLoading ? (
            <div className="flex gap-2 flex-wrap shrink-0">
              {mission.status === "pending" && (
                <Button variant="secondary" size="sm"
                  onClick={() => onAction(() => api.planMission(workspaceId, mission.id))}>
                  <PlayIcon size={12} className="mr-1.5" /> Planejar
                </Button>
              )}
              {mission.status === "waiting_approval" && (
                <>
                  <Button variant="secondary" size="sm"
                    className="text-status-success border-emerald-900/40 hover:bg-emerald-950/40"
                    onClick={() => onAction(() => api.approveMission(workspaceId, mission.id))}>
                    <CheckIcon size={12} className="mr-1.5" /> Aprovar
                  </Button>
                  <Button variant="danger" size="sm"
                    onClick={() => onAction(() => api.rejectMission(workspaceId, mission.id))}>
                    <XIcon size={12} className="mr-1.5" /> Rejeitar
                  </Button>
                </>
              )}
              {mission.status === "ready" && (
                <Button variant="primary" size="sm"
                  onClick={() => onAction(() => api.runMission(workspaceId, mission.id))}>
                  <PlayIcon size={12} className="mr-1.5" /> Executar
                </Button>
              )}
              {mission.status === "failed" && (
                <Button variant="secondary" size="sm"
                  onClick={() => onAction(() => api.planMission(workspaceId, mission.id))}>
                  <RefreshCwIcon size={12} className="mr-1.5" /> Replanejar
                </Button>
              )}
              {CANCELLABLE.has(mission.status) && (
                <Button variant="danger" size="sm"
                  onClick={() => onAction(() => api.cancelMission(workspaceId, mission.id))}>
                  <XIcon size={12} className="mr-1.5" /> Cancelar
                </Button>
              )}
            </div>
          ) : (
            <Spinner size="sm" />
          )}
        </div>

        {/* Progress bar */}
        {total > 0 && (
          <div className="mt-3">
            <div className="mb-1 flex items-center justify-between text-[10px] text-content-muted">
              <span>{done} / {total} passos</span>
              <span>{pct}%</span>
            </div>
            <Progress
              value={pct}
              variant={mission.status === "failed" ? "error" : mission.status === "succeeded" ? "success" : "default"}
              size="xs"
              animated={isLive}
            />
          </div>
        )}
      </div>

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto px-6 py-5">

        {/* Execution pipeline */}
        {mission.steps.length > 0 && (
          <Section title="Pipeline de execução" icon={<ActivityIcon size={12} />}>
            <div className="mt-2">
              {mission.steps
                .slice()
                .sort((a, b) => a.order - b.order)
                .map((step, i, arr) => (
                  <StepBlock
                    key={step.id}
                    step={step}
                    isLast={i === arr.length - 1}
                    stepLogs={mission.logs.filter((l) => l.step_id === step.id)}
                    stepArtifacts={mission.artifacts.filter((a) => a.step_id === step.id)}
                  />
                ))}
            </div>
          </Section>
        )}

        {/* Artifacts not linked to a step */}
        {mission.artifacts.filter((a) => !a.step_id).length > 0 && (
          <Section title="Artifacts da missão" icon={<PackageIcon size={12} />}>
            <div className="mt-2 space-y-1.5">
              {mission.artifacts.filter((a) => !a.step_id).map((a) => (
                <div
                  key={a.id}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5",
                    "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
                  )}
                >
                  <PackageIcon size={13} className="shrink-0 text-content-muted" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-content-primary truncate">{a.name}</p>
                    <p className="text-[10px] text-content-muted">{a.type} · {a.mime}</p>
                  </div>
                  <span className="text-[10px] text-content-muted shrink-0">{fmt(a.created_at)}</span>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Global logs (not tied to a step) */}
        {mission.logs.filter((l) => !l.step_id).length > 0 && (
          <Section title="Logs gerais" icon={<FileTextIcon size={12} />}>
            <div className={cn(
              "mt-2 max-h-60 overflow-y-auto rounded-lg border border-[var(--border-subtle)]",
              "bg-[var(--surface-inset)] p-4 font-mono",
            )}>
              {mission.logs.filter((l) => !l.step_id).map((log) => (
                <div key={log.id} className="flex gap-3 text-[11px] leading-relaxed">
                  <span className={cn(
                    "shrink-0 w-12 font-mono",
                    log.level === "error"   && "text-status-error",
                    log.level === "warning" && "text-status-warning",
                    log.level === "debug"   && "text-content-placeholder",
                    !["error","warning","debug"].includes(log.level) && "text-content-muted",
                  )}>
                    [{log.level.slice(0,4)}]
                  </span>
                  <span className="text-content-secondary">{log.message}</span>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Approval notice */}
        {mission.status === "waiting_approval" && (
          <div className={cn(
            "mt-2 flex items-start gap-3 rounded-lg border border-status-warning/40",
            "bg-status-warning/5 p-4",
          )}>
            <AlertTriangleIcon size={14} className="shrink-0 text-status-warning mt-0.5" />
            <div>
              <p className="text-xs font-medium text-status-warning">Aguardando aprovação</p>
              <p className="mt-0.5 text-[11px] text-content-muted">
                Este plano requer aprovação antes de ser executado. Revise os passos acima e aprove ou rejeite.
              </p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {mission.steps.length === 0 && mission.logs.length === 0 && (
          <div className="flex h-40 items-center justify-center">
            <div className="text-center">
              <CircleDashedIcon size={24} className="mx-auto mb-2 text-content-muted" />
              <p className="text-xs text-content-muted">
                {mission.status === "pending"
                  ? "Missão aguarda planejamento"
                  : "Nenhum dado de execução ainda"}
              </p>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Section wrapper
// ─────────────────────────────────────────────────────────────

function Section({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-1.5 mb-0.5">
        {icon && <span className="text-content-muted">{icon}</span>}
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
          {title}
        </h2>
      </div>
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────

export function MissionsPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [missions,      setMissions]      = useState<Mission[]>([]);
  const [selected,      setSelected]      = useState<MissionDetail | null>(null);
  const [loading,       setLoading]       = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [filterTab,     setFilterTab]     = useState<FilterTab>("all");
  const [createOpen,    setCreateOpen]    = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    api.listMissions(workspace.id)
      .then(setMissions)
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  // Poll active mission
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (!selected || !workspace) return;
    if (!ACTIVE.has(selected.status)) return;

    pollRef.current = setInterval(async () => {
      const detail = await api.getMission(workspace.id, selected.id);
      setSelected(detail);
      setMissions((prev) => prev.map((m) => (m.id === detail.id ? detail : m)));
      if (!ACTIVE.has(detail.status)) {
        clearInterval(pollRef.current!);
        pollRef.current = null;
      }
    }, 3000);

    return () => { if (pollRef.current) clearInterval(pollRef.current); };
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

  async function handleCreate(intent: string, requiresApproval: boolean) {
    if (!workspace) return;
    const m = await api.createMission(workspace.id, intent, requiresApproval);
    setMissions((prev) => [m, ...prev]);
    const detail = await api.getMission(workspace.id, m.id);
    setSelected(detail);
  }

  // Filtered missions
  const filtered = missions.filter((m) => {
    if (filterTab === "active")  return ACTIVE.has(m.status) || m.status === "waiting_approval";
    if (filterTab === "pending") return m.status === "pending" || m.status === "ready";
    if (filterTab === "done")    return ["succeeded","failed","cancelled"].includes(m.status);
    return true;
  });

  const activeCount  = missions.filter((m) => ACTIVE.has(m.status)).length;

  if (wsLoading || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Sidebar ── */}
      <aside className={cn(
        "flex w-72 shrink-0 flex-col",
        "border-r border-[var(--border-subtle)] bg-[var(--surface-raised)]",
      )}>
        {/* Header */}
        <header className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
          <TargetIcon size={13} className="text-content-muted" />
          <span className="text-xs font-semibold text-content-primary">Missões</span>
          {activeCount > 0 && (
            <span className="flex h-4 items-center rounded-full bg-accent px-1.5 text-[10px] font-bold text-white tabular-nums">
              {activeCount}
            </span>
          )}
          <button
            onClick={() => setCreateOpen(true)}
            className="ml-auto flex h-6 w-6 items-center justify-center rounded-md text-content-muted hover:bg-[var(--surface-subtle)] hover:text-content-secondary transition-colors"
            title="Nova missão"
          >
            <PlusIcon size={14} />
          </button>
        </header>

        {/* Filter tabs */}
        <div className="flex border-b border-[var(--border-subtle)]">
          {([["all","Todas"],["active","Ativas"],["pending","Prontas"],["done","Concluídas"]] as [FilterTab, string][]).map(([tab, label]) => (
            <button
              key={tab}
              onClick={() => setFilterTab(tab)}
              className={cn(
                "flex-1 py-2 text-[10px] font-medium transition-colors",
                filterTab === tab
                  ? "text-accent border-b-2 border-accent"
                  : "text-content-muted hover:text-content-secondary",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-12">
              <FilterIcon size={16} className="text-content-muted" />
              <p className="text-xs text-content-muted text-center px-4">
                {missions.length === 0 ? "Nenhuma missão ainda." : "Nenhuma missão nesta categoria."}
              </p>
              {missions.length === 0 && (
                <button
                  onClick={() => setCreateOpen(true)}
                  className="mt-1 text-xs text-accent hover:underline"
                >
                  Criar primeira missão
                </button>
              )}
            </div>
          ) : (
            filtered.map((m) => (
              <MissionRow
                key={m.id}
                mission={m}
                active={selected?.id === m.id}
                onClick={() => selectMission(m.id)}
              />
            ))
          )}
        </div>
      </aside>

      {/* ── Detail ── */}
      <main className="flex-1 overflow-hidden bg-[var(--surface-base)]">
        {!selected ? (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-dim">
              <TargetIcon size={22} className="text-accent" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-content-secondary">Pipeline de Missões</p>
              <p className="mt-1 text-xs text-content-muted max-w-xs">
                Selecione uma missão para ver o pipeline de execução em tempo real.
              </p>
            </div>
            <button
              onClick={() => setCreateOpen(true)}
              className="mt-2 flex items-center gap-1.5 rounded-lg border border-[var(--border-default)] bg-[var(--surface-raised)] px-3 py-2 text-xs text-content-secondary hover:text-content-primary hover:border-accent transition-colors"
            >
              <PlusIcon size={12} />
              Nova missão
            </button>
          </div>
        ) : (
          <MissionDetailPanel
            mission={selected}
            onAction={doAction}
            actionLoading={actionLoading}
            workspaceId={workspace!.id}
          />
        )}
      </main>

      {/* Create dialog */}
      <CreateMissionDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
