"use client";

import { LoaderCircle } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ Button */

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg" | "icon";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantClass: Record<Variant, string> = {
  primary: "gradient-bg text-white shadow-soft hover:brightness-110 active:brightness-95 disabled:opacity-60",
  secondary: "bg-surface-3 text-text hover:bg-border active:bg-border-strong disabled:opacity-60",
  outline: "border border-border bg-surface text-text hover:bg-surface-2 hover:border-border-strong disabled:opacity-60",
  ghost: "text-muted hover:text-text hover:bg-surface-3 disabled:opacity-50",
  danger: "bg-danger/10 text-danger hover:bg-danger/20 disabled:opacity-60",
};

const sizeClass: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5 rounded-lg",
  md: "h-9.5 px-4 text-sm gap-2 rounded-xl",
  lg: "h-11 px-5 text-sm gap-2 rounded-xl",
  icon: "h-9 w-9 rounded-lg",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "secondary", size = "md", loading, children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={cn(
        "inline-flex items-center justify-center font-medium whitespace-nowrap transition-[background,color,filter,transform] duration-150 select-none disabled:cursor-not-allowed",
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden /> : null}
      {children}
    </button>
  );
});

/* ------------------------------------------------------------------ Inputs */

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return <input ref={ref} className={cn("field", className)} {...props} />;
});

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...props }, ref) {
    return <textarea ref={ref} className={cn("field resize-y min-h-20 leading-relaxed", className)} {...props} />;
  },
);

export function Select({ className, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select className={cn("field appearance-none pr-8 cursor-pointer", className)} {...props}>
        {children}
      </select>
      <svg
        aria-hidden
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 size-4 text-faint"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M6 8l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

export function Label({ className, children, hint, ...props }: React.LabelHTMLAttributes<HTMLLabelElement> & { hint?: string }) {
  return (
    <label className={cn("flex items-baseline justify-between gap-2 text-xs font-medium text-muted mb-1.5", className)} {...props}>
      <span>{children}</span>
      {hint ? <span className="text-[11px] font-normal text-faint">{hint}</span> : null}
    </label>
  );
}

export function Field({ label, hint, children, className }: { label: string; hint?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col", className)}>
      <Label hint={hint}>{label}</Label>
      {children}
    </div>
  );
}

export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-surface px-3 py-2.5 text-left transition hover:border-border-strong disabled:opacity-60"
    >
      <span className="min-w-0">
        <span className="block text-sm font-medium text-text">{label}</span>
        {description ? <span className="block text-xs text-muted">{description}</span> : null}
      </span>
      <span
        className={cn(
          "relative inline-flex h-5.5 w-9.5 shrink-0 items-center rounded-full transition-colors",
          checked ? "gradient-bg" : "bg-border-strong",
        )}
      >
        <span
          className={cn(
            "inline-block size-4.5 rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-4.5" : "translate-x-0.5",
          )}
        />
      </span>
    </button>
  );
}

export function Range({
  value,
  min,
  max,
  onChange,
  label,
}: {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  label: string;
}) {
  return (
    <div>
      <Label hint={String(value)}>{label}</Label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
        aria-label={label}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ Tabs / Segmented */

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  size = "md",
  className,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: React.ReactNode; title?: string }[];
  size?: "sm" | "md";
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn("inline-flex items-center rounded-xl bg-surface-3 p-1 gap-0.5", size === "sm" ? "h-8" : "h-9.5", className)}
    >
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          type="button"
          title={o.title}
          aria-selected={o.value === value}
          onClick={() => onChange(o.value)}
          className={cn(
            "inline-flex h-full items-center justify-center gap-1.5 rounded-lg px-3 font-medium transition-colors whitespace-nowrap",
            size === "sm" ? "text-xs px-2.5" : "text-sm",
            o.value === value ? "bg-surface text-text shadow-soft" : "text-muted hover:text-text",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ Misc */

export function Badge({ children, tone = "neutral", className }: { children: React.ReactNode; tone?: "neutral" | "accent" | "success" | "warning" | "danger"; className?: string }) {
  const tones = {
    neutral: "bg-surface-3 text-muted",
    accent: "bg-accent/12 text-accent",
    success: "bg-success/12 text-success",
    warning: "bg-warning/15 text-warning",
    danger: "bg-danger/12 text-danger",
  };
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold leading-4", tones[tone], className)}>
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <LoaderCircle className={cn("size-4 animate-spin text-muted", className)} aria-hidden />;
}

export function SectionTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 mb-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-faint">{children}</h3>
      {action}
    </div>
  );
}

export function Divider({ className }: { className?: string }) {
  return <hr className={cn("border-t border-border my-5", className)} />;
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-5 items-center rounded border border-border bg-surface px-1.5 font-mono text-[10px] text-muted">
      {children}
    </kbd>
  );
}

/** Simple click-outside popover. */
export function Popover({
  open,
  onClose,
  children,
  className,
  align = "right",
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
  align?: "left" | "right";
}) {
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div
      ref={ref}
      className={cn(
        "absolute top-[calc(100%+6px)] z-40 min-w-56 rounded-2xl border border-border bg-surface p-1.5 shadow-pop animate-fade-up",
        align === "right" ? "right-0" : "left-0",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function MenuItem({
  icon,
  children,
  onClick,
  disabled,
  danger,
  hint,
}: {
  icon?: React.ReactNode;
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  danger?: boolean;
  hint?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-sm transition-colors disabled:opacity-50",
        danger ? "text-danger hover:bg-danger/10" : "text-text hover:bg-surface-3",
      )}
    >
      {icon ? <span className="text-muted [&>svg]:size-4">{icon}</span> : null}
      <span className="flex-1">{children}</span>
      {hint ? <span className="text-[11px] text-faint">{hint}</span> : null}
    </button>
  );
}

export function EmptyHint({ icon, title, body, action }: { icon: React.ReactNode; title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center text-center px-6 py-10 animate-fade-up">
      <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-surface-3 text-accent [&>svg]:size-7">{icon}</div>
      <h3 className="text-base font-semibold text-text">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-muted">{body}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
