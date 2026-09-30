// ──────────────────────────────────────────────────────────
// Central content store. In the original app this is admin-
// editable and served from the backend; here it's a plain data
// module so the same shape can later be swapped for an API call
// (see src/api/client.js) without touching any component.
// ──────────────────────────────────────────────────────────

export const BRAND = {
  name: "Perennia",
  wordmarkAr: "بيرينيا",
};

// Top-level site sections, mirrored in the header nav menu and the
// in-chat quick-access tray so both stay in sync from one place.
export const NAV = {
  en: [
    { id: "services", label: "Solutions" },
    { id: "products", label: "Products" },
    { id: "labs", label: "Labs" },
    { id: "about", label: "About" },
    { id: "contact", label: "Contact" },
  ],
  ar: [
    { id: "services", label: "الحلول" },
    { id: "products", label: "المنتجات" },
    { id: "labs", label: "المختبر" },
    { id: "about", label: "من نحن" },
    { id: "contact", label: "تواصل معنا" },
  ],
};

// Homepage "situations" cards — the three customer situations Perennia
// serves (HeroSituations in HeroShared.jsx; label-only pills in the
// centered-card layout). Unlike NAV/SECTIONS above these don't
// navigate to a page — clicking one hands its `question` straight to
// the AI Assistant chat (see Hero.jsx handleTopicClick), so the card
// IS the entry point into a relevant conversation, not a page link.
const HOME_TOPICS = {
  en: [
    {
      id: "starting-digital",
      label: "Starting Digital",
      audience: "For businesses beginning their digital journey",
      body: "You have a business process, but technology has not yet been properly integrated into it.",
      question: "My business is just starting with technology — how can Perennia help?",
    },
    {
      id: "practical-ai",
      label: "Making AI Practical",
      audience: "For businesses that want to use AI without the uncertainty",
      body: "We identify where AI genuinely adds value and implement it around the business — not simply because it is fashionable.",
      question: "Where could practical AI genuinely help my business?",
    },
    {
      id: "scaling-technology",
      label: "Scaling Technology",
      audience: "For businesses ready for their next stage of growth",
      body: "Technology needs to become more capable, connected and reliable as the business grows.",
      question: "My business is growing — how can Perennia help our technology scale with it?",
    },
  ],
  ar: [
    {
      id: "starting-digital",
      label: "البدء رقميًا",
      audience: "للشركات التي تبدأ رحلتها الرقمية",
      body: "لديك عمليات أعمال قائمة، لكن التقنية لم تُدمج فيها بالشكل الصحيح بعد.",
      question: "أعمالي في بداية رحلتها مع التقنية — كيف يمكن لبيرينيا المساعدة؟",
    },
    {
      id: "practical-ai",
      label: "ذكاء اصطناعي عملي",
      audience: "للشركات التي تريد استخدام الذكاء الاصطناعي دون حيرة أو غموض",
      body: "نحدد أين يضيف الذكاء الاصطناعي قيمة حقيقية، ونطبّقه بما يخدم أعمالك — لا لمجرد أنه رائج.",
      question: "أين يمكن للذكاء الاصطناعي العملي أن يفيد أعمالي فعلًا؟",
    },
    {
      id: "scaling-technology",
      label: "توسيع التقنية",
      audience: "للشركات المستعدة لمرحلة النمو التالية",
      body: "مع نمو أعمالك، تحتاج التقنية إلى أن تصبح أكثر قدرة وترابطًا وموثوقية.",
      question: "أعمالي تنمو — كيف يمكن لبيرينيا مساعدتنا على توسيع التقنية معها؟",
    },
  ],
};

// Homepage sectors (HeroSituations) — business types Perennia
// understands particularly well. Framed as relevance, not a limit on
// who we work with, and with no compliance/certification claims.
const HOME_SECTORS = {
  en: [
    { id: "trading", label: "Trading & Distribution", body: "Customers, orders, inventory, procurement and delivery, connected through business software built around how you trade." },
    { id: "professional-services", label: "Professional Services", body: "Workflows, approvals, documents and client management, made more connected and efficient through automation and custom systems." },
    { id: "healthcare", label: "Healthcare", body: "Dependable technology around operational workflows, information and service delivery." },
    { id: "education", label: "Education", body: "Practical technology for learning, administration and digital experiences." },
  ],
  ar: [
    { id: "trading", label: "التجارة والتوزيع", body: "العملاء والطلبات والمخزون والمشتريات والتسليم، مترابطة عبر برمجيات أعمال مبنية حول طريقة تجارتك." },
    { id: "professional-services", label: "الخدمات المهنية", body: "سير العمل والاعتمادات والمستندات وإدارة العملاء، أكثر ترابطًا وكفاءة عبر الأتمتة والأنظمة المخصصة." },
    { id: "healthcare", label: "الرعاية الصحية", body: "تقنية موثوقة حول سير العمل التشغيلي والمعلومات وتقديم الخدمات." },
    { id: "education", label: "التعليم", body: "تقنية عملية للتعلّم والإدارة والتجارب الرقمية." },
  ],
};

