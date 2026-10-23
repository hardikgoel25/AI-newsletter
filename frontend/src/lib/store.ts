"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { api, ApiError, session } from "./api";
import {
  DEFAULT_BRAND,
  DEFAULT_OPTIONS,
  type AutoHero,
  type BrandKit,
  type Byok,
  type GenerateOptions,
  type HealthResponse,
  type HeroImage,
  type HistoryEntry,
  type LLMOptions,
  type ModelInfo,
  type Newsletter,
  type RenderOptions,
  type Section,
  type Source,
  type TemplateInfo,
} from "./types";
import { uid } from "./utils";

export type Status = "idle" | "generating" | "rendering" | "error";
export type Pane = "compose" | "preview" | "edit";
export type ComposeTab = "content" | "settings" | "brand";
export type PreviewWidth = "desktop" | "tablet" | "mobile";
export type AppTheme = "system" | "dark" | "light";

export interface Toast {
  id: string;
  kind: "success" | "error" | "info" | "warning";
  message: string;
}

export interface GenerateMeta {
  model: string;
  provider: string;
  elapsed_ms: number;
  usage: Record<string, number>;
}

interface StudioState {
  // ---- inputs ----
  sources: Source[];
  options: GenerateOptions;
  brand: BrandKit;
  render: RenderOptions;
  llm: LLMOptions;
  autoHero: AutoHero;
  customHero: HeroImage | null;

  // ---- result ----
  newsletter: Newsletter | null;
  html: string;
  warnings: string[];
  meta: GenerateMeta | null;
  status: Status;
  step: string;
  error: string | null;

  // ---- catalogs ----
  templates: TemplateInfo[];
  presets: BrandKit[];
  models: ModelInfo[];
  fonts: string[];
  health: HealthResponse | null;
  healthError: string | null;

  // ---- user data ----
  savedBrands: BrandKit[];
  history: HistoryEntry[];
  accessKey: string; // shared secret for a private deployment
  byok: Byok | null; // the visitor's own provider key

  // ---- ui ----
  activePane: Pane;
  composeTab: ComposeTab;
  previewWidth: PreviewWidth;
  appTheme: AppTheme;
  toasts: Toast[];
  editorOpen: boolean;
  dirty: number; // bumps whenever the newsletter/brand/render changes -> triggers re-render

  // ---- actions ----
  setSources: (s: Source[]) => void;
  addSource: (s: Omit<Source, "id">) => void;
  updateSource: (id: string, patch: Partial<Source>) => void;
  removeSource: (id: string) => void;
  setOptions: (patch: Partial<GenerateOptions>) => void;
  setBrand: (patch: Partial<BrandKit>) => void;
  replaceBrand: (b: BrandKit) => void;
  setRender: (patch: Partial<RenderOptions>) => void;
  setLLM: (patch: Partial<LLMOptions>) => void;
  setAutoHero: (m: AutoHero) => void;
  setCustomHero: (h: HeroImage | null) => void;

  loadCatalogs: () => Promise<void>;
  generate: () => Promise<void>;
  cancelGenerate: () => void;
  rerender: () => Promise<void>;
  updateNewsletter: (fn: (n: Newsletter) => Newsletter) => void;
  regenerateSection: (index: number, instruction: string) => Promise<void>;
  clearResult: () => void;

  saveBrand: (name: string) => void;
  deleteSavedBrand: (id: string) => void;
  setCredentials: (accessKey: string, byok: Byok | null) => void;
  restoreHistory: (id: string) => void;
  deleteHistory: (id: string) => void;
  clearHistory: () => void;

  setPane: (p: Pane) => void;
  setComposeTab: (t: ComposeTab) => void;
  setPreviewWidth: (w: PreviewWidth) => void;
  setAppTheme: (t: AppTheme) => void;
  setEditorOpen: (v: boolean) => void;
  toast: (message: string, kind?: Toast["kind"]) => void;
  dismissToast: (id: string) => void;
}

