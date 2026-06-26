"use client";

import { cn } from "@/lib/cn";

interface SkeletonProps {
  className?: string;
  variant?:   "rect" | "line" | "circle";
}

export function Skeleton({ className, variant = "rect" }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse bg-surface-subtle",
        variant === "circle" && "rounded-full",
        variant === "line"   && "rounded h-3",
        variant === "rect"   && "rounded-md",
        className,
      )}
    />
  );
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton
          key={i}
          variant="line"
          className={i === lines - 1 ? "w-2/3" : "w-full"}
        />
      ))}
    </div>
  );
}
