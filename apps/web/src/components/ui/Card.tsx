"use client";

import { cn } from "@/lib/cn";

interface CardProps {
  children:  React.ReactNode;
  className?: string;
  onClick?:  () => void;
  padding?:  "none" | "sm" | "md" | "lg";
  variant?:  "default" | "raised" | "ghost";
}

const paddingCls = {
  none: "",
  sm:   "p-3",
  md:   "p-4",
  lg:   "p-5",
} as const;

const variantCls = {
  default: "bg-surface-raised  border border-border-subtle",
  raised:  "bg-surface-overlay border border-border-default",
  ghost:   "bg-transparent     border border-transparent",
} as const;

export function Card({
  children,
  className,
  onClick,
  padding = "md",
  variant = "default",
}: CardProps) {
  const interactive = Boolean(onClick);
  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-lg",
        paddingCls[padding],
        variantCls[variant],
        interactive &&
          "cursor-pointer transition-colors hover:border-border-default hover:bg-surface-overlay",
        className,
      )}
    >
      {children}
    </div>
  );
}
