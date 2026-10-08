/* Stage-one presentation only: no auth, CRM, investment intake or tracking. */
(function () {
  'use strict';
  var params = new URLSearchParams(window.location.search);
  var legacyKeys = ['sse', 'sse_url', 'invite', 'inviteCode', '__clerk_ticket', '__clerk_status', '__clerk_synced'];
  var legacyHashes = ['#how', '#roc', '#build', '#beta'];
  // Keep known historical product entry links on the unchanged Innovate page.
  if (legacyKeys.some(function (key) { return params.has(key); }) || legacyHashes.indexOf(window.location.hash) !== -1) {
    window.location.replace('/innovate.html' + window.location.search + window.location.hash);
    return;
  }
  document.documentElement.classList.add('js');
  var descriptions = {
    ja: '日本の空き施設を、AIを動かす拠点へ。Foundups Japan Computeは、AI Kobanを通じてFoundUps・EDUIT・地域の事業を支える全国構想です。現在は事業性の検証段階です。',
    en: 'A proposed Japan-wide network of local AI Koban compute nodes for autonomous FoundUps, EDUIT and regional businesses. Currently at feasibility stage.'
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
