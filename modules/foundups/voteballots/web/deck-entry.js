'use strict';

// This entry is a fixed handoff to the shared PWA, never another Mall shell.
// Prior root bookmarks retain their original guide destinations.
let fragment = '';
try { fragment = decodeURIComponent(location.hash.slice(1)); } catch { /* Use the deck. */ }
const guideSections = new Set([
  'main', 'top', 'hero-title', 'oversight', 'oversight-title', 'approach', 'approach-title',
  'progress', 'progress-title', 'funding-status', 'claims-status', 'coalition-callout-title',
  'questions-title', 'install-app',
]);
if (guideSections.has(fragment)) {
  const guide = new URL('./guide', location.href);
  guide.search = location.search;
  guide.hash = location.hash;
  location.replace(guide);
} else {
  location.replace('https://play.foundups.com/member/?foundup=voteballots');
}
