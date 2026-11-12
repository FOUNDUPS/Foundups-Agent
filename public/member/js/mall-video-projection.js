(function () {
  'use strict';

  // Public presentation routes. Membership and tenant capabilities are checked elsewhere.
  const dedicatedHosts = new Map([['hpc.foundups.com', 'hpc']]);
  const publicScopes = new Set(dedicatedHosts.values());
  const memberPaths = new Set(['/member', '/member/', '/member/index.html']);

  function hostScope(location) {
    return dedicatedHosts.get(location.hostname) || null;
  }

  function resolve(location) {
    if (!memberPaths.has(location.pathname)) return null;
    const requested = new URLSearchParams(location.search).getAll('foundup');
    return hostScope(location) ||
      (requested.length === 1 && publicScopes.has(requested[0]) ? requested[0] : null);
  }

  function discoveryPath(foundupId, pocUrl) {
    if (!publicScopes.has(foundupId)) return null;
    const path = '/member/?foundup=' + foundupId;
    return pocUrl === 'https://foundups.com' + path ? path : null;
  }

  async function mount(scope) {
    const element = (id) => document.getElementById(id);
    const field = element('mallTileField');
    document.documentElement.dataset.mallVideoScope = scope;
    element('gestureHints').remove();
    element('loadingState').style.display = 'none';
    element('memberArea').style.display = 'block';
    field.setAttribute('aria-label', 'Shorts');
    const home = document.querySelector('.mall-header .mall-brand-minimal');
    home.href = 'https://foundups.com/member/';
    home.setAttribute('aria-label', 'Return to Play FoundUps Mall');
    home.addEventListener('click', function () { window.mallStateRestore.save(); });

    try {
      const response = await fetch('/member/mall-public-video-catalog.json', { cache: 'no-store', credentials: 'omit' });
      if (!response.ok) throw new Error('Public video catalog unavailable');
      const projection = (await response.json())[scope];
      if (projection?.lane?.foundup_id !== scope || !projection.lane.videos?.length) {
        throw new Error('Public video projection missing');
      }
      const voiceResource = new URL(projection.voice_resource_url);
      if (voiceResource.protocol !== 'https:' || voiceResource.username || voiceResource.password) {
        throw new Error('Invalid civic resource destination');
      }

      document.title = projection.lane.title + ' | Play FoundUps Mall';
      element('videoScopeTitle').textContent = projection.lane.title;
      const identity = element('videoScopeIdentity');
      const topic = element('videoScopeTopic');
      identity.textContent = projection.identity;
      topic.textContent = projection.topic;
      identity.after(topic);
      element('videoScopeCredit').textContent = projection.credit + ' Shorts · Commentary and satire';
      field.setAttribute('aria-describedby', 'videoScopeCredit');
      element('videoScopeDisclosureText').textContent = projection.disclosure;
      const disclosure = element('videoScopeDisclosure');
      element('videoScopeInfo').addEventListener('click', () => disclosure.showModal());

      const voice = element('videoScopeVoice');
      voice.href = voiceResource.href;
      voice.addEventListener('click', () => window.mallStateRestore.save());
      const actions = document.createElement('nav');
      actions.id = 'videoScopeActions';
      actions.setAttribute('aria-label', 'Video collection actions');
      actions.append(voice);
      element('redDogAnchor').prepend(actions);

      element('videoScopeHeader').hidden = false;
      window.mallStateRestore.selectVideoScope(scope);
      window.mallTileField.initialize([projection.lane], { fixedVideoField: true });
      window.mallStateRestore.restore();
      window.mallStateRestore.bindAutoSave();

      const desktop = window.matchMedia('(min-width: 900px) and (hover: hover) and (pointer: fine)');
      const applyPresentation = () => window.mallTileField.setScopedTheater?.(desktop.matches);
      desktop.addEventListener('change', applyPresentation);
      // The shared state owner restores the tab's browse position before startup.
      requestAnimationFrame(applyPresentation);
    } catch (error) {
      console.warn('[Mall] Public video projection unavailable:', error);
      field.textContent = 'This video collection is unavailable. Reload the page to try again.';
    }
  }

  window.mallVideoProjection = { hostScope, resolve, discoveryPath, mount };
})();
