"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { AppNav }              from "@/components/nav/AppNav";
import { MobileNav }           from "@/components/nav/MobileNav";
import { TopBar }              from "@/components/shell/TopBar";
import { StatusBar }           from "@/components/shell/StatusBar";
import { CommandPalette }      from "@/components/search/CommandPalette";
import { ServiceWorkerRegistrar } from "@/components/shell/ServiceWorkerRegistrar";
import { WorkspaceProvider }   from "@/context/WorkspaceContext";
import { NotificationProvider } from "@/context/NotificationContext";
import { TooltipProvider }     from "@/components/ui";
import { useUIStore, type OverlayId } from "@/store/useUIStore";

// UX Overhaul: True SPA components
import { ChatPanel } from "@/components/chat/ChatPanel";
import { OverlayManager } from "@/components/shell/OverlayManager";
import { LivingDock } from "@/components/shell/LivingDock";

export function ShellLayout({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const pathname = usePathname();
  const { overlayStack, pushOverlay } = useUIStore();

  // Deep Link Support: Initialize overlay based on URL
  useEffect(() => {
    if (pathname && overlayStack.length === 0) {
      const route = pathname.replace('/', '');
      if (["memory", "knowledge", "missions", "artifacts", "inbox"].includes(route)) {
        pushOverlay(route as OverlayId);
      }
    }
  }, [pathname, overlayStack.length, pushOverlay]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
      if (e.key === "Escape" && paletteOpen) {
        setPaletteOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [paletteOpen]);

  return (
    <>
      <ServiceWorkerRegistrar />

      <NotificationProvider>
        <WorkspaceProvider>
          <TooltipProvider>

            {/* ── OS Shell ── */}
            <div className="flex h-[100dvh] flex-col overflow-hidden bg-[var(--surface-base)] text-content-primary">

              {/* TopBar / CognitiveStatusBar (poderá ser unificado depois) */}
              <TopBar onOpenPalette={() => setPaletteOpen(true)} />

              {/* Main area */}
              <div className="flex flex-1 overflow-hidden relative">
                <AppNav />
                
                <main className="relative flex-1 overflow-hidden pb-[var(--mobile-nav-h)] md:pb-0">
                  {/* Fundo Constante: O Chat nunca desmonta */}
                  <div className="absolute inset-0">
                    <ChatPanel />
                  </div>
                  
                  {/* Camada Portal: Overlays (Memory, Knowledge, etc) */}
                  <OverlayManager />
                  
                  {/* Fallback de rotas do Next.js (children invisível ou renderizado se não houver overlay) */}
                  {/* Exibimos children se a rota for de settings */}
                  <div className={pathname?.startsWith("/settings") ? "absolute inset-0 z-40 bg-[var(--surface-base)]" : "hidden"}>
                    {children}
                  </div>
                </main>
              </div>

              {/* StatusBar — desktop only */}
              <StatusBar />
            </div>

            {/* ── Sinais de Vida ── */}
            <LivingDock />

            {/* ── Mobile bottom navigation ── */}
            <MobileNav />

            {/* ── Floating layers ── */}
            <CommandPalette
              open={paletteOpen}
              onClose={() => setPaletteOpen(false)}
            />

          </TooltipProvider>
        </WorkspaceProvider>
      </NotificationProvider>
    </>
  );
}
