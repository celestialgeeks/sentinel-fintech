import { PortalHeader } from "@/components/dashboard/portal-header";
import { VolumeHero } from "@/components/dashboard/volume-hero";
import { MetricsGrid } from "@/components/dashboard/metrics-grid";
import { VerdictRing } from "@/components/dashboard/verdict-ring";
import { RiskHistogram } from "@/components/dashboard/risk-histogram";
import { QuarantineCard } from "@/components/dashboard/quarantine-card";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { ProviderHealth, TopRules } from "@/components/dashboard/signal-panels";
import { dashboardData } from "@/lib/dashboard-data";

/**
 * Overview — the first screen after login. It is the `/portal/overview` snapshot
 * laid out as a Zenix bento in the Neural Noir system: a hero for cleared
 * volume, three verdict tiles, a signals row (mix ring · risk distribution ·
 * quarantine), then the work that is actually waiting (HOLD queue) beside health
 * and rule leaderboards. Data is illustrative but field-for-field from
 * docs/PORTAL_API.md; swap `dashboardData` for the endpoint without touching JSX.
 */
export default function DashboardOverviewPage() {
  const d = dashboardData;

  return (
    <div className="flex flex-col gap-6">
      <PortalHeader />

      <VolumeHero summary={d.summary} timeseries={d.timeseries} />

      <MetricsGrid summary={d.summary} />

      {/* Signals row — three equal tiles. */}
      <section className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        <Panel stagger={4}>
          <VerdictRing mix={d.mix} />
        </Panel>
        <Panel stagger={5}>
          <RiskHistogram buckets={d.risk_histogram} />
        </Panel>
        <Panel stagger={6} className="md:col-span-2 lg:col-span-1">
          <QuarantineCard summary={d.summary} />
        </Panel>
      </section>

      {/* Work + context — the HOLD queue carries, health and rules support. */}
      <section className="grid gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ActivityFeed rows={d.needs_action} />
        </div>
        <div className="flex flex-col gap-5">
          <Panel stagger={7}>
            <ProviderHealth providers={d.providers} />
          </Panel>
          <Panel stagger={8}>
            <TopRules rules={d.top_rules} />
          </Panel>
        </div>
      </section>

      <p className="pt-2 text-center font-mono text-[11px] text-ink-500">
        Illustrative data · same shape as GET /api/v1/portal/overview · advisory tooling, files nothing.
      </p>
    </div>
  );
}

/** Shared glass tile wrapper so the bento cards keep identical depth + entrance. */
function Panel({
  children,
  stagger,
  className = "",
}: {
  children: React.ReactNode;
  stagger: number;
  className?: string;
}) {
  return (
    <div
      className={`liquid-glass glass-card fade-up rounded-2xl p-6 ${className}`}
      style={{ ["--stagger" as string]: stagger }}
    >
      {children}
    </div>
  );
}
