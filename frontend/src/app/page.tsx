const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        gap: "16px",
      }}
    >
      <div style={{ fontSize: "48px" }}>&#9823;</div>
      <h1 style={{ fontSize: "32px", fontWeight: 600 }}>ChessPA</h1>
      <p style={{ color: "var(--fg-secondary)", marginBottom: "24px" }}>
        Je persoonlijke schaakcoach
      </p>
      <a href={`${API_URL}/auth/google/login`}>
        <button style={{ width: "260px", marginBottom: "8px" }}>
          Login met Google
        </button>
      </a>
      <a href={`${API_URL}/auth/lichess/login`}>
        <button
          style={{
            width: "260px",
            marginBottom: "24px",
            background: "transparent",
            color: "var(--fg)",
            border: "1px solid var(--border)",
          }}
        >
          Login met Lichess
        </button>
      </a>
      <p
        style={{
          color: "var(--fg-secondary)",
          fontSize: "13px",
          maxWidth: "300px",
          textAlign: "center",
        }}
      >
        Chess.com koppel je na het inloggen via Instellingen.
      </p>
    </main>
  );
}
