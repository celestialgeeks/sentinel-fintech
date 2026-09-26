"use client";

/**
 * testimonial.tsx — 21st.dev bento testimonial section, adapted for Sentinel.
 *
 * Three deliberate changes to the upstream component, beyond the copy:
 *
 * 1. **Dark surfaces.** The original is `bg-white text-black` with
 *    `border-gray-200`; this page is a dark canvas with KineticGrid behind it,
 *    so every surface maps to the shadcn/Sentinel tokens instead. `bg-primaryColor`
 *    in the paste is an undefined class and is dropped.
 * 2. **Monograms instead of stock photos.** A "merchant testimonial" illustrated
 *    with an Unsplash face is a fabricated person. `photo` is supported for real
 *    portraits from `/public` when there are real people to show.
 * 3. **`consented` gates the disclosure.** Every entry below is an illustrative
 *    persona, not a real customer, and the section says so. The note disappears
 *    automatically once every entry is a quote the merchant has agreed to
 *    publish. Attribution to a real, named Binance merchant requires their
 *    permission — see docs/UI_BUILD_MAP.md §7.
 */

import Image from "next/image";
import { useRef } from "react";
import { MotionConfig } from "motion/react";

import { TimelineContent } from "@/components/ui/timeline-animation";
import { cn } from "@/lib/utils";

type Testimonial = {
  quote: string;
  /** Who is speaking. Role and desk, not a personal name, until it is real. */
  identity: string;
  detail?: string;
  monogram: string;
  /** Portrait served from /public, e.g. "/testimonials/desk.jpg". */
  photo?: string;
  /** True only once this person has agreed to be quoted by name. */
  consented: boolean;
};

const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      "The buyer paid from his brother's account. On a screenshot check that passes every time. Sentinel blocked it at the release gate before USDT left escrow — that credit is the reason my account is still operating.",
    identity: "USDT/INR desk, Bengaluru",
    detail: "~₹40L a month",
    monogram: "BL",
    consented: false,
  },
  {
    quote:
      "The pack did the arguing for me. Bank asked what the credit was; I sent the UTR, the voucher and the vendor verdicts. Lien lifted in four working days.",
    identity: "Solo merchant, Delhi NCR",
    monogram: "DN",
    consented: false,
  },
  {
    quote:
      "I run my own bot. Two signed POSTs and it never touched my strategy — it just says release, hold or reject, and I decide what to do about it.",
    identity: "Bot builder, Pune",
    monogram: "PB",
    consented: false,
  },
  {
    quote:
      "A HOLD used to mean guessing. Now it lists what to ask the buyer for, and most of them clear inside the release window.",
    identity: "Two-account desk, Hyderabad",
    monogram: "HY",
    consented: false,
  },
  {
    quote:
      "A data source went down for twenty minutes. Everything came back as degraded HOLD, not a quiet allow. That is the behaviour I was actually buying.",
    identity: "Desk with a night shift, Chennai",
    monogram: "CN",
    consented: false,
  },
  {
    quote:
      "Quarantine vouchers mean one bad credit does not sit in the same pool as tomorrow's settlements.",
    identity: "Merchant, Mumbai · CA-managed books",
    monogram: "MU",
    consented: false,
  },
];

function Card({
  testimonial,
  className,
  accent,
  tone = "neutral",
}: {
  testimonial: Testimonial;
  className?: string;
  accent?: boolean;
  tone?: "neutral" | "brand" | "ink";
}) {
  return (
    <article className="relative z-10 mt-auto">
      <p className="text-[0.95rem] leading-relaxed">
        &ldquo;{testimonial.quote}&rdquo;
      </p>
      <div className="flex items-end justify-between gap-4 pt-5">
        <div>
          <h3 className="text-sm font-semibold sm:text-base">{testimonial.identity}</h3>
          {testimonial.detail ? (
            <p className="mt-0.5 text-xs text-muted-foreground sm:text-sm">{testimonial.detail}</p>
          ) : null}
          {!testimonial.consented ? (
            <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              Illustrative
            </p>
          ) : null}
        </div>
        {testimonial.photo ? (
          <Image
            src={testimonial.photo}
            alt=""
            width={200}
            height={200}
            className="size-12 shrink-0 rounded-xl object-cover lg:size-16"
          />
        ) : (
          <span
            aria-hidden="true"
            className={cn(
              "grid size-12 shrink-0 place-items-center rounded-xl font-mono text-sm lg:size-16",
              accent ? "bg-black/15 text-white" : "border border-border bg-muted text-muted-foreground",
            )}
          >
            {testimonial.monogram}
          </span>
        )}
      </div>
    </article>
  );
}

