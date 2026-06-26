"use client";

import { useEffect, useState } from "react";
import { api, type MissionArtifact, type Mission } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import {
  PackageIcon, LoaderIcon, FileIcon, ImageIcon, FileTextIcon, CodeIcon,
  FilterIcon,
} from "lucide-react";

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function ArtifactIcon({ mime }: { mime: string }) {
  if (mime.startsWith("image/")) return <ImageIcon size={14} className="text-violet-400 shrink-0" />;
  if (mime.startsWith("text/")) return <FileTextIcon size={14} className="text-blue-400 shrink-0" />;
  if (mime.includes("json") || mime.includes("javascript") || mime.includes("python"))
    return <CodeIcon size={14} className="text-yellow-400 shrink-0" />;
  return <FileIcon size={14} className="text-neutral-400 shrink-0" />;
}

export function ArtifactsPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [artifacts, setArtifacts] = useState<MissionArtifact[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [selectedMission, setSelectedMission] = useState<string | "">("");
  const [loading, setLoading] = useState(false);
  const [filtering, setFiltering] = useState(false);

  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    Promise.all([api.listArtifacts(workspace.id), api.listMissions(workspace.id)])
      .then(([arts, ms]) => { setArtifacts(arts); setMissions(ms); })
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  async function filterByMission(missionId: string) {
    if (!workspace) return;
    setSelectedMission(missionId);
    setFiltering(true);
    try {
      const arts = await api.listArtifacts(workspace.id, missionId || undefined);
      setArtifacts(arts);
    } finally {
      setFiltering(false);
    }
  }

  const groupedByType = artifacts.reduce<Record<string, MissionArtifact[]>>((acc, a) => {
    (acc[a.type] ??= []).push(a);
    return acc;
  }, {});

  if (wsLoading || loading) {
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
        <div className="mb-4 flex items-center gap-2 flex-wrap">
          <PackageIcon size={15} className="text-neutral-400" />
          <h1 className="text-sm font-semibold text-neutral-300">Artifacts</h1>
          <span className="ml-auto text-xs text-neutral-600">{artifacts.length} arquivos</span>
        </div>

        {/* Mission filter */}
        {missions.length > 0 && (
          <div className="mb-5 flex items-center gap-2">
            <FilterIcon size={12} className="text-neutral-600 shrink-0" />
            <select
              value={selectedMission}
              onChange={(e) => filterByMission(e.target.value)}
              className="flex-1 max-w-xs rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-xs text-neutral-300 focus:outline-none focus:border-neutral-700"
            >
              <option value="">Todas as missões</option>
              {missions.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.intent.slice(0, 60)}
                </option>
              ))}
            </select>
            {filtering && <LoaderIcon size={13} className="animate-spin text-neutral-500" />}
          </div>
        )}

        {/* Artifacts */}
        {artifacts.length === 0 ? (
          <p className="text-center text-xs text-neutral-600 py-10">
            {selectedMission ? "Nenhum artifact para esta missão." : "Nenhum artifact gerado ainda."}
          </p>
        ) : (
          Object.entries(groupedByType).map(([type, items]) => (
            <div key={type} className="mb-6">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-widest text-neutral-500">
                {type} ({items.length})
              </h2>
              <div className="space-y-2">
                {items.map((a) => (
                  <div key={a.id} className="flex items-center gap-3 rounded-lg border border-neutral-800 p-3">
                    <ArtifactIcon mime={a.mime} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-neutral-200 truncate">{a.name}</p>
                      <p className="mt-0.5 text-[10px] text-neutral-600">{a.mime}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-[10px] text-neutral-600">{formatDate(a.created_at)}</p>
                      {a.uri && (
                        <a
                          href={a.uri}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-0.5 text-[10px] text-blue-500 hover:text-blue-400"
                        >
                          abrir
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