// Homepage capabilities (HeroCapabilities in HeroShared.jsx) — what
// Perennia does, as three connected capabilities. Static content, not
// links; the section's own CTAs lead to booking / the products page.
const HOME_CAPABILITIES = {
  en: [
    {
      id: "technology",
      label: "Technology",
      lead: "Build the technology your business needs.",
      body: "Custom software, business applications, automation and digital systems designed around the way the business actually operates.",
    },
    {
      id: "ai",
      label: "AI",
      lead: "Use AI where it makes business sense.",
      body: "AI implementation, intelligent workflows and practical AI solutions focused on useful business outcomes — not AI for its own sake.",
    },
    {
      id: "advisory",
      label: "Advisory",
      lead: "Make better technology decisions.",
      body: "Technology consulting, process assessment and guidance that helps businesses understand what to change, what to build and how to implement it reliably.",
    },
  ],
  ar: [
    {
      id: "technology",
      label: "التقنية",
      lead: "ابنِ التقنية التي تحتاجها أعمالك.",
      body: "برمجيات مخصصة وتطبيقات أعمال وأتمتة وأنظمة رقمية مصممة وفق طريقة عمل أعمالك فعليًا.",
    },
    {
      id: "ai",
      label: "الذكاء الاصطناعي",
      lead: "استخدم الذكاء الاصطناعي حيث يكون منطقيًا للأعمال.",
      body: "تطبيق الذكاء الاصطناعي وسير عمل ذكي وحلول عملية تركّز على نتائج مفيدة للأعمال — لا ذكاء اصطناعي لذاته.",
    },
    {
      id: "advisory",
      label: "الاستشارات",
      lead: "اتخذ قرارات تقنية أفضل.",
      body: "استشارات تقنية وتقييم للعمليات وتوجيه يساعدك على فهم ما يجب تغييره، وما يجب بناؤه، وكيف تنفّذه بشكل موثوق.",
    },
  ],
};

// Homepage GCC/Kuwait panel (HeroLocal in HeroShared.jsx) — only facts
// the existing site already supports (Kuwait-based per About; Arabic/
// English per the FAQ/Products page; in person or virtual per Contact).
// No customer names, counts, offices or partnerships.
const HOME_LOCAL_POINTS = {
  en: [
    { id: "kuwait", label: "Based in Kuwait", body: "Working with businesses across the GCC, in person or virtually." },
    { id: "bilingual", label: "Arabic and English", body: "Interfaces, content and AI assistants that work fully in both languages, right-to-left included — as on this site." },
    { id: "fit", label: "Built around how you operate", body: "Technology fitted to how your business actually works here — not an imported template." },
  ],
  ar: [
    { id: "kuwait", label: "مقرّنا الكويت", body: "نعمل مع الشركات في دول الخليج، حضوريًا أو عن بُعد." },
    { id: "bilingual", label: "العربية والإنجليزية", body: "واجهات ومحتوى ومساعدون أذكياء يعملون بالكامل باللغتين، مع دعم الكتابة من اليمين إلى اليسار — كما في هذا الموقع." },
    { id: "fit", label: "مصمَّمة حول طريقة عملك", body: "تقنية تناسب طريقة عمل أعمالك فعليًا هنا — لا قالبًا مستوردًا." },
  ],
};

// Homepage process (HeroProcess in HeroShared.jsx) — how Perennia takes
// a business from a problem to a working solution. Rendered as one
// ordered list: horizontal timeline on desktop, vertical on mobile.
const HOME_PROCESS = {
  en: [
    { id: "understand", label: "Understand", body: "A 30-minute discovery conversation to understand the business, problem and desired outcome." },
    { id: "assess", label: "Assess", body: "Examine the existing process, identify gaps and determine where technology can genuinely help." },
    { id: "propose", label: "Propose", body: "Define the solution, scope, implementation approach and investment clearly." },
    { id: "prototype", label: "Prototype", body: "Where appropriate, demonstrate the proposed solution before committing to the full build." },
    { id: "build", label: "Build", body: "Develop and integrate the solution around the customer's actual business process." },
    { id: "deploy", label: "Deploy", body: "Put the technology into operation, provide training and support adoption." },
    { id: "adapt", label: "Adapt", body: "Continue improving the solution as the business, market and requirements evolve." },
  ],
  ar: [
    { id: "understand", label: "الفهم", body: "محادثة استكشافية مدتها 30 دقيقة لفهم الأعمال والمشكلة والنتيجة المطلوبة." },
    { id: "assess", label: "التقييم", body: "دراسة العملية الحالية، وتحديد الفجوات، وتحديد أين يمكن للتقنية أن تساعد فعلًا." },
    { id: "propose", label: "المقترح", body: "تحديد الحل ونطاق العمل وأسلوب التنفيذ والتكلفة بوضوح." },
    { id: "prototype", label: "النموذج الأولي", body: "حيثما كان مناسبًا، نعرض الحل المقترح قبل الالتزام بالبناء الكامل." },
    { id: "build", label: "البناء", body: "تطوير الحل ودمجه حول عمليات أعمال العميل الفعلية." },
    { id: "deploy", label: "التشغيل", body: "وضع التقنية قيد التشغيل، وتقديم التدريب، ودعم اعتمادها." },
    { id: "adapt", label: "التكيّف", body: "مواصلة تحسين الحل مع تطور الأعمال والسوق والمتطلبات." },
  ],
};

