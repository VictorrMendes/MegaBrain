"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/context/WorkspaceContext";
import { api } from "@/lib/api";
import {
  ActivityIcon,
  BrainIcon,
  CalendarIcon,
  CpuIcon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

interface StatusData {
  activeMissions: number;
  schedulerTasks: number;
  systemOk:       boolean;
  memoryCount:    number;
}

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function StatusBar() {
  const { current: workspace } = useWorkspace();
  const [status, setStatus]   = useState<StatusData | null>(null);
  const [time,   setTime]     = useState(new Date());

  // Clock
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // Fetch runtime status (every 30s)
  useEffect(() => {
    async function fetch() {
      try {
        const [rt, mems] = await Promise.allSettled([
          api.getRuntimeStatus(),
          workspace ? api.listMemories(workspace.id, 1) : Promise.resolve([]),
        ]);

        const rtData = rt.status === "fulfilled" ? rt.value : null;
        const memData = mems.status === "fulfilled" ? mems.value : [];

        setStatus({
          activeMissions: rtData?.active_missions.length ?? 0,
          schedulerTasks: rtData?.scheduler.active_triggers ?? 0,
          systemOk:       rtData?.health.every((h) => h.status === "ready") ?? true,
          memoryCount:    Array.isArray(memData) ? memData.length : 0,
        });
      } catch {
        // silently ignore — status bar is non-critical
      }
    }

    fetch();
    const interval = setInterval(fetch, 30_000);
    return () => clearInterval(interval);
  }, [workspace?.id]);

  const timeStr = time.toLocaleTimeString("pt-BR", {
    hour: "2-digit", minute: "2-digit",
  });

  return (
    <footer
      className={cn(
        "hidden md:flex h-[var(--statusbar-h)] shrink-0 items-center justify-between",
        "border-t border-[var(--border-subtle)] bg-surface-inset",
        "px-3 z-statusbar",
      )}
    >
      {/* ── Left: System indicators ── */}
      <div className="flex items-center gap-3">
        {/* System health dot */}
        <Link
          href="/runtime"
          className="flex items-center gap-1 hover:opacity-80 transition-opacity"
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              status === null
                ? "bg-content-muted animate-pulse-dot"
                : status.systemOk
                  ? "bg-status-success"
                  : "bg-status-warning animate-pulse-dot",
            )}
          />
          <span className="text-2xs text-content-muted">
            {status === null ? "…" : status.systemOk ? "operacional" : "degradado"}
          </span>
        </Link>

        <span className="h-3 w-px bg-[var(--border-subtle)]" />

        {/* Active missions */}
        {status !== null && status.activeMissions > 0 && (
          <>
            <Link
              href="/missions"
              className="flex items-center gap-1 hover:opacity-80 transition-opacity"
            >
              <ActivityIcon size={10} className="text-status-active animate-pulse-dot" />
              <span className="text-2xs text-content-muted tabular-nums">
                {status.activeMissions} missão{status.activeMissions !== 1 ? "ões" : ""} ativa{status.activeMissions !== 1 ? "s" : ""}
              </span>
            </Link>
            <span className="h-3 w-px bg-[var(--border-subtle)]" />
          </>
        )}

        {/* Scheduler */}
        {status !== null && status.schedulerTasks > 0 && (
          <span className="flex items-center gap-1">
            <ZapIcon size={10} className="text-content-muted" />
            <span className="text-2xs text-content-muted tabular-nums">
              {status.schedulerTasks} trigger{status.schedulerTasks !== 1 ? "s" : ""}
            </span>
          </span>
        )}
      </div>

      {/* ── Center: Workspace name ── */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-1.5">
        <CpuIcon size={9} className="text-content-muted opacity-40" />
        <span className="text-2xs text-content-muted opacity-60">
          {workspace?.name ?? "Khonshu"}
        </span>
      </div>

      {/* ── Right: Memory count + time ── */}
      <div className="flex items-center gap-3">
        {status !== null && (
          <Link
            href="/memory"
            className="flex items-center gap-1 hover:opacity-80 transition-opacity"
          >
            <BrainIcon size={10} className="text-content-muted" />
            <span className="text-2xs text-content-muted tabular-nums">
              {status.memoryCount} memória{status.memoryCount !== 1 ? "s" : ""}
            </span>
          </Link>
        )}

        <span className="h-3 w-px bg-[var(--border-subtle)]" />

        {/* Clock */}
        <span className="flex items-center gap-1">
          <CalendarIcon size={10} className="text-content-muted" />
          <span className="text-2xs text-content-muted tabular-nums font-mono">
            {timeStr}
          </span>
        </span>
      </div>
    </footer>
  );
}
