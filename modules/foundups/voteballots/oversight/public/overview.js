'use strict';

const main = document.getElementById('main');
const sheet = document.querySelector('.thumb-nav');
const toggle = sheet.querySelector('summary');
const sectionLabel = sheet.querySelector('.thumb-current');
const sectionLinks = document.querySelectorAll('[data-section]');
const fixedSection = document.querySelector('[data-page-section]')?.dataset.pageSection;
const worker = document.currentScript.dataset.worker;
const legacySections = new Map([
  ['hiring', 'house'], ['assurance', 'library'], ['topics', 'library'],
  ['roadmap', 'home'], ['contribute', 'library'],
]);

function syncSection() {
  const hash = location.hash.slice(1);
  const legacy = hash.split('/')[0];
  const id = legacySections.get(legacy) || legacy;
  const section = fixedSection || (document.getElementById(id) ? id : 'home');
  if (!fixedSection && hash && hash !== id) {
    document.getElementById(id)?.scrollIntoView();
  }
  for (const link of sectionLinks) {
    if (link.dataset.section === section) {
      link.setAttribute('aria-current', fixedSection ? 'page' : 'location');
      sectionLabel.textContent = link.textContent;
    } else {
      link.removeAttribute('aria-current');
    }
  }
}

document.querySelector('.skip').addEventListener('click', (event) => {
  event.preventDefault();
  main.focus();
});

sheet.querySelector('nav').addEventListener('click', (event) => {
  const link = event.target.closest('a');
  if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  sheet.open = false;
  if (link.pathname === location.pathname && link.hash) {
    event.preventDefault();
    if (location.hash !== link.hash) location.hash = link.hash;
    document.getElementById(link.hash.slice(1))?.scrollIntoView();
    main.focus({preventScroll: true});
  }
});

document.addEventListener('keydown', (event) => {
  if (!sheet.open || event.key !== 'Escape') return;
  event.preventDefault();
  sheet.open = false;
  toggle.focus();
});

document.addEventListener('click', (event) => {
  if (sheet.open && !sheet.contains(event.target)) sheet.open = false;
});

window.addEventListener('hashchange', syncSection);
syncSection();

const install = document.getElementById('install');
let promptEvent;
window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  promptEvent = event;
  install.hidden = false;
});
install.addEventListener('click', () => {
  if (!promptEvent) return;
  const prompt = promptEvent;
  promptEvent = null;
  install.hidden = true;
  prompt.prompt().catch(() => {});
});
window.addEventListener('appinstalled', () => {
  promptEvent = null;
  install.hidden = true;
});

if ('serviceWorker' in navigator) navigator.serviceWorker.register(worker).catch(() => {});
