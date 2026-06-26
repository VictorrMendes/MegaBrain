import { forwardRef } from "react";
import { cn } from "@/lib/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  leftIcon?:  React.ReactNode;
  rightIcon?: React.ReactNode;
  error?:     boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, leftIcon, rightIcon, error, disabled, ...props }, ref) => {
    return (
      <div className="relative flex items-center">
        {leftIcon && (
          <span className="pointer-events-none absolute left-3 text-content-muted">
            {leftIcon}
          </span>
        )}
        <input
          ref={ref}
          disabled={disabled}
          className={cn(
            "w-full rounded-md border bg-surface-raised px-3 py-2",
            "text-sm text-content-primary placeholder:text-content-placeholder",
            "transition-colors duration-fast",
            "focus:outline-none focus:border-border-accent focus:ring-1 focus:ring-[var(--border-accent)]",
            "disabled:cursor-not-allowed disabled:opacity-40",
            error
              ? "border-status-error focus:border-status-error focus:ring-[rgba(239,68,68,0.25)]"
              : "border-[var(--border-default)] hover:border-[var(--border-strong)]",
            leftIcon  && "pl-9",
            rightIcon && "pr-9",
            className,
          )}
          {...props}
        />
        {rightIcon && (
          <span className="pointer-events-none absolute right-3 text-content-muted">
            {rightIcon}
          </span>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
