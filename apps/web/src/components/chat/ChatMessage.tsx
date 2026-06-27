"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import {
  BrainIcon,
  CheckIcon,
  CopyIcon,
  GlobeIcon,
  SkipForwardIcon,
  SparklesIcon,
  TriangleAlertIcon,
  XIcon,
  ZapIcon,
} from "lucide-react";
import type { OrchestratorDecision, OrchestratorTraceStep } from "@/lib/api";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export interface ContextUsed {
  memory:    number;
  knowledge: number;
  chunks:    number;
}

export type StreamPhase = "routing" | "searching" | "generating" | "learning" | null;

export interface LiveTraceStep {
  step:        string;
  engine:      string;
  status:      "completed" | "skipped" | "failed";
  output:      string | null;
  duration_ms: number | null;
}

export interface CognitiveData {
  confidence:       number;
  risk:             string;
  memory_used:      number;
  knowledge_used:   number;
  internet_sources: number;
  missions_created: string[];
  decision:         OrchestratorDecision | null;
  trace:            OrchestratorTraceStep[];
  thinking_steps:   string[];
  estimated_time:   number;
  learning_actions: number;
}

export interface ChatMessageData {
  id:            string;
  role:          "user" | "assistant";
  content:       string;
  streaming?:    boolean;
  streamPhase?:  StreamPhase;
  contextUsed?:  ContextUsed;
  liveSteps?:    LiveTraceStep[];
  cognitiveData?: CognitiveData;
}

// ─────────────────────────────────────────────────────────────
// Step label/icon map
// ─────────────────────────────────────────────────────────────

const STEP_META: Record<string, { label: string; icon: React.ReactNode }> = {
  build_context: {
    label: "Construindo contexto",
    icon: <BrainIcon size={9} />,
  },
  decide: {
    label: "Roteando requisição",
    icon: <ZapIcon size={9} />,
  },
  search: {
    label: "Pesquisando na internet",
    icon: <GlobeIcon size={9} />,
  },
  create_mission: {
    label: "Criando missão",
    icon: <SparklesIcon size={9} />,
  },
  generate: {
    label: "Gerando resposta",
    icon: <SparklesIcon size={9} />,
  },
  learn: {
    label: "Aprendendo",
    icon: <BrainIcon size={9} />,
  },
};

function stepLabel(step: string) {
  return STEP_META[step]?.label ?? step;
}
function stepIcon(step: string) {
  return STEP_META[step]?.icon ?? <ZapIcon size={9} />;
}

// ─────────────────────────────────────────────────────────────
// Live trace pipeline (shown during streaming)
// ─────────────────────────────────────────────────────────────

function LivePipeline({
  steps,
  phase,
}: {
  steps: LiveTraceStep[];
  phase: StreamPhase;
}) {
  const pending = pendingStep(phase);

  return (
    <div className="mb-3 overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)]">
      <div className="flex items-center gap-1.5 border-b border-[var(--border-subtle)] px-3 py-2">
        <ZapIcon size={9} className="text-accent" />
        <span className="text-[9px] font-semibold uppercase tracking-widest text-content-muted">
          Pipeline cognitivo
        </span>
        {phase && (
          <span className="ml-auto flex items-center gap-1 text-[10px] text-accent">
            <span className="h-1 w-1 rounded-full bg-accent animate-pulse" />
            Processando
          </span>
        )}
      </div>

      <div className="flex flex-col gap-0 divide-y divide-[var(--border-subtle)]">
        {steps.map((s) => (
          <StepRow key={s.step} step={s} />
        ))}
        {pending && (
          <PendingRow step={pending} />
        )}
      </div>
    </div>
  );
}

