"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  ActivityIcon,
  BookOpenIcon,
  BrainIcon,
  CheckIcon,
  GridIcon,
  InboxIcon,
  LayoutDashboardIcon,
  MessageSquareIcon,
  MonitorIcon,
  MoreHorizontalIcon,
  PackageIcon,
  PlugIcon,
  TargetIcon,
  XIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/context/WorkspaceContext";

// ─────────────────────────────────────────────────────────────
// Nav items (same as AppNav)
// ─────────────────────────────────────────────────────────────

const PRIMARY_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboardIcon, label: "Home"    },
  { href: "/chat",      icon: MessageSquareIcon,   label: "Chat"    },
  { href: "/missions",  icon: TargetIcon,           label: "Missões" },
  { href: "/memory",    icon: BrainIcon,            label: "Memória" },
  { href: "/inbox",     icon: InboxIcon,            label: "Inbox"   },
];

const MORE_ITEMS = [
  { href: "/knowledge",   icon: BookOpenIcon, label: "Conhecimento" },
  { href: "/timeline",    icon: ActivityIcon, label: "Timeline"     },
  { href: "/artifacts",   icon: PackageIcon,  label: "Artifacts"    },
  { href: "/runtime",     icon: MonitorIcon,  label: "Runtime"      },
  { href: "/integrations",icon: PlugIcon,     label: "Integrações"  },
];

// ─────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────

export function MobileNav() {
  const pathname = usePathname();
  const { workspaces, current, setCurrent } = useWorkspace();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [wsOpen,    setWsOpen]    = useState(false);

  const isMoreActive = MORE_ITEMS.some((i) => pathname.startsWith(i.href));

  return (
    <>
      {/* ── Bottom nav bar ── */}
      <nav
        className={cn(
          "fixed bottom-0 inset-x-0 z-[var(--z-dock)]",
          "flex md:hidden",
          "border-t border-[var(--border-subtle)] bg-[var(--surface-raised)]",
          "pb-safe",
        )}
      >
        <div className="flex flex-1 items-center justify-around px-1 pt-1.5 pb-1">
          {PRIMARY_ITEMS.map(({ href, icon: Icon, label }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-xl px-1 py-2",
                  "transition-colors duration-fast active:scale-95",
                  active
                    ? "text-accent"
                    : "text-content-muted active:bg-[var(--surface-subtle)]",
                )}
              >
                <Icon
                  size={20}
                  strokeWidth={active ? 2.2 : 1.8}
                  className={active ? "text-accent" : undefined}
                />
                <span
                  className={cn(
                    "text-[10px] font-medium leading-none",
                    active ? "text-accent" : "text-content-muted",
                  )}
                >
                  {label}
                </span>
              </Link>
            );
          })}

          {/* More button */}
          <button
            onClick={() => setSheetOpen(true)}
            className={cn(
              "flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-xl px-1 py-2",
              "transition-colors duration-fast active:scale-95",
              isMoreActive ? "text-accent" : "text-content-muted",
            )}
          >
            {isMoreActive ? (
              <GridIcon size={20} strokeWidth={2.2} className="text-accent" />
            ) : (
              <MoreHorizontalIcon size={20} strokeWidth={1.8} />
            )}
            <span className="text-[10px] font-medium leading-none">Mais</span>
          </button>
        </div>
      </nav>

      {/* ── More sheet (slides up from bottom) ── */}
      {sheetOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-[var(--z-overlay)] bg-black/60 backdrop-blur-sm md:hidden animate-fade-in"
            onClick={() => setSheetOpen(false)}
          />

          {/* Sheet */}
          <div
            className={cn(
              "fixed inset-x-0 bottom-0 z-[var(--z-modal)] md:hidden",
              "rounded-t-2xl border-t border-[var(--border-default)]",
              "bg-[var(--surface-overlay)] pb-safe",
              "animate-slide-up",
            )}
          >
            {/* Handle + header */}
            <div className="flex items-center justify-between px-4 pb-2 pt-3">
              <div className="mx-auto h-1 w-10 rounded-full bg-[var(--border-strong)]" />
            </div>
            <div className="flex items-center justify-between px-4 pb-3">
              <span className="text-[11px] font-semibold uppercase tracking-widest text-content-muted">
                Mais
              </span>
              <button
                onClick={() => setSheetOpen(false)}
                className="flex h-7 w-7 items-center justify-center rounded-lg text-content-muted hover:bg-[var(--surface-subtle)] transition-colors"
              >
                <XIcon size={14} />
              </button>
            </div>

            {/* Items grid */}
            <div className="grid grid-cols-3 gap-2 px-4 pb-4">
              {MORE_ITEMS.map(({ href, icon: Icon, label }) => {
                const active = pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setSheetOpen(false)}
                    className={cn(
                      "flex flex-col items-center gap-2 rounded-xl p-4",
                      "border border-[var(--border-subtle)]",
                      "transition-colors duration-fast active:scale-95",
                      active
                        ? "border-accent/30 bg-accent-dim text-accent"
                        : "bg-[var(--surface-raised)] text-content-secondary hover:border-[var(--border-default)]",
                    )}
                  >
                    <Icon size={22} strokeWidth={active ? 2.2 : 1.8} />
                    <span className="text-[11px] font-medium leading-none text-center">
                      {label}
                    </span>
                  </Link>
                );
              })}
            </div>

            {/* Workspace switcher */}
            <div className="border-t border-[var(--border-subtle)] px-4 pb-4 pt-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-content-muted">
                Workspace
              </p>
              <div className="flex flex-col gap-1">
                {workspaces.map((ws) => {
                  const isCurrent = current?.id === ws.id;
                  return (
                    <button
                      key={ws.id}
                      onClick={() => {
                        setCurrent(ws);
                        setWsOpen(false);
                        setSheetOpen(false);
                      }}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2.5",
                        "text-sm transition-colors duration-fast",
                        isCurrent
                          ? "bg-accent-dim text-accent"
                          : "text-content-secondary hover:bg-[var(--surface-subtle)]",
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-6 w-6 shrink-0 items-center justify-center rounded text-[11px] font-bold",
                          isCurrent
                            ? "bg-accent text-white"
                            : "bg-[var(--surface-subtle)] text-content-muted",
                        )}
                      >
                        {ws.name[0].toUpperCase()}
                      </span>
                      <span className="flex-1 truncate font-medium">{ws.name}</span>
                      {isCurrent && (
                        <CheckIcon size={14} className="shrink-0 text-accent" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
