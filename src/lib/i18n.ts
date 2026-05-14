/**
 * MAMOUN i18n — Simple, Fast Internationalization
 * No heavy libraries. Pure object lookup. Arabic + English.
 */

export type Lang = 'ar' | 'en';

export const getLang = (): Lang => {
  if (typeof window === 'undefined') return 'ar';
  return (localStorage.getItem('mamoun_lang') as Lang) || 'ar';
};

export const setLang = (lang: Lang) => {
  localStorage.setItem('mamoun_lang', lang);
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.documentElement.lang = lang;
};

export const isRTL = (): boolean => getLang() === 'ar';

type TranslationKeys = typeof translations['ar'];

const translations = {
  ar: {
    // App
    appName: 'مأمون',
    appTagline: 'مساعدك الذكي',

    // Modes
    modeChat: 'المحادثة',
    modeDeliberation: 'المداولة',
    modeWorkshop: 'الورشة',
    modeCommand: 'القيادة',
    modeChatDesc: 'تحدث مع مأمون — مساعدك الذكي',
    modeDeliberationDesc: 'شاهد الأدمغة تتناقش',
    modeWorkshopDesc: 'اكتب كود وابني مشاريع',
    modeCommandDesc: 'تحكم بالنظام بالكامل',

    // Chat
    chatPlaceholder: 'اكتب رسالتك هنا...',
    chatSend: 'إرسال',
    chatThinking: 'مأمون يفكر...',
    chatWelcome: 'مرحباً! أنا مأمون، مساعدك الذكي. جاهز أساعدك! 🚀',
    chatWelcomeSub: 'اختر سؤالاً أو اكتب أي شيء',
    chatError: 'صار مشكلة، جرب مرة ثانية!',
    chatSuggest1: 'اشرحلي الذكاء الاصطناعي',
    chatSuggest2: 'اكتبلي كود لعبة',
    chatSuggest3: 'ما رأي الأدمغة؟',
    chatSuggest4: 'ساعدني بمشروع',
    'chat.suggest.ai': 'اشرحلي الذكاء الاصطناعي',
    'chat.suggest.ai.desc': 'أيش هو وكيف يشتغل؟',
    'chat.suggest.game': 'اكتبلي كود لعبة',
    'chat.suggest.game.desc': 'لعبة ممتعة أقدر ألعبها!',
    'chat.suggest.brains': 'ما رأي الأدمغة؟',
    'chat.suggest.brains.desc': 'شوف الأدمغة الخمسة تتناقش',
    'chat.suggest.project': 'ساعدني بمشروع',
    'chat.suggest.project.desc': 'بناء مشروع من الصفر',
    chatCopied: 'تم النسخ!',
    chatSwitchingTo: 'التبديل لوضع',

    // Brains
    brainNeural: 'الدماغ العصبي',
    brainCausal: 'الدماغ السببي',
    brainSymbolic: 'الدماغ الرمزي',
    brainBayesian: 'الدماغ البايزي',
    brainWorldModel: 'الدماغ النموذجي',
    brainNeuralDesc: 'الإبداع والتحليل العميق',
    brainCausalDesc: 'الاستدلال والتفكير السببي',
    brainSymbolicDesc: 'المنطق والرياضيات',
    brainBayesianDesc: 'الاحتمالات والتقدير',
    brainWorldModelDesc: 'محاكاة المستقبل والتنبؤ',
    brainNeuralFun: 'أنا الدماغ الأساسي — أفكر بعمق!',
    brainCausalFun: 'أبحث عن الأسباب الحقيقية!',
    brainSymbolicFun: 'المنطق هو تخصصي!',
    brainBayesianFun: 'أحسب الاحتمالات بدقة!',
    brainWorldModelFun: 'أتنبأ بالمستقبل!',

    // Status
    statusOnline: 'متصل',
    statusOffline: 'غير متصل',
    statusHealthy: 'سليم',
    statusThinking: 'يفكر',
    statusResponding: 'يجيب',
    statusHealth: 'الصحة',
    statusConfidence: 'الثقة',
    statusResponse: 'الاستجابة',
    statusLatency: 'زمن الاستجابة',

    // Cards
    cardApprove: 'موافقة',
    cardReject: 'رفض',
    cardCopy: 'نسخ',
    cardExpand: 'عرض التفاصيل',
    cardCollapse: 'إخفاء',
    cardConfidence: 'الثقة',
    cardAgreement: 'الاتفاق',
    cardConsensus: 'الإجماع',
    cardTimeLeft: 'الوقت المتبقي',
    cardExtend: 'تمديد',
    cardPriority: 'الأولوية',
    cardProgress: 'التقدم',
    cardPause: 'إيقاف',
    cardResume: 'استئناف',
    cardCancel: 'إلغاء',

    // Deliberation
    delibAskTopic: 'اطرح سؤالاً وشوف الأدمغة تتناقش!',
    delibInputPlaceholder: 'اطرح سؤالاً أو بدأ مداولة...',
    delibVoteSupport: 'وافق',
    delibVoteOppose: 'اعترض',
    delibClose: 'إغلاق',
    delibStance: 'الموقف',
    delibSupport: 'داعم',
    delibOppose: 'معارض',
    delibNeutral: 'محايد',

    // Workshop
    wsCode: 'الكود',
    wsBrowser: 'المتصفح',
    wsTerminal: 'الطرفية',
    wsRun: 'تشغيل',
    wsTest: 'اختبار',
    wsBuild: 'بناء',
    wsDeploy: 'نشر',
    wsRunShort: '▶ تشغيل',
    wsTestShort: '🧪 اختبار',
    wsBuildShort: '📦 بناء',
    wsDeployShort: '🚀 نشر',

    // Command
    cmdActiveTasks: 'المهام النشطة',
    cmdBrainStatus: 'حالة الأدمغة',
    cmdNotifications: 'الإشعارات',
    cmdKeyVault: 'خزنة المفاتيح',
    cmdQuickActions: 'إجراءات سريعة',
    cmdSystemRadar: 'رادار النظام',
    cmdSystemHealth: 'صحة النظام',
    cmdActionRestart: 'إعادة تشغيل',
    cmdActionSecurity: 'فحص أمان',
    cmdActionBackup: 'نسخ احتياطي',
    cmdActionClear: 'مسح ذاكرة',
    cmdActionSleep: 'وضع نوم',
    cmdActionUpdate: 'تحديث سريع',
    cmdActionRestartDesc: 'إعادة تشغيل النظام',
    cmdActionSecurityDesc: 'فحص أمني شامل',
    cmdActionBackupDesc: 'نسخ احتياطي كامل',
    cmdActionClearDesc: '⚠️ مسح الذاكرة المؤقتة',
    cmdActionSleepDesc: 'وضع السكون',
    cmdActionUpdateDesc: 'تحديث سريع',
    cmdConfirm: 'تأكيد؟',

    // KeyVault
    kvAddKey: 'إضافة مفتاح',
    kvProvider: 'المزود',
    kvKeyValue: 'المفتاح',
    kvActive: 'نشط',
    kvExpiring: 'ينتهي قريباً',
    kvExpired: 'منتهي',
    kvDelete: 'حذف',
    kvShow: 'إظهار',
    kvHide: 'إخفاء',

    // Boot
    bootInitializing: 'جاري التهيئة...',
    bootKernelOnline: 'النظام جاهز ✓',
    bootSystemReady: 'جاهز للعمل',
    bootSkip: 'تخطي ⏭',

    // Onboarding
    onbWelcome: 'أهلاً! أنا مأمون — مساعدك الذكي',
    onbWelcomeBtn: 'يلا نتعرف!',
    onbChat: 'هنا تحكي معي — اسألني أي شيء!',
    onbBrains: 'في 5 أدمغة في رأسي — كل وحدة تفكر بطريقة مختلفة!',
    onbModes: 'جرب الأوضاع الأربعة!',
    onbDone: 'جاهز! يلا نبدأ 🚀',
    onbSkip: 'تخطي',

    // Terminal
    termPrompt: '$',
    termHelp: 'اكتب help لعرض الأوامر',
    termCleared: 'تم مسح الشاشة',

    // Browser
    browserPlaceholder: 'أدخل عنوان URL...',
    browserCantLoad: 'لا يمكن تحميل الصفحة — تأكد أن الخادم يعمل',
    browserOpenNew: 'فتح في تبويب جديد',
    browserRefresh: 'تحديث',

    // General
    generalClose: 'إغلاق',
    generalSave: 'حفظ',
    generalCancel: 'إلغاء',
    generalLoading: 'جاري التحميل...',
    generalNoData: 'لا توجد بيانات',
    generalError: 'حدث خطأ',
    generalSuccess: 'تم بنجاح!',
    generalLanguage: 'اللغة',
    generalSwitchLang: 'English',

    // Error keys used by ChatMode
    'error.connection': 'خطأ في الاتصال',
    'error.general': 'صار مشكلة، جرب مرة ثانية!',
    'error.noResponse': 'لم أتلقَّ رد',
    'error.server': 'الخادم لا يستجيب',

    // Command keys
    'cmd.switching': '🔄 التبديل لوضع',
    'cmd.changeLanguage': '🔄 تم تغيير اللغة',
    'cmd.deliberationNeeded': '🏛️ بدء المداولة',
    'cmd.stopping': '⏹ إيقاف',
    'cmd.approvalNeeded': '⚠️ يحتاج موافقة',
    'cmd.approvalDesc': 'هذا الإجراء يحتاج موافقتك',
    'cmd.command': 'أمر',

    // Chat extra
    'misc.mamoun': 'مأمون',
    'chat.typing': 'يكتب...',
    'chat.connected': 'متصل',
    'chat.welcomeSub': 'اختر سؤالاً أو اكتب أي شيء',
    'chat.thinking': 'يفكر',
    'card.approved': 'تمت الموافقة ✓',
    'card.rejected': 'تم الرفض ✗',
    'status.systemHealth': 'صحة النظام',
    'brain.neural': 'الدماغ العصبي',
    'lang.toggle': '🌐 تغيير اللغة',
  },
  en: {
    // App
    appName: 'Mamoun',
    appTagline: 'Your AI Assistant',

    // Modes
    modeChat: 'Chat',
    modeDeliberation: 'Deliberate',
    modeWorkshop: 'Workshop',
    modeCommand: 'Command',
    modeChatDesc: 'Talk to Mamoun — your AI assistant',
    modeDeliberationDesc: 'Watch brains deliberate',
    modeWorkshopDesc: 'Write code & build projects',
    modeCommandDesc: 'Full system control',

    // Chat
    chatPlaceholder: 'Type your message here...',
    chatSend: 'Send',
    chatThinking: 'Mamoun is thinking...',
    chatWelcome: 'Hello! I\'m Mamoun, your AI assistant. Ready to help! 🚀',
    chatWelcomeSub: 'Pick a question or type anything',
    chatError: 'Something went wrong, try again!',
    chatSuggest1: 'Explain AI to me',
    chatSuggest2: 'Write game code for me',
    chatSuggest3: 'What do the brains think?',
    chatSuggest4: 'Help me with a project',
    'chat.suggest.ai': 'Explain AI to me',
    'chat.suggest.ai.desc': 'What is it and how does it work?',
    'chat.suggest.game': 'Write me a game',
    'chat.suggest.game.desc': 'A fun game I can play!',
    'chat.suggest.brains': 'What do the brains think?',
    'chat.suggest.brains.desc': 'Watch the 5 brains debate',
    'chat.suggest.project': 'Help me build a project',
    'chat.suggest.project.desc': 'Build a project from scratch',
    chatCopied: 'Copied!',
    chatSwitchingTo: 'Switching to',

    // Brains
    brainNeural: 'Neural Brain',
    brainCausal: 'Causal Brain',
    brainSymbolic: 'Symbolic Brain',
    brainBayesian: 'Bayesian Brain',
    brainWorldModel: 'World Model Brain',
    brainNeuralDesc: 'Creativity & deep analysis',
    brainCausalDesc: 'Reasoning & causal thinking',
    brainSymbolicDesc: 'Logic & mathematics',
    brainBayesianDesc: 'Probabilities & estimation',
    brainWorldModelDesc: 'Future simulation & prediction',
    brainNeuralFun: 'I\'m the main brain — I think deep!',
    brainCausalFun: 'I find the real causes!',
    brainSymbolicFun: 'Logic is my specialty!',
    brainBayesianFun: 'I calculate probabilities precisely!',
    brainWorldModelFun: 'I predict the future!',

    // Status
    statusOnline: 'Online',
    statusOffline: 'Offline',
    statusHealthy: 'Healthy',
    statusThinking: 'Thinking',
    statusResponding: 'Responding',
    statusHealth: 'Health',
    statusConfidence: 'Confidence',
    statusResponse: 'Response',
    statusLatency: 'Latency',

    // Cards
    cardApprove: 'Approve',
    cardReject: 'Reject',
    cardCopy: 'Copy',
    cardExpand: 'Show details',
    cardCollapse: 'Hide',
    cardConfidence: 'Confidence',
    cardAgreement: 'Agreement',
    cardConsensus: 'Consensus',
    cardTimeLeft: 'Time left',
    cardExtend: 'Extend',
    cardPriority: 'Priority',
    cardProgress: 'Progress',
    cardPause: 'Pause',
    cardResume: 'Resume',
    cardCancel: 'Cancel',

    // Deliberation
    delibAskTopic: 'Ask a question and watch the brains debate!',
    delibInputPlaceholder: 'Ask a question or start a deliberation...',
    delibVoteSupport: 'Agree',
    delibVoteOppose: 'Disagree',
    delibClose: 'Close',
    delibStance: 'Stance',
    delibSupport: 'Supporter',
    delibOppose: 'Opponent',
    delibNeutral: 'Neutral',

    // Workshop
    wsCode: 'Code',
    wsBrowser: 'Browser',
    wsTerminal: 'Terminal',
    wsRun: 'Run',
    wsTest: 'Test',
    wsBuild: 'Build',
    wsDeploy: 'Deploy',
    wsRunShort: '▶ Run',
    wsTestShort: '🧪 Test',
    wsBuildShort: '📦 Build',
    wsDeployShort: '🚀 Deploy',

    // Command
    cmdActiveTasks: 'Active Tasks',
    cmdBrainStatus: 'Brain Status',
    cmdNotifications: 'Notifications',
    cmdKeyVault: 'Key Vault',
    cmdQuickActions: 'Quick Actions',
    cmdSystemRadar: 'System Radar',
    cmdSystemHealth: 'System Health',
    cmdActionRestart: 'Restart',
    cmdActionSecurity: 'Security Scan',
    cmdActionBackup: 'Backup',
    cmdActionClear: 'Clear Memory',
    cmdActionSleep: 'Sleep Mode',
    cmdActionUpdate: 'Quick Update',
    cmdActionRestartDesc: 'Restart the system',
    cmdActionSecurityDesc: 'Full security scan',
    cmdActionBackupDesc: 'Full backup',
    cmdActionClearDesc: '⚠️ Clear cache memory',
    cmdActionSleepDesc: 'Sleep mode',
    cmdActionUpdateDesc: 'Quick update',
    cmdConfirm: 'Confirm?',

    // KeyVault
    kvAddKey: 'Add Key',
    kvProvider: 'Provider',
    kvKeyValue: 'Key',
    kvActive: 'Active',
    kvExpiring: 'Expiring soon',
    kvExpired: 'Expired',
    kvDelete: 'Delete',
    kvShow: 'Show',
    kvHide: 'Hide',

    // Boot
    bootInitializing: 'Initializing...',
    bootKernelOnline: 'System Ready ✓',
    bootSystemReady: 'Ready to work',
    bootSkip: 'Skip ⏭',

    // Onboarding
    onbWelcome: 'Hi! I\'m Mamoun — your AI assistant',
    onbWelcomeBtn: 'Let\'s get started!',
    onbChat: 'Chat with me here — ask me anything!',
    onbBrains: 'I have 5 brains — each thinks differently!',
    onbModes: 'Try the 4 modes!',
    onbDone: 'Ready! Let\'s go 🚀',
    onbSkip: 'Skip',

    // Terminal
    termPrompt: '$',
    termHelp: 'Type help for commands',
    termCleared: 'Screen cleared',

    // Browser
    browserPlaceholder: 'Enter URL...',
    browserCantLoad: 'Can\'t load page — make sure the server is running',
    browserOpenNew: 'Open in new tab',
    browserRefresh: 'Refresh',

    // General
    generalClose: 'Close',
    generalSave: 'Save',
    generalCancel: 'Cancel',
    generalLoading: 'Loading...',
    generalNoData: 'No data',
    generalError: 'An error occurred',
    generalSuccess: 'Success!',
    generalLanguage: 'Language',
    generalSwitchLang: 'العربية',

    // Error keys
    'error.connection': 'Connection error',
    'error.general': 'Something went wrong, try again!',
    'error.noResponse': 'No response received',
    'error.server': 'Server not responding',

    // Command keys
    'cmd.switching': '🔄 Switching to',
    'cmd.changeLanguage': '🔄 Language changed',
    'cmd.deliberationNeeded': '🏛️ Starting deliberation',
    'cmd.stopping': '⏹ Stopping',
    'cmd.approvalNeeded': '⚠️ Needs approval',
    'cmd.approvalDesc': 'This action needs your approval',
    'cmd.command': 'Command',

    // Chat extra
    'misc.mamoun': 'Mamoun',
    'chat.typing': 'Typing...',
    'chat.connected': 'Connected',
    'chat.welcomeSub': 'Pick a question or type anything',
    'chat.thinking': 'Thinking',
    'card.approved': 'Approved ✓',
    'card.rejected': 'Rejected ✗',
    'status.systemHealth': 'System Health',
    'brain.neural': 'Neural Brain',
    'lang.toggle': '🌐 Change Language',
  },
} as const;

