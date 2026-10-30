# SEO — perennia.org and apps.perennia.org

Goal: rank organically (not ads) in Kuwait and the GCC for IT strategy,
software development, custom software, AI, AI implementation and
"AI company", in English and Arabic.

No one can guarantee a #1 position. Google ranks on relevance, content
quality, technical health and **authority** (links, Google Business
Profile, reviews, brand searches). The code now gives every page the
strongest technical and on-page footing it can have; the authority part
(section 4) is work outside the code, and in local markets it is often
what decides who is first. Expect movement over weeks and months, not
days. Never buy links or stuff keywords: both get sites demoted.

## 1. Keyword map

Each target phrase has one page that owns it, so pages don't compete.

| Search intent (EN / AR) | Page (EN / AR) | Title |
|---|---|---|
| AI company Kuwait, software company Kuwait, software & AI / شركة ذكاء اصطناعي، شركة برمجيات في الكويت | `/` · `/ar/` | AI & Custom Software Development Company in Kuwait |
| custom software development Kuwait, software development company, ERP development / تطوير برمجيات مخصصة في الكويت | `/software-development` · `/ar/software-development` | Custom Software Development Company in Kuwait |
| AI implementation, AI solutions, AI company Kuwait / تطبيق الذكاء الاصطناعي، شركة ذكاء اصطناعي في الكويت | `/ai-implementation` · `/ar/ai-implementation` | AI Implementation & AI Solutions Company in Kuwait |
| IT strategy, technology consulting Kuwait / استراتيجية تقنية المعلومات، استشارات تقنية | `/it-strategy` · `/ar/it-strategy` | IT Strategy & Technology Consulting in Kuwait |
| IT solutions Kuwait / حلول تقنية المعلومات في الكويت | `/services` · `/ar/services` | IT Solutions in Kuwait: Software, AI & IT Strategy |
| ERP case study, manufacturing ERP Kuwait | `/jdk-factory-erp` and apps.perennia.org | Manufacturing ERP Case Study, Kuwait |
| software / AI case studies | apps.perennia.org (`/`, `/ar/`) | Case Studies: Custom Software & AI Projects |

## 2. What the site now does (technical and on-page)

- **Every crawler sees each page's real content.** The server renders each URL's own title, description,
  canonical URL, `hreflang`, Open Graph/Twitter tags, structured data and the page text itself into the
  HTML (`backend/app/seo_render.py`). Before, every URL served the same shell with one generic title and no
  text. React takes over with the same content.
- **Arabic has its own URLs** (`/ar/...`), linked to the English pages with `hreflang` (en, ar, x-default),
  so Arabic searches in the GCC can return Arabic pages. The language switch moves between them.
- **Three keyword service pages, in English and Arabic**, with substantial, factual content (projects,
  timelines, process, local conventions) and a visible FAQ, marked up as `Service` and `FAQPage`.
- **Structured data:** `ProfessionalService` (Kuwait, serving the six GCC countries, topics, languages,
  phone, profiles), `WebSite`, `WebPage`, `BreadcrumbList`; `Article` for each case study on the apps site,
  tied to the same organization.
- **Internal links:** the header and footer menus are real links (they were buttons that crawlers can't
  follow); every page's footer links to the three service pages and the case studies; homepage capability
  cards link to their service pages; both sites link to each other in the same language.
- **Sitemaps** list every page in both languages with alternates (main: dynamic `/sitemap.xml`; apps:
  `sitemap.xml`); `robots.txt` points to them.
- **Correct status codes:** unknown URLs return 404 with `noindex`; caching and compression-friendly
  headers; PNG app icons for iOS/Android; mobile-friendly checks pass on every page.

## 3. Do these in the admin panel and consoles (first week)

1. **Google Search Console** (search.google.com/search-console): add `perennia.org` and `apps.perennia.org`,
   verify with the HTML-tag method, and paste the code in *Settings → SEO → Google Search Console
   verification code* (apps site: add the tag to `apps-site/source/build.py` or verify by DNS). Submit
   `https://perennia.org/sitemap.xml` and `https://apps.perennia.org/sitemap.xml`. Use *URL inspection →
   Request indexing* for `/`, `/ar/` and the six service pages.
2. **Bing Webmaster Tools** (also feeds DuckDuckGo, Yahoo and ChatGPT search): import from Search Console or
   paste the code in *Settings → SEO → Bing verification code*; submit both sitemaps.
3. **Settings → SEO → Official profiles:** add every real profile URL (LinkedIn company page, Google Business
   Profile, X, Instagram, Cogzidel's site if appropriate). This connects the site to the company in search.
4. **Settings → Contact:** set a business email and the street address in Kuwait. A full address
   strengthens local ranking (it appears in the structured data).
5. **Pages:** existing live pages got search titles/descriptions on deploy (only where empty). Review the
   *Search title* and *Search description* fields on each page; keep titles about 60 characters with the
   keyword first.
6. **Homepage headline (recommended):** the hero headline "Technology that moves your business forward."
   is the homepage `<h1>` and contains no search terms. Consider making the supporting line say what you are,
   e.g. *"Perennia is a Kuwait-based AI and custom software development company, helping GCC businesses
   adopt, build and scale technology — from IT strategy to practical AI."* (Settings → On-screen text →
   Home).
7. **Solutions page:** its live text predates the new pages. Add a "learn more" link under Technology, AI
   and Advisory to `/software-development`, `/ai-implementation` and `/it-strategy` (the bundled copy in
   `src/content/*/services.md` shows the wording), and consider a keyword-bearing heading such as
   "Software, AI and IT Strategy Solutions in Kuwait".

## 4. Authority — what usually decides #1 in Kuwait

1. **Google Business Profile** (business.google.com): create and verify "Perennia" in Kuwait, primary
   category *Software company*, secondary *Computer consultant* / *IT services*; add the website, phone,
   hours, services (the three service pages), photos and posts. Ask every client for a Google review.
   This drives the map pack for "software company Kuwait", which sits above organic results.
2. **Consistent name, address and phone (NAP)** everywhere the company is listed.
3. **Directories and listings:** Clutch, GoodFirms, DesignRush, Kuwait business directories (e.g. Kuwait
   Chamber of Commerce if a member, local yellow pages), LinkedIn company page.
4. **Links from real relationships:** ask clients (JDK, the consultancy, BBK, Zigora) for a link to their
   case study; Cogzidel's website linking to perennia.org; partner and vendor pages; university or
   incubator programmes.
5. **Content, steadily:** one useful article a month answering questions buyers search in English and
   Arabic (e.g. "ERP for manufacturers in Kuwait", "how to start with AI in a Kuwaiti SME", "custom software
   vs off-the-shelf"), each linking to the relevant service page. New case studies when projects launch.
6. **PR:** launches (Zigora), client wins and Labs releases in Kuwaiti and GCC tech/business media.

## 5. Measuring

- Search Console → *Performance*: impressions, clicks and average position for each target phrase, by
  country (Kuwait, Saudi Arabia, UAE, Qatar, Bahrain, Oman) and page; check monthly.
- Search Console → *Pages* and *Enhancements*: indexing and structured-data (FAQ, Breadcrumb) status.
- Track enquiries from the booking panel and chat as the business outcome.

## 6. Keeping it healthy

- Each new page: unique search title and description (admin fields), one clear heading, internal links to
  and from related pages, an Arabic version.
- Don't change URLs of ranking pages; if you must, ask a developer to add a redirect.
- Run the checks in `docs/PRODUCTION_CHECKLIST.md` after each deploy.
