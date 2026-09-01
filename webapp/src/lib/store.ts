import { create } from "zustand";
import { api, Health } from "./api";

interface AppState {
  health: Health | null;
  loading: boolean;
  checkHealth: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  health: null,
  loading: false,
  checkHealth: async () => {
    set({ loading: true });
    try {
      const h = await api.health();
      set({ health: h, loading: false });
    } catch {
      set({ health: null, loading: false });
    }
  },
}));
