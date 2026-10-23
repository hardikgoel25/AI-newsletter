"use client";

import { Eye, PenLine, RefreshCw, Sparkles, TriangleAlert } from "lucide-react";
import { useEffect, useSyncExternalStore } from "react";

import { API_URL } from "@/lib/api";
import { useStudio, type Pane } from "@/lib/store";
import { cn, downloadText, slugify } from "@/lib/utils";

import { ComposePanel } from "./compose/ComposePanel";
import { EditorPanel } from "./editor/EditorPanel";
import { Header } from "./Header";
import { PreviewPanel } from "./PreviewPanel";
import { Toaster } from "./Toaster";
import { Button } from "./ui";

export function Studio() {
  // True once persisted state has been loaded on the client (false during SSR).
  const hydrated = useSyncExternalStore(
    (cb) => useStudio.persist.onFinishHydration(cb),
    () => useStudio.persist.hasHydrated(),
    () => false,
  );
  const loadCatalogs = useStudio((s) => s.loadCatalogs);
  const generate = useStudio((s) => s.generate);
  const rerender = useStudio((s) => s.rerender);
  const dirty = useStudio((s) => s.dirty);
  const newsletter = useStudio((s) => s.newsletter);
  const html = useStudio((s) => s.html);
  const activePane = useStudio((s) => s.activePane);
  const setPane = useStudio((s) => s.setPane);
  const editorOpen = useStudio((s) => s.editorOpen);
  const healthError = useStudio((s) => s.healthError);
  const appTheme = useStudio((s) => s.appTheme);

  // Rehydrate persisted state after mount so SSR markup matches the first client render.
  useEffect(() => {
    if (!useStudio.persist.hasHydrated()) void useStudio.persist.rehydrate();
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    void loadCatalogs();
  }, [hydrated, loadCatalogs]);

  // Follow the OS theme while in "system" mode.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (useStudio.getState().appTheme === "system") document.documentElement.classList.toggle("dark", mq.matches);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [appTheme]);

  // Live re-render on edits (debounced). Also renders a restored newsletter that has no HTML yet.
  useEffect(() => {
    if (!hydrated || !newsletter) return;
    const t = setTimeout(() => void rerender(), html ? 450 : 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirty, hydrated, Boolean(newsletter)]);

  // Keyboard shortcuts.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (e.key === "Enter") {
        e.preventDefault();
        void generate();
      } else if (e.key.toLowerCase() === "s") {
        const st = useStudio.getState();
        if (st.html && st.newsletter) {
          e.preventDefault();
          downloadText(st.html, `${slugify(`${st.newsletter.company_name}-${st.newsletter.newsletter_type}-${st.newsletter.date}`)}.html`);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [generate]);

  const showEditor = Boolean(newsletter) && editorOpen;

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <Header />

      {healthError ? (
        <div className="flex items-center gap-3 border-b border-warning/30 bg-warning/10 px-4 py-2 text-xs text-text">
          <TriangleAlert className="size-4 shrink-0 text-warning" />
          <span className="min-w-0 flex-1 truncate">
            Cannot reach the API at <code className="font-mono">{API_URL}</code>. {healthError}
          </span>
          <Button size="sm" variant="outline" onClick={() => void loadCatalogs()}>
            <RefreshCw className="size-3.5" /> Retry
          </Button>
        </div>
      ) : null}

      <div className="relative flex min-h-0 flex-1">
        {/* Compose */}
        <div
          className={cn(
            "h-full w-full shrink-0 border-r border-border lg:w-[380px] lg:block",
            activePane === "compose" ? "block" : "hidden",
          )}
        >
          <ComposePanel />
        </div>

        {/* Preview */}
        <div className={cn("h-full min-w-0 flex-1 lg:block", activePane === "preview" ? "block" : "hidden")}>
          <PreviewPanel />
        </div>

        {/* Editor: third column on xl, drawer below xl */}
        {showEditor ? (
          <>
            <div className="hidden h-full w-[380px] shrink-0 border-l border-border xl:block">
              <EditorPanel />
            </div>
            <div
              className={cn(
                "absolute inset-y-0 right-0 z-20 h-full w-full border-l border-border shadow-pop xl:hidden sm:w-[420px] animate-fade-up",
                activePane === "edit" ? "block" : "hidden lg:block",
              )}
            >
              <EditorPanel />
            </div>
          </>
        ) : null}
      </div>

      {/* Mobile tab bar */}
      <nav className="glass flex h-14 shrink-0 items-stretch border-t border-border lg:hidden" aria-label="Panels">
        {(
          [
            ["compose", "Compose", <Sparkles key="c" className="size-4" />],
            ["preview", "Preview", <Eye key="p" className="size-4" />],
            ["edit", "Edit", <PenLine key="e" className="size-4" />],
          ] as [Pane, string, React.ReactNode][]
        ).map(([id, label, icon]) => (
          <button
            key={id}
            type="button"
            disabled={id === "edit" && !newsletter}
            onClick={() => {
              setPane(id);
              if (id === "edit") useStudio.getState().setEditorOpen(true);
            }}
            className={cn(
              "flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition disabled:opacity-40",
              activePane === id ? "text-accent" : "text-muted",
            )}
          >
            {icon}
            {label}
          </button>
        ))}
      </nav>

      <Toaster />
    </div>
  );
}
