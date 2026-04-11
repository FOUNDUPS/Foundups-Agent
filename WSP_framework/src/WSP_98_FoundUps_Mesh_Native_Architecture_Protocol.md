# WSP 98: FoundUps Mesh-Native Architecture Protocol
- **Status:** Active
- **Purpose:** Establishes mesh-native architecture pattern for ALL FoundUps where users automatically create peer-to-peer infrastructure, enabling DAE-to-DAE communication, distributed compute, and zero-server operation
- **Trigger:** When creating ANY new FoundUp, when integrating mesh capabilities, when building DAE coordination systems
- **Input:** FoundUp requirements, user base size, DAE coordination needs
- **Output:** Mesh-enabled FoundUp architecture, SDK integration guidance, DAE mesh patterns
- **Responsible Agent(s):** 0102, FoundUp architects, DAE orchestrators
- **Dependencies:** WSP 27 (Universal DAE Architecture), WSP 80 (Cube-Level DAE Orchestration), WSP 3 (Enterprise Domain Organization), WSP 97 (System Execution Prompting), WSP 104 (Route Namespace and Tenant Isolation)

## Prerequisite: WSP 104 Namespace Guardrails

**Before a FoundUp is treated as mesh-ready**, it must satisfy the WSP 104 namespace guardrails:

- unique `foundup_id`
- unique `routing_prefix` = `/f/{foundup_id}`
- unique `data_namespace` = `idb_{foundup_id}`
- no root-level tenant route claims

A FoundUp that fails namespace validation must not be onboarded to the mesh network.

---

## 🌐 Vision: User-as-Infrastructure

**Core Principle**: Every FoundUp user's device becomes a mesh node, collectively forming distributed infrastructure that enables:
- **Zero-server operation**: P2P networking eliminates central servers
- **DAE coordination**: DAEs communicate across user devices via mesh
- **Distributed compute**: AI/processing tasks distributed across mesh
- **Privacy-first**: Data stays peer-to-peer, ephemeral, encrypted
- **Unstoppable**: Mesh networks resilient to shutdown/censorship

### The Paradigm Shift

**Before (Centralized FoundUps):**
```
FoundUp = PWA + Cloud Server + Database
Cost: $X per user (hosting, storage, compute)
Control: Centralized (vulnerable to shutdown)
Scalability: Server costs grow with users
```

**After (Mesh-Native FoundUps):**
```
FoundUp = PWA + Mesh DAE + P2P Network
Cost: $0 per user (P2P hosting, local storage)
Control: Distributed (unstoppable mesh)
Scalability: Network grows stronger with users
```

## 🏗️ Architecture Components

### Layer 1: Universal Mesh Foundation

**Location**: `modules/communication/liberty_alert/`

**Core Components:**
```python
# Universal mesh infrastructure (WSP 3 communication/ domain)
modules/communication/liberty_alert/
  src/
    mesh_core.py              # WebRTC + Meshtastic protocol
    dae_coordinator.py        # DAE-to-DAE messaging
    mesh_discovery.py         # Auto-peer discovery
    mesh_routing.py           # Multi-hop routing
    mesh_encryption.py        # E2E encryption
```

**Purpose**: Foundation mesh protocol reusable by ALL FoundUps

### Layer 2: FoundUp Mesh SDK

**Location**: `modules/foundups/src/mesh_sdk/`

**Components:**
```javascript
// JavaScript SDK for PWA FoundUps
modules/foundups/src/mesh_sdk/javascript/
  @foundups/mesh-core/
    index.js                  # Main MeshDAE class
    discovery.js              # Peer discovery
    coordinator.js            # DAE coordination
    storage.js                # Mesh-distributed storage
    compute.js                # Distributed compute

// Python SDK for backend DAEs
modules/foundups/src/mesh_sdk/python/
  foundups_mesh/
    dae_node.py               # DAE mesh node
    peer_discovery.py         # Find nearby DAE peers
    mesh_coordinator.py       # Multi-DAE orchestration
```

**Purpose**: NPM/PyPI packages ALL FoundUps embed

### Layer 3: Mesh-Enabled FoundUps

