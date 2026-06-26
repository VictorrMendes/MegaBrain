"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import {
  BrainIcon,
  CheckIcon,
  CopyIcon,
  CpuIcon,
  SearchIcon,
  SparklesIcon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export interface ContextUsed {
  memory:    number;
  knowledge: number;
  chunks:    number;
}

export type StreamPhase = "thinking" | "reading" | "writing" | null;

export interface ChatMessageData {
  id:           string;
  role:         "user" | "assistant";
  content:      string;
  streaming?:   boolean;
  streamPhase?: StreamPhase;
  contextUsed?: ContextUsed;
}

// ─────────────────────────────────────────────────────────────
// Pipeline visual
// ─────────────────────────────────────────────────────────────

type StepStatus = "idle" | "running" | "done";

function stepStatus(stepId: StreamPhase, current: StreamPhase): StepStatus {
  if (!current) return "done";
  const order: StreamPhase[] = ["thinking", "reading", "writing"];
  const c = order.indexOf(current);
  const s = order.indexOf(stepId);
  if (s < c)  return "done";
  if (s === c) return "running";
  return "idle";
}

function ctxLabel(ctx?: ContextUsed): string | undefined {
  if (!ctx) return undefined;
  return [
    ctx.memory    > 0 ? `${ctx.memory} mem.`    : "",
    ctx.knowledge > 0 ? `${ctx.knowledge} fatos` : "",
    ctx.chunks    > 0 ? `${ctx.chunks} docs`     : "",
  ].filter(Boolean).join(" · ") || undefined;
}

