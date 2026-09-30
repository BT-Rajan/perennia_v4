import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { adminApi } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import PageHeader from "../components/PageHeader.jsx";
import SettingField from "../components/SettingField.jsx";
import ThemePresetPicker from "../components/ThemePresetPicker.jsx";
import LayoutTemplatePicker from "../components/LayoutTemplatePicker.jsx";
import HeadlineStylePicker from "../components/HeadlineStylePicker.jsx";
import SurfaceStylePicker from "../components/SurfaceStylePicker.jsx";
import ButtonStylePicker from "../components/ButtonStylePicker.jsx";
import TypeScalePicker from "../components/TypeScalePicker.jsx";
import HeadingCasePicker from "../components/HeadingCasePicker.jsx";
import BackgroundStylePicker from "../components/BackgroundStylePicker.jsx";
import BackgroundIntensityPicker from "../components/BackgroundIntensityPicker.jsx";
import DensityPicker from "../components/DensityPicker.jsx";
import SectionRhythmPicker from "../components/SectionRhythmPicker.jsx";
import LogoZoomControl from "../components/LogoZoomControl.jsx";
import CalendarSyncConnector from "../components/CalendarSyncConnector.jsx";
import WebhooksPage from "./WebhooksPage.jsx";
import PagesPage from "./PagesPage.jsx";
import FaqPage from "./FaqPage.jsx";
import "./SettingsPage.css";

// Nicer labels for the sidebar than a raw category key. Anything not
// listed here just gets capitalized — adding a brand-new category in
// the backend registry still shows up automatically, just title-cased.
const CATEGORY_LABELS = {
  branding: "Branding",
  theme: "Theme",
  locale: "Language",
  contact: "Contact",
  features: "Features",
  booking: "Booking",
  chat: "Chat / AI assistant",
  notifications: "Notifications",
  templates: "Message templates",
  copy: "On-screen text",
  calendar_sync: "Calendar Sync",
  webhooks: "Webhooks",
  pages: "Pages",
  faq: "FAQ",
};

// Webhooks, Pages, and FAQ aren't schema-driven categories from the
// backend registry like the rest — they're each their own CRUD
// resource (see WebhooksPage.jsx / PagesPage.jsx / FaqPage.jsx) — so
// they're pinned into the sidebar as virtual entries instead, letting
// them live under Settings without needing a settings_registry entry
// of their own.
const VIRTUAL_CATEGORIES = [
  { key: "pages", Component: PagesPage },
  { key: "faq", Component: FaqPage },
  { key: "webhooks", Component: WebhooksPage },
];
const VIRTUAL_CATEGORY_KEYS = new Set(VIRTUAL_CATEGORIES.map((v) => v.key));

function labelFor(category) {
  return CATEGORY_LABELS[category] || category[0].toUpperCase() + category.slice(1);
}

