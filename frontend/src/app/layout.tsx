import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Newsreader } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { ConfigProvider } from "@/context/ConfigContext";
import { ProfileProvider } from "@/context/ProfileContext";
import { Analytics } from "@vercel/analytics/react";
import { buildRootMetadata, buildSiteJsonLd } from "@/lib/seo";

/**
 * Body/UI: Plus Jakarta Sans (taste: avoid Inter default).
 * Display: Newsreader (user-approved distinctive serif; avoids Fraunces LLM-default).
 */
const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans-custom",
  weight: ["400", "500", "600", "700"],
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = buildRootMetadata();

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const jsonLd = buildSiteJsonLd();

  return (
    <html lang="en" className={`${jakarta.variable} ${newsreader.variable}`}>
      <body className="antialiased font-sans" suppressHydrationWarning>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <ConfigProvider>
          <ProfileProvider>
            <Navbar />
            {children}
          </ProfileProvider>
        </ConfigProvider>
        <Analytics />
      </body>
    </html>
  );
}
