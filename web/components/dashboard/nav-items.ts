import type { LucideIcon } from "lucide-react";
import {
  LayoutGrid,
  Radio,
  List,
  Clock,
  Users,
  Landmark,
  ShieldAlert,
  ScrollText,
  ChartColumn,
  Settings,
} from "lucide-react";

/**
 * Single source of truth for the desk navigation, shared by the desktop sidebar
 * and the mobile drawer so the two can never drift. Mirrors the merchant portal
 * IA in docs/PORTAL_API.md §5.
 */
export interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Monitor",
    items: [
      { name: "Overview", href: "/dashboard", icon: LayoutGrid },
      { name: "Live feed", href: "/dashboard/feed", icon: Radio },
      { name: "Orders", href: "/dashboard/orders", icon: List },
      { name: "Holds", href: "/dashboard/holds", icon: Clock, badge: "1" },
    ],
  },
  {
    label: "Operations",
    items: [
      { name: "Buyers", href: "/dashboard/buyers", icon: Users },
      { name: "Quarantine", href: "/dashboard/quarantine", icon: Landmark },
      { name: "Freeze cases", href: "/dashboard/freezes", icon: ShieldAlert, badge: "1" },
      { name: "Compliance", href: "/dashboard/compliance", icon: ScrollText },
      { name: "Insights", href: "/dashboard/insights", icon: ChartColumn },
      { name: "Settings", href: "/dashboard/settings", icon: Settings },
    ],
  },
];
