# FoundUP Cube Animation Spec

**For 0102 to implement**: Enhance `buildCanvas` in `index.html` to tell the FoundUP lifecycle story.

## Current State
- Static growing cube (1x1x1 → 4x4x4)
- Red agent dots moving toward cube
- No narrative, no phases, no investor flow

## Target: Dynamic FoundUP Lifecycle Animation

### Phase 1: SCAFFOLD (0-3s)
```
Visual: Wireframe/transparent cube outline (4x4x4 target size)
Agents: 2-3 spawn with status labels
Labels: "planning..." "researching..." "planning..."
Cube: Ghost outline only, very low alpha (0.1)
```

### Phase 2: BUILDING (3-15s)
```
Visual: Cube blocks fill in one-by-one as agents work
Agents: 3-5 agents actively moving to cube faces
Labels: "building..." "coding..." "designing..." "testing..."
Cube: Blocks materialize where agents touch (alpha 0.3 → 1.0)
Effect: Each block "pops" in with small particle burst
Token Counter: "F_i earned: 2,450" (incrementing)
```

### Phase 3: CUBE COMPLETE (15-17s)
```
Visual: Full 4x4x4 solid cube, brief glow/pulse
Text: "FoundUP Cube Complete!"
Agents: Pause briefly, celebrate (small bounce)
```

### Phase 4: PROMOTION (17-22s)
```
Visual: One agent detaches, moves to right edge
Agent Label: "promoting..." → "promoting..." → "promoting..."
Agent: Pulses/glows as it promotes
Other agents: Continue minor orbit around cube
```

### Phase 5: INVESTOR ARRIVES (22-25s)
```
Visual: GOLD dot appears from right edge
Gold Agent: Larger, glowing, moves toward cube
Label: "$" or "investor"
Effect: Trail of gold particles behind
Sound cue: (optional) subtle chime
```

### Phase 6: GROWTH BURST (25-28s)
```
Visual: 3-4 NEW agents spawn rapidly
Labels: "joining..." "building..." "expanding..."
Cube: Brief scale pulse (1.0 → 1.1 → 1.0)
Counter: "Agents: 8" → "Agents: 12"
```

### Phase 7: DAO LAUNCH (28-32s)
```
Visual: Cube transforms - rainbow shimmer effect
Text Overlay: "FoundUPS launches as DAO!"
Effect: Particle explosion, confetti-style
All agents: Orbit celebratory pattern
Cube: Glows intensely, then fades
```

### Phase 8: RESET (32-35s)
```
Visual: Fade to black, cube dissolves
Text: Brief pause
Then: Loop back to Phase 1 (new FoundUP begins)
```

## Agent Visual Spec

```javascript
// Agent object structure
{
  x, y,           // current position
  tx, ty,         // target position
  status: string, // "planning", "building", "promoting", etc.
  type: 'worker' | 'investor' | 'promoter',
  color: '#ff3b3b' | '#ffd700' | '#00e5d0',  // red, gold, cyan
  size: 6,        // radius
  showLabel: true,
  labelAlpha: 0.8
}
```

### Status Label Rendering
```javascript
// Below each agent dot
ctx.font = '10px monospace';
ctx.fillStyle = `rgba(255,255,255,${agent.labelAlpha})`;
ctx.fillText(agent.status, agent.x, agent.y + 16);
```

## Cube Block Fill Logic

```javascript
// Track which blocks are filled
const filledBlocks = new Set(); // "x,y,z" keys

// When agent reaches cube face:
function fillBlock(x, y, z) {
  const key = `${x},${y},${z}`;
  if (!filledBlocks.has(key)) {
    filledBlocks.add(key);
    // Trigger particle effect
    spawnBlockParticles(x, y, z);
    // Increment F_i counter
    fiEarned += Math.floor(Math.random() * 50) + 10;
  }
}
```

## Phase State Machine

```javascript
const PHASES = {
  SCAFFOLD: { duration: 3000, next: 'BUILDING' },
  BUILDING: { duration: 12000, next: 'COMPLETE' },
  COMPLETE: { duration: 2000, next: 'PROMOTING' },
  PROMOTING: { duration: 5000, next: 'INVESTOR' },
  INVESTOR: { duration: 3000, next: 'GROWTH' },
  GROWTH: { duration: 3000, next: 'LAUNCH' },
  LAUNCH: { duration: 4000, next: 'RESET' },
  RESET: { duration: 3000, next: 'SCAFFOLD' },
};

let currentPhase = 'SCAFFOLD';
let phaseStartTime = Date.now();

function updatePhase() {
  const elapsed = Date.now() - phaseStartTime;
  const phase = PHASES[currentPhase];

  if (elapsed > phase.duration) {
    currentPhase = phase.next;
    phaseStartTime = Date.now();
    onPhaseChange(currentPhase);
  }
}
```

## Key Visual Effects

### 1. Wireframe Cube (scaffold)
```javascript
function drawWireframeCube(cx, cy, size, scale, alpha) {
  ctx.strokeStyle = `rgba(124, 92, 252, ${alpha})`;
  ctx.lineWidth = 1;
  // Draw 12 edges of cube outline
  // ... isometric edge calculations
}
```

### 2. Block Materialize Effect
```javascript
function materializeBlock(x, y, z, progress) {
  // progress: 0 → 1
  const alpha = progress;
  const scale = 0.5 + progress * 0.5; // grow in
  drawCubelet(x, y, z, ..., alpha * scale);
}
```

### 3. Gold Investor Trail
```javascript
function drawInvestorTrail(agent) {
  for (let i = 0; i < agent.trail.length; i++) {
    const t = agent.trail[i];
    const alpha = (i / agent.trail.length) * 0.5;
    ctx.beginPath();
    ctx.arc(t.x, t.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255, 215, 0, ${alpha})`;
    ctx.fill();
  }
}
```

### 4. DAO Launch Confetti
```javascript
const confetti = [];

function spawnConfetti(cx, cy) {
  for (let i = 0; i < 50; i++) {
    confetti.push({
      x: cx, y: cy,
      vx: (Math.random() - 0.5) * 10,
      vy: (Math.random() - 0.5) * 10 - 5,
      color: FACE_COLORS[Math.floor(Math.random() * FACE_COLORS.length)],
      life: 1.0
    });
  }
}
```

## Integration with Simulator (Optional Enhancement)

If time permits, connect to Mesa simulation data:

```javascript
// Fetch live agent count from simulator
async function fetchSimulatorState() {
  try {
    const res = await fetch('/api/simulator/state');
    const data = await res.json();
    return {
      agentCount: data.agents.length,
      cubeProgress: data.buildProgress,
      phase: data.currentPhase
    };
  } catch {
    return null; // Fall back to animation-only mode
  }
}
```

## Bottom Status Bar

```
┌─────────────────────────────────────────────────────────┐
│  FoundUP Cube: 4×4×4  │  Agents: 8  │  F_i: 12,450  │  Phase: BUILDING  │
└─────────────────────────────────────────────────────────┘
```

## File Location
Modify: `public/about/index.html` (buildCanvas IIFE). The root `/` is public Play discovery; the explanatory cube lives on About.

## Success Criteria
1. Animation tells clear story of FoundUP lifecycle
2. Phases are distinct and readable
3. Agent labels show current activity
4. Investor (gold) arrival is dramatic
5. DAO launch celebration is satisfying
6. Smooth 35s loop, seamless restart
7. Mobile responsive (scales with canvas size)
