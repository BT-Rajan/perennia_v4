import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import ServiceDetailPanel from "../components/ServiceDetailPanel.jsx";
import "./ServicesPage.css";

const LOCATION_LABEL = { in_person: "In person", phone: "Phone", link_provided: "Link provided" };

export default function ServicesPage() {
  const { handleSessionExpired } = useAuth();
  const navigate = useNavigate();
  const { id: selectedId } = useParams();
  const [services, setServices] = useState(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    adminApi
      .listServices()
      .then(setServices)
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [handleSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated(service) {
    setServices((prev) => [...(prev ?? []), service]);
    setCreating(false);
    navigate(`/services/${service.id}`);
  }

  function handleUpdated(updated) {
    setServices((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  }

  function handleDeactivated(updated) {
    setServices((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  }

  const selectedService = services?.find((s) => s.id === selectedId) ?? null;

  return (
    <div>
      <PageHeader
        title="Services"
        subtitle="What visitors can book — each service has its own duration, buffer time, and intake questions."
        actions={
          <button className="row-action primary" onClick={() => { setCreating(true); navigate("/services"); }}>
            + New service
          </button>
        }
      />

      {error && <div className="page-error">{error}</div>}

      <div className="services-layout">
        <div className="card services-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Service</th>
                <th>Duration</th>
                <th>Location</th>
                <th>Confirmation</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {services === null && (
                <tr><td colSpan={5} className="table-empty">Loading…</td></tr>
              )}
              {services?.length === 0 && (
                <tr><td colSpan={5} className="table-empty">No services yet — add your first one.</td></tr>
              )}
              {services?.map((s) => (
                <tr
                  key={s.id}
                  className={selectedId === s.id ? "row-selected" : ""}
                  onClick={() => { setCreating(false); navigate(`/services/${s.id}`); }}
                  style={{ cursor: "pointer" }}
                >
                  <td>
                    <div>{s.name}</div>
                    <div className="table-subtext mono-chip-inline">{s.slug}</div>
                  </td>
                  <td>{s.duration_minutes} min</td>
                  <td>{LOCATION_LABEL[s.location_type] ?? s.location_type}</td>
                  <td>{s.requires_confirmation ? <span className="status-pill contacted">requires approval</span> : <span className="table-subtext">auto-confirms</span>}</td>
                  <td><span className={`status-pill ${s.is_active ? "confirmed" : "cancelled"}`}>{s.is_active ? "active" : "inactive"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {creating && (
          <ServiceDetailPanel
            mode="create"
            onClose={() => setCreating(false)}
            onCreated={handleCreated}
          />
        )}

        {!creating && selectedService && (
          <ServiceDetailPanel
            key={selectedService.id}
            mode="edit"
            service={selectedService}
            onClose={() => navigate("/services")}
            onUpdated={handleUpdated}
            onDeactivated={handleDeactivated}
          />
        )}
      </div>
    </div>
  );
}
