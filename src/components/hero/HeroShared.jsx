import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { isSafeHref } from "../../data/siteContent.js";
import ChatInput from "../chat/ChatInput.jsx";
import Button from "../ui/Button.jsx";
import GlassPanel from "../ui/GlassPanel.jsx";
import WorkflowChain from "../ui/WorkflowChain.jsx";

/**
 * The homepage's two fixed calls to action (copy.home.cta_primary /
 * cta_secondary) — primary opens the existing booking panel, secondary
 * goes to the "What We Build" page. Hero.jsx resolves both handlers
 * (and passes null for one it can't honour, e.g. the products page was
 * removed), so every layout renders this the same way. Separate from
 * the admin's HeroButtons row, which stays an optional extra.
 */
export function HeroCtas({ primaryLabel, secondaryLabel, onPrimary, onSecondary, className }) {
  const showPrimary = primaryLabel && onPrimary;
  const showSecondary = secondaryLabel && onSecondary;
  if (!showPrimary && !showSecondary) return null;
  return (
    <div className={`hero-ctas ${className || ""}`.trim()}>
      {showPrimary && <Button variant="primary" onClick={onPrimary}>{primaryLabel}</Button>}
      {showSecondary && <Button variant="ghost" onClick={onSecondary}>{secondaryLabel}</Button>}
    </div>
  );
}

/**
 * Heading + one-line intro shared by every homepage section below the
 * hero (situations, capabilities, …) so they read as one family.
 */
function HeroBlockHead({ id, kicker, heading, intro }) {
  if (!heading && !intro) return null;
  return (
    <div className="hero-block-head">
      {kicker && <p className="hero-eyebrow hero-block-kicker">{kicker}</p>}
      {heading && <h2 id={id}>{heading}</h2>}
      {intro && <p>{intro}</p>}
    </div>
  );
}

/**
 * The homepage's closing conversion point, after the visitor has seen
 * who Perennia helps, what it does and how it works: what the discovery
 * meeting is for (and is not), then the same HeroCtas as the hero —
 * one primary booking button, one secondary. A quiet GlassPanel, not a
 * sales banner. The hero and this panel are the only two places on the
 * homepage body that offer booking.
 */
export function HeroDiscovery({ heading, body, note, ctas, className }) {
  if (!ctas) return null;
  return (
    <section className={`hero-block hero-discovery-block ${className || ""}`.trim()} aria-labelledby="hero-discovery-heading">
      <GlassPanel className="hero-discovery">
        {heading && <h2 id="hero-discovery-heading">{heading}</h2>}
        {body && <p>{body}</p>}
        {note && <p className="hero-discovery-note">{note}</p>}
        {ctas}
      </GlassPanel>
    </section>
  );
}

/**
 * "Our work" — the single homepage portfolio section. Featured work (the
 * JDK Factory ERP case study: connected lifecycle, one real screen, link
 * to the full case-study content page "jdk-factory-erp") stands apart
 * from "Other work": a quiet text list (who it was for, the need, what
 * was built) with no screenshots or links, so the hierarchy is obvious
 * and nothing links to a page that doesn't exist. The featured panel is
 * omitted if its page is missing (featured.onOpen null).
 */