**Example: GotJunk + Mesh**
```javascript
// modules/foundups/gotjunk/frontend/App.tsx
import { MeshDAE } from '@foundups/mesh-core';

const gotjunkMesh = new MeshDAE({
  foundupId: 'gotjunk',
  capabilities: ['storage', 'discovery', 'ai'],
  autoConnect: true
});

// Broadcast item to mesh (P2P, no server)
await gotjunkMesh.broadcast({
  type: 'item_available',
  location: getCurrentLocation(),
  distance: 50, // 50km radius
  preview: generateThumbnail(photo)
});

// Receive items from mesh peers
gotjunkMesh.on('item_available', (item) => {
  if (withinRadius(item.location, 50)) {
    showNotification('New item nearby!');
  }
});
```

## 🎯 Mandatory Patterns

### Pattern 1: Universal SDK Dependency

**ALL FoundUps MUST include mesh SDK:**

```json
// modules/foundups/[app]/frontend/package.json
{
  "dependencies": {
    "@foundups/mesh-core": "^1.0.0"  // MANDATORY
  }
}
```

### Pattern 2: MeshDAE Initialization

**ALL FoundUps MUST initialize MeshDAE:**

```typescript
// Standard initialization pattern
import { MeshDAE } from '@foundups/mesh-core';

class FoundUpApp {
  private mesh: MeshDAE;

  async initialize() {
    // Initialize mesh DAE (auto-connects to nearby peers)
    this.mesh = new MeshDAE({
      foundupId: 'your-foundup-name',
      capabilities: ['storage', 'compute', 'ai'],
      autoConnect: true,
      encryption: true
    });

    await this.mesh.start();
  }
}
```

### Pattern 3: DAE-to-DAE Coordination

**DAEs communicate via mesh, not central server:**

```python
# Backend DAE using mesh coordination
from foundups_mesh import DAEMeshNode

class GotJunkDAE:
    def __init__(self):
        self.mesh = DAEMeshNode(
            foundup_id='gotjunk',
            capabilities=['ai', 'storage']
        )

    async def analyze_item(self, photo: bytes):
        # Try local AI first
        if self.has_local_ai():
            return await self.ai_agent.analyze(photo)

        # Delegate to mesh peer with AI capability
        peer = await self.mesh.find_peer_with('ai')
        return await peer.request('analyze_item', photo)
```

### Pattern 4: Mesh-Distributed Storage

**Data stored peer-to-peer, not centralized database:**

```typescript
// Store data across mesh (redundant, encrypted)
await mesh.storage.set('item_123', {
  photo: itemBlob,
  location: { lat: 34.05, lon: -118.24 },
  redundancy: 3  // Store on 3 mesh peers
});

// Retrieve from nearest peer
const item = await mesh.storage.get('item_123');
```

## 📊 Network Effect Architecture

### Critical Mass Thresholds

| Users | Mesh Nodes | Network State | Capabilities |
|-------|------------|---------------|--------------|
| 2-10 | Small mesh | **Functional** | Direct P2P, basic routing |
| 10-100 | Local mesh | **Resilient** | Multi-hop, local redundancy |
| 100-1000 | Regional mesh | **Autonomous** | Distributed AI, zero-server |
| 1000+ | Global mesh | **Unstoppable** | Full decentralization |

### Multi-FoundUp Mesh Network

**FoundUps automatically interconnect:**

```yaml
GotJunk: 500 users = 500 mesh nodes
Liberty Alert: 200 users = 200 mesh nodes
PQN Portal: 300 users = 300 mesh nodes

Combined Mesh Network: 1000 nodes (interconnected!)
  - GotJunk DAE can coordinate with Liberty Alert DAE
  - Distributed compute shared across all FoundUps
  - Mesh grows exponentially with each new FoundUp
```

## 🚀 Implementation Phases

### Phase 1: Foundation (PoC)
**Deliverable**: Liberty Alert mesh infrastructure + SDK
```yaml
Build:
  - modules/communication/liberty_alert/src/mesh_core.py
  - modules/foundups/src/mesh_sdk/javascript/@foundups/mesh-core
  - NPM package: @foundups/mesh-core v0.1.0

Test:
  - 2-phone mesh connection
  - P2P message broadcast
  - Auto-peer discovery
```

