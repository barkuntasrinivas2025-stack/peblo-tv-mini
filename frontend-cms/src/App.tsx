import { useState } from "react";
import { api, setAuthToken } from "./api-client";

type Show = {
  id: string;
  title: string;
  category?: string;
  synopsis?: string;
  artwork?: Record<string, string>;
  seasons?: unknown[];
  trailers?: unknown[];
};

type Catalog = {
  generated_fields_are_deterministic?: boolean;
  sections?: Record<string, Show[]>;
};

export default function App() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [loggedIn, setLoggedIn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [message, setMessage] = useState("");

  async function login() {
    try {
      setLoading(true);
      setMessage("");

      const data = await api.login(username, password);

      if (!data.access_token) {
        throw new Error("Login failed: access token was not returned");
      }

      setAuthToken(data.access_token);
      setLoggedIn(true);
      setMessage("Successfully connected to the Peblo TV API.");
    } catch (error: any) {
      setMessage(error.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadCatalog() {
    try {
      setLoading(true);
      setMessage("");

      const data = await api.getCatalog();
      setCatalog(data);

      const sectionCount = Object.keys(data.sections || {}).length;
      const showCount = Object.values(data.sections || {}).reduce(
        (total: number, shows: any) => total + shows.length,
        0
      );

      setMessage(
        `Published catalog loaded successfully — ${showCount} show(s) across ${sectionCount} section(s).`
      );
    } catch (error: any) {
      setMessage(error.message || "Unable to load published catalog");
    } finally {
      setLoading(false);
    }
  }

  const totalShows = catalog
    ? Object.values(catalog.sections || {}).reduce(
        (total, shows) => total + shows.length,
        0
      )
    : 0;

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(135deg, #020617 0%, #0f172a 45%, #172554 100%)",
        color: "#f8fafc",
        fontFamily:
          "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        padding: "32px",
      }}
    >
      <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "32px",
            flexWrap: "wrap",
            gap: "16px",
          }}
        >
          <div>
            <p
              style={{
                margin: 0,
                color: "#38bdf8",
                fontWeight: 700,
                letterSpacing: "0.08em",
                fontSize: "13px",
              }}
            >
              CONTENT MANAGEMENT SYSTEM
            </p>

            <h1
              style={{
                margin: "8px 0 0",
                fontSize: "36px",
              }}
            >
              Peblo TV CMS
            </h1>
          </div>

          <div
            style={{
              padding: "10px 16px",
              borderRadius: "999px",
              background: loggedIn
                ? "rgba(34, 197, 94, 0.15)"
                : "rgba(148, 163, 184, 0.15)",
              border: loggedIn
                ? "1px solid rgba(34, 197, 94, 0.35)"
                : "1px solid rgba(148, 163, 184, 0.25)",
              color: loggedIn ? "#86efac" : "#cbd5e1",
              fontWeight: 600,
            }}
          >
            {loggedIn ? "● API Connected" : "● Not Connected"}
          </div>
        </header>

        {!loggedIn ? (
          <div
            style={{
              maxWidth: "480px",
              margin: "80px auto",
              padding: "32px",
              background: "rgba(15, 23, 42, 0.85)",
              border: "1px solid rgba(148, 163, 184, 0.2)",
              borderRadius: "20px",
              boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Admin Login</h2>

            <p style={{ color: "#94a3b8", marginBottom: "24px" }}>
              Sign in to manage and review the Peblo TV catalog.
            </p>

            <label
              style={{
                display: "block",
                marginBottom: "8px",
                color: "#cbd5e1",
              }}
            >
              Username
            </label>

            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "13px",
                marginBottom: "18px",
                borderRadius: "10px",
                border: "1px solid #334155",
                background: "#020617",
                color: "white",
                fontSize: "15px",
              }}
            />

            <label
              style={{
                display: "block",
                marginBottom: "8px",
                color: "#cbd5e1",
              }}
            >
              Password
            </label>

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "13px",
                marginBottom: "20px",
                borderRadius: "10px",
                border: "1px solid #334155",
                background: "#020617",
                color: "white",
                fontSize: "15px",
              }}
            />

            <button
              onClick={login}
              disabled={loading}
              style={{
                width: "100%",
                padding: "14px",
                borderRadius: "10px",
                border: "none",
                cursor: loading ? "wait" : "pointer",
                fontWeight: 700,
                fontSize: "15px",
                background: "#38bdf8",
                color: "#082f49",
              }}
            >
              {loading ? "Connecting..." : "Login to CMS"}
            </button>

            {message && (
              <p
                style={{
                  marginTop: "20px",
                  padding: "12px",
                  borderRadius: "8px",
                  background: "rgba(15, 23, 42, 0.8)",
                  color: "#cbd5e1",
                }}
              >
                {message}
              </p>
            )}
          </div>
        ) : (
          <>
            <section
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "18px",
                marginBottom: "28px",
              }}
            >
              <StatCard
                label="API Status"
                value="Connected"
                accent="#22c55e"
              />

              <StatCard
                label="Published Shows"
                value={catalog ? String(totalShows) : "—"}
                accent="#38bdf8"
              />

              <StatCard
                label="Catalog Sections"
                value={
                  catalog
                    ? String(Object.keys(catalog.sections || {}).length)
                    : "—"
                }
                accent="#a78bfa"
              />
            </section>

            <section
              style={{
                padding: "28px",
                background: "rgba(15, 23, 42, 0.82)",
                border: "1px solid rgba(148, 163, 184, 0.18)",
                borderRadius: "20px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "20px",
                  flexWrap: "wrap",
                  marginBottom: "24px",
                }}
              >
                <div>
                  <h2 style={{ margin: 0 }}>Published Catalog</h2>

                  <p style={{ color: "#94a3b8", marginBottom: 0 }}>
                    Review content currently returned by the public catalog
                    endpoint.
                  </p>
                </div>

                <button
                  onClick={loadCatalog}
                  disabled={loading}
                  style={{
                    padding: "13px 20px",
                    borderRadius: "10px",
                    border: "none",
                    cursor: loading ? "wait" : "pointer",
                    fontWeight: 700,
                    background: "#38bdf8",
                    color: "#082f49",
                  }}
                >
                  {loading ? "Loading..." : "Load Published Catalog"}
                </button>
              </div>

              {message && (
                <div
                  style={{
                    marginBottom: "24px",
                    padding: "14px",
                    borderRadius: "10px",
                    background: "rgba(34, 197, 94, 0.08)",
                    border: "1px solid rgba(34, 197, 94, 0.2)",
                    color: "#bbf7d0",
                  }}
                >
                  {message}
                </div>
              )}

              {!catalog && (
                <div
                  style={{
                    padding: "50px 20px",
                    textAlign: "center",
                    color: "#94a3b8",
                    border: "1px dashed #334155",
                    borderRadius: "14px",
                  }}
                >
                  No catalog loaded yet. Click "Load Published Catalog" to
                  retrieve the public catalog.
                </div>
              )}

              {catalog &&
                Object.entries(catalog.sections || {}).map(
                  ([sectionName, shows]) => (
                    <div key={sectionName} style={{ marginBottom: "30px" }}>
                      <h3
                        style={{
                          marginBottom: "16px",
                          color: "#e2e8f0",
                        }}
                      >
                        {sectionName}
                      </h3>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns:
                            "repeat(auto-fit, minmax(250px, 1fr))",
                          gap: "18px",
                        }}
                      >
                        {shows.map((show) => (
                          <article
                            key={show.id}
                            style={{
                              padding: "20px",
                              borderRadius: "16px",
                              background:
                                "linear-gradient(145deg, #172554, #0f172a)",
                              border:
                                "1px solid rgba(56, 189, 248, 0.18)",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                gap: "12px",
                                alignItems: "flex-start",
                              }}
                            >
                              <h3
                                style={{
                                  margin: 0,
                                  fontSize: "20px",
                                  lineHeight: 1.3,
                                }}
                              >
                                {show.title}
                              </h3>

                              <span
                                style={{
                                  whiteSpace: "nowrap",
                                  padding: "5px 9px",
                                  borderRadius: "999px",
                                  background: "rgba(56, 189, 248, 0.12)",
                                  color: "#7dd3fc",
                                  fontSize: "12px",
                                  fontWeight: 700,
                                }}
                              >
                                {show.category || "Uncategorized"}
                              </span>
                            </div>

                            <p
                              style={{
                                color: "#94a3b8",
                                lineHeight: 1.6,
                                minHeight: "52px",
                              }}
                            >
                              {show.synopsis || "No synopsis available."}
                            </p>

                            <div
                              style={{
                                display: "flex",
                                gap: "16px",
                                paddingTop: "12px",
                                borderTop: "1px solid #1e293b",
                                color: "#64748b",
                                fontSize: "13px",
                              }}
                            >
                              <span>
                                {show.seasons?.length || 0} Seasons
                              </span>

                              <span>
                                {show.trailers?.length || 0} Trailers
                              </span>
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                  )
                )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div
      style={{
        padding: "22px",
        borderRadius: "16px",
        background: "rgba(15, 23, 42, 0.82)",
        border: `1px solid ${accent}33`,
      }}
    >
      <p
        style={{
          margin: 0,
          color: "#94a3b8",
          fontSize: "14px",
        }}
      >
        {label}
      </p>

      <p
        style={{
          margin: "10px 0 0",
          fontSize: "28px",
          fontWeight: 800,
          color: accent,
        }}
      >
        {value}
      </p>
    </div>
  );
}
