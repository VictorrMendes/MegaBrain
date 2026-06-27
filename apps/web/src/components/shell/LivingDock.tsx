"use client";

import { useChatStore } from "@/store/useChatStore";
import { useUIStore } from "@/store/useUIStore";
import { cn } from "@/lib/cn";
import { BrainCircuitIcon } from "lucide-react";
import { useEffect, useState } from "react";

export function LivingDock() {
  const { isStreaming } = useChatStore();
  const { overlayStack, cognitiveState, closeAllOverlays } = useUIStore();
  const hasOverlay = overlayStack.length > 0;
  
  // Apenas renderizamos se tiver um overlay aberto e estiver processando,
  // ou se tivermos um estado cognitivo ativo persistente
  const shouldShow = hasOverlay && (isStreaming || cognitiveState !== "idle");
  
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  return (
    <button
      onClick={closeAllOverlays}
      className={cn(
        "fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-2.5 rounded-full",
        "bg-[var(--surface-overlay)] border border-accent/30 shadow-[0_0_20px_rgba(var(--accent-rgb),0.15)]",
        "backdrop-blur-xl transition-all duration-500 ease-in-out cursor-pointer group",
        "hover:border-accent/60 hover:shadow-[0_0_30px_rgba(var(--accent-rgb),0.25)] hover:scale-105",
        shouldShow ? "translate-y-0 opacity-100" : "translate-y-12 opacity-0 pointer-events-none"
      )}
    >
      <div className="relative flex items-center justify-center">
        <BrainCircuitIcon size={18} className="text-accent animate-pulse" />
        <div className="absolute inset-0 rounded-full bg-accent/20 blur-md animate-pulse"></div>
      </div>
      
      <div className="flex flex-col items-start">
        <span className="text-[10px] font-bold tracking-widest text-accent uppercase">
          KHONSHU
        </span>
        <span className="text-xs font-medium text-content-primary capitalize">
          {cognitiveState === "idle" ? "Thinking..." : cognitiveState}...
        </span>
      </div>
    </button>
  );
}
