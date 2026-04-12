# GotJUNK? FoundUp - Interface Documentation

## Cloud Run Deployment

**AI Studio Project ID**: `1R_lBYHwMJHOxWjI_HAAx5DU9fqePG9nA`
**Deployment Method**: Google AI Studio → Cloud Run (one-click)
**Runtime**: Node.js (Vite static build)

### Deployment Endpoints

**Production URL**: https://gotjunk-56566376153.us-west1.run.app/
**AI Studio Editor**: https://ai.studio/apps/drive/1R_lBYHwMJHOxWjI_HAAx5DU9fqePG9nA

### Redeployment Process

1. **Local Development**:
   ```bash
   cd modules/foundups/gotjunk/frontend
   npm run dev  # Test changes locally
   npm run build  # Build for production
   ```

2. **AI Studio Redeploy**:
   - Open AI Studio project
   - Upload/sync changed files
   - Click 🚀 → "Redeploy app"
   - Verify at production URL

3. **Alternative: Cloud Run Source Editor**:
   - Edit code in Cloud Run console
   - Click "Save and redeploy"
   - **WARNING**: Will be overwritten by AI Studio redeploy!

## PWA Manifest

**Permissions Required**:
- `camera`: Photo and video capture
- `geolocation`: Location tagging and geo-filtering

**Install Experience**:
- Prompt appears when using HTTPS
- Can be installed on mobile home screen
- Works offline after first visit

### manifest.json
```json
{
  "name": "GotJUNK?",
  "short_name": "GotJUNK",
  "description": "Rapid-capture photo organization with AI",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#3b82f6",
  "icons": [...],
  "permissions": ["camera", "geolocation"]
}
```

## API Integration

### Gemini AI Service

**File**: `frontend/services/geminiService.ts`

**Configuration**:
```typescript
import { GoogleGenAI } from "@google/genai";

const genai = new GoogleGenAI({
  apiKey: import.meta.env.GEMINI_API_KEY_GotJunk
});
```

**Environment Variables**:
```bash
# .env.local (NOT committed)
GEMINI_API_KEY_GotJunk=your_api_key_here
```

**Future API Methods**:
- `analyzeImage(blob: Blob): Promise<ImageAnalysis>`
- `categorizeItem(item: CapturedItem): Promise<Category>`
- `suggestAction(item: CapturedItem): Promise<'keep' | 'delete'>`

### Storage Service

**File**: `frontend/services/storage.ts`

**Methods**:
```typescript
// Save captured item
async saveItem(item: CapturedItem): Promise<void>

// Get all items
async getAllItems(): Promise<CapturedItem[]>

// Update item status
async updateItem(id: string, updates: Partial<CapturedItem>): Promise<void>

// Delete item
async deleteItem(id: string): Promise<void>

// Clear all items
async clearAllItems(): Promise<void>
```

**Storage Backend**: IndexedDB via `localforage`
**Database Name**: `gotjunk-storage`
**Store Name**: `captured-items`

## Data Models

### CapturedItem
```typescript
interface CapturedItem {
  id: string;                          // `item-${timestamp}`
  blob: Blob;                          // Photo/video data
  url: string;                         // ObjectURL for display
  status: ItemStatus;                  // 'review' | 'kept' | 'deleted'
  latitude?: number;                   // GPS latitude
  longitude?: number;                  // GPS longitude
  timestamp?: number;                  // Capture time
  category?: string;                   // AI categorization (future)
  aiSuggestion?: 'keep' | 'delete';    // AI recommendation (future)
}

type ItemStatus = 'review' | 'kept' | 'deleted';
type CaptureMode = 'photo' | 'video';
```

### GeolocationPosition
```typescript
interface GeolocationPosition {
  coords: {
    latitude: number;
    longitude: number;
    accuracy: number;
  };
  timestamp: number;
}
```

## Component APIs

### App Component
```typescript
export const App: React.FC = () => {
  const [reviewItems, setReviewItems] = useState<CapturedItem[]>([]);
  const [keptItems, setKeptItems] = useState<CapturedItem[]>([]);
  const [captureMode, setCaptureMode] = useState<CaptureMode>('photo');

  // Capture handler
  const handleCapture = async (blob: Blob) => { ... }

  // Review decision handler
  const handleReviewDecision = async (
    item: CapturedItem,
    decision: 'keep' | 'delete'
  ) => { ... }
}
```

