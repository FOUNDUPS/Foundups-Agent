/**
 * Kosei Admin -- Authentication
 * Firebase Auth with admin-claim gating.
 * Per KOSEI_SERVICE_CONTRACT.md: admin requires `kosei_admin: true` custom claim.
 */

const KOSEI_FIREBASE_CONFIG = {
  apiKey: '',
  authDomain: 'gen-lang-client-0061781628.firebaseapp.com',
  projectId: 'gen-lang-client-0061781628',
  storageBucket: 'gen-lang-client-0061781628.firebasestorage.app',
  messagingSenderId: '',
  appId: ''
};

let _firebaseApp = null;
let _auth = null;
let _db = null;
let _currentUser = null;

/**
 * Initialize Firebase and auth listener.
 */
async function initAdmin() {
  // Try Firebase Hosting auto-config
  try {
    const resp = await fetch('/__/firebase/init.json', { cache: 'no-store' });
    if (resp.ok) {
      const config = await resp.json();
      Object.assign(KOSEI_FIREBASE_CONFIG, config);
    }
  } catch (_) {
    // No hosting config -- use defaults
  }

  if (KOSEI_FIREBASE_CONFIG.apiKey && typeof firebase !== 'undefined') {
    try {
      _firebaseApp = firebase.initializeApp(KOSEI_FIREBASE_CONFIG);
    } catch (e) {
      // App may already be initialized
      _firebaseApp = firebase.app();
    }
    _auth = firebase.auth();
    _db = firebase.firestore();
  }

  // Auth state listener
  if (_auth) {
    _auth.onAuthStateChanged(handleAuthChange);
  }

  // Sign-in button
  document.getElementById('googleSignIn')?.addEventListener('click', signInWithGoogle);
  document.getElementById('signOutBtn')?.addEventListener('click', signOut);
}

/**
 * Handle auth state changes.
 */
async function handleAuthChange(user) {
  const authGate = document.getElementById('authGate');
  const adminShell = document.getElementById('adminShell');
  const authError = document.getElementById('authError');

  if (!user) {
    // Not signed in -- show auth gate
    authGate.style.display = 'flex';
    adminShell.style.display = 'none';
    _currentUser = null;
    return;
  }

  // Check admin claim
  const idTokenResult = await user.getIdTokenResult();
  const isAdmin = idTokenResult.claims.kosei_admin === true;

  if (!isAdmin) {
    // Signed in but not admin -- show error, don't grant access
    authGate.style.display = 'flex';
    adminShell.style.display = 'none';
    authError.textContent = 'Access denied. Admin privileges required.';
    authError.style.display = 'block';
    console.warn('[Kosei Admin] User lacks kosei_admin claim:', user.email);
    return;
  }

  // Authenticated admin
  _currentUser = user;
  authGate.style.display = 'none';
  adminShell.style.display = 'flex';
  authError.style.display = 'none';

  document.getElementById('adminEmail').textContent = user.email || '';

  // Initialize data + UI
  window.koseiAdminData?.init(_db);
  window.koseiAdminUI?.init();

  console.log('[Kosei Admin] Authenticated:', user.email);
}

/**
 * Sign in with Google.
 */
async function signInWithGoogle() {
  if (!_auth) {
    showAuthError('Firebase not configured. Set API key in environment.');
    return;
  }

  try {
    const provider = new firebase.auth.GoogleAuthProvider();
    await _auth.signInWithPopup(provider);
  } catch (e) {
    console.error('[Kosei Admin] Sign-in failed:', e);
    showAuthError(e.message || 'Sign-in failed');
  }
}

/**
 * Sign out.
 */
async function signOut() {
  if (_auth) {
    await _auth.signOut();
  }
}

function showAuthError(msg) {
  const el = document.getElementById('authError');
  if (el) {
    el.textContent = msg;
    el.style.display = 'block';
  }
}

/**
 * Get Firestore instance (for use by other modules).
 */
function getDb() {
  return _db;
}

function getCurrentUser() {
  return _currentUser;
}

// Export
if (typeof window !== 'undefined') {
  window.koseiAdminAuth = {
    init: initAdmin,
    getDb,
    getCurrentUser,
    signOut
  };
}
