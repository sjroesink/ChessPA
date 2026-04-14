"use client";
import { useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Intercepts fetch responses to the backend API. On 401, redirects to /login.
 * Mounted once at the app root via layout.tsx.
 */
export default function AuthGuard() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const originalFetch = window.fetch;
    let installed = true;

    window.fetch = async (input, init) => {
      const response = await originalFetch(input, init);

      const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.toString();

      if (
        response.status === 401 &&
        url.startsWith(API_URL) &&
        window.location.pathname !== "/"
      ) {
        window.location.href = "/";
      }

      return response;
    };

    return () => {
      if (installed) {
        window.fetch = originalFetch;
        installed = false;
      }
    };
  }, []);

  return null;
}
