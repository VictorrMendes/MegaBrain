"use client";

import { useState, useEffect } from "react";
import { AppNav } from "@/components/nav/AppNav";
import { CommandPalette } from "@/components/search/CommandPalette";
import { WorkspaceProvider } from "@/context/WorkspaceContext";
import "./globals.css";

// metadata must be in a Server Component — moved to a separate generateMetadata or
// kept static via next/head when using "use client" at root.
// For now title is set via <title> below.

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <html lang="pt-BR">
      <head>
        <title>KHONSHU</title>
        <meta name="description" content="Sistema Operacional Cognitivo" />
      </head>
      <body className="antialiased">
        <WorkspaceProvider>
          <div className="flex h-screen overflow-hidden bg-neutral-950 text-neutral-100 font-sans">
            <AppNav />
            <div className="flex-1 overflow-hidden">{children}</div>
          </div>
          <CommandPalette
            open={paletteOpen}
            onClose={() => setPaletteOpen(false)}
          />
        </WorkspaceProvider>
      </body>
    </html>
  );
}
