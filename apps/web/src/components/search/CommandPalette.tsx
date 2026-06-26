"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type SearchResult } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import {
  SearchIcon,
  LoaderIcon,
  TargetIcon,
  BrainIcon,
  BookOpenIcon,
  PackageIcon,
  LightbulbIcon,
} from "lucide-react";

const TYPE_ICON: Record<string, React.ReactNode> = {
  mission:     <TargetIcon size={13} className="text-violet-400" />,
  memory:      <BrainIcon size={13} className="text-emerald-400" />,
  fact:        <BookOpenIcon size={13} className="text-blue-400" />,
  observation: <LightbulbIcon size={13} className="text-yellow-400" />,
  artifact:    <PackageIcon size={13} className="text-orange-400" />,
};

const TYPE_LABEL: Record<string, string> = {
  mission:     "missão",
  memory:      "memória",
  fact:        "fato",
  observation: "observação",
  artifact:    "artifact",
};

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: Props) {
  const router = useRouter();
  const { current: workspace } = useWorkspace();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setResults([]);
      setCursor(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) { setResults([]); return; }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.search(query, workspace?.id);
        setResults(res.results);
        setCursor(0);
      } finally {
        setLoading(false);
      }
    }, 280);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, workspace?.id]);

  function navigate(href: string) {
    router.push(href);
    onClose();
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") { onClose(); return; }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter" && results[cursor]) {
      navigate(results[cursor].href);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative w-full max-w-xl rounded-xl border border-neutral-700 bg-neutral-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-neutral-800">
          {loading
            ? <LoaderIcon size={15} className="shrink-0 animate-spin text-neutral-500" />
            : <SearchIcon size={15} className="shrink-0 text-neutral-500" />
          }
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar missões, memórias, conhecimento, artifacts…"
            className="flex-1 bg-transparent text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none"
          />
          <kbd className="rounded border border-neutral-700 px-1.5 py-0.5 text-[10px] text-neutral-600">
            ESC
          </kbd>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <ul className="max-h-96 overflow-y-auto py-1">
            {results.map((r, i) => (
              <li key={r.id}>
                <button
                  onClick={() => navigate(r.href)}
                  onMouseEnter={() => setCursor(i)}
                  className={cn(
                    "flex w-full items-start gap-3 px-4 py-2.5 text-left transition-colors",
                    cursor === i ? "bg-neutral-800" : "hover:bg-neutral-800/60"
                  )}
                >
                  <span className="mt-0.5 shrink-0">{TYPE_ICON[r.type] ?? <SearchIcon size={13} />}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-neutral-200 truncate">{r.title}</p>
                    <p className="text-xs text-neutral-500 truncate">{r.excerpt}</p>
                  </div>
                  <span className="shrink-0 text-[10px] text-neutral-600 mt-0.5">
                    {TYPE_LABEL[r.type] ?? r.type}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {query.trim() && !loading && results.length === 0 && (
          <p className="px-4 py-6 text-center text-xs text-neutral-600">
            Nenhum resultado para "{query}"
          </p>
        )}

        {!query.trim() && (
          <div className="flex flex-wrap gap-2 px-4 py-3">
            {[
              { label: "Missões", href: "/missions", icon: <TargetIcon size={11} /> },
              { label: "Memória", href: "/memory", icon: <BrainIcon size={11} /> },
              { label: "Conhecimento", href: "/knowledge", icon: <BookOpenIcon size={11} /> },
              { label: "Artifacts", href: "/artifacts", icon: <PackageIcon size={11} /> },
            ].map((item) => (
              <button
                key={item.href}
                onClick={() => navigate(item.href)}
                className="flex items-center gap-1.5 rounded-md bg-neutral-800 px-2.5 py-1.5 text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </div>
        )}

        {/* Footer hint */}
        <div className="flex items-center justify-between border-t border-neutral-800 px-4 py-2">
          <span className="text-[10px] text-neutral-700">↑↓ navegar · Enter abrir · Esc fechar</span>
          {workspace && (
            <span className="text-[10px] text-neutral-700">{workspace.name}</span>
          )}
        </div>
      </div>
    </div>
  );
}
