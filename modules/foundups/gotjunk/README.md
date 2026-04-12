# GotJUNK? FoundUp

**Purpose**: Rapid-capture PWA to take photos/videos and organize them with AI-powered swipe interface and geo-fencing

**Domain**: `modules/foundups/` (WSP 3 functional distribution)
**Deployment**: Google AI Studio → Google Cloud Run
**Tech Stack**: React 19 + TypeScript + Vite + Gemini AI + Progressive Web App

## AI Studio Integration

**AI Studio Project**: https://ai.studio/apps/drive/1R_lBYHwMJHOxWjI_HAAx5DU9fqePG9nA

**Cloud Run Deployment**:
- Deployed via AI Studio one-click deployment
- Updates via "Redeploy app" button in AI Studio
- Automatic scaling (including to zero)
- Stable HTTPS endpoint

## Features

### Core Capabilities
- **Photo/Video Capture**: Camera and video recording with countdown
- **Swipe Interface**: Keep (right) or Delete (left) captured items
- **Geo-Fencing**: 50km radius filtering - only shows items near current location
- **Local Storage**: IndexedDB via localforage for offline-first PWA
- **AI Organization**: Gemini-powered content analysis (future enhancement)

### Technical Features
- **PWA Manifest**: Installable as standalone app
- **Service Worker**: Offline support and background sync
- **Geolocation**: High-accuracy GPS tracking per capture
- **Framer Motion**: Smooth swipe animations
- **Export**: Download organized items

## WSP Compliance

- **WSP 3**: Enterprise domain organization (FoundUps)
- **WSP 49**: Module structure (README, INTERFACE, ModLog, tests)
- **WSP 22**: Documentation and ModLog maintenance
- **WSP 50/64**: Pre-action verification
- **WSP 89**: Production deployment (Cloud Run)

## Project Structure

```
modules/foundups/gotjunk/
├── README.md                    # This file
├── INTERFACE.md                 # API and deployment docs
├── ModLog.md                    # Change tracking
├── ROADMAP.md                   # Development phases
├── module.json                  # DAE discovery manifest
├── frontend/                    # React PWA application
│   ├── App.tsx                  # Main app component
│   ├── components/              # UI components
│   ├── services/                # Gemini API, storage
│   ├── package.json             # Frontend dependencies
│   ├── vite.config.ts           # Build configuration
│   ├── manifest.json            # PWA manifest
│   ├── service-worker.js        # Offline support
│   └── .env.local               # GEMINI_API_KEY (gitignored)
├── deployment/                  # Cloud Run deployment tools
│   ├── deploy.sh                # Deployment automation
│   └── cloud_run_config.yaml   # Cloud Run configuration
├── src/                         # Backend services (future)
├── tests/                       # E2E and unit tests
└── memory/                      # FoundUp memory (WSP 60)
```

## Quick Start

### Run Locally

**Prerequisites**: Node.js 18+

```bash
cd modules/foundups/gotjunk/frontend
npm install
cp .env.local.example .env.local  # Add your GEMINI_API_KEY
npm run dev
```

Visit: http://localhost:5173

### Deploy to Cloud Run

**Option 1: AI Studio Redeploy** (Recommended)
1. Open AI Studio: https://ai.studio/apps/drive/1R_lBYHwMJHOxWjI_HAAx5DU9fqePG9nA
2. Make changes in `frontend/` locally and test
3. Upload updated files to AI Studio
4. Click 🚀 "Redeploy app"
5. Verify deployment at Cloud Run URL

**Option 2: Automated Deployment**
```bash
cd modules/foundups/gotjunk
./deployment/deploy.sh
```

**WARNING**: AI Studio redeploy overwrites Cloud Run source editor changes!

## Architecture

### Frontend Architecture
- **React 19**: Modern hooks-based UI
- **TypeScript**: Type-safe development
- **Vite**: Fast build tooling
- **Framer Motion**: Animation library
- **LocalForage**: IndexedDB abstraction

### Data Flow
1. User captures photo/video → Geolocation recorded
2. Item stored in IndexedDB with lat/lon
3. On load: Filter items within 50km radius
4. User swipes: Update status (review → kept/deleted)
5. Export: Download kept items as ZIP

