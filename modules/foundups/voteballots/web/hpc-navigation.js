'use strict';

// Static links remain usable without JavaScript. No timers or account/session state.
(() => {
  const updateMotion = () => {
    document.documentElement.classList.toggle('hpc-navigation-motion', !document.hidden);
  };
  document.addEventListener('visibilitychange', updateMotion);
  updateMotion();
})();
