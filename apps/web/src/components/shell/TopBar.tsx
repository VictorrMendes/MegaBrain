"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/context/WorkspaceContext";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  NotificationBell,
  NotificationCenter,
} from "@/components/shell/NotificationCenter";
import {
  ChevronDownIcon,
  CommandIcon,
  LayersIcon,
  BrainCircuitIcon
} from "lucide-react";
import { useUIStore } from "@/store/useUIStore";

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

interface TopBarProps {
  onOpenPalette: () => void;
}

export function TopBar({ onOpenPalette }: TopBarProps) {
  const { current: workspace, workspaces, setCurrent } = useWorkspace();
  const [wsMenuOpen, setWsMenuOpen] = useState(false);
  const [notifOpen,  setNotifOpen]  = useState(false);
  const { cognitiveState } = useUIStore();

  return (
    <header
      className={cn(
        "relative flex h-[var(--topbar-h)] shrink-0 items-center",
        "border-b border-[var(--border-subtle)]",
        "bg-surface-base px-3",
        "z-topbar",
      )}
    >
      {/* ── Left: Logo + Workspace ── */}
      <div className="flex items-center gap-2 min-w-0">
        {/* Logo */}
        <Link
          href="/dashboard"
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-accent-dim"
        >
          <LayersIcon size={12} className="text-accent" />
        </Link>

        {/* Divider */}
        <span className="h-4 w-px bg-[var(--border-subtle)]" />

        {/* Workspace selector */}
        <div className="relative">
          <button
            onClick={() => setWsMenuOpen((v) => !v)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2 py-1",
              "text-xs text-content-secondary hover:text-content-primary",
              "hover:bg-surface-subtle transition-colors duration-fast",
              wsMenuOpen && "bg-surface-subtle text-content-primary",
            )}
          >
            <span className="max-w-[140px] truncate font-medium">
              {workspace?.name ?? "Workspace"}
            </span>
            <ChevronDownIcon
              size={11}
              className={cn(
                "transition-transform duration-fast text-content-muted",
                wsMenuOpen && "rotate-180",
              )}
            />
          </button>

          {/* Workspace dropdown */}
          {wsMenuOpen && workspaces.length > 0 && (
            <>
              <div
                className="fixed inset-0 z-dropdown"
                onClick={() => setWsMenuOpen(false)}
              />
              <div
                className={cn(
                  "absolute left-0 top-full mt-1 z-dropdown",
                  "min-w-[180px] rounded-lg",
                  "glass shadow-md animate-scale-in",
                  "py-1",
                )}
              >
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setCurrent(ws);
                      setWsMenuOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center gap-2.5 px-3 py-2 text-left",
                      "text-xs transition-colors duration-fast",
                      ws.id === workspace?.id
                        ? "text-accent bg-accent-subtle"
                        : "text-content-secondary hover:text-content-primary hover:bg-surface-subtle",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-5 w-5 shrink-0 items-center justify-center rounded text-2xs font-bold uppercase",
                        ws.id === workspace?.id
                          ? "bg-accent text-white"
                          : "bg-surface-subtle text-content-muted",
                      )}
                    >
                      {ws.name.charAt(0)}
                    </span>
                    <span className="truncate">{ws.name}</span>
                    {ws.id === workspace?.id && (
                      <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent" />
                    )}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Center: Search shortcut (hidden on xs, shown sm+) ── */}
      <div className="hidden sm:flex flex-1 justify-center">
        <button
          onClick={onOpenPalette}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1.5",
            "border border-[var(--border-subtle)] bg-surface-raised",
            "text-xs text-content-muted",
            "hover:border-[var(--border-default)] hover:text-content-secondary",
            "transition-colors duration-fast",
            "w-[220px]",
          )}
        >
          <CommandIcon size={11} />
          <span className="flex-1 text-left">Pesquisar...</span>
          <span className="flex items-center gap-0.5 text-2xs">
            <kbd className="rounded border border-[var(--border-subtle)] bg-surface-subtle px-1 py-0.5">⌘</kbd>
            <kbd className="rounded border border-[var(--border-subtle)] bg-surface-subtle px-1 py-0.5">K</kbd>
          </span>
        </button>
      </div>

      {/* Mobile spacer */}
      <div className="flex-1 sm:hidden" />

      {/* ── Right: Search icon (mobile) + Status + Notifications ── */}
      <div className="flex items-center gap-2">
        {/* Mobile search icon */}
        <button
          onClick={onOpenPalette}
          className="flex sm:hidden h-8 w-8 items-center justify-center rounded-lg text-content-muted hover:bg-surface-subtle transition-colors"
          title="Pesquisar"
        >
          <CommandIcon size={15} />
        </button>
        {/* System status pill */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-[var(--surface-subtle)] border border-[var(--border-subtle)]">
          <div className="relative flex items-center justify-center">
            <BrainCircuitIcon size={12} className={cn("text-accent", cognitiveState !== "idle" && "animate-pulse")} />
            {cognitiveState !== "idle" && (
              <div className="absolute inset-0 rounded-full bg-accent/20 blur-sm animate-pulse"></div>
            )}
          </div>
          <span className="text-[10px] font-semibold text-content-secondary uppercase tracking-widest">
            {cognitiveState === "idle" ? "Online" : cognitiveState}
          </span>
        </div>

        {/* Separator */}
        <span className="h-4 w-px bg-[var(--border-subtle)]" />

        {/* Notification bell */}
        <NotificationBell
          open={notifOpen}
          onToggle={() => setNotifOpen((v) => !v)}
        />
      </div>

      {/* Notification Center panel */}
      <NotificationCenter
        open={notifOpen}
        onClose={() => setNotifOpen(false)}
      />
    </header>
  );
}
