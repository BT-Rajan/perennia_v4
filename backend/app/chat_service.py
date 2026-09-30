"""
Orchestrates a single chat turn: reads chat.* config, builds a grounded
system prompt (persona + knowledge + FAQ + contact info + conversational
lead capture + turn-budget nudge), calls the configured LLM provider (or
skips straight to the fallback message if none is configured), and
captures a lead — either from a hidden tag the assistant emits once it
has collected name/phone/email conversationally, or opportunistically
if the visitor's message itself contains an email address. Keeps
routers/public_chat.py a thin HTTP wrapper.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app import chat_tools, content_service, knowledge_service, leads_service, llm_client
from app.settings_service import get_setting

EMAIL_RE = re.compile(r"[^\s@,;:!?()<>\[\]\"']+@[^\s@,;:!?()<>\[\]\"']+\.[^\s@,;:!?()<>\[\]\"']+")

# Hidden end-of-reply tag the assistant emits once it has naturally
# gathered name/phone/email during the conversation (see
# _lead_capture_instructions below). Stripped before the reply is
# ever sent to the visitor.
LEAD_TAG_RE = re.compile(
    r'\[\[LEAD_CAPTURED\s+name="([^"]*)"\s+phone="([^"]*)"\s+email="([^"]*)"\s*\]\]', re.IGNORECASE
)
NAME_RE = re.compile(r"^[^\x00-\x1f<>]{1,120}$")
PHONE_RE = re.compile(r"^[0-9+()\-\s]{6,25}$")
SIMPLE_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Minimal built-in company knowledge, used only when the admin hasn't
# configured any knowledge-base sources — so a fresh install can still
# answer basic "what is Perennia" / "how do I reach you" questions
# instead of always falling back to the "someone will follow up"
# message the moment an LLM is configured but nothing else has been.
DEFAULT_KNOWLEDGE = """
COMPANY: Perennia — AI-powered technology and innovation company.
TAGLINE: "Solving Today. Shaping Tomorrow."
NAME ORIGIN: From Latin "Perennis" — lasting, enduring, resilient, continuously growing.
MISSION: Practical, affordable AI solutions for today's challenges and tomorrow's opportunities.
""".strip()


def _lang_value(value: dict, lang: str) -> str:
    return value.get(lang) or value.get("en") or next(iter(value.values()), "")


def _contact_block(db: Session, lang: str) -> str:
    email = get_setting(db, "contact.email")
    phone = get_setting(db, "contact.phone")
    if not email and not phone:
        return ""
    contact = " / ".join(p for p in (email, phone) if p)
    if lang == "ar":
        return f"\n\nمعلومات التواصل الرسمية: {contact}. عند سؤال الزائر عن كيفية التواصل معنا أو الأسعار، زوّده بهذه المعلومات."
    return f"\n\nOfficial contact info: {contact}. If asked how to reach us, or about pricing, share this."


def _nudge_text(lang: str, turns_used: int, max_turns: int) -> str:
    """Steers the assistant toward booking a discovery meeting as the session's
    message budget runs low. Nothing shown to the visitor until the
    model naturally works it into a reply."""
    if max_turns - turns_used > 3:
        return ""
    if lang == "ar":
        return (
            "\n\nملاحظة مهمة: تبقّت بضع رسائل فقط في هذه الجلسة. اختم إجابتك القادمة بدعوة لطيفة "
            "وغير مُلحّة لحجز اجتماع استكشافي مدته 30 دقيقة مع الفريق لمناقشة التفاصيل مباشرة، دون تجاهل سؤال الزائر."
        )
    return (
        "\n\nIMPORTANT: only a few messages remain in this session. End your next reply with a "
        "brief, low-pressure invitation to book a 30-minute discovery meeting with the team — answer their "
        "question fully first, don't just deflect to booking."
    )


def _brevity_instructions(lang: str) -> str:
    """Always appended, regardless of what the admin wrote in
    chat.system_prompt — a persona edit shouldn't have to remember to
    re-state "keep it short" every time, and a visitor on a chat widget
    wants a quick back-and-forth, not an essay per turn."""
    if lang == "ar":
        return (
            "\n\nمهم بخصوص طول الرد: اجعل ردودك قصيرة ومحادثة — عادة من جملة إلى ثلاث جمل، وفقرة "
            "قصيرة واحدة كحد أقصى. لا تسرد كل التفاصيل دفعة واحدة؛ أعط أهم نقطة أو نقطتين واسأل "
            "إن كان الزائر يريد المزيد. استثناء: إذا طلب الزائر صراحة شرحاً أو قائمة مفصلة."
        )
    return (
        "\n\nIMPORTANT about reply length: keep responses short and conversational — normally "
        "1-3 sentences, one short paragraph at most. Don't dump every detail at once; give the "
        "one or two most relevant points and offer to say more if they want it. Exception: if the "
        "visitor explicitly asks for a detailed explanation or a list."
    )


def _booking_instructions(lang: str) -> str:
    """Tells the assistant it can complete a real booking — and manage
    an existing one — with its tools (see chat_tools.py) rather than
    only collecting contact details for a human follow-up call. Only
    included when booking tools are actually being passed to the LLM
    this turn — see get_reply — so the model is never told about tools
    it doesn't have."""
    if lang == "ar":
        return (
            "\n\nيمكنك حجز موعد فعلي مباشرة ضمن هذه المحادثة باستخدام أدواتك: ابدأ بـ "
            "list_services لمعرفة الخدمات المتاحة إن لم تكن تعرفها، ثم استخدم check_availability "
            "للحصول على الأوقات الحقيقية المتاحة ليوم معيّن — لا تخمّن وقتاً أبداً. لا تستدعِ "
            "book_appointment إلا بعد موافقة الزائر الصريحة على تاريخ ووقت محددين من نتائج "
            "check_availability، وبعد الحصول على الاسم والبريد الإلكتروني على الأقل. إذا لم تُرجع "
            "list_services أي خدمات (لا يوجد كتالوج)، اجمع وصفاً نصياً موجزاً لما يريد الزائر حجزه "
            "وأرسله في حقل service. إذا كانت الخدمة المختارة لها أسئلة مطلوبة (من list_services)، "
            "اجمع إجاباتها قبل الحجز. بعد نجاح الحجز، أخبر الزائر بوضوح برمز التأكيد الذي أعادته "
            "الأداة.\n\nيمكنك أيضاً إدارة موعد سابق: إذا ذكر الزائر رمز تأكيد وبريده الإلكتروني "
            "وأراد تعديل موعده أو إلغاءه، استخدم lookup_appointment أولاً للتحقق من الموعد قبل أي "
            "شيء آخر. لا تستدعِ cancel_appointment أو reschedule_appointment إلا بعد أن يؤكد "
            "الزائر صراحةً أنه يريد إلغاء أو نقل هذا الموعد بالتحديد — لا تفترض النية من مجرد ذكره "
            "لكلمة إلغاء أو تعديل. عند إعادة الجدولة، استخدم check_availability أولاً للتأكد من "
            "الوقت الجديد قبل استدعاء reschedule_appointment."
        )
    return (
        "\n\nYou can complete a real booking directly in this conversation using your tools: "
        "start with list_services if you don't already know what's offered, then use "
        "check_availability to get real open times for a specific date — never guess or invent a "
        "time. Only call book_appointment once the visitor has explicitly agreed to a specific "
        "date and time from check_availability's results, and you have at least their name and "
        "email. If list_services returns no services (no catalog configured), collect a short "
        "free-text description of what the visitor wants booked and pass it as the service field. "
        "If the chosen service has required questions (from list_services), collect those answers "
        "before booking. After a successful booking, clearly tell the visitor the confirmation "
        "code the tool returned.\n\nYou can also manage an existing appointment: if the visitor "
        "gives a confirmation code and the email it was booked under and wants to change or cancel "
        "it, call lookup_appointment first to verify it before anything else. Only call "
        "cancel_appointment or reschedule_appointment after the visitor has explicitly confirmed "
        "they want to cancel or move that specific appointment — never assume intent just because "
        "they mentioned the word cancel or reschedule. For a reschedule, confirm the new time with "
        "check_availability before calling reschedule_appointment."
    )


