/**
 * Red Dog Concierge — contextual guide for the p.fMALL shell.
 *
 * Injects contextual help content into the Red Dog surface.
 * Keeps local navigation help and mounts the separate public OpenRouter chat.
 * Membership does not grant this public chat private account or agent access.
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
       + 'Browse the catalog, check readiness states, and tap a tile to play its video queue.'
    },
    {
      q: 'How do I browse?',
      a: 'Tap any tile to play its video queue. Use the Enter button to visit its page. '
       + 'On desktop, use keyboard navigation or scroll.'
    },
    {
      q: 'Who is Red Dog?',
      a: 'Red Dog is the conversational face of 0102. '
       + 'Here you can ask public questions about FoundUPS and eSingularity. '
       + 'This chat cannot read your private account or perform actions for you.'
    }
  ] : isEntryPage ? [
    {
      q: 'What is this page?',
      a: 'The entry page for a single FoundUp. '
       + 'It shows the FoundUp\u2019s identity, readiness posture, token symbol, '
       + 'routing prefix, and lifecycle stage.'
    },
    {
      q: 'Who is Red Dog?',
      a: 'Red Dog is the conversational face of 0102 inside FoundUPS. '
       + 'Ask public project questions in the chat below. '
       + 'This chat cannot read your private account or perform actions for you.'
    },
    {
      q: 'What do readiness states mean?',
      a: 'Ready = live frontend, shell handoff coming. '
       + 'Conditional = frontend works with known gaps. '
       + 'Discoverable Only = backend service, no web frontend yet.'
    },
    {
      q: 'How do I go back?',
      a: 'Use the Back to Mall link at the top, or tap Return to Mall '
       + 'in the suggested actions above.'
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

  // Public Q&A remains separate from the signed-in Mall account and tools.
  var chat = document.createElement('section');
  chat.className = 'concierge-public-chat';
  chat.setAttribute('aria-label', 'Red Dog public project questions');
  chat.innerHTML = '<h3>Ask Red Dog · 0102</h3>'
    + '<p>Questions about FoundUPS, eSingularity or the YUMORI.me working plan?</p>'
    + '<div data-reddog-messages role="log" aria-live="polite" aria-label="Conversation"></div>'
    + '<div data-reddog-consent><p>Your public questions are sent to AI providers through OpenRouter. Avoid private information. Up to 10 questions, 2 minutes idle and 10 minutes total. Daily limits also apply.</p>'
    + '<button type="button" data-reddog-start>Agree and start chat</button></div>'
    + '<p data-reddog-status role="status"></p>'
    + '<button type="button" data-reddog-check hidden>Check session</button> '
    + '<button type="button" data-reddog-end hidden>End chat &amp; clear</button>'
    + '<form data-reddog-form><label>Question for Red Dog<input data-reddog-input type="text" maxlength="2000" autocomplete="off" placeholder="Ask a public project question…" disabled></label>'
    + '<button data-reddog-send type="submit" disabled>Send</button></form>';
  host.appendChild(chat);
  import('/js/reddog-public-client.js').then(function (client) {
    client.mountPublicChat(chat);
  }).catch(function () {
    chat.querySelector('[data-reddog-start]').disabled = true;
    chat.querySelector('[data-reddog-status]').textContent = 'Chat could not load. Please refresh the page.';
  });

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
    '}',
    '.concierge-public-chat { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(228,226,236,.15); color: #e4e2ec; font-size: .83rem; line-height: 1.5; }',
    '.concierge-public-chat h3 { margin: 0; font-size: .92rem; }',
    '.concierge-public-chat [hidden] { display: none !important; }',
    '.concierge-public-chat [data-reddog-messages] { max-height: 280px; overflow-y: auto; }',
    '.concierge-public-chat .chat-msg { padding: 8px 10px; margin: 6px 0; border-radius: 8px; background: rgba(228,226,236,.07); white-space: pre-wrap; overflow-wrap: anywhere; }',
    '.concierge-public-chat .chat-msg.user { background: rgba(124,92,252,.2); }',
    '.concierge-public-chat a { color: #c5b8ff; text-decoration: underline; }',
    '.concierge-public-chat button { padding: 7px 10px; margin: 4px 0; border: 1px solid rgba(228,226,236,.3); border-radius: 7px; color: #e4e2ec; background: rgba(124,92,252,.2); cursor: pointer; }',
    '.concierge-public-chat button:disabled, .concierge-public-chat input:disabled { opacity: .5; cursor: default; }',
    '.concierge-public-chat form { display: flex; align-items: end; gap: 8px; margin-top: 10px; }',
    '.concierge-public-chat label { flex: 1; min-width: 0; }',
    '.concierge-public-chat input { box-sizing: border-box; display: block; width: 100%; margin-top: 5px; padding: 9px; border: 1px solid rgba(228,226,236,.3); border-radius: 7px; background: rgba(0,0,0,.2); color: #fff; font: inherit; }'
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
