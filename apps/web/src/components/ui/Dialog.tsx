"use client";

import * as RadixDialog from "@radix-ui/react-dialog";
import { XIcon } from "lucide-react";
import { cn } from "@/lib/cn";

// ─── Root ──────────────────────────────────────────────────────────────────────

export const Dialog       = RadixDialog.Root;
export const DialogTrigger = RadixDialog.Trigger;

// ─── Portal wrapper ───────────────────────────────────────────────────────────

interface DialogContentProps {
  children:   React.ReactNode;
  className?: string;
  size?:      "sm" | "md" | "lg" | "xl" | "full";
  title?:     string;
  description?: string;
  onClose?:   () => void;
}

const SIZE = {
  sm:   "max-w-sm",
  md:   "max-w-lg",
  lg:   "max-w-2xl",
  xl:   "max-w-4xl",
  full: "max-w-[90vw]",
};

export function DialogContent({
  children,
  className,
  size = "md",
  title,
  description,
  onClose,
}: DialogContentProps) {
  return (
    <RadixDialog.Portal>
      {/* Overlay */}
      <RadixDialog.Overlay
        className={cn(
          "fixed inset-0 bg-black/65 backdrop-blur-sm",
          "z-modal animate-fade-in",
        )}
      />

      {/* Content */}
      <RadixDialog.Content
        className={cn(
          "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2",
          "w-full rounded-xl border border-[var(--border-default)]",
          "bg-surface-overlay shadow-xl",
          "z-modal animate-scale-in-spring",
          "focus:outline-none",
          SIZE[size],
          className,
        )}
      >
        {/* Header */}
        {(title || onClose) && (
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-5 py-4">
            <div>
              {title && (
                <RadixDialog.Title className="text-md font-semibold text-content-primary">
                  {title}
                </RadixDialog.Title>
              )}
              {description && (
                <RadixDialog.Description className="mt-0.5 text-xs text-content-muted">
                  {description}
                </RadixDialog.Description>
              )}
            </div>
            {onClose && (
              <RadixDialog.Close
                onClick={onClose}
                className={cn(
                  "rounded-md p-1.5 text-content-muted",
                  "hover:bg-surface-subtle hover:text-content-primary",
                  "transition-colors duration-fast",
                )}
              >
                <XIcon size={15} />
              </RadixDialog.Close>
            )}
          </div>
        )}

        {/* Body */}
        <div className="p-5">{children}</div>
      </RadixDialog.Content>
    </RadixDialog.Portal>
  );
}

// ─── Footer helper ────────────────────────────────────────────────────────────

export function DialogFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-2",
        "border-t border-[var(--border-subtle)] px-5 py-4 -mx-5 -mb-5 mt-4 rounded-b-xl",
        className,
      )}
    >
      {children}
    </div>
  );
}
