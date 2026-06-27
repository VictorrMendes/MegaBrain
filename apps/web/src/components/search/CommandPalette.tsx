"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type SearchResult } from "@/lib/api";
import { useWorkspace } from "@/context/WorkspaceContext";
import { cn } from "@/lib/cn";
import { Spinner } from "@/components/ui";
import { useUIStore, type OverlayId } from "@/store/useUIStore";
import {
  BookOpenIcon,
  BrainIcon,
  ClockIcon,
  LightbulbIcon,
  NetworkIcon,
  PackageIcon,
  PlusIcon,
  SearchIcon,
  TargetIcon,
  XIcon,
  ZapIcon,
  TerminalSquareIcon
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const HISTORY_KEY = "khonshu_search_history";
const MAX_HISTORY  = 6;

const TYPE_ICON: Record<string, React.ReactNode> = {
  mission:     <TargetIcon    size={13} className="text-status-active" />,
  memory:      <BrainIcon     size={13} className="text-status-success" />,
  fact:        <BookOpenIcon  size={13} className="text-status-info" />,
  observation: <LightbulbIcon size={13} className="text-status-warning" />,
  entity:      <NetworkIcon   size={13} className="text-accent" />,
  artifact:    <PackageIcon   size={13} className="text-content-secondary" />,
  os_command:  <TerminalSquareIcon size={13} className="text-accent" />
};

const TYPE_LABEL: Record<string, string> = {
  mission:     "missão",
  memory:      "memória",
  fact:        "fato",
  observation: "observação",
  entity:      "entidade",
  artifact:    "artifact",
  os_command:  "system action"
};

const QUICK_NAV = [
  { label: "Missões",      href: "missions",  icon: <TargetIcon    size={11} /> },
  { label: "Memória",      href: "memory",    icon: <BrainIcon     size={11} /> },
  { label: "Conhecimento", href: "knowledge", icon: <BookOpenIcon  size={11} /> },
  { label: "Artifacts",    href: "artifacts", icon: <PackageIcon   size={11} /> },
];

const TYPE_FILTERS = [
  { id: "all",         label: "Todos" },
  { id: "mission",     label: "Missões" },
  { id: "memory",      label: "Memória" },
  { id: "fact",        label: "Conhecimento" },
  { id: "entity",      label: "Entidades" },
  { id: "artifact",    label: "Artifacts" },
];

// ─────────────────────────────────────────────────────────────
// History helpers
// ─────────────────────────────────────────────────────────────

function loadHistory(): string[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveHistory(queries: string[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(queries.slice(0, MAX_HISTORY)));
}

function pushHistory(q: string) {
  const prev = loadHistory().filter((x) => x !== q);
  saveHistory([q, ...prev]);
}

function removeHistory(q: string) {
  saveHistory(loadHistory().filter((x) => x !== q));
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

interface Props {
  open:    boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: Props) {
  const router = useRouter();
  const { current: workspace } = useWorkspace();
  const { pushOverlay, setCognitiveState } = useUIStore();
  
  const [query,      setQuery]      = useState("");
  const [results,    setResults]    = useState<SearchResult[]>([]);
  const [loading,    setLoading]    = useState(false);
  const [cursor,     setCursor]     = useState(0);
  const [typeFilter, setTypeFilter] = useState("all");
  const [history,    setHistory]    = useState<string[]>([]);
  const inputRef    = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isOsCommandMode = query.startsWith(">");

  const OS_COMMANDS = [
    { id: "memory", title: "Open Memory Overlay", href: "memory" },
    { id: "knowledge", title: "Open Knowledge Overlay", href: "knowledge" },
    { id: "dashboard", title: "Open OS Dashboard", href: "dashboard" },
    { id: "missions", title: "Open Missions Overlay", href: "missions" },
    { id: "think", title: "Force Cognitive State: Thinking", action: () => setCognitiveState("thinking") },
    { id: "idle", title: "Force Cognitive State: Idle", action: () => setCognitiveState("idle") },
    { id: "summarize", title: "Summarize Workspace", action: () => setCognitiveState("generating") },
  ];

  useEffect(() => {
    if (open) {
      setQuery("");
      setResults([]);
      setCursor(0);
      setTypeFilter("all");
      setHistory(loadHistory());
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) { setResults([]); return; }

    if (isOsCommandMode) {
      const q = query.slice(1).trim().toLowerCase();
      const filtered = OS_COMMANDS.filter(c => c.title.toLowerCase().includes(q));
      setResults(filtered.map(c => ({
        id: c.id,
        type: "os_command",
        title: c.title,
        excerpt: "Action OS",
        href: c.href ?? "action",
        score: 1.0,
        workspace_id: workspace?.id ?? "global",
      })));
      setLoading(false);
      return;
    }

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

  function navigate(href: string, searchQuery?: string) {
    if (searchQuery && !isOsCommandMode) {
      pushHistory(searchQuery);
      setHistory(loadHistory());
    }
    
    // Execute action OS commands
    if (isOsCommandMode && href === "action") {
      const activeCmd = OS_COMMANDS.find(c => c.id === results[cursor]?.id);
      if (activeCmd && activeCmd.action) activeCmd.action();
      onClose();
      return;
    }

    // Default to pushing overlay
    pushOverlay(href.replace('/', '') as OverlayId);
    onClose();
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") { onClose(); return; }
    const visible = filteredResults;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, visible.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter" && visible[cursor]) {
      navigate(visible[cursor].href, query);
    }
  }

  const filteredResults = typeFilter === "all" || isOsCommandMode
    ? results
    : results.filter((r) => r.type === typeFilter || (typeFilter === "fact" && (r.type === "fact" || r.type === "observation")));

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]"
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
          {query && (
            <button
              onClick={() => { setQuery(""); setResults([]); }}
              className="text-content-muted hover:text-content-secondary"
            >
              <XIcon size={13} />
            </button>
          )}
          <kbd className="rounded border border-[var(--border-default)] px-1.5 py-0.5 text-[10px] text-content-muted">
            ESC
          </kbd>
        </div>

        {/* ── Type filter tabs ── */}
        {results.length > 0 && (
          <div className="flex gap-1.5 overflow-x-auto border-b border-[var(--border-subtle)] px-3 py-1.5">
            {TYPE_FILTERS.filter((f) => f.id === "all" || results.some((r) => r.type === f.id || (f.id === "fact" && (r.type === "fact" || r.type === "observation")))).map((f) => {
              const count = f.id === "all"
                ? results.length
                : results.filter((r) => r.type === f.id || (f.id === "fact" && (r.type === "fact" || r.type === "observation"))).length;
              return (
                <button
                  key={f.id}
                  onClick={() => { setTypeFilter(f.id); setCursor(0); }}
                  className={cn(
                    "shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium transition-colors",
                    typeFilter === f.id
                      ? "bg-accent-dim text-accent"
                      : "text-content-muted hover:text-content-secondary",
                  )}
                >
                  {f.label} <span className="opacity-60">{count}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* ── Results ── */}
        {filteredResults.length > 0 && (
          <ul className="max-h-80 overflow-y-auto py-1">
            {filteredResults.map((r, i) => (
              <li key={r.id}>
                <button
                  onClick={() => navigate(r.href, query)}
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
                    <p className={cn(
                      "truncate text-sm",
                      cursor === i ? "text-content-primary" : "text-content-secondary",
                    )}>
                      {r.title}
                    </p>
                    <p className="truncate text-xs text-content-muted">{r.excerpt}</p>
                  </div>

                  {/* Score bar */}
                  <div className="flex shrink-0 flex-col items-end gap-0.5">
                    <span className={cn(
                      "text-[10px]",
                      cursor === i ? "text-accent" : "text-content-muted",
                    )}>
                      {TYPE_LABEL[r.type] ?? r.type}
                    </span>
                    <div className="flex h-1 w-10 overflow-hidden rounded-full bg-[var(--surface-subtle)]">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          r.score >= 0.8 ? "bg-status-success" :
                          r.score >= 0.5 ? "bg-accent" :
                          "bg-content-muted",
                        )}
                        style={{ width: `${Math.round(r.score * 100)}%` }}
                      />
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* ── Empty query state ── */}
        {!query.trim() && (
          <div className="px-4 py-3">
            {/* Recent history */}
            {history.length > 0 && (
              <div className="mb-3">
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-content-muted">
                  Recentes
                </p>
                <div className="space-y-0.5">
                  {history.map((h) => (
                    <div key={h} className="group flex items-center gap-2">
                      <button
                        onClick={() => setQuery(h)}
                        className="flex flex-1 items-center gap-2 rounded px-2 py-1 text-left hover:bg-[var(--surface-subtle)]"
                      >
                        <ClockIcon size={11} className="text-content-muted" />
                        <span className="truncate text-xs text-content-secondary">{h}</span>
                      </button>
                      <button
                        onClick={() => { removeHistory(h); setHistory(loadHistory()); }}
                        className="hidden rounded p-1 text-content-muted hover:text-content-secondary group-hover:flex"
                      >
                        <XIcon size={10} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick nav */}
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-content-muted">
              Navegar
            </p>
            <div className="flex flex-wrap gap-2">
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

            {/* Create shortcuts */}
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => navigate("missions")}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs",
                  "border-accent-subtle bg-accent-dim text-accent",
                  "hover:bg-accent-subtle transition-colors",
                )}
              >
                <PlusIcon size={11} /> Nova missão
              </button>
              <button
                onClick={() => navigate("memory")}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs",
                  "border-[var(--border-subtle)] bg-[var(--surface-subtle)]",
                  "text-content-secondary hover:border-[var(--border-default)] transition-colors",
                )}
              >
                <PlusIcon size={11} /> Nova memória
              </button>
            </div>
          </div>
        )}

        {/* ── No results ── */}
        {query.trim() && !loading && filteredResults.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-content-muted">
            Nenhum resultado para &ldquo;{query}&rdquo;
          </p>
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
