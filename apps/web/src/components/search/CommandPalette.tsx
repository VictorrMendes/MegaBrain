"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type SearchResult } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Spinner } from "@/components/ui";
import {
  BookOpenIcon,
  BrainIcon,
  LightbulbIcon,
  PackageIcon,
  SearchIcon,
  TargetIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const TYPE_ICON: Record<string, React.ReactNode> = {
  mission:     <TargetIcon    size={13} className="text-status-active" />,
  memory:      <BrainIcon     size={13} className="text-status-success" />,
  fact:        <BookOpenIcon  size={13} className="text-status-info" />,
  observation: <LightbulbIcon size={13} className="text-status-warning" />,
  artifact:    <PackageIcon   size={13} className="text-content-secondary" />,
};

const TYPE_LABEL: Record<string, string> = {
  mission:     "missão",
  memory:      "memória",
  fact:        "fato",
  observation: "observação",
  artifact:    "artifact",
};

const QUICK_NAV = [
  { label: "Missões",      href: "/missions",  icon: <TargetIcon    size={11} /> },
  { label: "Memória",      href: "/memory",    icon: <BrainIcon     size={11} /> },
  { label: "Conhecimento", href: "/knowledge", icon: <BookOpenIcon  size={11} /> },
  { label: "Artifacts",    href: "/artifacts", icon: <PackageIcon   size={11} /> },
];

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

interface Props {
  open:    boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: Props) {
  const router    = useRouter();
  const { current: workspace } = useWorkspace();
  const [query,   setQuery]   = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [cursor,  setCursor]  = useState(0);
  const inputRef   = useRef<HTMLInputElement>(null);
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

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
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
        className={cn(
          "relative w-full max-w-xl rounded-xl shadow-2xl",
          "border border-[var(--border-default)]",
          "bg-[var(--surface-overlay)]",
          "animate-fade-in",
        )}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        {/* ── Input ── */}
        <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] px-4 py-3">
          {loading
            ? <Spinner size="sm" />
            : <SearchIcon size={15} className="shrink-0 text-content-muted" />
          }
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar missões, memórias, conhecimento, artifacts…"
            className={cn(
              "flex-1 bg-transparent text-sm",
              "text-content-primary placeholder:text-content-placeholder",
              "focus:outline-none",
            )}
          />
          <kbd className="rounded border border-[var(--border-default)] px-1.5 py-0.5 text-[10px] text-content-muted">
            ESC
          </kbd>
        </div>

        {/* ── Results ── */}
        {results.length > 0 && (
          <ul className="max-h-96 overflow-y-auto py-1">
            {results.map((r, i) => (
              <li key={r.id}>
                <button
                  onClick={() => navigate(r.href)}
                  onMouseEnter={() => setCursor(i)}
                  className={cn(
                    "flex w-full items-start gap-3 px-4 py-2.5 text-left transition-colors",
                    cursor === i
                      ? "bg-[var(--accent-dim)]"
                      : "hover:bg-[var(--surface-subtle)]",
                  )}
                >
                  <span className="mt-0.5 shrink-0">
                    {TYPE_ICON[r.type] ?? <SearchIcon size={13} className="text-content-muted" />}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        "truncate text-sm",
                        cursor === i ? "text-content-primary" : "text-content-secondary",
                      )}
                    >
                      {r.title}
                    </p>
                    <p className="truncate text-xs text-content-muted">{r.excerpt}</p>
                  </div>
                  <span
                    className={cn(
                      "mt-0.5 shrink-0 text-[10px]",
                      cursor === i ? "text-accent" : "text-content-muted",
                    )}
                  >
                    {TYPE_LABEL[r.type] ?? r.type}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* ── Empty state ── */}
        {query.trim() && !loading && results.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-content-muted">
            Nenhum resultado para "{query}"
          </p>
        )}

        {/* ── Quick nav ── */}
        {!query.trim() && (
          <div className="flex flex-wrap gap-2 px-4 py-3">
            {QUICK_NAV.map((item) => (
              <button
                key={item.href}
                onClick={() => navigate(item.href)}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs",
                  "border-[var(--border-subtle)] bg-[var(--surface-subtle)]",
                  "text-content-secondary hover:border-[var(--border-default)] hover:text-content-primary",
                  "transition-colors",
                )}
              >
                <span className="text-content-muted">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        )}

        {/* ── Footer ── */}
        <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-4 py-2">
          <span className="text-[10px] text-content-muted">
            ↑↓ navegar · Enter abrir · Esc fechar
          </span>
          {workspace && (
            <span className="text-[10px] text-content-muted">{workspace.name}</span>
          )}
        </div>
      </div>
    </div>
  );
}
