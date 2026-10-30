// ──────────────────────────────────────────────────────────
// Every call here uses a *relative* path ("api/…"), never a
// hardcoded host:port — see vite.config.js for the matching dev-time
// proxy to the Python backend (backend/app/main.py).
//
// In development only (`npm run dev`, possibly without the backend),
// a failed call falls back to an in-memory mock so the UI is still
// explorable. A production build never does: a failed booking or chat
// request is reported as an error, never as a fake success.
// ──────────────────────────────────────────────────────────

const API_BASE = "api";
const USE_MOCKS = import.meta.env.DEV;

// { data } on success, otherwise { error } with a booking error code
// ("rate_limited" for HTTP 429, "generic" for anything else).
async function request(path, options) {
  try {
    const res = await fetch(`${API_BASE}/${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) return { error: res.status === 429 ? "rate_limited" : "generic" };
    return { data: await res.json() };
  } catch {
    return { error: "generic" };
  }
}

// For read-only site content, where the caller has bundled fallback
// data: null on any failure.
export async function tryFetch(path, options) {
  const { data } = await request(path, options);
  return data ?? null;
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
  // { reply, leadCaptured } or { error }; the widget shows its own
  // error text, since the message never reached anyone.
  async chat(message, lang, history, leadCaptured) {
    const { data, error } = await request("chat", {
      method: "POST",
      body: JSON.stringify({ message, lang, history, leadCaptured: !!leadCaptured }),
    });
    if (data) return { reply: data.reply, leadCaptured: !!data.leadCaptured };
    if (!USE_MOCKS) return { error, leadCaptured: !!leadCaptured };
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
    const { data } = await request(qs);
    if (data) return data.slots;
    return USE_MOCKS ? mockSlotsFor(date) : [];
  },

  async createAppointment(payload) {
    const { data, error } = await request("booking/appointments", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (data) return data;
    if (!USE_MOCKS) return { ok: false, error };
    const id = genId();
    mockAppointments.set(id, { ...payload, id, status: "confirmed" });
    return { ok: true, id };
  },

  async lookupAppointment(id, email) {
    const { data, error } = await request("booking/appointments/lookup", {
      method: "POST",
      body: JSON.stringify({ id, email }),
    });
    if (data) return data;
    if (!USE_MOCKS) return { ok: false, error };
    const appt = mockAppointments.get(id);
    if (appt && appt.email?.toLowerCase() === email.toLowerCase()) {
      return { ok: true, appointment: appt };
    }
    return { ok: false, error: "not_found" };
  },

  async cancelAppointment(id, email) {
    const { data, error } = await request("booking/appointments/cancel", {
      method: "POST",
      body: JSON.stringify({ id, email }),
    });
    if (data) return data;
    if (!USE_MOCKS) return { ok: false, error };
    const appt = mockAppointments.get(id);
    if (appt) appt.status = "cancelled";
    return { ok: true };
  },

  async rescheduleAppointment(id, email, date, time) {
    const { data, error } = await request("booking/appointments/reschedule", {
      method: "POST",
      body: JSON.stringify({ id, email, date, time }),
    });
    if (data) return data;
    if (!USE_MOCKS) return { ok: false, error };
    const appt = mockAppointments.get(id);
    if (appt) Object.assign(appt, { date, time });
    return { ok: true };
  },
};
