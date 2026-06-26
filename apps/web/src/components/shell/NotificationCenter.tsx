"use client";

import { useRef } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import {
  useNotifications,
  type Notification,
  type NotificationKind,
  type NotificationPriority,
} from "@/context/NotificationContext";
import {
  BellIcon,
  BrainIcon,
  CheckCircle2Icon,
  CheckIcon,
  ClockIcon,
  FileTextIcon,
  InfoIcon,
  PackageIcon,
  PlugIcon,
  TargetIcon,
  TrashIcon,
  XCircleIcon,
  XIcon,
  ZapIcon,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function rel(date: Date): string {
  const diff = Date.now() - date.getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60)   return "agora";
  const m = Math.floor(s / 60);
  if (m < 60)   return `${m}m atrás`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `há ${h}h`;
  return         `há ${Math.floor(h / 24)}d`;
}

const KIND_ICON: Record<NotificationKind, React.ReactNode> = {
  mission_created:   <TargetIcon       size={13} className="text-status-active" />,
  mission_completed: <CheckCircle2Icon size={13} className="text-status-success" />,
  mission_failed:    <XCircleIcon      size={13} className="text-status-error" />,
  mission_waiting:   <ClockIcon        size={13} className="text-status-warning" />,
  memory_created:    <BrainIcon        size={13} className="text-status-success" />,
  document_indexed:  <FileTextIcon     size={13} className="text-status-info" />,
  scheduler_executed:<ZapIcon          size={13} className="text-status-warning" />,
  plugin_installed:  <PlugIcon         size={13} className="text-accent" />,
  briefing:          <PackageIcon      size={13} className="text-accent" />,
  system:            <InfoIcon         size={13} className="text-content-muted" />,
  info:              <InfoIcon         size={13} className="text-status-info" />,
};

const PRIORITY_DOT: Record<NotificationPriority, string> = {
  low:      "bg-content-muted",
  normal:   "bg-status-info",
  high:     "bg-status-warning",
  critical: "bg-status-error animate-pulse-dot",
};

// ─────────────────────────────────────────────────────────────
// Bell button (used by TopBar)
// ─────────────────────────────────────────────────────────────

interface BellProps {
  open:    boolean;
  onToggle:() => void;
}

export function NotificationBell({ open, onToggle }: BellProps) {
  const { unreadCount } = useNotifications();

  return (
    <button
      onClick={onToggle}
      aria-label="Notificações"
      className={cn(
        "relative rounded-md p-1.5 transition-colors duration-fast",
        "text-content-muted hover:text-content-primary hover:bg-surface-subtle",
        open && "bg-surface-subtle text-content-primary",
      )}
    >
      <BellIcon size={14} />
      {unreadCount > 0 && (
        <span
          className={cn(
            "absolute -right-0.5 -top-0.5",
            "flex h-4 w-4 items-center justify-center",
            "rounded-full bg-accent text-2xs text-white font-semibold",
            "animate-scale-in",
          )}
        >
          {unreadCount > 9 ? "9+" : unreadCount}
        </span>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Notification Center Panel
// ─────────────────────────────────────────────────────────────

interface NotificationCenterProps {
  open:    boolean;
  onClose: () => void;
}

export function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const { notifications, unreadCount, markRead, markAllRead, remove, clearAll } =
    useNotifications();
  const panelRef = useRef<HTMLDivElement>(null);

  if (!open) return null;

  return (
    <>
      {/* Backdrop (click outside to close) */}
      <div
        className="fixed inset-0 z-notification"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={cn(
          "fixed right-2 top-[44px] z-notification",
          "w-[360px] max-h-[calc(100vh-60px)]",
          "flex flex-col overflow-hidden",
          "rounded-xl border border-[var(--border-default)]",
          "bg-surface-overlay shadow-xl",
          "animate-slide-down",
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-content-primary">Notificações</span>
            {unreadCount > 0 && (
              <span className="rounded-full bg-accent px-1.5 py-0.5 text-2xs text-white font-semibold">
                {unreadCount}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                title="Marcar tudo como lido"
                className="rounded p-1 text-2xs text-content-muted hover:text-content-primary hover:bg-surface-subtle transition-colors"
              >
                <CheckIcon size={12} />
              </button>
            )}
            {notifications.length > 0 && (
              <button
                onClick={clearAll}
                title="Limpar tudo"
                className="rounded p-1 text-content-muted hover:text-status-error hover:bg-surface-subtle transition-colors"
              >
                <TrashIcon size={12} />
              </button>
            )}
            <button
              onClick={onClose}
              className="rounded p-1 text-content-muted hover:text-content-primary hover:bg-surface-subtle transition-colors"
            >
              <XIcon size={13} />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <BellIcon size={20} className="text-content-muted opacity-40" />
              <p className="text-xs text-content-muted">Nenhuma notificação</p>
            </div>
          ) : (
            <ul className="py-1">
              {notifications.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onRead={() => markRead(n.id)}
                  onRemove={() => remove(n.id)}
                  onClose={onClose}
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// Item
// ─────────────────────────────────────────────────────────────

function NotificationItem({
  notification: n,
  onRead,
  onRemove,
  onClose,
}: {
  notification: Notification;
  onRead:       () => void;
  onRemove:     () => void;
  onClose:      () => void;
}) {
  const inner = (
    <div
      className={cn(
        "group relative flex items-start gap-3 px-4 py-3",
        "transition-colors duration-fast cursor-pointer",
        !n.read
          ? "bg-accent-subtle hover:bg-[var(--surface-subtle)]"
          : "hover:bg-surface-raised",
      )}
      onClick={onRead}
    >
      {/* Priority dot */}
      <span
        className={cn(
          "mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
          PRIORITY_DOT[n.priority],
        )}
      />

      {/* Kind icon */}
      <span className="mt-0.5 shrink-0">{KIND_ICON[n.kind]}</span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-xs leading-snug",
            n.read ? "text-content-secondary" : "text-content-primary font-medium",
          )}
        >
          {n.title}
        </p>
        {n.body && (
          <p className="mt-0.5 text-2xs text-content-muted line-clamp-2">{n.body}</p>
        )}
        <div className="mt-1 flex items-center gap-2">
          <span className="text-2xs text-content-muted">{n.source}</span>
          <span className="text-2xs text-content-muted">·</span>
          <span className="text-2xs text-content-muted tabular-nums">{rel(n.timestamp)}</span>
        </div>
      </div>

      {/* Remove button */}
      <button
        onClick={(e) => { e.stopPropagation(); onRemove(); }}
        className="shrink-0 rounded p-0.5 text-content-muted opacity-0 group-hover:opacity-100 hover:text-status-error transition-all"
      >
        <XIcon size={11} />
      </button>
    </div>
  );

  if (n.href) {
    return (
      <li>
        <Link href={n.href} onClick={onClose}>
          {inner}
        </Link>
      </li>
    );
  }

  return <li>{inner}</li>;
}
