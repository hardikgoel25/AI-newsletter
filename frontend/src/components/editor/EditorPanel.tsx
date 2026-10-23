"use client";

import { ChevronDown, ChevronUp, Plus, RefreshCw, Trash, WandSparkles, X } from "lucide-react";
import { useState } from "react";

import { useStudio } from "@/lib/store";
import type { Highlight, Newsletter, Section, Stat } from "@/lib/types";
import { cn, countWords, uid } from "@/lib/utils";

import { Button, Field, Input, SectionTitle, Textarea } from "../ui";
import { HeroImagePicker } from "./HeroImagePicker";

function Group({ title, children, defaultOpen = true, count }: { title: string; children: React.ReactNode; defaultOpen?: boolean; count?: number }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="border-b border-border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-surface-2"
        aria-expanded={open}
      >
        <span className="text-sm font-semibold">
          {title}
          {typeof count === "number" ? <span className="ml-2 text-xs font-normal text-faint">{count}</span> : null}
        </span>
        <ChevronDown className={cn("size-4 text-faint transition-transform", open && "rotate-180")} />
      </button>
      {open ? <div className="space-y-3 px-4 pb-4 animate-fade-up">{children}</div> : null}
    </section>
  );
}

function move<T>(arr: T[], from: number, to: number): T[] {
  if (to < 0 || to >= arr.length) return arr;
  const next = arr.slice();
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

export function EditorPanel() {
  const n = useStudio((s) => s.newsletter);
  const update = useStudio((s) => s.updateNewsletter);
  const brand = useStudio((s) => s.brand);
  const render = useStudio((s) => s.render);
  const regenerate = useStudio((s) => s.regenerateSection);
  const setEditorOpen = useStudio((s) => s.setEditorOpen);

  if (!n) return null;

  const patch = (p: Partial<Newsletter>) => update((cur) => ({ ...cur, ...p }));

  return (
    <aside className="flex h-full min-h-0 flex-col bg-surface" aria-label="Editor">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-4">
        <div>
          <p className="text-sm font-semibold">Edit newsletter</p>
          <p className="text-[11px] text-faint">Changes re-render the preview live</p>
        </div>
        <Button size="icon" variant="ghost" className="xl:hidden" aria-label="Close editor" onClick={() => setEditorOpen(false)}>
          <X className="size-4" />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <Group title="Headline">
          <Field label="Hero title" hint={`${n.hero_title.length}/160`}>
            <Textarea rows={2} value={n.hero_title} maxLength={160} onChange={(e) => patch({ hero_title: e.target.value })} className="min-h-0 font-semibold" />
          </Field>
          <Field label="Subtitle" hint={`${n.subtitle.length}/300`}>
            <Textarea rows={2} value={n.subtitle} maxLength={300} onChange={(e) => patch({ subtitle: e.target.value })} className="min-h-0" />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Date">
              <Input value={n.date} onChange={(e) => patch({ date: e.target.value })} />
            </Field>
            <Field label="Read time">
              <Input value={n.estimated_read_time} onChange={(e) => patch({ estimated_read_time: e.target.value })} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Company">
              <Input value={n.company_name} onChange={(e) => patch({ company_name: e.target.value })} />
            </Field>
            <Field label="Type label">
              <Input value={n.newsletter_type} onChange={(e) => patch({ newsletter_type: e.target.value })} />
            </Field>
          </div>
        </Group>

        <Group title="Hero image" defaultOpen={false}>
          <HeroImagePicker
            value={n.hero_image}
            onChange={(h) => patch({ hero_image: h ?? { kind: "none", src: "", alt: "", credit: null } })}
            brand={brand}
            theme={render.theme}
            companyName={n.company_name}
            suggestedQuery={n.image_keywords[0]}
          />
          {n.image_keywords.length ? (
            <p className="text-[11px] text-faint">Suggested searches: {n.image_keywords.join(", ")}</p>
          ) : null}
        </Group>

        <Group title="Executive summary">
          <Field label="Summary" hint={`${countWords(n.summary)} words`}>
            <Textarea rows={6} value={n.summary} onChange={(e) => patch({ summary: e.target.value })} />
          </Field>
        </Group>

        <Group title="Highlights" count={n.highlights.length}>
          {n.highlights.map((h, i) => (
            <div key={i} className="rounded-xl border border-border bg-surface-2 p-2.5 space-y-2">
              <div className="flex gap-2">
                <Input
                  aria-label="Icon"
                  className="w-12 text-center px-1"
                  value={h.icon}
                  maxLength={8}
                  onChange={(e) => patch({ highlights: n.highlights.map((x, j) => (j === i ? { ...x, icon: e.target.value } : x)) })}
                />
                <Input
                  aria-label="Title"
                  placeholder="Title"
                  value={h.title}
                  maxLength={120}
                  onChange={(e) => patch({ highlights: n.highlights.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)) })}
                />
                <RowActions
                  onUp={() => patch({ highlights: move(n.highlights, i, i - 1) })}
                  onDown={() => patch({ highlights: move(n.highlights, i, i + 1) })}
                  onDelete={() => patch({ highlights: n.highlights.filter((_, j) => j !== i) })}
                />
              </div>
              <Input
                aria-label="Subtitle"
                placeholder="Subtitle"
                value={h.subtitle}
                maxLength={260}
                onChange={(e) => patch({ highlights: n.highlights.map((x, j) => (j === i ? { ...x, subtitle: e.target.value } : x)) })}
              />
            </div>
          ))}
          <Button
            size="sm"
            variant="outline"
            disabled={n.highlights.length >= 8}
            onClick={() => patch({ highlights: [...n.highlights, { icon: "⭐", title: "", subtitle: "" } as Highlight] })}
          >
            <Plus className="size-3.5" /> Add highlight
          </Button>
        </Group>

        <Group title="Key numbers" count={n.stats.length} defaultOpen={n.stats.length > 0}>
          {n.stats.map((s, i) => (
            <div key={i} className="flex gap-2">
              <Input aria-label="Value" placeholder="100k" className="w-24" value={s.value} onChange={(e) => patch({ stats: n.stats.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)) })} />
              <Input aria-label="Label" placeholder="active users" value={s.label} onChange={(e) => patch({ stats: n.stats.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)) })} />
              <Button size="icon" variant="ghost" aria-label="Delete" onClick={() => patch({ stats: n.stats.filter((_, j) => j !== i) })}>
                <Trash className="size-4" />
              </Button>
            </div>
          ))}
          <Button size="sm" variant="outline" disabled={n.stats.length >= 4} onClick={() => patch({ stats: [...n.stats, { value: "", label: "" } as Stat] })}>
            <Plus className="size-3.5" /> Add number
          </Button>
        </Group>

        <Group title="Sections" count={n.sections.length}>
          {n.sections.map((s, i) => (
            <SectionCard
              key={s.id}
              section={s}
              index={i}
              total={n.sections.length}
              onChange={(next) => patch({ sections: n.sections.map((x, j) => (j === i ? next : x)) })}
              onUp={() => patch({ sections: move(n.sections, i, i - 1) })}
              onDown={() => patch({ sections: move(n.sections, i, i + 1) })}
              onDelete={() => patch({ sections: n.sections.filter((_, j) => j !== i) })}
              onRegenerate={(instruction) => regenerate(i, instruction)}
            />
          ))}
          <Button
            size="sm"
            variant="outline"
            disabled={n.sections.length >= 10}
            onClick={() => patch({ sections: [...n.sections, { id: uid("s"), icon: "📰", title: "New section", content: "" }] })}
          >
            <Plus className="size-3.5" /> Add section
          </Button>
        </Group>

        <Group title="Quote" defaultOpen={Boolean(n.quote)}>
          <Field label="Quote text">
            <Textarea rows={3} value={n.quote?.text ?? ""} onChange={(e) => patch({ quote: { text: e.target.value, attribution: n.quote?.attribution ?? "" } })} />
          </Field>
          <Field label="Attribution">
            <Input value={n.quote?.attribution ?? ""} onChange={(e) => patch({ quote: { text: n.quote?.text ?? "", attribution: e.target.value } })} />
          </Field>
          {n.quote ? (
            <Button size="sm" variant="ghost" onClick={() => patch({ quote: null })}>
              <Trash className="size-3.5" /> Remove quote
            </Button>
          ) : null}
        </Group>

        <Group title="Call to action" defaultOpen={Boolean(n.cta)}>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Label">
              <Input value={n.cta?.label ?? ""} onChange={(e) => patch({ cta: { label: e.target.value, url: n.cta?.url ?? "" } })} />
            </Field>
            <Field label="URL">
              <Input placeholder="https://" value={n.cta?.url ?? ""} onChange={(e) => patch({ cta: { label: n.cta?.label ?? "", url: e.target.value } })} />
            </Field>
          </div>
          {n.cta ? (
            <Button size="sm" variant="ghost" onClick={() => patch({ cta: null })}>
              <Trash className="size-3.5" /> Remove CTA
            </Button>
          ) : null}
        </Group>

        <Group title="Footer" defaultOpen={false}>
          <SectionTitle>Shown at the bottom of the newsletter</SectionTitle>
          <Field label="Tagline">
            <Input value={n.footer.tagline} onChange={(e) => patch({ footer: { ...n.footer, tagline: e.target.value } })} />
          </Field>
          <Field label="Subscription note">
            <Textarea rows={2} className="min-h-0" value={n.footer.subscription_note} onChange={(e) => patch({ footer: { ...n.footer, subscription_note: e.target.value } })} />
          </Field>
          <Field label="Copyright">
            <Input value={n.footer.copyright} onChange={(e) => patch({ footer: { ...n.footer, copyright: e.target.value } })} />
          </Field>
          <p className="text-[11px] text-faint">Contact details and social links come from the Brand tab.</p>
        </Group>
      </div>
    </aside>
  );
}

