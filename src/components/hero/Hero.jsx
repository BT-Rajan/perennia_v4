import { useLang } from "../../context/LangContext.jsx";
import TopBar from "../layout/TopBar.jsx";
import SiteFooter from "../layout/SiteFooter.jsx";
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
// handlers — only the arrangement of headline, tagline, CTAs and
// nav cards differs between them. None of them touch chat,
// booking, or voice functionality, which all live in ChatWidget.
const LAYOUTS = {
  classic: ClassicLayout,
  split: SplitLayout,
  "centered-card": CenteredCardLayout,
  editorial: EditorialLayout,
};

/**
 * Landing page. Entry into the chat assistant is either via a topic
 * card (which hands its preset question off to the sticky AI Assistant
 * widget — see onEnter/App.jsx) or via the always-visible sticky button
 * itself. Which arrangement the headline/tagline/CTAs/nav-cards render in is chosen by the admin (see
 * Settings > Theme > Homepage layout) — see LAYOUTS above.
 */
export default function Hero({ onEnter, onNavigate, onBookingClick }) {
  const { copy, sections, nav, branding, heroButtons, lang, theme, pages, features } = useLang();
  const home = copy.home;

  // Primary CTA opens the same booking panel as the sticky Appointments
  // button; with booking switched off it falls back to the Contact page
  // rather than disappearing. Secondary CTA goes to the products ("What
  // We Build") page, hidden only if an admin has removed that page.
  const handleCtaPrimary = features?.bookingEnabled && onBookingClick
    ? onBookingClick
    : () => onNavigate("contact");
  const handleCtaSecondary = pages?.products ? () => onNavigate("products") : null;
  // The JDK Factory ERP case-study teaser only links if that page exists.
  // The featured case study is whichever content page copy.home.case_page_slug
  // names (admin-editable); the teaser only links if that page exists.
  const handleOpenCaseStudy = home.casePageSlug && pages?.[home.casePageSlug] ? () => onNavigate(home.casePageSlug) : null;

  // The homepage situation cards (Starting Digital / Making AI
  // Practical / Scaling Technology) aren't page links — clicking one hands its preset question straight to the
  // AI Assistant.
  const homeTopics = home.situations || [];
  function handleTopicClick(topicId) {
    const topic = homeTopics.find((t) => t.id === topicId);
    if (topic) onEnter(topic.question);
  }

  const homeCapabilities = home.capabilities || [];
  const homeSectors = home.sectors || [];
  const homeLocalPoints = home.localPoints || [];
  const homeProcess = home.processSteps || [];
  const homeTrustPoints = home.trustPoints || [];
  const homeCaseStages = home.caseStages || [];
  const homeOtherWork = home.otherWork || [];

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

      <SiteFooter onNavigate={onNavigate} />
    </div>
  );
}
