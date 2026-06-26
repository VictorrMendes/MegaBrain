"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
  CheckIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/context/WorkspaceContext";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboardIcon, label: "Home"           },
  { href: "/chat",      icon: MessageSquareIcon,   label: "Chat"           },
  { href: "/missions",  icon: TargetIcon,           label: "Missões"        },
  { href: "/memory",    icon: BrainIcon,            label: "Memória"        },
  { href: "/knowledge", icon: BookOpenIcon,         label: "Conhecimento"   },
  { href: "/inbox",     icon: InboxIcon,            label: "Inbox"          },
  { href: "/timeline",  icon: ActivityIcon,         label: "Timeline"       },
  { href: "/artifacts", icon: PackageIcon,          label: "Artifacts"      },
  { href: "/runtime",   icon: MonitorIcon,          label: "Runtime"        },
];

export function AppNav() {
  const pathname  = usePathname();
  const { workspaces, current, setCurrent } = useWorkspace();
  const [showSwitcher, setShowSwitcher] = useState(false);

  const initial = current?.name?.[0]?.toUpperCase() ?? "?";

  return (
    <nav
      className={cn(
        "relative flex w-12 shrink-0 flex-col",
        "border-r border-[var(--border-subtle)]",
        "bg-[var(--surface-raised)]",
        "py-3 gap-0.5",
      )}
    >
      {/* Logo mark */}
      <div className="mx-auto mb-4 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-dim text-accent text-sm font-bold tracking-widest select-none">
        K
      </div>

      {/* Nav items */}
      {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "group mx-auto flex h-9 w-9 items-center justify-center rounded-lg",
              "transition-colors duration-[100ms] relative",
              active
                ? "bg-accent-dim text-accent"
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
          </Link>
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
              "bg-[var(--surface-overlay)] border border-[var(--border-default)]",
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
            "rounded-xl border border-[var(--border-default)]",
            "bg-[var(--surface-overlay)] py-1.5 shadow-2xl",
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
