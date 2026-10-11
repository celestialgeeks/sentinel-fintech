"use client";

import { cn } from "@/lib/utils";

/**
 * Hamburger that morphs into an X. Two bars rather than three: at the sizes a
 * header icon uses, three lines read as noise once they animate.
 *
 * `duration` is in ms and drives the CSS transition, so the caller can match it
 * to the menu's own open animation. Motion is dropped entirely when the visitor
 * has asked for reduced motion.
 */
export function MenuToggleIcon({
  open,
  className,
  duration = 200,
}: {
  open: boolean;
  className?: string;
  duration?: number;
}) {
  const bar =
    "absolute left-0 block h-[1.5px] w-full rounded-full bg-current transition-transform motion-reduce:transition-none";
  const timing = { transitionDuration: `${duration}ms` };

  return (
    <span className={cn("relative block", className)} aria-hidden="true">
      <span
        style={timing}
        className={cn(
          bar,
          open ? "top-1/2 -translate-y-1/2 rotate-45" : "top-[30%] -translate-y-1/2",
        )}
      />
      <span
        style={timing}
        className={cn(
          bar,
          open ? "top-1/2 -translate-y-1/2 -rotate-45" : "top-[70%] -translate-y-1/2",
        )}
      />
    </span>
  );
}

export default MenuToggleIcon;
