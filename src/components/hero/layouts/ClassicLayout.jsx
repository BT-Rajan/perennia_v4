import { HeroButtons, HeroChatComposer, HeroCtas, HeroDiscovery, HeroEyebrow, HeroExamplePrompts, HeroHeadline, HeroLocal, HeroCapabilities, HeroProcess, HeroTrust, HeroWork, HeroSituations, HeroSupportingText } from "../HeroShared.jsx";

/**
 * "classic" — the site's original, and default, homepage body:
 * centered headline/tagline/quick-chat stacked above a grid of nav
 * cards. This is exactly the markup that existed before the layout
 * template setting did, so picking "classic" (or leaving the setting
 * unset) can never look different from what's already live.
 */
export default function ClassicLayout({ home, heroButtons, lang, quickDraft, setQuickDraft, onQuickSend, onExamplePick, onCtaPrimary, onCtaSecondary, copy, homeTopics, homeCapabilities, homeSectors, homeLocalPoints, homeProcess, homeTrustPoints, homeCaseStages, homeOtherWork, onOpenCaseStudy, onTopicClick, headlineTypingSpeedCps }) {
  return (
    <>
      <div className="hero-center">
        <HeroEyebrow text={home.eyebrow} />
        <HeroHeadline statement={home.heroStatement} taglineLine1={home.taglineLine1} taglineLine2={home.taglineLine2} typingSpeedCps={headlineTypingSpeedCps} />
        <HeroSupportingText text={home.supportingText} />
        <HeroCtas primaryLabel={home.ctaPrimary} secondaryLabel={home.ctaSecondary} onPrimary={onCtaPrimary} onSecondary={onCtaSecondary} />
        {heroButtons?.length > 0 && <HeroButtons buttons={heroButtons} lang={lang} />}

        <HeroChatComposer
          value={quickDraft}
          onChange={setQuickDraft}
          onSend={onQuickSend}
          placeholder={copy.chat.inputPlaceholder}
          sendLabel={copy.common.send}
          label={home.assistantLabel}
        />
        <HeroExamplePrompts prompts={home.examplePrompts} onPick={onExamplePick} />
      </div>

      <HeroSituations
        kicker={home.situationsKicker}
        heading={home.situationsHeading}
        intro={home.situationsIntro}
        topics={homeTopics}
        onTopicClick={onTopicClick}
        sectorsHeading={home.sectorsHeading}
        sectors={homeSectors}
        sectorsNote={home.sectorsNote}
        listClassName="hero-sections"
      />

      <HeroCapabilities
        heading={home.capabilitiesHeading}
        intro={home.capabilitiesIntro}
        items={homeCapabilities}
        roles={home.capabilitiesRoles}
        scopeNote={home.capabilitiesScopeNote}
      />

      <HeroLocal
        kicker={home.localKicker}
        heading={home.localHeading}
        intro={home.localIntro}
        points={homeLocalPoints}
      />

      <HeroProcess
        heading={home.processHeading}
        intro={home.processIntro}
        steps={homeProcess}
      />

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
      />

      <HeroTrust
        kicker={home.trustKicker}
        heading={home.trustHeading}
        intro={home.trustIntro}
        contrast={{ labelA: home.trustContrastLabelA, a: home.trustContrastA, labelB: home.trustContrastLabelB, b: home.trustContrastB }}
        points={homeTrustPoints}
        principles={home.principles}
      />

      <HeroDiscovery
        heading={home.discoveryHeading}
        body={home.discoveryBody}
        note={home.discoveryNote}
        ctas={<HeroCtas primaryLabel={home.ctaPrimary} secondaryLabel={home.ctaSecondary} onPrimary={onCtaPrimary} onSecondary={onCtaSecondary} />}
      />
    </>
  );
}