function RowActions({ onUp, onDown, onDelete }: { onUp: () => void; onDown: () => void; onDelete: () => void }) {
  return (
    <div className="flex shrink-0 items-center">
      <Button size="icon" variant="ghost" className="size-8" aria-label="Move up" onClick={onUp}>
        <ChevronUp className="size-4" />
      </Button>
      <Button size="icon" variant="ghost" className="size-8" aria-label="Move down" onClick={onDown}>
        <ChevronDown className="size-4" />
      </Button>
      <Button size="icon" variant="ghost" className="size-8 hover:text-danger" aria-label="Delete" onClick={onDelete}>
        <Trash className="size-4" />
      </Button>
    </div>
  );
}

function SectionCard({
  section,
  index,
  total,
  onChange,
  onUp,
  onDown,
  onDelete,
  onRegenerate,
}: {
  section: Section;
  index: number;
  total: number;
  onChange: (s: Section) => void;
  onUp: () => void;
  onDown: () => void;
  onDelete: () => void;
  onRegenerate: (instruction: string) => Promise<void>;
}) {
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [showRegen, setShowRegen] = useState(false);
  return (
    <div className="rounded-xl border border-border bg-surface-2 p-2.5 space-y-2">
      <div className="flex gap-2">
        <Input aria-label="Icon" className="w-12 text-center px-1" value={section.icon} maxLength={8} onChange={(e) => onChange({ ...section, icon: e.target.value })} />
        <Input aria-label="Section title" className="font-medium" value={section.title} maxLength={160} onChange={(e) => onChange({ ...section, title: e.target.value })} />
        <RowActions onUp={onUp} onDown={onDown} onDelete={onDelete} />
      </div>
      <Textarea rows={6} value={section.content} onChange={(e) => onChange({ ...section, content: e.target.value })} aria-label="Section content" />
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-faint">
          {index + 1}/{total} · {countWords(section.content)} words · Markdown supported
        </span>
        <Button size="sm" variant="ghost" onClick={() => setShowRegen((v) => !v)}>
          <WandSparkles className="size-3.5" /> Rewrite
        </Button>
      </div>
      {showRegen ? (
        <div className="flex gap-2 animate-fade-up">
          <Input
            placeholder="Instruction (optional): shorter, more technical, add a bullet list…"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={async (e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                setBusy(true);
                await onRegenerate(instruction);
                setBusy(false);
              }
            }}
          />
          <Button
            size="md"
            variant="primary"
            loading={busy}
            onClick={async () => {
              setBusy(true);
              await onRegenerate(instruction);
              setBusy(false);
            }}
            aria-label="Rewrite section"
          >
            <RefreshCw className="size-4" />
          </Button>
        </div>
      ) : null}
    </div>
  );
}
