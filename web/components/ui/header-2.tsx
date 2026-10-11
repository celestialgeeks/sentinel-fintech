"use client";

import React from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MenuToggleIcon } from "@/components/ui/menu-toggle-icon";
import { useScroll } from "@/components/ui/use-scroll";
import { SentinelLogo } from "@/components/ui/sentinel-logo";
import { LANDING_NAV, ProximityNav } from "@/components/ui/m-variable-font-cursor-proximity-3";

/**
 * header-2 — 21st.dev component, structure and classes intact. Five deliberate
 * local changes, all content or accessibility rather than design:
 *
 * 1. `WordmarkIcon` → `SentinelLogo` (the upstream mark is a placeholder brand).
 * 2. Links and CTAs carry Sentinel's nav (§6.1) instead of Features/Pricing/About.
 * 3. The mobile toggle is labelled and exposes `aria-expanded`; the icon inside
 *    it is `aria-hidden`, so without this the button announces nothing.
 * 4. Tapping a mobile link closes the menu — otherwise the full-screen overlay
 *    stays up over the section the visitor just asked to scroll to.
 * 5. Desktop links render through `ProximityNav` (variable-font cursor
 *    proximity). Nav items live in one place, `LANDING_NAV`, so the desktop row
 *    and the mobile overlay can never drift apart.
 */

const links = LANDING_NAV;

export function Header() {
  const [open, setOpen] = React.useState(false);
  const scrolled = useScroll(10);

  React.useEffect(() => {
    if (open) {
      // Disable scroll
      document.body.style.overflow = "hidden";
    } else {
      // Re-enable scroll
      document.body.style.overflow = "";
    }

    // Cleanup when component unmounts (important for Next.js)
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 mx-auto w-full max-w-5xl border-b border-transparent md:rounded-md md:border md:transition-all md:ease-out",
        {
          "bg-background/95 supports-[backdrop-filter]:bg-background/50 border-border backdrop-blur-lg md:top-4 md:max-w-4xl md:shadow":
            scrolled && !open,
          "bg-background/90": open,
        },
      )}
    >
      <nav
        className={cn(
          "flex h-14 w-full items-center justify-between px-4 md:h-12 md:transition-all md:ease-out",
          {
            "md:px-2": scrolled,
          },
        )}
        aria-label="Primary"
      >
        <SentinelLogo className="h-4" />

        <div className="hidden items-center gap-2 md:flex">
          <ProximityNav
            items={links}
            // Tighter than the upstream demo's `gap-10 px-6`, and a narrower
            // weight range: at 13px, 300 reads as thin and 800 as bold-heavy,
            // so the bloom lives between 400 and 700 where it stays legible.
            className="gap-0 px-0"
            itemClassName="px-3 py-2 text-[13px]"
            radius={90}
            fromFontVariationSettings="'wght' 400"
            toFontVariationSettings="'wght' 700"
          />
          <Button variant="outline" asChild>
            <a href="#login">Log in</a>
          </Button>
          <Button asChild>
            <a href="#connect">Connect your bot</a>
          </Button>
        </div>

        <Button
          size="icon"
          variant="outline"
          onClick={() => setOpen(!open)}
          className="md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          <MenuToggleIcon open={open} className="size-5" duration={300} />
        </Button>
      </nav>

      <div
        className={cn(
          "bg-background/90 fixed top-14 right-0 bottom-0 left-0 z-50 flex flex-col overflow-hidden border-y md:hidden",
          open ? "block" : "hidden",
        )}
      >
        <div
          data-slot={open ? "open" : "closed"}
          className={cn(
            "data-[slot=open]:animate-in data-[slot=open]:zoom-in-95 data-[slot=closed]:animate-out data-[slot=closed]:zoom-out-95 ease-out",
            "flex h-full w-full flex-col justify-between gap-y-2 p-4",
          )}
        >
          <div className="grid gap-y-2">
            {links.map((link) => (
              <a
                key={link.label}
                onClick={() => setOpen(false)}
                className={buttonVariants({
                  variant: "ghost",
                  className: "justify-start",
                })}
                href={link.href}
              >
                {link.label}
              </a>
            ))}
          </div>
          <div className="flex flex-col gap-2">
            <Button variant="outline" className="w-full" asChild>
              <a href="#login" onClick={() => setOpen(false)}>
                Log in
              </a>
            </Button>
            <Button className="w-full" asChild>
              <a href="#connect" onClick={() => setOpen(false)}>
                Connect your bot
              </a>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
