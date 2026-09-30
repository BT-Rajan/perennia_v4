import { useState } from "react";
import { useLang } from "../../context/LangContext.jsx";
import { COPY, HOME_CAPABILITIES, HOME_SECTORS, HOME_CASE_STAGES, HOME_OTHER_WORK, HOME_LOCAL_POINTS, HOME_PROCESS, HOME_TOPICS, HOME_TRUST_POINTS } from "../../data/content.js";
import TopBar from "../layout/TopBar.jsx";
import ClassicLayout from "./layouts/ClassicLayout.jsx";
import SplitLayout from "./layouts/SplitLayout.jsx";
import CenteredCardLayout from "./layouts/CenteredCardLayout.jsx";
import EditorialLayout from "./layouts/EditorialLayout.jsx";
import "./Hero.css";

// Keyed by theme.layout_template (see backend/app/settings_registry.py).
// "classic" is both the map's fallback and the default admin value, so
// an unset or unrecognized template can never fail to render — it
// just renders the site's original layout. Every layout receives the
// exact same props/data and calls the exact same onNavigate/onEnter
// handlers — only the arrangement of headline, tagline, quick-chat
// box, and nav cards differs between them. None of them touch chat,
// booking, or voice functionality, which all live in ChatWidget.
const LAYOUTS = {
  classic: ClassicLayout,
  split: SplitLayout,
  "centered-card": CenteredCardLayout,
  editorial: EditorialLayout,
};

/**
 * Landing page. Entry into the chat assistant is either straight from
 * the quick-start chat box (which hands the typed message off to the
 * sticky AI Assistant widget — see onEnter/App.jsx) or via the
 * always-visible sticky button itself. Which arrangement the headline/
 * tagline/quick-chat/nav-cards render in is chosen by the admin (see
 * Settings > Theme > Homepage layout) — see LAYOUTS above.
 */
// The new hero-hierarchy fields (heroStatement/taglineLine1/taglineLine2/
// supportingText/examplePrompts) live inside the same free-form
// copy.home JSON blob as the rest of the homepage text, so an admin
// who hasn't touched Settings > On-screen text yet simply won't have
// them in the live backend response. Falling back per-field (not
// per-object) to the bundled copy means a partially-configured
// copy.home still renders the full hierarchy instead of blank gaps.
function withHomeFallbacks(home, lang) {
  const fallback = COPY[lang]?.home ?? COPY.en.home;
  return {
    ...home,
    heroStatement: home.heroStatement ?? fallback.heroStatement,
    taglineLine1: home.taglineLine1 ?? fallback.taglineLine1,
    taglineLine2: home.taglineLine2 ?? fallback.taglineLine2,
    supportingText: home.supportingText ?? fallback.supportingText,
    examplePrompts: home.examplePrompts ?? fallback.examplePrompts,
    eyebrow: home.eyebrow ?? fallback.eyebrow,
    assistantLabel: home.assistantLabel ?? fallback.assistantLabel,
    ctaPrimary: home.ctaPrimary ?? fallback.ctaPrimary,
    ctaSecondary: home.ctaSecondary ?? fallback.ctaSecondary,
    principles: home.principles ?? fallback.principles,
    situationsKicker: home.situationsKicker ?? fallback.situationsKicker,
    situationsHeading: home.situationsHeading ?? fallback.situationsHeading,
    sectorsHeading: home.sectorsHeading ?? fallback.sectorsHeading,
    sectorsNote: home.sectorsNote ?? fallback.sectorsNote,
    situationsIntro: home.situationsIntro ?? fallback.situationsIntro,
    capabilitiesHeading: home.capabilitiesHeading ?? fallback.capabilitiesHeading,
    capabilitiesIntro: home.capabilitiesIntro ?? fallback.capabilitiesIntro,
    capabilitiesRoles: home.capabilitiesRoles ?? fallback.capabilitiesRoles,
    capabilitiesScopeNote: home.capabilitiesScopeNote ?? fallback.capabilitiesScopeNote,
    localKicker: home.localKicker ?? fallback.localKicker,
    localHeading: home.localHeading ?? fallback.localHeading,
    localIntro: home.localIntro ?? fallback.localIntro,
    processHeading: home.processHeading ?? fallback.processHeading,
    processIntro: home.processIntro ?? fallback.processIntro,
    workKicker: home.workKicker ?? fallback.workKicker,
    workHeading: home.workHeading ?? fallback.workHeading,
    workIntro: home.workIntro ?? fallback.workIntro,
    workOtherLabel: home.workOtherLabel ?? fallback.workOtherLabel,
    workNeedLabel: home.workNeedLabel ?? fallback.workNeedLabel,
    workBuiltLabel: home.workBuiltLabel ?? fallback.workBuiltLabel,
    caseKicker: home.caseKicker ?? fallback.caseKicker,
    caseHeading: home.caseHeading ?? fallback.caseHeading,
    caseBody: home.caseBody ?? fallback.caseBody,
    caseLink: home.caseLink ?? fallback.caseLink,
    caseImageAlt: home.caseImageAlt ?? fallback.caseImageAlt,
    trustKicker: home.trustKicker ?? fallback.trustKicker,
    trustHeading: home.trustHeading ?? fallback.trustHeading,
    trustIntro: home.trustIntro ?? fallback.trustIntro,
    trustContrastLabelA: home.trustContrastLabelA ?? fallback.trustContrastLabelA,
    trustContrastA: home.trustContrastA ?? fallback.trustContrastA,
    trustContrastLabelB: home.trustContrastLabelB ?? fallback.trustContrastLabelB,
    trustContrastB: home.trustContrastB ?? fallback.trustContrastB,
    discoveryHeading: home.discoveryHeading ?? fallback.discoveryHeading,
    discoveryBody: home.discoveryBody ?? fallback.discoveryBody,
    discoveryNote: home.discoveryNote ?? fallback.discoveryNote,
  };
}

