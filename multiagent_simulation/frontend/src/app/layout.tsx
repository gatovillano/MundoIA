import type { Metadata } from "next";
import { Outfit, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import BackgroundEffects from "@/components/BackgroundEffects";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Mundo IA: Genesis",
  description: "Simulación Multi-Agente Avanzada",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${outfit.variable} ${jetbrainsMono.variable} antialiased bg-background text-foreground overflow-hidden relative`}
      >
        <BackgroundEffects />
        {children}
      </body>
    </html>
  );
}
