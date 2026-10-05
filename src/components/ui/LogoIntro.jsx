import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLang } from "../../context/LangContext.jsx";
import "./LogoIntro.css";

/**
 * First-load logo intro, modelled on odontyn.com's header animation:
 * the logo mark appears large in the middle of a full-screen cover,
 * the wordmark slides out from behind it, then the whole logo flies up
 * into its real spot in the header and the nav fades in.
 *
 * Plays once per browser session (a full reload in the same tab won't
 * replay it), never for prefers-reduced-motion, and never when the
 * header shows the text wordmark instead of an image. Any click or key
 * press skips straight to the end. Uses the Web Animations API only —
 * no animation library.
 */

const SEEN_KEY = "perennia.logoIntroSeen";
const HTML_CLASS = "logo-intro-active";

function shouldPlay() {
  if (typeof window === "undefined") return false;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return false;
  try {
    return window.sessionStorage.getItem(SEEN_KEY) !== "1";
  } catch {
    return true;
  }
}

function markSeen() {
  try {
    window.sessionStorage.setItem(SEEN_KEY, "1");
  } catch {
    // storage blocked — the intro just plays again next load
  }
}

/**
 * Finds the logo's icon mark as a horizontal [start, end] fraction of
 * the image width: the first block of opaque columns, ended by a clear
 * gap before the wordmark. Works for any admin-uploaded logo laid out
 * as icon-then-text; returns null (no separate icon phase) when there's
 * no such gap or the image can't be read (e.g. cross-origin).
 */
function findIconSpan(img) {
  try {
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    if (!w || !h) return null;
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, w, h).data;
    const filled = new Uint8Array(w);
    for (let x = 0; x < w; x++) {
      for (let y = 0; y < h; y++) {
        if (data[(y * w + x) * 4 + 3] > 24) {
          filled[x] = 1;
          break;
        }
      }
    }
    const start = filled.indexOf(1);
    if (start < 0) return null;
    const minGap = Math.max(2, Math.round(w * 0.015));
    let gapStart = -1;
    for (let x = start; x < w; x++) {
      if (!filled[x]) {
        if (gapStart < 0) gapStart = x;
        if (x - gapStart + 1 >= minGap && filled.indexOf(1, x) > 0) {
          const end = gapStart / w;
          // An "icon" covering most of the logo isn't an icon — skip.
          return end > 0.6 ? null : { start: start / w, end };
        }
      } else {
        gapStart = -1;
      }
    }
    return null;
  } catch {
    return null;
  }
}

export default function LogoIntro() {
  const { branding } = useLang();
  const [play, setPlay] = useState(() => shouldPlay() && Boolean(branding.logoUrl));
  const coverRef = useRef(null);
  const markRef = useRef(null);
  const imgRef = useRef(null);
  // Logo URL captured at mount so a live-config swap mid-intro doesn't
  // restart the animation.
  const [src] = useState(branding.logoUrl);

  // Hide the header's own logo + nav before first paint while the intro
  // owns the screen (see LogoIntro.css).
  useLayoutEffect(() => {
    if (!play) return undefined;
    document.documentElement.classList.add(HTML_CLASS);
    return () => document.documentElement.classList.remove(HTML_CLASS);
  }, [play]);

  useEffect(() => {
    if (!play) return undefined;
    const cover = coverRef.current;
    const mark = markRef.current;
    const img = imgRef.current;
    let cancelled = false;
    let running = [];

    function finish() {
      if (cancelled) return;
      cancelled = true;
      running.forEach((a) => a.cancel());
      markSeen();
      document.documentElement.classList.remove(HTML_CLASS);
      setPlay(false);
    }

    function skip() {
      finish();
    }

    async function run() {
      try {
        if (!img.complete) await img.decode();
      } catch {
        finish();
        return;
      }
      if (cancelled) return;

      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const ratio = img.naturalHeight / img.naturalWidth;
      const W = Math.min(vw * 0.8, 620, (vh * 0.45) / ratio);
      const H = W * ratio;
      const left = (vw - W) / 2;
      const top = (vh - H) / 2;
      Object.assign(mark.style, { width: `${W}px`, left: `${left}px`, top: `${top}px` });
      cover.classList.add("logo-intro-ready");

      const span = findIconSpan(img);
      // Shift so the icon alone sits dead-centre, then slide back to
      // centre the full logo as the wordmark is revealed.
      const offset = span ? (0.5 - (span.start + span.end) / 2) * W : 0;
      const clipFrom = span ? `inset(-10% ${(1 - span.end) * 100}% -10% -10%)` : "inset(-10% -10% -10% -10%)";
      const clipTo = "inset(-10% -10% -10% -10%)";
      const ease = "cubic-bezier(0.65, 0, 0.35, 1)";

      // 1 — icon fades/zooms in, centred.
      const intro = img.animate(
        [
          { opacity: 0, transform: `translateX(${offset}px) scale(0.82)`, clipPath: clipFrom },
          { opacity: 1, transform: `translateX(${offset}px) scale(1)`, clipPath: clipFrom },
        ],
        { duration: 900, easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "forwards" },
      );
      running = [intro];
      await intro.finished;
      if (cancelled) return;

      // 2 — wordmark slides out from behind the icon.
      const reveal = img.animate(
        [
          { opacity: 1, transform: `translateX(${offset}px) scale(1)`, clipPath: clipFrom },
          { opacity: 1, transform: "translateX(0px) scale(1)", clipPath: clipTo },
        ],
        { duration: span ? 1300 : 600, easing: ease, fill: "forwards" },
      );
      running = [intro, reveal];
      await reveal.finished;
      if (cancelled) return;

      // 3 — fly into the header logo's slot while the cover fades away.
      const target = document.querySelector(".top-bar-header .logo-img");
      const rect = target?.getBoundingClientRect();
      const fly = rect && rect.width
        ? mark.animate(
            [
              { transform: "translate(0px, 0px) scale(1)" },
              { transform: `translate(${rect.left - left}px, ${rect.top - top}px) scale(${rect.width / W})` },
            ],
            { duration: 1000, delay: 350, easing: ease, fill: "forwards" },
          )
        : mark.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 600, delay: 350, fill: "forwards" });
      const fade = cover.firstElementChild.animate([{ opacity: 1 }, { opacity: 0 }], {
        duration: 900,
        delay: 450,
        easing: "ease-in-out",
        fill: "forwards",
      });
      running = [intro, reveal, fly, fade];
      await fly.finished;
      finish();
    }

    run();
    window.addEventListener("keydown", skip);
    cover.addEventListener("pointerdown", skip);
    return () => {
      window.removeEventListener("keydown", skip);
      cover.removeEventListener("pointerdown", skip);
      if (!cancelled) {
        cancelled = true;
        running.forEach((a) => a.cancel());
      }
    };
  }, [play]);

  if (!play) return null;

  return (
    <div className="logo-intro" ref={coverRef} aria-hidden="true">
      <div className="logo-intro-bg" />
      <div className="logo-intro-mark" ref={markRef}>
        <img ref={imgRef} src={src} alt="" onError={() => setPlay(false)} />
      </div>
    </div>
  );
}
