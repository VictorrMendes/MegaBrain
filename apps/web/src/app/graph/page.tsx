"use client";

import { useEffect, useState } from "react";
import { api, type GraphNode, type ObsidianGraph } from "@/lib/api";
import { ForceGraph } from "@/components/graph/ForceGraph";

const WORKSPACE_KEY = "khonshu_workspace_id";

export default function GraphPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [graph, setGraph] = useState<ObsidianGraph | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noteCount, setNoteCount] = useState(0);

  useEffect(() => {
    const stored = localStorage.getItem(WORKSPACE_KEY);
    if (!stored) {
      api.listWorkspaces().then((ws) => {
        if (ws.length > 0) {
          localStorage.setItem(WORKSPACE_KEY, ws[0].id);
          setWorkspaceId(ws[0].id);
        }
      });
    } else {
      setWorkspaceId(stored);
    }
  }, []);

  useEffect(() => {
    if (!workspaceId) return;
    setLoading(true);
    api
      .getObsidianGraph(workspaceId)
      .then((g) => {
        setGraph(g);
        setNoteCount(g.nodes.length);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [workspaceId]);

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <a href="/chat" className="text-sm text-gray-400 hover:text-gray-200">← Chat</a>
          <h1 className="mt-2 text-lg font-semibold">Knowledge Graph</h1>
          <p className="text-xs text-gray-500 mt-1">{noteCount} notas indexadas</p>
        </div>

        {selected ? (
          <div className="p-4 flex-1 overflow-y-auto">
            <h2 className="font-medium text-sm mb-1">{selected.title}</h2>
            <p className="text-xs text-gray-500 mb-3 break-all">{selected.path}</p>
            {selected.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {selected.tags.map((t) => (
                  <span key={t} className="px-2 py-0.5 bg-gray-700 rounded-full text-xs">
                    {t}
                  </span>
                ))}
              </div>
            )}
            {graph && (
              <div className="mt-4">
                <p className="text-xs text-gray-500 mb-1">Links de saída</p>
                <ul className="space-y-1">
                  {graph.edges
                    .filter((e) => e.source === selected.id)
                    .map((e) => {
                      const target = graph.nodes.find((n) => n.id === e.target);
                      return (
                        <li key={e.target} className="text-xs text-blue-400 cursor-pointer hover:underline"
                          onClick={() => setSelected(target ?? null)}>
                          → {target?.title ?? e.target}
                        </li>
                      );
                    })}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 text-xs text-gray-500">
            Clique em um nó para ver detalhes
          </div>
        )}
      </aside>

      {/* Graph canvas */}
      <main className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-gray-400 text-sm">Carregando grafo...</span>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-red-400 text-sm">{error}</span>
          </div>
        )}
        {graph && !loading && (
          <ForceGraph graph={graph} onNodeClick={setSelected} />
        )}
        {graph && graph.nodes.length === 0 && !loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <p className="text-gray-400 text-sm">Nenhuma nota sincronizada ainda.</p>
            <p className="text-gray-500 text-xs">
              Execute o script <code className="bg-gray-800 px-1 rounded">sync_obsidian.py</code> para indexar seu vault.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
