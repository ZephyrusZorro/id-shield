import {
  LayoutDashboard,
  FileScan,
  History,
  FileText,
  BarChart3,
  Users,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_MAIN: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/screen/new", label: "Screen Documents", icon: FileScan },
  { to: "/history", label: "Screening History", icon: History },
  { to: "/reports", label: "Reports", icon: FileText },
];

export const NAV_SECONDARY: NavItem[] = [
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/users", label: "User Management", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings },
];
