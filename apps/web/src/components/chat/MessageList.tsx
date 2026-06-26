"use client";

import { useEffect, useRef } from "react";
import { ChatMessage, type ChatMessageData } from "./ChatMessage";

interface MessageListProps {
  messages:        ChatMessageData[];
  onContextClick?: (msgId: string) => void;
}

export function MessageList({ messages, onContextClick }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent-dim">
          <span className="h-3 w-3 rounded-full bg-accent" />
        </div>
        <p className="text-sm text-content-muted">Inicie uma conversa</p>
        <p className="text-xs text-content-placeholder">
          O PAIOS acessa sua memória e conhecimento automaticamente
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-5 py-6">
      <div className="mx-auto w-full max-w-3xl flex flex-col gap-5">
        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            onContextClick={
              msg.contextUsed && onContextClick
                ? () => onContextClick(msg.id)
                : undefined
            }
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
