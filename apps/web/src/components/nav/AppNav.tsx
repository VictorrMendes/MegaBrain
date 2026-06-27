"use client";

import { useState } from "react";
import {
  LayoutDashboardIcon,
  MessageSquareIcon,
  TargetIcon,
  BrainIcon,
  BookOpenIcon,
  InboxIcon,
  ActivityIcon,
  MonitorIcon,
  PackageIcon,
  PlugIcon,
  CheckIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useUIStore, type OverlayId } from "@/store/useUIStore";

const NAV_ITEMS: { id: OverlayId | "chat", icon: any, label: string }[] = [
  { id: "dashboard",    icon: LayoutDashboardIcon,  label: "Home"           },
  { id: "chat",         icon: MessageSquareIcon,    label: "Chat"           },
  { id: "missions",     icon: TargetIcon,           label: "Missões"        },
  { id: "memory",       icon: BrainIcon,            label: "Memória"        },
  { id: "knowledge",    icon: BookOpenIcon,         label: "Conhecimento"   },
  { id: "inbox",        icon: InboxIcon,            label: "Inbox"          },
  { id: "timeline",     icon: ActivityIcon,         label: "Timeline"       },
  { id: "artifacts",    icon: PackageIcon,          label: "Artifacts"      },
  { id: "runtime",      icon: MonitorIcon,          label: "Runtime"        },
  { id: "integrations", icon: PlugIcon,             label: "Integrações"    },
];

export function AppNav() {
  const { workspaces, current, setCurrent } = useWorkspace();
  const [showSwitcher, setShowSwitcher] = useState(false);
  
  const { overlayStack, pushOverlay, closeAllOverlays } = useUIStore();
  const activeOverlay = overlayStack.length > 0 ? overlayStack[overlayStack.length - 1] : "chat";

  const initial = current?.name?.[0]?.toUpperCase() ?? "?";

  return (
    <nav
      className={cn(
        "relative hidden md:flex w-12 shrink-0 flex-col",
        "border-r border-[var(--border-subtle)]",
        "bg-[var(--surface-raised)]",
        "py-3 gap-0.5",
      )}
    >
      {/* Logo mark */}
      <div className="mx-auto mb-4 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-dim text-accent text-sm font-bold tracking-widest select-none shadow-glow-sm">
        K
      </div>

      {/* Nav items */}
      {NAV_ITEMS.map(({ id, icon: Icon, label }) => {
        const active = activeOverlay === id;
        
        return (
          <button
            key={id}
            onClick={() => {
              if (id === "chat") {
                closeAllOverlays();
              } else {
                pushOverlay(id as OverlayId);
              }
            }}
            className={cn(
              "group mx-auto flex h-9 w-9 items-center justify-center rounded-lg",
              "transition-colors duration-[100ms] relative",
              active
                ? "bg-accent-dim text-accent shadow-glow-sm"
                : "text-content-muted hover:bg-surface-subtle hover:text-content-secondary",
            )}
          >
            <Icon size={16} strokeWidth={active ? 2.2 : 1.8} />

            {/* Tooltip */}
            <span
              className={cn(
                "pointer-events-none absolute left-full ml-3 z-50",
                "hidden whitespace-nowrap rounded-md",
                "bg-[var(--surface-overlay)] border border-[var(--border-default)]",
                "px-2.5 py-1 text-xs text-content-primary shadow-xl",
                "group-hover:flex items-center",
              )}
            >
              {label}
            </span>
          </button>
        );
      })}

      {/* Workspace avatar — bottom */}
      <div className="mt-auto">
        <button
          onClick={() => setShowSwitcher((v) => !v)}
          className={cn(
            "group mx-auto flex h-9 w-9 items-center justify-center",
            "rounded-lg text-content-muted transition-colors duration-[100ms]",
            "hover:bg-surface-subtle hover:text-content-secondary",
            "relative",
          )}
        >
          <span
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-md",
              "bg-[var(--surface-subtle)] text-content-secondary text-[11px] font-semibold",
            )}
          >
            {initial}
          </span>

          {/* Tooltip */}
          <span
            className={cn(
              "pointer-events-none absolute left-full ml-3 z-50",
              "hidden whitespace-nowrap rounded-md",
              "glass",
              "px-2.5 py-1 text-xs text-content-primary shadow-xl",
              "group-hover:flex items-center",
            )}
          >
            {current?.name ?? "Workspace"}
          </span>
        </button>
      </div>

      {/* Workspace switcher dropdown */}
      {showSwitcher && workspaces.length > 0 && (
        <div
          className={cn(
            "absolute bottom-2 left-full ml-2 z-50 min-w-52",
            "rounded-xl",
            "glass-lg py-1.5 shadow-2xl",
          )}
          onMouseLeave={() => setShowSwitcher(false)}
        >
          <p className="px-3 pb-1 pt-0.5 text-[10px] font-semibold uppercase tracking-widest text-content-muted">
            Workspaces
          </p>

          {workspaces.map((ws) => {
            const isCurrent = current?.id === ws.id;
            return (
              <button
                key={ws.id}
                onClick={() => { setCurrent(ws); setShowSwitcher(false); }}
                className={cn(
                  "flex w-full items-center gap-2.5 px-3 py-1.5 text-left",
                  "text-xs transition-colors duration-[100ms]",
                  isCurrent
                    ? "text-content-primary"
                    : "text-content-secondary hover:text-content-primary hover:bg-[var(--surface-subtle)]",
                )}
              >
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded",
                    "text-[10px] font-bold",
                    isCurrent
                      ? "bg-accent-dim text-accent"
                      : "bg-[var(--surface-subtle)] text-content-secondary",
                  )}
                >
                  {ws.name[0].toUpperCase()}
                </span>
                <span className="flex-1 truncate">{ws.name}</span>
                {isCurrent && <CheckIcon size={11} className="shrink-0 text-accent" />}
              </button>
            );
          })}
        </div>
      )}
    </nav>
  );
}
