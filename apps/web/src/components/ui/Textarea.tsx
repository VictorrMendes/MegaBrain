import { forwardRef } from "react";
import { cn } from "@/lib/cn";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, disabled, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        disabled={disabled}
        className={cn(
          "w-full resize-none rounded-md border bg-surface-raised px-3 py-2",
          "text-sm text-content-primary placeholder:text-content-placeholder",
          "transition-colors duration-fast",
          "focus:outline-none focus:border-border-accent focus:ring-1 focus:ring-[var(--border-accent)]",
          "disabled:cursor-not-allowed disabled:opacity-40",
          error
            ? "border-status-error focus:border-status-error focus:ring-[rgba(239,68,68,0.25)]"
            : "border-[var(--border-default)] hover:border-[var(--border-strong)]",
          className,
        )}
        {...props}
      />
    );
  },
);

Textarea.displayName = "Textarea";
