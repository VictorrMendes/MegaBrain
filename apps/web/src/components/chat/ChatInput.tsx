"use client";

import { KeyboardEvent, useRef, useState } from "react";
import { SendIcon } from "lucide-react";
import { cn } from "@/lib/cn";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  return (
    <div className="border-t border-neutral-800 bg-neutral-950 p-4">
      <div className="mx-auto max-w-3xl flex items-end gap-3">
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
            "flex-1 resize-none rounded-lg border border-neutral-700 bg-neutral-900",
            "px-4 py-3 text-sm text-neutral-100 placeholder-neutral-500",
            "focus:outline-none focus:border-neutral-500",
            "disabled:opacity-40 disabled:cursor-not-allowed",
            "transition-colors overflow-hidden"
          )}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            "bg-neutral-100 text-neutral-900 transition-colors",
            "hover:bg-white",
            "disabled:opacity-30 disabled:cursor-not-allowed"
          )}
        >
          <SendIcon size={16} />
        </button>
      </div>
    </div>
  );
}
