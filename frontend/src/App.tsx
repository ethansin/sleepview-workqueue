import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import { Layout } from "./components/Layout";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { FollowupQueuePage } from "./pages/FollowupQueuePage";
import { LoginPage } from "./pages/LoginPage";
import { RecordPage } from "./pages/RecordPage";
import { UploadQueuePage } from "./pages/UploadQueuePage";

const DefaultRedirect: React.FC = () => {
  const { user } = useAuth();
  if (user?.role === "reviewer") return <Navigate to="/followup-queue" replace />;
  return <Navigate to="/upload-queue" replace />;
};

const ProtectedRoutes: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", color: "#94a3b8", fontFamily: "Inter, sans-serif" }}>
        Loading…
      </div>
    );
  }

  if (!user) return <LoginPage />;

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DefaultRedirect />} />
        <Route path="/upload-queue" element={<UploadQueuePage />} />
        <Route path="/followup-queue" element={<FollowupQueuePage />} />
        <Route path="/record" element={<RecordPage />} />
        <Route path="/admin/users" element={<AdminUsersPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ProtectedRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
