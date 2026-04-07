/**
 * Kosei Admin -- Data Layer
 * Reads from Firestore collections defined in KOSEI_DATA_MODEL.md.
 * All collection names match the canonical data model.
 *
 * Collections:
 *   kosei_audit_requests  -- lead intake records
 *   kosei_workspaces      -- client workspace roots
 *   kosei_trials           -- trial state documents
 *   kosei_issues           -- client feedback/issues
 *
 * This module is read-only in Phase 1. Write operations (notes, status updates)
 * are stubbed and will be wired when Cloud Functions are deployed.
 */

let _db = null;

// Unsubscribe handles for real-time listeners
let _unsubLeads = null;
let _unsubClients = null;
let _unsubTrials = null;
let _unsubIssues = null;

/**
 * Initialize data layer with Firestore instance.
 */
function initData(db) {
  _db = db;
  if (_db) {
    subscribeLeads();
    subscribeClients();
    subscribeTrials();
    subscribeIssues();
  }
}

// ============================================
// Leads (kosei_audit_requests)
// ============================================

function subscribeLeads() {
  if (_unsubLeads) _unsubLeads();
  if (!_db) return;

  _unsubLeads = _db
    .collection('kosei_audit_requests')
    .orderBy('created_at', 'desc')
    .limit(100)
    .onSnapshot(
      snapshot => {
        const leads = [];
        snapshot.forEach(doc => {
          leads.push({ id: doc.id, ...doc.data() });
        });
        window.koseiAdminUI?.renderLeads(leads);
      },
      err => {
        console.error('[Kosei Admin] Leads subscription error:', err);
        window.koseiAdminUI?.renderLeads([]);
      }
    );
}

/**
 * Get single lead by ID.
 */
async function getLead(id) {
  if (!_db) return null;
  const doc = await _db.collection('kosei_audit_requests').doc(id).get();
  return doc.exists ? { id: doc.id, ...doc.data() } : null;
}

/**
 * Update audit status on a lead. (Phase 1: direct write, Phase 2: Cloud Function)
 */
async function updateLeadStatus(id, newStatus) {
  if (!_db) return;
  await _db.collection('kosei_audit_requests').doc(id).update({
    audit_status: newStatus,
    updated_at: firebase.firestore.FieldValue.serverTimestamp()
  });
}

// ============================================
// Clients (kosei_workspaces)
// ============================================

function subscribeClients() {
  if (_unsubClients) _unsubClients();
  if (!_db) return;

  _unsubClients = _db
    .collection('kosei_workspaces')
    .orderBy('created_at', 'desc')
    .limit(100)
    .onSnapshot(
      snapshot => {
        const clients = [];
        snapshot.forEach(doc => {
          clients.push({ id: doc.id, ...doc.data() });
        });
        window.koseiAdminUI?.renderClients(clients);
      },
      err => {
        console.error('[Kosei Admin] Clients subscription error:', err);
        window.koseiAdminUI?.renderClients([]);
      }
    );
}

/**
 * Get single client workspace by ID.
 */
async function getClient(id) {
  if (!_db) return null;
  const doc = await _db.collection('kosei_workspaces').doc(id).get();
  if (!doc.exists) return null;

  const data = { id: doc.id, ...doc.data() };

  // Fetch subcollections: integrations, notes
  const intSnap = await _db.collection('kosei_workspaces').doc(id)
    .collection('integrations').get();
  data.integrations_list = [];
  intSnap.forEach(d => data.integrations_list.push({ id: d.id, ...d.data() }));

  const notesSnap = await _db.collection('kosei_workspaces').doc(id)
    .collection('notes').orderBy('created_at', 'desc').limit(20).get();
  data.notes_list = [];
  notesSnap.forEach(d => data.notes_list.push({ id: d.id, ...d.data() }));

  return data;
}

/**
 * Add operator note to a workspace.
 */
async function addNote(workspaceId, content, category) {
  if (!_db) return;
  const user = window.koseiAdminAuth?.getCurrentUser();
  await _db.collection('kosei_workspaces').doc(workspaceId)
    .collection('notes').add({
      author_uid: user?.uid || 'unknown',
      author_name: user?.displayName || user?.email || 'Operator',
      content: content,
      category: category || 'follow_up',
      created_at: firebase.firestore.FieldValue.serverTimestamp(),
      pinned: false
    });
}

