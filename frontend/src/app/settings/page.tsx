"use client";

import { useEffect, useState, useRef } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ConnectedAccount {
  id: string;
  platform: string;
  platform_username: string;
  auto_sync: boolean;
}

interface MeResponse {
  username: string;
  email: string | null;
  connected_accounts: ConnectedAccount[];
}

// ─── Style constants ──────────────────────────────────────────────────────────

const pageStyle: React.CSSProperties = {
  padding: "32px",
  maxWidth: "720px",
  margin: "0 auto",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "40px",
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "var(--fg-secondary)",
  marginBottom: "16px",
  borderBottom: "1px solid var(--border)",
  paddingBottom: "8px",
};

const cardStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  background: "var(--bg-secondary)",
  padding: "16px",
  marginBottom: "8px",
};

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "12px",
  flexWrap: "wrap",
};

const labelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "var(--fg-secondary)",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  marginBottom: "4px",
};

const inputStyle: React.CSSProperties = {
  background: "var(--bg)",
  border: "1px solid var(--border)",
  color: "var(--fg)",
  padding: "8px 12px",
  fontSize: "14px",
  fontFamily: "inherit",
  width: "100%",
  outline: "none",
};

const btnPrimaryStyle: React.CSSProperties = {
  background: "var(--accent)",
  color: "var(--bg)",
  border: "1px solid var(--border)",
  padding: "8px 16px",
  fontSize: "14px",
  cursor: "pointer",
  fontFamily: "inherit",
  flexShrink: 0,
};

const btnDangerStyle: React.CSSProperties = {
  background: "transparent",
  color: "var(--danger)",
  border: "1px solid var(--danger)",
  padding: "6px 12px",
  fontSize: "13px",
  cursor: "pointer",
  fontFamily: "inherit",
  flexShrink: 0,
};

const btnDisabledStyle: React.CSSProperties = {
  opacity: 0.5,
  cursor: "not-allowed",
};

const feedbackStyle = (ok: boolean): React.CSSProperties => ({
  fontSize: "13px",
  color: ok ? "var(--success)" : "var(--danger)",
  marginTop: "8px",
});

const toggleWrapStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  marginTop: "10px",
};

// ─── Toggle switch ────────────────────────────────────────────────────────────

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={() => !disabled && onChange(!checked)}
      style={{
        width: "36px",
        height: "20px",
        background: checked ? "var(--success)" : "var(--border)",
        border: "none",
        padding: 0,
        cursor: disabled ? "not-allowed" : "pointer",
        position: "relative",
        flexShrink: 0,
        opacity: disabled ? 0.5 : 1,
      }}
      aria-checked={checked}
      role="switch"
      type="button"
    >
      <span
        style={{
          position: "absolute",
          top: "3px",
          left: checked ? "18px" : "3px",
          width: "14px",
          height: "14px",
          background: "var(--bg)",
          transition: "left 0.15s",
          display: "block",
        }}
      />
    </button>
  );
}

// ─── Section 1: Gekoppelde accounts ──────────────────────────────────────────

