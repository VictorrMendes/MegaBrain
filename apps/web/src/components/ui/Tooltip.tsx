"use client";

import * as RadixTooltip from "@radix-ui/react-tooltip";
import { cn } from "@/lib/cn";

interface TooltipProps {
  content:    React.ReactNode;
  children:   React.ReactNode;
  side?:      "top" | "bottom" | "left" | "right";
  align?:     "start" | "center" | "end";
  delayMs?:   number;
  className?: string;
}

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return (
    <RadixTooltip.Provider delayDuration={400} skipDelayDuration={100}>
      {children}
    </RadixTooltip.Provider>
  );
}

export function Tooltip({
  content,
  children,
  side = "top",
  align = "center",
  delayMs = 400,
  className,
}: TooltipProps) {
  return (
    <RadixTooltip.Root delayDuration={delayMs}>
      <RadixTooltip.Trigger asChild>
        {children}
      </RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          align={align}
          sideOffset={6}
          className={cn(
            "z-tooltip max-w-xs rounded-md px-2.5 py-1.5",
            "border border-[var(--border-default)] bg-surface-overlay",
            "text-xs text-content-primary shadow-md",
            "animate-scale-in",
            "select-none",
            className,
          )}
        >
          {content}
          <RadixTooltip.Arrow className="fill-[var(--surface-overlay)]" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
