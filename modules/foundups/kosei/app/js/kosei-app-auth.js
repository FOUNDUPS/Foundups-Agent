/**
 * Kosei Client Workspace -- Authentication
 * Firebase Auth gating (no admin claim required).
 * Per KOSEI_SERVICE_CONTRACT.md Section 1.2:
 *   Client workspace requires Firebase Auth (email/password or Google OAuth).
 *   Workspace scoped by auth.uid via owner_uid field.
 *
 * Boundary: This is NOT the admin surface. No admin claim check.
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
async function initApp() {
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

  // Sign-in buttons
  document.getElementById('googleSignIn')?.addEventListener('click', signInWithGoogle);
  document.getElementById('emailSignIn')?.addEventListener('click', signInWithEmail);
  document.getElementById('signOutBtn')?.addEventListener('click', signOut);
}

/**
 * Handle auth state changes.
 * Client workspace: any authenticated user can enter. Workspace scoping
 * is done at the data layer (owner_uid match).
 */
async function handleAuthChange(user) {
  const authGate = document.getElementById('authGate');
  const appShell = document.getElementById('appShell');

  if (!user) {
    authGate.style.display = 'flex';
    appShell.style.display = 'none';
    _currentUser = null;
    return;
  }

  // Authenticated client
  _currentUser = user;
  authGate.style.display = 'none';
  appShell.style.display = 'flex';

  document.getElementById('clientEmail').textContent = user.email || user.displayName || 'Client';

  // Initialize data + UI
  window.koseiAppData?.init(_db, user.uid);
  window.koseiAppUI?.init();

  console.log('[Kosei App] Authenticated:', user.email || user.uid);
}

/**
 * Sign in with Google.
 */
async function signInWithGoogle() {
  if (!_auth) {
    showAuthError('Firebase not configured.');
    return;
  }
  try {
    const provider = new firebase.auth.GoogleAuthProvider();
    await _auth.signInWithPopup(provider);
  } catch (e) {
    console.error('[Kosei App] Google sign-in failed:', e);
    showAuthError(e.message || 'Sign-in failed');
  }
}

/**
 * Sign in with email/password.
 */
async function signInWithEmail() {
  if (!_auth) {
    showAuthError('Firebase not configured.');
    return;
  }
  const email = document.getElementById('emailInput')?.value?.trim();
  const password = document.getElementById('passwordInput')?.value;

  if (!email || !password) {
    showAuthError('Enter your email and password.');
    return;
  }

  try {
    await _auth.signInWithEmailAndPassword(email, password);
  } catch (e) {
    console.error('[Kosei App] Email sign-in failed:', e);
    showAuthError(e.message || 'Sign-in failed');
  }
}

/**
 * Sign out.
 */
async function signOut() {
  if (_auth) {
    await _auth.signOut();
    window.koseiAppData?.destroy();
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
 * Get Firestore instance.
 */
function getDb() {
  return _db;
}

function getCurrentUser() {
  return _currentUser;
}

// Export
if (typeof window !== 'undefined') {
  window.koseiAppAuth = {
    init: initApp,
    getDb,
    getCurrentUser,
    signOut
  };
}
