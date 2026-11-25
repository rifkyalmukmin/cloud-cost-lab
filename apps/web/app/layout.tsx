import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Cloud Cost Lab",
  description: "GCP FinOps & Cloud Cost Optimization Platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b bg-card">
          <div className="max-w-7xl mx-auto px-6 min-h-14 py-2 flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link href="/" className="font-semibold text-sm">
              Cloud Cost Lab
            </Link>
            <nav className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <Link href="/" className="hover:text-foreground transition-colors">
                Overview
              </Link>
              <Link href="/cost" className="hover:text-foreground transition-colors">
                Cost Explorer
              </Link>
              <Link href="/resources" className="hover:text-foreground transition-colors">
                Resources
              </Link>
              <Link href="/utilization" className="hover:text-foreground transition-colors">
                Utilization
              </Link>
              <Link href="/recommendations" className="hover:text-foreground transition-colors">
                Recommendations
              </Link>
              <Link href="/approvals" className="hover:text-foreground transition-colors">
                Approvals
              </Link>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