// Homepage featured work (HeroWork) — the JDK Factory ERP
// lifecycle, every stage of which is implemented in that project.
const HOME_CASE_STAGES = {
  en: ["Sales", "Feasibility", "Quotation", "Order", "Procurement", "Inventory", "Production", "Delivery", "Payment"],
  ar: ["المبيعات", "الجدوى", "عرض السعر", "الطلب", "المشتريات", "المخزون", "الإنتاج", "التسليم", "الدفع"],
};

// Homepage "Other work" (HeroWork) — supporting evidence under the
// featured JDK Factory ERP case study. Each item is described only from
// its own project README; clients are described, not named (JDK is
// already named by the featured case study). Excluded pending
// confirmation: projects whose status or client relationship isn't
// documented (see the Phase 1 portfolio report).
const HOME_OTHER_WORK = {
  en: [
    {
      id: "field-sales",
      tag: "Mobile sales app · for JDK",
      label: "Field sales app",
      need: "Salespeople need to take a customer from enquiry to confirmed order while out of the office, and keep managers informed.",
      built: "An installable Arabic/English app: customers and visits, feasibility against today's stock, quotations, proforma invoices and orders, with manager reports.",
    },
    {
      id: "service-operations",
      tag: "Business platform · for a Kuwait-based service company",
      label: "Service operations platform",
      need: "One place to run client projects — from onboarding and government submissions to quotations, contracts and payments.",
      built: "Client onboarding, project workspaces, a government forms library and submissions, quotations, contracts, tasks and reports, with an AI assistant — in Arabic and English.",
    },
    {
      id: "practice-management",
      tag: "Practice management · for a small law firm",
      label: "Law firm practice management",
      need: "A small firm's clients, compliance records, tasks and billing in one system.",
      built: "Client onboarding with KYC and leadership history, secure document storage, tasks and calendar, and billing with PDF invoices.",
    },
    {
      id: "perennia-site",
      tag: "Website & AI · our own platform",
      label: "This website",
      need: "Visitors should be able to get answers and book time without waiting for a reply.",
      built: "A bilingual website with an AI assistant grounded in our own content, and self-service booking with live availability.",
    },
  ],
  ar: [
    {
      id: "field-sales",
      tag: "تطبيق مبيعات · لـ JDK",
      label: "تطبيق المبيعات الميدانية",
      need: "يحتاج مندوبو المبيعات إلى نقل العميل من الاستفسار إلى الطلب المؤكد وهم خارج المكتب، مع إبقاء المديرين على اطلاع.",
      built: "تطبيق قابل للتثبيت بالعربية والإنجليزية: العملاء والزيارات، وفحص الجدوى مقابل مخزون اليوم، وعروض الأسعار والفواتير المبدئية والطلبات، مع تقارير للمديرين.",
    },
    {
      id: "service-operations",
      tag: "منصة أعمال · لشركة خدمات مقرّها الكويت",
      label: "منصة عمليات الخدمات",
      need: "مكان واحد لإدارة مشاريع العملاء — من الانضمام والمعاملات الحكومية إلى عروض الأسعار والعقود والمدفوعات.",
      built: "انضمام العملاء، ومساحات عمل للمشاريع، ومكتبة للنماذج الحكومية وتقديمها، وعروض الأسعار والعقود والمهام والتقارير، مع مساعد ذكي — بالعربية والإنجليزية.",
    },
    {
      id: "practice-management",
      tag: "إدارة مكتب · لمكتب محاماة صغير",
      label: "إدارة مكتب محاماة",
      need: "عملاء المكتب وسجلات الامتثال والمهام والفوترة في نظام واحد.",
      built: "انضمام العملاء مع التحقق من الهوية وسجل القيادات، وتخزين آمن للمستندات، ومهام وتقويم، وفوترة مع فواتير PDF.",
    },
    {
      id: "perennia-site",
      tag: "موقع وذكاء اصطناعي · منصتنا الخاصة",
      label: "هذا الموقع",
      need: "يجب أن يتمكن الزوار من الحصول على إجابات وحجز موعد دون انتظار رد.",
      built: "موقع ثنائي اللغة مع مساعد ذكي يستند إلى محتوانا، وحجز ذاتي بمواعيد متاحة مباشرة.",
    },
  ],
};

