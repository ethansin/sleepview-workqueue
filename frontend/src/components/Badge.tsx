import React from "react";

const colors: Record<string, string> = {
  pending_upload: "#f59e0b",
  pending_followup: "#3b82f6",
  completed: "#10b981",
  archived: "#6b7280",
};

const labels: Record<string, string> = {
  pending_upload: "Needs Upload",
  pending_followup: "Needs Follow-up",
  completed: "Completed",
  archived: "Archived",
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span
    style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      color: "#fff",
      background: colors[status] ?? "#6b7280",
      letterSpacing: 0.3,
    }}
  >
    {labels[status] ?? status}
  </span>
);
