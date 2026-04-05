/**
 * Kosei Client Workspace -- Data Layer
 * Reads client-safe fields from Firestore, scoped by owner_uid.
 *
 * Collections read:
 *   kosei_workspaces/{id}                      -- workspace root
 *   kosei_workspaces/{id}/integrations/{plat}  -- platform connections
 *   kosei_workspaces/{id}/content_queue/{item}  -- content items
 *   kosei_workspaces/{id}/post_history/{post}   -- published posts
 *   kosei_trials/{id}                           -- trial state (where workspace_id matches)
 *
 * Collections written:
 *   kosei_issues                                -- client feedback/issue submission
 *
 * NOT read (admin-only):
 *   kosei_workspaces/{id}/notes                 -- operator notes
 *   kosei_audit_requests                        -- lead pipeline
 */

let _db = null;
let _uid = null;
let _workspaceId = null;

// Unsubscribe handles
let _unsubWorkspace = null;

/**
 * Initialize data layer. Looks up workspace by owner_uid.
 */
async function initData(db, uid) {
  _db = db;
  _uid = uid;
  if (!_db || !_uid) return;

  // Find workspace owned by this user
  const snap = await _db.collection('kosei_workspaces')
    .where('owner_uid', '==', _uid)
    .limit(1)
    .get();

  if (snap.empty) {
    window.koseiAppUI?.showNoWorkspace();
    return;
  }

  const doc = snap.docs[0];
  _workspaceId = doc.id;

  // Subscribe to workspace changes
  subscribeWorkspace();
}

// ============================================
// Workspace subscription
// ============================================

function subscribeWorkspace() {
  if (_unsubWorkspace) _unsubWorkspace();
  if (!_db || !_workspaceId) return;

  _unsubWorkspace = _db
    .collection('kosei_workspaces')
    .doc(_workspaceId)
    .onSnapshot(
      async docSnap => {
        if (!docSnap.exists) {
          window.koseiAppUI?.showNoWorkspace();
          return;
        }

        const workspace = { id: docSnap.id, ...docSnap.data() };

        // Fetch subcollections in parallel
        const [integrations, contentQueue, postHistory, trial] = await Promise.all([
          fetchIntegrations(),
          fetchContentQueue(),
          fetchPostHistory(),
          fetchTrial()
        ]);

        window.koseiAppUI?.renderDashboard({
          workspace,
          integrations,
          contentQueue,
          postHistory,
          trial
        });
      },
      err => {
        console.error('[Kosei App] Workspace subscription error:', err);
      }
    );
}

// ============================================
// Subcollection fetches
// ============================================

async function fetchIntegrations() {
  if (!_db || !_workspaceId) return [];
  const snap = await _db.collection('kosei_workspaces').doc(_workspaceId)
    .collection('integrations').get();
  const items = [];
  snap.forEach(d => items.push({ id: d.id, ...d.data() }));
  return items;
}

async function fetchContentQueue() {
  if (!_db || !_workspaceId) return [];
  const snap = await _db.collection('kosei_workspaces').doc(_workspaceId)
    .collection('content_queue')
    .orderBy('created_at', 'desc')
    .limit(50)
    .get();
  const items = [];
  snap.forEach(d => items.push({ id: d.id, ...d.data() }));
  return items;
}

async function fetchPostHistory() {
  if (!_db || !_workspaceId) return [];
  const snap = await _db.collection('kosei_workspaces').doc(_workspaceId)
    .collection('post_history')
    .orderBy('published_at', 'desc')
    .limit(50)
    .get();
  const items = [];
  snap.forEach(d => items.push({ id: d.id, ...d.data() }));
  return items;
}

async function fetchTrial() {
  if (!_db || !_workspaceId) return null;
  // Trial ID matches workspace ID per KOSEI_DATA_MODEL.md
  const doc = await _db.collection('kosei_trials').doc(_workspaceId).get();
  return doc.exists ? { id: doc.id, ...doc.data() } : null;
}

// ============================================
// Client issues (write)
// ============================================

/**
 * Submit a client feedback/issue.
 * Per KOSEI_DATA_MODEL.md Section 7: kosei_issues collection.
 */
async function submitIssue(title, description, category) {
  if (!_db || !_workspaceId) return null;
  const user = window.koseiAppAuth?.getCurrentUser();

  const issue = {
    workspace_id: _workspaceId,
    author_uid: user?.uid || 'unknown',
    author_role: 'client',
    title: title,
    description: description,
    category: category || 'general',
    priority: 'medium',
    status: 'open',
    created_at: firebase.firestore.FieldValue.serverTimestamp(),
    updated_at: firebase.firestore.FieldValue.serverTimestamp()
  };

  const docRef = await _db.collection('kosei_issues').add(issue);
  console.log('[Kosei App] Issue submitted:', docRef.id);
  return { id: docRef.id };
}

/**
 * Fetch client's own issues.
 */
async function fetchMyIssues() {
  if (!_db || !_workspaceId) return [];
  const snap = await _db.collection('kosei_issues')
    .where('workspace_id', '==', _workspaceId)
    .orderBy('created_at', 'desc')
    .limit(20)
    .get();
  const items = [];
  snap.forEach(d => items.push({ id: d.id, ...d.data() }));
  return items;
}

// ============================================
// Getters
// ============================================

function getWorkspaceId() {
  return _workspaceId;
}

// ============================================
// Cleanup
// ============================================

function destroy() {
  if (_unsubWorkspace) _unsubWorkspace();
  _db = null;
  _uid = null;
  _workspaceId = null;
}

// Export
if (typeof window !== 'undefined') {
  window.koseiAppData = {
    init: initData,
    destroy,
    getWorkspaceId,
    fetchIntegrations,
    fetchContentQueue,
    fetchPostHistory,
    fetchTrial,
    fetchMyIssues,
    submitIssue
  };
}