function StepRow({ step }: { step: LiveTraceStep }) {
  const isSkipped = step.status === "skipped";
  const isFailed  = step.status === "failed";

  return (
    <div
      className={cn(
        "flex items-center gap-2.5 px-3 py-2 animate-fade-in",
        isSkipped && "opacity-40",
      )}
    >
      <div
        className={cn(
          "flex h-4 w-4 shrink-0 items-center justify-center rounded-full",
          isFailed  && "bg-red-500/15 text-status-error",
          isSkipped && "bg-[var(--surface-subtle)] text-content-muted",
          !isFailed && !isSkipped && "bg-[var(--status-success-dim,rgba(34,197,94,0.12))] text-status-success",
        )}
      >
        {isFailed  ? <XIcon size={7} strokeWidth={3} /> :
         isSkipped ? <SkipForwardIcon size={7} /> :
                     <CheckIcon size={7} strokeWidth={3} />}
      </div>

      <span className="flex items-center gap-1.5 text-[11px] text-content-muted flex-1 min-w-0">
        <span className="shrink-0 text-content-muted opacity-60">
          {stepIcon(step.step)}
        </span>
        <span
          className={cn(
            "truncate",
            isSkipped ? "line-through" : "text-content-secondary",
          )}
        >
          {stepLabel(step.step)}
        </span>
        {step.output && !isSkipped && (
          <span className="shrink-0 text-[10px] text-content-muted opacity-70 truncate max-w-[120px]">
            — {step.output}
          </span>
        )}
      </span>

      {step.duration_ms != null && !isSkipped && (
        <span className="shrink-0 text-[10px] tabular-nums text-content-muted opacity-50">
          {step.duration_ms < 1000
            ? `${Math.round(step.duration_ms)}ms`
            : `${(step.duration_ms / 1000).toFixed(1)}s`}
        </span>
      )}
    </div>
  );
}

function PendingRow({ step }: { step: string }) {
  return (
    <div className="flex items-center gap-2.5 px-3 py-2">
      <div className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-accent-dim">
        <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
      </div>
      <span className="flex items-center gap-1.5 text-[11px] flex-1">
        <span className="shrink-0 text-accent opacity-70">
          {stepIcon(step)}
        </span>
        <span className="font-medium text-content-primary">{stepLabel(step)}</span>
        <span className="text-[10px] text-content-muted animate-pulse">…</span>
      </span>
    </div>
  );
}

function pendingStep(phase: StreamPhase): string | null {
  const map: Record<NonNullable<StreamPhase>, string> = {
    routing:    "decide",
    searching:  "search",
    generating: "generate",
    learning:   "learn",
  };
  return phase ? map[phase] : null;
}

// ─────────────────────────────────────────────────────────────
// Transparency chip (post-streaming)
// ─────────────────────────────────────────────────────────────

const RISK_COLOR: Record<string, string> = {
  low:      "text-status-success",
  medium:   "text-status-warning",
  high:     "text-status-error",
  critical: "text-status-error",
};

function TransparencyChip({
  data,
  onShowTrace,
}: {
  data: CognitiveData;
  onShowTrace: () => void;
}) {
  const confPct = Math.round(data.confidence * 100);
  const riskCls = RISK_COLOR[data.risk] ?? "text-content-muted";
  const totalCtx = data.memory_used + data.knowledge_used;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5">
      {/* Confidence */}
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-md px-2 py-1",
          "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
          "text-[10px] font-medium",
          confPct >= 80
            ? "text-status-success"
            : confPct >= 60
            ? "text-status-warning"
            : "text-status-error",
        )}
        title="Confiança da resposta"
      >
        <SparklesIcon size={9} />
        {confPct}%
      </span>

      {/* Risk */}
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-md px-2 py-1",
          "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
          "text-[10px] font-medium capitalize",
          riskCls,
        )}
        title="Nível de risco"
      >
        <TriangleAlertIcon size={9} />
        {data.risk}
      </span>

      {/* Context used */}
      {totalCtx > 0 && (
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-2 py-1",
            "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
            "text-[10px] font-medium text-accent",
          )}
          title={`${data.memory_used} memórias, ${data.knowledge_used} fatos`}
        >
          <BrainIcon size={9} />
          {totalCtx} ctx
        </span>
      )}

      {/* Internet */}
      {data.internet_sources > 0 && (
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-md px-2 py-1",
            "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
            "text-[10px] font-medium text-blue-400",
          )}
          title="Fontes da internet"
        >
          <GlobeIcon size={9} />
          {data.internet_sources} web
        </span>
      )}

      {/* Reasoning button */}
      <button
        onClick={onShowTrace}
        className={cn(
          "inline-flex items-center gap-1 rounded-md px-2 py-1",
          "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
          "text-[10px] text-content-muted hover:border-accent hover:text-accent transition-colors",
        )}
        title="Ver raciocínio completo"
      >
        <ZapIcon size={9} />
        Como raciocinou →
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Context badge (legacy, kept for non-cognitive messages)
// ─────────────────────────────────────────────────────────────

