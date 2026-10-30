"""
Server-rendered SEO for the public site.

The public site is a React single-page app, so without this every URL
would serve the same HTML shell: one title, one description, no page
text. Search engines that don't run JavaScript (and Google before it
renders) would see nothing to rank. For each request this module fills
in, in the page's own language:

- <head>: title, meta description, canonical URL, hreflang alternates,
  Open Graph / Twitter tags, search-engine verification tags and a
  JSON-LD graph (ProfessionalService serving Kuwait and the GCC,
  WebSite, WebPage, BreadcrumbList, Service for service pages, FAQPage
  from a page's visible FAQ);
- <body>: the page's real content (header links, heading, body,
  footer links) inside #root. React replaces it with the same content
  when it starts, so visitors and crawlers see the same thing.

URLs: English at /<slug>, Arabic at /ar/<slug> (home: / and /ar/).
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ContentPage
from app.settings_registry import get_def
from app.settings_service import get_setting

CONTENT_DIR = Path(__file__).resolve().parents[2] / "src" / "content"

# Footer legal pages always resolve, from the bundled copy if the DB
# hasn't got them yet (same rule as the frontend's LEGAL_PAGE_IDS).
ALWAYS_ROUTABLE_PAGES = ("privacy", "terms")
# Keyword service pages: linked from every page's footer and marked up
# as schema.org Services.
SERVICE_PAGES = ("software-development", "ai-implementation", "it-strategy")
CASE_STUDIES_URL = {"en": "https://apps.perennia.org/", "ar": "https://apps.perennia.org/ar/"}

GCC_COUNTRIES = ["Kuwait", "Saudi Arabia", "United Arab Emirates", "Qatar", "Bahrain", "Oman"]
KNOWS_ABOUT = [
    "Custom software development", "Software development", "ERP development", "Business software",
    "Artificial intelligence", "AI implementation", "AI assistants", "Generative AI",
    "IT strategy", "Technology consulting", "Business automation", "Digital transformation",
]
OG_LOCALE = {"en": "en_US", "ar": "ar_KW"}
FAQ_HEADING = re.compile(r"frequently asked questions|الأسئلة الشائعة", re.I)


# ── URLs ──────────────────────────────────────────────────────────────

def split_path(full_path: str, languages: list[str]) -> tuple[str, str]:
    """("ar/about" → ("ar", "about")), ("" → ("en", "")). Unprefixed
    paths are the default language."""
    parts = full_path.strip("/").split("/", 1)
    if parts[0] in languages and parts[0] != languages[0]:
        return parts[0], parts[1] if len(parts) > 1 else ""
    return languages[0], full_path.strip("/")


def page_path(lang: str, slug: str, default_lang: str) -> str:
    prefix = "" if lang == default_lang else f"/{lang}"
    return f"{prefix}/{quote(slug)}" if slug else (f"{prefix}/" if prefix else "/")


# ── Markdown (same subset as src/components/ui/Markdown.jsx) ─────────

def _inline(text: str) -> str:
    out = escape(text, quote=False)
    out = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{escape(m.group(2))}">{m.group(1)}</a>'
        if re.match(r"^(https?://|/)", m.group(2)) else m.group(1),
        out,
    )
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)


def _list(tag: str, lines: list[str], marker: str) -> str:
    items = "".join("<li>" + _inline(re.sub(marker, "", line)) + "</li>" for line in lines)
    return f"<{tag}>{items}</{tag}>"


def markdown_to_html(source: str, *, cta_label: str, cta_href: str) -> str:
    html = []
    for block in re.split(r"\n\s*\n", (source or "").strip()):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        first = lines[0]
        if m := re.match(r"^\[\[workflow:\s*(.+)\]\]$", first):
            stages = [s for s in re.split(r"\s*(?:→|->)\s*", m.group(1)) if s]
            html.append("<ol>" + "".join(f"<li>{escape(s)}</li>" for s in stages) + "</ol>")
        elif first == "[[cta]]":
            html.append(f'<p><a href="{escape(cta_href)}">{escape(cta_label)}</a></p>')
        elif m := re.match(r"^(#{1,3})\s+(.*)$", first):
            level = len(m.group(1))
            html.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            rest = "\n".join(lines[1:]).strip()
            if rest:
                html.append(f"<p>{_inline(rest)}</p>")
        elif first.startswith(">"):
            text = " ".join(re.sub(r"^>\s?", "", line) for line in lines)
            html.append(f"<blockquote><p>{_inline(text)}</p></blockquote>")
        elif re.match(r"^[-*]\s+", first):
            html.append(_list("ul", lines, r"^[-*]\s+"))
        elif re.match(r"^\d+\.\s+", first):
            html.append(_list("ol", lines, r"^\d+\.\s+"))
        elif m := re.match(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)$', first):
            if re.match(r"^(https?://|/)", m.group(2)):
                caption = f"<figcaption>{escape(m.group(3))}</figcaption>" if m.group(3) else ""
                html.append(f'<figure><img src="{escape(m.group(2))}" alt="{escape(m.group(1))}" loading="lazy">{caption}</figure>')
        else:
            html.append(f"<p>{_inline(' '.join(lines))}</p>")
    return "\n".join(html)


def extract_faq(source: str) -> list[tuple[str, str]]:
    """(question, answer) pairs from a page's visible FAQ: the "###"
    headings under a "## Frequently asked questions" section."""
    faq, in_faq, question, answer = [], False, None, []
    for block in re.split(r"\n\s*\n", source or ""):
        block = block.strip()
        if block.startswith("## "):
            if question:
                faq.append((question, " ".join(answer)))
                question, answer = None, []
            in_faq = bool(FAQ_HEADING.search(block))
        elif in_faq and block.startswith("### "):
            if question:
                faq.append((question, " ".join(answer)))
            question, answer = block[4:].strip(), []
        elif in_faq and question and block and not block.startswith("[["):
            answer.append(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", block).replace("**", ""))
    if question:
        faq.append((question, " ".join(answer)))
    return [(q, a) for q, a in faq if a]


# ── Data ──────────────────────────────────────────────────────────────

def _bundled_page(slug: str) -> dict | None:
    records = json.loads((CONTENT_DIR / "pages.json").read_text(encoding="utf-8"))
    record = next((r for r in records if r["slug"] == slug), None)
    if not record:
        return None
    translations = {}
    for lang, fields in record.items():
        if isinstance(fields, dict):
            md = CONTENT_DIR / lang / f"{slug}.md"
            translations[lang] = {**fields, "body_markdown": md.read_text(encoding="utf-8") if md.exists() else ""}
    return {"slug": slug, "show_in_nav": record["show_in_nav"], "translations": translations}


def _copy(db: Session, key: str, lang: str) -> dict:
    """A copy.* blob for one language, saved values over the defaults
    field by field (as the frontend does in siteContent.js)."""
    default = get_def(key).default
    saved = get_setting(db, key) or {}
    base = default.get(lang) or default.get("en") or {}
    return {**base, **{k: v for k, v in (saved.get(lang) or {}).items() if v not in (None, "")}}


def _i18n(value, lang: str, default_lang: str) -> str:
    if isinstance(value, dict):
        return value.get(lang) or value.get(default_lang) or next(iter(value.values()), "")
    return value or ""


class SiteContext:
    """Everything one render needs, loaded once per request."""

    def __init__(self, db: Session, base_url: str):
        self.base = base_url.rstrip("/")
        self.languages = get_setting(db, "locale.supported_languages") or ["en", "ar"]
        self.default_lang = self.languages[0]
        self.pages = {
            p.slug: {"slug": p.slug, "show_in_nav": p.show_in_nav, "translations": p.translations, "order": p.order}
            for p in db.scalars(select(ContentPage).where(ContentPage.is_visible.is_(True)).order_by(ContentPage.order))
        }
        for slug in ALWAYS_ROUTABLE_PAGES:
            if slug not in self.pages and (bundled := _bundled_page(slug)):
                self.pages[slug] = bundled
        self.db = db
        self.site_name = get_setting(db, "branding.site_name")
        self.meta_description = get_setting(db, "branding.meta_description")
        self.logo = get_setting(db, "branding.logo_url") or "/static/perennia-logo.png"
        self.phone = get_setting(db, "contact.phone") or ""
        self.email = get_setting(db, "contact.email") or ""
        self.same_as = [u for u in (get_setting(db, "seo.same_as") or []) if isinstance(u, str) and u.startswith("https://")]
        self.google_verification = get_setting(db, "seo.google_site_verification") or ""
        self.bing_verification = get_setting(db, "seo.bing_site_verification") or ""

    def url(self, lang: str, slug: str = "") -> str:
        return self.base + page_path(lang, slug, self.default_lang)

    def name(self, lang: str) -> str:
        return _i18n(self.site_name, lang, self.default_lang) or "Perennia"

    def tr(self, slug: str, lang: str) -> dict:
        translations = self.pages[slug]["translations"]
        return translations.get(lang) or translations.get(self.default_lang) or {}


# ── Rendering ─────────────────────────────────────────────────────────

def _jsonld(ctx: SiteContext, lang: str, slug: str, title: str, description: str, faq) -> str:
    org_id = f"{ctx.base}/#organization"
    page_url = ctx.url(lang, slug)
    organization = {
        "@type": "ProfessionalService",
        "@id": org_id,
        "name": ctx.name("en"),
        "alternateName": ctx.name("ar"),
        "url": f"{ctx.base}/",
        "logo": ctx.base + ctx.logo if ctx.logo.startswith("/") else ctx.logo,
        "image": f"{ctx.base}/static/og-image.png",
        "description": _i18n(ctx.meta_description, "en", ctx.default_lang),
        "slogan": "Practical AI. Affordable Innovation.",
        "address": {"@type": "PostalAddress", "addressCountry": "KW"},
        "areaServed": [{"@type": "Country", "name": c} for c in GCC_COUNTRIES],
        "knowsAbout": KNOWS_ABOUT,
        "knowsLanguage": ["en", "ar"],
    }
    if ctx.phone:
        organization["telephone"] = ctx.phone.replace(" ", "")
    if ctx.email:
        organization["email"] = ctx.email
    if ctx.same_as:
        organization["sameAs"] = ctx.same_as
    website = {
        "@type": "WebSite", "@id": f"{ctx.base}/#website", "url": f"{ctx.base}/",
        "name": ctx.name("en"), "inLanguage": ctx.languages, "publisher": {"@id": org_id},
    }
    crumbs = [{"@type": "ListItem", "position": 1, "name": ctx.name(lang), "item": ctx.url(lang)}]
    if slug:
        crumbs.append({"@type": "ListItem", "position": 2, "name": ctx.tr(slug, lang).get("nav_label") or title, "item": page_url})
    webpage = {
        "@type": "WebPage", "@id": f"{page_url}#webpage", "url": page_url, "name": title,
        "description": description, "inLanguage": lang, "isPartOf": {"@id": f"{ctx.base}/#website"},
        "about": {"@id": org_id}, "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": crumbs},
    }
    graph = [organization, website, webpage]
    if slug in SERVICE_PAGES:
        tr = ctx.tr(slug, lang)
        graph.append({
            "@type": "Service", "@id": f"{page_url}#service", "name": tr.get("section_title") or title,
            "serviceType": tr.get("nav_label") or title, "description": description, "url": page_url,
            "provider": {"@id": org_id}, "areaServed": [{"@type": "Country", "name": c} for c in GCC_COUNTRIES],
            "inLanguage": lang,
        })
    if faq:
        graph.append({
            "@type": "FAQPage", "@id": f"{page_url}#faq", "inLanguage": lang,
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq],
        })
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return data.replace("</", "<\\/")  # never let content close the <script>


def _head(ctx: SiteContext, lang: str, slug: str, title: str, description: str, faq, indexable: bool) -> str:
    url = ctx.url(lang, slug) if indexable else ctx.base + "/"
    e = lambda v: escape(v, quote=True)  # noqa: E731
    tags = [
        f"<title>{e(title)}</title>",
        f'<meta id="meta-description" name="description" content="{e(description)}" />',
        f'<link rel="canonical" href="{e(url)}" />',
        f'<meta name="robots" content="{"index, follow, max-image-preview:large" if indexable else "noindex"}" />',
    ]
    if indexable:
        tags += [f'<link rel="alternate" hreflang="{code}" href="{e(ctx.url(code, slug))}" />' for code in ctx.languages]
        tags.append(f'<link rel="alternate" hreflang="x-default" href="{e(ctx.url(ctx.default_lang, slug))}" />')
    image = f"{ctx.base}/static/og-image.png"
    tags += [
        '<meta property="og:type" content="website" />',
        f'<meta property="og:site_name" content="{e(ctx.name(lang))}" />',
        f'<meta property="og:locale" content="{OG_LOCALE.get(lang, lang)}" />',
        *[f'<meta property="og:locale:alternate" content="{OG_LOCALE.get(code, code)}" />' for code in ctx.languages if code != lang],
        f'<meta property="og:title" content="{e(title)}" />',
        f'<meta property="og:description" content="{e(description)}" />',
        f'<meta property="og:url" content="{e(url)}" />',
        f'<meta property="og:image" content="{e(image)}" />',
        '<meta property="og:image:width" content="1200" />',
        '<meta property="og:image:height" content="630" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{e(title)}" />',
        f'<meta name="twitter:description" content="{e(description)}" />',
        f'<meta name="twitter:image" content="{e(image)}" />',
        '<meta name="geo.region" content="KW" />',
    ]
    if ctx.google_verification:
        tags.append(f'<meta name="google-site-verification" content="{e(ctx.google_verification)}" />')
    if ctx.bing_verification:
        tags.append(f'<meta name="msvalidate.01" content="{e(ctx.bing_verification)}" />')
    tags.append(f'<script type="application/ld+json">{_jsonld(ctx, lang, slug, title, description, faq)}</script>')
    return "\n    ".join(tags)


def _home_body(ctx: SiteContext, lang: str, home: dict) -> str:
    def items(key, title_key="label", body_key="body"):
        return "".join(
            f"<li><strong>{escape(i.get(title_key, ''))}</strong> — {escape(i.get(body_key, '') or i.get('lead', ''))}</li>"
            for i in home.get(key) or [] if isinstance(i, dict)
        )
    service_links = "".join(
        f'<li><a href="{escape(ctx.url(lang, s))}">{escape(ctx.tr(s, lang).get("section_title", s))}</a> — '
        f'{escape(ctx.tr(s, lang).get("section_body", ""))}</li>'
        for s in SERVICE_PAGES if s in ctx.pages
    )
    case = home.get("case_page_slug")
    case_link = (f'<p><a href="{escape(ctx.url(lang, case))}">{escape(home.get("case_link", ""))}</a></p>'
                 if case in ctx.pages else "")
    return f"""<h1>{escape(home.get('tagline_line1', ''))} {escape(home.get('tagline_line2', ''))}</h1>