### ItemReviewer Component
```typescript
interface ItemReviewerProps {
  items: CapturedItem[];
  onDecision: (item: CapturedItem, decision: 'keep' | 'delete') => void;
  captureMode: CaptureMode;
  onCapture: (blob: Blob) => void;
  onModeChange: (mode: CaptureMode) => void;
}
```

### FullscreenGallery Component
```typescript
interface FullscreenGalleryProps {
  items: CapturedItem[];
  isOpen: boolean;
  onClose: () => void;
}
```

## Geo-Filtering Algorithm

**Radius**: 50km
**Formula**: Haversine distance calculation

```typescript
function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) *
    Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; // Distance in km
}
```

**Filter Logic**:
```typescript
const nearbyItems = allItems.filter(item => {
  if (!item.latitude || !item.longitude) return false;
  const distance = calculateDistance(
    currentLat,
    currentLon,
    item.latitude,
    item.longitude
  );
  return distance <= 50;
});
```

## Build Configuration

### Vite Config
**File**: `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          motion: ['framer-motion'],
          ai: ['@google/genai']
        }
      }
    }
  }
});
```

### TypeScript Config
**File**: `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "jsx": "react-jsx",
    "strict": true
  }
}
```

## Performance Optimization

### Image Compression
- **Target**: < 1MB per photo
- **Format**: JPEG for photos, WebM for video
- **Quality**: 0.8 (80%)

### IndexedDB Limits
- **Per-item**: 10MB max (enforced by browser)
- **Total storage**: Quota API (typically 50% of disk)

### Lazy Loading
- Gallery images loaded on-demand
- Video thumbnails generated on capture

## Security Considerations

### API Key Management
```bash
# ✅ CORRECT: Environment variable
GEMINI_API_KEY_GotJunk=your_key_here  # In .env.local (gitignored)

# ❌ WRONG: Hardcoded
const apiKey = "<DO_NOT_HARDCODE_API_KEYS>"  # NEVER commit this!
```

### HTTPS Required
- Camera API requires secure context
- Geolocation requires HTTPS or localhost
- Cloud Run provides automatic TLS

### CORS Configuration
```typescript
// Cloud Run allows same-origin by default
// External API calls (Gemini) handled by SDK
```

## Deployment Checklist

- [ ] Set `GEMINI_API_KEY_GotJunk` in Cloud Run environment
- [ ] Test geolocation permissions
- [ ] Test camera permissions
- [ ] Verify HTTPS endpoint
- [ ] Test PWA install prompt
- [ ] Verify offline functionality
- [ ] Test 50km geo-filter accuracy
- [ ] Check IndexedDB quota handling
- [ ] Verify export functionality
- [ ] Load test with 100+ items

## Monitoring & Observability

### Future Enhancements
- **Cloud Run Logs**: Track deployment health
- **Analytics**: Google Analytics 4 integration
- **Error Tracking**: Sentry or similar
- **Performance**: Web Vitals monitoring

## Related Interfaces

- **AI Intelligence**: Could integrate with `modules/ai_intelligence/*/INTERFACE.md`
- **Infrastructure Models**: `modules/infrastructure/models/INTERFACE.md`
- **WSP Framework**: `WSP_framework/src/WSP_11_Interface_Protocol.md`

---

## Shell Embedding (WSP 104)

**Canonical Route**: `/f/gotjunk_001/app` (shell mounts Cloud Run app in iframe)

**Frame Policy**: `Content-Security-Policy: frame-ancestors` allows embedding from:
- `https://*.foundups.com` (production shell)
- `https://*.web.app` (Firebase hosting)
- `https://*.firebaseapp.com` (Firebase legacy)
- `http://localhost:*` / `https://localhost:*` (development)

**Dockerfile Config**: `frontend/Dockerfile` line 44 sets the frame-ancestors header.

**Deployment Requirement**: After Dockerfile changes, redeploy via:
1. Cloud Build: `gcloud builds submit --config=cloudbuild.yaml`
2. Or AI Studio: Upload changed files → "Redeploy app"

**Verification**: Check `Content-Security-Policy` header after deployment:
```bash
curl -sI https://gotjunk-56566376153.us-west1.run.app/ | grep -i content-security
```

---

**Deployment Status**: POC Complete, ready for Prototype phase
**Last Synced**: 2026-04-12
**Cloud Run URL**: https://gotjunk-56566376153.us-west1.run.app/
**Shell Embed Status**: Dockerfile fix in place; redeploy required for entry_url activation
