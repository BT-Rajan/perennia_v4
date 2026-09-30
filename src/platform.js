/**
 * Sets data-platform="ios" | "android" | "desktop" on <html>, purely
 * as a CSS hook for subtle native-feeling touch feedback (see
 * src/styles/native.css) — NEVER for gating features or content.
 * Every platform gets the identical app; this only changes how a
 * button feels when pressed. Runs once at startup, synchronously,
 * before first paint (imported directly in main.jsx) — there's no
 * SSR here, so no hydration-mismatch concern with reading
 * navigator.userAgent up front.
 */
export function applyPlatformAttribute() {
  if (typeof navigator === "undefined" || typeof document === "undefined") return;
  const ua = navigator.userAgent || "";
  // iPadOS 13+ reports as "Macintosh" with touch support — the
  // maxTouchPoints check catches that case too.
  const isIOS = /iPhone|iPad|iPod/.test(ua) || (ua.includes("Macintosh") && navigator.maxTouchPoints > 1);
  const isAndroid = /Android/.test(ua);
  const platform = isIOS ? "ios" : isAndroid ? "android" : "desktop";
  document.documentElement.setAttribute("data-platform", platform);
}
