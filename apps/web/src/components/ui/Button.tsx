"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size    = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?:    Size;
  loading?: boolean;
}

const variantCls: Record<Variant, string> = {
  primary:
    "bg-accent text-white border border-transparent " +
    "hover:bg-accent-hover",
  secondary:
    "bg-surface-overlay text-content-primary border border-border-default " +
    "hover:border-border-strong hover:bg-surface-subtle",
  ghost:
    "bg-transparent text-content-secondary border border-transparent " +
    "hover:bg-surface-subtle hover:text-content-primary",
  danger:
    "bg-transparent text-status-error border border-transparent " +
    "hover:bg-red-950/60 hover:border-red-900/40",
};

const sizeCls: Record<Size, string> = {
  sm: "h-6  px-2.5 text-xs rounded gap-1.5",
  md: "h-8  px-3   text-sm rounded-md gap-2",
  lg: "h-10 px-4   text-md rounded-lg gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = "secondary", size = "md", loading, disabled, className, children, ...rest },
    ref,
  ) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex shrink-0 items-center justify-center font-medium",
        "transition-colors duration-[100ms] select-none",
        "disabled:pointer-events-none disabled:opacity-40",
        variantCls[variant],
        sizeCls[size],
        className,
      )}
      {...rest}
    >
      {loading ? <InlineSpinner /> : children}
    </button>
  ),
);
Button.displayName = "Button";

function InlineSpinner() {
  return (
    <svg
      width={13} height={13} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
      className="animate-spin"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}
