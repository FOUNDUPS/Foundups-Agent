// This is a standalone deployment, with no inherited Mall login or storage.
const origins = '__STORYTIME_PWA_ORIGINS__'.split(',');
const install = document.getElementById('install-app');
const update = document.getElementById('update-app');
const status = document.getElementById('pwa-status');
const say = message => { if (status) status.textContent = message; };
const video = document.querySelector('video');
let installPrompt;

// A failed video is explained honestly; the game remains usable offline.
const offline = () => say('You are offline. The game is available after its first online visit; reconnect to watch the video.');
if (!navigator.onLine) offline();
window.addEventListener('offline', offline);
window.addEventListener('online', () => say('Connected. The story video is available again.'));
video?.addEventListener('error', () => say(navigator.onLine
  ? 'The video could not load. Retry playback or refresh when ready.'
  : 'Reconnect to watch the story video. The downloaded game remains available.'));
video?.querySelector('source')?.addEventListener('error', () => say(navigator.onLine
  ? 'The video could not load. Retry playback or refresh when ready.'
  : 'Reconnect to watch the story video. The downloaded game remains available.'));

if (window.isSecureContext && origins.includes(location.origin) && 'serviceWorker' in navigator) {
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    if (install) install.hidden = false;
  });
  install?.addEventListener('click', async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    say(choice.outcome === 'accepted' ? 'Story Time installation requested.' : 'Installation dismissed. You can keep playing here.');
    installPrompt = null;
    install.hidden = true;
  });
  window.addEventListener('appinstalled', () => {
    if (install) install.hidden = true;
    installPrompt = null;
    say('Story Time is installed.');
  });
  navigator.serviceWorker.register('/storytime-sw.js', {scope: '/', updateViaCache: 'none'})
    .then(registration => {
      const offerUpdate = () => {
        if (!registration.waiting || !navigator.serviceWorker.controller) return;
        if (update) update.hidden = false;
        say('A new revision is ready. Update & restart when you have finished playing.');
      };
      offerUpdate();
      registration.addEventListener('updatefound', () => {
        registration.installing?.addEventListener('statechange', offerUpdate);
      });
      update?.addEventListener('click', () => {
        const waiting = registration.waiting;
        if (!waiting) return;
        update.disabled = true;
        video?.pause();
        // Only an explicit click is permitted to replace this tab's revision.
        let restarting = false;
        const finish = () => {
          if (restarting) return;
          restarting = true;
          location.reload();
        };
        navigator.serviceWorker.addEventListener('controllerchange', finish, {once: true});
        waiting.addEventListener('statechange', () => {
          if (waiting.state === 'activated') finish();
        });
        waiting.postMessage({type: 'STORYTIME_ACTIVATE'});
      });
    })
    .catch(() => say('Offline installation is unavailable in this browser. You can still watch and play while connected.'));
}
