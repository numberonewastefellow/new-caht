import { create } from "zustand";
import { LlmDescriptor } from "@/lib/hooks";

/**
 * Multi-model "compare side-by-side" selection + panel-session state.
 *
 * Separate from the single-model `LlmManager` (which stays the primary model
 * for normal single chat). When >1 model is selected here, the app enters
 * compare mode: each model gets its own real chat session, streamed in
 * parallel into its own panel. `panelSessionIds` is index-aligned with
 * `compareModels` and filled lazily on first send (so follow-up turns reuse
 * the same panel sessions). Web-only — see MULTI_MODEL_COMPARE_PLAN.md.
 */
export const MAX_COMPARE_MODELS = 3;

function sameModel(a: LlmDescriptor, b: LlmDescriptor): boolean {
  return (
    a.name === b.name &&
    a.provider === b.provider &&
    a.modelName === b.modelName
  );
}

interface CompareStore {
  compareModels: LlmDescriptor[];
  // index-aligned with compareModels; entry is undefined until its session is created
  panelSessionIds: (string | undefined)[];

  setCompareModels: (models: LlmDescriptor[]) => void;
  toggleModel: (model: LlmDescriptor) => void;
  isModelSelected: (model: LlmDescriptor) => boolean;
  setPanelSessionId: (index: number, sessionId: string) => void;
  reset: () => void;
}

export const useCompareStore = create<CompareStore>((set, get) => ({
  compareModels: [],
  panelSessionIds: [],

  setCompareModels: (models) =>
    set({
      compareModels: models.slice(0, MAX_COMPARE_MODELS),
      panelSessionIds: [],
    }),

  toggleModel: (model) =>
    set((state) => {
      const exists = state.compareModels.some((m) => sameModel(m, model));
      if (exists) {
        return {
          compareModels: state.compareModels.filter(
            (m) => !sameModel(m, model)
          ),
          panelSessionIds: [], // model set changed → drop stale panel sessions
        };
      }
      if (state.compareModels.length >= MAX_COMPARE_MODELS) return state;
      return {
        compareModels: [...state.compareModels, model],
        panelSessionIds: [],
      };
    }),

  isModelSelected: (model) =>
    get().compareModels.some((m) => sameModel(m, model)),

  setPanelSessionId: (index, sessionId) =>
    set((state) => {
      const ids = [...state.panelSessionIds];
      ids[index] = sessionId;
      return { panelSessionIds: ids };
    }),

  reset: () => set({ compareModels: [], panelSessionIds: [] }),
}));

// Compare mode is active when more than one model is selected.
export const useIsCompareMode = () =>
  useCompareStore((s) => s.compareModels.length > 1);
