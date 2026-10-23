"use client";

import { KeyRound, LayoutTemplate, Moon, Newspaper, PanelRight, RotateCcwClock, Sun, Trash, X } from "lucide-react";
import { useState } from "react";

import { getAccessKey, setAccessKey } from "@/lib/api";
import { useStudio } from "@/lib/store";
import { cn, formatRelative } from "@/lib/utils";

import { ExportMenu } from "./ExportMenu";
import { Badge, Button, Input, MenuItem, Popover, Select } from "./ui";

export function Header() {
  const templates = useStudio((s) => s.templates);
  const render = useStudio((s) => s.render);
  const setRender = useStudio((s) => s.setRender);
  const appTheme = useStudio((s) => s.appTheme);
  const setAppTheme = useStudio((s) => s.setAppTheme);
  const health = useStudio((s) => s.health);
  const healthError = useStudio((s) => s.healthError);
  const newsletter = useStudio((s) => s.newsletter);
  const editorOpen = useStudio((s) => s.editorOpen);
  const setEditorOpen = useStudio((s) => s.setEditorOpen);
  const setPane = useStudio((s) => s.setPane);

  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");

  return (
    <header className="glass sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b border-border px-3 sm:px-4">
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="flex size-8 items-center justify-center rounded-xl gradient-bg text-white shadow-soft">
          <Newspaper className="size-4" />
        </span>
        <span className="hidden sm:flex flex-col leading-tight">
          <span className="text-sm font-semibold tracking-tight">Newsletter Studio</span>
          <span className="flex items-center gap-1.5 text-[11px] text-faint">
            <span
              className={cn("inline-block size-1.5 rounded-full", healthError ? "bg-danger" : health ? "bg-success" : "bg-warning")}
              aria-hidden
            />
            {healthError ? "API offline" : health ? `API v${health.version}` : "Connecting…"}
          </span>
        </span>
      </div>

      <div className="mx-auto flex items-center gap-2">
        <div className="hidden md:flex items-center gap-2">
          <LayoutTemplate className="size-4 text-faint" aria-hidden />
          <Select
            aria-label="Template"
            value={render.template}
            onChange={(e) => setRender({ template: e.target.value })}
            className="h-9 py-0 w-40 text-sm"
          >
            {(templates.length ? templates : [{ id: "modern", name: "Modern" }]).map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <HistoryButton />
        <SettingsButton accessKeyRequired={Boolean(health?.access_key_required)} />
        <Button
          size="icon"
          variant="ghost"
          aria-label="Toggle app theme"
          title={`Theme: ${appTheme}`}
          onClick={() => setAppTheme(appTheme === "dark" || (appTheme === "system" && isDark) ? "light" : "dark")}
        >
          <Sun className="size-4 dark:hidden" />
          <Moon className="size-4 hidden dark:block" />
        </Button>
        {newsletter ? (
          <Button
            size="icon"
            variant={editorOpen ? "secondary" : "ghost"}
            className="xl:hidden"
            aria-label="Toggle editor"
            onClick={() => {
              setEditorOpen(!editorOpen);
              setPane("edit");
            }}
          >
            <PanelRight className="size-4" />
          </Button>
        ) : null}
        <ExportMenu />
      </div>
    </header>
  );
}

function HistoryButton() {
  const [open, setOpen] = useState(false);
  const history = useStudio((s) => s.history);
  const restore = useStudio((s) => s.restoreHistory);
  const remove = useStudio((s) => s.deleteHistory);
  const clear = useStudio((s) => s.clearHistory);
  return (
    <div className="relative">
      <Button size="icon" variant="ghost" aria-label="History" title="History" onClick={() => setOpen((v) => !v)}>
        <RotateCcwClock className="size-4" />
      </Button>
      <Popover open={open} onClose={() => setOpen(false)} className="w-80">
        <div className="flex items-center justify-between px-2.5 py-1.5">
          <span className="text-xs font-semibold text-muted">Recent newsletters</span>
          {history.length ? (
            <button type="button" className="text-[11px] text-faint hover:text-danger" onClick={clear}>
              Clear all
            </button>
          ) : null}
        </div>
        {history.length === 0 ? (
          <p className="px-2.5 pb-3 pt-1 text-xs text-faint">Generated newsletters are kept here on this device.</p>
        ) : (
          <ul className="max-h-80 overflow-y-auto">
            {history.map((h) => (
              <li key={h.id} className="group flex items-center gap-2 rounded-xl px-2.5 py-2 hover:bg-surface-3">
                <button
                  type="button"
                  className="flex-1 min-w-0 text-left"
                  onClick={() => {
                    restore(h.id);
                    setOpen(false);
                  }}
                >
                  <span className="block truncate text-sm text-text">{h.title || "Untitled"}</span>
                  <span className="block truncate text-[11px] text-faint">
                    {h.company || "—"} · {formatRelative(h.createdAt)}
                  </span>
                </button>
                <button
                  type="button"
                  aria-label="Delete"
                  className="text-faint opacity-0 transition group-hover:opacity-100 hover:text-danger"
                  onClick={() => remove(h.id)}
                >
                  <Trash className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Popover>
    </div>
  );
}

function SettingsButton({ accessKeyRequired }: { accessKeyRequired: boolean }) {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState("");
  const loadCatalogs = useStudio((s) => s.loadCatalogs);
  const toast = useStudio((s) => s.toast);
  const models = useStudio((s) => s.models);
  const llm = useStudio((s) => s.llm);
  const setLLM = useStudio((s) => s.setLLM);

  return (
    <div className="relative">
      <Button
        size="icon"
        variant="ghost"
        aria-label="Connection settings"
        title="Connection settings"
        onClick={() => {
          setKey(getAccessKey());
          setOpen((v) => !v);
        }}
      >
        <KeyRound className="size-4" />
        {accessKeyRequired && !getAccessKey() ? <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-danger" /> : null}
      </Button>
      <Popover open={open} onClose={() => setOpen(false)} className="w-80 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-muted">Connection</span>
          <button type="button" onClick={() => setOpen(false)} className="text-faint hover:text-text" aria-label="Close">
            <X className="size-4" />
          </button>
        </div>
        <label className="text-xs text-muted">Model</label>
        <Select
          className="mt-1 mb-3"
          value={llm.model ?? ""}
          onChange={(e) => {
            const m = models.find((x) => x.id === e.target.value);
            setLLM({ model: e.target.value || null, provider: m?.provider ?? llm.provider });
          }}
        >
          <option value="">Server default</option>
          {models.map((m) => (
            <option key={`${m.provider}:${m.id}`} value={m.id}>
              {m.provider} · {m.label}
            </option>
          ))}
        </Select>
        <label className="text-xs text-muted">
          Access key {accessKeyRequired ? <Badge tone="danger">required</Badge> : <Badge>optional</Badge>}
        </label>
        <Input className="mt-1" type="password" placeholder="X-App-Key" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
        <p className="mt-1.5 text-[11px] text-faint">Only needed if the API was deployed with APP_ACCESS_KEY. Stored on this device.</p>
        <div className="mt-3 flex justify-end gap-2">
          <MenuItem
            onClick={() => {
              setAccessKey(key.trim());
              setOpen(false);
              toast("Connection settings saved.", "success");
              void loadCatalogs();
            }}
          >
            Save
          </MenuItem>
        </div>
      </Popover>
    </div>
  );
}
