import { useState } from "react";
import Field from "./Field.jsx";
import SlotPicker from "./SlotPicker.jsx";
import Button from "../ui/Button.jsx";
import { useLang } from "../../context/LangContext.jsx";
import { api } from "../../api/client.js";

export default function ManageBooking({ onDone }) {
  const { copy } = useLang();
  const t = copy.booking;

  const [id, setId] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [appt, setAppt] = useState(null);
  const [showReschedule, setShowReschedule] = useState(false);
  const [reDate, setReDate] = useState("");
  const [reSlot, setReSlot] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleLookup() {
    if (!id.trim() || !email.trim()) return setError(t.errLookupBoth);
    setError("");
    setBusy(true);
    const res = await api.lookupAppointment(id.trim(), email.trim());
    setBusy(false);
    if (res.ok) setAppt(res.appointment);
    else setError(t.errors[res.error] || t.errors.generic);
  }

  async function handleCancel() {
    setError("");
    setBusy(true);
    const res = await api.cancelAppointment(id.trim(), email.trim());
    setBusy(false);
    if (res.ok) onDone(t.successCancel);
    else setError(t.errors[res.error] || t.errors.generic);
  }

  async function handleReschedule() {
    if (!reDate || !reSlot) return setError(t.errPickNewDateSlot);
    setError("");
    setBusy(true);
    const res = await api.rescheduleAppointment(id.trim(), email.trim(), reDate, reSlot);
    setBusy(false);
    if (res.ok) onDone(t.successReschedule(reDate, reSlot));
    else setError(t.errors[res.error] || t.errors.generic);
  }

  function reset() {
    setAppt(null);
    setId("");
    setEmail("");
    setShowReschedule(false);
    setError("");
  }

  if (!appt) {
    return (
      <div>
        <Field label={t.lookupId}>
          <input value={id} onChange={(e) => setId(e.target.value)} placeholder={t.idPlaceholder} />
        </Field>
        <Field label={t.lookupEmail}>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        {error && <div className="bk-err">{error}</div>}
        <Button variant="primary" fullWidth onClick={handleLookup} disabled={busy}>
          {t.findBtn}
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div className="bk-appt-summary">
        <strong>{appt.id || id}</strong>
        <div>{appt.date} · {appt.slot || appt.time}</div>
        <div>{appt.name}</div>
      </div>

      {!showReschedule && error && <div className="bk-err">{error}</div>}

      {!showReschedule ? (
        <div className="booking-foot">
          <Button variant="ghost" onClick={handleCancel} disabled={busy}>{t.cancelAppt}</Button>
          <Button variant="primary" fullWidth onClick={() => setShowReschedule(true)}>{t.reschedule}</Button>
        </div>
      ) : (
        <div>
          <Field label={t.newDate}>
            <input type="date" value={reDate} onChange={(e) => setReDate(e.target.value)} />
          </Field>
          <Field label={t.slot}>
            <SlotPicker date={reDate} value={reSlot} onChange={setReSlot} emptyLabel={t.slotEmpty} />
          </Field>
          {error && <div className="bk-err">{error}</div>}
          <div className="booking-foot">
            <Button variant="ghost" onClick={() => setShowReschedule(false)}>{t.back}</Button>
            <Button variant="primary" fullWidth onClick={handleReschedule} disabled={busy}>{t.confirmNewTime}</Button>
          </div>
        </div>
      )}

      <Button variant="text" fullWidth onClick={reset} style={{ marginTop: 10 }}>
        {t.lookupDifferent}
      </Button>
    </div>
  );
}