### AI Integration (Future)
- **Gemini Vision**: Analyze captured items
- **Auto-Categorization**: Suggest keep/delete
- **Smart Search**: Find items by description
- **Batch Processing**: Organize multiple items

## Usage Examples

### Capture Flow
```typescript
// User opens app
const [reviewItems, setReviewItems] = useState<CapturedItem[]>([]);

// Capture photo with geolocation
const handleCapture = async (blob: Blob) => {
  const position = await getCurrentPositionPromise();
  const newItem: CapturedItem = {
    id: `item-${Date.now()}`,
    blob,
    url: URL.createObjectURL(blob),
    status: 'review',
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
  };
  await storage.saveItem(newItem);
  setReviewItems(current => [newItem, ...current]);
};

// Swipe decision
const handleReviewDecision = async (item: CapturedItem, decision: 'keep' | 'delete') => {
  setReviewItems(current => current.filter(i => i.id !== item.id));
  if (decision === 'keep') {
    await storage.updateItem(item.id, { status: 'kept' });
    setKeptItems(current => [item, ...current]);
  } else {
    await storage.deleteItem(item.id);
  }
};
```

### Geo-Filtering
```typescript
// Filter items within 50km radius
const allItems = await storage.getAllItems();
const position = await getCurrentPositionPromise();
const { latitude, longitude } = position.coords;

const nearbyItems = allItems.filter(item => {
  const distance = calculateDistance(latitude, longitude, item.latitude, item.longitude);
  return distance <= 50; // 50km radius
});
```

## Development Roadmap

See [ROADMAP.md](ROADMAP.md) for PoC → Prototype → MVP progression.

### Phase 1: PoC (COMPLETE)
- ✅ Photo capture with geolocation
- ✅ Swipe interface
- ✅ Local storage
- ✅ 50km geo-filtering
- ✅ PWA manifest
- ✅ Cloud Run deployment

### Phase 2: Prototype (CURRENT)
- [ ] Video capture enhancement
- [ ] Gemini AI content analysis
- [ ] Auto-categorization suggestions
- [ ] Enhanced export (ZIP with metadata)
- [ ] Performance optimization

### Phase 3: MVP
- [ ] User authentication
- [ ] Cloud sync (Firebase/Supabase)
- [ ] Multi-device support
- [ ] Batch operations
- [ ] Analytics dashboard

## Related Modules

This FoundUp leverages WRE-built platform modules:

- **AI Intelligence**: Could integrate `modules/ai_intelligence/banter_engine` for smart suggestions
- **Infrastructure**: Uses `modules/infrastructure/models` for shared schemas
- **Platform Integration**: Could add `modules/platform_integration/youtube_proxy` for content sharing

## Links

- **AI Studio Project**: https://ai.studio/apps/drive/1R_lBYHwMJHOxWjI_HAAx5DU9fqePG9nA
- **Google Cloud Run**: [View deployment console]
- **WSP Framework**: `../../WSP_framework/`
- **Module Documentation**: `../../README.md`

---

**Remember**: This is a **standalone FoundUp application**, not infrastructure. Platform definitions live in WSP_framework/, this implements them.

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`. Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `gotjunk_001` |
| `routing_prefix` | `/f/gotjunk_001` |
| Landing route | `/f/gotjunk_001` |
| App mount | `/f/gotjunk_001/app` |

---

## App Mount

Shell contract: **`/f/gotjunk_001/app`**. Currently deployed to Cloud Run via AI Studio; pfMALL mount pending production URL configuration.

---

## AI Capability Hooks

Contract surface (implementation staged): `get_status`, `get_context`, `navigate`, `launch_capability`, shell handoff/return — see `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`.

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach): health status, last action, error state, recommended next action, queue/work state (capture queue, swipe decisions), telemetry scoped by `foundup_id` / `data_namespace`.

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `gotjunk_001` |
| `data_namespace` | `idb_gotjunk_001` |
| Tenant bounds | IndexedDB via localforage, geolocation data, capture blobs — all tenant-scoped per WSP 104 |

---

## WSP References

- **WSP 91** — DAEMON observability (`WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md`)
- **WSP 104** — FoundUp route namespace (`WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`)