// Homepage trust section (HeroTrust in HeroShared.jsx) — how Perennia
// approaches delivery, grouped into four points rather than a long
// feature list. These describe an approach, not guarantees.
const HOME_TRUST_POINTS = {
  en: [
    { id: "business-first", label: "Business first", body: "We understand the business before building, and design around your actual process." },
    { id: "careful", label: "Careful implementation", body: "We introduce technology carefully to minimise disruption, and help your people adopt and use it." },
    { id: "security", label: "Security and accountability", body: "We treat security and data protection seriously, with clear accountability for what we deliver." },
    { id: "support", label: "Support as you change", body: "Ongoing support where required, and technology that adapts as your requirements evolve." },
  ],
  ar: [
    { id: "business-first", label: "الأعمال أولًا", body: "نفهم أعمالك قبل أن نبني، ونصمّم حول عملياتك الفعلية." },
    { id: "careful", label: "تنفيذ مدروس", body: "ندخل التقنية بعناية لتقليل التعطّل، ونساعد فريقك على اعتمادها واستخدامها." },
    { id: "security", label: "الأمان والمسؤولية", body: "نتعامل مع الأمان وحماية البيانات بجدية، مع مسؤولية واضحة عمّا نقدّمه." },
    { id: "support", label: "دعم مع تغيّر أعمالك", body: "دعم مستمر عند الحاجة، وتقنية تتكيّف مع تطور متطلباتك." },
  ],
};

export const SECTIONS = {
  en: {
    about: {
      title: "About Perennia",
      body: "Perennia is a Kuwait-based technology company. We help businesses adopt, build and scale technology — using AI where it makes business sense — from first conversation through to production support.",
    },
    products: {
      title: "Products",
      body: "Business platforms, booking systems, automation workflows and AI assistants — tuned to how your team actually works.",
    },
    services: {
      title: "Services",
      body: "Technology, AI and Advisory — three connected capabilities, built around how your business actually works.",
    },
    contact: {
      title: "Contact Us",
      body: "Ready to talk? Use \"Book a 30-Minute Discovery Meeting\" to pick a time directly, or start a chat below and our assistant will connect you with the right person.",
    },
  },
  ar: {
    about: {
      title: "عن بيرينيا",
      body: "بيرينيا شركة تقنية مقرّها الكويت. نساعد الشركات على تبنّي التقنية وبنائها وتوسيعها — مع استخدام الذكاء الاصطناعي حيث يكون منطقيًا للأعمال — من المحادثة الأولى وحتى الدعم في التشغيل.",
    },
    products: {
      title: "المنتجات",
      body: "مساعدون بالذكاء الاصطناعي، وأتمتة سير العمل، ومنصات رقمية مخصصة — مبنية على تقنيات حديثة ومصممة لتناسب طريقة عمل فريقك.",
    },
    services: {
      title: "الخدمات",
      body: "استشارات، وتصميم منتجات، وهندسة متكاملة. نندمج مع فريقك أو ننفذ المشروع بالكامل، وفق ما يناسب خطتك.",
    },
    contact: {
      title: "تواصل معنا",
      body: "جاهز للتحدث؟ استخدم \"احجز اجتماعًا استكشافيًا لمدة 30 دقيقة\" لاختيار موعد مباشرة، أو ابدأ محادثة أدناه وسيقوم مساعدنا بتوصيلك بالشخص المناسب.",
    },
  },
};

