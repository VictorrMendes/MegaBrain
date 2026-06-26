"use client";

import { useEffect, useState } from "react";
import { api, type Mission, type MissionDetail, type Workspace } from "@/lib/api";
import { cn } from "@/lib/cn";
import { TargetIcon, LoaderIcon, ChevronRightIcon, PlayIcon, CheckIcon, XIcon, RefreshCwIcon } from "lucide-react";

const STATUS_COLOR: Record<string, string> = {
  pending:          "text-neutral-400 bg-neutral-800",
  planning:         "text-blue-400 bg-blue-950",
  waiting_approval: "text-yellow-400 bg-yellow-950",
  ready:            "text-emerald-400 bg-emerald-950",
  running:          "text-blue-300 bg-blue-950 animate-pulse",
  paused:           "text-orange-400 bg-orange-950",
  retrying:         "text-orange-300 bg-orange-950",
  succeeded:        "text-emerald-400 bg-emerald-950",
  failed:           "text-red-400 bg-red-950",
  cancelled:        "text-neutral-500 bg-neutral-900",
};

const STATUS_LABEL: Record<string, string> = {
  pending:          "pendente",
  planning:         "planejando",
  waiting_approval: "aguardando aprovação",
  ready:            "pronto",
  running:          "executando",
  paused:           "pausado",
  retrying:         "repetindo",
  succeeded:        "concluído",
  failed:           "falhou",
  cancelled:        "cancelado",
};

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