def _lead_capture_instructions(lang: str) -> str:
    """Instructs the assistant to collect name, then phone, then
    email - one at a time, politely framed - before getting into
    anything else, and to signal back via a hidden tag once it has
    all three. If the visitor asks something real before giving a
    name, the assistant should acknowledge briefly rather than fully
    answer, then ask for the name."""
    if lang == "ar":
        return (
            "\n\nمهم — قبل أي شيء آخر: لم نحصل بعد على بيانات الزائر، وجمعها له الأولوية على "
            "الإجابة التفصيلية. بأسلوب دافئ وليس مُلحّاً، اجمع ثلاث معلومات بالترتيب التالي، "
            "معلومة واحدة في كل رسالة: 1) الاسم، 2) رقم الهاتف، 3) البريد الإلكتروني. إذا طرح "
            "الزائر سؤالاً حقيقياً قبل إعطاء اسمه، أقرّ باهتمامه بجملة قصيرة ثم اطلب اسمه أولاً؛ "
            "بعدها يمكنك مزج إجابة حقيقية أثناء متابعة الطلب. إذا تجاهل الزائر نفس الطلب مرتين "
            "متتاليتين، توقف عن السؤال وواصل مساعدته بشكل طبيعي. بمجرد حصولك على الاسم ورقم "
            "هاتف وبريد إلكتروني صالحين، أضِف هذا السطر بالضبط في نهاية ردّك، مع القيم الفعلية، "
            "ولا شيء آخر على ذلك السطر، ولا تذكره أو تشرحه للزائر أبداً:\n"
            '[[LEAD_CAPTURED name="..." phone="..." email="..."]]'
        )
    return (
        "\n\nIMPORTANT — before anything else: this visitor's details haven't been collected yet, "
        "and collecting them takes priority over answering in depth. In a warm, non-repetitive "
        "tone, collect three things in this order, one per message: 1) name, 2) phone number, "
        "3) email. If the visitor asks a real question before giving their name, do NOT answer it "
        "in full yet — acknowledge it in one short sentence, then ask for their name first. Once "
        "you have it, weave in a real answer while continuing to ask for phone, then email. If the "
        "visitor brushes off the same ask twice in a row, drop it and help them normally from then "
        "on. Once you have a name, a valid-looking phone number, and a valid-looking email, append "
        "this exact line at the very end of your reply, with the real values filled in and nothing "
        "else on that line, and never mention or explain it to the visitor:\n"
        '[[LEAD_CAPTURED name="..." phone="..." email="..."]]'
    )