export function MerchantTestimonials() {
  const sectionRef = useRef<HTMLElement>(null);

  const revealVariants = {
    visible: (i: number) => ({
      y: 0,
      opacity: 1,
      filter: "blur(0px)",
      transition: { delay: i * 0.12, duration: 0.5 },
    }),
    hidden: { filter: "blur(10px)", y: 20, opacity: 0 },
  };

  const allConsented = TESTIMONIALS.every((t) => t.consented);

  const card = "relative flex flex-col overflow-hidden rounded-lg border border-border p-5";
  const gridOverlay = (
    <span
      aria-hidden="true"
      className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:50px_56px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_110%)]"
    />
  );

  return (
    <MotionConfig reducedMotion="user">
      <section
        ref={sectionRef}
        id="merchants"
        className="mx-auto w-full max-w-6xl scroll-mt-24 px-4 py-16 sm:px-8 lg:py-24"
      >
        <article className="mx-auto max-w-screen-md space-y-2 text-center">
          <TimelineContent
            as="h2"
            animationNum={0}
            customVariants={revealVariants}
            timelineRef={sectionRef}
            className="font-serif text-3xl tracking-[-0.01em] text-foreground xl:text-4xl"
          >
            What changes on the desk after the guard goes live
          </TimelineContent>
          <TimelineContent
            as="p"
            animationNum={1}
            customVariants={revealVariants}
            timelineRef={sectionRef}
            className="mx-auto text-muted-foreground"
          >
            Six situations the verdicts were written for — a third-party payer, a
            lien notice, a vendor outage, a release window running out.
          </TimelineContent>
          {allConsented ? null : (
            <TimelineContent
              as="p"
              animationNum={2}
              customVariants={revealVariants}
              timelineRef={sectionRef}
              className="mx-auto max-w-md pt-2 font-mono text-[11px] leading-relaxed text-muted-foreground"
            >
              Sample copy. Not customer statements — each one becomes real only
              when a merchant has agreed to be quoted.
            </TimelineContent>
          )}
        </article>

        <div className="flex w-full flex-col gap-2 pt-10 lg:grid lg:grid-cols-3 lg:gap-2 lg:py-10">
          {/* Column 1 — the long story, then a short one. */}
          <div className="flex h-full flex-col gap-2 md:flex-row lg:flex-col lg:gap-2">
            <TimelineContent
              animationNum={0}
              customVariants={revealVariants}
              timelineRef={sectionRef}
              className={cn(card, "bg-card flex-[6] text-card-foreground lg:flex-[7]")}
            >
              {gridOverlay}
              <Card testimonial={TESTIMONIALS[0]} />
            </TimelineContent>
            <TimelineContent
              animationNum={1}
              customVariants={revealVariants}
              timelineRef={sectionRef}
              className={cn(card, "bg-primary flex-[4] text-primary-foreground lg:flex-[3]")}
            >
              <Card testimonial={TESTIMONIALS[1]} accent />
            </TimelineContent>
          </div>

          {/* Column 2 — three equal cards. */}
          <div className="flex h-fit flex-col gap-2 md:flex-row lg:flex-col lg:gap-2">
            {[2, 3, 4].map((index, i) => (
              <TimelineContent
                key={TESTIMONIALS[index].monogram}
                animationNum={index}
                customVariants={revealVariants}
                timelineRef={sectionRef}
                className={cn(card, "bg-card flex-1 text-card-foreground")}
              >
                {gridOverlay}
                <Card testimonial={TESTIMONIALS[index]} />
              </TimelineContent>
            ))}
          </div>

          {/* Column 3 — short one on top, long one below. */}
          <div className="flex h-full flex-col gap-2 md:flex-row lg:flex-col lg:gap-2">
            <TimelineContent
              animationNum={5}
              customVariants={revealVariants}
              timelineRef={sectionRef}
              className={cn(card, "bg-primary flex-[4] text-primary-foreground lg:flex-[3]")}
            >
              <Card testimonial={TESTIMONIALS[5]} accent />
            </TimelineContent>
            <TimelineContent
              animationNum={6}
              customVariants={revealVariants}
              timelineRef={sectionRef}
              className={cn(card, "bg-foreground/[0.06] flex-[6] text-foreground lg:flex-[7]")}
            >
              {gridOverlay}
              <Card
                testimonial={{
                  quote:
                    "Nothing here is a promise that an account will never be frozen. It is proof you asked the right question before the money moved, and a record of the answer.",
                  identity: "Why merchants keep the packs",
                  monogram: "EV",
                  consented: true,
                }}
              />
            </TimelineContent>
          </div>
        </div>
      </section>
    </MotionConfig>
  );
}

export default MerchantTestimonials;
