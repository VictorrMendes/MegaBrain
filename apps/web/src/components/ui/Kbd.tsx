import { cn } from "@/lib/cn";

interface KbdProps {
  children:  React.ReactNode;
  className?: string;
}

export function Kbd({ children, className }: KbdProps) {
  return (
    <kbd
      className={cn(
        "inline-flex items-center justify-center",
        "rounded border border-[var(--border-default)] bg-surface-subtle",
        "px-1.5 py-0.5 font-mono text-2xs text-content-muted",
        "shadow-xs select-none",
        className,
      )}
    >
      {children}
    </kbd>
  );
}
