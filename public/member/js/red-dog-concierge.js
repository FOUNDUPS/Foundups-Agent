/**
 * Red Dog Concierge — contextual guide for the p.fMALL shell.
 *
 * Injects contextual help content into the Red Dog surface.
 * No network dependency. No fake AI. No backend integration.
 *
 * Works on both Mall (index.html) and FoundUp entry (foundup.html) pages.
 * Builds against actual DOM hooks:
 *   Mall:  #accountPlane [data-reddog-concierge] (unified Red Dog plane)
 *   Entry: #conciergeSheet
 */
(function () {
  'use strict';

  // ---- page detection ----
  var isMallPage  = !!document.getElementById('mallTileField');
  var isEntryPage = !!document.getElementById('entryContent');

  // ---- find concierge host ----
  var host = null;
  if (isMallPage) {
    // Unified Red Dog plane — inject into the concierge guidance section
    var plane = document.getElementById('accountPlane');
    host = plane && plane.querySelector('[data-reddog-concierge]');
  } else {
    host = document.getElementById('conciergeSheet');
  }
  if (!host) return;

  // ---- help topics per page ----
  var topics = isMallPage ? [
    {
      q: 'What is the Mall?',
      a: 'The p.fMALL is your invite-gated home inside FoundUPS. '
       + 'Each tile represents a FoundUp \u2014 an autonomous venture in the pAVS ecosystem. '
       + 'Browse the catalog, check readiness states, and tap a tile to see its full entry page.'
    },
    {
      q: 'How do I browse?',
      a: 'Tap any tile to inspect it. Double-tap to enter its dedicated page. '
       + 'On desktop, use keyboard navigation or scroll.'
    },
    {
      q: 'Who is Red Dog?',
      a: 'Red Dog is your personal agent inside FoundUPS. '
       + 'Right now I help you navigate and keep track of your FoundUps. '
       + 'As the ecosystem grows, I will become more capable.'
    }
  ] : isEntryPage ? [
    {
      q: 'What is this page?',
      a: 'The entry page for a single FoundUp. '
       + 'It shows the FoundUp\u2019s identity, readiness posture, token symbol, '
       + 'routing prefix, and lifecycle stage.'
    },
    {
      q: 'What do readiness states mean?',
      a: 'Ready = live frontend, shell handoff coming. '
       + 'Conditional = frontend works with known gaps. '
       + 'Discoverable Only = backend service, no web frontend yet.'
    },
    {
      q: 'How do I go back?',
      a: 'Use the Back to Mall link at the top or the Return to Mall button '
       + 'at the bottom of this page.'
    }
  ] : [];

  if (!topics.length) return;

  // ---- build guide markup ----
  var html = '<div class="reddog-guide-topics" data-concierge="guide">';

  for (var i = 0; i < topics.length; i++) {
    html += '<details class="concierge-topic">'
          + '<summary class="concierge-topic-summary">' + esc(topics[i].q) + '</summary>'
          + '<p class="concierge-topic-body">' + esc(topics[i].a) + '</p>'
          + '</details>';
  }
  html += '</div>';

  // ---- inject into host ----
  if (isMallPage) {
    // Append topics inside the concierge section of the unified plane
    host.insertAdjacentHTML('beforeend', html);
  } else {
    // Entry page: inject before the navigation link section
    var anchor = (function () {
      var link = host.querySelector('.concierge-back');
      return link ? link.closest('.concierge-section') : null;
    })();

    if (anchor) {
      anchor.insertAdjacentHTML('beforebegin',
        '<div class="concierge-section" data-concierge="guide">' + html + '</div>');
    } else {
      host.insertAdjacentHTML('beforeend',
        '<div class="concierge-section" data-concierge="guide">' + html + '</div>');
    }
  }

  // ---- inject minimal styles ----
  var style = document.createElement('style');
  style.setAttribute('data-concierge', 'styles');
  style.textContent = [
    '.concierge-topic { margin-bottom: 0.35rem; }',
    '.concierge-topic:last-child { margin-bottom: 0; }',
    '.concierge-topic-summary {',
    '  cursor: pointer;',
    '  font-size: 0.84rem;',
    '  font-weight: 600;',
    '  color: rgba(228,226,236,0.85);',
    '  padding: 0.35rem 0;',
    '  list-style: none;',
    '  display: flex;',
    '  align-items: center;',
    '  gap: 0.4rem;',
    '}',
    '.concierge-topic-summary::-webkit-details-marker { display: none; }',
    '.concierge-topic-summary::before {',
    '  content: "\\25B8";',
    '  font-size: 0.65rem;',
    '  color: rgba(228,226,236,0.35);',
    '  transition: transform 0.15s;',
    '}',
    '.concierge-topic[open] > .concierge-topic-summary::before {',
    '  transform: rotate(90deg);',
    '}',
    '.concierge-topic-body {',
    '  margin: 0.15rem 0 0.4rem 1rem;',
    '  font-size: 0.82rem;',
    '  color: rgba(228,226,236,0.6);',
    '  line-height: 1.5;',
    '}'
  ].join('\n');
  document.head.appendChild(style);

  // ---- escape helper ----
  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }
})();
