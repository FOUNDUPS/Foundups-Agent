import { parseContactRoster, phoneHref, selectOffices } from './contact-queue.mjs';
import { suggestState } from './states-location.mjs';

const stateSelect = document.getElementById('contact-state');
const offices = document.getElementById('contact-offices');
const status = document.getElementById('contact-status');
const snapshot = document.getElementById('contact-snapshot');
const locationOptions = document.getElementById('contact-location');
const locate = document.getElementById('contact-locate');
const locationStatus = document.getElementById('contact-location-status');
const confirmation = document.getElementById('contact-suggestion');
const confirmState = document.getElementById('contact-confirm');

let roster;
let pendingSuggestion;
let requestId = 0;

async function readAsset(filename) {
  const response = await fetch(new URL(filename, import.meta.url), {
    credentials: 'omit', redirect: 'error',
  });
  if (!response.ok) throw new Error('Directory asset unavailable');
  return response.json();
}

function officeCard(office) {
  const card = document.createElement('li');
  const name = document.createElement('h2');
  name.textContent = office.name;
  card.append(name);
  const href = phoneHref(office.phone);
  if (href) {
    const call = document.createElement('a');
    call.href = href;
    call.className = 'button primary';
    call.textContent = `Call (${office.phone.slice(0, 3)}) ${office.phone.slice(3, 6)}-${office.phone.slice(6)}`;
    call.setAttribute('aria-label', `${call.textContent}, office of ${office.name}`);
    card.append(call);
  } else {
    const missing = document.createElement('p');
    missing.textContent = 'Check the official Senate directory for the office number.';
    card.append(missing);
  }
  return card;
}

function showOffices() {
  const state = stateSelect.value;
  const members = selectOffices(roster.offices, state, 'Senate');
  offices.replaceChildren(...members.map(officeCard));
  offices.hidden = !members.length;
  if (!state) {
    status.textContent = 'Choose your state or territory to see congressional contact options.';
  } else if (members.length) {
    status.textContent = `${roster.states[state]} · ${members.length} listed Senate office${members.length === 1 ? '' : 's'}`;
  } else {
    status.textContent = `${roster.states[state]} has no Senate office in the directory. Use the House office link below.`;
  }
}

function clearSuggestion() {
  requestId += 1;
  locate.disabled = false;
  pendingSuggestion = undefined;
  confirmation.hidden = true;
  locationStatus.textContent = '';
}

stateSelect.addEventListener('change', () => {
  clearSuggestion();
  showOffices();
});

confirmState.addEventListener('click', () => {
  if (!pendingSuggestion) return;
  stateSelect.value = pendingSuggestion;
  clearSuggestion();
  showOffices();
  stateSelect.focus();
});

locate.addEventListener('click', async () => {
  clearSuggestion();
  const currentRequest = requestId;
  locate.disabled = true;
  locationStatus.textContent = 'Waiting for your browser’s location result…';

  try {
    const { coords } = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: false, maximumAge: 0, timeout: 8000,
      });
    });
    if (currentRequest !== requestId) return;
    const boundaries = await readAsset('./states-boundaries.json');
    if (currentRequest !== requestId) return;
    const state = suggestState(coords, boundaries);
    if (state && Object.hasOwn(roster.states, state)) {
      pendingSuggestion = state;
      locationStatus.textContent = `Your current location suggests ${roster.states[state]}. Confirm only if it’s your home state.`;
      confirmState.textContent = `Use ${roster.states[state]}`;
      confirmation.hidden = false;
    } else {
      locationStatus.textContent = 'A state could not be suggested confidently. Choose your home state above.';
    }
  } catch {
    if (currentRequest === requestId) {
      locationStatus.textContent = 'The location lookup is unavailable. Choose your home state above.';
    }
  } finally {
    if (currentRequest === requestId) locate.disabled = false;
  }
});

async function loadDirectory() {
  try {
    roster = parseContactRoster(await readAsset('./contact-roster.json'));
    for (const [code, label] of Object.entries(roster.states)) {
      stateSelect.append(new Option(label, code));
    }
    stateSelect.disabled = false;
    locationOptions.hidden = !navigator.geolocation;
    document.getElementById('contact-boundary-source').hidden = locationOptions.hidden;
    snapshot.textContent = `Official directory snapshot · ${roster.retrievedOn} UTC · Congress ${roster.congress}`;
    snapshot.hidden = false;
    showOffices();
  } catch {
    status.textContent = 'The local office directory is unavailable. Use the official contact links below.';
  }
}

loadDirectory();
