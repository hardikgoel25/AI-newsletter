"use client";

import { ImagePlus, Search, Upload, WandSparkles, X } from "lucide-react";
import { useRef, useState } from "react";

import { api } from "@/lib/api";
import { useStudio } from "@/lib/store";
import type { BrandKit, HeroImage, ImageSearchResult, Theme } from "@/lib/types";
import { cn } from "@/lib/utils";

import { Badge, Button, Input, Spinner } from "../ui";

export function HeroImagePicker({
  value,
  onChange,
  brand,
  theme,
  companyName,
  suggestedQuery,
}: {
  value: HeroImage | null;
  onChange: (h: HeroImage | null) => void;
  brand: BrandKit;
  theme: Theme;
  companyName: string;
  suggestedQuery?: string;
}) {
  const unsplashEnabled = useStudio((s) => Boolean(s.health?.unsplash));
  const toast = useStudio((s) => s.toast);
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [query, setQuery] = useState(suggestedQuery ?? "");
  const [results, setResults] = useState<ImageSearchResult[] | null>(null);

  async function upload(file: File) {
    setBusy("upload");
    try {
      const res = await api.uploadImage(file, "hero");
      onChange({ kind: "upload", src: res.data_uri, alt: file.name.replace(/\.[^.]+$/, ""), credit: null });
      setResults(null);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  async function search() {
    if (!query.trim()) return;
    setBusy("search");
    try {
      setResults(await api.searchImages(query.trim(), 9));
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  async function pick(r: ImageSearchResult) {
    setBusy(r.id);
    try {
      onChange(await api.selectImage(r));
      setResults(null);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  async function generated() {
    setBusy("generated");
    try {
      onChange(await api.generatedBanner(brand, theme, companyName));
      setResults(null);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-xl border border-border bg-surface-2">
        {value?.src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={value.src} alt={value.alt || "Hero"} className="aspect-video w-full object-cover" />
        ) : (
          <div className="flex aspect-video items-center justify-center text-faint">
            <ImagePlus className="size-6" />
          </div>
        )}
        {value?.src ? (
          <>
            <Badge className="absolute left-2 top-2 bg-black/60 text-white">{value.kind}</Badge>
            <button
              type="button"
              aria-label="Remove image"
              onClick={() => onChange({ kind: "none", src: "", alt: "", credit: null })}
              className="absolute right-2 top-2 flex size-7 items-center justify-center rounded-lg bg-black/60 text-white hover:bg-black/80"
            >
              <X className="size-4" />
            </button>
          </>
        ) : null}
        {value?.credit?.name ? (
          <p className="px-2 py-1 text-[10px] text-faint">
            Photo by {value.credit.name} on {value.credit.source}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void upload(f);
            e.target.value = "";
          }}
        />
        <Button size="sm" variant="outline" loading={busy === "upload"} onClick={() => fileRef.current?.click()}>
          <Upload className="size-3.5" /> Upload
        </Button>
        <Button size="sm" variant="outline" loading={busy === "generated"} onClick={generated}>
          <WandSparkles className="size-3.5" /> Generated banner
        </Button>
      </div>

      {unsplashEnabled ? (
        <div>
          <div className="flex gap-2">
            <Input
              placeholder="Search Unsplash (e.g. modern office)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void search();
                }
              }}
            />
            <Button size="md" variant="secondary" loading={busy === "search"} onClick={search} aria-label="Search">
              <Search className="size-4" />
            </Button>
          </div>
          {results ? (
            results.length ? (
              <div className="mt-2 grid grid-cols-3 gap-1.5">
                {results.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    title={`${r.alt} — ${r.author}`}
                    onClick={() => pick(r)}
                    className={cn("relative aspect-[4/3] overflow-hidden rounded-lg border border-border", busy === r.id && "opacity-60")}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={r.thumb} alt={r.alt} className="h-full w-full object-cover transition hover:scale-105" loading="lazy" />
                    {busy === r.id ? (
                      <span className="absolute inset-0 flex items-center justify-center bg-black/40">
                        <Spinner className="text-white" />
                      </span>
                    ) : null}
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-xs text-faint">No photos found. Try different words.</p>
            )
          ) : null}
        </div>
      ) : (
        <p className="text-[11px] text-faint">Stock photo search is off (no Unsplash key on the server). Upload or use a generated banner.</p>
      )}
    </div>
  );
}
