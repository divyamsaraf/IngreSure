import type { Metadata } from "next";
import "./globals.css";
import ThemeRegistry from "@/theme/ThemeRegistry";

export const metadata: Metadata = {
  title: "IngreSure - AI Food Safety & Verification",
  description: "Verify menu ingredients, detect allergens, and eat with confidence using IngreSure's AI-powered platform.",
  openGraph: {
    title: "IngreSure - AI Food Safety",
    description: "Eat with confidence. Know what's inside.",
    type: "website",
  }
};

import Navbar from "@/components/Navbar";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased" suppressHydrationWarning>
        <ThemeRegistry>
          <Navbar />
          {children}
        </ThemeRegistry>
      </body>
    </html>
  );
}
