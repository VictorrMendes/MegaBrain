import * as RadixSeparator from "@radix-ui/react-separator";
import { cn } from "@/lib/cn";

interface SeparatorProps {
  orientation?: "horizontal" | "vertical";
  className?:   string;
  decorative?:  boolean;
}

export function Separator({
  orientation = "horizontal",
  className,
  decorative = true,
}: SeparatorProps) {
  return (
    <RadixSeparator.Root
      decorative={decorative}
      orientation={orientation}
      className={cn(
        "shrink-0 bg-[var(--border-subtle)]",
        orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
        className,
      )}
    />
  );
}