function ContextBadge({
  ctx,
  onClick,
}: {
  ctx: ContextUsed;
  onClick: () => void;
}) {
  const parts = [
    ctx.memory    > 0 ? `${ctx.memory} mem.`    : "",
    ctx.knowledge > 0 ? `${ctx.knowledge} fatos` : "",
    ctx.chunks    > 0 ? `${ctx.chunks} docs`     : "",
  ].filter(Boolean).join(" · ");
  if (!parts) return null;

  return (
    <button
      onClick={onClick}
      className={cn(
        "mt-2 inline-flex items-center gap-1.5 rounded-md px-2 py-1",
        "border border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "text-[11px] text-content-muted",
        "hover:border-accent hover:text-accent transition-colors duration-fast",
      )}
    >
      <BrainIcon size={10} />
      <span>{parts}</span>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Markdown renderer (no external deps)
// ─────────────────────────────────────────────────────────────

function parseInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**") && p.length > 4)
          return (
            <strong key={i} className="font-semibold text-content-primary">
              {p.slice(2, -2)}
            </strong>
          );
        if (p.startsWith("*") && p.endsWith("*") && p.length > 2)
          return <em key={i} className="italic">{p.slice(1, -1)}</em>;
        if (p.startsWith("`") && p.endsWith("`") && p.length > 2)
          return (
            <code
              key={i}
              className="rounded border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-1 font-mono text-[12px] text-accent"
            >
              {p.slice(1, -1)}
            </code>
          );
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

function renderMarkdown(text: string): React.ReactNode {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        code.push(lines[i]);
        i++;
      }
      nodes.push(
        <pre
          key={`cb${i}`}
          className="my-2 overflow-x-auto rounded-md border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-3 py-2.5"
        >
          {lang && (
            <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-content-muted">
              {lang}
            </div>
          )}
          <code className="font-mono text-[12px] text-content-secondary leading-relaxed">
            {code.join("\n")}
          </code>
        </pre>,
      );
      i++;
      continue;
    }

    const hm = line.match(/^(#{1,3})\s+(.+)/);
    if (hm) {
      const lvl = hm[1].length;
      nodes.push(
        <p
          key={`h${i}`}
          className={cn(
            "font-semibold text-content-primary",
            lvl === 1 ? "text-base mt-3 mb-1" : "text-sm mt-2 mb-0.5",
          )}
        >
          {parseInline(hm[2])}
        </p>,
      );
      i++;
      continue;
    }

    const bm = line.match(/^[-*]\s+(.+)/);
    if (bm) {
      nodes.push(
        <div key={`li${i}`} className="flex items-start gap-2 my-0.5">
          <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent opacity-60" />
          <span className="text-sm leading-relaxed">{parseInline(bm[1])}</span>
        </div>,
      );
      i++;
      continue;
    }

    const nm = line.match(/^(\d+)\.\s+(.+)/);
    if (nm) {
      nodes.push(
        <div key={`nl${i}`} className="flex items-start gap-2 my-0.5">
          <span className="mt-0.5 w-4 shrink-0 text-right font-mono text-[11px] text-accent opacity-60">
            {nm[1]}.
          </span>
          <span className="text-sm leading-relaxed">{parseInline(nm[2])}</span>
        </div>,
      );
      i++;
      continue;
    }

    if (line.trim() === "") {
      nodes.push(<div key={`sp${i}`} className="h-1.5" />);
      i++;
      continue;
    }

    nodes.push(
      <p key={`p${i}`} className="text-sm leading-relaxed">
        {parseInline(line)}
      </p>,
    );
    i++;
  }

  return <>{nodes}</>;
}

// ─────────────────────────────────────────────────────────────
// Copy button
// ─────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* ignore */ }
  }

  return (
    <button
      onClick={copy}
      className="flex h-6 w-6 items-center justify-center rounded text-content-muted hover:text-content-secondary hover:bg-[var(--surface-subtle)] transition-colors duration-fast"
      title="Copiar"
    >
      {copied
        ? <CheckIcon size={11} className="text-status-success" />
        : <CopyIcon size={11} />}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// ChatMessage
// ─────────────────────────────────────────────────────────────

interface ChatMessageProps {
  message:           ChatMessageData;
  onContextClick?:   () => void;
  onOpenContext?:    () => void;
  onShowReasoning?:  () => void;
}

export function ChatMessage({
  message,
  onContextClick,
  onOpenContext,
  onShowReasoning,
}: ChatMessageProps) {
  const {
    role,
    content,
    streaming,
    streamPhase,
    contextUsed,
    liveSteps,
    cognitiveData,
  } = message;

  const openCtx = onOpenContext ?? onContextClick ?? (() => {});

  if (role === "user") {
    return (
      <div className="flex justify-end px-4">
        <div
          className={cn(
            "max-w-[80%] rounded-xl rounded-br-sm px-4 py-2.5",
            "border border-[var(--border-default)] bg-[var(--surface-subtle)]",
            "text-sm text-content-primary leading-relaxed whitespace-pre-wrap break-words",
          )}
        >
          {content}
        </div>
      </div>
    );
  }

  const hasCognitive = Boolean(liveSteps && liveSteps.length > 0);
  const showLivePipeline = Boolean(streaming && hasCognitive);
  const showText         = content.length > 0;
  const showBadge        = !streaming && contextUsed &&
    (contextUsed.memory + contextUsed.knowledge + contextUsed.chunks > 0) &&
    !cognitiveData;
  const showTransparency = !streaming && Boolean(cognitiveData);

  return (
    <div className="group flex gap-3 px-4">
      {/* Avatar */}
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-dim">
        <SparklesIcon size={11} className="text-accent" />
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0">
        {/* Live cognitive pipeline (while streaming) */}
        {showLivePipeline && !showText && (
          <LivePipeline
            steps={liveSteps!}
            phase={streamPhase ?? null}
          />
        )}

        {/* Writing pulse (once text starts arriving) */}
        {streaming && showText && streamPhase === "generating" && (
          <div className="mb-2 flex items-center gap-1.5">
            <span className="flex gap-0.5">
              {[0, 1, 2].map((j) => (
                <span
                  key={j}
                  className="h-1 w-1 rounded-full bg-accent"
                  style={{
                    animation: "pulse-dot 1.4s ease-in-out infinite",
                    animationDelay: `${j * 0.18}s`,
                  }}
                />
              ))}
            </span>
            <span className="text-[11px] text-content-muted">Gerando…</span>
          </div>
        )}

        {/* Text */}
        {showText && (
          <div className="prose-cognitive text-content-primary">
            {renderMarkdown(content)}
            {streaming && streamPhase === "generating" && (
              <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-blink rounded-sm bg-accent align-text-bottom" />
            )}
          </div>
        )}

        {/* Legacy context badge (non-cognitive messages) */}
        {showBadge && contextUsed && (
          <ContextBadge ctx={contextUsed} onClick={openCtx} />
        )}

        {/* Transparency chip (cognitive messages, post-stream) */}
        {showTransparency && cognitiveData && (
          <TransparencyChip
            data={cognitiveData}
            onShowTrace={onShowReasoning ?? openCtx}
          />
        )}

        {/* Copy button */}
        {!streaming && showText && (
          <div className="mt-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-fast">
            <CopyButton text={content} />
            <span className="text-[10px] text-content-muted select-none">
              Copiar
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
