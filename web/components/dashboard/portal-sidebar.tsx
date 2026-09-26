"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { formatUSD } from "@/lib/dashboard-data";
import { NAV_GROUPS } from "@/components/dashboard/nav-items";

// Illustrative vendor spend for the current window (PORTAL_API summary.vendor_spend_usd).
const WINDOW_SPEND_USD = 7.3747;

export function PortalSidebar() {
  const pathname = usePathname();

  return (
    <aside className="glass-soft sticky top-0 z-20 hidden h-screen w-[280px] shrink-0 flex-col border-r border-line px-5 py-6 lg:flex">
      {/* Wordmark — 44px white box with the black Sentinel initial, per Zenix logo. */}
      <Link href="/dashboard" className="mb-8 flex items-center gap-3" aria-label="Sentinel dashboard">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-white font-serif text-2xl font-bold italic text-black shadow-[0_10px_28px_-8px_rgba(255,255,255,0.35)]">
          S
        </span>
        <span className="leading-tight">
          <span className="block font-serif text-lg italic tracking-tight text-ink-50">Sentinel</span>
          <span className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-500">Merchant desk</span>
        </span>
      </Link>

      <nav className="flex flex-1 flex-col gap-6 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="mb-2 px-3 font-mono text-[10px] uppercase tracking-[0.2em] text-ink-500">
              {group.label}
            </p>
            <ul className="flex flex-col gap-1">
              {group.items.map((item) => {
                const active =
                  item.href === "/dashboard"
                    ? pathname === "/dashboard"
                    : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-300 ease-[var(--ease-glass)]",
                        active
                          ? "bg-white/[0.06] text-ink-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.10)]"
                          : "text-ink-300 hover:bg-white/[0.03] hover:text-ink-50",
                      )}
                    >
                      <Icon
                        className={cn(
                          "size-[17px] shrink-0 transition-colors duration-300",
                          active ? "text-gold" : "text-ink-500 group-hover:text-gold-light",
                        )}
                        strokeWidth={1.8}
                        aria-hidden
                      />
                      <span className="flex-1">{item.name}</span>
                      {item.badge ? (
                        <span className="grid min-w-5 place-items-center rounded-full bg-hold/15 px-1.5 py-0.5 font-mono text-[10px] font-medium text-hold">
                          {item.badge}
                        </span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Floating guard card — the desk's live status, bobbing gently at the base. */}
      <div className="float mt-6">
        <GuardStatusCard />
      </div>
    </aside>
  );
}

/**
 * Guard status: the bot is in Enforce, the connection is healthy, and this is
 * what it has cost this window. Ties the "wallet card" Zenix slot to something a
 * Sentinel merchant actually watches (integration.status + summary.spend).
 */
function GuardStatusCard() {
  return (
    <div className="liquid-glass glass-strong rounded-2xl p-4">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs font-medium text-ink-300">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-allow opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-allow" />
          </span>
          Guard live
        </span>
        <span className="rounded-full border border-line bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-gold">
          Enforce
        </span>
      </div>
      <p className="mt-3 font-mono text-2xl font-medium tabular text-ink-50">
        24 <span className="text-sm font-normal text-ink-500">orders</span>
      </p>
      <div className="mt-3 flex items-center justify-between border-t border-line pt-3 text-[11px]">
        <span className="text-ink-500">Spend · 7d</span>
        <span className="font-mono tabular text-ink-300">{formatUSD(WINDOW_SPEND_USD)}</span>
      </div>
    </div>
  );
}

export default PortalSidebar;
