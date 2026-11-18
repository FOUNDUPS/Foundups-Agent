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

const radio = document.querySelector('.cover-radio audio');
if (radio) {
  const notice = document.querySelector('.cover-radio-error');
  const showError = () => { notice.hidden = false; };
  radio.addEventListener('error', showError);
  radio.addEventListener('playing', () => { notice.hidden = true; });
  if (radio.error) showError();
}

const ticker = document.querySelector('.cover-ticker');
if (ticker) {
  const track = ticker.querySelector('.cover-ticker-track');
  const repeat = track.firstElementChild.cloneNode(true);
  repeat.setAttribute('aria-hidden', 'true');
  track.append(repeat);
  ticker.classList.add('cover-ticker--moving');

  const toggle = ticker.querySelector('.cover-ticker-toggle');
  toggle.hidden = false;
  toggle.addEventListener('click', () => {
    const label = ticker.classList.toggle('cover-ticker--paused') ? 'Play' : 'Pause';
    toggle.textContent = label;
    toggle.setAttribute('aria-label', label + ' ticker');
  });
}