export function HeroWork({ kicker, heading, intro, featured, otherLabel, needLabel, builtLabel, otherItems, className }) {
  const showFeatured = featured?.heading && featured?.onOpen;
  if (!showFeatured && !otherItems?.length) return null;
  return (
    <section className={`hero-block hero-work ${className || ""}`.trim()} aria-labelledby="hero-work-heading">
      <HeroBlockHead id="hero-work-heading" kicker={kicker} heading={heading} intro={intro} />
      {showFeatured && (
        <GlassPanel className="hero-case-panel">
          <div className="hero-case-text">
            {featured.kicker && <p className="hero-eyebrow hero-case-kicker">{featured.kicker}</p>}
            <h3>{featured.heading}</h3>
            {featured.body && <p>{featured.body}</p>}
            <WorkflowChain stages={featured.stages} label={featured.heading} className="hero-case-chain" />
            <div>
              <Button variant="ghost" onClick={featured.onOpen}>{featured.linkLabel}</Button>
            </div>
          </div>
          {featured.imageSrc && (
            <img className="hero-case-image" src={featured.imageSrc} alt={featured.imageAlt || ""} loading="lazy" />
          )}
        </GlassPanel>
      )}
      {otherItems?.length > 0 && (
        <div className="hero-work-other">
          {otherLabel && <h3 className="hero-work-other-label">{otherLabel}</h3>}
          <ul className="hero-work-list">
            {otherItems.map(({ id, tag, label, need, built }) => (
              <li key={id}>
                {tag && <span className="hero-work-tag">{tag}</span>}
                <h4>{label}</h4>
                <p><span className="hero-work-term">{needLabel}</span> {need}</p>
                <p><span className="hero-work-term">{builtLabel}</span> {built}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

/**
 * "Why trust Perennia" — the single differentiator section: the central
 * claim (reliable technology induction), a two-sided contrast between
 * delivering software and getting it working in the business, four
 * grouped points on how Perennia approaches delivery (an approach, not
 * guarantees), and the short trust line (copy.home.principles) that
 * used to sit in the hero. Sits after the process, before the
 * discovery panel.
 */
export function HeroTrust({ kicker, heading, intro, contrast, points, principles, className }) {
  if (!heading) return null;
  return (
    <section className={`hero-block hero-trust ${className || ""}`.trim()} aria-labelledby="hero-trust-heading">
      <HeroBlockHead id="hero-trust-heading" kicker={kicker} heading={heading} intro={intro} />
      {contrast?.a && contrast?.b && (
        <GlassPanel className="hero-trust-contrast">
          <div className="hero-trust-side">
            <span className="hero-trust-side-label">{contrast.labelA}</span>
            <p>{contrast.a}</p>
          </div>
          <div className="hero-trust-side is-perennia">
            <span className="hero-trust-side-label">{contrast.labelB}</span>
            <p>{contrast.b}</p>
          </div>
        </GlassPanel>
      )}
      {points?.length > 0 && (
        <ul className="hero-trust-points">
          {points.map(({ id, label, body }) => (
            <li key={id}>
              <h3>{label}</h3>
              <p>{body}</p>
            </li>
          ))}
        </ul>
      )}
      <HeroPrinciples items={principles} className="hero-trust-principles" />
    </section>
  );
}

/**
 * "Who we work with" — the section under the hero: the positioning
 * heading and target profile, the three situation cards (HOME_TOPICS),
 * then the business types Perennia understands particularly well
 * (HOME_SECTORS, plain text — not an icon grid) with a closing note so
 * no other industry feels excluded. Shared by
 * the classic/split/editorial layouts; each passes its own list/card
 * classes (grid, stacked rows, or a horizontal strip) so only the
 * arrangement differs, never the content. Clicking a card still hands
 * its question to the AI Assistant. No booking CTA here on purpose —
 * see HeroDiscovery.
 */
export function HeroSituations({
  kicker, heading, intro, topics, onTopicClick,
  sectorsHeading, sectors, sectorsNote,
  className, listClassName, cardClassName,
}) {
  if (!topics?.length) return null;
  return (
    <section className={`hero-block hero-situations ${className || ""}`.trim()} aria-labelledby="hero-situations-heading">
      <HeroBlockHead id="hero-situations-heading" kicker={kicker} heading={heading} intro={intro} />
      <div className={listClassName}>
        {topics.map(({ id, label, audience, body }) => (
          <button key={id} className={`hero-section ${cardClassName || ""}`.trim()} onClick={() => onTopicClick(id)}>
            <h3>{label}</h3>
            {audience && <span className="hero-section-audience">{audience}</span>}
            <p>{body}</p>
            <span className="hero-section-arrow" aria-hidden="true">→</span>
          </button>
        ))}
      </div>
      {sectors?.length > 0 && (
        <div className="hero-sectors">
          {sectorsHeading && <h3 className="hero-sectors-heading">{sectorsHeading}</h3>}
          <ul className="hero-sectors-list">
            {sectors.map(({ id, label, body }) => (
              <li key={id}>
                <h4>{label}</h4>
                <p>{body}</p>
              </li>
            ))}
          </ul>
          {sectorsNote && <p className="hero-sectors-note">{sectorsNote}</p>}
        </div>
      )}
    </section>
  );
}

/**
 * "What Perennia does" — Technology / AI / Advisory (HOME_CAPABILITIES)
 * as three columns of ONE GlassPanel (the design system's shared
 * surface, so it follows the admin surface-style setting), deliberately
 * not three more cards: these are facets of one partner, not separate
 * services. Closes with the ways a customer can engage and the scope/
 * investment note (no prices, by design); the CTAs follow the process
 * section right after it.
 */
export function HeroCapabilities({ heading, intro, items, roles, scopeNote, className }) {
  if (!items?.length) return null;
  return (
    <section className={`hero-block hero-capabilities ${className || ""}`.trim()} aria-labelledby="hero-capabilities-heading">
      <HeroBlockHead id="hero-capabilities-heading" heading={heading} intro={intro} />
      <GlassPanel className="hero-capabilities-panel">
        {items.map(({ id, label, lead, body }) => (
          <div key={id} className="hero-capability">
            <h3>{label}</h3>
            <p className="hero-capability-lead">{lead}</p>
            <p>{body}</p>
          </div>
        ))}
      </GlassPanel>
      {(roles || scopeNote) && (
        <div className="hero-capabilities-foot">
          {roles && <p>{roles}</p>}
          {scopeNote && <p className="hero-capabilities-scope">{scopeNote}</p>}
        </div>
      )}
    </section>
  );
}

/**
 * Kuwait/GCC credibility — one restrained GlassPanel between "what we
 * do" and "how we work" (technology → GCC understanding → practical
 * implementation): the message on one side, three factual points on
 * the other. No imagery, flags or maps; facts only (HOME_LOCAL_POINTS).
 */
export function HeroLocal({ kicker, heading, intro, points, className }) {
  if (!heading) return null;
  return (
    <section className={`hero-block hero-local ${className || ""}`.trim()} aria-labelledby="hero-local-heading">
      <GlassPanel className="hero-local-panel">
        <div className="hero-local-message">
          {kicker && <p className="hero-eyebrow hero-local-kicker">{kicker}</p>}
          <h2 id="hero-local-heading">{heading}</h2>
          {intro && <p>{intro}</p>}
        </div>
        {points?.length > 0 && (
          <ul className="hero-local-points">
            {points.map(({ id, label, body }) => (
              <li key={id}>
                <h3>{label}</h3>
                <p>{body}</p>
              </li>
            ))}
          </ul>
        )}
      </GlassPanel>
    </section>
  );
}

/**
 * "How we work" — the seven-step method (HOME_PROCESS) as one ordered
 * list: a horizontal timeline on desktop, a vertical one on mobile
 * (see .hero-process in Hero.css). Plain numbered markers on a hairline
 * — a method, not an infographic. Followed by the page's closing CTAs.
 */
export function HeroProcess({ kicker, heading, intro, steps, ctas, className }) {
  if (!steps?.length) return null;
  return (
    <section className={`hero-block hero-process-block ${className || ""}`.trim()} aria-labelledby="hero-process-heading">
      <HeroBlockHead id="hero-process-heading" kicker={kicker} heading={heading} intro={intro} />
      <ol className="hero-process">
        {steps.map(({ id, label, body }, i) => (
          <li key={id} className="hero-process-step">
            <span className="hero-process-marker" aria-hidden="true">{i + 1}</span>
            <div className="hero-process-text">
              <h3>{label}</h3>
              <p>{body}</p>
            </div>
          </li>
        ))}
      </ol>
      {ctas}
    </section>
  );
}

/**
 * Small static line above the H1 (copy.home.eyebrow) — the brand
 * proposition. Deliberately not animated: the headline beneath it must
 * be readable the moment the page paints.
 */
export function HeroEyebrow({ text, className }) {
  if (!text) return null;
  return <p className={`hero-eyebrow ${className || ""}`.trim()}>{text}</p>;
}

/**
 * Short, quiet list of what Perennia stands for (copy.home.principles),
 * shown at the foot of the trust section (HeroTrust)
 * — plain text, not buttons, so it reads as context rather than as yet
 * another row of things to click.
 */
export function HeroPrinciples({ items, className }) {
  if (!items?.length) return null;
  return (
    <ul className={`hero-principles ${className || ""}`.trim()}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * Resolves admin-provisioned hero buttons (copy.home_hero_buttons) into
 * a flat, render-ready list — i18n label lookup + href safety check
 * done once, shared by every place that renders this same config
 * (HeroButtons above, CenteredCardLayout's pill row).
 */
export function resolveHeroButtons(buttons, lang) {
  return (buttons || [])
    .map((btn, i) => {
      const label = btn.label?.[lang] ?? Object.values(btn.label || {})[0] ?? "";
      if (!label || !isSafeHref(btn.url)) return null;
      return { key: i, label, url: btn.url, external: /^https?:\/\//.test(btn.url) };
    })
    .filter(Boolean);
}

/**
 * Admin-provisioned row of slim buttons, shown instead of the plain
 * tagline once at least one is configured. Every button shares the
 * same background (pill outline), so the row reads as one control
 * regardless of count or label length.
 */
export function HeroButtons({ buttons, lang }) {
  return (
    <div className="hero-buttons" role="navigation">
      {resolveHeroButtons(buttons, lang).map(({ key, label, url, external }) => (
        <a
          key={key}
          className="hero-button"
          href={url}
          {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
        >
          {label}
        </a>
      ))}
    </div>
  );
}

/**
 * Small circular avatar — an uploaded image (chat.avatar_url, admin-
 * configurable, Settings > Chat / AI assistant) if set, otherwise a
 * plain initial letter. Used by both HeroChatComposer here and
 * ChatWidget's header, so the homepage entry point and the sticky
 * popover always show the same face rather than looking like two
 * different assistants.
 */
export function ChatAvatar({ avatarUrl, initial, className }) {
  return (
    <span className={`chat-avatar ${className || ""}`.trim()} aria-hidden="true">
      {avatarUrl ? <img src={avatarUrl} alt="" /> : (initial || "A")}
    </span>
  );
}

/**
 * The homepage's quick-start entry into the AI Assistant — a plain
 * single-line text composer (no avatar here; ChatWidget's own header
 * still shows one once the conversation opens). Deliberately kept
 * text-only (no mic here, unlike the sticky ChatWidget popover, which
 * also supports voice) and this compact: it's meant to read as a fast
 * way in to the *same* assistant, not as a second, competing chat
 * surface with its own message history and status states.
 */
export function HeroChatComposer({ value, onChange, onSend, placeholder, sendLabel, label, className }) {
  return (
    <>
      {/* Optional caption (copy.home.assistant_label) framing the box as
          a working example of what Perennia builds, not a gimmick. */}
      {label && <p className="hero-quick-chat-label">{label}</p>}
      <div className={`hero-quick-chat ${className || ""}`.trim()}>
        <ChatInput value={value} onChange={onChange} onSend={onSend} placeholder={placeholder} sendLabel={sendLabel} />
      </div>
    </>
  );
}

/**
 * Renders `text` as a single unbroken line that always fits its
 * container, at any viewport width and at any string length (the
 * headline is admin-configurable copy, so we can't assume how long
 * it will be). Rather than guessing a font-size breakpoint by
 * breakpoint, it measures the natural width of the text after
 * render and uniformly scales it down just enough to fit — same
 * idea as `text-overflow: clamp`-by-hand. Re-measures on resize and
 * whenever the text itself changes (e.g. a language switch).
 *
 * Deliberately kept as ONE text node (no per-word/per-letter
 * splitting) — splitting the string into separate inline elements
 * broke text shaping and caused the words to overlap instead of
 * flowing normally. The ripple is done separately as a shimmer
 * sweep across the gradient fill (see .fit-one-line-inner in
 * Hero.css), which animates safely without touching layout at all.
 */
export function FitOneLine({ text, className, styleId }) {
  const outerRef = useRef(null);
  const innerRef = useRef(null);

  useLayoutEffect(() => {
    const outer = outerRef.current;
    const inner = innerRef.current;
    if (!outer || !inner) return;

    function fit() {
      inner.style.transform = "scale(1)";
      const outerWidth = outer.clientWidth;
      const innerWidth = inner.scrollWidth;
      // outerWidth can legitimately be 0 for a frame or two before the
      // parent has been laid out (first paint, font swap, tab restore).
      // Scaling to 0 in that window used to hide the headline for good —
      // ResizeObserver only fires on width *changes*, so if the width
      // never moves off 0→real in one observed step it never re-fires.
      if (outerWidth === 0 || innerWidth === 0) return;
      const nextScale = innerWidth > outerWidth ? outerWidth / innerWidth : 1;
      // Applied straight to the DOM instead of through React state.
      // fit() always resets the element to scale(1) before it
      // re-measures — if the final scale is set via setState and the
      // freshly computed value happens to match whatever was already
      // in state (very common: multiple ResizeObserver callbacks
      // firing for the same settled width), React bails out of the
      // re-render since the state didn't change, and the scale(1)
      // reset is left on screen — that's the desktop headline
      // clipping bug (text overflows both edges of the container's
      // overflow: hidden box). Writing the style directly guarantees
      // every fit() call ends with the correct scale applied, with no
      // dependency on whether the value changed since last time.
      inner.style.transform = `scale(${nextScale})`;
    }

    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(outer);
    // Re-fit once webfonts finish loading — the first measurement can
    // run before the display font swaps in, which would otherwise
    // lock in a scale sized for the fallback font's (different) width.
    document.fonts?.ready?.then(fit);
    return () => ro.disconnect();
  }, [text]);

  return (
    <div ref={outerRef} className={`fit-one-line ${className || ""}`.trim()} data-headline-style={styleId || "ripple-gradient"}>
      <span ref={innerRef} className="fit-one-line-inner">
        {text}
      </span>
    </div>
  );
}

// Admin-configurable — theme.headline_typing_speed_cps (characters per
// second; see backend/app/settings_registry.py and applyTheme.js). This
// is only the fallback for when no theme value has loaded yet.
const DEFAULT_TYPING_SPEED_CPS = 5;
const HOLD_AFTER_TYPE_MS = 1100; // beat before handing off to the permanent tagline

/**
 * The homepage's H1: types out the admin-configured `statement`
 * (copy.home.heroStatement — "what Perennia does"), then hands off to
 * the permanent two-line brand tagline (copy.home.taglineLine1/2),
 * which stays on screen for good (no looping/repeating — see the
 * brief). Both layers are mounted for the entire lifetime of this
 * component, stacked in the same grid cell (grid-area: 1/1), so the
 * container's height is reserved from first paint and never changes
 * as the visible layer swaps — only opacity animates, never layout.
 *
 * The typed-so-far substring runs through FitOneLine, reusing its
 * scale-to-fit measurement (transform: scale, not a layout property)
 * so an in-progress or very long statement never overflows.
 *
 * Accessibility: the essential content (both strings) is exposed via
 * a single static aria-label on the <h1>, independent of animation
 * phase — a screen reader never has to wait for the typing to finish,
 * and prefers-reduced-motion skips straight to the final tagline.
 */
export function HeroHeadline({ statement, taglineLine1, taglineLine2, className, typingSpeedCps }) {
  const reduceMotionRef = useRef(
    typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
  const skip = reduceMotionRef.current || !statement;

  const [phase, setPhase] = useState(skip ? "tagline" : "typing"); // "typing" -> "tagline"
  const [count, setCount] = useState(0);

  // Admin-configurable (theme.headline_typing_speed_cps) characters-
  // per-second, converted to a per-character delay. Falls back to
  // DEFAULT_TYPING_SPEED_CPS if the theme hasn't loaded / is unset.
  const typeSpeedMs = Math.max(1, Math.round(1000 / (typingSpeedCps || DEFAULT_TYPING_SPEED_CPS)));

  useEffect(() => {
    if (skip || phase !== "typing") return;
    if (count < statement.length) {
      const id = setTimeout(() => setCount((c) => c + 1), typeSpeedMs);
      return () => clearTimeout(id);
    }
    const id = setTimeout(() => setPhase("tagline"), HOLD_AFTER_TYPE_MS);
    return () => clearTimeout(id);
  }, [phase, count, statement, skip, typeSpeedMs]);

  const typingDone = phase !== "typing";
  // A literal newline in copy.home.hero_statement (admin-editable, see
  // settings_registry.py) types across two lines instead of one — the
  // typed-so-far substring is split on "\n" and each line renders as
  // its own FitOneLine, stacked (FitOneLine is block-level, so this
  // stacks with no extra markup). No newline present = today's
  // single-line behavior, unchanged.
  const flatStatement = statement ? statement.replace(/\n/g, " ") : "";
  const accessibleName = statement ? `${flatStatement} — ${taglineLine1} ${taglineLine2}` : `${taglineLine1} ${taglineLine2}`;
  const typedLines = statement ? statement.slice(0, count).split("\n") : [];

  return (
    <h1 className={`hero-headline-stage ${className || ""}`.trim()} aria-label={accessibleName}>
      {statement && (
        <span className={`hero-headline-layer ${typingDone ? "is-hidden" : ""}`} aria-hidden="true">
          {typedLines.map((line, i) => (
            <FitOneLine key={i} text={line} styleId="solid-white" />
          ))}
        </span>
      )}
      <span className={`hero-headline-layer hero-tagline-layer ${typingDone ? "is-visible" : ""}`} aria-hidden="true">
        <span className="hero-tagline-line1">{taglineLine1}</span>
        <span className="hero-tagline-line2">{taglineLine2}</span>
      </span>
    </h1>
  );
}

/**
 * One-line supporting proposition beneath the headline — the
 * "we design, build and operate…" sentence in the brief's hero
 * hierarchy. Plain paragraph, no admin styling hooks needed.
 */
export function HeroSupportingText({ text, className }) {
  if (!text) return null;
  return <p className={`hero-supporting ${className || ""}`.trim()}>{text}</p>;
}

/**
 * Subtle example-prompt chips under the quick-chat composer — tapping
 * one hands the preset question straight to onPick (same handoff the
 * composer's own Send button and the topic cards use). Kept as plain
 * text chips, deliberately quieter than the hero buttons/CTAs, so they
 * read as suggestions rather than another row of calls to action.
 */
export function HeroExamplePrompts({ prompts, onPick, className }) {
  if (!prompts?.length) return null;
  return (
    <div className={`hero-example-prompts ${className || ""}`.trim()}>
      {prompts.map((prompt, i) => (
        <button key={i} type="button" className="hero-example-prompt" onClick={() => onPick(prompt)}>
          {prompt}
        </button>
      ))}
    </div>
  );
}