// ============================================
// Trials (kosei_trials)
// ============================================

function subscribeTrials() {
  if (_unsubTrials) _unsubTrials();
  if (!_db) return;

  _unsubTrials = _db
    .collection('kosei_trials')
    .orderBy('started_at', 'desc')
    .limit(100)
    .onSnapshot(
      snapshot => {
        const trials = [];
        snapshot.forEach(doc => {
          trials.push({ id: doc.id, ...doc.data() });
        });
        window.koseiAdminUI?.renderTrials(trials);
      },
      err => {
        console.error('[Kosei Admin] Trials subscription error:', err);
        window.koseiAdminUI?.renderTrials([]);
      }
    );
}

/**
 * Get single trial by ID.
 */
async function getTrial(id) {
  if (!_db) return null;
  const doc = await _db.collection('kosei_trials').doc(id).get();
  return doc.exists ? { id: doc.id, ...doc.data() } : null;
}

// ============================================
// Issues (kosei_issues)
// ============================================

function subscribeIssues() {
  if (_unsubIssues) _unsubIssues();
  if (!_db) return;

  _unsubIssues = _db
    .collection('kosei_issues')
    .orderBy('created_at', 'desc')
    .limit(100)
    .onSnapshot(
      snapshot => {
        const issues = [];
        snapshot.forEach(doc => {
          issues.push({ id: doc.id, ...doc.data() });
        });
        window.koseiAdminUI?.renderIssues(issues);
      },
      err => {
        console.error('[Kosei Admin] Issues subscription error:', err);
        window.koseiAdminUI?.renderIssues([]);
      }
    );
}

async function getIssuesForWorkspace(workspaceId) {
  if (!_db) return [];
  const snap = await _db.collection('kosei_issues')
    .where('workspace_id', '==', workspaceId)
    .orderBy('created_at', 'desc')
    .limit(20)
    .get();
  const issues = [];
  snap.forEach(d => issues.push({ id: d.id, ...d.data() }));
  return issues;
}

/**
 * Get single issue by ID.
 */
async function getIssue(id) {
  if (!_db) return null;
  const doc = await _db.collection('kosei_issues').doc(id).get();
  return doc.exists ? { id: doc.id, ...doc.data() } : null;
}

/**
 * Update issue status (triage).
 */
async function updateIssueStatus(id, newStatus, assignedTo) {
  if (!_db) return;
  const update = {
    status: newStatus,
    updated_at: firebase.firestore.FieldValue.serverTimestamp()
  };
  if (assignedTo !== undefined) {
    update.assigned_to = assignedTo;
  }
  await _db.collection('kosei_issues').doc(id).update(update);
}

/**
 * Resolve an issue with resolution text.
 */
async function resolveIssue(id, resolution) {
  if (!_db) return;
  await _db.collection('kosei_issues').doc(id).update({
    status: 'resolved',
    resolution: resolution,
    resolved_at: firebase.firestore.FieldValue.serverTimestamp(),
    updated_at: firebase.firestore.FieldValue.serverTimestamp()
  });
}

/**
 * Update issue priority.
 */
async function updateIssuePriority(id, priority) {
  if (!_db) return;
  await _db.collection('kosei_issues').doc(id).update({
    priority: priority,
    updated_at: firebase.firestore.FieldValue.serverTimestamp()
  });
}

// ============================================
// Cleanup
// ============================================

function destroy() {
  if (_unsubLeads) _unsubLeads();
  if (_unsubClients) _unsubClients();
  if (_unsubTrials) _unsubTrials();
  if (_unsubIssues) _unsubIssues();
  _db = null;
}

// Export
if (typeof window !== 'undefined') {
  window.koseiAdminData = {
    init: initData,
    destroy,
    getLead,
    getClient,
    getTrial,
    getIssue,
    getIssuesForWorkspace,
    updateLeadStatus,
    updateIssueStatus,
    updateIssuePriority,
    resolveIssue,
    addNote
  };
}
