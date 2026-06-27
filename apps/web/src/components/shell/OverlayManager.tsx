"use client";

import dynamic from "next/dynamic";
import { useUIStore, type OverlayId } from "@/store/useUIStore";
import { cn } from "@/lib/cn";
import { XIcon } from "lucide-react";

const OVERLAYS: Record<OverlayId, React.ComponentType<any>> = {
  dashboard: dynamic(() => import("@/components/dashboard/DashboardPage").then(m => m.DashboardPage)),
  knowledge: dynamic(() => import("@/components/knowledge/KnowledgePage").then(m => m.KnowledgePage)),
  memory: dynamic(() => import("@/components/memory/MemoryPage").then(m => m.MemoryPage)),
  missions: dynamic(() => import("@/components/missions/MissionsPage").then(m => m.MissionsPage)),
  inbox: dynamic(() => import("@/components/inbox/InboxPage").then(m => m.InboxPage)),
  timeline: dynamic(() => import("@/components/timeline/TimelinePage").then(m => m.TimelinePage)),
  artifacts: dynamic(() => import("@/components/artifacts/ArtifactsPage").then(m => m.ArtifactsPage).catch(() => () => <div>Em breve</div>)),
  runtime: dynamic(() => import("@/components/runtime/RuntimeDashboard").then(m => m.RuntimeDashboard).catch(() => () => <div>Em breve</div>)),
  integrations: dynamic(() => import("@/components/integrations/IntegrationsPage").then(m => m.IntegrationsPage).catch(() => () => <div>Em breve</div>)),
};

export function OverlayManager() {
  const { overlayStack, popOverlay } = useUIStore();

  if (overlayStack.length === 0) return null;

  return (
    <div className="absolute inset-0 z-40 flex pointer-events-none">
      {overlayStack.map((overlayId, index) => {
        const Component = OVERLAYS[overlayId];
        const isTop = index === overlayStack.length - 1;
        
        if (!Component) return null;

        return (
          <div
            key={`${overlayId}-${index}`}
            className={cn(
              "absolute inset-0 bg-[var(--surface-base)]/95 backdrop-blur-xl pointer-events-auto",
              "transition-all duration-300 ease-out flex flex-col",
              isTop ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8 pointer-events-none"
            )}
            style={{ zIndex: 40 + index }}
          >
            {/* Header com botão de fechar */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]/50">
              <h2 className="text-sm font-semibold tracking-wider text-content-primary capitalize">
                {overlayId}
              </h2>
              <button
                onClick={popOverlay}
                className="p-2 rounded-lg text-content-muted hover:text-content-primary hover:bg-[var(--surface-subtle)] transition-colors"
              >
                <XIcon size={18} />
              </button>
            </div>
            
            {/* Conteúdo do Overlay */}
            <div className="flex-1 overflow-auto">
              <Component />
            </div>
          </div>
        );
      })}
    </div>
  );
}
