import React, { useEffect, useState } from "react";
import {
  checkGmailNow,
  disconnectGmail,
  getGmailStatus,
  gmailConnectUrl,
  GmailStatus,
  updateGmailSettings,
} from "../api";

export const AdminGmailSettingsPage: React.FC = () => {
  const [status, setStatus] = useState<GmailStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [interval, setInterval] = useState(30);
  const [lookback, setLookback] = useState(7);
  const [message, setMessage] = useState("");
  const [checking, setChecking] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getGmailStatus();
      setStatus(res);
      setInterval(res.check_interval_minutes);
      setLookback(res.lookback_days);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    if (params.get("error") === "connect_failed") {
      setMessage("Connecting Gmail failed. Please try again.");
      params.delete("error");
      const query = params.toString();
      window.history.replaceState({}, "", window.location.pathname + (query ? `?${query}` : ""));
    }
  }, []);

  const handleSaveSettings = async () => {
    try {
      const res = await updateGmailSettings(interval, lookback);
      setStatus(res);
      setMessage("Settings saved.");
    } catch (err: any) {
      setMessage(err.response?.data?.detail || "Error saving settings.");
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm("Disconnect the Gmail inbox? Automatic study ID ingestion will stop.")) return;
    try {
      await disconnectGmail();
      await load();
      setMessage("Gmail inbox disconnected.");
    } catch (err: any) {
      setMessage(err.response?.data?.detail || "Error disconnecting.");
    }
  };

  const handleCheckNow = async () => {
    setChecking(true);
    try {
      const res = await checkGmailNow();
      if (res.status === "ok") {
        setMessage(`Check complete: ${res.created} new, ${res.skipped} already queued.`);
      } else {
        setMessage(`Check finished with status: ${res.status}`);
      }
      await load();
    } catch (err: any) {
      setMessage(err.response?.data?.detail || "Error checking inbox.");
    } finally {
      setChecking(false);
    }
  };

  if (loading) return <p style={{ color: "#94a3b8" }}>Loading…</p>;
  if (!status) return null;

  return (
    <div>
      <h2 style={{ color: "#1e3a5f", fontSize: 20, fontWeight: 700, marginBottom: 4 }}>
        Gmail Integration
      </h2>
      <p style={{ color: "#64748b", fontSize: 13, marginBottom: 24 }}>
        Automatically create upload queue items from "SleepView HST report is ready"
        notification emails delivered to a connected inbox.
      </p>

      <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 20, marginBottom: 20 }}>
        {status.connected ? (
          <>
            <p style={{ margin: 0, fontSize: 14, color: "#1e293b" }}>
              Connected as <strong>{status.connected_email}</strong>
            </p>
            <p style={{ margin: "8px 0 0", fontSize: 13, color: "#64748b" }}>
              Last checked:{" "}
              {status.last_checked_at ? new Date(status.last_checked_at).toLocaleString() : "never"}
              {status.last_run_summary ? ` — ${status.last_run_summary}` : ""}
              {status.last_run_status === "error" && status.last_run_error
                ? ` — error: ${status.last_run_error}`
                : ""}
            </p>
            <button onClick={handleDisconnect} style={rejectBtnStyle}>
              Disconnect
            </button>
          </>
        ) : (
          <>
            <p style={{ margin: 0, fontSize: 14, color: "#1e293b" }}>Not connected.</p>
            <p style={{ margin: "8px 0 12px", fontSize: 13, color: "#64748b" }}>
              Before connecting, sign into the shared notifications mailbox (e.g.
              notifications@westlakesleep.com) in this browser — or use an incognito window —
              since the account you're signed into when you click Connect is the one that gets
              monitored.
            </p>
            <a href={gmailConnectUrl()}>
              <button style={approveBtnStyle}>Connect Gmail</button>
            </a>
          </>
        )}
      </div>

      <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 20, marginBottom: 20 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1e3a5f", marginTop: 0 }}>Polling settings</h3>
        <label style={{ display: "block", fontSize: 13, color: "#475569", marginBottom: 4 }}>
          Check interval (minutes)
        </label>
        <input
          type="number"
          min={1}
          max={1440}
          value={interval}
          onChange={(e) => setInterval(Number(e.target.value))}
          style={inputStyle}
        />
        <label style={{ display: "block", fontSize: 13, color: "#475569", margin: "12px 0 4px" }}>
          Look-back window (days)
        </label>
        <input
          type="number"
          min={1}
          max={30}
          value={lookback}
          onChange={(e) => setLookback(Number(e.target.value))}
          style={inputStyle}
        />
        <div style={{ marginTop: 16 }}>
          <button onClick={handleSaveSettings} style={approveBtnStyle}>
            Save
          </button>
          {status.connected && (
            <button onClick={handleCheckNow} disabled={checking} style={{ ...approveBtnStyle, marginLeft: 8, background: "#475569" }}>
              {checking ? "Checking…" : "Check now"}
            </button>
          )}
        </div>
      </div>

      {message && <p style={{ fontSize: 13, color: "#64748b" }}>{message}</p>}
    </div>
  );
};

const inputStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: 6,
  border: "1px solid #cbd5e1",
  fontSize: 14,
  width: 120,
};

const approveBtnStyle: React.CSSProperties = {
  background: "#1e3a5f",
  color: "#fff",
  border: "none",
  borderRadius: 6,
  padding: "6px 16px",
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
  marginTop: 12,
};
