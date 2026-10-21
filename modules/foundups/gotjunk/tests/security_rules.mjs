// Run with Firebase emulators; see SECURITY.md. No production project is used.
import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(process.env.SECURITY_NODE_MODULES ? `${process.env.SECURITY_NODE_MODULES}/../package.json` : import.meta.url);
const { initializeTestEnvironment, assertSucceeds, assertFails } = require('@firebase/rules-unit-testing');
const { doc, setDoc, updateDoc, getDoc, deleteDoc, Timestamp } = require('firebase/firestore');
const { ref, uploadBytes, deleteObject } = require('firebase/storage');
const root = new URL('../', import.meta.url);
let env;
const auth = uid => env.authenticatedContext(uid);
const item = () => ({ id: 'item', ownerUid: 'alice', status: 'listed', createdAt: Timestamp.now(), updatedAt: Timestamp.now() });
const message = (uid, id='m1') => ({ id, authorId: uid, text: 'hello', createdAt: Date.now() });
const thread = () => ({ threadKey: 'thread', ownerUid: 'alice', status: 'active', messages: [message('alice')], createdAt: Timestamp.now(), updatedAt: Timestamp.now() });
async function seed(collection, id, data) { await env.withSecurityRulesDisabled(c => setDoc(doc(c.firestore(), collection, id), data)); }
before(async () => {
  env = await initializeTestEnvironment({ projectId: 'demo-gotjunk-security',
    firestore: { rules: readFileSync(new URL('firestore.rules', root), 'utf8') },
    storage: { rules: readFileSync(new URL('storage.rules', root), 'utf8') } });
});
beforeEach(async () => { await env.clearFirestore(); await env.clearStorage(); });
after(async () => { await env?.cleanup(); });
test('both deployment entry points use canonical identical rules', () => {
  assert.equal(JSON.parse(readFileSync(new URL('frontend/firebase.json', root))).firestore.rules, 'firestore.rules');
  assert.equal(readFileSync(new URL('firestore.rules', root), 'utf8'), readFileSync(new URL('frontend/firestore.rules', root), 'utf8'));
});
test('storage requires path ownership for create, replace and delete', async () => {
  const target = c => ref(c.storage(), 'items/alice/photo');
  const image = new Uint8Array([1,2,3]); const type = { contentType: 'image/png' };
  await assertFails(uploadBytes(target(env.unauthenticatedContext()), image, type));
  await assertFails(uploadBytes(target(auth('bob')), image, type));
  await assertSucceeds(uploadBytes(target(auth('alice')), image, type));
  await assertFails(uploadBytes(target(auth('bob')), image, type));
  await assertFails(deleteObject(target(auth('bob'))));
  await assertSucceeds(deleteObject(target(auth('alice'))));
  await assertFails(uploadBytes(target(auth('alice')), image, { contentType: 'image/svg+xml' }));
});
test('item owner cannot transfer ownership or forge initial moderation', async () => {
  const target = doc(auth('alice').firestore(), 'gotjunk_items/item');
  await assertFails(setDoc(target, { ...item(), moderationStatus: 'cleared' }));
  await assertSucceeds(setDoc(target, item()));
  await assertFails(updateDoc(target, { ownerUid: 'bob' }));
  await assertSucceeds(updateDoc(target, { status: 'purchased' }));
});
test('public threads append own messages; history and authors remain immutable', async () => {
  const original = thread();
  await seed('gotjunk_messages', 'thread', original);
  const target = doc(auth('bob').firestore(), 'gotjunk_messages/thread');
  await assertSucceeds(updateDoc(target, { messages: [...original.messages, message('bob', 'm2')] }));
  const current = (await getDoc(target)).data();
  await assertFails(updateDoc(target, { messages: [message('bob')] }));
  await assertFails(updateDoc(target, { ownerUid: 'bob' }));
  await assertFails(updateDoc(target, { status: 'closed' }));
  await assertFails(updateDoc(target, { messages: [...current.messages, message('alice', 'm3')] }));
  await assertFails(deleteDoc(target));
  const owner = doc(auth('alice').firestore(), 'gotjunk_messages/thread');
  await assertSucceeds(updateDoc(owner, { status: 'closed' }));
  await assertFails(updateDoc(target, { messages: [...current.messages, message('bob', 'm3')] }));
});
test('new thread cannot impersonate another message author', async () => {
  const target = doc(auth('alice').firestore(), 'gotjunk_messages/thread');
  await assertFails(setDoc(target, { ...thread(), messages: [message('bob')] }));
  await assertSucceeds(setDoc(target, thread()));
});
test('one vote per principal; no forged aggregates or rewritten votes', async () => {
  await seed('gotjunk_items', 'item', item());
  const target = doc(auth('bob').firestore(), 'gotjunk_items/item');
  await assertFails(updateDoc(target, { moderationVotes: { keep: [], remove: ['alice', 'bob'] } }));
  await assertSucceeds(updateDoc(target, { moderationVotes: { keep: [], remove: ['bob'] } }));
  await assertFails(updateDoc(target, { moderationVotes: { keep: ['bob'], remove: [] } }));
  await assertFails(updateDoc(target, { moderationStatus: 'hidden', reportCount: 500 }));
  const carol = doc(auth('carol').firestore(), 'gotjunk_items/item');
  await assertSucceeds(updateDoc(carol, { moderationVotes: { keep: ['carol'], remove: ['bob'] } }));
});
test('reservation is caller-bound, bounded and cannot steal another live reservation', async () => {
  await seed('gotjunk_items', 'item', item());
  const target = doc(auth('bob').firestore(), 'gotjunk_items/item');
  const now = Date.now();
  await assertFails(updateDoc(target, { cartReservation: { reservedBy: 'alice', reservedAt: now, expiresAt: now+200000 } }));
  await assertFails(updateDoc(target, { cartReservation: { reservedBy: 'bob', reservedAt: now, expiresAt: now+900000 } }));
  await assertSucceeds(updateDoc(target, { cartReservation: { reservedBy: 'bob', reservedAt: now, expiresAt: now+200000 } }));
  const carol = doc(auth('carol').firestore(), 'gotjunk_items/item');
  await assertFails(updateDoc(carol, { cartReservation: null }));
  await assertFails(updateDoc(carol, { cartReservation: { reservedBy: 'carol', reservedAt: now, expiresAt: now+200000 } }));
  await assertSucceeds(updateDoc(target, { cartReservation: null }));
  await assertSucceeds(updateDoc(carol, { cartReservation: { reservedBy: 'carol', reservedAt: now, expiresAt: now+200000 } }));
});

