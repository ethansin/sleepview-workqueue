import React, { useEffect, useState } from "react";
import dayjs from "dayjs";
import { confirmFollowup, getFollowupQueue, getPdfUrl, WorkflowItem } from "../api";
import { StatusBadge } from "../components/Badge";

export const FollowupQueuePage: React.FC = () => {
  const [items, setItems] = useState<WorkflowItem[]>([]);
  const [selected, setSelected] = useState<WorkflowItem | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);

  const load = () => {
    setLoading(true);
    getFollowupQueue()
      .then(setItems)
      .catch(() => setError("Failed to load queue."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSelect = (item: WorkflowItem) => {
    setSelected(item);
    setNote("");
    setError("");
  };

  const openPdf = async () => {
    if (!selected) return;
    setPdfLoading(true);
    try {
      const url = await getPdfUrl(selected.id);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      setError("Could not retrieve PDF.");
    } finally {
      setPdfLoading(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !note.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await confirmFollowup(selected.id, note.trim());
      setSelected(null);
      setNote("");
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h2 style={{ color: "#1e3a5f", marginBottom: 4 }}>Follow-up Queue</h2>
      <p style={{ color: "#64748b", marginBottom: 24 }}>
        {items.length} item{items.length !== 1 ? "s" : ""} awaiting follow-up confirmation
      </p>

      {error && (
        <div style={{ color: "#dc2626", marginBottom: 16, padding: "8px 12px", background: "#fef2f2", borderRadius: 6 }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ color: "#94a3b8" }}>Loading…</p>
      ) : items.length === 0 ? (
        <div style={{ textAlign: "center", color: "#94a3b8", padding: "64px 0" }}>
          <div style={{ fontSize: 48 }}>✓</div>
          <p>Your queue is empty. All caught up!</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => handleSelect(item)}
              style={{
                background: "#fff",
                border: selected?.id === item.id ? "2px solid #1e3a5f" : "1px solid #e2e8f0",
                borderRadius: 10,
                padding: "16px 20px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
              }}
            >
              <div>
                <div style={{ fontWeight: 600, color: "#1e293b", fontSize: 16 }}>
                  {item.role1_data
                    ? `${item.role1_data.patient_last_name}, ${item.role1_data.patient_first_name}`
                    : "Unknown Patient"}
                </div>
                {item.role1_data && (
                  <div style={{ fontSize: 13, color: "#475569", marginTop: 4 }}>
                    Study ID: {item.study_id}
                    {" · "}DOB: {item.role1_data.date_of_birth}
                    {" · "}MRN: {item.role1_data.mrn}
                  </div>
                )}
                <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                  Upload completed {item.role1_data?.completed_at
                    ? dayjs(item.role1_data.completed_at).format("MMM D, YYYY h:mm A")
                    : "—"}
                </div>
              </div>
              <StatusBadge status={item.status} />
            </div>
          ))}
        </div>
      )}

      {selected && selected.role1_data && (
        <div
          style={{
            marginTop: 32,
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 12,
            padding: "28px 32px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          }}
        >
          <h3 style={{ color: "#1e3a5f", marginBottom: 16 }}>
            Confirm Follow-up — Study {selected.study_id}
          </h3>

          {/* Patient info summary */}
          <div
            style={{
              background: "#f1f5f9",
              borderRadius: 8,
              padding: "14px 18px",
              marginBottom: 20,
              fontSize: 14,
              lineHeight: 1.8,
              color: "#334155",
            }}
          >
            <strong>Patient:</strong> {selected.role1_data.patient_last_name},{" "}
            {selected.role1_data.patient_first_name}
            <br />
            <strong>DOB:</strong> {selected.role1_data.date_of_birth}
            {"  ·  "}
            <strong>MRN:</strong> {selected.role1_data.mrn}
            {selected.role1_data.comments && (
              <>
                <br />
                <strong>Notes:</strong> {selected.role1_data.comments}
              </>
            )}
          </div>

          <button
            onClick={openPdf}
            disabled={pdfLoading}
            style={{
              background: "#fff",
              border: "1px solid #1e3a5f",
              color: "#1e3a5f",
              borderRadius: 8,
              padding: "8px 20px",
              fontWeight: 600,
              fontSize: 14,
              cursor: pdfLoading ? "not-allowed" : "pointer",
              marginBottom: 24,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            {pdfLoading ? "Opening…" : "📄 View PDF Report"}
          </button>

          <form onSubmit={handleConfirm}>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "#475569",
                textTransform: "uppercase",
                letterSpacing: 0.5,
                marginBottom: 6,
              }}
            >
              Follow-up Note <span style={{ color: "#dc2626" }}>*</span>
            </label>
            <p style={{ fontSize: 13, color: "#64748b", marginBottom: 8 }}>
              Briefly describe what follow-up action was taken.
            </p>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
              required
              placeholder="e.g., Sent CPAP prescription to Sincere. Faxed report to Dr. Johnson at 555-0100."
              style={{
                width: "100%",
                padding: "8px 10px",
                border: "1px solid #cbd5e1",
                borderRadius: 6,
                fontSize: 14,
                boxSizing: "border-box",
                fontFamily: "inherit",
                resize: "vertical",
                marginBottom: 16,
              }}
            />

            <div style={{ display: "flex", gap: 12 }}>
              <button
                type="submit"
                disabled={submitting || !note.trim()}
                style={{
                  background: "#10b981",
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  padding: "10px 28px",
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: submitting || !note.trim() ? "not-allowed" : "pointer",
                  opacity: submitting || !note.trim() ? 0.7 : 1,
                }}
              >
                {submitting ? "Confirming…" : "Confirm Follow-up Complete"}
              </button>
              <button
                type="button"
                onClick={() => { setSelected(null); setError(""); }}
                style={{
                  background: "transparent",
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  padding: "10px 20px",
                  cursor: "pointer",
                  color: "#475569",
                  fontSize: 14,
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
