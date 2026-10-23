"use client";

import { FileText, Palette, Settings2, Sparkles, X } from "lucide-react";

import { useStudio, type ComposeTab as ComposeTabId } from "@/lib/store";

import { Button, Kbd, Segmented } from "../ui";
import { BrandTab } from "./BrandTab";
import { ContentTab } from "./ContentTab";
import { SettingsTab } from "./SettingsTab";

export function ComposePanel() {
  const tab = useStudio((s) => s.composeTab);
  const setTab = useStudio((s) => s.setComposeTab);
  const status = useStudio((s) => s.status);
  const generate = useStudio((s) => s.generate);
  const cancel = useStudio((s) => s.cancelGenerate);
  const sources = useStudio((s) => s.sources);
  const llm = useStudio((s) => s.llm);
  const healthError = useStudio((s) => s.healthError);
  const hasContent = sources.some((s) => s.text.trim());
  const generating = status === "generating";

  return (
    <aside className="flex h-full min-h-0 flex-col bg-surface" aria-label="Compose">
      <div className="shrink-0 border-b border-border px-3 py-2.5">
        <Segmented<ComposeTabId>
          className="w-full"
          value={tab}
          onChange={setTab}
          options={[
            { value: "content", label: (<><FileText className="size-4" /> Content</>) },
            { value: "settings", label: (<><Settings2 className="size-4" /> Settings</>) },
            { value: "brand", label: (<><Palette className="size-4" /> Brand</>) },
          ]}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {tab === "content" ? <ContentTab /> : tab === "settings" ? <SettingsTab /> : <BrandTab />}
      </div>

      <div className="shrink-0 border-t border-border bg-surface p-3">
        {generating ? (
          <Button variant="outline" size="lg" className="w-full" onClick={cancel}>
            <X className="size-4" /> Cancel generation
          </Button>
        ) : (
          <Button variant="primary" size="lg" className="w-full" disabled={!hasContent || Boolean(healthError)} onClick={() => void generate()}>
            <Sparkles className="size-4" />
            Generate newsletter
            <span className="ml-1 hidden items-center gap-0.5 sm:inline-flex opacity-80">
              <Kbd>⌘</Kbd>
              <Kbd>↵</Kbd>
            </span>
          </Button>
        )}
        <p className="mt-2 truncate text-center text-[11px] text-faint">
          {healthError ? "API offline — check the backend URL." : llm.model ? `Model: ${llm.model}` : "Model: server default"}
        </p>
      </div>
    </aside>
  );
}
