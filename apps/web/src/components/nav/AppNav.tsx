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
  ChevronUpDownIcon,
  CheckIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/context/WorkspaceContext";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboardIcon, label: "Dashboard" },
  { href: "/chat",      icon: MessageSquareIcon,  label: "Chat"        },
  { href: "/missions",  icon: TargetIcon,          label: "Missões"     },
  { href: "/memory",    icon: BrainIcon,           label: "Memória"     },
  { href: "/knowledge", icon: BookOpenIcon,        label: "Conhecimento"},
  { href: "/inbox",     icon: InboxIcon,           label: "Inbox"       },
  { href: "/timeline",  icon: ActivityIcon,        label: "Timeline"    },
  { href: "/artifacts", icon: PackageIcon,         label: "Artifacts"   },
  { href: "/runtime",   icon: MonitorIcon,         label: "Runtime"     },
];

export function AppNav() {
  const pathname = usePathname();
  const { workspaces, current, setCurrent } = useWorkspace();
  const [showSwitcher, setShowSwitcher] = useState(false);

  const initial = current?.name?.[0]?.toUpperCase() ?? "?";

  return (
    <nav className="relative flex w-12 shrink-0 flex-col items-center border-r border-neutral-800 bg-neutral-900 py-3 gap-1">
      {/* Logo */}
      <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-700 text-xs font-bold text-neutral-200 tracking-widest select-none">
        K
      </div>

      {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            title={label}
            className={cn(
              "group relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors",
              active
                ? "bg-neutral-700 text-neutral-100"
                : "text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300"
            )}
          >
            <Icon size={17} />
            <span className="pointer-events-none absolute left-full ml-2 z-50 hidden whitespace-nowrap rounded-md bg-neutral-800 px-2 py-1 text-xs text-neutral-200 shadow-lg group-hover:block">
              {label}
            </span>
          </Link>
        );
      })}

      {/* Workspace switcher at bottom */}
      <div className="mt-auto">
        <button
          title={current?.name ?? "Workspace"}
          onClick={() => setShowSwitcher((v) => !v)}
          className="group relative flex h-9 w-9 items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300 transition-colors"
        >
          <span className="text-[11px] font-bold">{initial}</span>
          <ChevronUpDownIcon size={9} className="absolute bottom-1 right-1 opacity-50" />
          <span className="pointer-events-none absolute left-full ml-2 z-50 hidden whitespace-nowrap rounded-md bg-neutral-800 px-2 py-1 text-xs text-neutral-200 shadow-lg group-hover:block">
            {current?.name ?? "Workspace"}
          </span>
        </button>
      </div>

      {/* Workspace dropdown */}
      {showSwitcher && workspaces.length > 0 && (
        <div
          className="absolute bottom-2 left-full ml-2 z-50 min-w-48 rounded-xl border border-neutral-700 bg-neutral-900 py-1 shadow-2xl"
          onMouseLeave={() => setShowSwitcher(false)}
        >
          <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-neutral-600">
            Workspaces
          </p>
          {workspaces.map((ws) => (
            <button
              key={ws.id}
              onClick={() => { setCurrent(ws); setShowSwitcher(false); }}
              className={cn(
                "flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors",
                current?.id === ws.id
                  ? "text-neutral-200"
                  : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800"
              )}
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-neutral-700 text-[10px] font-bold text-neutral-300">
                {ws.name[0].toUpperCase()}
              </span>
              <span className="flex-1 truncate">{ws.name}</span>
              {current?.id === ws.id && (
                <CheckIcon size={11} className="shrink-0 text-emerald-400" />
              )}
            </button>
          ))}
        </div>
      )}
    </nav>
  );
}
