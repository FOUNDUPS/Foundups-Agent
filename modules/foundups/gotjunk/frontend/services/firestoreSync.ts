/**
 * Firestore Sync Service - Cross-Device Item Synchronization
 * WSP 98: FoundUps Mesh-Native Architecture Protocol - Layer 2 (Global Index)
 *
 * Architecture (MB-3 Database Architecture):
 * - Layer 1: IndexedDB (local) - fast, offline-first
 * - Layer 2: Firestore (global) - cross-device sync (THIS FILE)
 * - Layer 3: Blockchain (audit) - future
 *
 * Collections:
 * - /items/{itemId} - Item metadata (no blob)
 * - /blobs/{itemId} - Base64 encoded blob (for small images)
 * - Storage: gs://gen-lang-client-0061781628.appspot.com/items/ (for large blobs)
 */

import {
  collection,
  doc,
  setDoc,
  runTransaction,
  arrayUnion,
  getDoc,
  getDocs,
  onSnapshot,
  query,
  where,
  orderBy,
  limit,
  Timestamp,
  Unsubscribe,
} from 'firebase/firestore';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { getFirestoreDb, getFirebaseStorage, isFirebaseConfigured } from './firebaseConfig';
import { CapturedItem, ItemStatus } from '../types';
import { getCurrentUserId } from './firebaseAuth';

// Collection names
const ITEMS_COLLECTION = 'gotjunk_items';
const BLOBS_COLLECTION = 'gotjunk_blobs';

// Types for Firestore documents
interface FirestoreItemDoc {
  id: string;
  ownerUid: string;
  classification?: string;
  status: ItemStatus;
  latitude?: number;
  longitude?: number;
  price?: number;
  discountPercent?: number;
  bidDurationHours?: number;
  description?: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
  // Alert fields
  alertStatus?: string;
  alertTimer?: {
    startTime: number;
    duration: number;
    expiresAt: number;
    isPermanent?: boolean;
  };
  // Cart reservation fields (multi-device coordination)
  cartReservation?: {
    reservedBy: string;
    reservedAt: number;
    expiresAt: number;
  };
  // Blob reference
  blobStorageUrl?: string; // Firebase Storage download URL
  blobBase64?: string; // For small blobs (<1MB), inline storage
}