def _build_system_prompt(
    db: Session, *, lang: str, turns_used: int, max_turns: int, lead_captured: bool, booking_enabled: bool
) -> str:
    base = _lang_value(get_setting(db, "chat.system_prompt"), lang)

    kb_block = knowledge_service.build_prompt_block(db)
    if not kb_block:
        kb_block = f"\n\n{DEFAULT_KNOWLEDGE}"

    faq_block = content_service.build_faq_prompt_block(db, lang)

    contact_block = _contact_block(db, lang)
    lead_block = "" if lead_captured else _lead_capture_instructions(lang)
    booking_block = _booking_instructions(lang) if booking_enabled else ""
    nudge_block = _nudge_text(lang, turns_used, max_turns)
    brevity_block = _brevity_instructions(lang)

    return f"{base}{kb_block}{faq_block}{contact_block}{lead_block}{booking_block}{nudge_block}{brevity_block}"


def _extract_conversational_lead(reply: str) -> tuple[str, dict | None]:
    """Strips a [[LEAD_CAPTURED ...]] tag out of an assistant reply
    and, if the values look valid, returns a lead dict ready to
    capture. Always returns the cleaned reply, even if the lead is
    rejected as malformed — the tag must never reach the visitor."""
    match = LEAD_TAG_RE.search(reply)
    if not match:
        return reply, None

    cleaned = (reply[: match.start()] + reply[match.end() :]).strip()
    name, phone, email = (g.strip() for g in match.groups())

    if not (NAME_RE.match(name) and PHONE_RE.match(phone) and SIMPLE_EMAIL_RE.match(email)):
        return cleaned, None

    return cleaned, {"name": name, "phone": phone, "email": email}


