"use client";

import { cn } from "@/lib/cn";
import {
  BrainIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  GlobeIcon,
  SkipForwardIcon,
  SparklesIcon,
  TriangleAlertIcon,
  XIcon,
  ZapIcon,
} from "lucide-react";
import { useState } from "react";
import type { CognitiveData } from "./ChatMessage";

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

const STEP_LABELS: Record<string, string> = {
  build_context:  "Construção de contexto",
  decide:         "Roteamento cognitivo",
  search:         "Pesquisa na internet",
  create_mission: "Criação de missão",
  generate:       "Geração de resposta",
  learn:          "Aprendizado",
};

const STEP_DESC: Record<string, string> = {
  build_context:  "Memórias, fatos e documentos relevantes foram recuperados para enriquecer o contexto.",
  decide:         "O DecisionEngine analisou a mensagem e decidiu quais engines ativar.",
  search:         "O SearchEngine buscou informações atualizadas na internet.",
  create_mission: "O MissionEngine criou uma missão autônoma para executar a tarefa.",
  generate:       "O LLMProvider gerou a resposta final com o contexto enriquecido.",
  learn:          "O LearningEngine decidiu o que vale persistir desta troca.",
};

const RISK_COLOR: Record<string, string> = {
  low:      "text-status-success border-status-success/20 bg-[rgba(34,197,94,0.07)]",
  medium:   "text-status-warning border-status-warning/20 bg-[rgba(245,158,11,0.07)]",
  high:     "text-status-error border-status-error/20 bg-[rgba(239,68,68,0.07)]",
  critical: "text-status-error border-status-error/20 bg-[rgba(239,68,68,0.1)]",
};

const RISK_LABEL: Record<string, string> = {
  low:      "Baixo",
  medium:   "Médio",
  high:     "Alto",
  critical: "Crítico",
};

function fmt(ms: number | null): string {
  if (ms == null) return "—";
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

// ─────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1.5 px-4 pt-3 pb-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
        {children}
      </span>
    </div>
  );
}

function MetricRow({
  label,
  value,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-1.5">
      <span className="text-[11px] text-content-muted">{label}</span>
      <span
        className={cn(
          "text-[11px] font-medium tabular-nums",
          accent ? "text-accent" : "text-content-secondary",
        )}
      >
        {value}
      </span>
    </div>
  );
}

interface TraceRowProps {
  step: {
    step: string;
    engine: string;
    status: string;
    output_summary: string | null;
    duration_ms: number | null;
  };
}

