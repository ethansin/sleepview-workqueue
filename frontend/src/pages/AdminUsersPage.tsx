import React, { useEffect, useState } from "react";
import { api } from "../api";

interface PendingUser {
  email: string;
  name: string;
  requested_at: string;
}

type Role = "uploader" | "reviewer" | "admin";

export const AdminUsersPage: React.FC = () => {
  const [users, setUsers] = useState<PendingUser[]>([]);
  const [roleSelections, setRoleSelections] = useState<Record<string, Role>>({});
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<Record<string, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get("/admin/pending-users");
      setUsers(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleApprove = async (email: string) => {
    const role = roleSelections[email] || "uploader";
    try {
      await api.post(`/admin/approve-user/${encodeURIComponent(email)}`, { role });
      setActionMsg((m) => ({ ...m, [email]: `Approved as ${role}.` }));
      setUsers((u) => u.filter((x) => x.email !== email));
    } catch (err: any) {
      setActionMsg((m) => ({ ...m, [email]: err.response?.data?.detail || "Error approving user." }));
    }
  };

  const handleReject = async (email: string) => {
    if (!window.confirm(`Reject account request from ${email}?`)) return;
    try {
      await api.post(`/admin/reject-user/${encodeURIComponent(email)}`);
      setActionMsg((m) => ({ ...m, [email]: "Rejected." }));
      setUsers((u) => u.filter((x) => x.email !== email));
    } catch (err: any) {
      setActionMsg((m) => ({ ...m, [email]: err.response?.data?.detail || "Error rejecting user." }));
    }
  };

  return (
    <div>
      <h2 style={{ color: "#1e3a5f", fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Pending Account Requests</h2>
      <p style={{ color: "#64748b", fontSize: 13, marginBottom: 24 }}>
        Review and approve or reject account requests from non-Google users.
      </p>

      {loading && <p style={{ color: "#94a3b8" }}>Loading…</p>}

      {!loading && users.length === 0 && (
        <p style={{ color: "#64748b", fontSize: 14 }}>No pending requests.</p>
      )}

      {!loading && users.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Email</th>
              <th style={thStyle}>Requested</th>
              <th style={thStyle}>Role</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.email} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={tdStyle}>{u.name}</td>
                <td style={tdStyle}>{u.email}</td>
                <td style={tdStyle}>{new Date(u.requested_at).toLocaleDateString()}</td>
                <td style={tdStyle}>
                  <select
                    value={roleSelections[u.email] || "uploader"}
                    onChange={(e) =>
                      setRoleSelections((r) => ({ ...r, [u.email]: e.target.value as Role }))
                    }
                    style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #cbd5e1", fontSize: 13 }}
                  >
                    <option value="uploader">Uploader</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td style={{ ...tdStyle, display: "flex", gap: 8, alignItems: "center" }}>
                  <button onClick={() => handleApprove(u.email)} style={approveBtnStyle}>
                    Approve
                  </button>
                  <button onClick={() => handleReject(u.email)} style={rejectBtnStyle}>
                    Reject
                  </button>
                  {actionMsg[u.email] && (
                    <span style={{ fontSize: 12, color: "#64748b" }}>{actionMsg[u.email]}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  color: "#475569",
  fontWeight: 600,
  fontSize: 13,
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px",
  color: "#1e293b",
  verticalAlign: "middle",
};

const approveBtnStyle: React.CSSProperties = {
  background: "#1e3a5f",
  color: "#fff",
  border: "none",
  borderRadius: 6,
  padding: "5px 14px",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};

const rejectBtnStyle: React.CSSProperties = {
  background: "none",
  color: "#dc2626",
  border: "1px solid #fca5a5",
  borderRadius: 6,
  padding: "5px 14px",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};