def get_reply(
    db: Session, *, message: str, lang: str, history: list[dict], lead_captured: bool = False
) -> tuple[str, bool]:
    """Returns (reply, lead_captured) — the latter echoed back so the
    caller can pass it into the next turn's request and skip
    re-running the lead-capture instructions once a lead is in."""
    lang = "ar" if lang == "ar" else "en"

    if not get_setting(db, "features.chat_enabled"):
        return _lang_value(get_setting(db, "chat.unavailable_message"), lang), lead_captured

    turns_used = len([h for h in history if h.get("from") == "user"]) + 1
    max_turns = get_setting(db, "chat.max_turns")
    if turns_used > max_turns:
        return _lang_value(get_setting(db, "chat.turn_limit_message"), lang), lead_captured

    provider = get_setting(db, "chat.llm_provider")
    unavailable = _lang_value(get_setting(db, "chat.unavailable_message"), lang)

    if provider == "none":
        reply = unavailable
    else:
        booking_enabled = bool(get_setting(db, "features.booking_enabled"))
        try:
            system_prompt = _build_system_prompt(
                db, lang=lang, turns_used=turns_used, max_turns=max_turns, lead_captured=lead_captured,
                booking_enabled=booking_enabled,
            )
            reply = llm_client.generate_reply(
                provider=provider,
                api_key=get_setting(db, "chat.llm_api_key"),
                model=get_setting(db, "chat.llm_model"),
                system_prompt=system_prompt,
                history=history,
                message=message,
                max_tokens=get_setting(db, "chat.max_tokens"),
                temperature=get_setting(db, "chat.temperature"),
                tools=chat_tools.BOOKING_TOOLS if booking_enabled else None,
                tool_executor=chat_tools.make_executor(db, lang=lang) if booking_enabled else None,
            )
        except llm_client.LLMError:
            reply = unavailable

    lead_captured_now = lead_captured
    if not lead_captured:
        reply, lead_entry = _extract_conversational_lead(reply)
        if lead_entry:
            _capture(db, email=lead_entry["email"], name=lead_entry["name"], phone=lead_entry["phone"],
                     message=message)
            lead_captured_now = True

    # Safety net: even without an LLM configured (or if it never emits
    # the tag), still capture a lead the moment a visitor volunteers
    # an email address in their own message.
    if not lead_captured_now:
        _maybe_capture_lead(db, message=message)

    return reply, lead_captured_now


def _capture(db: Session, *, email: str, name: str, phone: str, message: str) -> None:
    lead, created = leads_service.capture_lead(
        db, email=email, name=name, phone=phone, source="chat",
        transcript_entry={"from": "user", "text": message},
    )
    if created:
        from app import notification_service
        notification_service.notify_admin_new_lead(db, email=email, message=message)


def _maybe_capture_lead(db: Session, *, message: str) -> None:
    match = EMAIL_RE.search(message)
    if not match:
        return
    email = match.group(0)
    lead, created = leads_service.capture_lead(
        db, email=email, source="chat",
        transcript_entry={"from": "user", "text": message},
    )
    if created:
        # Only alert staff on a genuinely new contact — not on every
        # follow-up message an already-known lead sends, which would
        # turn an active conversation into an alert-email flood.
        from app import notification_service
        notification_service.notify_admin_new_lead(db, email=email, message=message)
