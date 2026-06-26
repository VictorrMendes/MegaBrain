"use client";

import { useEffect, useState } from "react";
import { api, type Memory, type Workspace } from "@/lib/api";
import { cn } from "@/lib/cn";
import { BrainIcon, LoaderIcon, SearchIcon } from "lucide-react";

const TYPE_COLOR: Record<string, string> = {
  semantic:    "bg-violet-950 text-violet-400",
  episodic:    "bg-blue-950 text-blue-400",
  procedural:  "bg-cyan-950 text-cyan-400",
  declarative: "bg-emerald-950 text-emerald-400",
};

function formatDate(s: string) {
  return new Date(s).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export function MemoryPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);

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
        const mems = await api.listMemories(ws.id);
        setMemories(mems);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function recall() {
    if (!workspace || !query.trim()) return;
    setSearching(true);
    try {
      const results = await api.recallMemories(workspace.id, query);
      setMemories(results);
    } finally {
      setSearching(false);
    }
  }

  async function resetList() {
    if (!workspace) return;
    setSearching(true);
    setQuery("");
    try {
      const mems = await api.listMemories(workspace.id);
      setMemories(mems);
    } finally {
      setSearching(false);
    }
  }

  const grouped = memories.reduce<Record<string, Memory[]>>((acc, m) => {
    const key = m.type || "outros";
    (acc[key] ??= []).push(m);
    return acc;
  }, {});

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
          <BrainIcon size={15} className="text-neutral-400" />
          <h1 className="text-sm font-semibold text-neutral-300">Memórias</h1>
          <span className="ml-auto text-xs text-neutral-600">{memories.length} registros</span>
        </div>

        {/* Search */}
        <div className="mb-6 flex gap-2">
          <div className="relative flex-1">
            <SearchIcon size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && recall()}
              placeholder="Buscar por relevância semântica…"
              className="w-full rounded-lg border border-neutral-800 bg-neutral-900 py-2 pl-8 pr-3 text-xs text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-neutral-700"
            />
          </div>
          <button
            onClick={query.trim() ? recall : resetList}
            disabled={searching}
            className="rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs text-neutral-300 hover:bg-neutral-800 disabled:opacity-50"
          >
            {searching ? <LoaderIcon size={13} className="animate-spin" /> : query.trim() ? "Buscar" : "Resetar"}
          </button>
        </div>

        {memories.length === 0 ? (
          <p className="text-center text-xs text-neutral-600 py-10">Nenhuma memória encontrada.</p>
        ) : (
          Object.entries(grouped).map(([type, items]) => (
            <div key={type} className="mb-6">
              <h2 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-neutral-500">
                <span className={cn("rounded px-1.5 py-0.5 text-[10px]", TYPE_COLOR[type] ?? "bg-neutral-800 text-neutral-500")}>{type}</span>
                <span>{items.length}</span>
              </h2>
              <div className="space-y-2">
                {items.map((m) => (
                  <div key={m.id} className="rounded-lg border border-neutral-800 p-3">
                    <p className="text-xs text-neutral-200">{m.content}</p>
                    <div className="mt-2 flex items-center gap-3 text-[10px] text-neutral-600">
                      {m.source && <span>fonte: {m.source}</span>}
                      <span>importância: {(m.importance * 100).toFixed(0)}%</span>
                      <span className="ml-auto">{formatDate(m.created_at)}</span>
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
