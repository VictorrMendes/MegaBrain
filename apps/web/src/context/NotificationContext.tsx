"use client";

import {
  createContext, useCallback, useContext, useReducer,
} from "react";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export type NotificationPriority = "low" | "normal" | "high" | "critical";

export type NotificationKind =
  | "mission_created"
  | "mission_completed"
  | "mission_failed"
  | "mission_waiting"
  | "memory_created"
  | "document_indexed"
  | "scheduler_executed"
  | "plugin_installed"
  | "briefing"
  | "system"
  | "info";

export interface Notification {
  id:        string;
  kind:      NotificationKind;
  title:     string;
  body?:     string;
  priority:  NotificationPriority;
  source:    string;
  href?:     string;
  timestamp: Date;
  read:      boolean;
}

// ─────────────────────────────────────────────────────────────
// Reducer
// ─────────────────────────────────────────────────────────────

type Action =
  | { type: "ADD";        payload: Omit<Notification, "id" | "timestamp" | "read"> }
  | { type: "READ";       id: string }
  | { type: "READ_ALL" }
  | { type: "REMOVE";     id: string }
  | { type: "CLEAR_ALL" };

interface State {
  items: Notification[];
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "ADD":
      return {
        items: [
          {
            ...action.payload,
            id:        crypto.randomUUID(),
            timestamp: new Date(),
            read:      false,
          },
          ...state.items,
        ].slice(0, 100), // max 100
      };
    case "READ":
      return {
        items: state.items.map((n) =>
          n.id === action.id ? { ...n, read: true } : n,
        ),
      };
    case "READ_ALL":
      return { items: state.items.map((n) => ({ ...n, read: true })) };
    case "REMOVE":
      return { items: state.items.filter((n) => n.id !== action.id) };
    case "CLEAR_ALL":
      return { items: [] };
    default:
      return state;
  }
}

// ─────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────

interface NotificationContextValue {
  notifications: Notification[];
  unreadCount:   number;
  add:           (n: Omit<Notification, "id" | "timestamp" | "read">) => void;
  markRead:      (id: string) => void;
  markAllRead:   () => void;
  remove:        (id: string) => void;
  clearAll:      () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

// ─────────────────────────────────────────────────────────────
// Provider
// ─────────────────────────────────────────────────────────────

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, { items: [] });

  const add       = useCallback((n: Omit<Notification, "id" | "timestamp" | "read">) =>
    dispatch({ type: "ADD", payload: n }), []);
  const markRead  = useCallback((id: string) => dispatch({ type: "READ", id }), []);
  const markAllRead = useCallback(() => dispatch({ type: "READ_ALL" }), []);
  const remove    = useCallback((id: string) => dispatch({ type: "REMOVE", id }), []);
  const clearAll  = useCallback(() => dispatch({ type: "CLEAR_ALL" }), []);

  const unreadCount = state.items.filter((n) => !n.read).length;

  return (
    <NotificationContext.Provider
      value={{
        notifications: state.items,
        unreadCount,
        add,
        markRead,
        markAllRead,
        remove,
        clearAll,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

// ─────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used within NotificationProvider");
  return ctx;
}
