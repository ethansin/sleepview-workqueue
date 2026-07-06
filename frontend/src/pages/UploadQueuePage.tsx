import React, { useEffect, useRef, useState } from "react";
import dayjs from "dayjs";
import { getUploadQueue, submitUpload, WorkflowItem } from "../api";
import { StatusBadge } from "../components/Badge";

export const UploadQueuePage: React.FC = () => {
  const [items, setItems] = useState<WorkflowItem[]>([]);
  const [selected, setSelected] = useState<WorkflowItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const lastNameRef = useRef<HTMLInputElement>(null);
  const firstNameRef = useRef<HTMLInputElement>(null);
  const dobRef = useRef<HTMLInputElement>(null);
  const mrnRef = useRef<HTMLInputElement>(null);
  const commentsRef = useRef<HTMLTextAreaElement>(null);
  const pdfRef = useRef<HTMLInputElement>(null);

  const load = () => {
    setLoading(true);
    getUploadQueue()
      .then(setItems)
      .catch(() => setError("Failed to load queue."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCopyStudyId = async () => {
    if (!selected) return;
    await navigator.clipboard.writeText(selected.study_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !pdfRef.current?.files?.[0]) return;
    const file = pdfRef.current.files[0];
    const form = new FormData();
    form.append("patient_last_name", lastNameRef.current!.value.trim());
    form.append("patient_first_name", firstNameRef.current!.value.trim());
    form.append("date_of_birth", dobRef.current!.value);
    form.append("mrn", mrnRef.current!.value.trim());
    form.append("comments", commentsRef.current!.value.trim());
    form.append("pdf", file);

    setSubmitting(true);
    setError("");
    try {
      await submitUpload(selected.id, form);
      setSelected(null);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h2 style={{ color: "#1e3a5f", marginBottom: 4 }}>Upload Queue</h2>
      <p style={{ color: "#64748b", marginBottom: 24 }}>
        {items.length} item{items.length !== 1 ? "s" : ""} awaiting report upload
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
            <React.Fragment key={item.id}>
              <div
                onClick={() => setSelected(item)}
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
                    Study ID: {item.study_id}
                  </div>
                  <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                    Received {dayjs(item.created_at).format("MMM D, YYYY h:mm A")}
                  </div>
                </div>
                <StatusBadge status={item.status} />
              </div>

              {selected?.id === item.id && (
                <div
                  className="inline-form-panel"
                  style={{
                    background: "#fff",
                    border: "1px solid #e2e8f0",
                    borderRadius: 12,
                    padding: "28px 32px",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                    <h3 style={{ color: "#1e3a5f", margin: 0 }}>
                      Complete Upload — Study {selected.study_id}
                    </h3>
                    <button
                      type="button"
                      onClick={handleCopyStudyId}
                      title="Copy Study ID"
                      style={{
                        background: "transparent",
                        border: "1px solid #cbd5e1",
                        borderRadius: 6,
                        padding: "2px 10px",
                        cursor: "pointer",
                        color: "#475569",
                        fontSize: 12,
                      }}
                    >
                      {copied ? "Copied!" : "Copy ID"}
                    </button>
                  </div>
                  <p style={{ color: "#64748b", fontSize: 14, marginBottom: 24 }}>
                    Fill in all fields and attach the signed PDF report.
                  </p>
                  <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                      <Field label="Last Name" required>
                        <input ref={lastNameRef} required style={inputStyle} />
                      </Field>
                      <Field label="First Name" required>
                        <input ref={firstNameRef} required style={inputStyle} />
                      </Field>
                      <Field label="Date of Birth" required>
                        <input ref={dobRef} type="date" required style={inputStyle} />
                      </Field>
                      <Field label="MRN" required>
                        <input ref={mrnRef} required style={inputStyle} />
                      </Field>
                    </div>
                    <Field label="Comments">
                      <textarea ref={commentsRef} rows={3} style={{ ...inputStyle, resize: "vertical" }} />
                    </Field>
                    <Field label="PDF Report" required>
                      <input ref={pdfRef} type="file" accept="application/pdf" required style={inputStyle} />
                    </Field>

                    <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
                      <button
                        type="submit"
                        disabled={submitting}
                        style={{
                          background: "#1e3a5f",
                          color: "#fff",
                          border: "none",
                          borderRadius: 8,
                          padding: "10px 28px",
                          fontWeight: 600,
                          fontSize: 14,
                          cursor: submitting ? "not-allowed" : "pointer",
                          opacity: submitting ? 0.7 : 1,
                        }}
                      >
                        {submitting ? "Submitting…" : "Submit & Send to Follow-up Queue"}
                      </button>
                      <button
                        type="button"
                        onClick={() => { setSelected(null); setError(""); setCopied(false); }}
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
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  border: "1px solid #cbd5e1",
  borderRadius: 6,
  fontSize: 14,
  boxSizing: "border-box",
  fontFamily: "inherit",
};

const Field: React.FC<{ label: string; required?: boolean; children: React.ReactNode }> = ({
  label, required, children,
}) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ fontSize: 12, fontWeight: 600, color: "#475569", textTransform: "uppercase", letterSpacing: 0.5 }}>
      {label}{required && <span style={{ color: "#dc2626" }}> *</span>}
    </label>
    {children}
  </div>
);
