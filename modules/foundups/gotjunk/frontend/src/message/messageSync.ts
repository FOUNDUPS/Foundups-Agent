/**
 * Message Sync Service - Cross-Device Message Synchronization
 * Sprint M2: Firestore Sync for Wave-Style Messaging
 * 
 * WSP ARCHITECTURE NOTE (DO NOT REMOVE):
 * This service syncs message threads to Firestore for multi-device support.
 * Without this, messages only exist on the device that created them.
 * 
 * Architecture (WSP 98 - Mesh-Native):
 * - Layer 1: IndexedDB (messageStorage.ts) - offline-first, instant access
 * - Layer 2: Firestore (this file) - cross-device sync
 * 
 * Collections:
 * - /gotjunk_messages/{threadKey} - Thread with nested messages array
 */

import {
  collection,
  doc,
  runTransaction,
  arrayUnion,
  getDoc,
  getDocs,
  deleteDoc,
  onSnapshot,
  query,
  where,
  orderBy,
  Timestamp,
  Unsubscribe,
} from 'firebase/firestore';
import { getFirestoreDb, isFirebaseConfigured } from '../../services/firebaseConfig';
import { getCurrentUserId } from '../../services/firebaseAuth';
import { MessageThread, MessageContextRef, Message, ThreadStatus } from './types';
import { contextKey } from './messageStorage';

// Collection name
const MESSAGES_COLLECTION = 'gotjunk_messages';

