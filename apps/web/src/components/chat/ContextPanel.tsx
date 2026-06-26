"use client";

import Link from "next/link";
import { BrainIcon, BookOpenIcon, FileTextIcon, XIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ContextUsed } from "./ChatMessage";

interface ContextPanelProps {
  context:  ContextUsed;
  onClose?: () => void;
}

export function ContextPanel({ context, onClose }: ContextPanelProps) {
  return (
    <aside
      className={cn(
        "flex w-60 shrink-0 flex-col",
        "border-l border-[var(--border-subtle)] bg-[var(--surface-raised)]",
        "animate-fade-in",
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
          Contexto utilizado
        </span>
        {onClose && (
          <button
            onClick={onClose}
            className="text-content-muted hover:text-content-secondary transition-colors"
          >
            <XIcon size={13} />
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-0 overflow-y-auto py-3">
        {context.memory > 0 && (
          <ContextSection
            icon={<BrainIcon size={13} />}
            label="Memória"
            count={context.memory}
            href="/memory"
            description={`${context.memory} registro${context.memory !== 1 ? "s" : ""} consultado${context.memory !== 1 ? "s" : ""}`}
          />
        )}

        {context.knowledge > 0 && (
          <ContextSection
            icon={<BookOpenIcon size={13} />}
            label="Conhecimento"
            count={context.knowledge}
            href="/knowledge"
            description={`${context.knowledge} fato${context.knowledge !== 1 ? "s" : ""} carregado${context.knowledge !== 1 ? "s" : ""}`}
          />
        )}

        {context.chunks > 0 && (
          <ContextSection
            icon={<FileTextIcon size={13} />}
            label="Documentos"
            count={context.chunks}
            href="/knowledge"
            description={`${context.chunks} trecho${context.chunks !== 1 ? "s" : ""} recuperado${context.chunks !== 1 ? "s" : ""}`}
          />
        )}

        {context.memory === 0 && context.knowledge === 0 && context.chunks === 0 && (
          <p className="px-4 text-xs text-content-muted">
            Nenhum contexto externo consultado.
          </p>
        )}
      </div>

      <div className="border-t border-[var(--border-subtle)] px-4 py-3">
        <p className="text-[11px] text-content-muted leading-relaxed">
          O PAIOS consulta automaticamente memórias e conhecimento relevantes a cada mensagem.
        </p>
      </div>
    </aside>
  );
}

function ContextSection({
  icon, label, count, href, description,
}: {
  icon:        React.ReactNode;
  label:       string;
  count:       number;
  href:        string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-start gap-3 px-4 py-3 hover:bg-[var(--surface-overlay)] transition-colors"
    >
      <span className="mt-0.5 text-content-muted group-hover:text-accent transition-colors">
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-content-secondary">{label}</span>
          <span
            className={cn(
              "flex h-4 items-center rounded px-1 text-[10px] font-medium",
              "bg-accent-dim text-accent",
            )}
          >
            {count}
          </span>
        </div>
        <p className="mt-0.5 text-[11px] text-content-muted">{description}</p>
      </div>
    </Link>
  );
}
