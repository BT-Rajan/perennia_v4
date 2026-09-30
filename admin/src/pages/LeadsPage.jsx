import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import LeadDetailPanel from "../components/LeadDetailPanel.jsx";
import LeadCreatePanel from "../components/LeadCreatePanel.jsx";
import "./LeadsPage.css";

const STATUS_OPTIONS = ["", "new", "contacted", "qualified", "converted", "lost"];
const SOURCE_OPTIONS = ["", "chat", "booking"];

export default function LeadsPage() {
  const { handleSessionExpired } = useAuth();
  const navigate = useNavigate();
  const { id: selectedId } = useParams();
  const [leads, setLeads] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    adminApi
      .listLeads({ status_filter: statusFilter, source: sourceFilter })
      .then(setLeads)
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [statusFilter, sourceFilter, handleSessionExpired]);

  useEffect(() => {
    load();
  }, [load]);

  function handleUpdated(updatedLead) {
    setLeads((prev) => prev.map((l) => (l.id === updatedLead.id ? updatedLead : l)));
  }

  function handleCreated(lead) {
    setLeads((prev) => [lead, ...(prev ?? [])]);
    setCreating(false);
    navigate(`/leads/${lead.id}`);
  }

  function handleDeleted() {
    setLeads((prev) => prev.filter((l) => l.id !== selectedId));
    navigate("/leads");
  }

  const selectedLead = leads?.find((l) => l.id === selectedId) ?? null;

  return (
    <div>
      <PageHeader
        title="Leads"
        subtitle="Everyone who's booked a call or left an email in chat."
        actions={
          <button className="row-action primary" onClick={() => { setCreating(true); navigate("/leads"); }}>
            + New lead
          </button>
        }
      />

      <div className="filters-row">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}</option>
          ))}
        </select>
        <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
          {SOURCE_OPTIONS.map((s) => (
            <option key={s} value={s}>{s ? s[0].toUpperCase() + s.slice(1) : "All sources"}</option>
          ))}
        </select>
      </div>

      {error && <div className="page-error">{error}</div>}

      <div className="leads-layout">
        <div className="card leads-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Contact</th>
                <th>Source</th>
                <th>Status</th>
                <th>Captured</th>
              </tr>
            </thead>
            <tbody>
              {leads === null && (
                <tr><td colSpan={4} className="table-empty">Loading…</td></tr>
              )}
              {leads?.length === 0 && (
                <tr><td colSpan={4} className="table-empty">No leads match these filters.</td></tr>
              )}
              {leads?.map((l) => (
                <tr
                  key={l.id}
                  className={selectedId === l.id ? "row-selected" : ""}
                  onClick={() => { setCreating(false); navigate(`/leads/${l.id}`); }}
                  style={{ cursor: "pointer" }}
                >
                  <td>
                    <div>{l.name || <span className="table-subtext">No name</span>}</div>
                    <div className="table-subtext">{l.email}</div>
                  </td>
                  <td>{l.source}</td>
                  <td><span className={`status-pill ${l.status}`}>{l.status}</span></td>
                  <td>{new Date(l.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {creating && (
          <LeadCreatePanel onClose={() => setCreating(false)} onCreated={handleCreated} />
        )}

        {!creating && selectedLead && (
          <LeadDetailPanel
            key={selectedLead.id}
            lead={selectedLead}
            onClose={() => navigate("/leads")}
            onUpdated={handleUpdated}
            onDeleted={handleDeleted}
          />
        )}
      </div>
    </div>
  );
}