// Firestore document structure
// WSP SECURITY: ownerUid required for thread-level access control
interface FirestoreThreadDoc {
  threadKey: string;
  ownerUid: string; // WSP AUDIT FIX: Thread creator for ownership enforcement
  contextType: string; // 'item' | 'liberty'
  itemId?: string;
  alertId?: string;
  status: ThreadStatus;
  closedAt?: number;
  closedReason?: string;
  messages: FirestoreMessage[];
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

interface FirestoreMessage {
  id: string;
  authorId: string;
  authorDisplayName?: string;
  text: string;
  createdAt: number;
  parentId?: string;
  ttlMs?: number;
  expiresAt?: number;
}

/**
 * Sync a message thread to Firestore
 * Called after addMessage, closeThread, lockThread
 * 
 * WSP SECURITY (DO NOT REMOVE):
 * - Requires authenticated user (getCurrentUserId)
 * - Stamps ownerUid on thread creation
 * - Preserves createdAt on updates (only set on first write)
 */
export const syncThreadToCloud = async (
  key: string,
  thread: MessageThread
): Promise<boolean> => {
  if (!isFirebaseConfigured()) {
    console.log('[MessageSync] Firebase not configured - skipping cloud sync');
    return false;
  }

  // WSP AUDIT FIX: Require auth before any cloud writes
  const currentUserId = getCurrentUserId();
  if (!currentUserId) {
    console.warn('[MessageSync] No authenticated user - skipping cloud sync');
    return false;
  }

  const db = getFirestoreDb();
  if (!db) return false;

  try {
    const docRef = doc(db, MESSAGES_COLLECTION, key);
    for (const message of thread.messages) {
      if (message.authorId !== currentUserId) continue;
      const serialized = Object.fromEntries(Object.entries({
        id: message.id, authorId: message.authorId,
        authorDisplayName: message.authorDisplayName, text: message.text,
        createdAt: message.createdAt, parentId: message.parentId,
        ttlMs: message.ttlMs, expiresAt: message.expiresAt,
      }).filter(([, value]) => value !== undefined));
      await runTransaction(db, async (transaction) => {
        const existing = await transaction.get(docRef);
        const now = Timestamp.now();
        if (!existing.exists()) {
          transaction.set(docRef, {
            threadKey: key, ownerUid: currentUserId,
            contextType: thread.context.type,
            ...(thread.context.itemId ? { itemId: thread.context.itemId } : {}),
            ...(thread.context.alertId ? { alertId: thread.context.alertId } : {}),
            status: 'active', messages: [serialized], createdAt: now, updatedAt: now,
          });
          return;
        }
        const remote = existing.data();
        if (remote.messages.some((stored: FirestoreMessage) => stored.id === message.id)) return;
        if (remote.status !== 'active') throw new Error('Thread is closed');
        transaction.update(docRef, { messages: arrayUnion(serialized), updatedAt: now });
      });
    }
    await runTransaction(db, async (transaction) => {
      const existing = await transaction.get(docRef);
      if (!existing.exists() || existing.data().ownerUid !== currentUserId) return;
      if (existing.data().status === thread.metadata.status) return;
      transaction.update(docRef, {
        status: thread.metadata.status,
        closedAt: thread.metadata.closedAt ?? null,
        closedReason: thread.metadata.closedReason ?? null,
        updatedAt: Timestamp.now(),
      });
    });
    return true;
  } catch (error) {
    console.error('[MessageSync] Failed to sync thread:', key, error);
    return false;
  }
};

/**
 * Delete a thread from Firestore
 * Called when thread is emptied
 * 
 * WSP SECURITY: Requires authenticated user
 * Note: Firestore rules should also enforce owner-only delete
 */
export const deleteThreadFromCloud = async (key: string): Promise<boolean> => {
  if (!isFirebaseConfigured()) {
    return false;
  }

  // WSP AUDIT FIX: Require auth before cloud deletes
  const currentUserId = getCurrentUserId();
  if (!currentUserId) {
    console.warn('[MessageSync] No authenticated user - skipping cloud delete');
    return false;
  }

  const db = getFirestoreDb();
  if (!db) return false;

  try {
    await deleteDoc(doc(db, MESSAGES_COLLECTION, key));
    console.log(`[MessageSync] Deleted thread from cloud: ${key}`);
    return true;
  } catch (error) {
    console.error('[MessageSync] Failed to delete thread:', key, error);
    return false;
  }
};

/**
 * Fetch a single thread from Firestore
 */
export const fetchThreadFromCloud = async (
  context: MessageContextRef
): Promise<MessageThread | null> => {
  if (!isFirebaseConfigured()) {
    return null;
  }

  const db = getFirestoreDb();
  if (!db) return null;

  try {
    const key = contextKey(context);
    const docSnap = await getDoc(doc(db, MESSAGES_COLLECTION, key));

    if (!docSnap.exists()) {
      return null;
    }

    return firestoreDocToThread(docSnap.data() as FirestoreThreadDoc);
  } catch (error) {
    console.error('[MessageSync] Failed to fetch thread:', error);
    return null;
  }
};

/**
 * Fetch all threads for a specific item or alert
 */
export const fetchThreadsForItem = async (itemId: string): Promise<MessageThread[]> => {
  if (!isFirebaseConfigured()) {
    return [];
  }

  const db = getFirestoreDb();
  if (!db) return [];

  try {
    const q = query(
      collection(db, MESSAGES_COLLECTION),
      where('itemId', '==', itemId)
    );

    const snapshot = await getDocs(q);
    const threads: MessageThread[] = [];

    for (const docSnap of snapshot.docs) {
      const thread = firestoreDocToThread(docSnap.data() as FirestoreThreadDoc);
      if (thread) threads.push(thread);
    }

    return threads;
  } catch (error) {
    console.error('[MessageSync] Failed to fetch threads for item:', itemId, error);
    return [];
  }
};

/**
 * Subscribe to real-time updates for a specific thread
 * Returns unsubscribe function
 */
export const subscribeToThread = (
  context: MessageContextRef,
  onUpdate: (thread: MessageThread | null) => void
): Unsubscribe | null => {
  if (!isFirebaseConfigured()) {
    console.log('[MessageSync] Firebase not configured - cannot subscribe');
    return null;
  }

  const db = getFirestoreDb();
  if (!db) return null;

  const key = contextKey(context);

  const unsubscribe = onSnapshot(
    doc(db, MESSAGES_COLLECTION, key),
    (docSnap) => {
      if (!docSnap.exists()) {
        onUpdate(null);
        return;
      }

      const thread = firestoreDocToThread(docSnap.data() as FirestoreThreadDoc);
      console.log(`[MessageSync] Real-time update for thread: ${key}`);
      onUpdate(thread);
    },
    (error) => {
      console.error('[MessageSync] Subscription error:', error);
      onUpdate(null);
    }
  );

  return unsubscribe;
};

/**
 * Convert Firestore document to MessageThread
 */
const firestoreDocToThread = (data: FirestoreThreadDoc): MessageThread | null => {
  try {
    const context: MessageContextRef = {
      type: data.contextType as 'item' | 'liberty',
      itemId: data.itemId,
      alertId: data.alertId,
    };

    const messages: Message[] = data.messages.map(msg => ({
      id: msg.id,
      context,
      authorId: msg.authorId,
      authorDisplayName: msg.authorDisplayName,
      text: msg.text,
      createdAt: msg.createdAt,
      parentId: msg.parentId,
      ttlMs: msg.ttlMs,
      expiresAt: msg.expiresAt,
    }));

    return {
      context,
      messages,
      metadata: {
        status: data.status,
        closedAt: data.closedAt,
        closedReason: data.closedReason,
      },
    };
  } catch (error) {
    console.error('[MessageSync] Failed to convert document:', error);
    return null;
  }
};

/**
 * Check if message sync is available
 */
export const isMessageSyncConfigured = (): boolean => {
  return isFirebaseConfigured();
};

/**
 * Fetch all threads from Firestore for cloud hydration
 * Called on app init to merge cloud data with local IndexedDB
 * 
 * WSP AUDIT FIX: Enables cross-device sync by fetching cloud threads
 * Returns Map<threadKey, MessageThread> for merging with local store
 */
export const fetchAllThreadsFromCloud = async (): Promise<Map<string, MessageThread>> => {
  const threads = new Map<string, MessageThread>();

  if (!isFirebaseConfigured()) {
    console.log('[MessageSync] Firebase not configured - skipping cloud fetch');
    return threads;
  }

  const db = getFirestoreDb();
  if (!db) return threads;

  try {
    const snapshot = await getDocs(collection(db, MESSAGES_COLLECTION));
    
    for (const docSnap of snapshot.docs) {
      const data = docSnap.data() as FirestoreThreadDoc;
      const thread = firestoreDocToThread(data);
      if (thread) {
        threads.set(data.threadKey, thread);
      }
    }

    console.log(`[MessageSync] Fetched ${threads.size} threads from cloud`);
    return threads;
  } catch (error) {
    console.error('[MessageSync] Failed to fetch threads from cloud:', error);
    return threads;
  }
};

/**
 * Subscribe to all threads for real-time sync
 * Returns unsubscribe function
 * 
 * WSP AUDIT FIX: Enables real-time cross-device updates
 */
export const subscribeToAllThreads = (
  onUpdate: (threads: Map<string, MessageThread>) => void
): Unsubscribe | null => {
  if (!isFirebaseConfigured()) {
    console.log('[MessageSync] Firebase not configured - cannot subscribe to all');
    return null;
  }

  const db = getFirestoreDb();
  if (!db) return null;

  const unsubscribe = onSnapshot(
    collection(db, MESSAGES_COLLECTION),
    (snapshot) => {
      const threads = new Map<string, MessageThread>();
      
      for (const docSnap of snapshot.docs) {
        const data = docSnap.data() as FirestoreThreadDoc;
        const thread = firestoreDocToThread(data);
        if (thread) {
          threads.set(data.threadKey, thread);
        }
      }

      console.log(`[MessageSync] Real-time update: ${threads.size} threads`);
      onUpdate(threads);
    },
    (error) => {
      console.error('[MessageSync] Subscription error:', error);
      onUpdate(new Map());
    }
  );

  return unsubscribe;
};

