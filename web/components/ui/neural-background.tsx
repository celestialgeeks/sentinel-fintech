import { cn } from "@/lib/utils";

/**
 * NeuralBackground — the fixed page backdrop for the Neural Noir system: the
 * #0a0a0a canvas, a radial dot grid (32px, white 8%), a warm gold central glow,
 * and a top vignette so the navbar reads against it. Purely decorative, so it is
 * aria-hidden and pointer-events-none; content sits in a higher stacking layer.
 */
export function NeuralBackground({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("pointer-events-none fixed inset-0 z-0 overflow-hidden", className)}
    >
      {/* Base canvas */}
      <div className="absolute inset-0 bg-canvas" />

      {/* Radial dot grid, faded toward the edges so it never competes with text. */}
      <div className="bg-dots absolute inset-0 [mask-image:radial-gradient(ellipse_90%_80%_at_50%_35%,#000_55%,transparent_100%)]" />

      {/* Gold central glow. */}
      <div className="absolute left-1/2 top-[38%] h-[820px] w-[820px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(167,139,113,0.22),transparent_62%)] blur-2xl" />

      {/* Faint corner ember for depth. */}
      <div className="absolute -right-40 top-10 h-[420px] w-[420px] rounded-full bg-[radial-gradient(circle,rgba(201,184,160,0.1),transparent_65%)] blur-3xl" />

      {/* Top + bottom vignettes. */}
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-black/60 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/70 to-transparent" />
    </div>
  );
}

export default NeuralBackground;
