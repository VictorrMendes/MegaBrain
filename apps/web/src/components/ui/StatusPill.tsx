import { cn } from "@/lib/cn";

type PillStatus = "online" | "offline" | "degraded" | "loading" | "idle";

interface StatusPillProps {
  status:     PillStatus;
  label?:     string;
  pulse?:     boolean;
  className?: string;
  size?:      "sm" | "md";
}

const DOT_COLOR: Record<PillStatus, string> = {
  online:   "bg-status-success",
  offline:  "bg-status-error",
  degraded: "bg-status-warning",
  loading:  "bg-status-info animate-pulse-dot",
  idle:     "bg-content-muted",
};

const LABEL_COLOR: Record<PillStatus, string> = {
  online:   "text-status-success",
  offline:  "text-status-error",
  degraded: "text-status-warning",
  loading:  "text-status-info",
  idle:     "text-content-muted",
};

export function StatusPill({
  status,
  label,
  pulse = true,
  className,
  size = "sm",
}: StatusPillProps) {
  const dotSize = size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5",
        className,
      )}
    >
      <span className="relative inline-flex">
        <span className={cn("rounded-full", dotSize, DOT_COLOR[status])} />
        {pulse && status === "online" && (
          <span
            className={cn(
              "absolute inset-0 rounded-full animate-ping opacity-40",
              DOT_COLOR[status],
            )}
          />
        )}
      </span>
      {label && (
        <span
          className={cn(
            "tabular-nums",
            size === "sm" ? "text-2xs" : "text-xs",
            LABEL_COLOR[status],
          )}
        >
          {label}
        </span>
      )}
    </span>
  );
}
