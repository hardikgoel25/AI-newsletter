"use client";

import { FileText, Link, Plus, Rss, Sparkles, Trash, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { api } from "@/lib/api";
import { EXAMPLE_COMPANY, EXAMPLE_UPDATES } from "@/lib/example";
import { useStudio } from "@/lib/store";
import type { Source, SourceKind } from "@/lib/types";
import { cn, countWords } from "@/lib/utils";

import { Badge, Button, Input, Textarea } from "../ui";

const kindMeta: Record<SourceKind, { label: string; icon: React.ReactNode }> = {
  text: { label: "Text", icon: <FileText className="size-3.5" /> },
  file: { label: "File", icon: <Upload className="size-3.5" /> },
  url: { label: "URL", icon: <Link className="size-3.5" /> },
  feed: { label: "Feed", icon: <Rss className="size-3.5" /> },
};

export function ContentTab() {
  const sources = useStudio((s) => s.sources);
  const addSource = useStudio((s) => s.addSource);
  const updateSource = useStudio((s) => s.updateSource);
  const removeSource = useStudio((s) => s.removeSource);
  const setBrand = useStudio((s) => s.setBrand);
  const brand = useStudio((s) => s.brand);
  const toast = useStudio((s) => s.toast);
  const maxChars = 40_000;

  const fileRef = useRef<HTMLInputElement>(null);
  const [importMode, setImportMode] = useState<"url" | "feed" | null>(null);
  const [importUrl, setImportUrl] = useState("");
  const [importing, setImporting] = useState(false);

  const totalChars = sources.reduce((a, s) => a + s.text.length, 0);
  const isEmpty = sources.every((s) => !s.text.trim());

  async function handleFile(file: File) {
    setImporting(true);
    try {
      const res = await api.extract(file);
      addSource({ kind: "file", label: res.filename, text: res.text });
      toast(`Imported ${res.filename} (${res.chars.toLocaleString()} characters${res.pages ? `, ${res.pages} pages` : ""}).`, "success");
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setImporting(false);
    }
  }

  async function handleImport() {
    const url = importUrl.trim();
    if (!url) return;
    setImporting(true);
    try {
      if (importMode === "feed") {
        const res = await api.fetchFeed(url, 8);
        addSource({ kind: "feed", label: res.title || url, text: res.text });
        toast(`Imported ${res.items.length} feed items.`, "success");
      } else {
        const res = await api.fetchUrl(url);
        addSource({ kind: "url", label: res.title || res.site || url, text: res.text });
        toast(`Imported "${res.title || res.site}".`, "success");
      }
      setImportUrl("");
      setImportMode(null);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setImporting(false);
    }
  }

  function loadExample() {
    const first = sources[0];
    if (first && !first.text.trim()) updateSource(first.id, { text: EXAMPLE_UPDATES, label: "Company updates" });
    else addSource({ kind: "text", label: "Example updates", text: EXAMPLE_UPDATES });
    if (!brand.company_name) setBrand({ ...EXAMPLE_COMPANY });
    toast("Example content loaded. Press Generate.", "info");
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted">
          Paste updates, bullet points, meeting notes or press releases. Add several sources if you like.
        </p>
      </div>

      <div className="space-y-3">
        {sources.map((s, i) => (
          <SourceCard key={s.id} source={s} index={i} onChange={(p) => updateSource(s.id, p)} onRemove={() => removeSource(s.id)} canRemove={sources.length > 1 || Boolean(s.text)} />
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.markdown,.docx,.pdf,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
            e.target.value = "";
          }}
        />
        <Button size="sm" variant="outline" onClick={() => addSource({ kind: "text", label: `Notes ${sources.length + 1}`, text: "" })}>
          <Plus className="size-3.5" /> Text
        </Button>
        <Button size="sm" variant="outline" loading={importing && importMode === null} onClick={() => fileRef.current?.click()}>
          <Upload className="size-3.5" /> File
        </Button>
        <Button size="sm" variant={importMode === "url" ? "secondary" : "outline"} onClick={() => setImportMode(importMode === "url" ? null : "url")}>
          <Link className="size-3.5" /> URL
        </Button>
        <Button size="sm" variant={importMode === "feed" ? "secondary" : "outline"} onClick={() => setImportMode(importMode === "feed" ? null : "feed")}>
          <Rss className="size-3.5" /> RSS
        </Button>
      </div>

      {importMode ? (
        <div className="flex gap-2 animate-fade-up">
          <Input
            type="url"
            inputMode="url"
            placeholder={importMode === "feed" ? "https://example.com/feed.xml" : "https://example.com/press/launch"}
            value={importUrl}
            onChange={(e) => setImportUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleImport();
              }
            }}
            autoFocus
          />
          <Button variant="primary" loading={importing} onClick={handleImport}>
            Import
          </Button>
        </div>
      ) : null}

      <div className="flex items-center justify-between text-[11px] text-faint">
        <span className={cn(totalChars > maxChars && "text-danger")}>
          {totalChars.toLocaleString()} / {maxChars.toLocaleString()} characters
        </span>
        {isEmpty ? (
          <button type="button" onClick={loadExample} className="inline-flex items-center gap-1 text-accent hover:underline">
            <Sparkles className="size-3" /> Load example
          </button>
        ) : null}
      </div>
    </div>
  );
}

function SourceCard({
  source,
  index,
  onChange,
  onRemove,
  canRemove,
}: {
  source: Source;
  index: number;
  onChange: (p: Partial<Source>) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const meta = kindMeta[source.kind];
  return (
    <div className="rounded-2xl border border-border bg-surface p-3 shadow-soft">
      <div className="mb-2 flex items-center gap-2">
        <Badge tone={source.kind === "text" ? "neutral" : "accent"}>
          {meta.icon}
          {meta.label}
        </Badge>
        <input
          aria-label="Source label"
          className="min-w-0 flex-1 bg-transparent text-xs font-medium text-muted outline-none placeholder:text-faint"
          value={source.label}
          placeholder={`Source ${index + 1}`}
          onChange={(e) => onChange({ label: e.target.value })}
        />
        <span className="text-[11px] text-faint">{countWords(source.text)} words</span>
        {canRemove ? (
          <button type="button" onClick={onRemove} className="text-faint hover:text-danger" aria-label="Remove source">
            <Trash className="size-3.5" />
          </button>
        ) : null}
      </div>
      <Textarea
        rows={source.kind === "text" && index === 0 ? 12 : 5}
        value={source.text}
        placeholder={
          index === 0
            ? "• Launched AI Assistant 2.0\n• Crossed 100,000 active users\n• Partnered with Microsoft Azure\n• Opened Bangalore office\n• Hiring ML engineers"
            : "Paste content…"
        }
        maxLength={60_000}
        onChange={(e) => onChange({ text: e.target.value })}
        className="text-[13px]"
      />
    </div>
  );
}