// Execute production TypeScript sync functions with actual emulator-backed SDKs.
// Only configuration/identity and unused context-key helpers are substituted.
async function loadSync(relativePath, uid) {
  const vm = await import('node:vm');
  const ts = require('typescript');
  const source = readFileSync(new URL(relativePath, root), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  const db = auth(uid).firestore();
  const dependencies = name => {
    if (name.endsWith('firebaseConfig')) return { getFirestoreDb: () => db, getFirebaseStorage: () => auth(uid).storage(), isFirebaseConfigured: () => true };
    if (name.endsWith('firebaseAuth')) return { getCurrentUserId: () => uid };
    if (name.endsWith('messageStorage')) return { contextKey: () => 'thread' };
    return require(name);
  };
  vm.runInThisContext('(function(require,module,exports){'+js+'\n})')(dependencies, module, module.exports);
  return module.exports;
}
test('production message sync merges concurrent authors without history loss', async () => {
  const alice = await loadSync('frontend/src/message/messageSync.ts', 'alice');
  const bob = await loadSync('frontend/src/message/messageSync.ts', 'bob');
  const local = (uid,id) => ({ context: { type: 'item', itemId: 'item' }, metadata: { status: 'active' }, messages: [message(uid,id)] });
  assert.equal(await alice.syncThreadToCloud('thread', local('alice','first')), true);
  const outcomes = await Promise.all([
    alice.syncThreadToCloud('thread', local('alice','second')),
    bob.syncThreadToCloud('thread', local('bob','third')),
  ]);
  assert.deepEqual(outcomes, [true,true]);
  const target = doc(auth('alice').firestore(), 'gotjunk_messages/thread');
  assert.deepEqual((await getDoc(target)).data().messages.map(m=>m.id).sort(), ['first','second','third']);
  // Replaying a local snapshot must not duplicate cloud messages.
  assert.equal(await alice.syncThreadToCloud('thread', local('alice','second')), true);
  assert.equal((await getDoc(target)).data().messages.length, 3);
});
test('production voting transaction retains concurrent voters', async () => {
  await seed('gotjunk_items', 'item', item());
  const bob = await loadSync('frontend/services/firestoreSync.ts', 'bob');
  const carol = await loadSync('frontend/services/firestoreSync.ts', 'carol');
  await Promise.all([bob.voteOnItem('item','keep'), carol.voteOnItem('item','remove')]);
  const data = (await getDoc(doc(auth('bob').firestore(), 'gotjunk_items/item'))).data();
  assert.deepEqual(data.moderationVotes, {keep:['bob'],remove:['carol']});
});
