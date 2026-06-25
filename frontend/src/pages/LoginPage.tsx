import React from "react";

const API = process.env.REACT_APP_API_URL || "http://localhost:8080";

export const LoginPage: React.FC = () => (
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
        padding: "48px 56px",
        textAlign: "center",
        maxWidth: 380,
        width: "100%",
      }}
    >
      <h1
        style={{
          color: "#1e3a5f",
          fontSize: 24,
          fontWeight: 700,
          marginBottom: 8,
        }}
      >
        SleepView Workqueue
      </h1>
      <p style={{ color: "#64748b", fontSize: 14, marginBottom: 32 }}>
        Sign in with your Westlake Sleep account to continue.
      </p>
      <a
        href={`${API}/auth/login`}
        style={{
          display: "inline-block",
          background: "#1e3a5f",
          color: "#fff",
          padding: "12px 28px",
          borderRadius: 8,
          textDecoration: "none",
          fontWeight: 600,
          fontSize: 15,
          letterSpacing: 0.2,
        }}
      >
        Sign in with Google
      </a>
    </div>
  </div>
);
