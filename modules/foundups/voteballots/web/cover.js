'use strict';

// Old landing links retain their original destination after the cover becomes the front door.
const guideFragments = new Set([
  'main', 'top', 'hero-title', 'oversight', 'oversight-title', 'approach', 'approach-title',
  'progress', 'progress-title', 'funding-status', 'claims-status', 'coalition-callout-title',
  'questions-title', 'install-app',
]);

function openLegacyGuideFragment() {
  let fragment;
  try {
    fragment = decodeURIComponent(location.hash.slice(1));
  } catch {
    return;
  }
  if (!guideFragments.has(fragment)) return;
  const guide = new URL('./guide', location.href);
  guide.search = location.search;
  guide.hash = location.hash;
  location.replace(guide);
}

openLegacyGuideFragment();
window.addEventListener('hashchange', openLegacyGuideFragment);

if ('serviceWorker' in navigator && window.isSecureContext) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
}
