import { useEffect, useState } from "react";
import Field from "./Field.jsx";
import SlotPicker from "./SlotPicker.jsx";
import Button from "../ui/Button.jsx";
import { useLang } from "../../context/LangContext.jsx";
import { api } from "../../api/client.js";

const todayISO = () => new Date().toISOString().slice(0, 10);

export default function NewAppointmentForm({ onCancel, onBooked }) {
  const { copy, lang } = useLang();
  const t = copy.booking;
  const [form, setForm] = useState({
    date: "", slot: "", name: "", email: "", phone: "", service: "", notes: "", serviceId: "",
  });
  const [answers, setAnswers] = useState({}); // { [questionId]: string }
  const [services, setServices] = useState(null); // null = still loading
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.getServices().then((list) => {
      if (cancelled) return;
      setServices(list);
      // A single-service (or freshly-set-up) site shouldn't make the
      // visitor pick from a list of one — just preselect it.
      if (list.length === 1) setForm((f) => ({ ...f, serviceId: list[0].id }));
    });
    return () => { cancelled = true; };
  }, []);

  const selectedService = services?.find((s) => s.id === form.serviceId) ?? null;
  const usingCatalog = (services?.length ?? 0) > 0;

  function set(key, val) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  function handleServiceChange(serviceId) {
    // Changing service can change duration/buffers, so any date/time
    // already picked against the old service's slot math is no longer
    // trustworthy — clear it rather than silently keep a stale slot.
    setForm((f) => ({ ...f, serviceId, slot: "" }));
    setAnswers({});
  }

  function setAnswer(questionId, val) {
    setAnswers((a) => ({ ...a, [questionId]: val }));
  }

  function validate() {
    if (usingCatalog && !form.serviceId) return t.errPickService;
    if (!form.date || !form.slot) return t.errPickDateSlot;
    if (!form.name.trim()) return t.errName;
    if (!/^\S+@\S+\.\S+$/.test(form.email)) return t.errEmail;
    if (selectedService) {
      for (const q of selectedService.questions) {
        if (q.required && !(answers[q.id] || "").trim()) return t.errRequiredQuestion;
      }
    }
    return "";
  }

  async function handleSubmit() {
    const validationError = validate();
    if (validationError) return setError(validationError);

    setError("");
    setSubmitting(true);
    const payload = {
      date: form.date, slot: form.slot, name: form.name, email: form.email,
      phone: form.phone, notes: form.notes, lang,
      service: usingCatalog ? (selectedService?.name || "") : form.service,
      service_id: form.serviceId || null,
      answers: selectedService
        ? selectedService.questions
            .filter((q) => (answers[q.id] || "").trim())
            .map((q) => ({ question_id: q.id, answer: answers[q.id].trim() }))
        : [],
    };
    const result = await api.createAppointment(payload);
    setSubmitting(false);
    if (result.ok) {
      onBooked({ ...form, id: result.id });
    } else {
      setError(t.errors[result.error] || t.errors.generic);
    }
  }

  return (
    <div>
      {usingCatalog && (
        <Field label={t.service}>
          <select value={form.serviceId} onChange={(e) => handleServiceChange(e.target.value)}>
            <option value="">{t.selectService}</option>
            {services.map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.duration_minutes} {t.minutesShort})</option>
            ))}
          </select>
        </Field>
      )}

      <Field label={t.date}>
        <input type="date" min={todayISO()} value={form.date} onChange={(e) => set("date", e.target.value)} />
      </Field>
      <Field label={t.slot}>
        <SlotPicker
          date={form.date}
          serviceId={form.serviceId || undefined}
          value={form.slot}
          onChange={(s) => set("slot", s)}
          emptyLabel={t.slotEmpty}
        />
      </Field>
      <Field label={t.name}>
        <input type="text" maxLength={120} value={form.name} onChange={(e) => set("name", e.target.value)} />
      </Field>
      <Field label={t.email}>
        <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />
      </Field>
      <Field label={t.phone}>
        <input type="tel" value={form.phone} onChange={(e) => set("phone", e.target.value)} />
      </Field>

      {!usingCatalog && (
        <Field label={t.service}>
          <input type="text" maxLength={200} value={form.service} onChange={(e) => set("service", e.target.value)} />
        </Field>
      )}

      {selectedService?.questions.map((q) => (
        <Field key={q.id} label={q.required ? `${q.label} *` : q.label}>
          {q.kind === "textarea" ? (
            <textarea rows={2} maxLength={2000} value={answers[q.id] || ""} onChange={(e) => setAnswer(q.id, e.target.value)} />
          ) : q.kind === "bool" ? (
            <input
              type="checkbox"
              checked={answers[q.id] === "true"}
              onChange={(e) => setAnswer(q.id, e.target.checked ? "true" : "")}
            />
          ) : (
            <input
              type={q.kind === "number" ? "number" : q.kind === "phone" ? "tel" : "text"}
              maxLength={2000}
              value={answers[q.id] || ""}
              onChange={(e) => setAnswer(q.id, e.target.value)}
            />
          )}
        </Field>
      ))}

      <Field label={t.notes}>
        <textarea rows={2} maxLength={1000} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
      </Field>

      {error && <div className="bk-err">{error}</div>}

      <div className="booking-foot">
        <Button variant="ghost" onClick={onCancel}>{t.cancel}</Button>
        <Button variant="primary" fullWidth onClick={handleSubmit} disabled={submitting}>
          {t.confirm}
        </Button>
      </div>
    </div>
  );
}
