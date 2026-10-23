"use client";

import { ExternalLink, Monitor, Moon, Newspaper, Smartphone, Sparkles, Sun, Tablet, X } from "lucide-react";
import { useMemo } from "react";

import { useStudio } from "@/lib/store";
import { cn, openHtmlInNewTab } from "@/lib/utils";

import { Badge, Button, EmptyHint, Segmented, Spinner } from "./ui";

const widths = { desktop: "100%", tablet: "768px", mobile: "390px" } as const;

export function PreviewPanel() {
  const html = useStudio((s) => s.html);
  const status = useStudio((s) => s.status);
  const step = useStudio((s) => s.step);
  const error = useStudio((s) => s.error);
  const newsletter = useStudio((s) => s.newsletter);
  const meta = useStudio((s) => s.meta);
  const previewWidth = useStudio((s) => s.previewWidth);
  const setPreviewWidth = useStudio((s) => s.setPreviewWidth);
  const render = useStudio((s) => s.render);
  const setRender = useStudio((s) => s.setRender);
  const setPane = useStudio((s) => s.setPane);
  const cancel = useStudio((s) => s.cancelGenerate);
  const templates = useStudio((s) => s.templates);

  const templateName = useMemo(() => templates.find((t) => t.id === render.template)?.name ?? render.template, [templates, render.template]);

  return (
    <section className="flex h-full min-h-0 flex-1 flex-col bg-bg" aria-label="Preview">
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border bg-surface/60 px-3">
        <Segmented
          size="sm"
          value={previewWidth}
          onChange={setPreviewWidth}
          options={[
            { value: "desktop", label: <Monitor className="size-4" />, title: "Desktop" },
            { value: "tablet", label: <Tablet className="size-4" />, title: "Tablet" },
            { value: "mobile", label: <Smartphone className="size-4" />, title: "Mobile" },
          ]}
        />
        <Segmented
          size="sm"
          value={render.theme}
          onChange={(theme) => setRender({ theme })}
          options={[
            { value: "dark", label: <Moon className="size-4" />, title: "Dark newsletter" },
            { value: "light", label: <Sun className="size-4" />, title: "Light newsletter" },
          ]}
        />
        <div className="ml-auto flex items-center gap-2 min-w-0">
          {status === "rendering" ? (
            <span className="flex items-center gap-1.5 text-xs text-muted">
              <Spinner /> Updating
            </span>
          ) : meta ? (
            <span className="hidden sm:flex items-center gap-1.5 text-[11px] text-faint">
              <Badge>{templateName}</Badge>
              <Badge tone="accent">{meta.model.split("/").pop()}</Badge>
              <span>{(meta.elapsed_ms / 1000).toFixed(1)}s</span>
            </span>
          ) : null}
          <Button size="sm" variant="ghost" disabled={!html} onClick={() => openHtmlInNewTab(html)} title="Open in new tab">
            <ExternalLink className="size-4" />
            <span className="hidden sm:inline">Open</span>
          </Button>
        </div>
      </div>

      <div className="relative flex-1 min-h-0 overflow-auto p-3 sm:p-5">
        {html ? (
          <div
            className={cn(
              "mx-auto h-full overflow-hidden rounded-2xl border border-border bg-white shadow-soft transition-[max-width] duration-300",
            )}
            style={{ maxWidth: widths[previewWidth] }}
          >
            <iframe
              title="Newsletter preview"
              sandbox=""
              srcDoc={html}
              className="h-full w-full bg-white"
              referrerPolicy="no-referrer"
            />
          </div>
        ) : status === "generating" ? null : newsletter ? (
          <div className="mx-auto h-full max-w-3xl space-y-4 p-6">
            <div className="skeleton h-40" />
            <div className="skeleton h-8 w-2/3" />
            <div className="skeleton h-5 w-1/2" />
            <div className="grid grid-cols-2 gap-4">
              <div className="skeleton h-24" />
              <div className="skeleton h-24" />
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <EmptyHint
              icon={<Newspaper />}
              title="Your newsletter will appear here"
              body="Paste updates, pick a template and brand, then press Generate. You can edit every block afterwards."
              action={
                <Button variant="primary" onClick={() => setPane("compose")} className="lg:hidden">
                  <Sparkles className="size-4" /> Start composing
                </Button>
              }
            />
          </div>
        )}

        {status === "generating" ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/70 backdrop-blur-sm animate-fade-up">
            <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-6 shadow-pop">
              <div className="flex items-center gap-3">
                <span className="flex size-10 items-center justify-center rounded-xl gradient-bg text-white">
                  <Sparkles className="size-5 animate-pulse" />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold">Generating your newsletter</p>
                  <p className="text-xs text-muted">{step || "Working…"}</p>
                </div>
              </div>
              <ol className="mt-5 space-y-2 text-xs">
                {["Preparing prompt", "Writing with the model", "Validating and picking images", "Rendering template"].map((s, i) => {
                  const idx = ["Preparing prompt", "Writing with the model", "Validating and picking images"].indexOf(step);
                  const state = i < idx ? "done" : i === idx ? "active" : "todo";
                  return (
                    <li key={s} className={cn("flex items-center gap-2", state === "todo" ? "text-faint" : "text-text")}>
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          state === "done" ? "bg-success" : state === "active" ? "bg-accent animate-pulse" : "bg-border-strong",
                        )}
                      />
                      {s}
                    </li>
                  );
                })}
              </ol>
              <div className="mt-5 flex justify-end">
                <Button size="sm" variant="ghost" onClick={cancel}>
                  <X className="size-4" /> Cancel
                </Button>
              </div>
            </div>
          </div>
        ) : null}

        {status === "error" && error && !html ? (
          <div className="mx-auto mt-4 max-w-xl rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm">
            <p className="font-semibold text-danger">Generation failed</p>
            <p className="mt-1 text-muted">{error}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
