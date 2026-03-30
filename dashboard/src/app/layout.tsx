import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import styles from "./layout.module.css";

export const metadata: Metadata = {
  title: "DarkGuard — Dark Pattern Auditor",
  description: "Enterprise dark pattern detection and compliance auditing dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className={styles.layoutWrap}>
          <Sidebar />
          <main className={styles.main}>{children}</main>
        </div>
      </body>
    </html>
  );
}
