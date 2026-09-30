import { useState } from "react";
import GlassPanel from "../ui/GlassPanel.jsx";
import NewAppointmentForm from "./NewAppointmentForm.jsx";
import ManageBooking from "./ManageBooking.jsx";
import { useLang } from "../../context/LangContext.jsx";
import "./BookingPanel.css";

export default function BookingPanel({ onClose, onResult }) {
  const { copy } = useLang();
  const t = copy.booking;
  const [tab, setTab] = useState("new");

  return (
    <GlassPanel className="booking-panel" as="div" role="dialog" aria-modal="true">
      <button className="booking-close" onClick={onClose} aria-label={copy.common.close}>✕</button>
      <div className="booking-badge" aria-hidden="true">📅</div>
      <h3>{t.title}</h3>
      <p className="booking-sub">{t.subtitle}</p>
      <div className="booking-head-divider" />

      <div className="bk-tabs" role="tablist">
        <button className={`bk-tab${tab === "new" ? " active" : ""}`} onClick={() => setTab("new")} role="tab">
          {t.tabNew}
        </button>
        <button className={`bk-tab${tab === "manage" ? " active" : ""}`} onClick={() => setTab("manage")} role="tab">
          {t.tabManage}
        </button>
      </div>

      <div className="booking-body">
        {tab === "new" ? (
          <NewAppointmentForm
            onCancel={onClose}
            onBooked={(appt) => onResult(t.successNew(appt.id))}
          />
        ) : (
          <ManageBooking onDone={onResult} />
        )}
      </div>
    </GlassPanel>
  );
}
