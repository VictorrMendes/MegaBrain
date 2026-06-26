"use client";

import * as RadixTabs from "@radix-ui/react-tabs";
import { cn } from "@/lib/cn";

// ─── Root ────────────────────────────────────────────────────────────────────

interface TabsProps {
  defaultValue?: string;
  value?:        string;
  onValueChange?:(value: string) => void;
  children:      React.ReactNode;
  className?:    string;
}

export function Tabs({ children, className, ...props }: TabsProps) {
  return (
    <RadixTabs.Root className={cn("flex flex-col", className)} {...props}>
      {children}
    </RadixTabs.Root>
  );
}

// ─── List ─────────────────────────────────────────────────────────────────────

interface TabsListProps {
  children:   React.ReactNode;
  className?: string;
  variant?:   "underline" | "pills" | "segment";
}

export function TabsList({ children, className, variant = "underline" }: TabsListProps) {
  return (
    <RadixTabs.List
      className={cn(
        "flex items-center",
        variant === "underline" && "gap-0 border-b border-[var(--border-subtle)]",
        variant === "pills"     && "gap-1.5",
        variant === "segment"   && "gap-0.5 rounded-lg bg-surface-subtle p-1",
        className,
      )}
    >
      {children}
    </RadixTabs.List>
  );
}

// ─── Trigger ──────────────────────────────────────────────────────────────────

interface TabsTriggerProps {
  value:      string;
  children:   React.ReactNode;
  className?: string;
  variant?:   "underline" | "pills" | "segment";
  icon?:      React.ReactNode;
  count?:     number;
}

export function TabsTrigger({
  value, children, className, variant = "underline", icon, count,
}: TabsTriggerProps) {
  return (
    <RadixTabs.Trigger
      value={value}
      className={cn(
        "flex items-center gap-1.5 text-sm transition-colors duration-fast",
        "focus-visible:outline-none",

        variant === "underline" && [
          "relative px-3 py-2 text-content-muted hover:text-content-secondary",
          "data-[state=active]:text-content-primary",
          "after:absolute after:bottom-0 after:left-0 after:right-0 after:h-px",
          "after:transition-colors after:duration-fast",
          "data-[state=active]:after:bg-accent after:bg-transparent",
        ],

        variant === "pills" && [
          "rounded-full border px-3 py-1 font-medium",
          "text-content-secondary border-transparent",
          "hover:border-[var(--border-subtle)] hover:text-content-primary",
          "data-[state=active]:bg-accent-dim data-[state=active]:border-accent-subtle data-[state=active]:text-accent",
        ],

        variant === "segment" && [
          "rounded-md px-3 py-1.5 font-medium text-content-muted",
          "hover:text-content-primary",
          "data-[state=active]:bg-surface-overlay data-[state=active]:text-content-primary data-[state=active]:shadow-sm",
        ],

        className,
      )}
    >
      {icon && <span className="opacity-75">{icon}</span>}
      {children}
      {count !== undefined && (
        <span
          className={cn(
            "rounded px-1 text-2xs transition-colors",
            "data-[active]:bg-accent/20 data-[active]:text-accent text-content-muted",
          )}
        >
          {count}
        </span>
      )}
    </RadixTabs.Trigger>
  );
}

// ─── Content ──────────────────────────────────────────────────────────────────

interface TabsContentProps {
  value:      string;
  children:   React.ReactNode;
  className?: string;
}

export function TabsContent({ value, children, className }: TabsContentProps) {
  return (
    <RadixTabs.Content
      value={value}
      className={cn("flex-1 animate-fade-in focus-visible:outline-none", className)}
    >
      {children}
    </RadixTabs.Content>
  );
}