export default function Hero({ onEnter, onNavigate, onBookingClick }) {
  const { copy, sections, nav, branding, heroButtons, lang, theme, pages, features } = useLang();
  const [quickDraft, setQuickDraft] = useState("");
  const home = withHomeFallbacks(copy.home, lang);

  function handleQuickSend() {
    const text = quickDraft.trim();
    if (!text) return;
    setQuickDraft("");
    onEnter(text);
  }

  // Same direct handoff to the AI Assistant as the topic buttons below
  // — an example prompt is a suggestion, not text the visitor typed,
  // so it skips the quick-chat draft state entirely.
  function handleExamplePick(prompt) {
    onEnter(prompt);
  }

  // Primary CTA opens the same booking panel as the sticky Appointments
  // button; with booking switched off it falls back to the Contact page
  // rather than disappearing. Secondary CTA goes to the products ("What
  // We Build") page, hidden only if an admin has removed that page.
  const handleCtaPrimary = features?.bookingEnabled && onBookingClick
    ? onBookingClick
    : () => onNavigate("contact");
  const handleCtaSecondary = pages?.products ? () => onNavigate("products") : null;
  // The JDK Factory ERP case-study teaser only links if that page exists.
  const handleOpenCaseStudy = pages?.["jdk-factory-erp"] ? () => onNavigate("jdk-factory-erp") : null;

  // The homepage situation cards (Starting Digital / Making AI
  // Practical / Scaling Technology) aren't page links — clicking one hands its preset question straight to the
  // AI Assistant, the same handoff the quick-chat box uses above.
  const homeTopics = HOME_TOPICS[lang] || HOME_TOPICS.en;
  function handleTopicClick(topicId) {
    const topic = homeTopics.find((t) => t.id === topicId);
    if (topic) onEnter(topic.question);
  }

  const homeCapabilities = HOME_CAPABILITIES[lang] || HOME_CAPABILITIES.en;
  const homeSectors = HOME_SECTORS[lang] || HOME_SECTORS.en;
  const homeLocalPoints = HOME_LOCAL_POINTS[lang] || HOME_LOCAL_POINTS.en;
  const homeProcess = HOME_PROCESS[lang] || HOME_PROCESS.en;
  const homeTrustPoints = HOME_TRUST_POINTS[lang] || HOME_TRUST_POINTS.en;
  const homeCaseStages = HOME_CASE_STAGES[lang] || HOME_CASE_STAGES.en;
  const homeOtherWork = HOME_OTHER_WORK[lang] || HOME_OTHER_WORK.en;

  const Layout = LAYOUTS[theme?.layoutTemplate] || ClassicLayout;

  return (
    <div className="hero-page">
      <TopBar onNavigate={onNavigate} onBook={handleCtaPrimary} />

      <Layout
        copy={copy}
        home={home}
        sections={sections}
        nav={nav}
        heroButtons={heroButtons}
        lang={lang}
        onNavigate={onNavigate}
        quickDraft={quickDraft}
        setQuickDraft={setQuickDraft}
        onQuickSend={handleQuickSend}
        onExamplePick={handleExamplePick}
        onCtaPrimary={handleCtaPrimary}
        onCtaSecondary={handleCtaSecondary}
        headlineStyle={theme?.headlineStyle}
        headlineTypingSpeedCps={theme?.headlineTypingSpeedCps}
        branding={branding}
        homeTopics={homeTopics}
        homeCapabilities={homeCapabilities}
        homeSectors={homeSectors}
        homeLocalPoints={homeLocalPoints}
        homeProcess={homeProcess}
        homeTrustPoints={homeTrustPoints}
        homeCaseStages={homeCaseStages}
        homeOtherWork={homeOtherWork}
        onOpenCaseStudy={handleOpenCaseStudy}
        onTopicClick={handleTopicClick}
      />

      <footer className="hero-footer">© {new Date().getFullYear()} {branding.siteName}</footer>
    </div>
  );
}
