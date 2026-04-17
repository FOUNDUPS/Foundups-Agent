/**
 * Kosei AI Systems - Intake Form Handler
 * Writes audit requests to Firestore (kosei_audit_requests collection)
 * Uses Firebase SDK loaded from CDN
 */

// Firebase configuration (shared project)
const KOSEI_FIREBASE_CONFIG = {
  apiKey: '', // Set via env or Firebase Hosting auto-config
  authDomain: 'gen-lang-client-0061781628.firebaseapp.com',
  projectId: 'gen-lang-client-0061781628',
  storageBucket: 'gen-lang-client-0061781628.firebasestorage.app',
  messagingSenderId: '',
  appId: ''
};

let firebaseApp = null;
let firestoreDb = null;

/**
 * Initialize Firebase (lazy)
 * Uses Firebase Hosting auto-config if available
 */
async function initKoseiFirebase() {
  if (firebaseApp) return firebaseApp;

  // Check for Firebase Hosting auto-config
  if (typeof firebase !== 'undefined' && firebase.apps?.length > 0) {
    firebaseApp = firebase.apps[0];
    firestoreDb = firebase.firestore();
    console.log('[Kosei] Using existing Firebase app');
    return firebaseApp;
  }

  // Try Firebase Hosting auto-init
  try {
    const response = await fetch('/__/firebase/init.json', { cache: 'no-store' });
    if (response.ok) {
      const config = await response.json();
      Object.assign(KOSEI_FIREBASE_CONFIG, config);
    }
  } catch (e) {
    console.log('[Kosei] No Firebase Hosting config, using defaults');
  }

  // Initialize if config is valid
  if (KOSEI_FIREBASE_CONFIG.apiKey && typeof firebase !== 'undefined') {
    try {
      firebaseApp = firebase.initializeApp(KOSEI_FIREBASE_CONFIG);
      firestoreDb = firebase.firestore();
      console.log('[Kosei] Firebase initialized');
    } catch (e) {
      console.error('[Kosei] Firebase init failed:', e);
    }
  }

  return firebaseApp;
}

/**
 * Get Firestore instance
 */
async function getKoseiFirestore() {
  if (firestoreDb) return firestoreDb;
  await initKoseiFirebase();
  return firestoreDb;
}

/**
 * Submit audit request to Firestore
 */
async function submitAuditRequest(formData) {
  const db = await getKoseiFirestore();

  // Build audit request document per KOSEI_DATA_MODEL.md
  const auditRequest = {
    // Identity
    created_at: firebase.firestore.FieldValue.serverTimestamp(),
    updated_at: firebase.firestore.FieldValue.serverTimestamp(),

    // Lead source
    lead_source: 'web_form',
    referral_code: formData.referral || null,

    // Contact
    contact_email: formData.email,
    contact_name: formData.name || null,
    business_name: formData.business || null,
    locale: window.koseiI18n?.getLocale() || 'en',

    // Audit input
    content_urls: [], // Empty for now, user provides handle
    platform_handles: buildPlatformHandles(formData),
    business_goals: formData.goals || null,
    current_posting_frequency: formData.frequency || null,

    // Audit output (pending)
    audit_status: 'pending',
    gaps: null,
    recommendations: null,
    recommended_tier: null,
    audit_completed_at: null,

    // Funnel tracking
    trial_offered: false,
    trial_accepted: false,
    workspace_id: null,
    converted_at: null
  };

  // Write to Firestore if available
  if (db) {
    try {
      const docRef = await db.collection('kosei_audit_requests').add(auditRequest);
      console.log('[Kosei] Audit request submitted:', docRef.id);
      return { success: true, id: docRef.id };
    } catch (e) {
      console.error('[Kosei] Firestore write failed:', e);
      // Fall through to localStorage backup
    }
  }

  // Fallback: store locally if Firestore unavailable
  return storeLocalAuditRequest(auditRequest);
}

/**
 * Build platform_handles object from form checkboxes
 */
function buildPlatformHandles(formData) {
  const handles = {};
  const platforms = ['youtube', 'linkedin', 'x', 'instagram', 'tiktok', 'other'];

  platforms.forEach(p => {
    if (formData.platforms?.includes(p)) {
      handles[p] = formData.handle || '';
    }
  });

  return handles;
}

/**
 * Fallback: store audit request in localStorage for later sync
 */
function storeLocalAuditRequest(auditRequest) {
  const localKey = 'kosei_pending_audits';
  const pending = JSON.parse(localStorage.getItem(localKey) || '[]');

  auditRequest.local_id = `local_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  auditRequest.created_at = new Date().toISOString();
  auditRequest.updated_at = new Date().toISOString();

  pending.push(auditRequest);
  localStorage.setItem(localKey, JSON.stringify(pending));

  console.log('[Kosei] Audit request stored locally:', auditRequest.local_id);
  return { success: true, id: auditRequest.local_id, local: true };
}

/**
 * Initialize intake form handler
 */
function initKoseiIntakeForm() {
  const form = document.getElementById('koseiIntakeForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = form.querySelector('[type="submit"]');
    const statusEl = document.getElementById('formStatus');

    // Disable button during submission
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');

    // Gather form data
    const formData = {
      name: form.querySelector('[name="name"]')?.value?.trim(),
      email: form.querySelector('[name="email"]')?.value?.trim(),
      business: form.querySelector('[name="business"]')?.value?.trim(),
      handle: form.querySelector('[name="handle"]')?.value?.trim(),
      frequency: form.querySelector('[name="frequency"]')?.value,
      goals: form.querySelector('[name="goals"]')?.value?.trim(),
      platforms: Array.from(form.querySelectorAll('[name="platforms"]:checked'))
        .map(cb => cb.value),
      referral: new URLSearchParams(window.location.search).get('ref')
    };

    // Validate
    if (!formData.email) {
      showFormStatus(statusEl, window.koseiI18n?.t('form_error') || 'Email required', 'error');
      submitBtn.disabled = false;
      submitBtn.classList.remove('loading');
      return;
    }

    // Submit
    const result = await submitAuditRequest(formData);

    if (result.success) {
      showFormStatus(statusEl, window.koseiI18n?.t('form_success'), 'success');
      form.reset();

      // Track conversion (future analytics)
      if (typeof gtag !== 'undefined') {
        gtag('event', 'audit_request', { event_category: 'conversion' });
      }
    } else {
      showFormStatus(statusEl, window.koseiI18n?.t('form_error'), 'error');
    }

    submitBtn.disabled = false;
    submitBtn.classList.remove('loading');
  });

  // Initialize Firebase in background
  initKoseiFirebase();
}

/**
 * Show form status message
 */
function showFormStatus(el, message, type) {
  if (!el) return;
  el.textContent = message;
  el.className = `form-status ${type}`;
  el.style.display = 'block';

  if (type === 'success') {
    setTimeout(() => { el.style.display = 'none'; }, 5000);
  }
}

// Export
if (typeof window !== 'undefined') {
  window.koseiIntake = {
    init: initKoseiIntakeForm,
    submit: submitAuditRequest
  };
}
