"use client";

import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from "lucide-react";

import { useStudio } from "@/lib/store";
import { cn } from "@/lib/utils";

const icons = {
  success: <CircleCheck className="size-4 text-success" />,
  error: <CircleAlert className="size-4 text-danger" />,
  warning: <TriangleAlert className="size-4 text-warning" />,
  info: <Info className="size-4 text-accent" />,
};

export function Toaster() {
  const toasts = useStudio((s) => s.toasts);
  const dismiss = useStudio((s) => s.dismissToast);
  if (!toasts.length) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 lg:bottom-6" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-2xl border border-border bg-surface px-4 py-3 text-sm shadow-pop animate-fade-up",
          )}
        >
          <span className="mt-0.5 shrink-0">{icons[t.kind]}</span>
          <span className="flex-1 text-text">{t.message}</span>
          <button type="button" onClick={() => dismiss(t.id)} className="text-faint hover:text-text" aria-label="Dismiss">
            <X className="size-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
