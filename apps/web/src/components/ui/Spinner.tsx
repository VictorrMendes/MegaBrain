"use client";

import { cn } from "@/lib/cn";

interface SpinnerProps {
  size?:      "sm" | "md" | "lg";
  className?: string;
}

const sizePx: Record<NonNullable<SpinnerProps["size"]>, number> = {
  sm: 14,
  md: 18,
  lg: 22,
};

export function Spinner({ size = "md", className }: SpinnerProps) {
  const s = sizePx[size];
  return (
    <svg
      width={s} height={s} viewBox="0 0 24 24"
      fill="none" stroke="currentColor"
      strokeWidth="2.5" strokeLinecap="round"
      className={cn("animate-spin text-content-muted", className)}
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}
