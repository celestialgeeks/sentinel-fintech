import type { Metadata } from "next";
import { PortalShell } from "@/components/dashboard/portal-shell";

export const metadata: Metadata = {
  title: "Merchant desk",
  description: "Sentinel merchant portal — pre-settlement AML guard overview.",
};

/**
 * Everything under /dashboard shares the portal shell: the fixed glass sidebar,
 * the ambient noir backdrop, and the mobile nav drawer. Individual screens fill
 * the main column only.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <PortalShell>{children}</PortalShell>;
}
