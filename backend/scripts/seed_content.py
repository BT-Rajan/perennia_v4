#!/usr/bin/env python3
"""
One-time content seed: reads the frontend's existing content (the
former source of truth, in ../src/content/*.md and the strings that
used to live in src/data/content.js / pages.js) and writes it into the
DB as the initial admin-editable content. After this runs, the DB rows
are authoritative — this script is what performs the migration, not
something the running app depends on.

Safe to re-run: skips any page/FAQ item/setting that already has a DB
override, so it never clobbers an admin's edits.

    python scripts/seed_content.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base, engine, session_scope
from app.models import ContentPage, FaqItem, SiteSetting
from app import content_service
from app.settings_registry import get_def
from app.settings_service import set_many

FRONTEND_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "content"

# nav_label / section_title / section_body / tagline_* hand-ported once
# here from the JS structures that used to hold them (NAV, SECTIONS,
# PAGE_META in src/data/content.js and pages.js). Full body copy is read
# directly from the .md files below rather than duplicated inline.
PAGE_META = {
    "about": {
        "en": {"nav_label": "About", "section_title": "About Perennia",
               "section_body": "Perennia is a Kuwait-based technology company. We help businesses adopt, build and scale technology — using AI where it makes business sense — from first conversation through to production support.",
               "tagline_line1": "Who We ", "tagline_line2": "Are", "tagline_sub": "PRACTICAL AI · AFFORDABLE INNOVATION"},
        "ar": {"nav_label": "من نحن", "section_title": "عن بيرينيا",
               "section_body": "بيرينيا شركة تقنية مقرّها الكويت. نساعد الشركات على تبنّي التقنية وبنائها وتوسيعها — مع استخدام الذكاء الاصطناعي حيث يكون منطقيًا للأعمال — من المحادثة الأولى وحتى الدعم في التشغيل.",
               "tagline_line1": "من ", "tagline_line2": "نحن", "tagline_sub": "ذكاء اصطناعي عملي · ابتكار في المتناول"},
    },
    "products": {
        "en": {"nav_label": "Products", "section_title": "Products",
               "section_body": "Business platforms, booking systems, automation workflows and AI assistants — tuned to how your team actually works.",
               "tagline_line1": "What We ", "tagline_line2": "Build", "tagline_sub": "PRODUCTS & PLATFORMS"},
        "ar": {"nav_label": "المنتجات", "section_title": "المنتجات",
               "section_body": "مساعدون بالذكاء الاصطناعي، وأتمتة سير العمل، ومنصات رقمية مخصصة — مبنية على تقنيات حديثة ومصممة لتناسب طريقة عمل فريقك.",
               "tagline_line1": "ماذا ", "tagline_line2": "نبني", "tagline_sub": "المنتجات والمنصات"},
    },
    "services": {
        "en": {"nav_label": "Solutions", "section_title": "Solutions",
               "section_body": "Technology, AI and Advisory — three connected capabilities, built around how your business actually works.",
               "tagline_line1": "What We ", "tagline_line2": "Do", "tagline_sub": "SOLUTIONS"},
        "ar": {"nav_label": "الحلول", "section_title": "الحلول",
               "section_body": "استشارات، وتصميم منتجات، وهندسة متكاملة. نندمج مع فريقك أو ننفذ المشروع بالكامل، وفق ما يناسب خطتك.",
               "tagline_line1": "ماذا ", "tagline_line2": "نقدّم", "tagline_sub": "الحلول"},
    },
    "contact": {
        "en": {"nav_label": "Contact", "section_title": "Contact Us",
               "section_body": "Ready to talk? Use \"Book a 30-Minute Discovery Meeting\" to pick a time directly, or start a chat below and our assistant will connect you with the right person.",
               "tagline_line1": "Let's ", "tagline_line2": "Talk", "tagline_sub": "GET IN TOUCH"},
        "ar": {"nav_label": "تواصل معنا", "section_title": "تواصل معنا",
               "section_body": "جاهز للتحدث؟ استخدم \"احجز اجتماعًا استكشافيًا لمدة 30 دقيقة\" لاختيار موعد مباشرة، أو ابدأ محادثة أدناه وسيقوم مساعدنا بتوصيلك بالشخص المناسب.",
               "tagline_line1": "لنتحدث", "tagline_line2": "", "tagline_sub": "تواصل معنا"},
    },
    "labs": {
        "en": {"nav_label": "Labs", "section_title": "Labs",
               "section_body": "Experiments and free AI utilities, kept separate from client work and products.",
               "tagline_line1": "Perennia ", "tagline_line2": "Labs", "tagline_sub": "EXPERIMENTS & OPEN WORK"},
        "ar": {"nav_label": "المختبر", "section_title": "المختبر",
               "section_body": "تجارب وأدوات ذكاء اصطناعي مجانية، منفصلة عن أعمال العملاء والمنتجات.",
               "tagline_line1": "مختبر ", "tagline_line2": "بيرينيا", "tagline_sub": "تجارب وأعمال مفتوحة"},
    },
    # Case study: reached from the homepage teaser, not the top nav (see
    # NOT_IN_NAV below). Its section_* fields are required by the page
    # schema but aren't shown anywhere while it stays out of the nav.
    "jdk-factory-erp": {
        "en": {"nav_label": "JDK Factory ERP", "section_title": "JDK Factory ERP",
               "section_body": "A manufacturing ERP built around one business's operational workflow.",
               "tagline_line1": "JDK Factory ", "tagline_line2": "ERP", "tagline_sub": "CASE STUDY · MANUFACTURING"},
        "ar": {"nav_label": "نظام ERP لمصنع JDK", "section_title": "نظام ERP لمصنع JDK",
               "section_body": "نظام ERP للتصنيع مبني حول سير العمل التشغيلي لشركة واحدة.",
               "tagline_line1": "نظام ERP ", "tagline_line2": "لمصنع JDK", "tagline_sub": "دراسة حالة · التصنيع"},
    },
}

NOT_IN_NAV = {"jdk-factory-erp"}

# Nav order for a fresh install: Solutions, Products, Labs, About,
# Contact ("Work" is injected client-side after Solutions — see
# withWorkNav in src/data/siteContent.js). Existing installs keep
# whatever order an admin has set.
PAGE_ORDER = ["services", "products", "labs", "about", "contact", "jdk-factory-erp"]

FAQ_SEED = [
    {"en": {"q": "What services does Perennia offer?",
            "a": "We help businesses adopt, build and scale technology: custom business software and automation, practical AI where it genuinely helps, and advisory — from the first discovery conversation through implementation and ongoing support."},
     "ar": {"q": "ما هي الخدمات التي تقدمها بيرينيا؟",
            "a": "نساعد الشركات على تبنّي التقنية وبنائها وتوسيعها: برمجيات أعمال مخصصة وأتمتة، وذكاء اصطناعي عملي حيث يفيد فعلًا، واستشارات — من محادثة الاستكشاف الأولى حتى التنفيذ والدعم المستمر."}},
    {"en": {"q": "How can I book a consultation?",
            "a": "Tap \"Book a 30-Minute Discovery Meeting\", choose a free slot, and you'll get an instant confirmation by email — no back-and-forth required."},
     "ar": {"q": "كيف يمكنني حجز استشارة؟",
            "a": "اضغط على \"احجز اجتماعًا استكشافيًا لمدة 30 دقيقة\"، اختر موعدًا متاحًا، وستحصل على تأكيد فوري عبر البريد الإلكتروني."}},
    {"en": {"q": "Do you support Arabic and English?",
            "a": "Yes — the whole experience, including this assistant, works fully in both English and Arabic with proper right-to-left layout."},
     "ar": {"q": "هل تدعمون اللغتين العربية والإنجليزية؟",
            "a": "نعم — التجربة بأكملها، بما في ذلك هذا المساعد، تعمل بالكامل باللغتين مع تخطيط صحيح من اليمين إلى اليسار."}},
    {"en": {"q": "Where are you located?",
            "a": "We're based in Kuwait and work with businesses across the GCC. We meet either virtually or in person — "
                 "ask during booking and we'll accommodate you."},
     "ar": {"q": "أين يقع مقركم؟",
            "a": "مقرّنا الكويت، ونعمل مع الشركات في دول الخليج. نلتقي افتراضيًا أو شخصيًا — أخبرنا أثناء الحجز "
                 "وسنوفر لك ما يناسبك."}},
]

# The homepage copy (text and lists) has one source: copy.home's
# registry default in app/settings_registry.py — seeding reads it
# rather than keeping a hand-synced duplicate here.
COPY_HOME = get_def("copy.home").default

COPY_CHAT = {
    "en": {"tagline_line1": "Practical AI. ", "tagline_line2": "Affordable Innovation.",
           "sub": "PRACTICAL AI · AFFORDABLE INNOVATION", "header": "Perennia Assistant",
           "book_btn": "Book a 30-Minute Discovery Meeting", "faq_title": "Quick Questions",
           "input_placeholder": "Type your message…",
           "welcome_msg": "Hello! I'm Perennia's AI assistant. Before we get started, may I know your name? "
                          "It helps us build a good relationship with you and follow up properly.",
           "lang_switch": "AR | عربي"},
    "ar": {"tagline_line1": "ذكاء اصطناعي عملي. ", "tagline_line2": "ابتكار في المتناول.",
           "sub": "ذكاء اصطناعي عملي · ابتكار في المتناول", "header": "مساعد بيرينيا",
           "book_btn": "احجز اجتماعًا استكشافيًا لمدة 30 دقيقة", "faq_title": "أسئلة سريعة",
           "input_placeholder": "اكتب رسالتك…",
           "welcome_msg": "مرحباً! أنا المساعد الذكي لبيرينيا. قبل أن نبدأ، هل لي أن أعرف اسمك؟ "
                          "هذا يساعدنا على بناء علاقة أفضل معك ومتابعة طلبك بشكل صحيح.",
           "lang_switch": "EN | English"},
}

COPY_BOOKING = {
    "en": {"title": "Book a 30-Minute Discovery Meeting",
           "subtitle": "A conversation about your business, the problem and the outcome you want. "
                       "Pick a time — we'll confirm by email.",
           "tab_new": "New Appointment", "tab_manage": "Manage Booking", "date": "Date",
           "slot": "Available times", "slot_empty": "Pick a date to see available times",
           "name": "Name", "email": "Email", "phone": "Phone (optional)",
           "service": "What are you interested in? (optional)", "notes": "Notes (optional)",
           "cancel": "Cancel", "confirm": "Confirm Booking", "lookup_id": "Appointment ID",
           "lookup_email": "Email used to book", "find_btn": "Find My Appointment",
           "cancel_appt": "Cancel Appointment", "reschedule": "Reschedule",
           "lookup_different": "Look up a different appointment", "new_date": "New date",
           "back": "Back", "confirm_new_time": "Confirm New Time",
           "success_new": "You're booked! Confirmation code: {id}. A confirmation email is on its way.",
           "success_cancel": "Your appointment has been cancelled.",
           "success_reschedule": "All set — your appointment is now on {date} at {time}.",
           "id_placeholder": "PRN-XXXXXXXX",
           "no_availability": "No availability that day — try another date.",
           "err_pick_date_slot": "Please pick a date and time.",
           "err_name": "Please enter your name.",
           "err_email": "Please enter a valid email.",
           "err_lookup_both": "Enter both the appointment ID and email.",
           "err_pick_new_date_slot": "Pick a new date and time.",
           "errors": {
               "slot_unavailable": "That time is no longer available — please pick another.",
               "notice_window_passed": "This is too close to the appointment time to make that change.",
               "not_found": "We couldn't find a matching appointment.",
               "invalid_email": "Please enter a valid email.",
               "invalid_name": "Please enter your name.",
               "invalid_date": "That date isn't valid.",
               "already_cancelled": "This appointment has already been cancelled.",
               "booking_disabled": "Booking is currently unavailable — please check back soon.",
               "generic": "Something went wrong — please try again.",
           }},
    "ar": {"title": "احجز اجتماعًا استكشافيًا لمدة 30 دقيقة",
           "subtitle": "محادثة حول أعمالك والمشكلة والنتيجة التي تريدها. اختر الوقت المناسب — "
                       "سنؤكد عبر البريد الإلكتروني.",
           "tab_new": "موعد جديد", "tab_manage": "إدارة الحجز", "date": "التاريخ",
           "slot": "الأوقات المتاحة", "slot_empty": "اختر تاريخًا لرؤية الأوقات المتاحة",
           "name": "الاسم", "email": "البريد الإلكتروني", "phone": "الهاتف (اختياري)",
           "service": "ما الذي يهمك؟ (اختياري)", "notes": "ملاحظات (اختياري)",
           "cancel": "إلغاء", "confirm": "تأكيد الحجز", "lookup_id": "رقم الموعد",
           "lookup_email": "البريد الإلكتروني المستخدم للحجز", "find_btn": "ابحث عن موعدي",
           "cancel_appt": "إلغاء الموعد", "reschedule": "إعادة الجدولة",
           "lookup_different": "البحث عن موعد آخر", "new_date": "تاريخ جديد",
           "back": "رجوع", "confirm_new_time": "تأكيد الوقت الجديد",
           "success_new": "تم الحجز! رمز التأكيد: {id}. بريد التأكيد في طريقه إليك.",
           "success_cancel": "تم إلغاء موعدك.",
           "success_reschedule": "تم! موعدك الآن في {date} الساعة {time}.",
           "id_placeholder": "PRN-XXXXXXXX",
           "no_availability": "لا توجد مواعيد متاحة في هذا اليوم — جرّب تاريخًا آخر.",
           "err_pick_date_slot": "يرجى اختيار تاريخ ووقت.",
           "err_name": "يرجى إدخال اسمك.",
           "err_email": "يرجى إدخال بريد إلكتروني صالح.",
           "err_lookup_both": "أدخل رقم الموعد والبريد الإلكتروني معًا.",
           "err_pick_new_date_slot": "اختر تاريخًا ووقتًا جديدين.",
           "errors": {
               "slot_unavailable": "لم يعد هذا الوقت متاحًا — يرجى اختيار وقت آخر.",
               "notice_window_passed": "الوقت المتبقي غير كافٍ لإجراء هذا التغيير.",
               "not_found": "لم نتمكن من العثور على موعد مطابق.",
               "invalid_email": "يرجى إدخال بريد إلكتروني صالح.",
               "invalid_name": "يرجى إدخال اسمك.",
               "invalid_date": "هذا التاريخ غير صالح.",
               "already_cancelled": "تم إلغاء هذا الموعد بالفعل.",
               "booking_disabled": "الحجز غير متاح حاليًا — يرجى المحاولة لاحقًا.",
               "generic": "حدث خطأ ما — يرجى المحاولة مرة أخرى.",
           }},
}


def _read_md(lang: str, slug: str) -> str:
    path = FRONTEND_CONTENT_DIR / lang / f"{slug}.md"
    if not path.exists():
        print(f"  WARNING: {path} not found, leaving body_markdown empty for {slug}/{lang}")
        return ""
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with session_scope() as db:
        # --- pages ---
        for order, slug in enumerate(PAGE_ORDER):
            per_lang = PAGE_META[slug]
            if db.get(ContentPage, slug) is not None:
                print(f"Page '{slug}' already exists — skipping.")
                continue
            translations = {
                lang: {**fields, "body_markdown": _read_md(lang, slug)}
                for lang, fields in per_lang.items()
            }
            content_service.upsert_page(db, slug, translations=translations, order=order,
                                         show_in_nav=slug not in NOT_IN_NAV,
                                         actor_id=None, actor_username="seed_script")
            print(f"Seeded page '{slug}'.")

        # --- FAQ ---
        if db.query(FaqItem).count() == 0:
            for order, translations in enumerate(FAQ_SEED):
                content_service.create_faq(db, translations=translations, order=order,
                                            actor_id=None, actor_username="seed_script")
            print(f"Seeded {len(FAQ_SEED)} FAQ items.")
        else:
            print("FAQ items already exist — skipping.")

        # --- copy blobs ---
        to_set = {}
        for key, value in (("copy.home", COPY_HOME), ("copy.chat", COPY_CHAT), ("copy.booking", COPY_BOOKING)):
            if db.get(SiteSetting, key) is None:
                to_set[key] = value
            else:
                print(f"Setting '{key}' already overridden — skipping.")
        if to_set:
            set_many(db, to_set, actor_id=None, actor_username="seed_script")
            print(f"Seeded copy blobs: {list(to_set)}.")


if __name__ == "__main__":
    main()
