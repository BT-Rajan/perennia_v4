// ──────────────────────────────────────────────────────────
// Every call here is same-origin in dev via vite.config.js's proxy
// (so the session cookie set by the backend just works, no CORS
// dance needed) and expected to be same-origin in production too -
// see PASS7_NOTES.md for the deployment note. `credentials: "include"`
// is kept anyway as a safety net if this ever *is* cross-origin.
// ──────────────────────────────────────────────────────────

let csrfToken = null;

export function setCsrfToken(token) {
  csrfToken = token;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Parses a response body as JSON without ever throwing a raw
// SyntaxError at the caller. Reads the text first, so a non-JSON body
// (an HTML error/login page from a proxy, a stale SPA fallback, a
// gateway timeout page, etc.) turns into a clear ApiError instead of
// an uncaught `Unexpected token '<', "<!doctype "... is not valid
// JSON` — that message was the underlying bug: the old code called
// `res.json()` directly on every 2xx response and let it throw
// whatever the JSON parser produced.
async function parseJsonSafe(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    throw new ApiError(
      "The server sent back an unexpected response instead of data — this usually means the request " +
        "didn't reach the API (a proxy/deployment routing issue) or the session needs a refresh. " +
        "Please reload the page and try again.",
      res.status
    );
  }
}

async function request(path, options = {}) {
  const method = options.method || "GET";
  const isFormData = options.body instanceof FormData;
  const headers = { ...(isFormData ? {} : { "Content-Type": "application/json" }), ...options.headers };
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;

  const res = await fetch(`/${path}`, { credentials: "include", ...options, headers });

  if (res.status === 401) {
    throw new ApiError("Session expired — please log in again.", 401);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await parseJsonSafe(res);
      detail = body?.detail || detail;
    } catch {
      // response wasn't JSON; keep the generic message
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return null;
  return parseJsonSafe(res);
}

export const adminApi = {
  login: (username, password) =>
    request("admin/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request("admin/api/auth/logout", { method: "POST" }),
  me: () => request("admin/api/auth/me"),

  statsOverview: () => request("admin/api/stats/overview"),

  listAppointments: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
    return request(`admin/api/booking/appointments?${qs}`);
  },
  createAppointment: (body) => request("admin/api/booking/appointments", { method: "POST", body: JSON.stringify(body) }),
  // Public slot-availability check, reused here so the admin's manual
  // "Add appointment" form can only pick a slot the grid actually allows.
  getSlots: (date, serviceId) =>
    request(`api/booking/slots?date=${encodeURIComponent(date)}${serviceId ? `&service_id=${encodeURIComponent(serviceId)}` : ""}`),
  cancelAppointment: (id) => request(`admin/api/booking/appointments/${id}/cancel`, { method: "POST" }),
  acceptAppointment: (id) => request(`admin/api/booking/appointments/${id}/accept`, { method: "POST" }),
  rejectAppointment: (id, reason) =>
    request(`admin/api/booking/appointments/${id}/reject`, { method: "POST", body: JSON.stringify({ reason: reason || "" }) }),
  rescheduleAppointment: (id, date, time) =>
    request(`admin/api/booking/appointments/${id}/reschedule`, { method: "POST", body: JSON.stringify({ date, time }) }),

  listLeads: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
    return request(`admin/api/leads?${qs}`);
  },
  createLead: (body) => request("admin/api/leads", { method: "POST", body: JSON.stringify(body) }),
  getLead: (id) => request(`admin/api/leads/${id}`),
  updateLead: (id, body) => request(`admin/api/leads/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteLead: (id) => request(`admin/api/leads/${id}`, { method: "DELETE" }),

  listSettingCategories: () => request("admin/api/settings/categories"),
  getSettingCategory: (category) => request(`admin/api/settings/${category}`),
  updateSettingCategory: (category, values) =>
    request(`admin/api/settings/${category}`, { method: "PUT", body: JSON.stringify(values) }),
  uploadImage: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("admin/api/uploads/image", { method: "POST", body: formData });
  },

  // -- calendar module: services (Pass 0 — admin-only catalog, see
  //    docs/CALENDAR_MODULE_PLAN.md) --
  listServices: () => request("admin/api/services"),
  getService: (id) => request(`admin/api/services/${id}`),
  createService: (body) => request("admin/api/services", { method: "POST", body: JSON.stringify(body) }),
  updateService: (id, body) => request(`admin/api/services/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteService: (id) => request(`admin/api/services/${id}`, { method: "DELETE" }),
  addServiceQuestion: (serviceId, body) =>
    request(`admin/api/services/${serviceId}/questions`, { method: "POST", body: JSON.stringify(body) }),
  updateServiceQuestion: (serviceId, questionId, body) =>
    request(`admin/api/services/${serviceId}/questions/${questionId}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteServiceQuestion: (serviceId, questionId) =>
    request(`admin/api/services/${serviceId}/questions/${questionId}`, { method: "DELETE" }),
  reorderServiceQuestions: (serviceId, orderedIds) =>
    request(`admin/api/services/${serviceId}/questions/reorder`, {
      method: "POST", body: JSON.stringify({ ordered_ids: orderedIds }),
    }),

  // -- calendar module: webhooks (Pass 11, see docs/CALENDAR_MODULE_PLAN.md) --
  listWebhooks: () => request("admin/api/webhooks"),
  createWebhook: (body) => request("admin/api/webhooks", { method: "POST", body: JSON.stringify(body) }),
  updateWebhook: (id, body) => request(`admin/api/webhooks/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteWebhook: (id) => request(`admin/api/webhooks/${id}`, { method: "DELETE" }),
  regenerateWebhookSecret: (id) => request(`admin/api/webhooks/${id}/regenerate-secret`, { method: "POST" }),
  listWebhookDeliveries: (id) => request(`admin/api/webhooks/${id}/deliveries`),
  testWebhook: (id) => request(`admin/api/webhooks/${id}/test`, { method: "POST" }),

  // -- calendar module: calendar sync (Pass 12, see docs/CALENDAR_MODULE_PLAN.md) --
  getCalendarSyncStatus: () => request("admin/api/calendar-sync/status"),
  completeCalendarSyncCallback: (code, state) =>
    request(`admin/api/calendar-sync/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`),
  selectCalendarSyncCalendar: (credentialId, calendarId) =>
    request("admin/api/calendar-sync/select", {
      method: "POST", body: JSON.stringify({ credential_id: credentialId, calendar_id: calendarId }),
    }),
  disconnectCalendarSync: () => request("admin/api/calendar-sync/disconnect", { method: "POST" }),
  syncCalendarNow: () => request("admin/api/calendar-sync/sync-now", { method: "POST" }),

  // -- calendar module: direct/manual event management, independent of
  //    the booking flow — "full calendar controls" for whatever's on
  //    the connected account's calendar, not just this app's own
  //    appointment-linked events --
  listCalendarEvents: (dateFrom, dateTo) =>
    request(`admin/api/calendar-events?date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}`),
  createCalendarEvent: (body) => request("admin/api/calendar-events", { method: "POST", body: JSON.stringify(body) }),
  updateCalendarEvent: (id, body) => request(`admin/api/calendar-events/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCalendarEvent: (id) => request(`admin/api/calendar-events/${id}`, { method: "DELETE" }),

  // -- knowledge base (chat grounding: uploaded documents + web pages) --
  listKnowledge: () => request("admin/api/knowledge"),
  getKnowledgeSource: (id) => request(`admin/api/knowledge/${id}`),
  uploadKnowledgeFile: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("admin/api/knowledge/upload", { method: "POST", body: formData });
  },
  addKnowledgeUrl: (url) => request("admin/api/knowledge/url", { method: "POST", body: JSON.stringify({ url }) }),
  refreshKnowledgeSource: (id) => request(`admin/api/knowledge/${id}/refresh`, { method: "POST" }),
  setKnowledgeSourceActive: (id, isActive) =>
    request(`admin/api/knowledge/${id}`, { method: "PATCH", body: JSON.stringify({ is_active: isActive }) }),
  deleteKnowledgeSource: (id) => request(`admin/api/knowledge/${id}`, { method: "DELETE" }),

  // -- content: pages + FAQ (admin-editable, served publicly via /api/content) --
  getPageSchema: () => request("admin/api/content/pages/schema"),
  listPages: () => request("admin/api/content/pages"),
  getPage: (slug) => request(`admin/api/content/pages/${slug}`),
  upsertPage: (slug, body) => request(`admin/api/content/pages/${slug}`, { method: "PUT", body: JSON.stringify(body) }),
  deletePage: (slug) => request(`admin/api/content/pages/${slug}`, { method: "DELETE" }),
  reorderPages: (orderedSlugs) =>
    request("admin/api/content/pages/reorder", { method: "POST", body: JSON.stringify({ ordered_slugs: orderedSlugs }) }),
  listPageVersions: (slug) => request(`admin/api/content/pages/${slug}/versions`),
  rollbackPage: (slug, versionId) => request(`admin/api/content/pages/${slug}/rollback/${versionId}`, { method: "POST" }),

  getFaqSchema: () => request("admin/api/content/faq/schema"),
  listFaq: () => request("admin/api/content/faq"),
  createFaq: (body) => request("admin/api/content/faq", { method: "POST", body: JSON.stringify(body) }),
  updateFaq: (id, body) => request(`admin/api/content/faq/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteFaq: (id) => request(`admin/api/content/faq/${id}`, { method: "DELETE" }),
  reorderFaq: (orderedIds) =>
    request("admin/api/content/faq/reorder", { method: "POST", body: JSON.stringify({ ordered_ids: orderedIds }) }),
};

export { ApiError };
