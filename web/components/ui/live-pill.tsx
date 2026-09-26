import { cn } from "@/lib/utils";

/**
 * LivePill — the floating status indicator from the Neural Noir spec: a
 * glass pill with a breathing green dot, "LIVE", then a status string. Hue is
 * never the only signal here — the word "LIVE" carries the state — which keeps
 * it consistent with the rest of the verdict colour rules on this site.
 */
export function LivePill({
  status = "Guarding · release-gate online",
  className,
}: {
  status?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "glass inline-flex items-center gap-2.5 rounded-full py-2 pl-3 pr-4",
        className,
      )}
    >
      <span className="relative flex size-2">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-allow/70" />
        <span className="relative inline-flex size-2 rounded-full bg-allow" />
      </span>
      <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-allow">
        Live
      </span>
      <span className="text-xs font-normal text-ink-50">{status}</span>
    </div>
  );
}

export default LivePill;
