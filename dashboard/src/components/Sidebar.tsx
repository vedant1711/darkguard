"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "@/app/layout.module.css";

const NAV_ITEMS = [
  { href: "/", icon: "📊", label: "Dashboard" },
  { href: "/scan", icon: "🔍", label: "New Scan" },
  { href: "/history", icon: "📋", label: "Scan History" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>🛡️</div>
        <span className={styles.logoText}>DarkGuard</span>
      </div>
      <nav className={styles.nav}>
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navLink} ${isActive ? styles.navLinkActive : ""}`}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
