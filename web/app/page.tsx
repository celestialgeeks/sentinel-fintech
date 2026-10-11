import { NeuralBackground } from "@/components/ui/neural-background";
import { NavNoir } from "@/components/ui/nav-noir";
import { NeuralHero } from "@/components/ui/neural-hero";
import { FeaturesGrid } from "@/components/ui/features-grid";
import { Evidence } from "@/components/ui/evidence";
import { Integrations } from "@/components/ui/integrations";
import { Pricing } from "@/components/ui/pricing";
import { Audience } from "@/components/ui/audience";
import { NeuralFooter } from "@/components/ui/neural-footer";
import { MerchantTestimonials } from "@/components/ui/testimonial";

/**
 * Sentinel landing page — "Neural Noir" system.
 *
 * The visual language (dark #0a0a0a canvas, gold/bronze accents, glassmorphism,
 * Playfair Italic headings, a neural hero with pulsing connection lines) follows
 * the template; every word — hero copy, verdict payload, signals, evidence
 * structure, pricing tiers, disclaimer — is Sentinel's own, from
 * docs/WEBSITE_CONTENT_BRIEF.md. Compliance is preserved: verdict colour is never
 * carried by hue alone, personas and testimonials are labelled illustrative, and
 * the advisory disclaimer is always present.
 */
export default function LandingPage() {
  return (
    <>
      <NeuralBackground />
      <NavNoir />

      <div className="relative z-10">
        <main>
          <NeuralHero />
          <FeaturesGrid />
          <Evidence />
          <Integrations />
          <MerchantTestimonials />
          <Pricing />
          <Audience />
        </main>
        <NeuralFooter />
      </div>
    </>
  );
}
