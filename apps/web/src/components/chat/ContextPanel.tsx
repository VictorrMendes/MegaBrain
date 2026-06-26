"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import { Separator } from "@/components/ui";
import {
  BookOpenIcon,
  BotIcon,
  BrainIcon,
  FileTextIcon,
  InfoIcon,
  PlugZapIcon,
  XIcon,
} from "lucide-react";
import type { ContextUsed } from "./ChatMessage";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export interface ContextPanelCapability {
  name:        string;
  description: string;
  enabled:     boolean;
}

interface ContextPanelProps {
  context:       ContextUsed;
  capabilities?: ContextPanelCapability[];
  onClose?:      () => void;
}

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function SectionHeader({ icon, label, count }: { icon: React.ReactNode; label: string; count?: number }) {
  return (
    <div className="flex items-center gap-1.5 px-4 pt-3 pb-1">
      <span className="text-content-muted">{icon}</span>
      <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted flex-1">
        {label}
      </span>
      {count !== undefined && count > 0 && (
        <span className="flex h-4 items-center rounded px-1.5 text-[10px] font-medium bg-accent-dim text-accent tabular-nums">
          {count}
        </span>
      )}
    </div>
  );
}

function ContextRow({ href, label, sublabel }: { href: string; label: string; sublabel: string }) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-0.5 px-4 py-2 hover:bg-[var(--surface-overlay)] transition-colors"
    >
      <span className="text-xs font-medium text-content-secondary group-hover:text-content-primary transition-colors">
        {label}
      </span>
      <span className="text-[11px] text-content-muted">{sublabel}</span>
    </Link>
  );
}

function CapabilityPill({ cap }: { cap: ContextPanelCapability }) {
  return (
    <div
      className={cn(
        "mx-4 flex items-center gap-1.5 rounded-md border px-2 py-1.5",
        cap.enabled
          ? "border-[var(--border-default)] bg-[var(--surface-raised)]"
          : "border-[var(--border-subtle)] bg-transparent opacity-40",
      )}
      title={cap.description}
    >
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", cap.enabled ? "bg-status-success" : "bg-content-muted")} />
      <span className="truncate text-[11px] text-content-secondary">{cap.name}</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// ContextPanel
// ─────────────────────────────────────────────────────────────

export function ContextPanel({ context, capabilities, onClose }: ContextPanelProps) {
  const total   = context.memory + context.knowledge + context.chunks;
  const hasCaps = capabilities && capabilities.length > 0;

  return (
    <aside
      className={cn(
        "flex w-64 shrink-0 flex-col",
        "border-l border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "animate-slide-in-right",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-2.5">
        <div className="flex items-center gap-1.5">
          <BotIcon size={12} className="text-accent" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-content-muted">
            Inteligência usada
          </span>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-content-muted hover:text-content-secondary transition-colors">
            <XIcon size={12} />
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col overflow-y-auto">

        {/* Summary */}
        {total > 0 ? (
          <div className="m-3 rounded-lg border border-accent-dim bg-accent-subtle p-3">
            <p className="text-xs font-medium text-accent">
              {total} fonte{total !== 1 ? "s" : ""} consultada{total !== 1 ? "s" : ""}
            </p>
            <p className="mt-0.5 text-[11px] text-content-muted leading-snug">
              Resposta enriquecida com memória, conhecimento e documentos relevantes.
            </p>
          </div>
        ) : (
          <div className="m-3 flex items-start gap-2 rounded-lg border border-[var(--border-subtle)] p-3">
            <InfoIcon size={12} className="mt-0.5 shrink-0 text-content-muted" />
            <p className="text-[11px] text-content-muted leading-snug">
              Nenhum contexto externo foi consultado nesta resposta.
            </p>
          </div>
        )}

        {/* Memory */}
        {context.memory > 0 && (
          <>
            <Separator />
            <SectionHeader icon={<BrainIcon size={11} />} label="Memória" count={context.memory} />
            <ContextRow
              href="/memory"
              label={`${context.memory} registro${context.memory !== 1 ? "s" : ""} consultado${context.memory !== 1 ? "s" : ""}`}
              sublabel="Experiências e contexto pessoal"
            />
          </>
        )}

        {/* Knowledge */}
        {context.knowledge > 0 && (
          <>
            <Separator />
            <SectionHeader icon={<BookOpenIcon size={11} />} label="Conhecimento" count={context.knowledge} />
            <ContextRow
              href="/knowledge"
              label={`${context.knowledge} fato${context.knowledge !== 1 ? "s" : ""} recuperado${context.knowledge !== 1 ? "s" : ""}`}
              sublabel="Fatos estruturados e informações"
            />
          </>
        )}

        {/* Documents */}
        {context.chunks > 0 && (
          <>
            <Separator />
            <SectionHeader icon={<FileTextIcon size={11} />} label="Documentos" count={context.chunks} />
            <ContextRow
              href="/knowledge"
              label={`${context.chunks} trecho${context.chunks !== 1 ? "s" : ""} recuperado${context.chunks !== 1 ? "s" : ""}`}
              sublabel="Fragmentos de documentos indexados"
            />
          </>
        )}

        {/* Capabilities */}
        {hasCaps && (
          <>
            <Separator />
            <SectionHeader icon={<PlugZapIcon size={11} />} label="Capacidades" />
            <div className="flex flex-col gap-1 py-2">
              {capabilities!.map((cap) => (
                <CapabilityPill key={cap.name} cap={cap} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-[var(--border-subtle)] px-4 py-2">
        <p className="text-[10px] text-content-muted leading-relaxed">
          Clique nos itens para explorar as fontes de contexto.
        </p>
      </div>
    </aside>
  );
}