function TraceRow({ step }: TraceRowProps) {
  const [open, setOpen] = useState(false);
  const isSkipped = step.status === "skipped";
  const isFailed  = step.status === "failed";
  const hasDetail = Boolean(step.output_summary) || Boolean(STEP_DESC[step.step]);

  return (
    <div
      className={cn(
        "border-b border-[var(--border-subtle)] last:border-0",
        isSkipped && "opacity-40",
      )}
    >
      <button
        className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left hover:bg-[var(--surface-overlay)] transition-colors"
        onClick={() => hasDetail && setOpen((p) => !p)}
        disabled={!hasDetail}
      >
        {/* Status dot */}
        <div
          className={cn(
            "flex h-4 w-4 shrink-0 items-center justify-center rounded-full",
            isFailed  && "bg-red-500/15 text-status-error",
            isSkipped && "bg-[var(--surface-subtle)] text-content-muted",
            !isFailed && !isSkipped &&
              "bg-[rgba(34,197,94,0.12)] text-status-success",
          )}
        >
          {isFailed  ? <XIcon size={7} strokeWidth={3} /> :
           isSkipped ? <SkipForwardIcon size={7} /> :
                       <CheckIcon size={7} strokeWidth={3} />}
        </div>

        {/* Label */}
        <div className="flex-1 min-w-0">
          <p
            className={cn(
              "text-[12px]",
              isSkipped
                ? "line-through text-content-muted"
                : "font-medium text-content-primary",
            )}
          >
            {STEP_LABELS[step.step] ?? step.step}
          </p>
          <p className="text-[10px] text-content-muted">{step.engine}</p>
        </div>

        {/* Duration */}
        {!isSkipped && step.duration_ms != null && (
          <span className="shrink-0 text-[11px] tabular-nums text-content-muted">
            {fmt(step.duration_ms)}
          </span>
        )}

        {/* Expand arrow */}
        {hasDetail && !isSkipped && (
          <span className="shrink-0 text-content-muted">
            {open
              ? <ChevronDownIcon size={12} />
              : <ChevronRightIcon size={12} />}
          </span>
        )}
      </button>

      {/* Expandable detail */}
      {open && (
        <div className="px-4 pb-3 pt-0 animate-fade-in">
          <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--surface-inset)] p-3">
            {step.output_summary && (
              <p className="mb-1.5 text-[11px] font-medium text-accent">
                {step.output_summary}
              </p>
            )}
            {STEP_DESC[step.step] && (
              <p className="text-[11px] text-content-muted leading-relaxed">
                {STEP_DESC[step.step]}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// ReasoningPanel
// ─────────────────────────────────────────────────────────────

interface ReasoningPanelProps {
  data:     CognitiveData;
  onClose?: () => void;
}

export function ReasoningPanel({ data, onClose }: ReasoningPanelProps) {
  const confPct  = Math.round(data.confidence * 100);
  const riskCls  = RISK_COLOR[data.risk] ?? "text-content-muted";
  const totalCtx = data.memory_used + data.knowledge_used;
  const totalMs  = data.trace.reduce((s, n) => s + (n.duration_ms ?? 0), 0);

  return (
    <aside
      className={cn(
        "flex w-72 shrink-0 flex-col md:h-full",
        "border-l border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "animate-slide-in-right",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-2.5">
        <div className="flex items-center gap-1.5">
          <ZapIcon size={12} className="text-accent" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
            Raciocínio
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-content-muted hover:text-content-secondary transition-colors"
          >
            <XIcon size={12} />
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col overflow-y-auto">

        {/* Summary card */}
        <div className="m-3 rounded-lg border border-accent-dim bg-accent-subtle p-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-accent">
              {confPct}% de confiança
            </p>
            <span
              className={cn(
                "rounded-md border px-2 py-0.5 text-[10px] font-medium capitalize",
                riskCls,
              )}
            >
              Risco {RISK_LABEL[data.risk] ?? data.risk}
            </span>
          </div>
          {data.decision?.reason && (
            <p className="mt-1.5 text-[11px] text-content-muted leading-snug">
              {data.decision.reason}
            </p>
          )}
        </div>

        {/* Metrics */}
        <SectionTitle>Métricas</SectionTitle>
        <div className="divide-y divide-[var(--border-subtle)] border-y border-[var(--border-subtle)]">
          <MetricRow label="Tempo total" value={fmt(totalMs)} />
          <MetricRow
            label="Contexto usado"
            value={totalCtx > 0 ? `${totalCtx} itens` : "—"}
            accent={totalCtx > 0}
          />
          {data.memory_used > 0 && (
            <MetricRow
              label="Memórias"
              value={
                <span className="flex items-center gap-1">
                  <BrainIcon size={9} />
                  {data.memory_used}
                </span>
              }
              accent
            />
          )}
          {data.knowledge_used > 0 && (
            <MetricRow
              label="Fatos"
              value={
                <span className="flex items-center gap-1">
                  <SparklesIcon size={9} />
                  {data.knowledge_used}
                </span>
              }
              accent
            />
          )}
          {data.internet_sources > 0 && (
            <MetricRow
              label="Fontes web"
              value={
                <span className="flex items-center gap-1 text-blue-400">
                  <GlobeIcon size={9} />
                  {data.internet_sources}
                </span>
              }
            />
          )}
          {data.learning_actions > 0 && (
            <MetricRow
              label="Aprendizados"
              value={`${data.learning_actions} ações`}
              accent
            />
          )}
          {data.missions_created.length > 0 && (
            <MetricRow
              label="Missões criadas"
              value={data.missions_created.length}
              accent
            />
          )}
        </div>

        {/* Decision flags */}
        {data.decision && (
          <>
            <SectionTitle>Decisões</SectionTitle>
            <div className="flex flex-wrap gap-1.5 px-4 pb-3">
              {([
                ["need_search",      "Pesquisa web",  <GlobeIcon size={9} key="s" />],
                ["need_mission",     "Missão",        <ZapIcon size={9} key="m" />],
                ["need_memory",      "Memória",       <BrainIcon size={9} key="mem" />],
                ["need_learning",    "Aprendizado",   <SparklesIcon size={9} key="l" />],
                ["need_confirmation","Confirmação",   <TriangleAlertIcon size={9} key="c" />],
              ] as [keyof typeof data.decision, string, React.ReactNode][]).map(
                ([key, label, icon]) => {
                  const active = Boolean(data.decision![key]);
                  return (
                    <span
                      key={key}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px]",
                        active
                          ? "border-accent/30 bg-accent-dim text-accent"
                          : "border-[var(--border-subtle)] text-content-muted opacity-40",
                      )}
                    >
                      {icon}
                      {label}
                    </span>
                  );
                },
              )}
            </div>
          </>
        )}

        {/* Trace steps */}
        {data.trace.length > 0 && (
          <>
            <SectionTitle>Passos do pipeline</SectionTitle>
            <div className="border-t border-[var(--border-subtle)]">
              {data.trace.map((step) => (
                <TraceRow key={step.id} step={step} />
              ))}
            </div>
          </>
        )}

        {/* Thinking steps */}
        {data.thinking_steps.length > 0 && (
          <>
            <SectionTitle>Pensamentos</SectionTitle>
            <div className="mx-3 mb-3 flex flex-col gap-1.5">
              {data.thinking_steps.map((t, i) => (
                <div
                  key={i}
                  className="rounded-md border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-3 py-2 text-[11px] text-content-muted leading-relaxed"
                >
                  {t}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-[var(--border-subtle)] px-4 py-2">
        <p className="text-[10px] text-content-muted leading-relaxed">
          Rastreamento completo de como Khonshu processou esta mensagem.
        </p>
      </div>
    </aside>
  );
}