function StreamingPipeline({ phase, ctx }: { phase: StreamPhase; ctx?: ContextUsed }) {
  const steps = [
    { id: "thinking" as StreamPhase, label: "Processando",     icon: <CpuIcon size={10} /> },
    { id: "reading"  as StreamPhase, label: "Lendo contexto",  icon: <SearchIcon size={10} />, meta: ctxLabel(ctx) },
    { id: "writing"  as StreamPhase, label: "Gerando resposta",icon: <SparklesIcon size={10} /> },
  ];

  return (
    <div className="mb-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-3 py-2.5">
      <div className="mb-2 flex items-center gap-1.5">
        <ZapIcon size={9} className="text-accent" />
        <span className="text-[9px] font-semibold uppercase tracking-widest text-content-muted">
          Pipeline cognitivo
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        {steps.map((step) => {
          const st = stepStatus(step.id, phase);
          return (
            <div key={step.id as string} className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full",
                  st === "done"    && "bg-[var(--status-success-dim)] text-status-success",
                  st === "running" && "bg-accent-dim text-accent",
                  st === "idle"    && "bg-[var(--surface-subtle)] text-content-muted",
                )}
              >
                {st === "done"    ? <CheckIcon size={7} strokeWidth={3} /> :
                 st === "running" ? <span className="h-1 w-1 rounded-full bg-accent animate-pulse" /> :
                                   <span className="h-1 w-1 rounded-full bg-content-muted opacity-30" />}
              </div>

              <span
                className={cn(
                  "text-[11px] leading-none flex-1",
                  st === "done"    && "text-content-muted line-through decoration-[var(--border-default)]",
                  st === "running" && "font-medium text-content-primary",
                  st === "idle"    && "text-content-muted opacity-40",
                )}
              >
                {step.label}
              </span>

              {st !== "idle" && step.meta && (
                <span className="text-[10px] font-medium text-accent tabular-nums">
                  {step.meta}
                </span>
              )}
              {st === "running" && !step.meta && (
                <span className="text-[10px] text-content-muted animate-pulse">…</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Context badge (post-streaming)
// ─────────────────────────────────────────────────────────────

function ContextBadge({ ctx, onClick }: { ctx: ContextUsed; onClick: () => void }) {
  const label = ctxLabel(ctx);
  if (!label) return null;

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
      <span>{label}</span>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Inline markdown renderer (no external deps)
// ─────────────────────────────────────────────────────────────

function parseInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith("**") && p.endsWith("**") && p.length > 4)
          return <strong key={i} className="font-semibold text-content-primary">{p.slice(2, -2)}</strong>;
        if (p.startsWith("*") && p.endsWith("*") && p.length > 2)
          return <em key={i} className="italic">{p.slice(1, -1)}</em>;
        if (p.startsWith("`") && p.endsWith("`") && p.length > 2)
          return (
            <code key={i} className="rounded border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-1 font-mono text-[12px] text-accent">
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
      while (i < lines.length && !lines[i].startsWith("```")) { code.push(lines[i]); i++; }
      nodes.push(
        <pre key={`cb${i}`} className="my-2 overflow-x-auto rounded-md border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-3 py-2.5">
          {lang && <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-content-muted">{lang}</div>}
          <code className="font-mono text-[12px] text-content-secondary leading-relaxed">{code.join("\n")}</code>
        </pre>
      );
      i++;
      continue;
    }

    const hm = line.match(/^(#{1,3})\s+(.+)/);
    if (hm) {
      const lvl = hm[1].length;
      nodes.push(
        <p key={`h${i}`} className={cn("font-semibold text-content-primary", lvl === 1 ? "text-base mt-3 mb-1" : "text-sm mt-2 mb-0.5")}>
          {parseInline(hm[2])}
        </p>
      );
      i++; continue;
    }

    const bm = line.match(/^[-*]\s+(.+)/);
    if (bm) {
      nodes.push(
        <div key={`li${i}`} className="flex items-start gap-2 my-0.5">
          <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent opacity-60" />
          <span className="text-sm leading-relaxed">{parseInline(bm[1])}</span>
        </div>
      );
      i++; continue;
    }

    const nm = line.match(/^(\d+)\.\s+(.+)/);
    if (nm) {
      nodes.push(
        <div key={`nl${i}`} className="flex items-start gap-2 my-0.5">
          <span className="mt-0.5 w-4 shrink-0 text-right font-mono text-[11px] text-accent opacity-60">{nm[1]}.</span>
          <span className="text-sm leading-relaxed">{parseInline(nm[2])}</span>
        </div>
      );
      i++; continue;
    }

    if (line.trim() === "") { nodes.push(<div key={`sp${i}`} className="h-1.5" />); i++; continue; }

    nodes.push(
      <p key={`p${i}`} className="text-sm leading-relaxed">{parseInline(line)}</p>
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
  message:         ChatMessageData;
  onContextClick?: () => void;
  onOpenContext?:  () => void;
}

export function ChatMessage({ message, onContextClick, onOpenContext }: ChatMessageProps) {
  const { role, content, streaming, streamPhase, contextUsed } = message;
  const openCtx = onOpenContext ?? onContextClick ?? (() => {});

  if (role === "user") {
    return (
      <div className="flex justify-end px-4">
        <div className={cn(
          "max-w-[80%] rounded-xl rounded-br-sm px-4 py-2.5",
          "border border-[var(--border-default)] bg-[var(--surface-subtle)]",
          "text-sm text-content-primary leading-relaxed whitespace-pre-wrap break-words",
        )}>
          {content}
        </div>
      </div>
    );
  }

  const showPipeline  = Boolean(streaming && streamPhase);
  const showText      = content.length > 0;
  const showBadge     = !streaming && contextUsed &&
    (contextUsed.memory + contextUsed.knowledge + contextUsed.chunks > 0);

  return (
    <div className="group flex gap-3 px-4">
      {/* Avatar */}
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-dim">
        <SparklesIcon size={11} className="text-accent" />
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0">
        {/* Pipeline — shown when streaming, before text */}
        {showPipeline && !showText && (
          <StreamingPipeline phase={streamPhase!} ctx={contextUsed} />
        )}

        {/* Writing pulse indicator (once text starts) */}
        {showPipeline && showText && streamPhase === "writing" && (
          <div className="mb-2 flex items-center gap-1.5">
            <span className="flex gap-0.5">
              {[0, 1, 2].map((j) => (
                <span
                  key={j}
                  className="h-1 w-1 rounded-full bg-accent"
                  style={{ animation: "pulse-dot 1.4s ease-in-out infinite", animationDelay: `${j * 0.18}s` }}
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
            {streaming && streamPhase === "writing" && (
              <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-blink rounded-sm bg-accent align-text-bottom" />
            )}
          </div>
        )}

        {/* Context badge */}
        {showBadge && contextUsed && (
          <ContextBadge ctx={contextUsed} onClick={openCtx} />
        )}

        {/* Copy button (hover) */}
        {!streaming && showText && (
          <div className="mt-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-fast">
            <CopyButton text={content} />
            <span className="text-[10px] text-content-muted select-none">Copiar</span>
          </div>
        )}
      </div>
    </div>
  );
}
