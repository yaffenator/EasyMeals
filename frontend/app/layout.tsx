import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "./context/auth";

export const metadata: Metadata = {
  title: "EasyMeals",
  description:
    "Get personalized meal plans tailored to your budget. Save money, eat healthier, and never wonder what's for dinner again.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
