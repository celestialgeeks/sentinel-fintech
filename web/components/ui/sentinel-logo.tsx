import Link from "next/link";
import { ScanLine } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Sentinel wordmark. Replaces the generic `WordmarkIcon` that shipped with the
 * 21st.dev header example — the mark is brand content, and content comes from
 * docs/WEBSITE_CONTENT_BRIEF.md §6.1. Typographic, not a shield: the brief rules
 * out glowing-shield iconography on this site.
 */
export function SentinelLogo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      aria-label="Sentinel — home"
      className={cn("flex shrink-0 items-center gap-2.5", className)}
    >
      <span className="grid size-6 place-items-center rounded-[6px] bg-primary/15 text-primary">
        <ScanLine className="size-3.5" strokeWidth={2.2} aria-hidden="true" />
      </span>
      <span className="font-mono text-sm font-medium tracking-[0.22em] text-foreground">
        SENTINEL
      </span>
    </Link>
  );
}

export default SentinelLogo;
