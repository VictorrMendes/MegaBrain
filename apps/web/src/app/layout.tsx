"use client";

import { useState, useEffect } from "react";
import { AppNav }              from "@/components/nav/AppNav";
import { TopBar }              from "@/components/shell/TopBar";
import { StatusBar }           from "@/components/shell/StatusBar";
import { CommandPalette }      from "@/components/search/CommandPalette";
import { WorkspaceProvider }   from "@/context/WorkspaceContext";
import { NotificationProvider } from "@/context/NotificationContext";
import { TooltipProvider }     from "@/components/ui";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);

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
    <html lang="pt-BR">
      <head>
        <title>PAIOS — Sistema Operacional Cognitivo</title>
        <meta name="description" content="Personal AI Operating System" />
        <meta name="theme-color" content="#08080c" />
      </head>
      <body className="antialiased">
        <NotificationProvider>
          <WorkspaceProvider>
            <TooltipProvider>

              {/* ── OS Shell ── */}
              <div className="flex h-screen flex-col overflow-hidden bg-[var(--surface-base)] text-content-primary">

                {/* TopBar — 40px */}
                <TopBar onOpenPalette={() => setPaletteOpen(true)} />

                {/* Main area */}
                <div className="flex flex-1 overflow-hidden">

                  {/* Sidebar */}
                  <AppNav />

                  {/* Content */}
                  <main className="flex-1 overflow-hidden">
                    {children}
                  </main>

                </div>

                {/* StatusBar — 24px */}
                <StatusBar />

              </div>

              {/* ── Floating layers ── */}
              <CommandPalette
                open={paletteOpen}
                onClose={() => setPaletteOpen(false)}
              />

            </TooltipProvider>
          </WorkspaceProvider>
        </NotificationProvider>
      </body>
    </html>
  );
}
