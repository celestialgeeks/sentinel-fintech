"use client";

import { useState } from "react";
import { Search, Plus, Menu } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Dashboard header. Zenix structure (greeting block · glass search · glowing
 * primary action · slate avatar) rendered in Neural Noir: Playfair for the
 * display line, our gold for the primary CTA instead of pure white. The window
 * toggle is the real `/portal/overview?window=` range so a switch is honest.
 */
const WINDOWS = ["today", "24h", "7d", "30d", "all"] as const;
type Window = (typeof WINDOWS)[number];

export function PortalHeader({ onOpenNav }: { onOpenNav?: () => void }) {
  const [window, setWindow] = useState<Window>("7d");

  const greeting = getGreeting();
  const dateLabel = new Date().toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  });

  return (
    <header className="flex flex-col gap-5 border-b border-line pb-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          {onOpenNav ? (
            <button
              type="button"
              onClick={onOpenNav}
              aria-label="Open navigation"
              className="grid size-10 place-items-center rounded-xl border border-line text-ink-50 lg:hidden"
            >
              <Menu className="size-5" aria-hidden />
            </button>
          ) : null}
          <div>
            <h1 className="font-serif text-[1.9rem] italic leading-tight tracking-[-0.01em] text-ink-50">
              {greeting}, Ramesh
            </h1>
            <p className="mt-0.5 text-sm text-ink-500">{dateLabel}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search — 224px glass field. */}
          <label className="glass-card hidden items-center gap-2 rounded-xl px-3 py-2 md:flex md:w-56">
            <Search className="size-4 shrink-0 text-ink-500" aria-hidden />
            <input
              type="search"
              placeholder="Order, UTR, buyer…"
              className="w-full bg-transparent text-sm text-ink-50 placeholder:text-ink-500 focus:outline-none"
            />
          </label>

          {/* Window segmented control. */}
          <div className="glass-soft flex items-center gap-1 rounded-xl p-1" role="tablist" aria-label="Time window">
            {WINDOWS.map((w) => (
              <button
                key={w}
                type="button"
                role="tab"
                aria-selected={window === w}
                onClick={() => setWindow(w)}
                className={cn(
                  "rounded-lg px-2.5 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors duration-300 ease-[var(--ease-glass)]",
                  window === w
                    ? "bg-white/[0.08] text-ink-50"
                    : "text-ink-500 hover:text-ink-300",
                )}
              >
                {w}
              </button>
            ))}
          </div>

          {/* Primary action with the heavy glow. */}
          <a
            href="/dashboard/connect"
            className="inline-flex items-center gap-2 rounded-xl bg-gold px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] shadow-[0_10px_28px_-8px_rgba(167,139,113,0.55)] transition-transform duration-300 ease-[var(--ease-glass)] hover:scale-[1.03] hover:bg-gold-hover"
          >
            <Plus className="size-4" aria-hidden />
            Screen an order
          </a>

          {/* Avatar — slate gradient, initials. */}
          <button
            type="button"
            aria-label="Account"
            className="grid size-10 place-items-center rounded-full bg-gradient-to-br from-[#3a3a3a] to-[#141414] font-mono text-sm text-ink-50 ring-1 ring-line"
          >
            RD
          </button>
        </div>
      </div>
    </header>
  );
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default PortalHeader;
