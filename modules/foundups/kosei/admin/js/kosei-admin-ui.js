/**
 * Kosei Admin -- UI Controller
 * Renders lead/client/trial lists and detail panels.
 * All status models match KOSEI_DATA_MODEL.md and contracts.py.
 */

// Cached data for filtering
let _leads = [];
let _clients = [];
let _trials = [];
let _issues = [];

/**
 * Initialize UI: tabs, filters, detail panel close.
 */
function initUI() {
  // Tab switching
  document.querySelectorAll('.ka-tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });

  // Filters
  document.getElementById('leadStatusFilter')?.addEventListener('change', () => {
    renderLeads(_leads);
  });
  document.getElementById('clientStatusFilter')?.addEventListener('change', () => {
    renderClients(_clients);
  });
  document.getElementById('trialStatusFilter')?.addEventListener('change', () => {
    renderTrials(_trials);
  });
  document.getElementById('issueStatusFilter')?.addEventListener('change', () => {
    renderIssues(_issues);
  });
  document.getElementById('issuePriorityFilter')?.addEventListener('change', () => {
    renderIssues(_issues);
  });

  // Detail panel close
  document.getElementById('closeDetail')?.addEventListener('click', closeDetail);
}

// ============================================
// Tab switching
// ============================================

function switchTab(tabName) {
  document.querySelectorAll('.ka-tab').forEach(t => {
    t.classList.toggle('ka-tab--active', t.dataset.tab === tabName);
  });
  document.querySelectorAll('.ka-tab-panel').forEach(p => {
    p.style.display = p.id === `tab-${tabName}` ? 'block' : 'none';
  });
  closeDetail();
}

// ============================================
// Leads rendering
// ============================================

function renderLeads(leads) {
  _leads = leads;
  const filter = document.getElementById('leadStatusFilter')?.value || 'all';
  const filtered = filter === 'all' ? leads : leads.filter(l => l.audit_status === filter);

  const container = document.getElementById('leadsList');
  const countEl = document.getElementById('leadCount');
  if (countEl) countEl.textContent = `${filtered.length} of ${leads.length}`;

  if (filtered.length === 0) {
    container.innerHTML = '<div class="ka-empty">No leads found</div>';
    return;
  }

  container.innerHTML = filtered.map(lead => `
    <div class="ka-card" data-type="lead" data-id="${lead.id}">
      <div class="ka-card-top">
        <span class="ka-card-name">${esc(lead.contact_name || lead.contact_email || 'Unknown')}</span>
        <span class="ka-badge ka-badge--${lead.audit_status || 'pending'}">${lead.audit_status || 'pending'}</span>
      </div>
      <div class="ka-card-meta">
        ${lead.contact_email ? `<span>${esc(lead.contact_email)}</span>` : ''}
        ${lead.business_name ? `<span>${esc(lead.business_name)}</span>` : ''}
        ${lead.locale ? `<span>${lead.locale.toUpperCase()}</span>` : ''}
        <span>${formatDate(lead.created_at)}</span>
      </div>
    </div>
  `).join('');

  // Click handlers
  container.querySelectorAll('.ka-card').forEach(card => {
    card.addEventListener('click', () => openLeadDetail(card.dataset.id));
  });
}

async function openLeadDetail(id) {
  const lead = await window.koseiAdminData?.getLead(id);
  if (!lead) return;

  const handles = lead.platform_handles || {};
  const handleStr = Object.entries(handles)
    .map(([p, h]) => `${p}: ${h}`)
    .join(', ') || 'None';

  const gaps = (lead.gaps || []).map(g => `<li>${esc(g)}</li>`).join('') || '<li>Not yet analyzed</li>';
  const recs = (lead.recommendations || []).map(r => `<li>${esc(r)}</li>`).join('') || '<li>Not yet analyzed</li>';

  const html = `
    <div class="ka-detail-section">
      <h4>Contact</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Name</span><span class="ka-detail-value">${esc(lead.contact_name || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Email</span><span class="ka-detail-value">${esc(lead.contact_email || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Business</span><span class="ka-detail-value">${esc(lead.business_name || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Locale</span><span class="ka-detail-value">${(lead.locale || 'en').toUpperCase()}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Intake</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Source</span><span class="ka-detail-value">${esc(lead.lead_source || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Platforms</span><span class="ka-detail-value">${handleStr}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Frequency</span><span class="ka-detail-value">${esc(lead.current_posting_frequency || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Goals</span><span class="ka-detail-value">${esc(lead.business_goals || '--')}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Audit Status</h4>
      <div class="ka-detail-row">
        <span class="ka-detail-label">Status</span>
        <span class="ka-badge ka-badge--${lead.audit_status || 'pending'}">${lead.audit_status || 'pending'}</span>
      </div>
      <div class="ka-detail-row"><span class="ka-detail-label">Recommended Tier</span><span class="ka-detail-value">${esc(lead.recommended_tier || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Trial Offered</span><span class="ka-detail-value">${lead.trial_offered ? 'Yes' : 'No'}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Trial Accepted</span><span class="ka-detail-value">${lead.trial_accepted ? 'Yes' : 'No'}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Gaps Found</h4>
      <ul style="margin:0;padding-left:var(--space-lg);color:var(--kosei-text-muted);font-size:0.875rem;">${gaps}</ul>
    </div>

    <div class="ka-detail-section">
      <h4>Recommendations</h4>
      <ul style="margin:0;padding-left:var(--space-lg);color:var(--kosei-text-muted);font-size:0.875rem;">${recs}</ul>
    </div>

    <div class="ka-detail-section">
      <h4>Timeline</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Submitted</span><span class="ka-detail-value">${formatDate(lead.created_at)}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Audit Completed</span><span class="ka-detail-value">${formatDate(lead.audit_completed_at)}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Converted</span><span class="ka-detail-value">${formatDate(lead.converted_at)}</span></div>
    </div>
  `;

  showDetail(lead.contact_name || lead.contact_email || 'Lead', html);
}

// ============================================
// Clients rendering
// ============================================

function renderClients(clients) {
  _clients = clients;
  const filter = document.getElementById('clientStatusFilter')?.value || 'all';
  const filtered = filter === 'all' ? clients : clients.filter(c => c.status === filter);

  const container = document.getElementById('clientsList');
  const countEl = document.getElementById('clientCount');
  if (countEl) countEl.textContent = `${filtered.length} of ${clients.length}`;

  if (filtered.length === 0) {
    container.innerHTML = '<div class="ka-empty">No clients found</div>';
    return;
  }

  container.innerHTML = filtered.map(client => `
    <div class="ka-card" data-type="client" data-id="${client.id}">
      <div class="ka-card-top">
        <span class="ka-card-name">${esc(client.client_name || client.id)}</span>
        <span class="ka-badge ka-badge--${client.status || 'onboarding'}">${client.status || 'onboarding'}</span>
      </div>
      <div class="ka-card-meta">
        ${client.client_email ? `<span>${esc(client.client_email)}</span>` : ''}
        <span>Tier: ${esc(client.tier || 'trial')}</span>
        <span>Step ${client.onboarding_step || 0}/5</span>
        <span>${formatDate(client.created_at)}</span>
      </div>
    </div>
  `).join('');

  container.querySelectorAll('.ka-card').forEach(card => {
    card.addEventListener('click', () => openClientDetail(card.dataset.id));
  });
}

async function openClientDetail(id) {
  const client = await window.koseiAdminData?.getClient(id);
  if (!client) return;

  const prefs = client.posting_preferences || {};
  const integrations = (client.integrations_list || []).map(int => `
    <div class="ka-detail-row">
      <span class="ka-detail-label">${esc(int.platform || int.id)}</span>
      <span class="ka-badge ka-badge--${int.status || 'disconnected'}">${int.status || 'disconnected'}</span>
    </div>
  `).join('') || '<div class="ka-detail-row"><span class="ka-detail-label">No integrations</span></div>';

  const notes = (client.notes_list || []).map(n => `
    <div class="ka-note">
      <div class="ka-note-meta">${esc(n.author_name || 'Operator')} -- ${formatDate(n.created_at)} -- ${n.category || 'note'}</div>
      <div>${esc(n.content)}</div>
    </div>
  `).join('') || '<div style="color:var(--kosei-text-muted);font-size:0.8125rem;">No notes yet</div>';

  const html = `
    <div class="ka-detail-section">
      <h4>Client Info</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Name</span><span class="ka-detail-value">${esc(client.client_name || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Email</span><span class="ka-detail-value">${esc(client.client_email || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Tier</span><span class="ka-detail-value">${esc(client.tier || 'trial')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Status</span><span class="ka-badge ka-badge--${client.status}">${client.status}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Locale</span><span class="ka-detail-value">${(client.locale || 'en').toUpperCase()}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Timezone</span><span class="ka-detail-value">${esc(client.timezone || '--')}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Onboarding</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Step</span><span class="ka-detail-value">${client.onboarding_step || 0} / 5</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Complete</span><span class="ka-detail-value">${client.onboarding_complete ? 'Yes' : 'No'}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Posting Preferences</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Frequency</span><span class="ka-detail-value">${esc(prefs.frequency || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Days</span><span class="ka-detail-value">${(prefs.preferred_days || []).join(', ') || '--'}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Platforms</span><span class="ka-detail-value">${(prefs.platforms || []).join(', ') || '--'}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Platform Connections</h4>
      ${integrations}
    </div>

    <div class="ka-detail-section">
      <h4>Operator Notes</h4>
      <div class="ka-notes-list">${notes}</div>
      <div class="ka-note-add">
        <input id="noteInput" class="ka-note-input" placeholder="Add a note..." />
        <button class="ka-note-submit" onclick="submitNote('${client.id}')">Add</button>
      </div>
    </div>

    <div class="ka-detail-section">
      <h4>Timeline</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Created</span><span class="ka-detail-value">${formatDate(client.created_at)}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Tier Changed</span><span class="ka-detail-value">${formatDate(client.tier_changed_at)}</span></div>
    </div>
  `;

  showDetail(client.client_name || 'Client', html);
}

async function submitNote(workspaceId) {
  const input = document.getElementById('noteInput');
  if (!input || !input.value.trim()) return;

  await window.koseiAdminData?.addNote(workspaceId, input.value.trim(), 'follow_up');
  input.value = '';

  // Re-open to refresh notes
  openClientDetail(workspaceId);
}

// ============================================
// Trials rendering
// ============================================

function renderTrials(trials) {
  _trials = trials;
  const filter = document.getElementById('trialStatusFilter')?.value || 'all';
  const filtered = filter === 'all' ? trials : trials.filter(t => t.status === filter);

  const container = document.getElementById('trialsList');
  const countEl = document.getElementById('trialCount');
  if (countEl) countEl.textContent = `${filtered.length} of ${trials.length}`;

  if (filtered.length === 0) {
    container.innerHTML = '<div class="ka-empty">No trials found</div>';
    return;
  }

  container.innerHTML = filtered.map(trial => `
    <div class="ka-card" data-type="trial" data-id="${trial.id}">
      <div class="ka-card-top">
        <span class="ka-card-name">${esc(trial.client_email || trial.workspace_id || trial.id)}</span>
        <span class="ka-badge ka-badge--${trial.status || 'active'}">${trial.status || 'active'}</span>
      </div>
      <div class="ka-card-meta">
        <span>Days left: ${trial.days_remaining ?? '--'}</span>
        <span>Usage: ${trial.usage_count || 0}/${trial.usage_limit || 10}</span>
        <span>Platforms: ${trial.platforms_connected || 0}</span>
        <span>${formatDate(trial.started_at)}</span>
      </div>
    </div>
  `).join('');

  container.querySelectorAll('.ka-card').forEach(card => {
    card.addEventListener('click', () => openTrialDetail(card.dataset.id));
  });
}

async function openTrialDetail(id) {
  const trial = await window.koseiAdminData?.getTrial(id);
  if (!trial) return;

  const html = `
    <div class="ka-detail-section">
      <h4>Trial Info</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Workspace</span><span class="ka-detail-value">${esc(trial.workspace_id || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Email</span><span class="ka-detail-value">${esc(trial.client_email || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Status</span><span class="ka-badge ka-badge--${trial.status}">${trial.status}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Usage</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Days Remaining</span><span class="ka-detail-value">${trial.days_remaining ?? '--'}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Items Used</span><span class="ka-detail-value">${trial.usage_count || 0} / ${trial.usage_limit || 10}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Platforms Connected</span><span class="ka-detail-value">${trial.platforms_connected || 0}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Decision</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Action</span><span class="ka-detail-value">${esc(trial.decision || 'continue')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Reason</span><span class="ka-detail-value">${esc(trial.decision_reason || '--')}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Timeline</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Started</span><span class="ka-detail-value">${formatDate(trial.started_at)}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Expires</span><span class="ka-detail-value">${formatDate(trial.expires_at)}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Converted</span><span class="ka-detail-value">${formatDate(trial.converted_at)}</span></div>
    </div>

    ${trial.converted_to_tier ? `
    <div class="ka-detail-section">
      <h4>Conversion</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Converted To</span><span class="ka-detail-value">${esc(trial.converted_to_tier)}</span></div>
    </div>
    ` : ''}

    ${trial.cancellation_reason ? `
    <div class="ka-detail-section">
      <h4>Cancellation</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Reason</span><span class="ka-detail-value">${esc(trial.cancellation_reason)}</span></div>
    </div>
    ` : ''}
  `;

  showDetail(trial.client_email || 'Trial', html);
}

// ============================================
// Issues rendering
// ============================================

function renderIssues(issues) {
  _issues = issues;
  const statusFilter = document.getElementById('issueStatusFilter')?.value || 'all';
  const priorityFilter = document.getElementById('issuePriorityFilter')?.value || 'all';

  let filtered = issues;
  if (statusFilter !== 'all') {
    filtered = filtered.filter(i => i.status === statusFilter);
  }
  if (priorityFilter !== 'all') {
    filtered = filtered.filter(i => i.priority === priorityFilter);
  }

  const container = document.getElementById('issuesList');
  const countEl = document.getElementById('issueCount');
  if (countEl) countEl.textContent = `${filtered.length} of ${issues.length}`;

  if (filtered.length === 0) {
    container.innerHTML = '<div class="ka-empty">No issues found</div>';
    return;
  }

  container.innerHTML = filtered.map(issue => `
    <div class="ka-card" data-type="issue" data-id="${issue.id}">
      <div class="ka-card-top">
        <span class="ka-card-name">${esc(issue.title || 'Untitled')}</span>
        <span class="ka-badge ka-badge--${issue.status || 'open'}">${issue.status || 'open'}</span>
        <span class="ka-badge ka-badge--priority-${issue.priority || 'medium'}">${issue.priority || 'medium'}</span>
      </div>
      <div class="ka-card-meta">
        <span>${esc(issue.category || 'general')}</span>
        <span>WS: ${esc(issue.workspace_id?.slice(0, 8) || '--')}</span>
        ${issue.assigned_to ? `<span>Assigned: ${esc(issue.assigned_to)}</span>` : '<span style="color:var(--kosei-warning);">Unassigned</span>'}
        <span>${formatDate(issue.created_at)}</span>
      </div>
    </div>
  `).join('');

  container.querySelectorAll('.ka-card').forEach(card => {
    card.addEventListener('click', () => openIssueDetail(card.dataset.id));
  });
}

async function openIssueDetail(id) {
  const issue = await window.koseiAdminData?.getIssue(id);
  if (!issue) return;

  const statusOptions = ['open', 'in_progress', 'waiting_client', 'resolved', 'closed']
    .map(s => `<option value="${s}" ${issue.status === s ? 'selected' : ''}>${s.replace('_', ' ')}</option>`)
    .join('');

  const priorityOptions = ['low', 'medium', 'high', 'urgent']
    .map(p => `<option value="${p}" ${issue.priority === p ? 'selected' : ''}>${p}</option>`)
    .join('');

  const html = `
    <div class="ka-detail-section">
      <h4>Issue Details</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Title</span><span class="ka-detail-value">${esc(issue.title || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Category</span><span class="ka-detail-value">${esc(issue.category || 'general')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Workspace</span><span class="ka-detail-value">${esc(issue.workspace_id || '--')}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Author</span><span class="ka-detail-value">${esc(issue.author_role || 'client')}</span></div>
    </div>

    <div class="ka-detail-section">
      <h4>Description</h4>
      <div style="color:var(--kosei-text-muted);font-size:0.875rem;white-space:pre-wrap;">${esc(issue.description || 'No description provided.')}</div>
    </div>

    <div class="ka-detail-section">
      <h4>Triage</h4>
      <div class="ka-detail-row">
        <span class="ka-detail-label">Status</span>
        <select id="issueStatusSelect" class="ka-select" style="flex:1;">
          ${statusOptions}
        </select>
      </div>
      <div class="ka-detail-row">
        <span class="ka-detail-label">Priority</span>
        <select id="issuePrioritySelect" class="ka-select" style="flex:1;">
          ${priorityOptions}
        </select>
      </div>
      <div class="ka-detail-row">
        <span class="ka-detail-label">Assigned To</span>
        <input id="issueAssignedInput" class="ka-input" placeholder="Operator name or email" value="${esc(issue.assigned_to || '')}" style="flex:1;" />
      </div>
      <div style="margin-top:var(--space-md);">
        <button class="ka-btn ka-btn--primary" onclick="saveIssueTriage('${issue.id}')">Save Triage</button>
      </div>
    </div>

    ${issue.status !== 'resolved' && issue.status !== 'closed' ? `
    <div class="ka-detail-section">
      <h4>Resolve Issue</h4>
      <textarea id="issueResolutionInput" class="ka-textarea" placeholder="Resolution notes..." rows="3"></textarea>
      <div style="margin-top:var(--space-md);">
        <button class="ka-btn ka-btn--success" onclick="resolveIssueTriage('${issue.id}')">Mark Resolved</button>
      </div>
    </div>
    ` : `
    <div class="ka-detail-section">
      <h4>Resolution</h4>
      <div style="color:var(--kosei-text-muted);font-size:0.875rem;white-space:pre-wrap;">${esc(issue.resolution || 'No resolution notes.')}</div>
      <div class="ka-detail-row"><span class="ka-detail-label">Resolved</span><span class="ka-detail-value">${formatDate(issue.resolved_at)}</span></div>
    </div>
    `}

    ${issue.attachment_urls?.length ? `
    <div class="ka-detail-section">
      <h4>Attachments</h4>
      ${issue.attachment_urls.map(url => `<a href="${esc(url)}" target="_blank" rel="noopener" style="display:block;margin-bottom:var(--space-xs);color:var(--kosei-primary);">${esc(url.split('/').pop())}</a>`).join('')}
    </div>
    ` : ''}

    <div class="ka-detail-section">
      <h4>Timeline</h4>
      <div class="ka-detail-row"><span class="ka-detail-label">Created</span><span class="ka-detail-value">${formatDate(issue.created_at)}</span></div>
      <div class="ka-detail-row"><span class="ka-detail-label">Updated</span><span class="ka-detail-value">${formatDate(issue.updated_at)}</span></div>
    </div>
  `;

  showDetail(issue.title || 'Issue', html);
}

async function saveIssueTriage(issueId) {
  const status = document.getElementById('issueStatusSelect')?.value;
  const priority = document.getElementById('issuePrioritySelect')?.value;
  const assigned = document.getElementById('issueAssignedInput')?.value?.trim();

  try {
    if (status) {
      await window.koseiAdminData?.updateIssueStatus(issueId, status, assigned || null);
    }
    if (priority) {
      await window.koseiAdminData?.updateIssuePriority(issueId, priority);
    }
    openIssueDetail(issueId);
  } catch (err) {
    console.error('[Kosei Admin] Triage save error:', err);
  }
}

async function resolveIssueTriage(issueId) {
  const resolution = document.getElementById('issueResolutionInput')?.value?.trim();
  if (!resolution) {
    alert('Please enter resolution notes.');
    return;
  }

  try {
    await window.koseiAdminData?.resolveIssue(issueId, resolution);
    openIssueDetail(issueId);
  } catch (err) {
    console.error('[Kosei Admin] Resolve error:', err);
  }
}

// ============================================
// Detail panel
// ============================================

function showDetail(title, html) {
  const panel = document.getElementById('detailPanel');
  document.getElementById('detailTitle').textContent = title;
  document.getElementById('detailContent').innerHTML = html;
  panel.style.display = 'block';
}

function closeDetail() {
  document.getElementById('detailPanel').style.display = 'none';
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
  // Firestore Timestamp
  if (ts.toDate) {
    return ts.toDate().toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  }
  // ISO string or epoch
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric'
  });
}

// Export
if (typeof window !== 'undefined') {
  window.koseiAdminUI = {
    init: initUI,
    renderLeads,
    renderClients,
    renderTrials,
    renderIssues,
    closeDetail
  };

  // Make onclick handlers accessible
  window.submitNote = submitNote;
  window.saveIssueTriage = saveIssueTriage;
  window.resolveIssueTriage = resolveIssueTriage;
}
