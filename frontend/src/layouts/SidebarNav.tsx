import { NavLink } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
  module: "dashboard" | "reception" | "clinical";
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Tổng quan", module: "dashboard", icon: "◉" },
  { to: "/reception", label: "Tiếp đón", module: "reception", icon: "◎" },
  { to: "/clinical", label: "Lâm sàng", module: "clinical", icon: "◈" },
];

export function SidebarNav() {
  const { canAccess } = useAuth();

  const visibleItems = NAV_ITEMS.filter((item) => canAccess(item.module));

  return (
    <nav className="space-y-1">
      {visibleItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            [
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
              isActive
                ? "bg-brand-600 text-white shadow-sm"
                : "text-slate-300 hover:bg-surface-800 hover:text-white",
            ].join(" ")
          }
        >
          <span className="text-base">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
