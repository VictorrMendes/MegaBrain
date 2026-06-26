"use client";

import { useEffect, useRef } from "react";
import { SparklesIcon } from "lucide-react";
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
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-dim shadow-glow-sm">
          <SparklesIcon size={22} className="text-accent" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-content-secondary">Intelligence Lab</p>
          <p className="mt-1 text-xs text-content-muted max-w-xs">
            Cada resposta acessa memória, conhecimento e documentos automaticamente.
            O pipeline cognitivo é exibido em tempo real.
          </p>
        </div>
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