<p>{escape(home.get('supporting_text', ''))}</p>
<p><a href="{escape(ctx.url(lang, 'contact'))}">{escape(home.get('cta_primary', ''))}</a></p>
<h2>{escape(home.get('capabilities_heading', ''))}</h2>
<p>{escape(home.get('capabilities_intro', ''))}</p>
<ul>{items('capabilities')}</ul>
<ul>{service_links}</ul>
<h2>{escape(home.get('situations_heading', ''))}</h2>
<p>{escape(home.get('situations_intro', ''))}</p>
<ul>{items('situations')}</ul>
<h2>{escape(home.get('sectors_heading', ''))}</h2>
<ul>{items('sectors')}</ul>
<h2>{escape(home.get('process_heading', ''))}</h2>
<p>{escape(home.get('process_intro', ''))}</p>
<ol>{items('process_steps')}</ol>
<h2>{escape(home.get('work_heading', ''))}</h2>
<p>{escape(home.get('work_intro', ''))}</p>
<h3>{escape(home.get('case_heading', ''))}</h3>
<p>{escape(home.get('case_body', ''))}</p>
{case_link}
<ul>{items('other_work', 'label', 'built')}</ul>
<p><a href="{CASE_STUDIES_URL.get(lang, CASE_STUDIES_URL['en'])}">{escape(home.get('work_all_label', ''))}</a></p>
<h2>{escape(home.get('trust_heading', ''))}</h2>
<p>{escape(home.get('trust_intro', ''))}</p>
<ul>{items('trust_points')}</ul>
<h2>{escape(home.get('local_heading', ''))}</h2>
<p>{escape(home.get('local_intro', ''))}</p>
<ul>{items('local_points')}</ul>
<h2>{escape(home.get('discovery_heading', ''))}</h2>
<p>{escape(home.get('discovery_body', ''))}</p>"""


def _body(ctx: SiteContext, lang: str, slug: str, main_html: str, home: dict, common: dict) -> str:
    nav = [(p["translations"].get(lang, {}).get("nav_label") or s, ctx.url(lang, s))
           for s, p in ctx.pages.items() if p["show_in_nav"]]
    nav_html = "".join(f'<li><a href="{escape(u)}">{escape(label)}</a></li>' for label, u in nav)
    services = "".join(
        f'<li><a href="{escape(ctx.url(lang, s))}">{escape(ctx.tr(s, lang).get("nav_label", s))}</a></li>'
        for s in SERVICE_PAGES if s in ctx.pages
    )
    legal = "".join(
        f'<li><a href="{escape(ctx.url(lang, s))}">{escape(ctx.tr(s, lang).get("nav_label", s))}</a></li>'
        for s in ALWAYS_ROUTABLE_PAGES if s in ctx.pages
    )
    other = next((c for c in ctx.languages if c != lang), None)
    switch = (f'<li><a href="{escape(ctx.url(other, slug if slug in ctx.pages else ""))}" hreflang="{other}" lang="{other}">'
              f'{escape(home.get("lang_switch", other))}</a></li>') if other else ""
    phone = f'<li><a href="tel:{escape(ctx.phone.replace(" ", ""))}">{escape(ctx.phone)}</a></li>' if ctx.phone else ""
    logo = ctx.logo if ctx.logo.startswith(("/", "https://")) else "/static/perennia-logo.png"
    return f"""<div class="ssr-page">
