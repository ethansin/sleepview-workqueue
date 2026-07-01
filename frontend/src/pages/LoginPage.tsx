import React, { useState } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";

const API = process.env.REACT_APP_API_URL || "http://localhost:8080";

type Tab = "google" | "password" | "register";

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: 6,
  border: "1px solid #cbd5e1",
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
};

const btnStyle: React.CSSProperties = {
  width: "100%",
  background: "#1e3a5f",
  color: "#fff",
  padding: "11px 0",
  borderRadius: 8,
  border: "none",
  fontWeight: 600,
  fontSize: 15,
  cursor: "pointer",
  letterSpacing: 0.2,
};

export const LoginPage: React.FC = () => {
  const [tab, setTab] = useState<Tab>("google");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const { refetch } = useAuth();

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/login/password", { email, password });
      await refetch();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/register", { name, email, password });
      setSuccess("Your request has been submitted. An admin will review it shortly.");
      setName("");
      setEmail("");
      setPassword("");
    } catch (err: any) {
      setError(err.response?.data?.detail || (err.request ? "Could not reach the server. Is the backend running?" : "Registration failed. Please try again."));
    } finally {
      setLoading(false);
    }
  };

  const tabStyle = (active: boolean): React.CSSProperties => ({
    flex: 1,
    padding: "8px 0",
    background: "none",
    border: "none",
    borderBottom: active ? "2px solid #1e3a5f" : "2px solid transparent",
    color: active ? "#1e3a5f" : "#64748b",
    fontWeight: active ? 600 : 400,
    fontSize: 13,
    cursor: "pointer",
  });

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#f8fafc",
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 12,
          boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
          padding: "40px 48px",
          maxWidth: 380,
          width: "100%",
        }}
      >
        <h1 style={{ color: "#1e3a5f", fontSize: 22, fontWeight: 700, marginBottom: 4, textAlign: "center" }}>
          SleepView Workqueue
        </h1>
        <p style={{ color: "#64748b", fontSize: 13, marginBottom: 24, textAlign: "center" }}>
          Westlake Sleep internal portal
        </p>

        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid #e2e8f0", marginBottom: 24 }}>
          <button style={tabStyle(tab === "google")} onClick={() => { setTab("google"); setError(""); setSuccess(""); }}>
            Google
          </button>
          <button style={tabStyle(tab === "password")} onClick={() => { setTab("password"); setError(""); setSuccess(""); }}>
            Email
          </button>
          <button style={tabStyle(tab === "register")} onClick={() => { setTab("register"); setError(""); setSuccess(""); }}>
            Request Access
          </button>
        </div>

        {/* Google tab */}
        {tab === "google" && (
          <div style={{ textAlign: "center" }}>
            <p style={{ color: "#64748b", fontSize: 13, marginBottom: 20 }}>
              Sign in with your Westlake Sleep Google Workspace account.
            </p>
            <a
              href={`${API}/auth/login`}
              style={{ ...btnStyle, display: "inline-block", textDecoration: "none", textAlign: "center" }}
            >
              Sign in with Google
            </a>
          </div>
        )}

        {/* Password login tab */}
        {tab === "password" && (
          <form onSubmit={handlePasswordLogin} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ fontSize: 13, color: "#475569", display: "block", marginBottom: 4 }}>Email</label>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, color: "#475569", display: "block", marginBottom: 4 }}>Password</label>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
              />
            </div>
            {error && <p style={{ color: "#dc2626", fontSize: 13, margin: 0 }}>{error}</p>}
            <button type="submit" style={btnStyle} disabled={loading}>
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        )}

        {/* Register tab */}
        {tab === "register" && (
          <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {success ? (
              <p style={{ color: "#16a34a", fontSize: 14, textAlign: "center", lineHeight: 1.5 }}>{success}</p>
            ) : (
              <>
                <div>
                  <label style={{ fontSize: 13, color: "#475569", display: "block", marginBottom: 4 }}>Full name</label>
                  <input
                    type="text"
                    required
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 13, color: "#475569", display: "block", marginBottom: 4 }}>Email</label>
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 13, color: "#475569", display: "block", marginBottom: 4 }}>Password</label>
                  <input
                    type="password"
                    required
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    style={inputStyle}
                  />
                  <p style={{ fontSize: 12, color: "#94a3b8", margin: "4px 0 0" }}>Minimum 8 characters.</p>
                </div>
                {error && <p style={{ color: "#dc2626", fontSize: 13, margin: 0 }}>{error}</p>}
                <button type="submit" style={btnStyle} disabled={loading}>
                  {loading ? "Submitting…" : "Request Account"}
                </button>
                <p style={{ fontSize: 12, color: "#94a3b8", textAlign: "center", margin: 0 }}>
                  An admin will review and approve your request before you can sign in.
                </p>
              </>
            )}
          </form>
        )}
      </div>
    </div>
  );
};
