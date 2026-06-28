"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import { Separator } from "@/components/ui";
import {
  BookOpenIcon,
  BotIcon,
  BrainIcon,
  FileTextIcon,
  GlobeIcon,
  InfoIcon,
  RocketIcon,
  XIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export interface ContextPanelData {
  memory_used:      number;
  knowledge_used:   number;
  internet_sources: number;
  missions_created: string[];
  chunks?:          number;
}

interface ContextPanelProps {
  data:     ContextPanelData;
  onClose?: () => void;
}

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function SectionHeader({
  icon,
  label,
  count,
}: {
  icon: React.ReactNode;
  label: string;
  count?: number;
}) {
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

function ContextRow({
  href,
  label,
  sublabel,
}: {
  href: string;
  label: string;
  sublabel: string;
}) {
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

// ─────────────────────────────────────────────────────────────
// ContextPanel
// ─────────────────────────────────────────────────────────────

export function ContextPanel({ data, onClose }: ContextPanelProps) {
  const total = data.memory_used + data.knowledge_used +
    (data.chunks ?? 0) + data.internet_sources;

  return (
    <aside
      className={cn(
        "flex w-64 shrink-0 flex-col md:h-full",
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

        {/* Summary */}
        {total > 0 ? (
          <div className="m-3 rounded-lg border border-accent-dim bg-accent-subtle p-3">
            <p className="text-xs font-medium text-accent">
              {total} fonte{total !== 1 ? "s" : ""} consultada{total !== 1 ? "s" : ""}
            </p>
            <p className="mt-0.5 text-[11px] text-content-muted leading-snug">
              Resposta enriquecida com memória, conhecimento e informações relevantes.
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
        {data.memory_used > 0 && (
          <>
            <Separator />
            <SectionHeader
              icon={<BrainIcon size={11} />}
              label="Memória"
              count={data.memory_used}
            />
            <ContextRow
              href="/memory"
              label={`${data.memory_used} registro${data.memory_used !== 1 ? "s" : ""} consultado${data.memory_used !== 1 ? "s" : ""}`}
              sublabel="Experiências e contexto pessoal"
            />
          </>
        )}

        {/* Knowledge */}
        {data.knowledge_used > 0 && (
          <>
            <Separator />
            <SectionHeader
              icon={<BookOpenIcon size={11} />}
              label="Conhecimento"
              count={data.knowledge_used}
            />
            <ContextRow
              href="/knowledge"
              label={`${data.knowledge_used} fato${data.knowledge_used !== 1 ? "s" : ""} recuperado${data.knowledge_used !== 1 ? "s" : ""}`}
              sublabel="Fatos estruturados e informações"
            />
          </>
        )}

        {/* Documents */}
        {(data.chunks ?? 0) > 0 && (
          <>
            <Separator />
            <SectionHeader
              icon={<FileTextIcon size={11} />}
              label="Documentos"
              count={data.chunks}
            />
            <ContextRow
              href="/knowledge"
              label={`${data.chunks} trecho${data.chunks !== 1 ? "s" : ""} recuperado${data.chunks !== 1 ? "s" : ""}`}
              sublabel="Fragmentos de documentos indexados"
            />
          </>
        )}

        {/* Internet */}
        {data.internet_sources > 0 && (
          <>
            <Separator />
            <SectionHeader
              icon={<GlobeIcon size={11} />}
              label="Internet"
              count={data.internet_sources}
            />
            <ContextRow
              href="/knowledge"
              label={`${data.internet_sources} resultado${data.internet_sources !== 1 ? "s" : ""} encontrado${data.internet_sources !== 1 ? "s" : ""}`}
              sublabel="Pesquisa em tempo real na web"
            />
          </>
        )}

        {/* Missions */}
        {data.missions_created.length > 0 && (
          <>
            <Separator />
            <SectionHeader
              icon={<RocketIcon size={11} />}
              label="Missões criadas"
              count={data.missions_created.length}
            />
            {data.missions_created.map((id) => (
              <ContextRow
                key={id}
                href="/missions"
                label={`Missão ${id.slice(0, 8)}…`}
                sublabel="Tarefa autônoma criada por esta requisição"
              />
            ))}
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
