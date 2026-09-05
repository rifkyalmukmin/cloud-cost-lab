import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { SiteHeader } from "@/components/site-header";

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
  title: {
    default: "Cloud Cost Lab — GCP FinOps Dashboard",
    template: "%s · Cloud Cost Lab",
  },
  description:
    "GCP FinOps & Cloud Cost Optimization platform — cost visibility, breakdowns, trends and budget awareness on synthetic demo data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="flex min-h-screen flex-col antialiased">
        <SiteHeader />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
        <footer className="border-t">
          <div className="mx-auto max-w-7xl px-4 py-3 text-xs text-muted-foreground sm:px-6">
            All figures come from the Cloud Cost Lab API and are synthetic demo data (
            <span className="font-mono">DEMO_MODE=true</span>) — treat every number as estimated/potential, never as
            realized savings.
          </div>
        </footer>
      </body>
    </html>
  );
}