let generateController: AbortController | null = null;
let renderController: AbortController | null = null;

const MAX_HISTORY = 12;

function applyTheme(theme: AppTheme) {
  if (typeof document === "undefined") return;
  const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
  try {
    localStorage.setItem("ains.theme", theme);
  } catch {
    /* ignore */
  }
}

/** localStorage wrapper that sheds history entries when the quota is exceeded. */
const resilientStorage = {
  getItem: (name: string) => {
    try {
      return localStorage.getItem(name);
    } catch {
      return null;
    }
  },
  setItem: (name: string, value: string) => {
    try {
      localStorage.setItem(name, value);
    } catch {
      try {
        const parsed = JSON.parse(value);
        const state = parsed?.state;
        if (state?.history?.length) {
          state.history = state.history.slice(0, Math.max(0, Math.floor(state.history.length / 2)));
          localStorage.setItem(name, JSON.stringify(parsed));
        }
      } catch {
        /* give up silently */
      }
    }
  },
  removeItem: (name: string) => {
    try {
      localStorage.removeItem(name);
    } catch {
      /* ignore */
    }
  },
};

export const useStudio = create<StudioState>()(
  persist(
    (set, get) => ({
      sources: [{ id: uid("src"), kind: "text", label: "Company updates", text: "" }],
      options: { ...DEFAULT_OPTIONS },
      brand: { ...DEFAULT_BRAND, socials: { ...DEFAULT_BRAND.socials } },
      render: { template: "modern", theme: "dark" },
      llm: { provider: null, model: null, temperature: 0.3 },
      autoHero: "unsplash",
      customHero: null,

      newsletter: null,
      html: "",
      warnings: [],
      meta: null,
      status: "idle",
      step: "",
      error: null,

      templates: [],
      presets: [],
      models: [],
      fonts: [],
      health: null,
      healthError: null,

      savedBrands: [],
      history: [],
      accessKey: "",
      byok: null,

      activePane: "compose",
      composeTab: "content",
      previewWidth: "desktop",
      appTheme: "system",
      toasts: [],
      editorOpen: false,
      dirty: 0,

      // ------------------------------------------------------------ inputs
      setSources: (sources) => set({ sources }),
      addSource: (s) => set((st) => ({ sources: [...st.sources, { ...s, id: uid("src") }] })),
      updateSource: (id, patch) =>
        set((st) => ({ sources: st.sources.map((s) => (s.id === id ? { ...s, ...patch } : s)) })),
      removeSource: (id) =>
        set((st) => {
          const next = st.sources.filter((s) => s.id !== id);
          return { sources: next.length ? next : [{ id: uid("src"), kind: "text", label: "Company updates", text: "" }] };
        }),
      setOptions: (patch) => set((st) => ({ options: { ...st.options, ...patch } })),
      setBrand: (patch) => set((st) => ({ brand: { ...st.brand, ...patch, id: patch.id ?? "custom" }, dirty: st.dirty + 1 })),
      replaceBrand: (b) => set((st) => ({ brand: { ...b, socials: { ...b.socials } }, dirty: st.dirty + 1 })),
      setRender: (patch) => set((st) => ({ render: { ...st.render, ...patch }, dirty: st.dirty + 1 })),
      setLLM: (patch) => set((st) => ({ llm: { ...st.llm, ...patch } })),
      setAutoHero: (autoHero) => set({ autoHero }),
      setCustomHero: (customHero) => set({ customHero }),

      // ------------------------------------------------------------ catalogs
      loadCatalogs: async () => {
        try {
          const health = await api.health();
          set({ health, healthError: null });
        } catch (err) {
          set({ healthError: (err as Error).message });
          return;
        }
        const [templates, presets, models, fonts] = await Promise.allSettled([
          api.templates(),
          api.presets(),
          api.models(),
          api.fonts(),
        ]);
        set({
          templates: templates.status === "fulfilled" ? templates.value : [],
          presets: presets.status === "fulfilled" ? presets.value : [],
          models: models.status === "fulfilled" ? models.value : [],
          fonts: fonts.status === "fulfilled" ? fonts.value : [],
        });
        const st = get();
        if (!st.llm.model && models.status === "fulfilled") {
          const usable = models.value.filter((m) => (st.byok ? m.provider === st.byok.provider : m.available));
          const def = usable.find((m) => m.default) ?? usable[0];
          if (def) set({ llm: { ...st.llm, provider: def.provider, model: def.id } });
        }
      },

      // ------------------------------------------------------------ generate
      generate: async () => {
        const st = get();
        const sources = st.sources.filter((s) => s.text.trim());
        if (!sources.length) {
          st.toast("Add some content first.", "warning");
          return;
        }
        generateController?.abort();
        generateController = new AbortController();
        set({ status: "generating", step: "Preparing prompt", error: null, warnings: [] });
        const stepTimer = setTimeout(() => set({ step: "Writing with the model" }), 900);
        const stepTimer2 = setTimeout(() => set({ step: "Validating and picking images" }), 6000);
        try {
          const res = await api.generate(
            {
              sources: sources.map(({ kind, label, text }) => ({ kind, label, text })),
              options: st.options,
              brand: st.brand,
              render: st.render,
              llm: { ...st.llm, provider: st.byok ? st.byok.provider : st.llm.provider },
              hero_image: st.customHero,
              auto_hero: st.autoHero,
            },
            generateController.signal,
          );
          const entry: HistoryEntry = {
            id: uid("h"),
            createdAt: Date.now(),
            title: res.newsletter.hero_title,
            company: res.newsletter.company_name,
            newsletter: res.newsletter,
            brand: st.brand,
            render: st.render,
          };
          set((s) => ({
            newsletter: res.newsletter,
            html: res.html,
            warnings: res.warnings,
            meta: { model: res.model, provider: res.provider, elapsed_ms: res.elapsed_ms, usage: res.usage },
            status: "idle",
            step: "",
            history: [entry, ...s.history].slice(0, MAX_HISTORY),
            activePane: "preview",
            editorOpen: true,
          }));
          get().toast(`Newsletter ready in ${(res.elapsed_ms / 1000).toFixed(1)}s`, "success");
          res.warnings.forEach((w) => get().toast(w, "warning"));
        } catch (err) {
          if ((err as Error).name === "AbortError") {
            set({ status: "idle", step: "" });
            return;
          }
          const message = err instanceof ApiError ? err.message : "Generation failed.";
          set({ status: "error", error: message, step: "" });
          get().toast(message, "error");
        } finally {
          clearTimeout(stepTimer);
          clearTimeout(stepTimer2);
        }
      },
      cancelGenerate: () => {
        generateController?.abort();
        set({ status: "idle", step: "" });
      },

      rerender: async () => {
        const st = get();
        if (!st.newsletter) return;
        renderController?.abort();
        renderController = new AbortController();
        set({ status: st.status === "generating" ? "generating" : "rendering" });
        try {
          const res = await api.render(st.newsletter, st.brand, st.render, renderController.signal);
          set({ html: res.html, status: "idle" });
        } catch (err) {
          if ((err as Error).name === "AbortError") return;
          set({ status: "idle" });
          get().toast((err as Error).message || "Preview update failed.", "error");
        }
      },

      updateNewsletter: (fn) =>
        set((st) => (st.newsletter ? { newsletter: fn(st.newsletter), dirty: st.dirty + 1 } : {})),

      regenerateSection: async (index, instruction) => {
        const st = get();
        if (!st.newsletter) return;
        try {
          const res = await api.regenerateSection({
            newsletter: st.newsletter,
            section_index: index,
            instruction,
            tone: st.options.tone,
            language: st.options.language,
            llm: { ...st.llm, provider: st.byok ? st.byok.provider : st.llm.provider },
          });
          get().updateNewsletter((n) => ({
            ...n,
            sections: n.sections.map((s, i) => (i === index ? ({ ...res.section, id: s.id } as Section) : s)),
          }));
          get().toast("Section rewritten.", "success");
        } catch (err) {
          get().toast((err as Error).message || "Could not rewrite the section.", "error");
        }
      },

      clearResult: () => set({ newsletter: null, html: "", warnings: [], meta: null, error: null, editorOpen: false, activePane: "compose" }),

      // ------------------------------------------------------------ user data
      saveBrand: (name) =>
        set((st) => {
          const kit: BrandKit = { ...st.brand, id: uid("brand"), name: name.trim() || "My brand" };
          return { savedBrands: [kit, ...st.savedBrands.filter((b) => b.name !== kit.name)].slice(0, 20), brand: kit };
        }),
      deleteSavedBrand: (id) => set((st) => ({ savedBrands: st.savedBrands.filter((b) => b.id !== id) })),
      setCredentials: (accessKey, byok) =>
        set((st) => {
          const next: Partial<StudioState> = { accessKey: accessKey.trim(), byok: byok?.key.trim() ? { provider: byok.provider, key: byok.key.trim() } : null };
          // A personal key pins the provider; clear a model that belongs to another provider.
          if (next.byok && st.llm.provider !== next.byok.provider) next.llm = { ...st.llm, provider: next.byok.provider, model: null };
          if (!next.byok && st.byok) next.llm = { ...st.llm, provider: null, model: null };
          return next;
        }),
      restoreHistory: (id) => {
        const entry = get().history.find((h) => h.id === id);
        if (!entry) return;
        set((st) => ({
          newsletter: entry.newsletter,
          brand: entry.brand,
          render: entry.render,
          html: "",
          warnings: [],
          meta: null,
          error: null,
          dirty: st.dirty + 1,
          activePane: "preview",
          editorOpen: true,
        }));
      },
      deleteHistory: (id) => set((st) => ({ history: st.history.filter((h) => h.id !== id) })),
      clearHistory: () => set({ history: [] }),

      // ------------------------------------------------------------ ui
      setPane: (activePane) => set({ activePane }),
      setComposeTab: (composeTab) => set({ composeTab }),
      setPreviewWidth: (previewWidth) => set({ previewWidth }),
      setAppTheme: (appTheme) => {
        applyTheme(appTheme);
        set({ appTheme });
      },
      setEditorOpen: (editorOpen) => set({ editorOpen }),
      toast: (message, kind = "info") => {
        const id = uid("t");
        set((st) => ({ toasts: [...st.toasts, { id, kind, message }].slice(-5) }));
        setTimeout(() => get().dismissToast(id), kind === "error" ? 8000 : 4500);
      },
      dismissToast: (id) => set((st) => ({ toasts: st.toasts.filter((t) => t.id !== id) })),
    }),
    {
      name: "ains.studio.v1",
      storage: createJSONStorage(() => resilientStorage),
      // Hydrate after mount (see Studio.tsx) so server and first client render match.
      skipHydration: true,
      partialize: (st) => ({
        sources: st.sources,
        options: st.options,
        brand: st.brand,
        render: st.render,
        llm: st.llm,
        autoHero: st.autoHero,
        newsletter: st.newsletter,
        savedBrands: st.savedBrands,
        history: st.history,
        accessKey: st.accessKey,
        byok: st.byok,
        composeTab: st.composeTab,
        appTheme: st.appTheme,
        previewWidth: st.previewWidth,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) applyTheme(state.appTheme);
      },
    },
  ),
);

// Mirror credentials into the fetch layer whenever they change (including after rehydration).
useStudio.subscribe((st) => {
  session.accessKey = st.accessKey;
  session.byok = st.byok;
});

export const selectHasResult = (s: StudioState) => Boolean(s.newsletter);
