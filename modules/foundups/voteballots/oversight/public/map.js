const map = document.querySelector('.map-deck');

function focusMapScreen() {
  const id = location.hash.slice(1);
  const requested = document.getElementById(id);
  const screen = requested?.parentElement === map && requested.classList.contains('map-screen')
    ? requested
    : document.getElementById('overview');
  screen.scrollIntoView({ block: 'start' });
  screen.querySelector('h2').focus({ preventScroll: true });
}

window.addEventListener('hashchange', focusMapScreen);
if (location.hash) focusMapScreen();
