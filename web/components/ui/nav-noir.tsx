"use client";

import React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { MenuToggleIcon } from "@/components/ui/menu-toggle-icon";

/**
 * NavNoir — the fixed top navbar from the Neural Noir spec: full-bleed, a
 * Playfair Display Bold-Italic wordmark, centre-aligned uppercase Inter links
 * with heavy tracking, and a white pill CTA (black text, rounded-full) on the
 * right. Structure follows the spec; the links and the CTA are Sentinel's real
 * nav (docs/WEBSITE_CONTENT_BRIEF.md §6.1).
 */
const LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Evidence", href: "#evidence" },
  { label: "Integrations", href: "#integrations" },
  { label: "Pricing", href: "#pricing" },
];

export function NavNoir() {
  const [open, setOpen] = React.useState(false);
  const scrolled = React.useSyncExternalStore(
    (cb) => {
      window.addEventListener("scroll", cb, { passive: true });
      return () => window.removeEventListener("scroll", cb);
    },
    () => window.scrollY > 12,
    () => false,
  );

  React.useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-[background-color,box-shadow,border-color] duration-300 ease-[var(--ease-noir)]",
        scrolled || open
          ? "border-b border-line bg-canvas/70 backdrop-blur-xl"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <nav
        className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-6 md:h-20 md:px-12"
        aria-label="Primary"
      >
        {/* Wordmark — Playfair Bold Italic, gold. */}
        <Link
          href="/"
          className="font-serif text-2xl font-bold italic tracking-tight text-ink-50"
          onClick={() => setOpen(false)}
        >
          Sentinel<span className="text-gold">.</span>
        </Link>

        {/* Desktop links — uppercase, wide tracked. */}
        <div className="hidden items-center gap-9 lg:flex">
          {LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-[11px] font-medium uppercase tracking-[0.22em] text-ink-300 transition-colors ease-[var(--ease-noir)] hover:text-gold-hover"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Right actions. */}
        <div className="hidden items-center gap-5 lg:flex">
          <a
            href="#login"
            className="text-[11px] font-medium uppercase tracking-[0.22em] text-ink-300 transition-colors hover:text-ink-50"
          >
            Log in
          </a>
          <a
            href="#connect"
            className="rounded-full bg-white px-5 py-2.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-black transition-transform duration-300 ease-[var(--ease-noir)] hover:scale-[1.03] hover:bg-gold-hover"
          >
            Connect your bot
          </a>
        </div>

        {/* Mobile toggle. */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          className="grid size-10 place-items-center rounded-full border border-line text-ink-50 lg:hidden"
        >
          <MenuToggleIcon open={open} className="size-5" duration={300} />
        </button>
      </nav>

      {/* Mobile overlay. */}
      <div
        className={cn(
          "fixed inset-x-0 top-16 bottom-0 z-40 flex flex-col gap-2 bg-canvas/95 px-6 pb-8 pt-6 backdrop-blur-xl transition-opacity duration-300 lg:hidden",
          open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
        )}
      >
        {LINKS.map((link) => (
          <a
            key={link.href}
            href={link.href}
            onClick={() => setOpen(false)}
            className="border-b border-line py-3 text-sm font-medium uppercase tracking-[0.2em] text-ink-300"
          >
            {link.label}
          </a>
        ))}
        <a
          href="#connect"
          onClick={() => setOpen(false)}
          className="mt-4 rounded-full bg-white px-5 py-3 text-center text-xs font-semibold uppercase tracking-[0.18em] text-black"
        >
          Connect your bot
        </a>
      </div>
    </header>
  );
}

export default NavNoir;
