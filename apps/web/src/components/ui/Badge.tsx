"use client";

import { cn } from "@/lib/cn";

export type BadgeVariant =
  | "default"
  | "success"
  | "warning"
  | "error"
  | "info"
  | "active"
  | "muted";

interface BadgeProps {
  variant?:  BadgeVariant;
  size?:     "sm" | "md";
  children:  React.ReactNode;
  className?: string;
}

const variantCls: Record<BadgeVariant, string> = {
  default: "bg-surface-overlay text-content-secondary border border-border-default",
  success: "bg-emerald-950/60 text-status-success  border border-emerald-900/30",
  warning: "bg-amber-950/60  text-status-warning   border border-amber-900/30",
  error:   "bg-red-950/60    text-status-error     border border-red-900/30",
  info:    "bg-blue-950/60   text-status-info      border border-blue-900/30",
  active:  "bg-violet-950/60 text-status-active    border border-violet-900/30",
  muted:   "text-content-muted border border-transparent",
};

export function Badge({
  variant = "default",
  size    = "sm",
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center font-medium whitespace-nowrap",
        size === "sm"
          ? "h-4 rounded px-1.5 text-[10px]"
          : "h-5 rounded-md px-2 text-xs",
        variantCls[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
