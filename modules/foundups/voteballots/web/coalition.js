import { createCoalitionDraft } from './coalition-draft.mjs';

const form = document.getElementById('coalition-form');
const fields = {
  displayName: document.getElementById('display-name'),
  participationRole: document.getElementById('participation-role'),
  profileUrl: document.getElementById('profile-url'),
  contribution: document.getElementById('contribution'),
  acknowledged: document.getElementById('draft-acknowledgment')
};
const summary = document.getElementById('draft-errors');
const errorList = document.getElementById('draft-error-list');
const preview = document.getElementById('draft-preview');
const previewFields = {
  displayName: document.getElementById('preview-display-name'),
  participationRole: document.getElementById('preview-pathway'),
  profileUrl: document.getElementById('preview-profile-url'),
  contribution: document.getElementById('preview-contribution')
};
const emptyPreview = document.getElementById('draft-empty');
const status = document.getElementById('draft-status');
const download = document.getElementById('download-draft');
let currentDraft = null;

function clearErrors() {
  summary.hidden = true;
  errorList.replaceChildren();
  for (const [name, field] of Object.entries(fields)) {
    field.removeAttribute('aria-invalid');
    document.getElementById(`${name}-error`).textContent = '';
  }
}

function clearPreview() {
  currentDraft = null;
  preview.hidden = true;
  for (const field of Object.values(previewFields)) field.textContent = '';
  emptyPreview.hidden = false;
  download.disabled = true;
}

function updateRoleHint() {
  const required = fields.participationRole.value !== 'community';
  fields.profileUrl.required = required;
  document.getElementById('profile-requirement').textContent = required ? 'Required for this pathway' : 'Optional for community participation';
}

function showErrors(errors) {
  for (const [name, message] of Object.entries(errors)) {
    const item = document.createElement('li');
    if (fields[name]) {
      const field = fields[name];
      field.setAttribute('aria-invalid', 'true');
      document.getElementById(`${name}-error`).textContent = message;
      const link = document.createElement('a');
      link.href = `#${field.id}`;
      link.textContent = message;
      link.addEventListener('click', (event) => {
        event.preventDefault();
        field.focus();
      });
      item.append(link);
    } else {
      item.textContent = message;
    }
    errorList.append(item);
  }
  summary.hidden = false;
  summary.focus();
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  clearErrors();
  clearPreview();
  const result = createCoalitionDraft({
    displayName: fields.displayName.value,
    participationRole: fields.participationRole.value,
    profileUrl: fields.profileUrl.value,
    contribution: fields.contribution.value,
    acknowledged: fields.acknowledged.checked
  }, new Date().toISOString());
  if (!result.ok) {
    status.textContent = 'The draft needs a correction. Nothing has been sent.';
    showErrors(result.errors);
    return;
  }
  currentDraft = result.draft;
  previewFields.displayName.textContent = currentDraft.displayName;
  previewFields.participationRole.textContent = fields.participationRole.selectedOptions[0].textContent;
  previewFields.profileUrl.textContent = currentDraft.profileUrl || 'Not provided';
  previewFields.contribution.textContent = currentDraft.contribution || 'Not provided';
  emptyPreview.hidden = true;
  preview.hidden = false;
  download.disabled = false;
  status.textContent = 'Local draft prepared. You have not joined, and nothing has been sent or reviewed.';
  document.getElementById('draft-preview-title').focus();
});

form.addEventListener('input', () => {
  const hadDraft = currentDraft !== null;
  const hadErrors = !summary.hidden;
  clearErrors();
  clearPreview();
  updateRoleHint();
  if (hadDraft) status.textContent = 'Draft changed. Preview it again before downloading. Nothing has been sent.';
  else if (hadErrors) status.textContent = '';
});

form.addEventListener('reset', () => {
  clearErrors();
  clearPreview();
  status.textContent = 'Form and preview cleared. Any file already downloaded stays on your device.';
  // The browser applies the default values after the reset event.
  queueMicrotask(updateRoleHint);
});

document.getElementById('clear-draft').addEventListener('click', () => {
  form.reset();
  fields.displayName.focus();
});

download.addEventListener('click', () => {
  if (!currentDraft) return;
  const blob = new Blob([`${JSON.stringify(currentDraft, null, 2)}\n`], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'vote-coalition-application-draft.json';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  status.textContent = 'Download requested. This file is a private, unsubmitted draft; no application was sent or account created.';
});

// Clear in-memory fields when leaving, including a page retained in browser history.
window.addEventListener('pagehide', () => form.reset());
window.addEventListener('pageshow', (event) => { if (event.persisted) form.reset(); });
updateRoleHint();
form.hidden = false;
document.getElementById('draft-loading-note').hidden = true;
