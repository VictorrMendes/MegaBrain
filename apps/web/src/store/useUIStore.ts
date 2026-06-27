import { create } from "zustand";

export type OverlayId = 
  | "dashboard" 
  | "missions" 
  | "memory" 
  | "knowledge" 
  | "inbox" 
  | "timeline" 
  | "artifacts" 
  | "runtime" 
  | "integrations";

export type CognitiveState = 
  | "idle" 
  | "thinking" 
  | "searching" 
  | "retrieving" 
  | "generating" 
  | "learning";

interface UIStore {
  // Overlays (Stack for real depth/hierarchy)
  overlayStack: OverlayId[];
  pushOverlay: (overlay: OverlayId) => void;
  popOverlay: () => void;
  closeAllOverlays: () => void;
  
  // Cognitive Status Global
  cognitiveState: CognitiveState;
  setCognitiveState: (state: CognitiveState) => void;
  
  // Legacy or global ui states
  mobileDrawerOpen: boolean;
  setMobileDrawerOpen: (open: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  overlayStack: [],
  
  pushOverlay: (overlay) => set((state) => {
    if (state.overlayStack[state.overlayStack.length - 1] === overlay) {
      return state;
    }
    const filtered = state.overlayStack.filter((id) => id !== overlay);
    return { overlayStack: [...filtered, overlay] };
  }),
  
  popOverlay: () => set((state) => ({
    overlayStack: state.overlayStack.slice(0, -1)
  })),
  
  closeAllOverlays: () => set({ overlayStack: [] }),

  cognitiveState: "idle",
  setCognitiveState: (s) => set({ cognitiveState: s }),

  mobileDrawerOpen: false,
  setMobileDrawerOpen: (open) => set({ mobileDrawerOpen: open }),
}));
