/* Presentation only: no auth, CRM, investment intake or tracking. */
(function () {
  'use strict';
  var params = new URLSearchParams(window.location.search);
  var legacyKeys = ['sse', 'sse_url', 'invite', 'inviteCode', '__clerk_ticket', '__clerk_status', '__clerk_synced'];
  var legacyHashes = ['#how', '#roc', '#build', '#beta'];
  if (legacyKeys.some(function (key) { return params.has(key); }) || legacyHashes.indexOf(window.location.hash) !== -1) {
    window.location.replace('/innovate.html' + window.location.search + window.location.hash);
    return;
  }
  document.documentElement.classList.add('js');
  var descriptions = {
    ja: '計算基盤は誰のものか。誰が使い、利用料を払うのか。Foundups Japan ComputeのAI Koban構想を、所有・需要・価格・投資採算から検討する投資家向け事業概要。',
    en: 'Who owns the compute? Review the AI Koban investment thesis: ownership, paying customers, affordability and transparent scenario economics. feasibility-stage information.'
  };
  function setLanguage(language, updateUrl) {
    var lang = language === 'en' ? 'en' : 'ja';
    document.documentElement.lang = lang;
    document.querySelector('meta[name="description"]').setAttribute('content', descriptions[lang]);
    document.querySelectorAll('[data-language]').forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.language === lang));
    });
    if (updateUrl && /^https?:$/.test(window.location.protocol)) {
      var url = new URL(window.location.href);
      url.searchParams.set('lang', lang);
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
  }
  document.querySelectorAll('[data-language]').forEach(function (button) {
    button.addEventListener('click', function () { setLanguage(button.dataset.language, true); });
  });
  setLanguage(params.get('lang'), false);
})();
