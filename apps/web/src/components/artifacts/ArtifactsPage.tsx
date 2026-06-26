"use client";

import { useEffect, useState } from "react";
import { api, type MissionArtifact, type Mission } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Badge, Spinner } from "@/components/ui";
import {
  CodeIcon,
  ExternalLinkIcon,
  FileIcon,
  FileTextIcon,
  FilterIcon,
  ImageIcon,
  PackageIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function ArtifactIcon({ mime }: { mime: string }) {
  if (mime.startsWith("image/"))
    return <ImageIcon    size={14} className="shrink-0 text-status-active" />;
  if (mime.startsWith("text/"))
    return <FileTextIcon size={14} className="shrink-0 text-status-info" />;
  if (mime.includes("json") || mime.includes("javascript") || mime.includes("python"))
    return <CodeIcon     size={14} className="shrink-0 text-status-warning" />;
  return   <FileIcon     size={14} className="shrink-0 text-content-muted" />;
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function ArtifactsPage() {
  const { current: workspace, loading: wsLoading } = useWorkspace();
  const [artifacts,       setArtifacts]       = useState<MissionArtifact[]>([]);
  const [missions,        setMissions]        = useState<Mission[]>([]);
  const [selectedMission, setSelectedMission] = useState<string>("");
  const [loading,         setLoading]         = useState(false);
  const [filtering,       setFiltering]       = useState(false);

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
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-6 py-8">

        {/* ── Header ── */}
        <div className="mb-6 flex items-center gap-2">
          <PackageIcon size={14} className="text-content-muted" />
          <h1 className="text-md font-semibold text-content-primary">Artifacts</h1>
          <span className="ml-auto text-xs text-content-muted">
            {artifacts.length} arquivo{artifacts.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* ── Mission filter ── */}
        {missions.length > 0 && (
          <div className="mb-6 flex items-center gap-2">
            <FilterIcon size={12} className="shrink-0 text-content-muted" />
            <div className="relative flex-1 max-w-sm">
              <select
                value={selectedMission}
                onChange={(e) => filterByMission(e.target.value)}
                className={cn(
                  "w-full appearance-none rounded-lg border py-2 pl-3 pr-8 text-sm",
                  "border-[var(--border-default)] bg-[var(--surface-raised)]",
                  "text-content-primary focus:outline-none focus:border-[var(--border-accent)]",
                  "transition-colors cursor-pointer",
                )}
              >
                <option value="">Todas as missões</option>
                {missions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.intent.slice(0, 60)}
                  </option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-content-muted">
                ▾
              </span>
            </div>
            {filtering && <Spinner size="sm" />}
          </div>
        )}

        {/* ── Artifacts ── */}
        {artifacts.length === 0 ? (
          <p className="py-16 text-center text-sm text-content-muted">
            {selectedMission
              ? "Nenhum artifact para esta missão."
              : "Nenhum artifact gerado ainda."}
          </p>
        ) : (
          <div className="space-y-8 animate-fade-in">
            {Object.entries(groupedByType).map(([type, items]) => (
              <div key={type}>
                <div className="mb-3 flex items-center gap-3">
                  <h2 className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
                    {type}
                  </h2>
                  <Badge variant="default" size="sm">{items.length}</Badge>
                  <div className="flex-1 h-px bg-[var(--border-subtle)]" />
                </div>

                <div className="space-y-1.5">
                  {items.map((a) => (
                    <ArtifactRow key={a.id} artifact={a} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Sub-component
// ─────────────────────────────────────────────────────────────

function ArtifactRow({ artifact: a }: { artifact: MissionArtifact }) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border border-[var(--border-subtle)]",
        "bg-[var(--surface-raised)] px-4 py-3",
        "transition-colors hover:border-[var(--border-default)]",
      )}
    >
      <ArtifactIcon mime={a.mime} />

      <div className="flex-1 min-w-0">
        <p className="text-sm text-content-primary truncate">{a.name}</p>
        <p className="mt-0.5 text-[11px] font-mono text-content-muted">{a.mime}</p>
      </div>

      <div className="shrink-0 flex items-center gap-3">
        <span className="text-[11px] text-content-muted tabular-nums">
          {formatDate(a.created_at)}
        </span>
        {a.uri && (
          <a
            href={a.uri}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover transition-colors"
          >
            <ExternalLinkIcon size={12} />
            abrir
          </a>
        )}
      </div>
    </div>
  );
}
