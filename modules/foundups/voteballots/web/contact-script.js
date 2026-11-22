import { SKINS, createCallScript, resolveSkin } from './contact-script.mjs';

const byId = (id) => document.getElementById(id);
const skin = byId('script-skin');
const intro = byId('script-intro');
const callback = byId('script-callback');
const request = byId('script-request');
const reason = byId('script-reason');
const output = byId('contact-notes');
const status = byId('script-status');
const toneButtons = [...document.querySelectorAll('[data-script-tone]')];
let tone = 0;
let variant = 0;

function generate() {
  output.value = createCallScript({ intro: intro.value, callback: callback.value, request: request.value, reason: reason.value, tone, variant });
  status.textContent = output.value ? 'Script ready. Edit it below to make it yours.' : 'Add your core request to generate a script.';
}
function applySkin(value) {
  skin.value = resolveSkin(value);
  const selected = SKINS[skin.value];
  document.body.dataset.voteSkin = skin.value;
  byId('script-title').textContent = selected.title;
  byId('script-hpc-help').hidden = skin.value !== 'hpc';
  byId('script-spokesperson').hidden = skin.value !== 'hpc';
  byId('script-authorized').checked = false;
  byId('script-director').disabled = true;
  intro.value = selected.intro;
  request.value = selected.request;
  reason.value = selected.reason;
  // Personal details never travel in the skin URL or transfer between skins.
  callback.value = '';
  tone = 0;
  toneButtons.forEach((button, index) => button.setAttribute('aria-pressed', String(index === 0)));
  variant = 0;
  generate();
}
skin.addEventListener('change', () => {
  history.replaceState(null, '', skin.value === 'hpc' ? '#hpc' : location.pathname + location.search);
  applySkin(skin.value);
});
window.addEventListener('hashchange', () => {
  const requested = location.hash.slice(1);
  // Ordinary page anchors (including the skip link) must not erase a draft.
  if (['', 'vote', 'hpc'].includes(requested) && resolveSkin(requested) !== skin.value) applySkin(requested);
});
for (const field of [intro, callback, request, reason]) field.addEventListener('input', generate);
for (const button of toneButtons) button.addEventListener('click', () => {
  tone = Number(button.dataset.scriptTone);
  for (const item of toneButtons) item.setAttribute('aria-pressed', String(item === button));
  generate();
});
byId('script-regenerate').addEventListener('click', () => { variant = (variant + 1) % 3; generate(); });
byId('script-authorized').addEventListener('change', () => { byId('script-director').disabled = !byId('script-authorized').checked; });
byId('script-director').addEventListener('click', () => {
  if (skin.value !== 'hpc' || !byId('script-authorized').checked) return;
  intro.value = "I'm the executive director of HPC, a coalition of more than 2,000 large and small streamers.";
  callback.value = '202-656-6012';
  generate();
});
byId('script-copy').addEventListener('click', async () => {
  if (!output.value.trim()) { status.textContent = 'Add your core request first.'; return; }
  try {
    await navigator.clipboard.writeText(output.value);
    status.textContent = 'Script copied.';
  } catch {
    output.focus(); output.select();
    status.textContent = 'Select and copy the script using your device’s copy command.';
  }
});
byId('contact-clear').addEventListener('click', () => {
  for (const field of [intro, callback, request, reason, output]) field.value = '';
  tone = 0; variant = 0;
  byId('script-authorized').checked = false;
  byId('script-director').disabled = true;
  toneButtons.forEach((button, index) => button.setAttribute('aria-pressed', String(index === 0)));
  status.textContent = 'Script and personal details cleared.';
});
applySkin(location.hash.slice(1));
