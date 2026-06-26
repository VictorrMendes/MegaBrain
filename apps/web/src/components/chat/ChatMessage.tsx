import { cn } from "@/lib/cn";

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  statusHint?: string;
}

interface ChatMessageProps {
  message: ChatMessageData;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-neutral-700 text-neutral-100 rounded-br-sm"
            : "bg-neutral-900 border border-neutral-800 text-neutral-200 rounded-bl-sm"
        )}
      >
        {/* Status hint shown while streaming, before text arrives */}
        {message.streaming && message.statusHint && !message.content && (
          <p className="text-xs text-neutral-500 italic">{message.statusHint}</p>
        )}

        {message.content && (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        )}

        {message.streaming && message.content && (
          <span className="inline-block w-1.5 h-4 bg-neutral-400 ml-0.5 animate-pulse rounded-sm" />
        )}
      </div>
    </div>
  );
}
