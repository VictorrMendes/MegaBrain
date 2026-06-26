"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, type Workspace } from "@/lib/api";

interface WorkspaceContextValue {
  workspaces: Workspace[];
  current: Workspace | null;
  setCurrent: (ws: Workspace) => void;
  loading: boolean;
  refresh: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextValue>({
  workspaces: [],
  current: null,
  setCurrent: () => {},
  loading: true,
  refresh: async () => {},
});

const STORAGE_KEY = "khonshu.workspace";

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [current, setCurrent] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      let list = await api.listWorkspaces();
      if (list.length === 0) {
        const ws = await api.createWorkspace("Personal");
        list = [ws];
      }
      setWorkspaces(list);

      const savedId =
        typeof window !== "undefined"
          ? localStorage.getItem(STORAGE_KEY)
          : null;
      const saved = savedId ? list.find((w) => w.id === savedId) : null;
      setCurrent(saved ?? list[0]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSetCurrent = useCallback((ws: Workspace) => {
    setCurrent(ws);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, ws.id);
    }
  }, []);

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        current,
        setCurrent: handleSetCurrent,
        loading,
        refresh: load,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  return useContext(WorkspaceContext);
}
