// ──────────────────────────────────────────────────────────
// Every call here uses a *relative* path ("api/…"), never a
// hardcoded host:port — see vite.config.js for the matching dev-time
// proxy to the Python backend (backend/app/main.py).
//
// If the backend isn't reachable (e.g. running `npm run dev` without
// it started), every call transparently falls back to an in-memory
// mock so the UI is still fully explorable.
// ──────────────────────────────────────────────────────────

const API_BASE = "api";

export async function tryFetch(path, options) {
  try {
    const res = await fetch(`${API_BASE}/${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return null; // signal caller to use the mock
  }
}

// ---- Mock data used only when no backend is present ----
const mockAppointments = new Map();
let mockCounter = 1000;

function genId() {
  mockCounter += 1;
  return `PRN-${mockCounter.toString(36).toUpperCase().padStart(8, "0")}`;
}

function mockSlotsFor(dateStr) {
  const base = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:30", "16:30"];
  const date = new Date(dateStr);
  const isWeekend = date.getDay() === 0 || date.getDay() === 6; // matches the backend's default Mon-Fri workweek
  if (isWeekend) return [];
  return base.filter((_, i) => (date.getDate() + i) % 4 !== 0);
}

export const api = {
  async chat(message, lang, history, leadCaptured) {
    const data = await tryFetch("chat", {
      method: "POST",
      body: JSON.stringify({ message, lang, history, leadCaptured: !!leadCaptured }),
    });
    if (data) return { reply: data.reply, leadCaptured: !!data.leadCaptured };
    // mock fallback: simple canned response
    return {
      reply: lang === "ar"
        ? "شكرًا لك! سيقوم أحد أعضاء فريقنا بمتابعة رسالتك قريبًا. هل ترغب في حجز موعد؟"
        : "Thanks for sharing that! Someone from our team will follow up shortly. Would you like to book a time to talk?",
      leadCaptured: !!leadCaptured,
    };
  },

  // Pass 8 (docs/CALENDAR_MODULE_PLAN.md): the bookable service catalog.
  // No mock fallback beyond an empty list — a fresh/offline install with
  // no backend simply shows the old free-text "what are you interested
  // in?" field, same as before this pass existed.
  async getServices() {
    const data = await tryFetch("booking/services");
    return data || [];
  },

  async getSlots(date, serviceId) {
    const qs = serviceId ? `booking/slots?date=${date}&service_id=${serviceId}` : `booking/slots?date=${date}`;
    const data = await tryFetch(qs);
    if (data) return data.slots;
    return mockSlotsFor(date);
  },

  async createAppointment(payload) {
    const data = await tryFetch("booking/appointments", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (data) return data;
    const id = genId();
    mockAppointments.set(id, { ...payload, id, status: "confirmed" });
    return { ok: true, id };
  },

  async lookupAppointment(id, email) {
    const data = await tryFetch("booking/appointments/lookup", {
      method: "POST",
      body: JSON.stringify({ id, email }),
    });
    if (data) return data;
    const appt = mockAppointments.get(id);
    if (appt && appt.email?.toLowerCase() === email.toLowerCase()) {
      return { ok: true, appointment: appt };
    }
    return { ok: false, error: "not_found" };
  },

  async cancelAppointment(id, email) {
    const data = await tryFetch("booking/appointments/cancel", {
      method: "POST",
      body: JSON.stringify({ id, email }),
    });
    if (data) return data;
    const appt = mockAppointments.get(id);
    if (appt) appt.status = "cancelled";
    return { ok: true };
  },

  async rescheduleAppointment(id, email, date, time) {
    const data = await tryFetch("booking/appointments/reschedule", {
      method: "POST",
      body: JSON.stringify({ id, email, date, time }),
    });
    if (data) return data;
    const appt = mockAppointments.get(id);
    if (appt) Object.assign(appt, { date, time });
    return { ok: true };
  },
};