export default function SettingsPage() {
  const { handleSessionExpired } = useAuth();
  const { category: categoryParam } = useParams();
  const navigate = useNavigate();

  const [categories, setCategories] = useState(null);
  const [schema, setSchema] = useState(null);
  const [values, setValues] = useState({});
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [savedAt, setSavedAt] = useState(null);

  // Load the category list once, then land on the first one if the
  // URL didn't specify one.
  useEffect(() => {
    adminApi
      .listSettingCategories()
      .then((cats) => {
        setCategories(cats);
        if (!categoryParam && cats.length > 0) {
          navigate(`/settings/${cats[0]}`, { replace: true });
        }
      })
      .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)));
  }, [categoryParam, navigate, handleSessionExpired]);

  const loadCategory = useCallback(
    (category) => {
      setLoading(true);
      setError("");
      setSavedAt(null);
      adminApi
        .getSettingCategory(category)
        .then((data) => {
          setSchema(data.schema_);
          // Secret fields never arrive with a real value (see backend) —
          // start them blank; a blank secret field on save just means
          // "leave the stored value alone".
          const initial = { ...data.values };
          for (const f of data.schema_) {
            if (f.secret) initial[f.key] = "";
          }
          setValues(initial);
          setFieldErrors({});
        })
        .catch((e) => (e.status === 401 ? handleSessionExpired() : setError(e.message)))
        .finally(() => setLoading(false));
    },
    [handleSessionExpired]
  );

  useEffect(() => {
    // Virtual categories (Pages, Webhooks) render their own
    // self-contained panel below, not through the generic schema
    // form — don't ask the settings API for a category that doesn't
    // exist there.
    if (categoryParam && !VIRTUAL_CATEGORY_KEYS.has(categoryParam)) loadCategory(categoryParam);
  }, [categoryParam, loadCategory]);

  function handleFieldChange(key, value) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleFieldError(key, message) {
    setFieldErrors((prev) => {
      const next = { ...prev };
      if (message) next[key] = message;
      else delete next[key];
      return next;
    });
  }

  async function handleSave(e) {
    e.preventDefault();
    if (Object.keys(fieldErrors).length > 0) return;

    setSaving(true);
    setError("");
    setSavedAt(null);
    try {
      // Secret fields: only send one the admin actually typed into —
      // an untouched (blank) secret field means "keep what's stored".
      const payload = {};
      for (const f of schema) {
        const v = values[f.key];
        if (f.secret && v === "") continue;
        payload[f.key] = v;
      }
      await adminApi.updateSettingCategory(categoryParam, payload);
      setSavedAt(Date.now());
      loadCategory(categoryParam); // re-fetch so secret placeholders reflect the new state
    } catch (e) {
      if (e.status === 401) handleSessionExpired();
      else setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (error) return <div className="page-error">{error}</div>;
  if (!categories) return <div className="page-loading">Loading…</div>;

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Everything customer-facing on the site is configured here — no deploy needed."
      />

      <div className="settings-layout">
        <nav className="settings-nav card">
          {categories.map((c) => (
            <button
              key={c}
              className={c === categoryParam ? "settings-nav-item active" : "settings-nav-item"}
              onClick={() => navigate(`/settings/${c}`)}
            >
              {labelFor(c)}
            </button>
          ))}
          {VIRTUAL_CATEGORIES.map(({ key }) => (
            <button
              key={key}
              className={key === categoryParam ? "settings-nav-item active" : "settings-nav-item"}
              onClick={() => navigate(`/settings/${key}`)}
            >
              {labelFor(key)}
            </button>
          ))}
        </nav>

        {(() => {
          const virtual = VIRTUAL_CATEGORIES.find((v) => v.key === categoryParam);
          if (virtual) {
            const { Component } = virtual;
            return <Component />;
          }
          return (
            <div className="card settings-form-wrap">
              {loading || !schema ? (
                <div className="page-loading">Loading…</div>
              ) : (
                <form onSubmit={handleSave}>
                  <h2 className="settings-form-title">{labelFor(categoryParam)}</h2>

                  {categoryParam === "theme" && (
                    <ThemePresetPicker
                      values={values}
                      onApply={(presetValues) => setValues((prev) => ({ ...prev, ...presetValues }))}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <LayoutTemplatePicker
                      value={values["theme.layout_template"]}
                      onChange={(v) => handleFieldChange("theme.layout_template", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <HeadlineStylePicker
                      value={values["theme.headline_style"]}
                      onChange={(v) => handleFieldChange("theme.headline_style", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <SurfaceStylePicker
                      value={values["theme.surface_style"]}
                      onChange={(v) => handleFieldChange("theme.surface_style", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <ButtonStylePicker
                      value={values["theme.button_style"]}
                      onChange={(v) => handleFieldChange("theme.button_style", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <TypeScalePicker
                      value={values["theme.type_scale"]}
                      onChange={(v) => handleFieldChange("theme.type_scale", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <HeadingCasePicker
                      value={values["theme.heading_case"]}
                      onChange={(v) => handleFieldChange("theme.heading_case", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <BackgroundStylePicker
                      value={values["theme.background_style"]}
                      onChange={(v) => handleFieldChange("theme.background_style", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <BackgroundIntensityPicker
                      value={values["theme.background_intensity"]}
                      onChange={(v) => handleFieldChange("theme.background_intensity", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <DensityPicker
                      value={values["theme.density"]}
                      onChange={(v) => handleFieldChange("theme.density", v)}
                    />
                  )}

                  {categoryParam === "theme" && (
                    <SectionRhythmPicker
                      value={values["theme.section_rhythm"]}
                      onChange={(v) => handleFieldChange("theme.section_rhythm", v)}
                    />
                  )}

                  {schema.map((field) => {
                    // Superseded by the LogoZoomControl composite below
                    // (rendered right after branding.logo_url) — a bare
                    // number input for a zoom factor isn't useful without
                    // a live preview next to it.
                    if (field.key === "branding.logo_scale") return null;
                    // Superseded by the picker galleries above — bare
                    // dropdowns of opaque ids aren't useful without the
                    // mini visual previews.
                    if (field.key === "theme.layout_template") return null;
                    if (field.key === "theme.headline_style") return null;
                    if (field.key === "theme.surface_style") return null;
                    if (field.key === "theme.button_style") return null;
                    if (field.key === "theme.type_scale") return null;
                    if (field.key === "theme.heading_case") return null;
                    if (field.key === "theme.background_style") return null;
                    if (field.key === "theme.background_intensity") return null;
                    if (field.key === "theme.density") return null;
                    if (field.key === "theme.section_rhythm") return null;
                    return (
                      <div key={field.key}>
                        <SettingField
                          field={field}
                          value={values[field.key]}
                          error={fieldErrors[field.key]}
                          onChange={(v) => handleFieldChange(field.key, v)}
                          onError={(msg) => handleFieldError(field.key, msg)}
                        />
                        {field.key === "branding.logo_url" && (
                          <LogoZoomControl
                            logoUrl={values["branding.logo_url"]}
                            scale={values["branding.logo_scale"]}
                            onScaleChange={(v) => handleFieldChange("branding.logo_scale", v)}
                          />
                        )}
                      </div>
                    );
                  })}

                  <div className="settings-form-footer">
                    <button type="submit" className="btn-primary" disabled={saving || Object.keys(fieldErrors).length > 0}>
                      {saving ? "Saving…" : "Save changes"}
                    </button>
                    {savedAt && <span className="settings-saved-msg">Saved.</span>}
                  </div>

                  {categoryParam === "calendar_sync" && <CalendarSyncConnector />}
                </form>
              )}
            </div>
          );
        })()}
      </div>
    </div>
  );
}
