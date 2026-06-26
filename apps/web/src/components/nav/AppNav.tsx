"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquareIcon,
  TargetIcon,
  BrainIcon,
  BookOpenIcon,
  InboxIcon,
  ActivityIcon,
  MonitorIcon,
  PackageIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";

const NAV_ITEMS = [
  { href: "/chat",      icon: MessageSquareIcon, label: "Chat"       },
  { href: "/missions",  icon: TargetIcon,         label: "Missões"    },
  { href: "/memory",    icon: BrainIcon,          label: "Memória"    },
  { href: "/knowledge", icon: BookOpenIcon,       label: "Conhecimento" },
  { href: "/inbox",     icon: InboxIcon,          label: "Inbox"      },
  { href: "/timeline",  icon: ActivityIcon,       label: "Timeline"   },
  { href: "/artifacts", icon: PackageIcon,        label: "Artifacts"  },
  { href: "/runtime",   icon: MonitorIcon,        label: "Runtime"    },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="flex w-12 shrink-0 flex-col items-center border-r border-neutral-800 bg-neutral-900 py-3 gap-1">
      {/* Logo mark */}
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
            {/* Tooltip */}
            <span className="pointer-events-none absolute left-full ml-2 z-50 hidden whitespace-nowrap rounded-md bg-neutral-800 px-2 py-1 text-xs text-neutral-200 shadow-lg group-hover:block">
              {label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