export type TranslationKey = keyof TranslationKeys | string;

export function t(key: TranslationKey, lang?: Lang): string {
  const l = lang || getLang();
  const arDict = translations['ar'] as Record<string, string>;
  const enDict = translations['en'] as Record<string, string>;
  const dict = l === 'en' ? enDict : arDict;
  return dict?.[key] || arDict?.[key] || enDict?.[key] || key;
}

export function toggleLang(): Lang {
  const current = getLang();
  const next = current === 'ar' ? 'en' : 'ar';
  setLang(next);
  return next;
}

// Brain name helper
export const brainNameMap: Record<string, { ar: string; en: string; descAr: string; descEn: string; funAr: string; funEn: string; color: string }> = {
  neural: { ar: 'الدماغ العصبي', en: 'Neural Brain', descAr: 'الإبداع والتحليل العميق', descEn: 'Creativity & deep analysis', funAr: 'أنا الدماغ الأساسي — أفكر بعمق!', funEn: 'I\'m the main brain — I think deep!', color: '#4A6FA5' },
  causal: { ar: 'الدماغ السببي', en: 'Causal Brain', descAr: 'الاستدلال والتفكير السببي', descEn: 'Reasoning & causal thinking', funAr: 'أبحث عن الأسباب الحقيقية!', funEn: 'I find the real causes!', color: '#8A8A8A' },
  symbolic: { ar: 'الدماغ الرمزي', en: 'Symbolic Brain', descAr: 'المنطق والرياضيات', descEn: 'Logic & mathematics', funAr: 'المنطق هو تخصصي!', funEn: 'Logic is my specialty!', color: '#8A8A8A' },
  bayesian: { ar: 'الدماغ البايزي', en: 'Bayesian Brain', descAr: 'الاحتمالات والتقدير', descEn: 'Probabilities & estimation', funAr: 'أحسب الاحتمالات بدقة!', funEn: 'I calculate probabilities precisely!', color: '#4A6FA5' },
  world_model: { ar: 'الدماغ النموذجي', en: 'World Model Brain', descAr: 'محاكاة المستقبل والتنبؤ', descEn: 'Future simulation & prediction', funAr: 'أتنبأ بالمستقبل!', funEn: 'I predict the future!', color: '#C0C0C0' },
};
