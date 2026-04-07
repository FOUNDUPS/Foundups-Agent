/**
 * Kosei Client Workspace -- UI Controller
 * Renders dashboard, trial status, platforms, onboarding, reporting, and issue form.
 *
 * Boundary: No admin-only fields (operator notes, lead pipeline, internal triage).
 */

let _dashData = null;

/**
 * Initialize UI: tab switching, issue form.
 */
function initUI() {
  // Tab switching
  document.querySelectorAll('.kc-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  // Issue form
  document.getElementById('issueForm')?.addEventListener('submit', handleIssueSubmit);
}

// ============================================
// Tab switching
// ============================================

function switchTab(tabName) {
  document.querySelectorAll('.kc-tab').forEach(t => {
    t.classList.toggle('kc-tab--active', t.dataset.tab === tabName);
  });
  document.querySelectorAll('.kc-tab-panel').forEach(p => {
    p.style.display = p.id === `tab-${tabName}` ? 'block' : 'none';
  });

  // Lazy-load issues when support tab opened
  if (tabName === 'support') {
    loadIssues();
  }
}

// ============================================
// Dashboard rendering
// ============================================

function renderDashboard(data) {
  _dashData = data;
  const { workspace, integrations, contentQueue, postHistory, trial } = data;

  // --- Identity ---
  document.getElementById('wsName').textContent = workspace.client_name || workspace.workspace_id || '--';
  document.getElementById('wsTier').textContent = (workspace.tier || 'trial').toUpperCase();
  document.getElementById('wsTier').className = 'kc-badge kc-badge--' + (workspace.status || 'onboarding');
  document.getElementById('wsLocale').textContent = (workspace.locale || 'en').toUpperCase();

  // --- Trial status ---
  const trialEl = document.getElementById('trialSection');
  if (trial && trial.status === 'active') {
    trialEl.style.display = 'block';
    document.getElementById('trialDays').textContent = trial.days_remaining ?? '--';
    document.getElementById('trialUsage').textContent =
      `${trial.usage_count || 0} / ${trial.usage_limit || 10} items used`;
    document.getElementById('trialPlatforms').textContent =
      `${trial.platforms_connected || 0} platform(s) connected`;

    // Progress bar
    const pct = trial.usage_limit ? Math.min(100, Math.round(((trial.usage_count || 0) / trial.usage_limit) * 100)) : 0;
    document.getElementById('trialProgress').style.width = pct + '%';
  } else {
    trialEl.style.display = trial ? 'block' : 'none';
    if (trial) {
      document.getElementById('trialDays').textContent = trial.status === 'converted' ? 'Converted' : trial.status || '--';
      document.getElementById('trialUsage').textContent = '';
      document.getElementById('trialPlatforms').textContent = '';
      document.getElementById('trialProgress').style.width = '0%';
    }
  }

  // --- Onboarding ---
  const step = workspace.onboarding_step || 0;
  const complete = workspace.onboarding_complete || false;
  document.getElementById('onboardStep').textContent = complete ? 'Complete' : `Step ${step} of 5`;
  renderOnboardingChecklist(step, complete);

  // --- Connected platforms ---
  renderPlatforms(integrations);

  // --- Posting preferences ---
  renderPreferences(workspace.posting_preferences || {});

  // --- Reporting ---
  renderReporting(contentQueue, postHistory, integrations, trial);
}

// ============================================
// Onboarding checklist
// ============================================

const ONBOARDING_STEPS = [
  'Workspace created',
  'Account verified',
  'Platform connected',
  'Branding set',
  'First content approved',
  'First post published'
];

function renderOnboardingChecklist(currentStep, complete) {
  const container = document.getElementById('onboardChecklist');
  if (!container) return;

  container.innerHTML = ONBOARDING_STEPS.map((label, i) => {
    const done = complete || i < currentStep;
    const current = !complete && i === currentStep;
    const cls = done ? 'kc-step--done' : (current ? 'kc-step--current' : 'kc-step--pending');
    return `<div class="kc-step ${cls}">
      <span class="kc-step-icon">${done ? '&#10003;' : (i + 1)}</span>
      <span class="kc-step-label">${esc(label)}</span>
    </div>`;
  }).join('');
}

// ============================================
// Platform connections
// ============================================

function renderPlatforms(integrations) {
  const container = document.getElementById('platformsList');
  if (!container) return;

  if (integrations.length === 0) {
    container.innerHTML = '<div class="kc-empty">No platforms connected yet</div>';
    return;
  }

  container.innerHTML = integrations.map(int => `
    <div class="kc-platform-row">
      <span class="kc-platform-name">${esc(int.platform || int.id)}</span>
      <span class="kc-badge kc-badge--${int.status || 'disconnected'}">${int.status || 'disconnected'}</span>
      ${int.account_handle ? `<span class="kc-platform-handle">${esc(int.account_handle)}</span>` : ''}
      ${int.health_status ? `<span class="kc-platform-health">${int.health_status}</span>` : ''}
    </div>
  `).join('');
}

// ============================================
// Posting preferences
// ============================================

function renderPreferences(prefs) {
  const container = document.getElementById('preferencesSection');
  if (!container) return;

  container.innerHTML = `
    <div class="kc-pref-row"><span class="kc-pref-label">Frequency</span><span>${esc(prefs.frequency || 'Not set')}</span></div>
    <div class="kc-pref-row"><span class="kc-pref-label">Days</span><span>${(prefs.preferred_days || []).join(', ') || 'Not set'}</span></div>
    <div class="kc-pref-row"><span class="kc-pref-label">Times</span><span>${(prefs.preferred_times || []).join(', ') || 'Not set'}</span></div>
    <div class="kc-pref-row"><span class="kc-pref-label">Platforms</span><span>${(prefs.platforms || []).join(', ') || 'Not set'}</span></div>
  `;
}

// ============================================
// Reporting
// ============================================

function renderReporting(contentQueue, postHistory, integrations, trial) {
  const created = contentQueue.length;
  const published = postHistory.length;
  const pendingApproval = contentQueue.filter(c => c.status === 'pending_approval').length;
  const connectedPlatforms = integrations.filter(i => i.status === 'connected').length;
  const repliesSent = postHistory.reduce((sum, p) => sum + ((p.engagement?.comments) || 0), 0);
  const daysLeft = trial?.days_remaining ?? '--';

  document.getElementById('statCreated').textContent = created;
  document.getElementById('statPublished').textContent = published;
  document.getElementById('statPending').textContent = pendingApproval;
  document.getElementById('statReplies').textContent = repliesSent;
  document.getElementById('statPlatforms').textContent = connectedPlatforms;
  document.getElementById('statDaysLeft').textContent = daysLeft;
}

// ============================================
// No workspace state
// ============================================

function showNoWorkspace() {
  const authGate = document.getElementById('authGate');
  const appShell = document.getElementById('appShell');
  const noWs = document.getElementById('noWorkspace');
  if (authGate) authGate.style.display = 'none';
  if (appShell) appShell.style.display = 'none';
  if (noWs) noWs.style.display = 'flex';
}

// ============================================
// Issues / Feedback
// ============================================

async function handleIssueSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const title = form.querySelector('[name="issueTitle"]')?.value?.trim();
  const desc = form.querySelector('[name="issueDesc"]')?.value?.trim();
  const cat = form.querySelector('[name="issueCat"]')?.value || 'general';
  const priority = form.querySelector('[name="issuePriority"]')?.value || 'medium';

  if (!title) return;

  const btn = form.querySelector('button[type="submit"]');
  if (btn) btn.disabled = true;

  const status = document.getElementById('issueStatus');

  try {
    await window.koseiAppData?.submitIssue(title, desc, cat, priority);
    form.reset();
    if (status) {
      status.textContent = 'Issue submitted. We\'ll get back to you soon.';
      status.className = 'kc-form-status kc-form-status--success';
      status.style.display = 'block';
    }
    loadIssues();
  } catch (err) {
    console.error('[Kosei App] Issue submission error:', err);
    if (status) {
      status.textContent = 'Failed to submit. Please try again.';
      status.className = 'kc-form-status kc-form-status--error';
      status.style.display = 'block';
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadIssues() {
  const container = document.getElementById('issuesList');
  if (!container) return;

  const issues = await window.koseiAppData?.fetchMyIssues() || [];

  if (issues.length === 0) {
    container.innerHTML = '<div class="kc-empty">No issues submitted yet</div>';
    return;
  }

  container.innerHTML = issues.map(issue => `
    <div class="kc-issue-card">
      <div class="kc-issue-top">
        <span class="kc-issue-title">${esc(issue.title)}</span>
        <span class="kc-badge kc-badge--${issue.status || 'open'}">${(issue.status || 'open').replace('_', ' ')}</span>
        <span class="kc-badge kc-badge--priority-${issue.priority || 'medium'}">${issue.priority || 'medium'}</span>
      </div>
      <div class="kc-issue-meta">
        <span>${esc(issue.category || 'general')}</span>
        <span>${formatDate(issue.created_at)}</span>
      </div>
      ${issue.description ? `<div class="kc-issue-desc">${esc(issue.description)}</div>` : ''}
      ${issue.resolution ? `<div class="kc-issue-resolution"><strong>Resolution:</strong> ${esc(issue.resolution)}</div>` : ''}
    </div>
  `).join('');
}

// ============================================
// Utilities
// ============================================

function esc(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

function formatDate(ts) {
  if (!ts) return '--';
  if (ts.toDate) {
    return ts.toDate().toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  }
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric'
  });
}

// Export
if (typeof window !== 'undefined') {
  window.koseiAppUI = {
    init: initUI,
    renderDashboard,
    showNoWorkspace
  };
}
