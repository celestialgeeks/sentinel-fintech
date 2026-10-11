"use client";

import * as React from "react";

/**
 * True once the page has scrolled past `threshold` pixels.
 *
 * Initialised from `window.scrollY` on mount, not `false`: a visitor who lands on
 * `/#pricing` from a search result is already scrolled, and a header that only
 * learns the truth on the first scroll event renders a transparent bar over
 * content.
 */
export function useScroll(threshold: number) {
  const [scrolled, setScrolled] = React.useState(false);

  const onScroll = React.useCallback(() => {
    setScrolled(window.scrollY > threshold);
  }, [threshold]);

  React.useEffect(() => {
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [onScroll]);

  return scrolled;
}

export default useScroll;
