"use client";

import { useState, useEffect } from "react";
import { AppNav }              from "@/components/nav/AppNav";
import { MobileNav }           from "@/components/nav/MobileNav";
import { TopBar }              from "@/components/shell/TopBar";
import { StatusBar }           from "@/components/shell/StatusBar";
import { CommandPalette }      from "@/components/search/CommandPalette";
import { ServiceWorkerRegistrar } from "@/components/shell/ServiceWorkerRegistrar";
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
        <title>Khonshu — Sistema Operacional Cognitivo</title>
        <meta name="description" content="Personal AI Operating System" />
        <meta name="theme-color" content="#08080c" />

        {/* ── Mobile viewport ── */}
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover"
        />

        {/* ── PWA / iOS ── */}
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="PAIOS" />
        <link rel="manifest" href="/manifest.webmanifest" />
        <link rel="apple-touch-startup-image" href="/apple-icon.png" />
      </head>
      <body className="antialiased">
        <ServiceWorkerRegistrar />

        <NotificationProvider>
          <WorkspaceProvider>
            <TooltipProvider>

              {/* ── OS Shell ── */}
              <div className="flex h-[100dvh] flex-col overflow-hidden bg-[var(--surface-base)] text-content-primary">

                {/* TopBar — 40px */}
                <TopBar onOpenPalette={() => setPaletteOpen(true)} />

                {/* Main area */}
                <div className="flex flex-1 overflow-hidden">

                  {/* Desktop sidebar */}
                  <AppNav />

                  {/* Content — extra bottom padding on mobile for nav bar */}
                  <main className="flex-1 overflow-hidden pb-[var(--mobile-nav-h)] md:pb-0">
                    {children}
                  </main>

                </div>

                {/* StatusBar — desktop only */}
                <StatusBar />

              </div>

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
      </body>
    </html>
  );
}
