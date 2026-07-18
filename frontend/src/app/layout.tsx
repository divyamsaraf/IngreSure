import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Newsreader } from "next/font/google";
import "./globals.css";

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

export const metadata: Metadata = {
  title: "IngreSure - Ingredient safety you can verify",
  description:
    "Paste a label or menu. Get Safe / Avoid / Depends audits for your diet and allergens — rules-based, not guesswork. No signup.",
  openGraph: {
    title: "IngreSure — Know what's inside",
    description: "Eat with confidence. Personalized ingredient audits without an account.",
    type: "website",
  },
};

import Navbar from "@/components/Navbar";
import { ConfigProvider } from "@/context/ConfigContext";
import { ProfileProvider } from "@/context/ProfileContext";
import { Analytics } from "@vercel/analytics/react";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${jakarta.variable} ${newsreader.variable}`}>
      <body className="antialiased font-sans" suppressHydrationWarning>
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
