"use client";

/**
 * TimelineContent — the dependency `testimonial.tsx` imports but the paste did
 * not include. Implemented against the props the caller actually uses:
 * `as`, `animationNum` (the stagger index handed to `variants.visible(i)`),
 * `customVariants`, and `timelineRef` (the shared element the reveal is timed
 * against, so a section animates as one sequence rather than seven independent
 * intersections).
 */

import { motion } from "motion/react";
import type { ElementType, ReactNode, RefObject } from "react";

// Pre-bound motion components instead of `motion[tag]`: the index signature is
// gone in current `motion`, and a lookup table keeps this type-safe.
const MOTION_TAGS: Record<string, ElementType> = {
  div: motion.div,
  span: motion.span,
  p: motion.p,
  h1: motion.h1,
  h2: motion.h2,
  h3: motion.h3,
  article: motion.article,
  section: motion.section,
  li: motion.li,
  ul: motion.ul,
};

export function TimelineContent({
  as = "div",
  className,
  children,
  animationNum = 0,
  customVariants,
  timelineRef,
  amount = 0.2,
  once = true,
}: {
  as?: keyof typeof MOTION_TAGS;
  className?: string;
  children?: ReactNode;
  /** Position in the sequence; passed to `variants.visible(i)` for the delay. */
  animationNum?: number;
  customVariants?: Record<string, unknown>;
  /** Section element the reveal is measured against. */
  timelineRef?: RefObject<HTMLElement | null>;
  amount?: number;
  once?: boolean;
}) {
  const Tag = MOTION_TAGS[as] ?? motion.div;

  return (
    <Tag
      className={className}
      custom={animationNum}
      variants={customVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ root: timelineRef?.current ?? undefined, amount, once }}
    >
      {children}
    </Tag>
  );
}

export default TimelineContent;
