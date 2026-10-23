"use client";

import { useStudio } from "@/lib/store";
import { NEWSLETTER_TYPES, READING_TIMES, TONES, type AutoHero } from "@/lib/types";

import { HeroImagePicker } from "../editor/HeroImagePicker";
import { Divider, Field, Input, Range, SectionTitle, Segmented, Select, Switch, Textarea } from "../ui";

const LANGUAGES = ["English", "German", "French", "Spanish", "Italian", "Portuguese", "Dutch", "Hindi", "Japanese", "Chinese", "Arabic"];

export function SettingsTab() {
  const options = useStudio((s) => s.options);
  const setOptions = useStudio((s) => s.setOptions);
  const llm = useStudio((s) => s.llm);
  const setLLM = useStudio((s) => s.setLLM);
  const models = useStudio((s) => s.models);
  const autoHero = useStudio((s) => s.autoHero);
  const setAutoHero = useStudio((s) => s.setAutoHero);
  const customHero = useStudio((s) => s.customHero);
  const setCustomHero = useStudio((s) => s.setCustomHero);
  const brand = useStudio((s) => s.brand);
  const render = useStudio((s) => s.render);
  const unsplash = useStudio((s) => Boolean(s.health?.unsplash));

  return (
    <div className="space-y-4">
      <SectionTitle>Format</SectionTitle>
      <Field label="Newsletter type">
        <Select value={options.newsletter_type} onChange={(e) => setOptions({ newsletter_type: e.target.value as typeof options.newsletter_type })}>
          {NEWSLETTER_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
      </Field>
      {options.newsletter_type === "Custom" ? (
        <Field label="Describe the newsletter">
          <Input
            placeholder="e.g. Quarterly sustainability report for partners"
            value={options.custom_type_instruction}
            maxLength={400}
            onChange={(e) => setOptions({ custom_type_instruction: e.target.value })}
          />
        </Field>
      ) : null}
      <div className="grid grid-cols-2 gap-3">
        <Field label="Tone">
          <Select value={options.tone} onChange={(e) => setOptions({ tone: e.target.value as typeof options.tone })}>
            {TONES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Language">
          <Input list="ains-languages" value={options.language} maxLength={40} onChange={(e) => setOptions({ language: e.target.value })} />
          <datalist id="ains-languages">
            {LANGUAGES.map((l) => (
              <option key={l} value={l} />
            ))}
          </datalist>
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Reading time">
          <Select value={options.reading_time} onChange={(e) => setOptions({ reading_time: e.target.value })}>
            {READING_TIMES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Publication date" hint="optional">
          <Input placeholder="October 2026" value={options.publication_date} maxLength={60} onChange={(e) => setOptions({ publication_date: e.target.value })} />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Range label="Highlights" min={2} max={8} value={options.highlight_count} onChange={(v) => setOptions({ highlight_count: v })} />
        <Range label="Sections" min={2} max={8} value={options.section_count} onChange={(v) => setOptions({ section_count: v })} />
      </div>

      <Divider />
      <SectionTitle>Blocks</SectionTitle>
      <div className="space-y-2">
        <Switch label="Key numbers row" description="Pull 2–4 stats from the content" checked={options.include_stats} onChange={(v) => setOptions({ include_stats: v })} />
        <Switch label="Pull quote" description="Only if a quotable line exists" checked={options.include_quote} onChange={(v) => setOptions({ include_quote: v })} />
        <Switch label="Call to action" description="Button with a link from the content" checked={options.include_cta} onChange={(v) => setOptions({ include_cta: v })} />
      </div>

      <Divider />
      <SectionTitle>Hero image</SectionTitle>
      <Segmented<AutoHero>
        className="w-full"
        value={autoHero}
        onChange={setAutoHero}
        options={[
          { value: "unsplash", label: "Stock photo", title: unsplash ? "Search Unsplash automatically" : "Unsplash key not configured; falls back to generated" },
          { value: "generated", label: "Generated" },
          { value: "none", label: "None" },
        ]}
      />
      {!unsplash && autoHero === "unsplash" ? (
        <p className="text-[11px] text-warning">Unsplash is not configured on the server. A generated banner will be used instead.</p>
      ) : null}
      <details className="group rounded-xl border border-border bg-surface-2 p-3">
        <summary className="cursor-pointer text-xs font-medium text-muted group-open:mb-3">Use my own image instead</summary>
        <HeroImagePicker value={customHero} onChange={setCustomHero} brand={brand} theme={render.theme} companyName={brand.company_name} />
      </details>

      <Divider />
      <SectionTitle>Overrides</SectionTitle>
      <Field label="Headline" hint="leave empty for AI">
        <Input value={options.hero_title_override} maxLength={160} onChange={(e) => setOptions({ hero_title_override: e.target.value })} />
      </Field>
      <Field label="Executive summary" hint="leave empty for AI">
        <Textarea rows={3} value={options.summary_override} maxLength={2500} onChange={(e) => setOptions({ summary_override: e.target.value })} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="CTA label">
          <Input
            value={options.cta_override?.label ?? ""}
            maxLength={80}
            onChange={(e) => setOptions({ cta_override: { label: e.target.value, url: options.cta_override?.url ?? "" } })}
          />
        </Field>
        <Field label="CTA URL">
          <Input
            placeholder="https://"
            value={options.cta_override?.url ?? ""}
            onChange={(e) => setOptions({ cta_override: { label: options.cta_override?.label ?? "", url: e.target.value } })}
          />
        </Field>
      </div>
      <Field label="Extra instructions" hint={`${options.extra_instructions.length}/2000`}>
        <Textarea
          rows={3}
          placeholder="e.g. Lead with the funding news. Mention the Berlin event in every section where relevant. Avoid exclamation marks."
          value={options.extra_instructions}
          maxLength={2000}
          onChange={(e) => setOptions({ extra_instructions: e.target.value })}
        />
      </Field>

      <Divider />
      <SectionTitle>Model</SectionTitle>
      <Field label="Model">
        <Select
          value={llm.model ?? ""}
          onChange={(e) => {
            const m = models.find((x) => x.id === e.target.value);
            setLLM({ model: e.target.value || null, provider: m?.provider ?? null });
          }}
        >
          <option value="">Server default</option>
          {models.map((m) => (
            <option key={`${m.provider}:${m.id}`} value={m.id}>
              {m.provider} · {m.label}
            </option>
          ))}
        </Select>
      </Field>
      <Range label="Creativity (temperature)" min={0} max={10} value={Math.round(llm.temperature * 10)} onChange={(v) => setLLM({ temperature: v / 10 })} />
    </div>
  );
}
