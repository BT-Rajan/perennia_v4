import { HeroCtas, HeroEyebrow, HeroHeadline, HeroSupportingText, resolveHeroButtons } from "../HeroShared.jsx";

/**
 * "centered-card" — headline, tagline, CTAs, and topic pills all
 * live inside one bordered glass card instead of being spread across
 * the page. Deliberately kept lean (only the eyebrow, supporting line
 * and two CTAs) — that's the point of this template: everything in one
 * compact card, not a longer page.
 *
 * The pill row below the CTAs comes from the admin's Hero
 * buttons config (Settings > On-screen text > Home hero buttons) —
 * deliberately NOT the top nav/page menu — falling back to the 3
 * homepage topic buttons only if no hero buttons are configured, so
 * the card never ends up with an empty pill row on a fresh install.
 */
export default function CenteredCardLayout({ home, heroButtons, lang, onCtaPrimary, onCtaSecondary, homeTopics, onTopicClick, headlineTypingSpeedCps }) {
  const resolvedHeroButtons = resolveHeroButtons(heroButtons, lang);
  const usingHeroButtons = resolvedHeroButtons.length > 0;

  return (
    <div className="hero-card-wrap">
      <div className="hero-card">
        <HeroEyebrow text={home.eyebrow} />
        <HeroHeadline statement={home.heroStatement} taglineLine1={home.taglineLine1} taglineLine2={home.taglineLine2} typingSpeedCps={headlineTypingSpeedCps} />
        <HeroSupportingText text={home.supportingText} />
        <HeroCtas primaryLabel={home.ctaPrimary} secondaryLabel={home.ctaSecondary} onPrimary={onCtaPrimary} onSecondary={onCtaSecondary} />

        {usingHeroButtons ? (
          <div className="hero-card-pills">
            {resolvedHeroButtons.map(({ key, label, url, external }) => (
              <a
                key={key}
                className="hero-card-pill"
                href={url}
                {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
              >
                {label}
              </a>
            ))}
          </div>
        ) : homeTopics.length > 0 && (
          <div className="hero-card-pills">
            {homeTopics.map(({ id, label }) => (
              <button key={id} className="hero-card-pill" onClick={() => onTopicClick(id)}>
                {label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
