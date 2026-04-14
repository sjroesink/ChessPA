"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UserData {
  username: string;
  email: string | null;
}

export default function Nav() {
  const [user, setUser] = useState<UserData | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    fetch(`${API_URL}/auth/me`, { credentials: "include" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setUser(data))
      .catch(() => setUser(null));
  }, []);

  if (!user || pathname === "/") return null;

  const links = [
    { href: "/coach", label: "Coach" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/games", label: "Partijen" },
    { href: "/settings", label: "Instellingen" },
  ];

  return (
    <nav style={{
      display: "flex",
      alignItems: "center",
      padding: "0 24px",
      height: "48px",
      borderBottom: "1px solid var(--border)",
      background: "var(--bg)",
      gap: "24px",
      fontSize: "14px",
    }}>
      <Link href="/coach" style={{ fontWeight: 700, fontSize: "16px", marginRight: "8px" }}>
        ♟ ChessPA
      </Link>
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          style={{
            color: pathname === link.href ? "var(--fg)" : "var(--fg-secondary)",
            fontWeight: pathname === link.href ? 600 : 400,
          }}
        >
          {link.label}
        </Link>
      ))}
      <span style={{ marginLeft: "auto", color: "var(--fg-secondary)", fontSize: "13px" }}>
        {user.username}
      </span>
    </nav>
  );
}