// Device ID for identifying this device's items
const getDeviceId = (): string => {
  let deviceId = localStorage.getItem('gotjunk_device_id');
  if (!deviceId) {
    deviceId = `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('gotjunk_device_id', deviceId);
  }
  return deviceId;
};

/**
 * Convert Blob to Base64 string
 */
const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      resolve(base64.split(',')[1]); // Remove data:*/*;base64, prefix
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

/**
 * Convert Base64 string to Blob
 */
const base64ToBlob = (base64: string, mimeType: string = 'image/jpeg'): Blob => {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
};

/**
 * Sync a captured item to Firestore (cloud)
 * @param item - The captured item to sync
 * @returns Promise<boolean> - true if sync successful
 */
export const syncItemToCloud = async (item: CapturedItem): Promise<boolean> => {
  if (!isFirebaseConfigured()) {
    console.log('[FirestoreSync] Firebase not configured - skipping cloud sync');
    return false;
  }

  const ownerUid = getCurrentUserId();
  if (!ownerUid) {
    console.warn('[FirestoreSync] No auth user - skipping cloud sync');
    return false;
  }

  if (item.userId && item.userId !== ownerUid) return false;

  const db = getFirestoreDb();
  const storage = getFirebaseStorage();
  if (!db) return false;

  try {
    const deviceId = getDeviceId();
    const now = Timestamp.now();

    // Upload blob to Storage if available
    let blobStorageUrl: string | undefined;
    let blobBase64: string | undefined;

    if (item.blob) {
      // Small blobs (<500KB): store inline as base64
      // Large blobs: upload to Firebase Storage
      if (item.blob.size < 500 * 1024 && storage) {
        blobBase64 = await blobToBase64(item.blob);
      } else if (storage) {
        const storageRef = ref(storage, `items/${ownerUid}/${item.id}`);
        await uploadBytes(storageRef, item.blob);
        blobStorageUrl = await getDownloadURL(storageRef);
      } else {
        // Fallback: store as base64 even if large
        blobBase64 = await blobToBase64(item.blob);
      }
    }

    // Create Firestore document
    const itemDoc: FirestoreItemDoc = {
      id: item.id,
      ownerUid,
      classification: item.classification,
      status: item.status,
      ownership: item.ownership,
      latitude: item.latitude,
      longitude: item.longitude,
      price: item.price,
      discountPercent: item.discountPercent,
      bidDurationHours: item.bidDurationHours,
      description: item.description,
      createdAt: Timestamp.fromMillis(item.createdAt),
      updatedAt: now,
      alertStatus: item.alertStatus,
      alertTimer: item.alertTimer,
      blobStorageUrl,
      blobBase64,
    };

    // Save to Firestore
    await setDoc(doc(db, ITEMS_COLLECTION, item.id), {
      ...itemDoc,
      deviceId,
    }, { merge: true });

    console.log('[FirestoreSync] Synced item to cloud:', item.id);
    return true;
  } catch (error) {
    console.error('[FirestoreSync] Failed to sync item:', error);
    return false;
  }
};

/**
 * Update cart reservation for an item in Firestore
 * @param itemId - The item ID
 * @param reservation - Cart reservation data (or null to clear)
 * @returns Promise<boolean> - true if update successful
 */
export const updateCartReservation = async (
  itemId: string,
  reservation: { reservedBy: string; reservedAt: number; expiresAt: number } | null
): Promise<boolean> => {
  if (!isFirebaseConfigured()) {
    console.log('[FirestoreSync] Firebase not configured - skipping reservation update');
    return false;
  }

  const db = getFirestoreDb();
  if (!db) return false;

  try {
    const itemRef = doc(db, ITEMS_COLLECTION, itemId);
    await setDoc(
      itemRef,
      {
        cartReservation: reservation,
        updatedAt: Timestamp.now(),
      },
      { merge: true } // Only update these fields
    );

    console.log('[FirestoreSync] Updated cart reservation:', itemId, reservation ? 'reserved' : 'cleared');
    return true;
  } catch (error) {
    console.error('[FirestoreSync] Failed to update cart reservation:', error);
    return false;
  }
};

/**
 * Fetch all items from Firestore (cloud)
 * @param limitCount - Max items to fetch (default 100)
 * @returns Promise<CapturedItem[]> - Items from cloud
 */
export const fetchItemsFromCloud = async (limitCount: number = 100): Promise<CapturedItem[]> => {
  if (!isFirebaseConfigured()) {
    console.log('[FirestoreSync] Firebase not configured - cannot fetch from cloud');
    return [];
  }

  const db = getFirestoreDb();
  if (!db) return [];

  try {
    const q = query(
      collection(db, ITEMS_COLLECTION),
      orderBy('createdAt', 'desc'),
      limit(limitCount)
    );

    const snapshot = await getDocs(q);
    const items: CapturedItem[] = [];

    for (const docSnap of snapshot.docs) {
      const data = docSnap.data() as FirestoreItemDoc & { deviceId: string };
      const item = await firestoreDocToItem(data);
      if (item) items.push(item);
    }

    console.log('[FirestoreSync] Fetched', items.length, 'items from cloud');
    return items;
  } catch (error) {
    console.error('[FirestoreSync] Failed to fetch items:', error);
    return [];
  }
};

/**
 * Fetch Liberty Alert items from Firestore (for global map)
 * @returns Promise<CapturedItem[]> - Active Liberty Alert items
 */
export const fetchLibertyAlertsFromCloud = async (): Promise<CapturedItem[]> => {
  if (!isFirebaseConfigured()) {
    return [];
  }

  const db = getFirestoreDb();
  if (!db) return [];

  try {
    // Query for ICE and Police alerts that are active
    const q = query(
      collection(db, ITEMS_COLLECTION),
      where('classification', 'in', ['ice', 'police']),
      where('alertStatus', 'in', ['active', 'ongoing']),
      orderBy('createdAt', 'desc'),
      limit(50)
    );

    const snapshot = await getDocs(q);
    const items: CapturedItem[] = [];

    for (const docSnap of snapshot.docs) {
      const data = docSnap.data() as FirestoreItemDoc & { deviceId: string };
      const item = await firestoreDocToItem(data);
      if (item) items.push(item);
    }

    console.log('[FirestoreSync] Fetched', items.length, 'Liberty Alerts from cloud');
    return items;
  } catch (error) {
    console.error('[FirestoreSync] Failed to fetch Liberty Alerts:', error);
    return [];
  }
};

/**
 * Subscribe to real-time updates from Firestore
 * @param onItemsUpdated - Callback when items change
 * @returns Unsubscribe function
 */
export const subscribeToCloudItems = (
  onItemsUpdated: (items: CapturedItem[]) => void
): Unsubscribe | null => {
  if (!isFirebaseConfigured()) {
    console.log('[FirestoreSync] Firebase not configured - cannot subscribe');
    return null;
  }

  const db = getFirestoreDb();
  if (!db) return null;

  const q = query(
    collection(db, ITEMS_COLLECTION),
    orderBy('createdAt', 'desc'),
    limit(100)
  );

  const unsubscribe = onSnapshot(q, async (snapshot) => {
    const items: CapturedItem[] = [];

    for (const docSnap of snapshot.docs) {
      const data = docSnap.data() as FirestoreItemDoc & { deviceId: string };
      const item = await firestoreDocToItem(data);
      if (item) items.push(item);
    }

    console.log('[FirestoreSync] Real-time update:', items.length, 'items');
    onItemsUpdated(items);
  });

  return unsubscribe;
};

/**
 * Convert Firestore document to CapturedItem
 */
const firestoreDocToItem = async (
  data: FirestoreItemDoc & { deviceId: string }
): Promise<CapturedItem | null> => {
  try {
    const currentUid = getCurrentUserId();
    const ownership = currentUid && data.ownerUid === currentUid ? 'mine' : 'others';

    // Reconstruct blob from storage URL or base64
    let blob: Blob;
    if (data.blobBase64) {
      blob = base64ToBlob(data.blobBase64);
    } else if (data.blobStorageUrl) {
      // Fetch blob from Storage URL
      const response = await fetch(data.blobStorageUrl);
      blob = await response.blob();
    } else {
      // Create placeholder blob
      blob = new Blob([''], { type: 'image/jpeg' });
    }

    const url = URL.createObjectURL(blob);

    return {
      id: data.id,
      blob,
      url,
      classification: data.classification as CapturedItem['classification'],
      status: data.status,
      ownership: ownership as CapturedItem['ownership'],
      latitude: data.latitude,
      longitude: data.longitude,
      price: data.price,
      discountPercent: data.discountPercent,
      bidDurationHours: data.bidDurationHours,
      description: data.description,
      createdAt: data.createdAt.toMillis(),
      alertStatus: data.alertStatus as CapturedItem['alertStatus'],
      alertTimer: data.alertTimer,
      cartReservation: data.cartReservation,
      userId: data.ownerUid,
    };
  } catch (error) {
    console.error('[FirestoreSync] Failed to convert document:', error);
    return null;
  }
};

/**
 * Check sync status
 */
export const getSyncStatus = (): {
  isConfigured: boolean;
  deviceId: string;
} => ({
  isConfigured: isFirebaseConfigured(),
  deviceId: getDeviceId(),
});

/** Append one vote under the caller UID; transaction preserves concurrent votes. */
export async function voteOnItem(itemId: string, choice: 'keep' | 'remove') {
  const uid = getCurrentUserId();
  const db = getFirestoreDb();
  if (!uid || !db) throw new Error('Sign in before voting.');
  return runTransaction(db, async transaction => {
    const target = doc(db, ITEMS_COLLECTION, itemId);
    const existing = await transaction.get(target);
    if (!existing.exists()) throw new Error('Item is unavailable.');
    const stored = existing.data().moderationVotes;
    const before = { keep: stored?.keep || [], remove: stored?.remove || [] };
    if (before.keep.includes(uid) || before.remove.includes(uid)) return before;
    const votes = { keep: [...before.keep], remove: [...before.remove] };
    votes[choice].push(uid);
    transaction.update(target, { [`moderationVotes.${choice}`]: arrayUnion(uid), updatedAt: Timestamp.now() });
    return votes;
  });
}
