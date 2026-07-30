import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { UsersSection } from "./UsersSection";
import { LabelsSection } from "./LabelsSection";
import { MaintenanceSection } from "./MaintenanceSection";
import "./AdminPage.css";

const TABS = [
  { id: "users", label: "Пользователи" },
  { id: "labels", label: "Метки" },
  { id: "maintenance", label: "Обслуживание" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function AdminPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("users");

  if (user?.role !== "ADMIN") return <Navigate to="/" replace />;

  return (
    <div className="admin-page">
      <h1 className="admin-page__title">Администрирование</h1>

      <div className="admin-page__tabs" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`admin-page__tab${activeTab === tab.id ? " admin-page__tab--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "users" && <UsersSection currentUserId={user.id} />}
      {activeTab === "labels" && <LabelsSection />}
      {activeTab === "maintenance" && <MaintenanceSection />}
    </div>
  );
}