export const COPY = {
  en: {
    dir: "ltr",
    common: {
      close: "Close", back: "Back", send: "Send", quickMenu: "Quick menu",
      primaryNav: "Primary", goHome: "Go to home", assistantTyping: "Assistant is typing",
      footerExplore: "Explore", footerContact: "Get in touch", footerRights: "All rights reserved.",
    },
    home: {
      welcome: "Welcome to Perennia",
      tagline: "Visit our V-Lounge for more",
      // Empty = no typed intro; the headline shows immediately. An admin
      // can still set one via copy.home.hero_statement.
      heroStatement: "",
      eyebrow: "Practical AI. Affordable Innovation.",
      assistantLabel: "Try the bilingual assistant we built — the same kind of tool we build for clients.",
      taglineLine1: "Technology that moves",
      taglineLine2: "your business forward.",
      supportingText: "Perennia helps GCC businesses adopt, build and scale technology — from their first digital initiative to practical AI and larger-scale transformation.",
      ctaPrimary: "Book a 30-Minute Discovery Meeting",
      ctaSecondary: "Explore What We Build",
      situations: HOME_TOPICS.en,
      sectors: HOME_SECTORS.en,
      capabilities: HOME_CAPABILITIES.en,
      localPoints: HOME_LOCAL_POINTS.en,
      processSteps: HOME_PROCESS.en,
      caseStages: HOME_CASE_STAGES.en,
      otherWork: HOME_OTHER_WORK.en,
      trustPoints: HOME_TRUST_POINTS.en,
      casePageSlug: "jdk-factory-erp",
      caseImageUrl: "/static/case-studies/jdk-erp/sales-order.png",
      situationsKicker: "Who we work with",
      situationsHeading: "Technology should fit the business — not force the business into a template.",
      situationsIntro: "We work with SMEs in Kuwait and the wider GCC, typically organisations of around 100 to 500 people. Whatever stage your business is at, we help you adopt technology reliably, practically and with a clear path forward.",
      sectorsHeading: "Businesses we understand particularly well",
      sectorsNote: "Not in one of these? The approach is the same: understand how your business works, then build the technology around it.",
      workKicker: "Our work",
      workHeading: "Different businesses have different technology problems.",
      workIntro: "We understand the problem first, then build the appropriate solution — from a factory's complete operation to a sales team in the field.",
      workOtherLabel: "Other work",
      workNeedLabel: "The need",
      workBuiltLabel: "What we built",
      caseKicker: "Featured work",
      caseHeading: "JDK Factory ERP: one system around a manufacturing workflow.",
      caseBody: "We mapped how a manufacturing business actually runs — from sales and feasibility through procurement, production, delivery and payment — and built its ERP around that workflow.",
      caseLink: "View Case Study",
      caseImageAlt: "The completed sales order in JDK Factory ERP, linked to its quotation, finance record and deliveries",
      trustKicker: "What sets Perennia apart",
      trustHeading: "Reliable technology induction for your business.",
      trustIntro: "Technology only creates value when it works in the real business. Building software is one part of that — we focus on the complete journey, from understanding the business through implementation, adoption and change.",
      trustContrastLabelA: "Software delivery",
      trustContrastA: "“We can build software.”",
      trustContrastLabelB: "Technology induction",
      trustContrastB: "“We can help you introduce technology into your business reliably.”",
      discoveryHeading: "Let's understand the problem before deciding what to build.",
      discoveryBody: "In 30 minutes we look at your business, your current process or problem, the outcome you want, whether technology can help — and what the sensible next step is.",
      discoveryNote: "A working conversation, not a sales pitch — no solution or price is committed in the meeting.",
      capabilitiesHeading: "Three capabilities. One technology partner.",
      capabilitiesIntro: "Understand the business. Decide what technology is needed. Build it. Put it into operation. Help the business adapt.",
      capabilitiesRoles: "Work with us as an advisor, an implementation partner, a software builder, an AI implementation partner — or a combination of these.",
      capabilitiesScopeNote: "Scope and investment are agreed once we understand your requirements.",
      localKicker: "Kuwait and the GCC",
      localHeading: "Technology built with your business environment in mind.",
      localIntro: "Perennia combines technology expertise with practical understanding of how businesses operate in Kuwait and the wider GCC.",
      processHeading: "Start with the business. Build the technology around it.",
      processIntro: "We normally take responsibility for the whole journey — from the first conversation to the solution in operation — so you are not left coordinating several vendors.",
      principles: [
        "Practical AI, not fashionable AI",
        "Experienced technology professionals",
        "Transparent scope and investment",
      ],
      examplePrompts: ["Where should my business start with technology?", "Where could AI genuinely help my business?", "What happens in a discovery meeting?"],
      hint: "Start chatting",
      langSwitch: "AR | عربي",
    },
    chat: {
      taglineLine1: "Practical AI. ",
      taglineLine2: "Affordable Innovation.",
      sub: "PRACTICAL AI · AFFORDABLE INNOVATION",
      header: "AI Assistant",
      onlineStatus: "Online · AI Assistant",
      poweredBy: "Powered by",
      bookBtn: "Book a 30-Minute Discovery Meeting",
      faqTitle: "Quick Questions",
      inputPlaceholder: "Ask Perennia anything…",
      welcomeMsg:
        "Hello! I'm Perennia's AI assistant. Before we get started, may I know your name? It helps us build a good relationship with you and follow up properly.",
      langSwitch: "AR | عربي",
      micLabel: "Talk",
      micLabelListening: "Listening…",
      micLabelSpeaking: "Speaking…",
      micUnsupported: "Voice input isn't supported in this browser — try Chrome or Edge, or use the text box instead.",
      micDenied: "Microphone access was blocked. Allow microphone access in your browser settings to talk to the assistant.",
      muteTts: "Mute replies",
      unmuteTts: "Unmute replies",
    },
    booking: {
      title: "Book a 30-Minute Discovery Meeting",
      subtitle: "A conversation about your business, the problem and the outcome you want. Pick a time — we'll confirm by email.",
      tabNew: "New Appointment",
      tabManage: "Manage Booking",
      date: "Date",
      slot: "Available times",
      slotEmpty: "Pick a date to see available times",
      name: "Name",
      email: "Email",
      phone: "Phone (optional)",
      service: "Service",
      selectService: "Choose a service…",
      minutesShort: "min",
      errPickService: "Please choose a service.",
      errRequiredQuestion: "Please answer all required questions.",
      notes: "Notes (optional)",
      cancel: "Cancel",
      confirm: "Confirm Booking",
      lookupId: "Appointment ID",
      lookupEmail: "Email used to book",
      findBtn: "Find My Appointment",
      cancelAppt: "Cancel Appointment",
      reschedule: "Reschedule",
      lookupDifferent: "Look up a different appointment",
      newDate: "New date",
      back: "Back",
      confirmNewTime: "Confirm New Time",
      successNew: (id) => `You're booked! Confirmation code: ${id}. A confirmation email is on its way.`,
      successCancel: "Your appointment has been cancelled.",
      successReschedule: (date, time) => `All set — your appointment is now on ${date} at ${time}.`,
      idPlaceholder: "PRN-XXXXXXXX",
      noAvailability: "No availability that day — try another date.",
      errPickDateSlot: "Please pick a date and time.",
      errName: "Please enter your name.",
      errEmail: "Please enter a valid email.",
      errLookupBoth: "Enter both the appointment ID and email.",
      errPickNewDateSlot: "Pick a new date and time.",
      errors: {
        slot_unavailable: "That time is no longer available — please pick another.",
        notice_window_passed: "This is too close to the appointment time to make that change.",
        not_found: "We couldn't find a matching appointment.",
        invalid_email: "Please enter a valid email.",
        invalid_name: "Please enter your name.",
        invalid_date: "That date isn't valid.",
        invalid_service: "That service isn't available anymore — please pick another.",
        invalid_question: "Something about the form didn't match — please try again.",
        missing_required_answer: "Please answer all required questions.",
        already_cancelled: "This appointment has already been cancelled.",
        booking_disabled: "Booking is currently unavailable — please check back soon.",
        generic: "Something went wrong — please try again.",
      },
    },
  },
  ar: {
    dir: "rtl",
    common: {
      close: "إغلاق", back: "رجوع", send: "إرسال", quickMenu: "قائمة سريعة",
      primaryNav: "الأساسية", goHome: "الذهاب إلى الرئيسية", assistantTyping: "المساعد يكتب",
      footerExplore: "استكشف", footerContact: "تواصل معنا", footerRights: "جميع الحقوق محفوظة.",
    },
    home: {
      welcome: "مرحبا بك في بيرينيا",
      tagline: "زوروا V-Lounge الخاص بنا لمزيد من المعلومات",
      heroStatement: "",
      eyebrow: "ذكاء اصطناعي عملي. ابتكار في المتناول.",
      assistantLabel: "جرّب المساعد ثنائي اللغة الذي بنيناه — من نوع الأدوات التي نبنيها لعملائنا.",
      taglineLine1: "تقنية تدفع",
      taglineLine2: "أعمالك إلى الأمام.",
      supportingText: "تساعد بيرينيا الشركات في دول الخليج على تبنّي التقنية وبنائها وتوسيعها — من أول مبادرة رقمية إلى الذكاء الاصطناعي العملي والتحول على نطاق أوسع.",
      ctaPrimary: "احجز اجتماعًا استكشافيًا لمدة 30 دقيقة",
      ctaSecondary: "استكشف ما نبنيه",
      situations: HOME_TOPICS.ar,
      sectors: HOME_SECTORS.ar,
      capabilities: HOME_CAPABILITIES.ar,
      localPoints: HOME_LOCAL_POINTS.ar,
      processSteps: HOME_PROCESS.ar,
      caseStages: HOME_CASE_STAGES.ar,
      otherWork: HOME_OTHER_WORK.ar,
      trustPoints: HOME_TRUST_POINTS.ar,
      casePageSlug: "jdk-factory-erp",
      caseImageUrl: "/static/case-studies/jdk-erp/sales-order.png",
      situationsKicker: "مع من نعمل",
      situationsHeading: "يجب أن تناسب التقنية الأعمال — لا أن تُجبر الأعمال على قالب جاهز.",
      situationsIntro: "نعمل مع الشركات الصغيرة والمتوسطة في الكويت ودول الخليج، وعادةً ما تضم نحو 100 إلى 500 موظف. أيًّا كانت المرحلة التي تمر بها أعمالك، نساعدك على تبنّي التقنية بشكل موثوق وعملي، مع مسار واضح للمضي قدمًا.",
      sectorsHeading: "أعمال نفهمها جيدًا بشكل خاص",
      sectorsNote: "لست ضمن هذه القطاعات؟ النهج نفسه: نفهم طريقة عمل أعمالك، ثم نبني التقنية حولها.",
      workKicker: "أعمالنا",
      workHeading: "لكل عمل مشكلاته التقنية الخاصة.",
      workIntro: "نفهم المشكلة أولًا، ثم نبني الحل المناسب — من التشغيل الكامل لمصنع إلى فريق مبيعات في الميدان.",
      workOtherLabel: "أعمال أخرى",
      workNeedLabel: "الحاجة",
      workBuiltLabel: "ما بنيناه",
      caseKicker: "عمل مميز",
      caseHeading: "نظام ERP لمصنع JDK: نظام واحد حول سير عمل تصنيعي.",
      caseBody: "رسمنا طريقة عمل شركة تصنيع فعليًا — من المبيعات والجدوى إلى المشتريات والإنتاج والتسليم والدفع — وبنينا نظام ERP الخاص بها حول سير العمل هذا.",
      caseLink: "عرض دراسة الحالة",
      caseImageAlt: "أمر بيع مكتمل في نظام ERP لمصنع JDK، مرتبط بعرض السعر والسجل المالي والتسليمات",
      trustKicker: "ما يميّز بيرينيا",
      trustHeading: "إدخال موثوق للتقنية إلى أعمالك.",
      trustIntro: "لا تُحدث التقنية قيمة إلا عندما تعمل في واقع الأعمال. بناء البرمجيات جزء من ذلك فقط — نحن نركّز على الرحلة كاملة، من فهم الأعمال إلى التنفيذ والاعتماد والتكيّف مع التغيير.",
      trustContrastLabelA: "تسليم البرمجيات",
      trustContrastA: "«نستطيع بناء البرمجيات.»",
      trustContrastLabelB: "إدخال التقنية",
      trustContrastB: "«نساعدك على إدخال التقنية إلى أعمالك بشكل موثوق.»",
      discoveryHeading: "لنفهم المشكلة قبل أن نقرر ما يجب بناؤه.",
      discoveryBody: "خلال 30 دقيقة نتعرّف على أعمالك، والعملية أو المشكلة الحالية، والنتيجة التي تريدها، وما إذا كانت التقنية قادرة على المساعدة — وما الخطوة التالية المناسبة.",
      discoveryNote: "محادثة عمل، لا عرض مبيعات — لا نلتزم في الاجتماع بحل أو سعر.",
      capabilitiesHeading: "ثلاث قدرات. شريك تقني واحد.",
      capabilitiesIntro: "نفهم الأعمال. نحدد التقنية المطلوبة. نبنيها. نضعها قيد التشغيل. ونساعد الأعمال على التكيّف.",
      capabilitiesRoles: "اعمل معنا كمستشار، أو شريك تنفيذ، أو مطوّر برمجيات، أو شريك لتطبيق الذكاء الاصطناعي — أو مزيج من ذلك.",
      capabilitiesScopeNote: "نتفق على نطاق العمل والتكلفة بعد فهم متطلباتك.",
      localKicker: "الكويت ودول الخليج",
      localHeading: "تقنية مبنية مع مراعاة بيئة أعمالك.",
      localIntro: "تجمع بيرينيا بين الخبرة التقنية والفهم العملي لطريقة عمل الشركات في الكويت ودول الخليج.",
      processHeading: "ابدأ بالأعمال. وابنِ التقنية حولها.",
      processIntro: "نتحمّل عادةً مسؤولية الرحلة كاملة — من المحادثة الأولى حتى تشغيل الحل — فلا تضطر إلى التنسيق بين عدة موردين.",
      principles: [
        "ذكاء اصطناعي عملي، لا لمجرد مواكبة الموضة",
        "خبراء تقنية ذوو خبرة",
        "نطاق عمل وتكلفة واضحان",
      ],
      examplePrompts: ["من أين تبدأ أعمالي مع التقنية؟", "أين يمكن للذكاء الاصطناعي أن يفيد أعمالي فعلًا؟", "ماذا يحدث في الاجتماع الاستكشافي؟"],
      hint: "ابدأ المحادثة",
      langSwitch: "EN | English",
    },
    chat: {
      taglineLine1: "ذكاء اصطناعي عملي. ",
      taglineLine2: "ابتكار في المتناول.",
      sub: "ذكاء اصطناعي عملي · ابتكار في المتناول",
      header: "المساعد الذكي",
      onlineStatus: "متصل الآن · مساعد ذكي",
      poweredBy: "بدعم من",
      bookBtn: "احجز اجتماعًا استكشافيًا لمدة 30 دقيقة",
      faqTitle: "أسئلة سريعة",
      inputPlaceholder: "اسأل مساعد بيرينيا أي شيء…",
      welcomeMsg:
        "مرحباً! أنا المساعد الذكي لبيرينيا. قبل أن نبدأ، هل لي أن أعرف اسمك؟ هذا يساعدنا على بناء علاقة أفضل معك ومتابعة طلبك بشكل صحيح.",
      langSwitch: "EN | English",
      micLabel: "تحدث",
      micLabelListening: "جارٍ الاستماع…",
      micLabelSpeaking: "يتحدث الآن…",
      micUnsupported: "الإدخال الصوتي غير مدعوم في هذا المتصفح — جرّب Chrome أو Edge، أو استخدم مربع الكتابة بدلاً من ذلك.",
      micDenied: "تم حظر الوصول إلى الميكروفون. يرجى السماح بالوصول إليه من إعدادات المتصفح للتحدث مع المساعد.",
      muteTts: "كتم الردود الصوتية",
      unmuteTts: "تفعيل الردود الصوتية",
    },
    booking: {
      title: "احجز اجتماعًا استكشافيًا لمدة 30 دقيقة",
      subtitle: "محادثة حول أعمالك والمشكلة والنتيجة التي تريدها. اختر الوقت المناسب — سنؤكد عبر البريد الإلكتروني.",
      tabNew: "موعد جديد",
      tabManage: "إدارة الحجز",
      date: "التاريخ",
      slot: "الأوقات المتاحة",
      slotEmpty: "اختر تاريخًا لرؤية الأوقات المتاحة",
      name: "الاسم",
      email: "البريد الإلكتروني",
      phone: "الهاتف (اختياري)",
      service: "الخدمة",
      selectService: "اختر خدمة…",
      minutesShort: "د",
      errPickService: "يرجى اختيار خدمة.",
      errRequiredQuestion: "يرجى الإجابة عن جميع الأسئلة المطلوبة.",
      notes: "ملاحظات (اختياري)",
      cancel: "إلغاء",
      confirm: "تأكيد الحجز",
      lookupId: "رقم الموعد",
      lookupEmail: "البريد الإلكتروني المستخدم للحجز",
      findBtn: "ابحث عن موعدي",
      cancelAppt: "إلغاء الموعد",
      reschedule: "إعادة الجدولة",
      lookupDifferent: "البحث عن موعد آخر",
      newDate: "تاريخ جديد",
      back: "رجوع",
      confirmNewTime: "تأكيد الوقت الجديد",
      successNew: (id) => `تم الحجز! رمز التأكيد: ${id}. بريد التأكيد في طريقه إليك.`,
      successCancel: "تم إلغاء موعدك.",
      successReschedule: (date, time) => `تم! موعدك الآن في ${date} الساعة ${time}.`,
      idPlaceholder: "PRN-XXXXXXXX",
      noAvailability: "لا توجد مواعيد متاحة في هذا اليوم — جرّب تاريخًا آخر.",
      errPickDateSlot: "يرجى اختيار تاريخ ووقت.",
      errName: "يرجى إدخال اسمك.",
      errEmail: "يرجى إدخال بريد إلكتروني صالح.",
      errLookupBoth: "أدخل رقم الموعد والبريد الإلكتروني معًا.",
      errPickNewDateSlot: "اختر تاريخًا ووقتًا جديدين.",
      errors: {
        slot_unavailable: "لم يعد هذا الوقت متاحًا — يرجى اختيار وقت آخر.",
        notice_window_passed: "الوقت المتبقي غير كافٍ لإجراء هذا التغيير.",
        not_found: "لم نتمكن من العثور على موعد مطابق.",
        invalid_email: "يرجى إدخال بريد إلكتروني صالح.",
        invalid_name: "يرجى إدخال اسمك.",
        invalid_date: "هذا التاريخ غير صالح.",
        invalid_service: "هذه الخدمة لم تعد متاحة — يرجى اختيار خدمة أخرى.",
        invalid_question: "حدث خلل في النموذج — يرجى المحاولة مرة أخرى.",
        missing_required_answer: "يرجى الإجابة عن جميع الأسئلة المطلوبة.",
        already_cancelled: "تم إلغاء هذا الموعد بالفعل.",
        booking_disabled: "الحجز غير متاح حاليًا — يرجى المحاولة لاحقًا.",
        generic: "حدث خطأ ما — يرجى المحاولة مرة أخرى.",
      },
    },
  },
};

