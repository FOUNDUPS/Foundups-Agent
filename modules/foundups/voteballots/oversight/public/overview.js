'use strict';

const accountabilityOverview = document.getElementById('accountability-overview');
const professionalView = document.getElementById('view');
const professionalRoutes = new Set(
  Array.from(document.querySelectorAll('[data-nav]'), (link) => link.dataset.nav)
);
professionalRoutes.delete('home');

function showAccountabilityRoute() {
  const route = location.hash.slice(1).split('/')[0];
  const showProfessionalView = professionalRoutes.has(route) && professionalView.hasChildNodes();
  accountabilityOverview.hidden = showProfessionalView;
  professionalView.hidden = !showProfessionalView;
}

window.addEventListener('hashchange', showAccountabilityRoute);
showAccountabilityRoute();
