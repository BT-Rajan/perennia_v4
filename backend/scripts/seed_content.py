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
from app.settings_service import set_many

FRONTEND_CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "content"

# nav_label / section_title / section_body / tagline_* hand-ported once
# here from the JS structures that used to hold them (NAV, SECTIONS,
# PAGE_META in src/data/content.js and pages.js). Full body copy is read
# directly from the .md files below rather than duplicated inline.
PAGE_META = {
    "about": {
        "en": {"nav_label": "About", "section_title": "About Perennia",
               "section_body": "Perennia is an AI-powered technology and innovation company. We partner with businesses to design, build, and operate intelligent products — from first concept through to production support.",
               "tagline_line1": "Who We ", "tagline_line2": "Are", "tagline_sub": "AI-POWERED TECHNOLOGY & INNOVATION"},
        "ar": {"nav_label": "من نحن", "section_title": "عن بيرينيا",
               "section_body": "بيرينيا شركة تقنية وابتكار مدعومة بالذكاء الاصطناعي. نتعاون مع الشركات لتصميم وبناء وتشغيل منتجات ذكية — من الفكرة الأولى وحتى الدعم الإنتاجي.",
               "tagline_line1": "من ", "tagline_line2": "نحن", "tagline_sub": "تقنية وابتكار مدعومان بالذكاء الاصطناعي"},
    },
    "products": {
        "en": {"nav_label": "Products", "section_title": "Products",
               "section_body": "AI assistants, automation workflows, and custom digital platforms — built on modern stacks and tuned to how your team actually works.",
               "tagline_line1": "What We ", "tagline_line2": "Build", "tagline_sub": "PRODUCTS & PLATFORMS"},
        "ar": {"nav_label": "المنتجات", "section_title": "المنتجات",
               "section_body": "مساعدون بالذكاء الاصطناعي، وأتمتة سير العمل، ومنصات رقمية مخصصة — مبنية على تقنيات حديثة ومصممة لتناسب طريقة عمل فريقك.",
               "tagline_line1": "ماذا ", "tagline_line2": "نبني", "tagline_sub": "المنتجات والمنصات"},
    },
    "services": {
        "en": {"nav_label": "Solutions", "section_title": "Solutions",
               "section_body": "Consulting, product design, and full-cycle engineering. We embed with your team or run the build end-to-end, whichever fits your roadmap.",
               "tagline_line1": "What We ", "tagline_line2": "Do", "tagline_sub": "SOLUTIONS"},
        "ar": {"nav_label": "الحلول", "section_title": "الحلول",
               "section_body": "استشارات، وتصميم منتجات، وهندسة متكاملة. نندمج مع فريقك أو ننفذ المشروع بالكامل، وفق ما يناسب خطتك.",
               "tagline_line1": "ماذا ", "tagline_line2": "نقدّم", "tagline_sub": "الحلول"},
    },
    "contact": {
        "en": {"nav_label": "Contact Us", "section_title": "Contact Us",
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
            "a": "We build AI-powered assistants, automation, and digital products tailored to your business — from concept through to production support."},
     "ar": {"q": "ما هي الخدمات التي تقدمها بيرينيا؟",
            "a": "نصمم مساعدين مدعومين بالذكاء الاصطناعي وحلول أتمتة ومنتجات رقمية مخصصة لعملك — من الفكرة وحتى الدعم الإنتاجي."}},
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

# Must stay in sync with copy.home's default in settings_registry.py —
# get_setting() only merges copy.home at the top level (per-language,
# not per-field), so a DB row missing a field here would silently drop
# that field out of the live response rather than falling through to
# the registry default. See withHomeFallbacks in Hero.jsx for the
# frontend-side safety net this is meant to make unnecessary.
COPY_HOME = {
    "en": {"welcome": "Welcome to Perennia", "tagline": "Visit our V-Lounge for more",
           "hero_statement": "", "eyebrow": "Practical AI. Affordable Innovation.",
           "assistant_label": "Try the bilingual assistant we built — the same kind of tool we build for clients.",
           "tagline_line1": "Technology that moves", "tagline_line2": "your business forward.",
           "supporting_text": "Perennia helps GCC businesses adopt, build and scale technology — from their "
                              "first digital initiative to practical AI and larger-scale transformation.",
           "cta_primary": "Book a 30-Minute Discovery Meeting", "cta_secondary": "Explore What We Build",
           "situations_kicker": "Who we work with",
           "situations_heading": "Technology should fit the business — not force the business into a template.",
           "situations_intro": "We work with SMEs in Kuwait and the wider GCC, typically organisations of around 100 to 500 people. "
                               "Whatever stage your business is at, we help you adopt technology reliably, practically and with a clear path forward.",
           "sectors_heading": "Businesses we understand particularly well",
           "sectors_note": "Not in one of these? The approach is the same: understand how your business works, then build the technology around it.",
           "work_kicker": "Our work",
           "work_heading": "Different businesses have different technology problems.",
           "work_intro": "We understand the problem first, then build the appropriate solution — "
                         "from a factory's complete operation to a sales team in the field.",
           "work_other_label": "Other work",
           "work_need_label": "The need",
           "work_built_label": "What we built",
           "case_kicker": "Featured work",
           "case_heading": "JDK Factory ERP: one system around a manufacturing workflow.",
           "case_body": "We mapped how a manufacturing business actually runs — "
                        "from sales and feasibility through procurement, production, delivery and payment — and built its ERP around that workflow.",
           "case_link": "Read the case study",
           "case_image_alt": "The completed sales order in JDK Factory ERP, linked to its quotation, finance record and deliveries",
           "trust_kicker": "What sets Perennia apart",
           "trust_heading": "Reliable technology induction for your business.",
           "trust_intro": "Technology only creates value when it works in the real business. Building software is one part of that — "
                          "we focus on the complete journey, from understanding the business through implementation, adoption and change.",
           "trust_contrast_label_a": "Software delivery",
           "trust_contrast_a": "“We can build software.”",
           "trust_contrast_label_b": "Technology induction",
           "trust_contrast_b": "“We can help you introduce technology into your business reliably.”",
           "discovery_heading": "Let's understand the problem before deciding what to build.",
           "discovery_body": "In 30 minutes we look at your business, your current process or problem, "
                             "the outcome you want, whether technology can help — and what the sensible "
                             "next step is.",
           "discovery_note": "A working conversation, not a sales pitch — no solution or price is committed in the meeting.",
           "capabilities_heading": "Three capabilities. One technology partner.",
           "capabilities_intro": "Understand the business. Decide what technology is needed. Build it. "
                                 "Put it into operation. Help the business adapt.",
           "capabilities_roles": "Work with us as an advisor, an implementation partner, a software builder, "
                                 "an AI implementation partner — or a combination of these.",
           "capabilities_scope_note": "Scope and investment are agreed once we understand your requirements.",
           "local_kicker": "Kuwait and the GCC",
           "local_heading": "Technology built with your business environment in mind.",
           "local_intro": "Perennia combines technology expertise with practical understanding of how businesses operate in Kuwait and the wider GCC.",
           "process_heading": "Start with the business. Build the technology around it.",
           "process_intro": "We normally take responsibility for the whole journey — from the first conversation "
                            "to the solution in operation — so you are not left coordinating several vendors.",
           "principles": ["Practical AI, not fashionable AI",
                          "Experienced technology professionals",
                          "Transparent scope and investment"],
           "example_prompts": ["Where should my business start with technology?",
                                "Where could AI genuinely help my business?",
                                "What happens in a discovery meeting?"],
           "hint": "Start chatting", "lang_switch": "AR | عربي"},
    "ar": {"welcome": "مرحبا بك في بيرينيا", "tagline": "زوروا V-Lounge الخاص بنا لمزيد من المعلومات",
           "hero_statement": "", "eyebrow": "ذكاء اصطناعي عملي. ابتكار في المتناول.",
           "assistant_label": "جرّب المساعد ثنائي اللغة الذي بنيناه — من نوع الأدوات التي نبنيها لعملائنا.",
           "tagline_line1": "تقنية تدفع", "tagline_line2": "أعمالك إلى الأمام.",
           "supporting_text": "تساعد بيرينيا الشركات في دول الخليج على تبنّي التقنية وبنائها وتوسيعها — من أول "
                              "مبادرة رقمية إلى الذكاء الاصطناعي العملي والتحول على نطاق أوسع.",
           "cta_primary": "احجز اجتماعًا استكشافيًا لمدة 30 دقيقة", "cta_secondary": "استكشف ما نبنيه",
           "situations_kicker": "مع من نعمل",
           "situations_heading": "يجب أن تناسب التقنية الأعمال — لا أن تُجبر الأعمال على قالب جاهز.",
           "situations_intro": "نعمل مع الشركات الصغيرة والمتوسطة في الكويت ودول الخليج، وعادةً ما تضم نحو 100 إلى 500 موظف. "
                               "أيًّا كانت المرحلة التي تمر بها أعمالك، نساعدك على تبنّي التقنية بشكل موثوق وعملي، مع مسار واضح للمضي قدمًا.",
           "sectors_heading": "أعمال نفهمها جيدًا بشكل خاص",
           "sectors_note": "لست ضمن هذه القطاعات؟ النهج نفسه: نفهم طريقة عمل أعمالك، ثم نبني التقنية حولها.",
           "work_kicker": "أعمالنا",
           "work_heading": "لكل عمل مشكلاته التقنية الخاصة.",
           "work_intro": "نفهم المشكلة أولًا، ثم نبني الحل المناسب — "
                         "من التشغيل الكامل لمصنع إلى فريق مبيعات في الميدان.",
           "work_other_label": "أعمال أخرى",
           "work_need_label": "الحاجة",
           "work_built_label": "ما بنيناه",
           "case_kicker": "عمل مميز",
           "case_heading": "نظام ERP لمصنع JDK: نظام واحد حول سير عمل تصنيعي.",
           "case_body": "رسمنا طريقة عمل شركة تصنيع فعليًا — "
                        "من المبيعات والجدوى إلى المشتريات والإنتاج والتسليم والدفع — وبنينا نظام ERP الخاص بها حول سير العمل هذا.",
           "case_link": "اقرأ دراسة الحالة",
           "case_image_alt": "أمر بيع مكتمل في نظام ERP لمصنع JDK، مرتبط بعرض السعر والسجل المالي والتسليمات",
           "trust_kicker": "ما يميّز بيرينيا",
           "trust_heading": "إدخال موثوق للتقنية إلى أعمالك.",
           "trust_intro": "لا تُحدث التقنية قيمة إلا عندما تعمل في واقع الأعمال. بناء البرمجيات جزء من ذلك فقط — "
                          "نحن نركّز على الرحلة كاملة، من فهم الأعمال إلى التنفيذ والاعتماد والتكيّف مع التغيير.",
           "trust_contrast_label_a": "تسليم البرمجيات",
           "trust_contrast_a": "«نستطيع بناء البرمجيات.»",
           "trust_contrast_label_b": "إدخال التقنية",
           "trust_contrast_b": "«نساعدك على إدخال التقنية إلى أعمالك بشكل موثوق.»",
           "discovery_heading": "لنفهم المشكلة قبل أن نقرر ما يجب بناؤه.",
           "discovery_body": "خلال 30 دقيقة نتعرّف على أعمالك، والعملية أو المشكلة الحالية، والنتيجة التي "
                             "تريدها، وما إذا كانت التقنية قادرة على المساعدة — وما الخطوة التالية المناسبة.",
           "discovery_note": "محادثة عمل، لا عرض مبيعات — لا نلتزم في الاجتماع بحل أو سعر.",
           "capabilities_heading": "ثلاث قدرات. شريك تقني واحد.",
           "capabilities_intro": "نفهم الأعمال. نحدد التقنية المطلوبة. نبنيها. نضعها قيد التشغيل. "
                                 "ونساعد الأعمال على التكيّف.",
           "capabilities_roles": "اعمل معنا كمستشار، أو شريك تنفيذ، أو مطوّر برمجيات، أو شريك لتطبيق الذكاء "
                                 "الاصطناعي — أو مزيج من ذلك.",
           "capabilities_scope_note": "نتفق على نطاق العمل والتكلفة بعد فهم متطلباتك.",
           "local_kicker": "الكويت ودول الخليج",
           "local_heading": "تقنية مبنية مع مراعاة بيئة أعمالك.",
           "local_intro": "تجمع بيرينيا بين الخبرة التقنية والفهم العملي لطريقة عمل الشركات في الكويت ودول الخليج.",
           "process_heading": "ابدأ بالأعمال. وابنِ التقنية حولها.",
           "process_intro": "نتحمّل عادةً مسؤولية الرحلة كاملة — من المحادثة الأولى حتى تشغيل الحل — فلا تضطر "
                            "إلى التنسيق بين عدة موردين.",
           "principles": ["ذكاء اصطناعي عملي، لا لمجرد مواكبة الموضة",
                          "خبراء تقنية ذوو خبرة", "نطاق عمل وتكلفة واضحان"],
           "example_prompts": ["من أين تبدأ أعمالي مع التقنية؟", "أين يمكن للذكاء الاصطناعي أن يفيد أعمالي فعلًا؟",
                                "ماذا يحدث في الاجتماع الاستكشافي؟"],
           "hint": "ابدأ المحادثة", "lang_switch": "EN | English"},
}

COPY_CHAT = {
    "en": {"tagline_line1": "Solving Today. ", "tagline_line2": "Shaping Tomorrow.",
           "sub": "AI-POWERED TECHNOLOGY & INNOVATION", "header": "Perennia Assistant",
           "book_btn": "Book a 30-Minute Discovery Meeting", "faq_title": "Quick Questions",
           "input_placeholder": "Type your message…",
           "welcome_msg": "Hello! I'm Perennia's AI assistant. Before we get started, may I know your name? "
                          "It helps us build a good relationship with you and follow up properly.",
           "lang_switch": "AR | عربي"},
    "ar": {"tagline_line1": "حلول اليوم. ", "tagline_line2": "لصناعة الغد.",
           "sub": "تقنية وابتكار مدعومان بالذكاء الاصطناعي", "header": "مساعد بيرينيا",
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
