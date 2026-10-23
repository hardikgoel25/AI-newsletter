"use client";

import { Braces, ChevronDown, Copy, Download, ExternalLink, FileCode, FileText, Mail, Printer } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";
import { useStudio } from "@/lib/store";
import type { ExportFormat } from "@/lib/types";
import { copyToClipboard, downloadBlob, downloadText, openHtmlInNewTab, slugify } from "@/lib/utils";

import { Button, MenuItem, Popover } from "./ui";

export function ExportMenu() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const newsletter = useStudio((s) => s.newsletter);
  const html = useStudio((s) => s.html);
  const brand = useStudio((s) => s.brand);
  const render = useStudio((s) => s.render);
  const toast = useStudio((s) => s.toast);

  const disabled = !newsletter || !html;
  const base = newsletter ? slugify(`${newsletter.company_name}-${newsletter.newsletter_type}-${newsletter.date}`) : "newsletter";

  async function serverExport(format: ExportFormat) {
    if (!newsletter) return;
    setBusy(format);
    try {
      const { blob, filename } = await api.export(newsletter, brand, render, format);
      downloadBlob(blob, filename);
      toast(`Downloaded ${filename}`, "success");
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(null);
      setOpen(false);
    }
  }

  function printPdf() {
    const w = window.open("", "_blank");
    if (!w) {
      toast("Pop-up blocked. Allow pop-ups to print.", "warning");
      return;
    }
    w.document.open();
    w.document.write(html);
    w.document.close();
    w.addEventListener("load", () => setTimeout(() => w.print(), 300));
    setOpen(false);
  }

  return (
    <div className="relative">
      <Button variant="primary" size="md" disabled={disabled} onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open}>
        <Download className="size-4" />
        <span className="hidden sm:inline">Export</span>
        <ChevronDown className="size-3.5 opacity-80" />
      </Button>
      <Popover open={open} onClose={() => setOpen(false)} className="w-64">
        <MenuItem
          icon={<FileCode />}
          hint="⌘S"
          onClick={() => {
            downloadText(html, `${base}.html`);
            setOpen(false);
          }}
        >
          Standalone HTML
        </MenuItem>
        <MenuItem icon={<Mail />} onClick={() => serverExport("email")} disabled={busy !== null}>
          Email-safe HTML {busy === "email" ? "…" : ""}
        </MenuItem>
        <MenuItem icon={<FileText />} onClick={() => serverExport("markdown")} disabled={busy !== null}>
          Markdown
        </MenuItem>
        <MenuItem icon={<FileText />} onClick={() => serverExport("text")} disabled={busy !== null}>
          Plain text
        </MenuItem>
        <MenuItem icon={<Braces />} onClick={() => serverExport("json")} disabled={busy !== null}>
          JSON data
        </MenuItem>
        <div className="my-1 border-t border-border" />
        <MenuItem
          icon={<Copy />}
          onClick={async () => {
            const ok = await copyToClipboard(html);
            toast(ok ? "HTML copied to clipboard." : "Clipboard unavailable.", ok ? "success" : "error");
            setOpen(false);
          }}
        >
          Copy HTML
        </MenuItem>
        <MenuItem
          icon={<ExternalLink />}
          onClick={() => {
            openHtmlInNewTab(html);
            setOpen(false);
          }}
        >
          Open in new tab
        </MenuItem>
        <MenuItem icon={<Printer />} onClick={printPdf}>
          Print / Save as PDF
        </MenuItem>
      </Popover>
    </div>
  );
}