export const FAQ = {
  en: [
    { q: "What services does Perennia offer?", a: "We help businesses adopt, build and scale technology: custom business software and automation, practical AI where it genuinely helps, and advisory — from the first discovery conversation through implementation and ongoing support." },
    { q: "How can I book a discovery meeting?", a: "Tap \"Book a 30-Minute Discovery Meeting\", choose a free slot, and you'll get an instant confirmation by email — no back-and-forth required." },
    { q: "Do you support Arabic and English?", a: "Yes — the whole experience, including this assistant, works fully in both English and Arabic with proper right-to-left layout." },
    { q: "Where are you located?", a: "We're based in Kuwait and work with businesses across the GCC. We meet either virtually or in person — ask during booking and we'll accommodate you." },
  ],
  ar: [
    { q: "ما هي الخدمات التي تقدمها بيرينيا؟", a: "نساعد الشركات على تبنّي التقنية وبنائها وتوسيعها: برمجيات أعمال مخصصة وأتمتة، وذكاء اصطناعي عملي حيث يفيد فعلًا، واستشارات — من محادثة الاستكشاف الأولى حتى التنفيذ والدعم المستمر." },
    { q: "كيف يمكنني حجز اجتماع استكشافي؟", a: "اضغط على \"احجز اجتماعًا استكشافيًا لمدة 30 دقيقة\"، اختر موعدًا متاحًا، وستحصل على تأكيد فوري عبر البريد الإلكتروني." },
    { q: "هل تدعمون اللغتين العربية والإنجليزية؟", a: "نعم — التجربة بأكملها، بما في ذلك هذا المساعد، تعمل بالكامل باللغتين مع تخطيط صحيح من اليمين إلى اليسار." },
    { q: "أين يقع مقركم؟", a: "مقرّنا الكويت، ونعمل مع الشركات في دول الخليج. نلتقي افتراضيًا أو شخصيًا — أخبرنا أثناء الحجز وسنوفر لك ما يناسبك." },
  ],
};