export function MissionsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selected, setSelected] = useState<MissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        let wss = await api.listWorkspaces();
        if (wss.length === 0) {
          const ws = await api.createWorkspace("Personal");
          wss = [ws];
        }
        const ws = wss[0];
        setWorkspace(ws);
        const ms = await api.listMissions(ws.id);
        setMissions(ms);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function selectMission(id: string) {
    if (!workspace) return;
    const detail = await api.getMission(workspace.id, id);
    setSelected(detail);
  }

  async function action(fn: () => Promise<Mission>) {
    setActionLoading(true);
    try {
      const updated = await fn();
      setMissions((prev) => prev.map((m) => m.id === updated.id ? updated : m));
      if (selected?.id === updated.id) {
        const detail = await api.getMission(workspace!.id, updated.id);
        setSelected(detail);
      }
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoaderIcon size={20} className="animate-spin text-neutral-500" />
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* List */}
      <div className="flex w-80 shrink-0 flex-col border-r border-neutral-800">
        <header className="flex items-center gap-2 border-b border-neutral-800 px-4 py-3">
          <TargetIcon size={15} className="text-neutral-400" />
          <span className="text-sm font-medium text-neutral-300">Missões</span>
          <span className="ml-auto text-xs text-neutral-600">{missions.length}</span>
        </header>

        <div className="flex-1 overflow-y-auto">
          {missions.length === 0 ? (
            <p className="px-4 py-6 text-center text-xs text-neutral-600">
              Nenhuma missão ainda.
            </p>
          ) : (
            missions.map((m) => (
              <button
                key={m.id}
                onClick={() => selectMission(m.id)}
                className={cn(
                  "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors border-b border-neutral-800/50",
                  selected?.id === m.id
                    ? "bg-neutral-800"
                    : "hover:bg-neutral-800/50"
                )}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-neutral-200 truncate">{m.intent}</p>
                  <p className="mt-0.5 text-[10px] text-neutral-600">{formatDate(m.created_at)}</p>
                </div>
                <span className={cn("mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium", STATUS_COLOR[m.status])}>
                  {STATUS_LABEL[m.status] ?? m.status}
                </span>
                <ChevronRightIcon size={13} className="mt-0.5 shrink-0 text-neutral-600" />
              </button>
            ))
          )}
        </div>
      </div>

      {/* Detail */}
      <div className="flex-1 overflow-y-auto">
        {!selected ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-xs text-neutral-600">Selecione uma missão</p>
          </div>
        ) : (
          <div className="p-6 max-w-3xl">
            {/* Header */}
            <div className="mb-4 flex items-start gap-3">
              <div className="flex-1">
                <h1 className="text-sm font-semibold text-neutral-100">{selected.intent}</h1>
                <p className="mt-1 text-xs text-neutral-500">
                  Criado em {formatDate(selected.created_at)}
                  {selected.completed_at && ` · Concluído em ${formatDate(selected.completed_at)}`}
                </p>
              </div>
              <span className={cn("shrink-0 rounded px-2 py-1 text-xs font-medium", STATUS_COLOR[selected.status])}>
                {STATUS_LABEL[selected.status] ?? selected.status}
              </span>
            </div>

            {/* Actions */}
            {!actionLoading && (
              <div className="mb-5 flex gap-2 flex-wrap">
                {selected.status === "pending" && (
                  <ActionBtn icon={<PlayIcon size={12} />} label="Planejar"
                    onClick={() => action(() => api.planMission(workspace!.id, selected.id))} />
                )}
                {selected.status === "waiting_approval" && (
                  <>
                    <ActionBtn icon={<CheckIcon size={12} />} label="Aprovar" variant="green"
                      onClick={() => action(() => api.approveMission(workspace!.id, selected.id))} />
                    <ActionBtn icon={<XIcon size={12} />} label="Rejeitar" variant="red"
                      onClick={() => action(() => api.rejectMission(workspace!.id, selected.id))} />
                  </>
                )}
                {selected.status === "ready" && (
                  <ActionBtn icon={<PlayIcon size={12} />} label="Executar" variant="green"
                    onClick={() => action(() => api.runMission(workspace!.id, selected.id))} />
                )}
                {["pending","planning","waiting_approval","ready","running","paused"].includes(selected.status) && (
                  <ActionBtn icon={<XIcon size={12} />} label="Cancelar" variant="red"
                    onClick={() => action(() => api.cancelMission(workspace!.id, selected.id))} />
                )}
                {selected.status === "failed" && (
                  <ActionBtn icon={<RefreshCwIcon size={12} />} label="Replanejar"
                    onClick={() => action(() => api.planMission(workspace!.id, selected.id))} />
                )}
              </div>
            )}
            {actionLoading && (
              <div className="mb-5">
                <LoaderIcon size={16} className="animate-spin text-neutral-500" />
              </div>
            )}

            {/* Steps */}
            {selected.steps.length > 0 && (
              <Section title="Passos de execução">
                <div className="space-y-2">
                  {selected.steps.map((step) => (
                    <div key={step.id} className="flex items-start gap-3 rounded-lg border border-neutral-800 p-3">
                      <span className="mt-0.5 w-5 shrink-0 text-center text-xs text-neutral-600">{step.order}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-neutral-300 font-medium">{step.tool}</p>
                        <p className="text-[10px] text-neutral-600">{step.type}</p>
                      </div>
                      <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px]", STATUS_COLOR[step.status] ?? "text-neutral-500 bg-neutral-800")}>
                        {step.status}
                      </span>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Artifacts */}
            {selected.artifacts.length > 0 && (
              <Section title="Artifacts produzidos">
                <div className="space-y-2">
                  {selected.artifacts.map((a) => (
                    <div key={a.id} className="flex items-center gap-3 rounded-lg border border-neutral-800 p-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-neutral-200 truncate">{a.name}</p>
                        <p className="text-[10px] text-neutral-600">{a.type} · {a.mime}</p>
                      </div>
                      <p className="text-[10px] text-neutral-600 shrink-0">{formatDate(a.created_at)}</p>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Logs */}
            {selected.logs.length > 0 && (
              <Section title="Logs">
                <div className="space-y-1 rounded-lg border border-neutral-800 p-3 font-mono">
                  {selected.logs.map((log) => (
                    <div key={log.id} className="flex gap-2 text-[11px]">
                      <span className={cn("shrink-0", log.level === "error" ? "text-red-400" : "text-neutral-600")}>
                        [{log.level}]
                      </span>
                      <span className="text-neutral-400">{log.message}</span>
                    </div>
                  ))}
                </div>
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-widest text-neutral-500">{title}</h2>
      {children}
    </div>
  );
}

function ActionBtn({
  icon, label, onClick, variant = "default",
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  variant?: "default" | "green" | "red";
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
        variant === "green" && "bg-emerald-900 text-emerald-300 hover:bg-emerald-800",
        variant === "red" && "bg-red-950 text-red-400 hover:bg-red-900",
        variant === "default" && "bg-neutral-800 text-neutral-300 hover:bg-neutral-700",
      )}
    >
      {icon}
      {label}
    </button>
  );
}
