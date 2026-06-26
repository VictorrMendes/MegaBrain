import { cn } from "@/lib/cn";

export interface ContextUsed {
  memory:    number;
  knowledge: number;
  chunks:    number;
}

export interface ChatMessageData {
  id:           string;
  role:         "user" | "assistant";
  content:      string;
  streaming?:   boolean;
  streamPhase?: "thinking" | "reading" | "writing" | null;
  contextUsed?: ContextUsed;
}

interface ChatMessageProps {
  message: ChatMessageData;
  onContextClick?: () => void;
}

export function ChatMessage({ message, onContextClick }: ChatMessageProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className={cn(
            "max-w-[72%] rounded-xl rounded-br-sm px-4 py-3",
            "bg-[var(--surface-subtle)] border border-[var(--border-default)]",
            "text-sm text-content-primary leading-relaxed",
          )}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-start gap-3">
        {/* Avatar dot */}
        <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-dim">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
        </span>

        <div className="flex-1 min-w-0">
          {/* Streaming phases */}
          {message.streaming && message.streamPhase !== "writing" && (
            <StreamingIndicator phase={message.streamPhase ?? "thinking"} contextUsed={message.contextUsed} />
          )}

          {/* Content */}
          {message.content && (
            <p className="text-sm text-content-primary leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
              {message.streaming && message.streamPhase === "writing" && (
                <span className="inline-block w-0.5 h-4 bg-accent ml-0.5 animate-pulse align-text-bottom" />
              )}
            </p>
          )}
        </div>
      </div>

      {/* Context used badge — shown after streaming completes */}
      {!message.streaming && message.contextUsed && hasContext(message.contextUsed) && (
        <ContextBadge contextUsed={message.contextUsed} onClick={onContextClick} />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────

function hasContext(ctx: ContextUsed): boolean {
  return ctx.memory > 0 || ctx.knowledge > 0 || ctx.chunks > 0;
}

function StreamingIndicator({
  phase,
  contextUsed,
}: {
  phase: "thinking" | "reading";
  contextUsed?: ContextUsed;
}) {
  if (phase === "thinking") {
    return (
      <div className="flex items-center gap-2 py-1">
        <ThinkingDots />
        <span className="text-xs text-content-muted">Pensando</span>
      </div>
    );
  }

  // reading phase
  const parts: string[] = [];
  if (contextUsed?.memory)    parts.push(`${contextUsed.memory} memória${contextUsed.memory !== 1 ? "s" : ""}`);
  if (contextUsed?.knowledge) parts.push(`${contextUsed.knowledge} fato${contextUsed.knowledge !== 1 ? "s" : ""}`);
  if (contextUsed?.chunks)    parts.push(`${contextUsed.chunks} trecho${contextUsed.chunks !== 1 ? "s" : ""}`);

  return (
    <div className="flex items-center gap-2 py-1">
      <span className="h-3 w-3 rounded-full border border-accent-hover animate-pulse-dot" />
      <span className="text-xs text-content-secondary">
        Lendo {parts.length > 0 ? parts.join(" · ") : "contexto"}…
      </span>
    </div>
  );
}

function ThinkingDots() {
  return (
    <span className="flex items-center gap-[3px]">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-content-muted"
          style={{
            animation: "pulse-dot 1.4s ease-in-out infinite",
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </span>
  );
}

function ContextBadge({
  contextUsed,
  onClick,
}: {
  contextUsed: ContextUsed;
  onClick?: () => void;
}) {
  const parts: string[] = [];
  if (contextUsed.memory)    parts.push(`${contextUsed.memory} mem.`);
  if (contextUsed.knowledge) parts.push(`${contextUsed.knowledge} fatos`);
  if (contextUsed.chunks)    parts.push(`${contextUsed.chunks} docs`);

  return (
    <button
      onClick={onClick}
      className={cn(
        "ml-8 inline-flex items-center gap-1 text-[11px] text-content-muted",
        "hover:text-content-secondary transition-colors",
        onClick && "cursor-pointer",
      )}
    >
      <span className="h-1 w-1 rounded-full bg-content-muted" />
      {parts.join(" · ")}
    </button>
  );
}
