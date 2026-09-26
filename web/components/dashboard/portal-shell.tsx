"use client";

import { useState } from "react";
import Link from "next/link";
import { X, Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { PortalSidebar } from "@/components/dashboard/portal-sidebar";
import { NAV_GROUPS } from "@/components/dashboard/nav-items";

/**
 * Portal shell — the fixed glass sidebar + scrolling main column the dashboard
 * lives in, plus the ambient background (two warm radial lights, the Neural Noir
 * dot grid and film grain) that gives the Zenix depth without a single heavy
 * shadow. Under `lg` the sidebar collapses into a drawer toggled from the header.
 */
export function PortalShell({ children }: { children: React.ReactNode }) {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="relative min-h-screen">
      <AmbientBackdrop />

      {/* Content sits above the fixed backdrop. */}
      <div className="relative z-10 flex">
        <PortalSidebar />

        {/* Mobile drawer. */}
        <div
          className={cn(
            "fixed inset-0 z-40 lg:hidden",
            navOpen ? "pointer-events-auto" : "pointer-events-none",
          )}
        >
          <div
            className={cn(
              "absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300",
              navOpen ? "opacity-100" : "opacity-0",
            )}
            onClick={() => setNavOpen(false)}
            aria-hidden
          />
          <div
            className={cn(
              "absolute left-0 top-0 h-full w-[280px] transition-transform duration-300 ease-[var(--ease-glass)]",
              navOpen ? "translate-x-0" : "-translate-x-full",
            )}
          >
            <div className="glass-soft relative flex h-full flex-col border-r border-line px-5 py-6">
              <button
                type="button"
                onClick={() => setNavOpen(false)}
                aria-label="Close navigation"
                className="absolute right-3 top-3 grid size-9 place-items-center rounded-lg border border-line text-ink-50"
              >
                <X className="size-4" aria-hidden />
              </button>
              <Link href="/dashboard" onClick={() => setNavOpen(false)} className="mb-6 flex items-center gap-3">
                <span className="grid size-11 place-items-center rounded-xl bg-white font-serif text-2xl font-bold italic text-black">
                  S
                </span>
                <span className="font-serif text-lg italic text-ink-50">Sentinel</span>
              </Link>
              <MobileNav onNavigate={() => setNavOpen(false)} />
            </div>
          </div>
        </div>

        <main className="min-w-0 flex-1 px-5 py-6 sm:px-8 sm:py-8 lg:px-10">
          <ShellInner onOpenNav={() => setNavOpen(true)}>{children}</ShellInner>
        </main>
      </div>
    </div>
  );
}

// Provide the header's menu button a way to open the drawer via context-free
// prop drilling kept local: the header is rendered by the page, so we expose a
// slot. Children that need the trigger receive it through ShellInner clone.
function ShellInner({ onOpenNav, children }: { onOpenNav: () => void; children: React.ReactNode }) {
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-6">
      <MobileNavTrigger onOpenNav={onOpenNav} />
      {children}
    </div>
  );
}

// A compact, accessible top-of-page trigger shown only on small screens.
function MobileNavTrigger({ onOpenNav }: { onOpenNav: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpenNav}
      className="glass-card inline-flex items-center gap-2 self-start rounded-xl px-4 py-2 text-sm font-medium text-ink-50 lg:hidden"
    >
      <Menu className="size-4" aria-hidden />
      Menu
    </button>
  );
}

function MobileNav({ onNavigate }: { onNavigate: () => void }) {
  return (
    <nav className="flex flex-1 flex-col gap-4 overflow-y-auto">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-1 px-3 font-mono text-[10px] uppercase tracking-[0.2em] text-ink-500">{group.label}</p>
          <ul className="flex flex-col gap-1">
            {group.items.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-ink-300 hover:bg-white/[0.03] hover:text-ink-50"
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function AmbientBackdrop() {
  return (
    <>
      <div className="bg-dots fixed inset-0 -z-0 bg-canvas [mask-image:radial-gradient(ellipse_90%_80%_at_50%_20%,#000_50%,transparent_100%)]" aria-hidden />
      <div className="ambient-glow" aria-hidden />
      <div className="grain-overlay" aria-hidden />
    </>
  );
}

export default PortalShell;
