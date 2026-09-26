"use client";

import { useRef } from "react";

import { VariableFontCursorProximity } from "@/registry/default/motion/variable-font-cursor-proximity";
import { cn } from "@/lib/utils";

export type ProximityNavItem = { label: string; href: string };

/** Sentinel's primary nav — docs/WEBSITE_CONTENT_BRIEF.md §6.1. */
export const LANDING_NAV: ProximityNavItem[] = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Integrations", href: "#integrations" },
  { label: "Evidence", href: "#evidence" },
  { label: "Pricing", href: "#pricing" },
];

/**
 * m-variable-font-cursor-proximity-3 — 21st.dev component. Glyph weight blooms
 * toward the pointer, measured against the shared container so a word two links
 * away still lights up in sequence.
 *
 * The upstream demo hard-coded `["Home","Work","About","Contact"]` in a
 * centred 200px-tall block; here the items come from props so the header can
 * render Sentinel's real nav with one container ref, which is what makes the
 * proximity read as a single field rather than four independent words.
 */
export function ProximityNav({
  items = LANDING_NAV,
  className,
  itemClassName,
  radius = 60,
  fromFontVariationSettings = "'wght' 300",
  toFontVariationSettings = "'wght' 800",
}: {
  items?: ProximityNavItem[];
  className?: string;
  itemClassName?: string;
  radius?: number;
  fromFontVariationSettings?: string;
  toFontVariationSettings?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <div ref={containerRef} className={cn("flex flex-wrap items-center gap-10 px-6", className)}>
      {items.map((item) => (
        <a
          key={item.href}
          href={item.href}
          aria-label={item.label}
          className={cn(
            "cursor-pointer rounded-sm text-xl text-muted-foreground transition-colors",
            "hover:text-foreground focus-visible:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            itemClassName,
          )}
        >
          <VariableFontCursorProximity
            containerRef={containerRef}
            falloff="exponential"
            fromFontVariationSettings={fromFontVariationSettings}
            radius={radius}
            toFontVariationSettings={toFontVariationSettings}
          >
            {item.label}
          </VariableFontCursorProximity>
        </a>
      ))}
    </div>
  );
}

export default ProximityNav;
