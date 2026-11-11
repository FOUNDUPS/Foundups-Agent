import { appendOffice, parseContactRoster, phoneHref, QUEUE_SIZES, selectOffices } from './contact-queue.mjs';

const stateSelect = document.getElementById('contact-state');
const chamberSelect = document.getElementById('contact-chamber');
const officeSelect = document.getElementById('contact-office');
const sizeSelect = document.getElementById('contact-size');
const addButton = document.getElementById('contact-add');
const previousButton = document.getElementById('contact-prev');
const nextButton = document.getElementById('contact-next');
const removeButton = document.getElementById('contact-remove');
const clearButton = document.getElementById('contact-clear');
const notes = document.getElementById('contact-notes');
const call = document.getElementById('contact-call');
const current = document.getElementById('contact-current');
const queueList = document.getElementById('contact-queue');
const status = document.getElementById('contact-queue-status');
const date = document.getElementById('contact-date');
const coverage = document.getElementById('contact-coverage');
const officeInfo = document.getElementById('contact-office-info');

let roster;
let shownOffices = [];
let queue = [];
let cursor = 0;
let limit = 1;

function option(value, label) {
  const item = document.createElement('option');
  item.value = value;
  item.textContent = label;
  return item;
}

function describeOffice(office) {
  return [office.name, office.chamber, roster.states[office.state], office.district].filter(Boolean).join(' · ');
}

function formattedPhone(phone) {
  return `(${phone.slice(0, 3)}) ${phone.slice(3, 6)}-${phone.slice(6)}`;
}

function selectedOffice() {
  return shownOffices.find((office) => office.id === officeSelect.value);
}

function showOfficeInfo() {
  const office = selectedOffice();
  const href = office?.chamber === 'House'
    ? `https://clerk.house.gov/members/${office.id}`
    : 'https://www.senate.gov/senators/contact/';
  officeInfo.replaceChildren();
  officeInfo.hidden = !office;
  addButton.disabled = !office?.phone;
  if (!office) return;
  const source = document.createElement('a');
  source.href = href;
  source.textContent = 'Verify in the official directory';
  officeInfo.append(office.phone ? `${formattedPhone(office.phone)} · ` : 'Phone unavailable in this snapshot. ', source);
}

function showDirectory() {
  const state = stateSelect.value;
  shownOffices = selectOffices(roster.offices, state, chamberSelect.value);
  const prompt = state ? 'Choose an office' : 'Choose a state first';
  officeSelect.replaceChildren(option('', prompt));
  for (const office of shownOffices) {
    const label = describeOffice(office) + (office.phone ? '' : ' · phone unavailable');
    officeSelect.append(option(office.id, label));
  }
  officeSelect.disabled = !shownOffices.length;
  if (!state) {
    coverage.textContent = '';
  } else if (!shownOffices.length) {
    coverage.textContent = 'No listed offices match this filter. Check the official directories above.';
  } else {
    coverage.textContent = `${shownOffices.length} listed office${shownOffices.length === 1 ? '' : 's'}.`;
  }
  showOfficeInfo();
}

function showQueue(message = '') {
  const office = queue[cursor];
  status.textContent = message || `${queue.length} of ${limit} offices selected. Choose each office yourself.`;
  queueList.replaceChildren();
  queue.forEach((entry, index) => {
    const item = document.createElement('li');
    item.textContent = describeOffice(entry);
    if (index === cursor) item.setAttribute('aria-current', 'step');
    queueList.append(item);
  });
  queueList.hidden = !office;
  current.hidden = !office;
  call.hidden = !office;
  previousButton.disabled = cursor === 0;
  nextButton.disabled = cursor + 1 >= queue.length;
  removeButton.disabled = !office;

  if (!office) {
    current.textContent = '';
    call.textContent = '';
    call.removeAttribute('href');
    return;
  }
  current.textContent = `Office ${cursor + 1} of ${queue.length} · ${describeOffice(office)}`;
  call.href = phoneHref(office.phone);
  call.textContent = `Open dialer · ${formattedPhone(office.phone)}`;
}

stateSelect.addEventListener('change', showDirectory);
chamberSelect.addEventListener('change', showDirectory);
officeSelect.addEventListener('change', showOfficeInfo);

sizeSelect.addEventListener('change', () => {
  const requested = Number(sizeSelect.value);
  if (!QUEUE_SIZES.includes(requested) || queue.length > requested) {
    sizeSelect.value = String(limit);
    showQueue('Remove offices before choosing a smaller list.');
    return;
  }
  limit = requested;
  showQueue();
});

addButton.addEventListener('click', () => {
  const office = selectedOffice();
  const updated = appendOffice(queue, office, limit);
  if (updated === queue) {
    showQueue('This office is already listed, the list is full, or a phone number is unavailable.');
    return;
  }
  queue = updated;
  showQueue(`${office.name} added. ${queue.length} of ${limit} offices selected.`);
});

previousButton.addEventListener('click', () => {
  if (cursor > 0) cursor -= 1;
  showQueue(`Office ${cursor + 1} of ${queue.length} selected.`);
});

nextButton.addEventListener('click', () => {
  if (cursor + 1 < queue.length) cursor += 1;
  showQueue(`Office ${cursor + 1} of ${queue.length} selected.`);
});

removeButton.addEventListener('click', () => {
  if (!queue[cursor]) return;
  queue.splice(cursor, 1);
  cursor = Math.max(0, Math.min(cursor, queue.length - 1));
  showQueue(`Office removed. ${queue.length} of ${limit} offices selected.`);
  if (!queue.length) {
    const selector = officeSelect.disabled ? stateSelect : officeSelect;
    selector.focus();
  }
});

clearButton.addEventListener('click', () => {
  queue = [];
  cursor = 0;
  notes.value = '';
  showQueue('List and notes cleared.');
});

async function loadDirectory() {
  try {
    const url = new URL('./contact-roster.json', import.meta.url);
    const response = await fetch(url, { credentials: 'omit', redirect: 'error' });
    if (!response.ok) throw new Error('Contact snapshot unavailable');
    roster = parseContactRoster(await response.json());
    const sourceRows = roster.sources.reduce((total, source) => total + source.sourceRows, 0);
    const omitted = sourceRows - roster.offices.length;
    const gaps = omitted > 0 ? ` ${omitted} source rows had no usable member identifier.` : '';
    date.textContent = `Official directory snapshot from ${roster.retrievedOn} UTC. Congress ${roster.congress}.${gaps}`;
    for (const [code, name] of Object.entries(roster.states)) stateSelect.append(option(code, name));
    for (const control of [stateSelect, chamberSelect, sizeSelect, notes, clearButton]) control.disabled = false;
    showDirectory();
    showQueue();
  } catch {
    date.textContent = 'The local snapshot is unavailable. Use the official directories above.';
  }
}

loadDirectory();
