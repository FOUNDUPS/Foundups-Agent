/**
 * Kosei AI Systems - Internationalization (EN/JP)
 * Centralized string management with localStorage persistence.
 */

const KOSEI_STRINGS = {
  en: {
    // Navigation
    nav_audit: 'Free Audit',
    nav_pricing: 'Pricing',
    nav_login: 'Client Login',
    lang_toggle: 'JP',

    // Hero
    hero_title: 'AI-Powered Content That Works While You Sleep',
    hero_subtitle: 'Stop spending hours creating content. Our AI agents analyze your brand, create posts, and publish across all platforms — automatically.',
    hero_cta: 'Get Your Free 20-Minute Audit',

    // Value propositions
    value_title: 'Why Creators Choose Kosei',
    value_1_title: 'Save 10+ Hours Weekly',
    value_1_desc: 'AI agents handle research, writing, scheduling, and publishing. You focus on your expertise.',
    value_2_title: 'Consistent Brand Voice',
    value_2_desc: 'We analyze your existing content to match your tone, style, and messaging perfectly.',
    value_3_title: 'Multi-Platform Publishing',
    value_3_desc: 'YouTube, LinkedIn, X, Instagram — one creation, optimized for each platform automatically.',
    value_4_title: 'Human Review Option',
    value_4_desc: 'Approve posts before they go live, or trust our AI to handle everything.',

    // Audit section
    audit_title: 'Start With a Free Content Audit',
    audit_subtitle: 'In 20 minutes, we\'ll analyze your content gaps and show you exactly how AI can help.',
    audit_what_title: 'What You\'ll Get',
    audit_what_1: 'Content gap analysis across your platforms',
    audit_what_2: 'Competitor positioning insights',
    audit_what_3: 'Custom AI content strategy recommendation',
    audit_what_4: 'ROI projection for your specific case',

    // Form
    form_title: 'Book Your Free Audit',
    form_name: 'Your Name',
    form_email: 'Email Address',
    form_business: 'Business / Brand Name',
    form_platforms: 'Platforms You Use',
    form_platform_youtube: 'YouTube',
    form_platform_linkedin: 'LinkedIn',
    form_platform_x: 'X (Twitter)',
    form_platform_instagram: 'Instagram',
    form_platform_tiktok: 'TikTok',
    form_platform_other: 'Other',
    form_handle: 'Primary Social Handle',
    form_handle_placeholder: '@yourhandle or URL',
    form_frequency: 'Current Posting Frequency',
    form_freq_daily: 'Daily',
    form_freq_weekly: '2-3 times per week',
    form_freq_monthly: 'A few times per month',
    form_freq_rarely: 'Rarely or never',
    form_goals: 'What are your content goals?',
    form_goals_placeholder: 'E.g., grow audience, establish thought leadership, drive sales...',
    form_consent: 'I agree to be contacted about Kosei services',
    form_submit: 'Request Free Audit',
    form_success: 'Thank you! We\'ll be in touch within 24 hours.',
    form_error: 'Something went wrong. Please try again.',

    // Trust section
    trust_title: 'Trusted by Creators Worldwide',
    trust_stat_1: '500+',
    trust_stat_1_label: 'Creators Served',
    trust_stat_2: '50K+',
    trust_stat_2_label: 'Posts Delivered',
    trust_stat_3: '10hrs',
    trust_stat_3_label: 'Avg. Time Saved Weekly',

    // Pricing teaser
    pricing_title: 'Simple, Transparent Pricing',
    pricing_trial: 'Start with a 14-day free trial',
    pricing_cta: 'Start Free Audit',

    // Footer
    footer_tagline: 'AI content automation for creators who mean business.',
    footer_links: 'Quick Links',
    footer_contact: 'Contact',
    footer_copyright: '2026 Kosei AI Systems. Part of the FoundUps ecosystem.'
  },

  ja: {
    // Navigation
    nav_audit: '無料診断',
    nav_pricing: '料金',
    nav_login: 'ログイン',
    lang_toggle: 'EN',

    // Hero
    hero_title: 'AIがあなたの代わりにコンテンツを作成',
    hero_subtitle: 'コンテンツ作成に何時間も費やすのをやめましょう。AIエージェントがあなたのブランドを分析し、投稿を作成し、すべてのプラットフォームに自動公開します。',
    hero_cta: '無料20分診断を予約',

    // Value propositions
    value_title: 'クリエイターがKoseiを選ぶ理由',
    value_1_title: '週10時間以上の節約',
    value_1_desc: 'AIエージェントがリサーチ、執筆、スケジュール、公開を担当。あなたは専門分野に集中できます。',
    value_2_title: '一貫したブランドボイス',
    value_2_desc: '既存のコンテンツを分析し、あなたのトーン、スタイル、メッセージを完璧に再現します。',
    value_3_title: 'マルチプラットフォーム配信',
    value_3_desc: 'YouTube、LinkedIn、X、Instagram — 1つの制作で、各プラットフォームに最適化して自動配信。',
    value_4_title: '人間によるレビューオプション',
    value_4_desc: '公開前に投稿を承認するか、AIにすべてを任せるか選択できます。',

    // Audit section
    audit_title: '無料コンテンツ診断から始めましょう',
    audit_subtitle: '20分で、あなたのコンテンツギャップを分析し、AIがどのように役立つかを正確にお見せします。',
    audit_what_title: '診断でわかること',
    audit_what_1: 'プラットフォーム全体のコンテンツギャップ分析',
    audit_what_2: '競合他社のポジショニングインサイト',
    audit_what_3: 'カスタムAIコンテンツ戦略の提案',
    audit_what_4: 'あなたの具体的なケースに対するROI予測',

    // Form
    form_title: '無料診断を予約',
    form_name: 'お名前',
    form_email: 'メールアドレス',
    form_business: 'ビジネス / ブランド名',
    form_platforms: 'ご利用中のプラットフォーム',
    form_platform_youtube: 'YouTube',
    form_platform_linkedin: 'LinkedIn',
    form_platform_x: 'X (Twitter)',
    form_platform_instagram: 'Instagram',
    form_platform_tiktok: 'TikTok',
    form_platform_other: 'その他',
    form_handle: 'メインのソーシャルハンドル',
    form_handle_placeholder: '@yourhandle または URL',
    form_frequency: '現在の投稿頻度',
    form_freq_daily: '毎日',
    form_freq_weekly: '週2-3回',
    form_freq_monthly: '月数回',
    form_freq_rarely: 'ほとんど投稿しない',
    form_goals: 'コンテンツの目標は何ですか？',
    form_goals_placeholder: '例: オーディエンスの拡大、ソートリーダーシップの確立、売上促進...',
    form_consent: 'Koseiサービスに関する連絡を受けることに同意します',
    form_submit: '無料診断をリクエスト',
    form_success: 'ありがとうございます！24時間以内にご連絡いたします。',
    form_error: '問題が発生しました。もう一度お試しください。',

    // Trust section
    trust_title: '世界中のクリエイターに信頼されています',
    trust_stat_1: '500+',
    trust_stat_1_label: 'クリエイター',
    trust_stat_2: '50K+',
    trust_stat_2_label: '配信投稿数',
    trust_stat_3: '10時間',
    trust_stat_3_label: '週平均節約時間',

    // Pricing teaser
    pricing_title: 'シンプルで透明な料金',
    pricing_trial: '14日間の無料トライアルから始めましょう',
    pricing_cta: '無料診断を開始',

    // Footer
    footer_tagline: '本気のクリエイターのためのAIコンテンツ自動化',
    footer_links: 'クイックリンク',
    footer_contact: 'お問い合わせ',
    footer_copyright: '2026 Kosei AI Systems. FoundUpsエコシステムの一部。'
  }
};

