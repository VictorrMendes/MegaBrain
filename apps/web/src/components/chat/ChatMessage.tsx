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
    <div className="flex flex-col gap-4 py-3 pl-3 relative mb-2">
      {/* Connecting line */}
      <div className="absolute left-[15px] top-5 bottom-3 w-[2px] bg-accent/20 rounded-full" />
      
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-4 relative z-10 animate-fade-in-up" style={{ animationDelay: `${i * 0.1}s` }}>
          <div className="h-2 w-2 rounded-full bg-accent/40 shadow-[0_0_10px_rgba(var(--accent-rgb),0.3)] ring-4 ring-[var(--surface-base)]" />
          <span className="text-xs font-medium text-content-muted flex items-center gap-2">
            {stepIcon(s.step)}
            {stepLabel(s.step)}
          </span>
          {s.duration_ms != null && (
            <span className="text-[10px] text-content-muted opacity-40 ml-2">
              {s.duration_ms < 1000 ? `${Math.round(s.duration_ms)}ms` : `${(s.duration_ms / 1000).toFixed(1)}s`}
            </span>
          )}
        </div>
      ))}
      
      {pending && (
        <div className="flex items-center gap-4 relative z-10 animate-fade-in-up">
          <div className="relative flex items-center justify-center h-2 w-2 ring-4 ring-[var(--surface-base)]">
            <div className="absolute inset-0 rounded-full bg-accent opacity-75 animate-ping" />
            <div className="relative h-2 w-2 rounded-full bg-accent" />
          </div>
          <span className="text-xs font-semibold text-content-primary flex items-center gap-2 text-glow">
            {stepIcon(pending)}
            {stepLabel(pending)}
            <span className="animate-pulse">...</span>
          </span>
        </div>
      )}
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
// Transparency chip (Context Layer Accordion)
// ─────────────────────────────────────────────────────────────

const RISK_COLOR: Record<string, string> = {
  low:      "text-status-success",
  medium:   "text-status-warning",
  high:     "text-status-error",
  critical: "text-status-error",
};

function TransparencyAccordion({
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
    <details className="mt-4 group/accordion cursor-pointer">
      <summary className="list-none flex items-center gap-2 text-[11px] font-semibold tracking-wide text-content-muted hover:text-accent transition-colors select-none">
        <span className="group-open/accordion:rotate-90 transition-transform duration-300">
          ▶
        </span>
        <span className="uppercase tracking-widest text-[10px]">Context Layer & Debug</span>
        <span className="ml-2 px-1.5 py-0.5 rounded bg-[var(--surface-subtle)] text-[9px] text-content-secondary">
          {totalCtx} fontes • Risco: {data.risk}
        </span>
      </summary>
      
      <div className="mt-3 p-4 bg-[var(--surface-inset)] border border-[var(--border-subtle)] rounded-xl text-xs text-content-secondary grid grid-cols-2 gap-4 cursor-default animate-fade-in-up">
        
        {/* Memory & Knowledge */}
        <div className="space-y-2">
          <div className="font-semibold text-content-primary flex items-center gap-2">
            <BrainIcon size={12} className="text-accent" /> Memória e Conhecimento
          </div>
          <ul className="space-y-1 pl-5 list-disc marker:text-accent/50 text-[11px]">
            <li>{data.memory_used} memórias episódicas acionadas</li>
            <li>{data.knowledge_used} fatos de conhecimento extraídos</li>
            <li>{data.internet_sources} consultas web ativas</li>
          </ul>
        </div>
        
        {/* Metadados de Decisão */}
        <div className="space-y-2">
          <div className="font-semibold text-content-primary flex items-center gap-2">
            <ZapIcon size={12} className="text-accent" /> Avaliação Cognitiva
          </div>
          <ul className="space-y-1 pl-5 list-disc marker:text-accent/50 text-[11px]">
            <li>Confiança da resposta: <span className={confPct >= 80 ? "text-status-success" : "text-status-warning"}>{confPct}%</span></li>
            <li>Risco avaliado: <span className={riskCls}>{data.risk}</span></li>
            <li>Tempo de processamento: {data.estimated_time}ms</li>
          </ul>
        </div>
        
        {/* Botão de Trace Completo */}
        <div className="col-span-2 pt-2 border-t border-[var(--border-subtle)] flex justify-end">
          <button
            onClick={onShowTrace}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[10px] font-semibold text-content-primary hover:border-accent hover:text-accent transition-colors"
          >
            Inspecionar Trace Completo →
          </button>
        </div>
      </div>
    </details>
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
          <TransparencyAccordion
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
