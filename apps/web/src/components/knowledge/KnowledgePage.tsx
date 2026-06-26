"use client";

import { useEffect, useState } from "react";
import { api, type Fact, type Observation, type Workspace } from "@/lib/api";
import { LoaderIcon, BookOpenIcon, LightbulbIcon, DatabaseIcon } from "lucide-react";
import { cn } from "@/lib/cn";

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-[10px] font-medium",
        pct >= 80 ? "bg-emerald-950 text-emerald-400" :
        pct >= 50 ? "bg-yellow-950 text-yellow-400" :
        "bg-red-950 text-red-400"
      )}
    >
      {pct}%
    </span>
  );
}

export function KnowledgePage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"facts" | "observations">("facts");

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
        const [fs, obs] = await Promise.all([
          api.listFacts(ws.id),
          api.listObservations(ws.id),
        ]);
        setFacts(fs);
        setObservations(obs);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoaderIcon size={20} className="animate-spin text-neutral-500" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-4 flex items-center gap-2">
          <BookOpenIcon size={15} className="text-neutral-400" />
          <h1 className="text-sm font-semibold text-neutral-300">Base de Conhecimento</h1>
        </div>

        {/* Tabs */}
        <div className="mb-5 flex gap-1 rounded-lg border border-neutral-800 p-1 bg-neutral-900 w-fit">
          <TabBtn active={tab === "facts"} onClick={() => setTab("facts")} icon={<DatabaseIcon size={12} />} label={`Fatos (${facts.length})`} />
          <TabBtn active={tab === "observations"} onClick={() => setTab("observations")} icon={<LightbulbIcon size={12} />} label={`Observações (${observations.length})`} />
        </div>

        {tab === "facts" && (
          <div>
            {facts.length === 0 ? (
              <p className="text-center text-xs text-neutral-600 py-10">Nenhum fato registrado ainda.</p>
            ) : (
              <div className="space-y-2">
                {facts.map((f) => (
                  <div key={f.id} className="rounded-lg border border-neutral-800 p-3">
                    <p className="text-xs text-neutral-200">{f.statement}</p>
                    <div className="mt-2 flex items-center gap-2 text-[10px] text-neutral-600 flex-wrap">
                      <ConfidencePill value={f.confidence} />
                      <span>fonte: {f.source_type}</span>
                      {f.entity_id && <span>entidade: {f.entity_id}</span>}
                      <span className="ml-auto">{formatDate(f.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "observations" && (
          <div>
            {observations.length === 0 ? (
              <p className="text-center text-xs text-neutral-600 py-10">Nenhuma observação registrada ainda.</p>
            ) : (
              <div className="space-y-2">
                {observations.map((o) => (
                  <div
                    key={o.id}
                    className={cn(
                      "rounded-lg border p-3",
                      o.expired ? "border-neutral-800 opacity-50" : "border-neutral-800"
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <p className="flex-1 text-xs text-neutral-200">{o.statement}</p>
                      {o.expired && (
                        <span className="shrink-0 rounded px-1.5 py-0.5 text-[9px] bg-neutral-800 text-neutral-500">expirado</span>
                      )}
                    </div>
                    <div className="mt-2 flex items-center gap-2 text-[10px] text-neutral-600 flex-wrap">
                      <ConfidencePill value={o.confidence} />
                      <span>derivado de: {o.derived_from}</span>
                      <span>reforços: {o.reinforcement_count}</span>
                      <span className="ml-auto">{formatDate(o.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TabBtn({
  active, onClick, icon, label,
}: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs transition-colors",
        active ? "bg-neutral-700 text-neutral-200" : "text-neutral-500 hover:text-neutral-400",
      )}
    >
      {icon}
      {label}
    </button>
  );
}