<header><a href="{escape(ctx.url(lang))}"><img src="{escape(logo)}" alt="{escape(ctx.name(lang))}" width="160" height="40"></a>
<nav aria-label="{escape(common.get('primary_nav', ''))}"><ul><li><a href="{escape(ctx.url(lang))}">{escape(common.get('go_home', ''))}</a></li>{nav_html}{switch}</ul></nav></header>
<main>
{main_html}
</main>
<footer>
<p>{escape(ctx.name(lang))} — {escape(home.get('eyebrow', ''))}</p>
<nav aria-label="{escape(common.get('footer_services', ''))}"><h2>{escape(common.get('footer_services', ''))}</h2><ul>{services}<li><a href="{CASE_STUDIES_URL.get(lang, CASE_STUDIES_URL['en'])}">{escape(common.get('footer_case_studies', ''))}</a></li></ul></nav>
<nav aria-label="{escape(common.get('footer_explore', ''))}"><h2>{escape(common.get('footer_explore', ''))}</h2><ul>{nav_html}</ul></nav>
<h2>{escape(common.get('footer_contact', ''))}</h2><ul>{phone}</ul>
<ul>{legal}</ul>
</footer>
</div>"""


def render(index_html: str, *, db: Session, base_url: str, full_path: str) -> tuple[str, int]:
    """The SPA shell for full_path with its SEO head and content filled
    in. Returns (html, status): 404 (noindex, homepage content) for an
    unknown page."""
    ctx = SiteContext(db, base_url)
    lang, slug = split_path(full_path, ctx.languages)
    known = not slug or slug in ctx.pages
    if not known:
        slug = ""
    home = _copy(db, "copy.home", lang)
    common = _copy(db, "copy.common", lang)
    cta_href = ctx.url(lang, "contact")

    if slug:
        tr = ctx.tr(slug, lang)
        body_md = tr.get("body_markdown", "")
        title = tr.get("seo_title") or f"{tr.get('section_title') or tr.get('nav_label') or slug} | {ctx.name(lang)}"
        description = tr.get("seo_description") or tr.get("section_body") or _i18n(ctx.meta_description, lang, ctx.default_lang)
        main_html = markdown_to_html(body_md, cta_label=home.get("cta_primary", ""), cta_href=cta_href)
        if not re.search(r"^#\s", body_md, re.M):
            heading = f"{tr.get('tagline_line1', '')}{tr.get('tagline_line2', '')}".strip() or tr.get("nav_label", slug)
            main_html = f"<h1>{escape(heading)}</h1>\n{main_html}"
        faq = extract_faq(body_md)
    else:
        title = home.get("seo_title") or ctx.name(lang)
        description = home.get("seo_description") or _i18n(ctx.meta_description, lang, ctx.default_lang)
        main_html = _home_body(ctx, lang, home)
        faq = []

    head = _head(ctx, lang, slug, title, description, faq, indexable=known)
    body = _body(ctx, lang, slug, main_html, home, common)
    html = re.sub(r"<!-- seo:head.*?<!-- /seo:head -->", lambda _: head, index_html, count=1, flags=re.S)
    html = html.replace('<div id="root"></div>', f'<div id="root">{body}</div>', 1)
    # The build uses relative asset paths (vite base "./"), which break
    # below the root (/ar/about would load /ar/assets/…). This server
    # always serves the site at the domain root, so make them absolute.
    html = re.sub(r'(\s(?:src|href)=")\./', r"\1/", html)
    html = re.sub(r'<html lang="[^"]*"', f'<html lang="{lang}" dir="{"rtl" if lang in ("ar", "he", "fa", "ur") else "ltr"}"', html, count=1)
    return html, 200 if known else 404
