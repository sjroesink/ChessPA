import type { Metadata } from "next";
import "./globals.css";

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
      <body>{children}</body>
    </html>
  );
}
