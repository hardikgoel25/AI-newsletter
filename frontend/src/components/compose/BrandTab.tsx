"use client";

import { Check, Download, Pipette, Save, Trash, Upload, X } from "lucide-react";
import { useRef, useState } from "react";

import { api } from "@/lib/api";
import { useStudio } from "@/lib/store";
import { DEFAULT_BRAND, type BrandKit, type LogoInvert } from "@/lib/types";
import { cn, derivePalette, downloadText, isHexColor } from "@/lib/utils";

import { Button, Divider, Field, Input, SectionTitle, Segmented, Select, Textarea } from "../ui";

export function BrandTab() {
  const brand = useStudio((s) => s.brand);
  const setBrand = useStudio((s) => s.setBrand);
  const replaceBrand = useStudio((s) => s.replaceBrand);
  const presets = useStudio((s) => s.presets);
  const savedBrands = useStudio((s) => s.savedBrands);
  const saveBrand = useStudio((s) => s.saveBrand);
  const deleteSavedBrand = useStudio((s) => s.deleteSavedBrand);
  const fonts = useStudio((s) => s.fonts);
  const toast = useStudio((s) => s.toast);
  const templates = useStudio((s) => s.templates);
  const render = useStudio((s) => s.render);

  const logoRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveName, setSaveName] = useState("");

  const templateFonts = templates.find((t) => t.id === render.template)?.default_fonts;

  async function uploadLogo(file: File) {
    setUploading(true);
    try {
      const res = await api.uploadImage(file, "logo");
      setBrand({ logo: res.data_uri });
      toast("Logo uploaded and sanitised.", "success");
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setUploading(false);
    }
  }

  function importKit(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(String(reader.result)) as Partial<BrandKit>;
        const kit: BrandKit = { ...DEFAULT_BRAND, ...data, socials: { ...DEFAULT_BRAND.socials, ...(data.socials ?? {}) }, id: "custom" };
        if (!isHexColor(kit.primary) || !isHexColor(kit.secondary) || !isHexColor(kit.accent)) throw new Error("Invalid colours");
        replaceBrand(kit);
        toast(`Imported brand kit "${kit.name}".`, "success");
      } catch {
        toast("That file is not a valid brand kit.", "error");
      }
    };
    reader.readAsText(file);
  }

  return (
    <div className="space-y-4">
      <SectionTitle>Presets</SectionTitle>
      <div className="flex flex-wrap gap-2">
        {[...presets, ...savedBrands].map((p) => {
          const active = brand.id === p.id;
          return (
            <div key={p.id} className="group relative">
              <button
                type="button"
                onClick={() => replaceBrand(p)}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition",
                  active ? "border-accent bg-accent/10 text-text" : "border-border bg-surface text-muted hover:border-border-strong hover:text-text",
                )}
              >
                <span className="flex -space-x-1">
                  <span className="size-3 rounded-full ring-1 ring-surface" style={{ background: p.primary }} />
                  <span className="size-3 rounded-full ring-1 ring-surface" style={{ background: p.secondary }} />
                  <span className="size-3 rounded-full ring-1 ring-surface" style={{ background: p.accent }} />
                </span>
                {p.name}
                {active ? <Check className="size-3" /> : null}
              </button>
              {savedBrands.some((b) => b.id === p.id) ? (
                <button
                  type="button"
                  aria-label={`Delete ${p.name}`}
                  onClick={() => deleteSavedBrand(p.id)}
                  className="absolute -right-1 -top-1 hidden size-4 items-center justify-center rounded-full bg-danger text-white group-hover:flex"
                >
                  <X className="size-2.5" />
                </button>
              ) : null}
            </div>
          );
        })}
      </div>

      <Divider />
      <SectionTitle>Identity</SectionTitle>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Company name">
          <Input value={brand.company_name} maxLength={120} onChange={(e) => setBrand({ company_name: e.target.value })} placeholder="Acme Inc." />
        </Field>
        <Field label="Tagline">
          <Input value={brand.tagline} maxLength={120} onChange={(e) => setBrand({ tagline: e.target.value })} placeholder="Reimagining motion" />
        </Field>
      </div>

      <div>
        <Field label="Logo" hint="SVG, PNG, JPG · sanitised on upload">
          <div className="flex items-center gap-3 rounded-xl border border-border bg-surface-2 p-3">
            <div className="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-surface">
              {brand.logo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={brand.logo} alt="Logo" className="max-h-12 max-w-12 object-contain" />
              ) : (
                <span className="text-xs text-faint">None</span>
              )}
            </div>
            <div className="flex flex-1 flex-wrap gap-2">
              <input
                ref={logoRef}
                type="file"
                accept=".svg,.png,.jpg,.jpeg,.webp,.gif,image/*"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void uploadLogo(f);
                  e.target.value = "";
                }}
              />
              <Button size="sm" variant="outline" loading={uploading} onClick={() => logoRef.current?.click()}>
                <Upload className="size-3.5" /> Upload
              </Button>
              {brand.logo ? (
                <Button size="sm" variant="ghost" onClick={() => setBrand({ logo: "" })}>
                  <Trash className="size-3.5" /> Remove
                </Button>
              ) : null}
            </div>
          </div>
        </Field>
        {brand.logo ? (
          <div className="mt-2">
            <Segmented<LogoInvert>
              size="sm"
              className="w-full"
              value={brand.logo_invert}
              onChange={(v) => setBrand({ logo_invert: v })}
              options={[
                { value: "never", label: "Keep colours" },
                { value: "on-dark", label: "White on dark" },
                { value: "always", label: "Always white" },
              ]}
            />
          </div>
        ) : null}
      </div>

      <Divider />
      <SectionTitle
        action={
          <button
            type="button"
            className="inline-flex items-center gap-1 text-[11px] text-accent hover:underline"
            onClick={() => setBrand(derivePalette(brand.primary))}
          >
            <Pipette className="size-3" /> Auto palette from primary
          </button>
        }
      >
        Colours
      </SectionTitle>
      <div className="grid grid-cols-3 gap-3">
        {(["primary", "secondary", "accent"] as const).map((key) => (
          <ColorField key={key} label={key} value={brand[key]} onChange={(v) => setBrand({ [key]: v })} />
        ))}
      </div>
      <div className="h-3 w-full rounded-full" style={{ background: `linear-gradient(120deg, ${brand.primary}, ${brand.secondary} 55%, ${brand.accent})` }} />

      <div className="grid grid-cols-2 gap-3">
        <Field label="Heading font">
          <Select value={brand.font_heading} onChange={(e) => setBrand({ font_heading: e.target.value })}>
            <option value="">Template default{templateFonts ? ` (${templateFonts.heading})` : ""}</option>
            {fonts.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Body font">
          <Select value={brand.font_body} onChange={(e) => setBrand({ font_body: e.target.value })}>
            <option value="">Template default{templateFonts ? ` (${templateFonts.body})` : ""}</option>
            {fonts.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <Divider />
      <SectionTitle>Contact</SectionTitle>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Website">
          <Input type="url" value={brand.website} placeholder="https://acme.com" onChange={(e) => setBrand({ website: e.target.value })} />
        </Field>
        <Field label="Email">
          <Input type="email" value={brand.contact_email} placeholder="hello@acme.com" onChange={(e) => setBrand({ contact_email: e.target.value })} />
        </Field>
        <Field label="Phone">
          <Input value={brand.phone} onChange={(e) => setBrand({ phone: e.target.value })} />
        </Field>
        <Field label="Address">
          <Input value={brand.address} onChange={(e) => setBrand({ address: e.target.value })} />
        </Field>
      </div>

      <SectionTitle>Social links</SectionTitle>
      <div className="grid grid-cols-2 gap-3">
        {(
          [
            ["linkedin", "LinkedIn"],
            ["x", "X / Twitter"],
            ["instagram", "Instagram"],
            ["facebook", "Facebook"],
            ["youtube", "YouTube"],
            ["github", "GitHub"],
          ] as const
        ).map(([key, label]) => (
          <Field key={key} label={label}>
            <Input
              type="url"
              placeholder="https://"
              value={brand.socials[key]}
              onChange={(e) => setBrand({ socials: { ...brand.socials, [key]: e.target.value } })}
            />
          </Field>
        ))}
      </div>

      <SectionTitle>Footer</SectionTitle>
      <Field label="Subscription note">
        <Textarea rows={2} className="min-h-0" value={brand.subscription_note} placeholder="You are receiving this newsletter because…" onChange={(e) => setBrand({ subscription_note: e.target.value })} />
      </Field>
      <div className="grid grid-cols-3 gap-3">
        <Field label="Privacy URL">
          <Input type="url" value={brand.privacy_url} onChange={(e) => setBrand({ privacy_url: e.target.value })} />
        </Field>
        <Field label="Terms URL">
          <Input type="url" value={brand.terms_url} onChange={(e) => setBrand({ terms_url: e.target.value })} />
        </Field>
        <Field label="Unsubscribe URL">
          <Input type="url" value={brand.unsubscribe_url} onChange={(e) => setBrand({ unsubscribe_url: e.target.value })} />
        </Field>
      </div>

      <Divider />
      <SectionTitle>Save &amp; share</SectionTitle>
      {saving ? (
        <div className="flex gap-2 animate-fade-up">
          <Input placeholder="Brand kit name" value={saveName} onChange={(e) => setSaveName(e.target.value)} autoFocus />
          <Button
            variant="primary"
            onClick={() => {
              saveBrand(saveName);
              setSaving(false);
              setSaveName("");
              toast("Brand kit saved on this device.", "success");
            }}
          >
            Save
          </Button>
          <Button variant="ghost" onClick={() => setSaving(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => setSaving(true)}>
            <Save className="size-3.5" /> Save as kit
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => downloadText(JSON.stringify(brand, null, 2), `${(brand.name || "brand").toLowerCase().replace(/\s+/g, "-")}.brand.json`, "application/json")}
          >
            <Download className="size-3.5" /> Export JSON
          </Button>
          <input
            ref={importRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) importKit(f);
              e.target.value = "";
            }}
          />
          <Button size="sm" variant="outline" onClick={() => importRef.current?.click()}>
            <Upload className="size-3.5" /> Import JSON
          </Button>
        </div>
      )}
    </div>
  );
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const [text, setText] = useState(value);
  const valid = isHexColor(text);
  // Keep the text box in sync when a preset swaps the colour.
  if (valid && text.toLowerCase() !== value.toLowerCase() && document.activeElement?.getAttribute("data-color") !== label) {
    setText(value);
  }
  return (
    <Field label={label.charAt(0).toUpperCase() + label.slice(1)}>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`${label} colour`}
          value={valid ? text : value}
          onChange={(e) => {
            setText(e.target.value);
            onChange(e.target.value);
          }}
          className="size-9 shrink-0 rounded-lg"
        />
        <Input
          data-color={label}
          value={text}
          maxLength={7}
          spellCheck={false}
          className={cn("font-mono text-xs uppercase", !valid && "border-danger")}
          onChange={(e) => {
            const v = e.target.value.startsWith("#") ? e.target.value : `#${e.target.value}`;
            setText(v);
            if (isHexColor(v)) onChange(v);
          }}
        />
      </div>
    </Field>
  );
}
