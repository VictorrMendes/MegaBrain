"use client";

import { type KeyboardEvent, useRef, useState } from "react";
import { ArrowUpIcon, Loader2Icon } from "lucide-react";
import { cn } from "@/lib/cn";

interface ChatInputProps {
  onSend:     (message: string) => void;
  disabled?:  boolean;
  streaming?: boolean;
}

export function ChatInput({ onSend, disabled, streaming }: ChatInputProps) {
  const [value, setValue]   = useState("");
  const textareaRef         = useRef<HTMLTextAreaElement>(null);

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
            "flex items-end gap-3 rounded-xl px-4 py-3 transition-colors",
            "border bg-[var(--surface-raised)]",
            streaming
              ? "border-accent/30 bg-accent-subtle"
              : "border-[var(--border-default)] focus-within:border-[var(--border-accent)]",
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={streaming ? "Aguarde a resposta…" : "Mensagem…"}
            rows={1}
            disabled={disabled}
            className={cn(
              "flex-1 resize-none bg-transparent text-sm text-content-primary",
              "placeholder:text-content-placeholder focus:outline-none leading-relaxed",
              "disabled:opacity-40 disabled:cursor-not-allowed overflow-hidden",
            )}
          />

          <button
            onClick={handleSend}
            disabled={!canSend}
            className={cn(
              "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition-colors",
              canSend
                ? "bg-accent text-white hover:bg-accent-hover"
                : "bg-[var(--surface-subtle)] text-content-muted cursor-not-allowed",
            )}
          >
            {streaming
              ? <Loader2Icon size={13} className="animate-spin text-accent" />
              : <ArrowUpIcon size={14} strokeWidth={2.5} />}
          </button>
        </div>

        <p className="mt-2 text-center text-[11px] text-content-muted">
          {streaming ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-accent animate-pulse" />
              IA processando…
            </span>
          ) : (
            "Enter para enviar · Shift+Enter para nova linha · Ctrl+K para busca"
          )}
        </p>
      </div>
    </div>
  );
}
