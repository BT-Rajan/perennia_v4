# Production checklist — perennia.org and apps.perennia.org

One checklist for both sites, in the same sections and order, so each
check is answered for each site side by side.

**Last full run:** 30 Oct 2026, commit `57b60b4` on `claude/brave-goldberg-4ixzti`.

**How it was verified.** Both sites were run from this repo exactly as
production serves them: the public site and admin built with `npm run
build`, the FastAPI backend under `uvicorn` with a freshly seeded
database, and `apps-site/` from a static file server. Every page was then
loaded in Chromium (Playwright) in English and Arabic, at 1440 px and
390 px wide, and checked for HTTP status, title, description, canonical
URL, a single `<h1>`, language and direction, horizontal overflow,
broken or alt-less images, console errors and accessibility
(axe-core 4.10, WCAG 2 A/AA plus best practice). Every link and button
was then clicked and its landing page checked: 94 click-throughs, all
passing.

The live servers could not be reached from the environment that ran
these checks, so anything that depends on the real server (TLS, DNS,
nginx, server-only files, the database's current content) is marked
**Verify live** with the exact command to run, in the last section.

## Status key

| Mark | Meaning |
|---|---|
| ✅ | Passes; verified as described |
| 🔧 | Was failing; fixed in this pass and re-verified |
| ❌ | **Blocker**: fix before calling the site production-ready |
| ⚠️ | Open, recommended |
| 🔍 | Verify on the live server (command in section 11) |
| — | Not applicable to this site |

## Summary

**Blockers (❌)**
1. **Rotate every secret** that was in `backend/.env` before the path-traversal fix (1.2). Assume they were exposed.
2. **Upgrade the Python dependencies** that have published vulnerabilities (1.10).
3. **Replace the placeholder Privacy Policy and Terms of Use**, which are still marked draft in English and Arabic (4.1).
4. **Set up database backups.** The repo has none (10.3).
5. **Serve the demo applications over HTTPS** on proper hostnames, not `http://169.58.13.213:<port>` (1.11).

**Fixed in this pass (🔧)**: path traversal exposing `backend/.env`;
fake booking confirmations and chat replies when the API failed;
chat cut off after six messages; soft-404s; unknown API paths returning
HTML; HEAD 405; missing caching and security headers; missing `<h1>` on
four main-site pages and every apps-site page; the language choice not
remembered; the footer phone link; and the apps site's missing
canonical, share tags, favicon, sitemap, robots and 404 page.

---

## 1. Security

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 1.1 | No file outside the build is reachable over HTTP | 🔧 | 🔍 | `GET /static/..%2f..%2fbackend/.env` returned the secrets file through real uvicorn; fixed in `3602dba` and covered by `backend/tests/test_spa_path_traversal.py`. Apps: the webroot must contain only the published files; `install.sh` copies only `apps-site/`'s top-level files, never `source/`. |
| 1.2 | Secrets rotated after the traversal fix is deployed | ❌ | — | Regenerate `SECRET_KEY` (signs out all admins), change the MySQL `app_user` password and the admin password. Rotating `ENCRYPTION_KEY` makes stored secret settings unreadable, so re-enter them (LLM API key, SMTP password, WhatsApp/Google credentials) in the admin panel afterwards. |
| 1.3 | Production mode: `ENVIRONMENT=production`, `COOKIE_SECURE=true`, strong keys | 🔍 | — | The app refuses to start in production without `SECRET_KEY` (≥32 chars), `ENCRYPTION_KEY` and secure cookies (`backend/app/config.py`). A server installed with `--public-ip` / `--http-cookies` runs in **development** mode (API docs exposed, non-secure cookies). |
| 1.4 | HTTPS only, HTTP→HTTPS redirect, HSTS | 🔍 | 🔍 | The app sends HSTS in production only; nginx must redirect port 80. |
| 1.5 | Security headers | 🔧 | ⚠️ | Main: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` (microphone for chat voice only) and a CSP limited to `frame-ancestors`/`base-uri`/`object-src`/`form-action`; tested in `test_spa_routing.py`. A full `script-src` CSP is still open (⚠️). Apps: static files get no headers from the repo; add them in nginx (section 11). |
| 1.6 | Admin session: HttpOnly, Secure, SameSite cookie; CSRF; login rate limit | ✅ | — | `admin_auth.py` sets `httponly`, `secure`, `samesite=lax`; admin routers require CSRF; login limited to 5/minute. |
| 1.7 | API docs off in production | ✅ 🔍 | — | `docs_url=None` when production (`main.py`); confirm `/api/docs` is 404 live. |
| 1.8 | Bootstrap admin credentials file removed | 🔍 | — | `install.sh` writes `backend/ADMIN_CREDENTIALS.txt` (mode 600) on first install; it must be deleted once the password is stored. |
| 1.9 | Public endpoints rate-limited sensibly | 🔧 | — | Booking 6/hour, lookup 20/hour, login 5/minute. Chat used the booking limit, so a visitor was cut off after six messages; it now has `RATE_LIMIT_CHAT` (default 40/hour). |
| 1.10 | Dependencies free of known vulnerabilities | ❌ | — | `npm audit`: public site 0. Admin: 2 moderate (`react-router`, fix with `npm audit fix` in `admin/`, ⚠️). `pip-audit` on `backend/requirements.txt` reports issues in **fastapi 0.115.0 (starlette 0.38.6)**, **cryptography 43.0.1**, **python-multipart 0.0.9**, **pypdf 5.1.0**, **lxml 5.3.0** and **python-dotenv 1.0.1**. Upgrade, then re-run the backend tests and this checklist. |
| 1.11 | No internal infrastructure exposed | — | ❌ | The case studies link to `http://169.58.13.213:5252`, `:9007` and `:4173`: plain HTTP on the server's raw IP. Visitors see "Not secure", and it advertises open ports. Put each demo behind HTTPS on a subdomain (e.g. `zigora-demo.perennia.org`) and update the links in `apps-site/source/build.py`. |
| 1.12 | Secrets and runtime data not committed | ✅ | ✅ | `.env`, `dist/`, `ADMIN_CREDENTIALS.txt` and `ecosystem.config.cjs` are git-ignored. |

## 2. Server and HTTP

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 2.1 | Every page returns 200 | ✅ | ✅ | Main: 9 pages × EN/AR × 2 widths. Apps: 6 pages × 2 widths. |
| 2.2 | Unknown URL returns 404 | 🔧 | ✅ 🔍 | Main: was 200 for any path; now 404 with `noindex`, still showing the site. Apps: a generated `404.html` exists; nginx must use it (`error_page 404 /404.html;`). |
| 2.3 | Unknown API path returns a JSON 404 | 🔧 | — | `/api/<anything>` and `/admin/api/<anything>` returned the site's HTML with 200. |
| 2.4 | HEAD requests answered | 🔧 | 🔍 | `HEAD /` returned 405, which breaks some uptime monitors and link checkers. |
| 2.5 | Caching headers | 🔧 | 🔍 | Main: hashed `/assets` `max-age=31536000, immutable`; HTML `no-cache`; `/static` one day. Apps: set in nginx (section 11). |
| 2.6 | Compression (gzip or brotli) | 🔍 | 🔍 | uvicorn does not compress; nginx must. |
| 2.7 | One canonical host (`www` → apex) | 🔍 | — | |
| 2.8 | TLS certificate valid and auto-renewing | 🔍 | 🔍 | |
| 2.9 | Health endpoint | ✅ | — | `GET /api/health` → `{"status":"ok"}`; `install.sh` waits on it after deploy. |

## 3. SEO and link previews

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 3.1 | Unique `<title>` per page | ✅ ⚠️ | ✅ | All unique. ⚠️ Main-site titles use the page tagline ("What We Do · Perennia") while the page heading says "Solutions": consider titles that match the nav label. |
| 3.2 | Meta description per page | ✅ | ✅ | |
| 3.3 | Canonical URL | ✅ | 🔧 | Main: filled per request by the backend. Apps: added (`https://apps.perennia.org/<page>`); internal links use `/`, not `index.html`, so one page has one URL. |
| 3.4 | Exactly one `<h1>` per page | 🔧 | 🔧 | Main: Labs, JDK Factory ERP, Privacy and Terms had none; the tagline is now the `<h1>` when the page body has no `# ` heading. Apps: no page had one; each title is now the `<h1>`. |
| 3.5 | Open Graph / Twitter share tags with image | ✅ | 🔧 | Main share image 1200×630 (249 KB). Apps now use the same image. |
| 3.6 | `robots.txt` and `sitemap.xml` | ✅ | 🔧 | Main: generated per request from the visible pages (9 URLs). Apps: generated static files (6 URLs). Submit both sitemaps in Google Search Console (🔍). |
| 3.7 | Arabic content indexable | ⚠️ | 🔧 | Main: both languages share one URL; `?lang=ar` now opens any page in Arabic, but search engines still index English only. Separate URLs (e.g. `/ar/...`) plus `hreflang` remain a product decision. Apps: every page has an Arabic version under `/ar/` with `hreflang` en/ar/x-default, and the sitemap lists both. |
| 3.8 | Structured data | ✅ | ⚠️ | Main: JSON-LD Organization in `index.html`. Apps: none. |
| 3.9 | Favicon and app icons | ⚠️ | 🔧 | Main favicon ✅, but `apple-touch-icon` is an SVG (iOS ignores it) and the web manifest has only SVG icons: add 180×180, 192×192 and 512×512 PNGs. Apps: favicon added (shared with the main site). |

## 4. Content and copy

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 4.1 | Legal pages final | ❌ | — | `privacy.md` and `terms.md` (EN and AR) still start with "Placeholder — draft text" and contain `[DATE]`, `[CONTACT EMAIL]` and `[PLACEHOLDER]`. Google OAuth verification links to the privacy page. Apps link to the main site's legal pages. |
| 4.2 | No placeholder text elsewhere | ✅ | ✅ | Only the legal pages above. |
| 4.3 | Same names and facts on both sites | ✅ | ✅ | Shared copy in `src/content/*.json`; "JDK Factory ERP" and its workflow stages match on both sites. |
| 4.4 | Arabic version and language switch on every page | ✅ | 🔧 | Main: all 10 page types have the AR/EN switch at desktop and phone width; each switches fully to `lang="ar"` `dir="rtl"` and back, the choice is remembered, and `?lang=ar`/`?lang=en` selects it from a link. Apps: Arabic versions of all 7 pages (`apps-site/ar/`, content in `apps-site/source/content_ar.py`), each with an "AR \| عربي" / "EN \| English" switch to the same page in the other language; links to perennia.org keep the language. 28 page checks pass (7 pages × 2 languages × 2 widths). |
| 4.5 | Contact details consistent | ✅ ⚠️ | ✅ | Phone +965 9933 1344 on both. No contact email is configured (`contact.email`); the Contact page's Email bullet was removed in the repo. |
| 4.6 | Live database content matches the repo | 🔍 | — | The seed never overwrites existing rows, so the live site may still show older text: the Contact page's Email bullet, chat header "Perennia Assistant", the FAQ "book a consultation", and old Arabic Solutions/Products summaries. Edit them in the admin panel. |
| 4.7 | Copyright year current | ✅ | ✅ | Main computes it; apps take it from the build date (regenerate yearly). |

## 5. Links and navigation

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 5.1 | Header navigation | ✅ | ✅ | Main: Solutions, Work, Products, Labs, About, Contact, logo and Book clicked from Home, About, JDK Factory ERP and Privacy (31 checks); each lands on the right page and heading. Work scrolls to "Our work". Apps: Work returns to the index from every page. |
| 5.2 | Footer navigation and legal links | ✅ | 🔍 | Main: 8 footer links plus the phone link, all correct. Apps: footer links point to perennia.org (check live). |
| 5.3 | Booking entry points | ✅ | — | Header, hero, Solutions/Labs/JDK page buttons, Contact page and the floating calendar button all open the booking panel (10 checks). |
| 5.4 | Case-study links | ✅ | ✅ | Home "View Case Study" → `/jdk-factory-erp`; **new** "View all case studies" → `https://apps.perennia.org/` (new tab, EN and AR). Apps: card titles and "Read the case study" (10), Previous/Next on every page (10) and breadcrumbs (5) all land correctly. |
| 5.5 | In-page anchors | ✅ | ✅ | `#work` on both. |
| 5.6 | Internal links resolve | ✅ | ✅ | Every internal `href` returns 200. |
| 5.7 | External links | 🔍 | 🔍 | Not reachable from the test environment; list in section 11. |
| 5.8 | External links open safely in a new tab | ✅ | ✅ | `target="_blank"` with `noopener`/`noreferrer`. |
| 5.9 | Phone links dial correctly | 🔧 | ✅ | Main footer used `tel:+965 9933 1344` (spaces); now `tel:+96599331344`, like the Contact page. |
| 5.10 | Back button and deep links | ✅ | ✅ | Back after in-app navigation returns to the previous page; `/labs` loads directly. |
| 5.11 | Language switch | 🔧 | — | The AR/EN choice reverted to the browser language on every reload or new tab; it is now remembered (`localStorage`). Toggle → reload → still Arabic, verified. |
| 5.12 | Logo, header menu, chatbot and footer the same on every page, both languages, both sites | ✅ | 🔧 | Checked on all 9 main and 7 apps pages × EN/AR × 1440/390 px: each is identical across pages, and main and apps match. The apps site used a text logo, had no Home icon, **no menu at all on phones** and no chatbot; it now has the main site's logo image, Home icon, phone menu drawer (Home, sections, Book; closes on Escape) and floating AI Assistant + booking buttons, which open the main site's chat or booking (`?open=chat` / `?open=booking`) in the same language. |
| 5.13 | Mobile friendly | ✅ | 🔧 | Both sites at 390 px: no horizontal scroll, no text under 12 px (small labels were 11 px), every tap target at least 24 px (the apps footer links and the Contact page phone link were 15–17 px). |

## 6. Accessibility

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 6.1 | No serious or critical axe violations | ✅ | 🔧 | Main: none on any page, either language, either width. Apps: the breadcrumb link was distinguishable by colour alone (now underlined); now 0 violations on all 7 pages. |
| 6.2 | Moderate axe findings | ⚠️ | ✅ | Main homepage: `region` (3): the floating chat and booking buttons sit outside a landmark. |
| 6.3 | `lang` and `dir` correct | ✅ | ✅ | `en`/`ltr` and `ar`/`rtl`. |
| 6.4 | Images have alt text | ✅ | ✅ | No image without `alt` on any page. |
| 6.5 | Keyboard: visible focus, logical order, overlays closable | ✅ 🔍 | ✅ 🔍 | `:focus-visible` outlines in both stylesheets; do one manual tab-through of each site, including the booking panel and chat. |

## 7. Responsive and browsers

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 7.1 | No horizontal scroll at 390 px | ✅ | ✅ | Every page, both languages. |
| 7.2 | Desktop layout at 1440 px | ✅ | ✅ | |
| 7.3 | Real devices: iPhone Safari, Android Chrome | 🔍 | 🔍 | Includes the notch / safe areas and the chat's microphone permission. |

## 8. Performance

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 8.1 | JavaScript and CSS size | ✅ | ✅ | Main: 331 KB JS (102 KB gzipped), 66 KB CSS. Apps: one 17 KB stylesheet, no JS beyond a one-line video fallback. |
| 8.2 | Image weight | ⚠️ | — | Case-study screenshots are PNG at 82–124 KB each; WebP would roughly halve them. |
| 8.3 | Promo video size | — | 🔍 | `/promo/*.mp4` live only on the server; keep each under ~10 MB and check `preload="metadata"` behaves. |
| 8.4 | Fonts | ✅ | ✅ | Google Fonts with `display=swap`. |
| 8.5 | Lighthouse on the live site | 🔍 | 🔍 | Target ≥90 for Performance, Accessibility, Best Practices and SEO on mobile. |

## 9. Features

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 9.1 | Booking never reports a false success | 🔧 | — | On any failed request (rate limit, validation, server error, outage) the site showed **"You're booked! Confirmation code: PRN-…"** for an appointment that was never saved; lookups, cancels and reschedules were faked too, and failed slot requests showed invented times. Mocks now run only in development; production shows the real error. |
| 9.2 | Booking end to end | 🔍 | — | Book a real slot → confirmation email arrives → appears in admin → appears in the Google Calendar (if connected) → reschedule → cancel. Needs SMTP and calendar configured. |
| 9.3 | Chat opens and is labelled | ✅ | — | Opens from the floating button and the topic cards; status line and "Powered by" render (they were blank on a seeded install before the shared-copy fix). |
| 9.4 | Chat failure is honest | 🔧 | — | A failed message got "Someone from our team will follow up shortly" although nothing was sent; it now says the message couldn't be sent (EN/AR, admin-editable), verified with a forced 429. |
| 9.5 | Chat answers | 🔍 | — | Needs the LLM API key set in the admin panel; ask in EN and AR. |
| 9.6 | Admin dashboard | ✅ 🔍 | — | Builds and is served at `/admin`; log in live and check settings, pages, bookings. |
| 9.7 | Promo videos play | — | 🔍 | Not in the repo (served from `promo/` on the server). Locally each page shows its fallback message instead, as designed. |
| 9.8 | Demo applications reachable | — | 🔍 | See 1.11. |

## 10. Operations

| # | Check | perennia.org | apps.perennia.org | Evidence / action |
|---|---|---|---|---|
| 10.1 | Repeatable deploy | ✅ | ✅ | `install.sh` is idempotent: builds both frontends, migrates, seeds missing content, restarts pm2, health-checks, and copies the apps site. Regenerate the apps pages with `python3 apps-site/source/build.py` before deploying content changes. |
| 10.2 | Restart on reboot | 🔍 | — | Run `pm2 startup` once as the pm2 user; `install.sh` already runs `pm2 save`. |
| 10.3 | Database backups | ❌ | — | Nothing in the repo or installer. Schedule a nightly `mysqldump perennia4`, plus `backend/data/uploads/`, copied off the server, and test a restore. |
| 10.4 | Log rotation | ⚠️ | 🔍 | pm2 logs grow unbounded: `pm2 install pm2-logrotate`. |
| 10.5 | Uptime monitoring and alerts | ⚠️ | ⚠️ | Monitor `https://perennia.org/api/health` and `https://apps.perennia.org/`. |
| 10.6 | Rollback plan | ⚠️ | ⚠️ | Check out the previous commit and re-run `install.sh` (database changes are additive). Note the deployed commit, which `install.sh` prints. |
| 10.7 | Single backend worker | ✅ | — | Deliberate: scheduled jobs run in-process (`install.sh` comment). |
| 10.8 | Automated tests pass | ✅ | ✅ | Backend 70 passed (including new traversal, routing, caching and header tests); `oxlint` clean; public and admin builds succeed. |

## 11. Live verification

Run these against the real servers after deploying this branch. Each
line names the item it confirms.

```bash
# 1.1 traversal closed: must NOT print SECRET_KEY
curl -s 'https://perennia.org/static/..%2f..%2fbackend/.env' | grep -c SECRET_KEY
# 1.3 / 1.7 production mode: API docs must be 404
curl -s -o /dev/null -w '%{http_code}\n' https://perennia.org/api/docs
# 1.4 / 2.7 / 2.8 redirects and certificates
curl -sI http://perennia.org/ | grep -i '^location'
curl -sI https://www.perennia.org/ | grep -i '^location'
curl -sI http://apps.perennia.org/ | grep -i '^location'
echo | openssl s_client -connect perennia.org:443 -servername perennia.org 2>/dev/null | openssl x509 -noout -enddate
echo | openssl s_client -connect apps.perennia.org:443 -servername apps.perennia.org 2>/dev/null | openssl x509 -noout -enddate
# 1.5 headers (both sites)
curl -sI https://perennia.org/ | grep -iE 'strict-transport|content-security|permissions-policy|x-frame|x-content-type'
curl -sI https://apps.perennia.org/ | grep -iE 'strict-transport|content-security|x-frame|x-content-type|cache-control'
# 1.8 bootstrap credentials removed (on the server, in the repo checkout)
ls backend/ADMIN_CREDENTIALS.txt
# 2.2 / 2.3 / 2.4 status codes
curl -s -o /dev/null -w '%{http_code}\n' https://perennia.org/no-such-page
curl -s -o /dev/null -w '%{http_code}\n' https://perennia.org/api/no-such-endpoint
curl -s -o /dev/null -w '%{http_code}\n' https://apps.perennia.org/no-such-page.html
curl -sI https://perennia.org/ | head -1
# 2.5 / 2.6 caching and compression
curl -sI -H 'Accept-Encoding: gzip, br' "https://perennia.org/$(curl -s https://perennia.org/ | grep -o 'assets/[^"]*\.js' | head -1)" | grep -iE 'cache-control|content-encoding'
curl -sI -H 'Accept-Encoding: gzip, br' https://apps.perennia.org/style.css | grep -iE 'cache-control|content-encoding'
# 3.6 sitemaps and robots
curl -s https://perennia.org/robots.txt https://apps.perennia.org/robots.txt
curl -s https://perennia.org/sitemap.xml https://apps.perennia.org/sitemap.xml | grep -c '<loc>'
# 5.7 / 9.7 / 9.8 external links, promo videos, demos: every line should be 200 (or 301/302)
for u in https://apps.perennia.org/ https://github.com/perennia-kw https://playbbk.com/ \
  https://developers.google.com/terms/api-services-user-data-policy \
  https://apps.perennia.org/promo/zigora.mp4 https://apps.perennia.org/promo/bbk.mp4 \
  https://apps.perennia.org/promo/consultancy.mp4 https://apps.perennia.org/promo/jdk.mp4 \
  https://apps.perennia.org/promo/perennia.mp4 \
  http://169.58.13.213:5252/ http://169.58.13.213:9007/ http://169.58.13.213:4173/; do
  printf '%s %s\n' "$(curl -s -o /dev/null -m 15 -w '%{http_code}' "$u")" "$u"
done
```

### nginx snippet for apps.perennia.org (items 1.5, 2.2, 2.5, 2.6)

```nginx
error_page 404 /404.html;
location /ar/ { error_page 404 /ar/404.html; }
gzip on;
gzip_types text/css application/javascript image/svg+xml application/xml text/plain;
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header Referrer-Policy strict-origin-when-cross-origin always;
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
location ~* \.html$ { add_header Cache-Control "no-cache" always; }
location ~* \.(css|svg|mp4)$ { add_header Cache-Control "public, max-age=86400" always; }
```

`add_header` inside a `location` replaces the server-level ones, so if
you use the two `location` lines, repeat the security headers inside
them (or use the `headers-more` module).
