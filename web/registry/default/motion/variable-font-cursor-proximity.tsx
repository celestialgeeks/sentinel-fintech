"use client";

/**
 * VariableFontCursorProximity — the primitive behind
 * `m-variable-font-cursor-proximity-3` from 21st.dev.
 *
 * The paste shipped the demo but not this registry file, so it is implemented
 * here against the same public API (`containerRef`, `radius`, `falloff`,
 * `from/toFontVariationSettings`). Once `npx @21st-dev/cli login` is done, the
 * upstream version can replace this file without touching a single call site.
 *
 * Two deliberate choices:
 *
 * **No animation library.** Weight is written straight to each glyph's
 * `font-variation-settings` from one rAF loop, the same way `kinetic-grid`
 * works. A per-character `useTransform` tree for ~60 nav glyphs would add a
 * dependency to do arithmetic.
 *
 * **The loop idles.** It runs only while the pointer is inside the container or
 * a glyph is still settling, then stops. `KineticGrid` already keeps one rAF
 * alive for the whole page; a second one that never sleeps would be a battery
 * cost for an effect nobody is looking at.
 */

import { useEffect, useRef } from "react";
import type { ReactNode, RefObject } from "react";

import { cn } from "@/lib/utils";

export type CursorProximityFalloff = "linear" | "exponential" | "gaussian";

const AXIS_PATTERN = /['"]?([a-z]{4})['"]?\s*(-?\d+(?:\.\d+)?)/i;

/** `"'wght' 300"` → `{ axis: "wght", value: 300 }`. */
function parseVariation(spec: string, fallbackAxis: string, fallbackValue: number) {
  const match = AXIS_PATTERN.exec(spec);
  return { axis: match?.[1] ?? fallbackAxis, value: match ? Number(match[2]) : fallbackValue };
}

/** 0 far away → 1 dead centre of the pointer. */
function proximity(distance: number, radius: number, falloff: CursorProximityFalloff) {
  if (radius <= 0 || distance >= radius) return 0;
  const p = 1 - distance / radius;
  switch (falloff) {
    case "linear":
      return p;
    case "gaussian": {
      const sigma = radius / 2;
      return Math.exp(-(distance * distance) / (2 * sigma * sigma));
    }
    case "exponential":
    default: {
      const k = 4;
      return (Math.exp(k * p) - 1) / (Math.exp(k) - 1);
    }
  }
}

const OFF_SCREEN = -10_000;

export function VariableFontCursorProximity({
  children,
  className,
  containerRef,
  radius = 60,
  falloff = "exponential",
  fromFontVariationSettings = "'wght' 300",
  toFontVariationSettings = "'wght' 800",
  speed = 0.18,
}: {
  children: ReactNode;
  className?: string;
  /** Element whose box the pointer is measured against — the shared nav, not this word. */
  containerRef?: RefObject<HTMLElement | null>;
  radius?: number;
  falloff?: CursorProximityFalloff;
  fromFontVariationSettings?: string;
  toFontVariationSettings?: string;
  /** Lerp factor toward the target weight, per frame. */
  speed?: number;
}) {
  const text = typeof children === "string" ? children : "";
  const chars = text.split("");
  const hostRef = useRef<HTMLSpanElement>(null);
  const glyphRefs = useRef<(HTMLSpanElement | null)[]>([]);

  const from = parseVariation(fromFontVariationSettings, "wght", 300);
  const to = parseVariation(toFontVariationSettings, from.axis, 800);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || chars.length === 0) return;

    const container = containerRef?.current ?? host.parentElement;
    if (!container) return;

    const glyphs = glyphRefs.current.filter((el): el is HTMLSpanElement => Boolean(el));
    const setWeight = (el: HTMLSpanElement, value: number) => {
      el.style.fontVariationSettings = `'${from.axis}' ${value.toFixed(2)}`;
    };

    // Reduced motion: one static weight, no listeners, no loop.
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      glyphs.forEach((el) => setWeight(el, from.value));
      return;
    }

    const centers = new Array<{ x: number; y: number }>(glyphs.length).fill({
      x: OFF_SCREEN,
      y: OFF_SCREEN,
    });
    const current = new Array<number>(glyphs.length).fill(from.value);
    const target = new Array<number>(glyphs.length).fill(from.value);
    const pointer = { x: OFF_SCREEN, y: OFF_SCREEN, inside: false };

    let needsMeasure = true;
    let frame = 0;

    const measure = () => {
      const box = container.getBoundingClientRect();
      glyphs.forEach((el, i) => {
        const rect = el.getBoundingClientRect();
        centers[i] = {
          x: rect.left - box.left + rect.width / 2,
          y: rect.top - box.top + rect.height / 2,
        };
      });
      needsMeasure = false;
    };

    const computeTargets = () => {
      for (let i = 0; i < glyphs.length; i += 1) {
        if (!pointer.inside) {
          target[i] = from.value;
          continue;
        }
        const dx = centers[i].x - pointer.x;
        const dy = centers[i].y - pointer.y;
        const t = proximity(Math.hypot(dx, dy), radius, falloff);
        target[i] = from.value + (to.value - from.value) * t;
      }
    };

    const tick = () => {
      if (needsMeasure) measure();
      computeTargets();

      let settling = false;
      for (let i = 0; i < glyphs.length; i += 1) {
        const delta = target[i] - current[i];
        if (Math.abs(delta) < 0.05) {
          if (current[i] !== target[i]) {
            current[i] = target[i];
            setWeight(glyphs[i], current[i]);
          }
          continue;
        }
        settling = true;
        current[i] += delta * speed;
        setWeight(glyphs[i], current[i]);
      }

      if (settling || pointer.inside) {
        frame = requestAnimationFrame(tick);
      } else {
        frame = 0;
      }
    };

    const start = () => {
      if (!frame) frame = requestAnimationFrame(tick);
    };

    const onPointerMove = (event: PointerEvent) => {
      const box = container.getBoundingClientRect();
      pointer.x = event.clientX - box.left;
      pointer.y = event.clientY - box.top;
      pointer.inside = true;
      start();
    };

    const onPointerLeave = () => {
      pointer.inside = false;
      start(); // one last pass to settle back to `from`
    };

    const onLayoutChange = () => {
      needsMeasure = true;
      start();
    };

    container.addEventListener("pointermove", onPointerMove);
    container.addEventListener("pointerleave", onPointerLeave);
    window.addEventListener("resize", onLayoutChange);
    window.addEventListener("scroll", onLayoutChange, { passive: true });
    needsMeasure = true;
    start();

    return () => {
      if (frame) cancelAnimationFrame(frame);
      container.removeEventListener("pointermove", onPointerMove);
      container.removeEventListener("pointerleave", onPointerLeave);
      window.removeEventListener("resize", onLayoutChange);
      window.removeEventListener("scroll", onLayoutChange);
    };
  }, [chars.length, containerRef, falloff, from.axis, from.value, radius, speed, to.value]);

  return (
    // The animated glyphs are decorative: the pointer is what they respond to, so
    // a screen reader gets the name from the surrounding link's `aria-label` and
    // this subtree is hidden rather than read out letter by letter.
    <span ref={hostRef} className={cn("inline-block whitespace-pre", className)} aria-hidden="true">
      {chars.map((char, index) => (
        <span
          key={`${char}-${index}`}
          ref={(el) => {
            glyphRefs.current[index] = el;
          }}
          style={{ fontVariationSettings: `'${from.axis}' ${from.value}` }}
        >
          {char}
        </span>
      ))}
    </span>
  );
}

export default VariableFontCursorProximity;
