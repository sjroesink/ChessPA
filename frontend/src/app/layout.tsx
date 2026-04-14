import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import AuthGuard from "@/components/AuthGuard";

export const metadata: Metadata = {
  title: "ChessPA",
  description: "Your personal chess coach",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthGuard />
        <Nav />
        {children}
      </body>
    </html>
  );
}
