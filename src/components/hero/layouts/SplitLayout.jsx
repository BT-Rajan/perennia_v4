import { HeroButtons, HeroCapabilities, HeroProcess, HeroChatComposer, HeroCtas, HeroDiscovery, HeroEyebrow, HeroExamplePrompts, HeroHeadline, HeroLocal, HeroTrust, HeroWork, HeroSituations, HeroSupportingText } from "../HeroShared.jsx";

/**
 * "split" — two-column: headline, tagline, and the quick-chat box
 * left-aligned on one side, page-navigation cards stacked as a list
 * on the other. Stacks to a single column (main content first, then
 * nav) below the tablet breakpoint — see .hero-split-* in Hero.css.
 */
export default function SplitLayout({ home, heroButtons, lang, quickDraft, setQuickDraft, onQuickSend, onExamplePick, onCtaPrimary, onCtaSecondary, copy, homeTopics, homeCapabilities, homeSectors, homeLocalPoints, homeProcess, homeTrustPoints, homeCaseStages, homeOtherWork, onOpenCaseStudy, onTopicClick, headlineTypingSpeedCps }) {
  return (
    <>
      <div className="hero-split-wrap">
        <div className="hero-split-main">
          <HeroEyebrow text={home.eyebrow} className="hero-eyebrow-left" />
          <HeroHeadline
            statement={home.heroStatement}
            taglineLine1={home.taglineLine1}
            taglineLine2={home.taglineLine2}
            className="hero-welcome-left"
            typingSpeedCps={headlineTypingSpeedCps}
          />
          <HeroSupportingText text={home.supportingText} className="hero-supporting-left" />
          <HeroCtas primaryLabel={home.ctaPrimary} secondaryLabel={home.ctaSecondary} onPrimary={onCtaPrimary} onSecondary={onCtaSecondary} className="hero-ctas-left" />
          {heroButtons?.length > 0 && <HeroButtons buttons={heroButtons} lang={lang} />}

          <HeroChatComposer
            value={quickDraft}
            onChange={setQuickDraft}
            onSend={onQuickSend}
            placeholder={copy.chat.inputPlaceholder}
            sendLabel={copy.common.send}
            label={home.assistantLabel}
          />
          <HeroExamplePrompts prompts={home.examplePrompts} onPick={onExamplePick} className="hero-example-prompts-left" />
        </div>

        {/* No section CTA here — this column sits right beside the hero's
            own CTAs, so a second booking button would just repeat them. */}
        <HeroSituations
          kicker={home.situationsKicker}
          heading={home.situationsHeading}
          intro={home.situationsIntro}
          topics={homeTopics}
          onTopicClick={onTopicClick}
          sectorsHeading={home.sectorsHeading}
          sectors={homeSectors}
          sectorsNote={home.sectorsNote}
          className="hero-situations-aside hero-block-start"
          listClassName="hero-split-nav"
          cardClassName="hero-section-row"
        />
      </div>

      <HeroCapabilities
        heading={home.capabilitiesHeading}
        intro={home.capabilitiesIntro}
        items={homeCapabilities}
        roles={home.capabilitiesRoles}
        scopeNote={home.capabilitiesScopeNote}
        className="hero-block-start"
      />

      <HeroProcess
        heading={home.processHeading}
        intro={home.processIntro}
        steps={homeProcess}
        className="hero-block-start"
      />

      <HeroTrust
        kicker={home.trustKicker}
        heading={home.trustHeading}
        intro={home.trustIntro}
        contrast={{ labelA: home.trustContrastLabelA, a: home.trustContrastA, labelB: home.trustContrastLabelB, b: home.trustContrastB }}
        points={homeTrustPoints}
        className="hero-block-start"
      >
        <HeroLocal
          kicker={home.localKicker}
          heading={home.localHeading}
          intro={home.localIntro}
          points={homeLocalPoints}
        />
      </HeroTrust>

      <HeroWork
        kicker={home.workKicker}
        heading={home.workHeading}
        intro={home.workIntro}
        featured={{
          kicker: home.caseKicker,
          heading: home.caseHeading,
          body: home.caseBody,
          stages: homeCaseStages,
          linkLabel: home.caseLink,
          onOpen: onOpenCaseStudy,
          imageSrc: home.caseImageUrl,
          imageAlt: home.caseImageAlt,
        }}
        otherLabel={home.workOtherLabel}
        needLabel={home.workNeedLabel}
        builtLabel={home.workBuiltLabel}
        otherItems={homeOtherWork}
        className="hero-block-start"
      />

      <HeroDiscovery
        heading={home.discoveryHeading}
        body={home.discoveryBody}
        note={home.discoveryNote}
        ctas={<HeroCtas primaryLabel={home.ctaPrimary} secondaryLabel={home.ctaSecondary} onPrimary={onCtaPrimary} onSecondary={onCtaSecondary} className="hero-ctas-left" />}
        className="hero-block-start"
      />
    </>
  );
}
