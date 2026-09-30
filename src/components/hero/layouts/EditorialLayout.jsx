import { HeroButtons, HeroChatComposer, HeroCtas, HeroDiscovery, HeroEyebrow, HeroExamplePrompts, HeroHeadline, HeroLocal, HeroCapabilities, HeroProcess, HeroTrust, HeroWork, HeroSituations, HeroSupportingText } from "../HeroShared.jsx";

/**
 * "editorial" — a bigger, left-aligned headline and a narrower
 * quick-chat box beneath it, with page-navigation rendered as a
 * horizontal-scrolling strip of compact cards instead of a grid —
 * a more magazine/editorial feel than the centered classic layout.
 */
export default function EditorialLayout({ home, heroButtons, lang, quickDraft, setQuickDraft, onQuickSend, onExamplePick, onCtaPrimary, onCtaSecondary, copy, homeTopics, homeCapabilities, homeSectors, homeLocalPoints, homeProcess, homeTrustPoints, homeCaseStages, homeOtherWork, onOpenCaseStudy, onTopicClick, headlineTypingSpeedCps }) {
  return (
    <>
      <div className="hero-editorial-main">
        <HeroEyebrow text={home.eyebrow} className="hero-eyebrow-left" />
        <HeroHeadline
          statement={home.heroStatement}
          taglineLine1={home.taglineLine1}
          taglineLine2={home.taglineLine2}
          className="hero-welcome-left hero-welcome-editorial"
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
          className="hero-quick-chat-narrow"
        />
        <HeroExamplePrompts prompts={home.examplePrompts} onPick={onExamplePick} className="hero-example-prompts-left" />
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
        className="hero-block-start"
        listClassName="hero-editorial-strip"
        cardClassName="hero-section-compact"
      />

      <HeroCapabilities
        heading={home.capabilitiesHeading}
        intro={home.capabilitiesIntro}
        items={homeCapabilities}
        roles={home.capabilitiesRoles}
        scopeNote={home.capabilitiesScopeNote}
        className="hero-block-start"
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
        className="hero-block-start"
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
          imageSrc: "/static/case-studies/jdk-erp/sales-order.png",
          imageAlt: home.caseImageAlt,
        }}
        otherLabel={home.workOtherLabel}
        needLabel={home.workNeedLabel}
        builtLabel={home.workBuiltLabel}
        otherItems={homeOtherWork}
        className="hero-block-start"
      />

      <HeroTrust
        kicker={home.trustKicker}
        heading={home.trustHeading}
        intro={home.trustIntro}
        contrast={{ labelA: home.trustContrastLabelA, a: home.trustContrastA, labelB: home.trustContrastLabelB, b: home.trustContrastB }}
        points={homeTrustPoints}
        principles={home.principles}
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
