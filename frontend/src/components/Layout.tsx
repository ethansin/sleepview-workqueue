import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { api } from "../api";

const NAV: Record<string, { label: string; path: string; roles: string[] }[]> =
  {
    uploader: [
      { label: "My Queue", path: "/upload-queue", roles: ["uploader", "admin"] },
      { label: "Record", path: "/record", roles: ["uploader", "admin", "reviewer"] },
    ],
    reviewer: [
      { label: "My Queue", path: "/followup-queue", roles: ["reviewer", "admin"] },
      { label: "Record", path: "/record", roles: ["uploader", "admin", "reviewer"] },
    ],
    admin: [
      { label: "Upload Queue", path: "/upload-queue", roles: ["admin"] },
      { label: "Follow-up Queue", path: "/followup-queue", roles: ["admin"] },
      { label: "Record", path: "/record", roles: ["admin"] },
      { label: "Pending Users", path: "/admin/users", roles: ["admin"] },
      { label: "Gmail Integration", path: "/admin/gmail", roles: ["admin"] },
    ],
  };

export const Layout: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { user } = useAuth();
  const location = useLocation();

  const navItems = user ? (NAV[user.role] ?? []) : [];

  const logout = async () => {
    await api.post("/auth/logout");
    window.location.href = "/";
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "Inter, system-ui, sans-serif" }}>
      <header
        style={{
          background: "#1e3a5f",
          color: "#fff",
          padding: "0 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 56,
          boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: 0.5 }}>
          SleepView Workqueue
        </span>
        <nav style={{ display: "flex", gap: 24, alignItems: "center" }}>
          {navItems.map((n) => (
            <Link
              key={n.path}
              to={n.path}
              style={{
                color: location.pathname === n.path ? "#93c5fd" : "#cbd5e1",
                textDecoration: "none",
                fontWeight: 500,
                fontSize: 14,
                borderBottom:
                  location.pathname === n.path
                    ? "2px solid #93c5fd"
                    : "2px solid transparent",
                paddingBottom: 2,
              }}
            >
              {n.label}
            </Link>
          ))}
          {user && (
            <span style={{ fontSize: 13, color: "#94a3b8", marginLeft: 8 }}>
              {user.name}
            </span>
          )}
          {user && (
            <button
              onClick={logout}
              style={{
                background: "transparent",
                border: "1px solid #475569",
                color: "#cbd5e1",
                borderRadius: 6,
                padding: "4px 12px",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              Sign out
            </button>
          )}
        </nav>
      </header>
      <main style={{ maxWidth: 960, margin: "0 auto", padding: "32px 16px" }}>
        {children}
      </main>
    </div>
  );
};
