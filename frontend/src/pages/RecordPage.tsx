import React, { useEffect, useState } from "react";
import dayjs from "dayjs";
import { getArchived, getCompleted, getPdfUrl, reactivateItem, WorkflowItem } from "../api";
import { MedicareBadge, StatusBadge } from "../components/Badge";
import { useAuth } from "../AuthContext";

type Tab = "completed" | "archived";

export const RecordPage: React.FC = () => {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("completed");
  const [items, setItems] = useState<WorkflowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<WorkflowItem | null>(null);
  const [reactivateReason, setReactivateReason] = useState("");
  const [reactivating, setReactivating] = useState(false);
  const [error, setError] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);

  const load = (t: Tab = tab) => {
    setLoading(true);
    setSelected(null);
    const fn = t === "archived" ? getArchived : getCompleted;
    fn()
      .then(setItems)
      .catch(() => setError("Failed to load records."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(tab); }, [tab]); // eslint-disable-line

  const openPdf = async (item: WorkflowItem) => {
    setPdfLoading(true);
    try {
      const url = await getPdfUrl(item.id);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      setError("Could not retrieve PDF.");
    } finally {
      setPdfLoading(false);
    }
  };

  const handleReactivate = async () => {
    if (!selected || !reactivateReason.trim()) return;
    setReactivating(true);
    try {
      await reactivateItem(selected.id, reactivateReason.trim());
      setSelected(null);
      setReactivateReason("");
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Reactivation failed.");
    } finally {
      setReactivating(false);
    }
  };

  return (
    <div>
      <h2 style={{ color: "#1e3a5f", marginBottom: 4 }}>Record</h2>
      <p style={{ color: "#64748b", marginBottom: 20 }}>
        View completed and archived workqueue items.
      </p>

      <div style={{ display: "flex", gap: 0, marginBottom: 24, border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden", width: "fit-content" }}>
        {(["completed", "archived"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 24px",
              border: "none",
              background: tab === t ? "#1e3a5f" : "#fff",
              color: tab === t ? "#fff" : "#475569",
              fontWeight: 600,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ color: "#dc2626", marginBottom: 16, padding: "8px 12px", background: "#fef2f2", borderRadius: 6 }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: "#94a3b8" }}>Loading…</p>
      ) : items.length === 0 ? (
        <p style={{ color: "#94a3b8", textAlign: "center", padding: "48px 0" }}>No records found.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelected(selected?.id === item.id ? null : item)}
              style={{
                background: "#fff",
                border: selected?.id === item.id ? "2px solid #1e3a5f" : "1px solid #e2e8f0",
                borderRadius: 10,
                padding: "14px 20px",
                cursor: "pointer",
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <span style={{ fontWeight: 600, color: "#1e293b" }}>Study {item.study_id}</span>
                  {item.role1_data && (
                    <span style={{ color: "#475569", fontSize: 13, marginLeft: 12 }}>
                      {item.role1_data.patient_last_name}, {item.role1_data.patient_first_name}
                      {" · "} MRN {item.role1_data.mrn}
                    </span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {item.role1_data?.medicare && <MedicareBadge />}
                  <StatusBadge status={item.status} />
                </div>
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                Completed {item.role2_data?.confirmed_at
                  ? dayjs(item.role2_data.confirmed_at).format("MMM D, YYYY h:mm A")
                  : "—"}
                {item.role1_data?.medicare && (
                  <>{" · "}Clinical Note Exp: {item.role1_data.clinical_note_expiration}</>
                )}
              </div>

              {/* Expanded detail */}
              {selected?.id === item.id && item.role1_data && (
                <div
                  style={{
                    marginTop: 16,
                    paddingTop: 16,
                    borderTop: "1px solid #e2e8f0",
                    fontSize: 14,
                    color: "#334155",
                    lineHeight: 1.8,
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 24px", marginBottom: 12 }}>
                    <div><strong>DOB:</strong> {item.role1_data.date_of_birth}</div>
                    <div><strong>MRN:</strong> {item.role1_data.mrn}</div>
                    <div><strong>Uploaded by:</strong> {item.role1_data.completed_by}</div>
                    <div><strong>Upload date:</strong> {item.role1_data.completed_at ? dayjs(item.role1_data.completed_at).format("MMM D, YYYY") : "—"}</div>
                    {item.role1_data.comments && (
                      <div style={{ gridColumn: "span 2" }}><strong>Notes:</strong> {item.role1_data.comments}</div>
                    )}
                    {item.role2_data && (
                      <div style={{ gridColumn: "span 2" }}>
                        <strong>Follow-up note:</strong> {item.role2_data.followup_note}
                      </div>
                    )}
                    {item.role2_data?.confirmed_by && (
                      <div><strong>Confirmed by:</strong> {item.role2_data.confirmed_by}</div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    {item.role1_data.pdf_gcs_path && (
                      <button
                        onClick={() => openPdf(item)}
                        disabled={pdfLoading}
                        style={outlineBtn}
                      >
                        📄 View PDF
                      </button>
                    )}
                    {user?.role === "admin" && (
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <input
                          value={reactivateReason}
                          onChange={(e) => setReactivateReason(e.target.value)}
                          placeholder="Reason for reactivation…"
                          style={{ padding: "6px 10px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 13, width: 240 }}
                        />
                        <button
                          onClick={handleReactivate}
                          disabled={reactivating || !reactivateReason.trim()}
                          style={{
                            ...outlineBtn,
                            color: "#dc2626",
                            borderColor: "#dc2626",
                            opacity: reactivating || !reactivateReason.trim() ? 0.5 : 1,
                          }}
                        >
                          {reactivating ? "Moving…" : "Mark Incomplete"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const outlineBtn: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #1e3a5f",
  color: "#1e3a5f",
  borderRadius: 6,
  padding: "6px 14px",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 500,
};