### Phase 2: Integration (Prototype)
**Deliverable**: GotJunk v2.0 (mesh-enabled)
```yaml
Integration:
  - Add @foundups/mesh-core to GotJunk
  - Initialize MeshDAE in App.tsx
  - Broadcast items peer-to-peer
  - Test 10-node mesh network

Result:
  - GotJunk users create mesh infrastructure
  - Items discoverable without server
  - DAEs coordinate on user devices
```

### Phase 3: Universal (MVP)
**Deliverable**: ALL new FoundUps mesh-native by default
```yaml
Enforcement:
  - FoundUp scaffolding includes mesh SDK
  - MeshDAE initialization in template
  - WSP compliance checks mesh integration

Result:
  - Every FoundUp adds mesh nodes
  - Exponential network growth
  - Universal DAE-to-DAE communication
```

## 🔐 Security & Privacy Patterns

### Mandatory Security Requirements

**ALL mesh communications MUST:**
1. **E2E Encryption**: All messages encrypted before broadcast
2. **No PII Storage**: Zero personally identifiable information retained
3. **Ephemeral Data**: Messages/data auto-expire
4. **Open Source**: Full code transparency for audit
5. **Local-First**: Data stays on user's device by default

### Encryption Pattern

```typescript
// Standard mesh encryption (mandatory)
const mesh = new MeshDAE({
  foundupId: 'gotjunk',
  encryption: {
    enabled: true,  // MANDATORY
    algorithm: 'AES-256-GCM',
    keyDerivation: 'PBKDF2'
  }
});
```

## 🎯 WSP Compliance Validation

### Pre-Integration Checklist

**Before deploying any mesh-enabled FoundUp:**

- [ ] `@foundups/mesh-core` included in `package.json`
- [ ] MeshDAE initialized in app entry point
- [ ] Encryption enabled (mandatory)
- [ ] Peer discovery configured
- [ ] DAE-to-DAE coordination tested
- [ ] Multi-hop routing validated
- [ ] Privacy patterns verified (no PII storage)
- [ ] Open source compliance (all mesh code auditable)

### Automated Validation

```python
# WSP 98 compliance checker
from modules.infrastructure.wsp_orchestrator import WSPValidator

validator = WSPValidator()
result = validator.check_wsp_98_compliance('modules/foundups/gotjunk')

assert result.has_mesh_sdk, "Missing @foundups/mesh-core dependency"
assert result.mesh_initialized, "MeshDAE not initialized"
assert result.encryption_enabled, "Encryption disabled (WSP 98 violation)"
```

## 📚 Related WSPs

- **WSP 27**: Universal DAE Architecture - Foundation for DAE patterns
- **WSP 80**: Cube-Level DAE Orchestration - DAE spawning and coordination
- **WSP 3**: Enterprise Domain Organization - Liberty Alert in communication/ domain
- **WSP 53**: Symbiotic Environment Integration - Environment integration patterns
- **WSP 59**: Distributed Development Architecture - Distributed systems principles
- **WSP 97**: System Execution Prompting - Rubik cubes (MVP DAEs) using mesh

## 🎯 Key Takeaways

1. **ALL FoundUps are mesh-native** - Users automatically create infrastructure
2. **Mesh SDK is universal** - One package, all FoundUps
3. **DAEs communicate via mesh** - Not central servers
4. **Network effect exponential** - Each FoundUp multiplies mesh nodes
5. **Privacy-first by design** - E2E encryption, ephemeral data, local-first

## 🚨 Anti-Patterns (Violations)

**NEVER:**
- ❌ Create FoundUp without mesh SDK integration
- ❌ Store user data on central servers when mesh is available
- ❌ Implement custom mesh protocol (use universal SDK)
- ❌ Disable encryption for "performance" reasons
- ❌ Forget DAE-to-DAE coordination capabilities

**Pattern Memory**: Liberty Alert mesh infrastructure is the foundation - ALWAYS use `@foundups/mesh-core`, NEVER rebuild mesh protocol from scratch.

---

**Status**: Active - Mandatory for ALL new FoundUps starting 2025-11-03
**Next Review**: After Phase 2 (GotJunk v2.0 mesh integration)