// Current locale
let currentLocale = 'en';

/**
 * Initialize i18n from localStorage or browser preference
 */
function initKoseiI18n() {
  const stored = localStorage.getItem('kosei_locale');
  if (stored && (stored === 'en' || stored === 'ja')) {
    currentLocale = stored;
  } else {
    // Detect from browser
    const browserLang = navigator.language.toLowerCase();
    currentLocale = browserLang.startsWith('ja') ? 'ja' : 'en';
  }
  applyKoseiStrings();
  updateLangToggle();
}

/**
 * Get string by key for current locale
 */
function t(key) {
  return KOSEI_STRINGS[currentLocale]?.[key] || KOSEI_STRINGS.en[key] || key;
}

/**
 * Get current locale
 */
function getKoseiLocale() {
  return currentLocale;
}

/**
 * Toggle between EN and JP
 */
function toggleKoseiLang() {
  currentLocale = currentLocale === 'en' ? 'ja' : 'en';
  localStorage.setItem('kosei_locale', currentLocale);
  applyKoseiStrings();
  updateLangToggle();
}

/**
 * Apply all strings to DOM elements with data-i18n attribute
 */
function applyKoseiStrings() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const text = t(key);
    if (el.tagName === 'INPUT' && el.type === 'submit') {
      el.value = text;
    } else if (el.hasAttribute('placeholder')) {
      el.placeholder = text;
    } else {
      el.textContent = text;
    }
  });

  // Update HTML lang attribute
  document.documentElement.lang = currentLocale;
}

/**
 * Update lang toggle button text
 */
function updateLangToggle() {
  const toggle = document.getElementById('langToggle');
  if (toggle) {
    toggle.textContent = t('lang_toggle');
  }
}

// Export for module use
if (typeof window !== 'undefined') {
  window.koseiI18n = {
    init: initKoseiI18n,
    t,
    getLocale: getKoseiLocale,
    toggle: toggleKoseiLang
  };
}
