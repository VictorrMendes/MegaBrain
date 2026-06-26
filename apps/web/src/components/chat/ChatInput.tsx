"use client";

import { type KeyboardEvent, useRef, useState } from "react";
import { ArrowUpIcon } from "lucide-react";
import { cn } from "@/lib/cn";

interface ChatInputProps {
  onSend:    (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue]     = useState("");
  const textareaRef           = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  const canSend = Boolean(value.trim()) && !disabled;

  return (
    <div className="border-t border-[var(--border-subtle)] bg-[var(--surface-base)] px-5 py-4">
      <div className="mx-auto max-w-3xl">
        <div
          className={cn(
            "flex items-end gap-3 rounded-xl",
            "border border-[var(--border-default)] bg-[var(--surface-raised)]",
            "px-4 py-3",
            "focus-within:border-[var(--border-accent)]",
            "transition-colors",
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder="Mensagem…"
            rows={1}
            disabled={disabled}
            className={cn(
              "flex-1 resize-none bg-transparent text-sm text-content-primary",
              "placeholder:text-content-placeholder",
              "focus:outline-none",
              "disabled:opacity-40 disabled:cursor-not-allowed",
              "overflow-hidden leading-relaxed",
            )}
          />

          <button
            onClick={handleSend}
            disabled={!canSend}
            className={cn(
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
              "transition-colors",
              canSend
                ? "bg-accent text-white hover:bg-accent-hover"
                : "bg-[var(--surface-subtle)] text-content-muted cursor-not-allowed",
            )}
          >
            <ArrowUpIcon size={14} strokeWidth={2.5} />
          </button>
        </div>

        <p className="mt-2 text-center text-[11px] text-content-muted">
          Enter para enviar · Shift+Enter para nova linha · Ctrl+K para busca
        </p>
      </div>
    </div>
  );
}