function AccountCard({
  account,
  onToggleSync,
  onUnlink,
}: {
  account: ConnectedAccount;
  onToggleSync: (id: string, val: boolean) => Promise<void>;
  onUnlink: (id: string) => Promise<void>;
}) {
  const [toggling, setToggling] = useState(false);
  const [unlinking, setUnlinking] = useState(false);
  const [localSync, setLocalSync] = useState(account.auto_sync);
  const [error, setError] = useState<string | null>(null);

  async function handleToggle(val: boolean) {
    setToggling(true);
    setError(null);
    try {
      await onToggleSync(account.id, val);
      setLocalSync(val);
    } catch {
      setError("Kon auto-sync niet bijwerken.");
    } finally {
      setToggling(false);
    }
  }

  async function handleUnlink() {
    if (!confirm(`${account.platform_username} ontkoppelen?`)) return;
    setUnlinking(true);
    setError(null);
    try {
      await onUnlink(account.id);
    } catch {
      setError("Ontkoppelen mislukt.");
      setUnlinking(false);
    }
  }

  return (
    <div style={cardStyle}>
      <div style={rowStyle}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: "14px" }}>{account.platform_username}</div>
          <div style={{ fontSize: "12px", color: "var(--fg-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {account.platform.replace("_", ".")}
          </div>
        </div>
        {account.platform === "chess_com" && (
          <button
            onClick={handleUnlink}
            disabled={unlinking}
            style={{ ...btnDangerStyle, ...(unlinking ? btnDisabledStyle : {}) }}
          >
            {unlinking ? "Bezig..." : "Ontkoppelen"}
          </button>
        )}
      </div>
      <div style={toggleWrapStyle}>
        <Toggle checked={localSync} onChange={handleToggle} disabled={toggling} />
        <span style={{ fontSize: "13px", color: "var(--fg-secondary)" }}>
          Automatisch synchroniseren
        </span>
        {toggling && <span style={{ fontSize: "12px", color: "var(--fg-secondary)" }}>Opslaan...</span>}
      </div>
      {error && <div style={feedbackStyle(false)}>{error}</div>}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);

  // Chess.com koppelen
  const [connectUsername, setConnectUsername] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectFeedback, setConnectFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  // PGN importeren
  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importFeedback, setImportFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  // Synchroniseren
  const [syncing, setSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/auth/me`, { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error();
        return res.json() as Promise<MeResponse>;
      })
      .then((data) => {
        setAccounts(data.connected_accounts ?? []);
      })
      .catch(() => setAccountsError("Kon accounts niet laden."))
      .finally(() => setLoadingAccounts(false));
  }, []);

  async function handleToggleSync(id: string, val: boolean) {
    const res = await fetch(`${API_URL}/api/accounts/${id}/auto-sync`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_sync: val }),
    });
    if (!res.ok) throw new Error();
  }

  async function handleUnlink(id: string) {
    const res = await fetch(`${API_URL}/api/accounts/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) throw new Error();
    setAccounts((prev) => prev.filter((a) => a.id !== id));
  }

  async function handleConnect(e: React.FormEvent) {
    e.preventDefault();
    if (!connectUsername.trim()) return;
    setConnecting(true);
    setConnectFeedback(null);
    try {
      const res = await fetch(`${API_URL}/api/accounts/connect/chess-com`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: connectUsername.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setConnectFeedback({ ok: false, msg: (err as { detail?: string }).detail ?? "Koppelen mislukt." });
        return;
      }
      const data = await res.json();
      // Refetch accounts to get full objects with id
      const meRes = await fetch(`${API_URL}/auth/me`, { credentials: "include" });
      if (meRes.ok) {
        const me = await meRes.json();
        setAccounts(me.connected_accounts ?? []);
      }
      setConnectUsername("");
      setConnectFeedback({ ok: true, msg: `${data.username} succesvol gekoppeld.` });
    } catch {
      setConnectFeedback({ ok: false, msg: "Netwerkfout bij koppelen." });
    } finally {
      setConnecting(false);
    }
  }

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportFeedback(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_URL}/api/games/import/pgn`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setImportFeedback({ ok: false, msg: (err as { detail?: string }).detail ?? "Importeren mislukt." });
        return;
      }
      const data = await res.json();
      const count: number = data.imported ?? data.count ?? data.games_imported ?? 0;
      setImportFeedback({ ok: true, msg: `${count} ${count === 1 ? "partij" : "partijen"} geïmporteerd.` });
      if (fileRef.current) fileRef.current.value = "";
    } catch {
      setImportFeedback({ ok: false, msg: "Netwerkfout bij importeren." });
    } finally {
      setImporting(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    setSyncFeedback(null);
    try {
      const res = await fetch(`${API_URL}/api/games/sync`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setSyncFeedback({ ok: false, msg: (err as { detail?: string }).detail ?? "Synchronisatie mislukt." });
        return;
      }
      const data = await res.json();
      const count: number = data.synced ?? data.count ?? data.games_synced ?? 0;
      setSyncFeedback({ ok: true, msg: `${count} ${count === 1 ? "partij" : "partijen"} gesynchroniseerd.` });
    } catch {
      setSyncFeedback({ ok: false, msg: "Netwerkfout bij synchroniseren." });
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main style={pageStyle}>
      <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "32px" }}>Instellingen</h1>

      {/* ── 1. Gekoppelde accounts ── */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle as React.CSSProperties}>Gekoppelde accounts</div>
        {loadingAccounts ? (
          <p style={{ color: "var(--fg-secondary)", fontSize: "14px" }}>Accounts laden...</p>
        ) : accountsError ? (
          <p style={{ color: "var(--danger)", fontSize: "14px" }}>{accountsError}</p>
        ) : accounts.length === 0 ? (
          <div
            style={{
              border: "1px solid var(--border)",
              background: "var(--bg-secondary)",
              padding: "32px",
              textAlign: "center",
              color: "var(--fg-secondary)",
              fontSize: "14px",
            }}
          >
            Geen accounts gekoppeld.
          </div>
        ) : (
          accounts.map((acc) => (
            <AccountCard
              key={acc.id}
              account={acc}
              onToggleSync={handleToggleSync}
              onUnlink={handleUnlink}
            />
          ))
        )}
      </div>

      {/* ── 2. Chess.com koppelen ── */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle as React.CSSProperties}>Chess.com koppelen</div>
        <form onSubmit={handleConnect}>
          <div style={{ marginBottom: "12px" }}>
            <div style={labelStyle}>Chess.com gebruikersnaam</div>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type="text"
                value={connectUsername}
                onChange={(e) => setConnectUsername(e.target.value)}
                placeholder="bijv. hikaru"
                style={inputStyle}
                disabled={connecting}
                autoComplete="off"
              />
              <button
                type="submit"
                disabled={connecting || !connectUsername.trim()}
                style={{
                  ...btnPrimaryStyle,
                  ...(connecting || !connectUsername.trim() ? btnDisabledStyle : {}),
                }}
              >
                {connecting ? "Bezig..." : "Koppelen"}
              </button>
            </div>
          </div>
          {connectFeedback && (
            <div style={feedbackStyle(connectFeedback.ok)}>{connectFeedback.msg}</div>
          )}
        </form>
      </div>

      {/* ── 3. PGN importeren ── */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle as React.CSSProperties}>PGN importeren</div>
        <form onSubmit={handleImport}>
          <div style={{ marginBottom: "12px" }}>
            <div style={labelStyle}>PGN-bestand</div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <input
                ref={fileRef}
                type="file"
                accept=".pgn,text/plain"
                disabled={importing}
                style={{
                  fontSize: "14px",
                  color: "var(--fg)",
                  flex: 1,
                  minWidth: 0,
                }}
              />
              <button
                type="submit"
                disabled={importing}
                style={{
                  ...btnPrimaryStyle,
                  ...(importing ? btnDisabledStyle : {}),
                }}
              >
                {importing ? "Bezig..." : "Importeren"}
              </button>
            </div>
          </div>
          {importFeedback && (
            <div style={feedbackStyle(importFeedback.ok)}>{importFeedback.msg}</div>
          )}
        </form>
      </div>

      {/* ── 4. Partijen synchroniseren ── */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle as React.CSSProperties}>Partijen synchroniseren</div>
        <p style={{ fontSize: "14px", color: "var(--fg-secondary)", marginBottom: "12px" }}>
          Haal de nieuwste partijen op van alle gekoppelde accounts.
        </p>
        <button
          onClick={handleSync}
          disabled={syncing}
          style={{ ...btnPrimaryStyle, ...(syncing ? btnDisabledStyle : {}) }}
        >
          {syncing ? "Bezig..." : "Nu synchroniseren"}
        </button>
        {syncFeedback && (
          <div style={feedbackStyle(syncFeedback.ok)}>{syncFeedback.msg}</div>
        )}
      </div>
    </main>
  );
}
