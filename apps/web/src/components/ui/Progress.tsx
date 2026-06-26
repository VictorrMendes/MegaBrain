import * as RadixProgress from "@radix-ui/react-progress";
import { cn } from "@/lib/cn";

type ProgressVariant = "default" | "success" | "warning" | "error" | "accent";

interface ProgressProps {
  value?:     number;   // 0-100
  max?:       number;
  variant?:   ProgressVariant;
  size?:      "xs" | "sm" | "md";
  animated?:  boolean;
  className?: string;
  label?:     string;
}

const TRACK_H = {
  xs: "h-0.5",
  sm: "h-1",
  md: "h-1.5",
};

const FILL_COLOR: Record<ProgressVariant, string> = {
  default: "bg-content-muted",
  success: "bg-status-success",
  warning: "bg-status-warning",
  error:   "bg-status-error",
  accent:  "bg-accent",
};

export function Progress({
  value = 0,
  max = 100,
  variant = "accent",
  size = "sm",
  animated = false,
  className,
  label,
}: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn("w-full", className)}>
      <RadixProgress.Root
        value={value}
        max={max}
        className={cn(
          "relative overflow-hidden rounded-full bg-surface-subtle",
          TRACK_H[size],
        )}
      >
        <RadixProgress.Indicator
          className={cn(
            "h-full rounded-full transition-all",
            animated && "animate-shimmer bg-[length:400px_100%]",
            FILL_COLOR[variant],
          )}
          style={{ transform: `translateX(-${100 - pct}%)` }}
        />
      </RadixProgress.Root>
      {label && (
        <span className="mt-1 block text-2xs text-content-muted">{label}</span>
      )}
    </div>
  );
}
