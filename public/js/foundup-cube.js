/**
 * FoundUP Cube Animation Module
 *
 * Tells the FoundUP lifecycle story:
 * IDEA → SCAFFOLD → BUILD → PROMOTE → STAKING → CUSTOMERS → LAUNCH (MVP) → CELEBRATE → RESET
 *
 * Location: public/js/foundup-cube.js
 * Spec: public/cube-story-spec.md
 *
 * Phases:
 *   Phase 1: Single-cube 45s deterministic loop
 *   Phase 2: Camera handoff to next cube spawn
 *   Phase 3: Multi-cube zoom-out with staggered states
 *   Phase 4: Simulator event integration (USE_SIM_EVENTS flag)
 *   Phase 5: Ticker/chat as event subscribers
 *
 * Usage:
 *   <canvas id="buildCanvas"></canvas>
 *   <script src="js/foundup-cube.js"></script>
 *   <script>FoundupCube.init('buildCanvas');</script>
 */

const FoundupCube = (function () {
    'use strict';

    // ═══════════════════════════════════════════════════════════════════════
    // FROZEN STYLE CONSTANTS (DO NOT MODIFY - guardrail for visual consistency)
    // ═══════════════════════════════════════════════════════════════════════
    const STYLE = Object.freeze({
        // Color palette
        palette: Object.freeze({
            accent: '#7c5cfc',
            cyan: '#00e5d0',
            gold: '#f5a623',
            pink: '#ff4ea0',
            bg: '#08080f',
        }),

        // Face colors for cube blocks
        faceColors: Object.freeze([
            '#ff2d2d', '#ff8c00', '#ffd700', '#00b341', '#0066ff', '#9b59b6',
            '#00e5d0', '#ff6b9d', '#a855f7', '#22c55e'
        ]),

        // Agent type colors
        agentColors: Object.freeze({
            builder: '#ff3b3b',
            promoter: '#00e5d0',
            staker: '#ffd700',   // CABR/PoB: staker (not investor)
            founder: '#f5a623',
            idle: '#666688',  // Dimmed color for IDLE state
        }),

        // WSP 27 priority level colors
        levelColors: Object.freeze({
            P0: '#ff2d2d',  // Elite - red
            P1: '#ff8c00',  // Senior - orange
            P2: '#ffd700',  // Mid - yellow
            P3: '#00b341',  // Junior - green
            P4: '#0066ff',  // Novice - blue
        }),

        // Easing functions
        easing: Object.freeze({
            quadInOut: (t) => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
            quadOut: (t) => 1 - (1 - t) * (1 - t),
            linear: (t) => t,
        }),

        // Particle settings
        particles: Object.freeze({
            blockBurstCount: 8,
            confettiCount: 60,
            trailLength: 20,
            particleDecay: 0.03,
            confettiDecay: 0.015,
        }),

        // Camera settings (for future multi-cube phases)
        camera: Object.freeze({
            panSpeed: 0.02,      // Normalized units per frame
            zoomSpeed: 0.01,
            defaultScale: 15,
            minScale: 3,         // Far zoom: ecosystem view with 5-10 cubes
            maxScale: 25,
            ecosystemThreshold: 10,  // Below this scale, show tile grid of cubes
        }),

        // Typography
        fonts: Object.freeze({
            status: '11px monospace',
            label: '10px monospace',
            announcement: 'bold 18px monospace',
            agentSymbol: 'bold 6px sans-serif',
        }),
    });

    // ═══════════════════════════════════════════════════════════════════════
    // FEATURE FLAGS
    // ═══════════════════════════════════════════════════════════════════════
    // Auto-enable SSE via URL param: ?sim=1 or ?sse=1 or when on SSE-enabled host
    const urlParams = new URLSearchParams(window.location.search);
    const autoEnableSSE = urlParams.get('sim') === '1' || urlParams.get('sse') === '1';

    const FLAGS = {
        USE_SIM_EVENTS: autoEnableSSE,  // Phase 4: Wire to simulator events
        ENABLE_TICKER: true,    // Phase 5: Event subscriber ticker (now active)
        ENABLE_CHAT: false,     // Phase 5: Event subscriber chat bubbles
        MULTI_CUBE: false,      // Phase 3: Multi-cube zoom-out
        DEBUG_TIMING: false,    // Log phase transitions
        WRITE_FIRESTORE: true,  // Phase 6: Write events to Firestore
        DRIVEN_MODE: false,     // Phase 7: Animation controlled by simulator state (not timer)
    };

    // ═══════════════════════════════════════════════════════════════════════
    // FIRESTORE BRIDGE (Phase 6) - Persist cube events
    // ═══════════════════════════════════════════════════════════════════════
    const firestoreBridge = {
        db: null,
        sessionId: crypto.randomUUID(),
        loopCount: 0,
        totalFiEarned: 0,
        eventsWritten: 0,

        // Events to persist (not all events - reduce write volume)
        PERSIST_EVENTS: new Set([
            'phase_changed', 'cube_complete', 'dao_launched',
            'staker_arrived', 'customers_arrived', 'loop_started',
            'fi_ups_exchange', 'zoom_out'
        ]),

        init(firestore) {
            this.db = firestore;
            console.log('[Cube] Firestore bridge initialized, session:', this.sessionId);
            this.writeSessionStart();
        },

        async writeSessionStart() {
            if (!this.db || !FLAGS.WRITE_FIRESTORE) return;
            try {
                const { collection, addDoc, serverTimestamp } = await import('https://www.gstatic.com/firebasejs/11.4.0/firebase-firestore.js');
                await addDoc(collection(this.db, 'cube_sessions'), {
                    session_id: this.sessionId,
                    started_at: serverTimestamp(),
                    user_agent: navigator.userAgent,
                    referrer: document.referrer || 'direct',
                    screen: `${window.innerWidth}x${window.innerHeight}`,
                });
            } catch (e) {
                console.warn('[Cube] Firestore session write failed:', e.message);
            }
        },

        async writeEvent(type, data) {
            if (!this.db || !FLAGS.WRITE_FIRESTORE) return;
            if (!this.PERSIST_EVENTS.has(type)) return;

            try {
                const { collection, addDoc, serverTimestamp } = await import('https://www.gstatic.com/firebasejs/11.4.0/firebase-firestore.js');
                await addDoc(collection(this.db, 'cube_events'), {
                    event_type: type,
                    session_id: this.sessionId,
                    loop_count: this.loopCount,
                    phase: currentPhase,
                    timestamp: serverTimestamp(),
                    data: data || {},
                });
                this.eventsWritten++;
            } catch (e) {
                // Silent fail - don't break animation for Firestore issues
                if (FLAGS.DEBUG_TIMING) console.warn('[Cube] Firestore event write failed:', e.message);
            }
        },

        onLoopStart() {
            this.loopCount++;
        },

        onFiEarned(amount) {
            this.totalFiEarned += amount;
        }
    };

    // ═══════════════════════════════════════════════════════════════════════
    // SIMULATOR EVENT BRIDGE (Phase 4)
    // ═══════════════════════════════════════════════════════════════════════

    // SSE endpoint configuration - environment-aware
    const SSE_ENDPOINTS = {
        // Production: Cloud Run service URL (set this after deploying)
        production: 'https://sse-foundups-gen-lang-client-0061781628.run.app/api/sim-events',
        // Development: local SSE server
        development: 'http://localhost:8080/api/sim-events',
        // Fallback: relative URL (works if SSE server is proxied)
        relative: '/api/sim-events',
    };

    // Detect environment and select endpoint
    function getSSEEndpoint() {
        const hostname = window.location.hostname;
        // Check URL param override first
        const customEndpoint = urlParams.get('sse_url');
        if (customEndpoint) return customEndpoint;

        // Production hosts
        if (hostname === 'foundups.com' || hostname.includes('firebaseapp.com') || hostname.includes('web.app')) {
            // Try relative first (if proxied), fallback to production Cloud Run
            return SSE_ENDPOINTS.relative;
        }
        // Local development
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return SSE_ENDPOINTS.development;
        }
        // Default to relative
        return SSE_ENDPOINTS.relative;
    }

    const simBridge = {
        connected: false,
        eventSource: null,
        reconnectAttempts: 0,
        maxReconnectAttempts: 5,
        reconnectDelay: 2000,
        baseReconnectDelay: 2000,  // For exponential backoff
        lastLifecycleStage: 'PoC',
        lastSequenceId: 0,  // Track last sequence to avoid duplicates on reconnect
        endpoint: getSSEEndpoint(),  // SSE endpoint (environment-aware)
    };

    // Map simulator events to cube events (from modules/foundups/simulator/event_bus.py)
    const SIM_EVENT_MAP = {
        'foundup_created': (d) => ({
            type: 'foundup_created',
            data: { foundupIndex: d.foundup_index || 1, name: d.name || 'new foundup' },
        }),
        'task_state_changed': (d) => {
            const status = d.new_status || d.new_state;
            if (status === 'claimed') return { type: 'agent_spawned', data: { type: 'builder', status: 'claiming...' } };
            if (status === 'submitted') return { type: 'proof_submitted', data: { proof_type: 'work', task_id: d.task_id } };
            if (status === 'verified') return { type: 'sim_security_audit', data: {} };
            if (status === 'paid') return {
                type: 'agent_earned',
                data: { foundupIndex: d.foundup_index || 1, agentId: d.actor_id },
                triggerEarningPulse: true,  // Signal to pulse builder $
            };
            return { type: 'task_state_changed', data: { task_id: d.task_id, new_status: status } };
        },
        'fi_trade_executed': (d) => ({
            type: 'sim_dex_trade',
            data: {
                quantity: d.quantity || d.fi_amount || d.amount || 100,
                ups_total: d.ups_total || 0,
                foundupIndex: d.foundup_index || 1,
            },
        }),
        'investor_funding_received': (d) => ({
            type: 'sim_staker_funding',  // CABR/PoB: staker (not investor)
            data: {
                btcAmount: d.btc_amount || d.amount || 0,
                sourceIndex: d.source_foundup_index || 0,
            },
        }),
        'mvp_subscription_accrued': (d) => ({ type: 'sim_mvp_subscription', data: { addedUps: d.added_ups || 0 } }),
        'mvp_bid_submitted': (d) => ({ type: 'sim_mvp_bid', data: { bidUps: d.bid_ups || 0 } }),
        'mvp_offering_resolved': (d) => ({ type: 'sim_mvp_resolved', data: { injectedUps: d.total_injection_ups || 0 } }),
        'milestone_published': (d) => ({ type: 'dao_launched', data: { milestone: d.milestone || 'MVP' } }),
        'lifecycle_changed': (d) => {
            if (d.stage === 'Proto') return { type: 'phase_changed', data: { phase: 'BUILDING' } };
            if (d.stage === 'MVP') return { type: 'phase_changed', data: { phase: 'LAUNCH' } };
            return null;
        },
        'customer_arrived': (d) => ({ type: 'customers_arrived', data: { count: d.count || 1 } }),
        'payout_triggered': (d) => ({
            type: 'payout_triggered',
            data: { amount: d.amount || 0, agentId: d.agent_id },
            triggerEarningPulse: true,
        }),
        'proof_submitted': (d) => ({
            type: 'proof_submitted',
            data: { proof_type: d.proof_type || 'work' },
        }),

        // Handshake events (WSP 15 gated)
        'work_approved': (d) => ({
            type: 'work_approved',
            data: { agentId: d.agent_id, foundupIndex: d.foundup_index || 1, mpsScore: d.mps_score },
        }),
        'work_rejected': (d) => ({
            type: 'work_rejected',
            data: { agentId: d.agent_id, reason: d.reason || 'MPS threshold not met' },
        }),
        'promoter_assigned': (d) => ({
            type: 'promoter_assigned',
            data: { agentId: d.agent_id, priority: d.mps_priority || 4 },
        }),
        'handshake_complete': (d) => ({
            type: 'handshake_complete',
            data: { agentId: d.agent_id, foundupIndex: d.foundup_index || 1 },
        }),
        // F_i Rating updated (color temperature gradient)
        'fi_rating_updated': (d) => ({
            type: 'fi_rating_updated',
            data: {
                foundupId: d.foundup_id,
                velocity: d.rating?.velocity || 0,
                traction: d.rating?.traction || 0,
                health: d.rating?.health || 0,
                potential: d.rating?.potential || 0,
                composite: d.rating?.composite || 0,
                borderColor: d.border_color || '#7c5cfc',
                tierName: d.tier_name || 'GREEN',
            },
        }),
        // CABR Score updated (3V Engine consensus)
        'cabr_score_updated': (d) => ({
            type: 'cabr_score_updated',
            data: {
                foundupId: d.foundup_id,
                env_score: d.env_score || 0,
                soc_score: d.soc_score || 0,
                part_score: d.part_score || 0,
                total: d.total || 0,
                threshold: d.threshold || 0.618,
                threshold_met: d.threshold_met || false,
                confidence: d.confidence || 0,
            },
        }),
        'cabr_pipe_flow_routed': (d) => ({
            type: 'cabr_pipe_flow_routed',
            data: {
                foundupId: d.foundup_id,
                cabr_pipe_size: d.cabr_pipe_size || 0,
                routed_ups: d.routed_ups || 0,
                worker_ups: d.worker_ups || 0,
                assignee_id: d.assignee_id || null,
            },
            triggerEarningPulse: true,
        }),

        // Agent Lifecycle Events (01(02) → 0102 → 01/02 state machine)
        'agent_joins': (d) => ({
            type: 'agent_joins',
            data: {
                actor_id: d.actor_id,
                agent_type: d.agent_type || 'user',
                public_key: d.public_key || '',
                rank: d.rank || 1,
                state: d.state || '01(02)',
                foundup_idx: d.foundup_idx || 1,
            },
        }),
        'agent_awakened': (d) => ({
            type: 'agent_awakened',
            data: {
                actor_id: d.actor_id,
                coherence: d.coherence || 0.72,
                state: d.state || '0102',
            },
        }),
        'agent_idle': (d) => ({
            type: 'agent_idle',
            data: {
                actor_id: d.actor_id,
                inactive_ticks: d.inactive_ticks || 0,
                current_tick: d.current_tick || 0,
                state: d.state || '01/02',
            },
        }),
        'agent_ranked': (d) => ({
            type: 'agent_ranked',
            data: {
                actor_id: d.actor_id,
                old_rank: d.old_rank || 1,
                new_rank: d.new_rank || 2,
                old_title: d.old_title || 'Apprentice',
                new_title: d.new_title || 'Builder',
            },
        }),
        'agent_earned': (d) => ({
            type: 'agent_earned',
            data: {
                actor_id: d.actor_id,
                amount: d.amount || 0,
                foundup_idx: d.foundup_idx || 1,
                task_id: d.task_id,
            },
            triggerEarningPulse: true,
        }),
        'agent_leaves': (d) => ({
            type: 'agent_leaves',
            data: {
                actor_id: d.actor_id,
                public_key: d.public_key || '',
                wallet_balance: d.wallet_balance || 0,
            },
        }),

        // State Sync Events (DRIVEN_MODE: simulator controls animation)
        'state_sync': (d) => ({
            type: 'state_sync',
            data: {
                phase: d.phase || 'IDEA',
                tick: d.tick || 0,
                foundups_count: d.foundups_count || 0,
                agents_count: d.agents_count || 0,
                total_fi: d.total_fi || 0,
                lifecycle_stage: d.lifecycle_stage || 'PoC',
                filled_blocks: d.filled_blocks || 0,
                total_blocks: d.total_blocks || 64,
            },
        }),
        'phase_command': (d) => ({
            type: 'phase_command',
            data: {
                target_phase: d.target_phase,
                force: d.force || false,
            },
        }),

        // Synthetic User Events (Simile AI pattern - pre-launch market testing)
        'synthetic_user_adopted': (d) => ({
            type: 'synthetic_user_adopted',
            data: {
                agentId: d.agent_id,
                foundupId: d.foundup_id,
                confidence: d.confidence || 0,
                reasons: d.reasons || [],
                viralCoefficient: d.viral_coefficient || 1.0,
                personaType: `${d.persona_income || 'medium'}_${d.persona_risk || 'moderate'}`,
            },
        }),
        'synthetic_user_rejected': (d) => ({
            type: 'synthetic_user_rejected',
            data: {
                agentId: d.agent_id,
                foundupId: d.foundup_id,
                confidence: d.confidence || 0,
                reasons: d.reasons || [],
                personaType: `${d.persona_income || 'medium'}_${d.persona_risk || 'moderate'}`,
            },
        }),
    };

    // ═══════════════════════════════════════════════════════════════════════
    // F_i RATING STATE (color temperature gradient for key border)
    // ═══════════════════════════════════════════════════════════════════════
    const fiRating = {
        velocity: 0.0,      // Agent execution rate (0102)
        traction: 0.0,      // Market response (012)
        health: 0.0,        // Operational state
        potential: 0.5,     // Founder conviction (neutral start)
        composite: 0.5,     // Weighted composite (0.0-1.0)
        borderColor: '#00B341',  // Default: GREEN (neutral)
        tierName: 'GREEN',

        // Color gradient stops for interpolation (VIOLET → RED)
        colorStops: [
            { stop: 0.0, color: '#8B00FF' },  // Violet
            { stop: 0.2, color: '#0066FF' },  // Blue
            { stop: 0.4, color: '#00E5D0' },  // Cyan
            { stop: 0.5, color: '#00B341' },  // Green
            { stop: 0.6, color: '#FFD700' },  // Yellow
            { stop: 0.8, color: '#FF8C00' },  // Orange
            { stop: 1.0, color: '#FF2D2D' },  // Red
        ],

        // Interpolate color based on composite rating
        getColor(rating) {
            const r = Math.max(0, Math.min(1, rating));
            let lower = this.colorStops[0];
            let upper = this.colorStops[this.colorStops.length - 1];

            for (let i = 0; i < this.colorStops.length; i++) {
                if (this.colorStops[i].stop <= r) lower = this.colorStops[i];
                if (this.colorStops[i].stop >= r) {
                    upper = this.colorStops[i];
                    break;
                }
            }

            if (upper.stop === lower.stop) return lower.color;

            const t = (r - lower.stop) / (upper.stop - lower.stop);
            return this.lerpColor(lower.color, upper.color, t);
        },

        // Linear interpolate between two hex colors
        lerpColor(c1, c2, t) {
            const hex = (c) => parseInt(c.slice(1), 16);
            const r1 = (hex(c1) >> 16) & 255, g1 = (hex(c1) >> 8) & 255, b1 = hex(c1) & 255;
            const r2 = (hex(c2) >> 16) & 255, g2 = (hex(c2) >> 8) & 255, b2 = hex(c2) & 255;
            const r = Math.round(r1 + t * (r2 - r1));
            const g = Math.round(g1 + t * (g2 - g1));
            const b = Math.round(b1 + t * (b2 - b1));
            return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
        },

        // Update from SSE event
        update(data) {
            this.velocity = data.velocity || this.velocity;
            this.traction = data.traction || this.traction;
            this.health = data.health || this.health;
            this.potential = data.potential || this.potential;
            this.composite = data.composite || (
                this.velocity * 0.30 + this.traction * 0.30 +
                this.health * 0.20 + this.potential * 0.20
            );
            this.borderColor = data.borderColor || this.getColor(this.composite);
            this.tierName = data.tierName || this.getTierName(this.composite);
        },

        getTierName(rating) {
            if (rating >= 0.9) return 'RED';
            if (rating >= 0.7) return 'ORANGE';
            if (rating >= 0.55) return 'YELLOW';
            if (rating >= 0.45) return 'GREEN';
            if (rating >= 0.3) return 'CYAN';
            if (rating >= 0.1) return 'BLUE';
            return 'VIOLET';
        },

        // Simulate gradual rating change (for demo without SSE)
        simulateProgress(phase, progress) {
            // Rating evolves with phase/progress
            if (phase === 'IDEA') {
                this.velocity = 0.1;
                this.traction = 0.0;
                this.health = 0.2;
                this.potential = 0.5;  // Neutral founder
            } else if (phase === 'SCAFFOLD') {
                this.velocity = 0.2 + progress * 0.2;
                this.traction = progress * 0.1;
                this.health = 0.3 + progress * 0.2;
            } else if (phase === 'BUILDING') {
                this.velocity = 0.4 + progress * 0.3;
                this.traction = 0.1 + progress * 0.2;
                this.health = 0.5 + progress * 0.3;
            } else if (phase === 'PROMOTING') {
                this.velocity = 0.5;
                this.traction = 0.3 + progress * 0.4;
                this.health = 0.7;
            } else if (phase === 'STAKING' || phase === 'CUSTOMERS') {
                this.velocity = 0.6;
                this.traction = 0.6 + progress * 0.2;
                this.health = 0.8;
            } else if (phase === 'LAUNCH' || phase === 'CELEBRATE') {
                this.velocity = 0.8;
                this.traction = 0.8;
                this.health = 0.9;
            }

            this.composite = (
                this.velocity * 0.30 + this.traction * 0.30 +
                this.health * 0.20 + this.potential * 0.20
            );
            this.borderColor = this.getColor(this.composite);
            this.tierName = this.getTierName(this.composite);
        }
    };

    // ═══════════════════════════════════════════════════════════════════════
    // CABR SCORE STATE (3V Engine: Validation → Verification → Valuation)
    // ═══════════════════════════════════════════════════════════════════════
    const cabrScore = {
        env_score: 0.0,      // Environmental impact (0-1)
        soc_score: 0.0,      // Social impact (0-1)
        part_score: 0.0,     // Participation metrics (0-1)
        total: 0.0,          // Weighted average
        threshold: 0.618,    // Golden ratio consensus threshold
        threshold_met: false,
        confidence: 0.0,

        // Update from SSE event
        update(data) {
            this.env_score = data.env_score ?? this.env_score;
            this.soc_score = data.soc_score ?? this.soc_score;
            this.part_score = data.part_score ?? this.part_score;
            this.total = data.total ?? this.total;
            this.threshold_met = data.threshold_met ?? (this.total >= this.threshold);
            this.confidence = data.confidence ?? this.confidence;
        },

        // Get display color based on threshold
        getColor() {
            return this.threshold_met ? '#00FF00' : '#FF6B6B';
        },

        // Simulate for demo mode
        simulateProgress(phase, progress) {
            // CABR evolves slower than F_i rating (impact takes time)
            if (phase === 'IDEA') {
                this.env_score = 0.3;
                this.soc_score = 0.4;
                this.part_score = 0.0;
            } else if (phase === 'SCAFFOLD' || phase === 'BUILDING') {
                this.env_score = 0.4;
                this.soc_score = 0.5;
                this.part_score = progress * 0.3;
            } else if (phase === 'PROMOTING' || phase === 'STAKING') {
                this.env_score = 0.5;
                this.soc_score = 0.6;
                this.part_score = 0.3 + progress * 0.3;
            } else if (phase === 'LAUNCH' || phase === 'CELEBRATE') {
                this.env_score = 0.6;
                this.soc_score = 0.7;
                this.part_score = 0.6 + progress * 0.2;
            }
            this.total = this.env_score * 0.33 + this.soc_score * 0.33 + this.part_score * 0.34;
            this.threshold_met = this.total >= this.threshold;
        }
    };

    function connectSimulatorBridge() {
        if (!FLAGS.USE_SIM_EVENTS || simBridge.connected) return;

        console.log('[CUBE] Connecting to SSE:', simBridge.endpoint);

        try {
            if (simBridge.eventSource) {
                simBridge.eventSource.close();
                simBridge.eventSource = null;
            }
            simBridge.eventSource = new EventSource(simBridge.endpoint);

            simBridge.eventSource.onopen = () => {
                simBridge.connected = true;
                simBridge.reconnectAttempts = 0;
                simBridge.reconnectDelay = simBridge.baseReconnectDelay;  // Reset backoff
                console.log('[CUBE] Simulator bridge connected to:', simBridge.endpoint);
                addTickerMessage('sim_connected', {});
            };

            // Handle named 'sim_event' events from SSE server
            simBridge.eventSource.addEventListener('sim_event', (event) => {
                try {
                    const simEvent = JSON.parse(event.data);
                    // Dedupe by sequence_id on reconnect
                    if (simEvent.sequence_id && simEvent.sequence_id <= simBridge.lastSequenceId) {
                        return;  // Skip duplicate
                    }
                    if (simEvent.sequence_id) {
                        simBridge.lastSequenceId = simEvent.sequence_id;
                    }
                    handleSimulatorEvent(simEvent);
                } catch (e) {
                    console.warn('[CUBE] Invalid sim_event:', e);
                }
            });

            // Handle 'connected' event from SSE server
            simBridge.eventSource.addEventListener('connected', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[CUBE] SSE connected:', data.mode);
                } catch (e) { /* ignore */ }
            });

            // Handle 'heartbeat' events (keepalive)
            simBridge.eventSource.addEventListener('heartbeat', () => {
                // Just a keepalive, no action needed
            });

            // Fallback for generic messages (legacy compatibility)
            simBridge.eventSource.onmessage = (event) => {
                try {
                    const simEvent = JSON.parse(event.data);
                    handleSimulatorEvent(simEvent);
                } catch (e) {
                    console.warn('[CUBE] Invalid simulator event:', e);
                }
            };

            simBridge.eventSource.onerror = () => {
                simBridge.connected = false;
                if (simBridge.eventSource) {
                    simBridge.eventSource.close();
                    simBridge.eventSource = null;
                }

                if (simBridge.reconnectAttempts < simBridge.maxReconnectAttempts) {
                    simBridge.reconnectAttempts++;
                    // Exponential backoff with jitter
                    const jitter = Math.random() * 1000;
                    simBridge.reconnectDelay = Math.min(
                        30000,  // Max 30s
                        simBridge.baseReconnectDelay * Math.pow(1.5, simBridge.reconnectAttempts) + jitter
                    );
                    console.log(`[CUBE] Reconnecting in ${Math.round(simBridge.reconnectDelay)}ms (attempt ${simBridge.reconnectAttempts})`);
                    setTimeout(connectSimulatorBridge, simBridge.reconnectDelay);
                } else {
                    console.warn('[CUBE] Max reconnect attempts reached, falling back to local animation');
                }
            };
        } catch (e) {
            console.warn('[CUBE] Simulator bridge unavailable:', e.message);
        }
    }

    function handleSimulatorEvent(simEvent) {
        // Handle both formats: {type, data} (legacy) and {event_type, payload} (SSE server)
        const eventType = simEvent.event_type || simEvent.type;
        const eventData = simEvent.payload || simEvent.data || {};

        const mapper = SIM_EVENT_MAP[eventType] || ((d) => ({
            type: eventType,
            data: d || {},
        }));

        const mapped = mapper(eventData);
        if (!mapped) return;

        // Emit as internal cube event
        emitEvent(mapped.type, mapped.data);

        // Spawn $ earning pulse for economic events or if mapper signals it
        if (mapped.triggerEarningPulse || isEconomicEvent(eventType)) {
            spawnEarningPulse(eventType, eventData);
            // Pulse a random builder's $ to show earning
            pulseBuilderEarning(mapped.data?.agentId);
        }

        // Track lifecycle stage changes
        if (eventType === 'lifecycle_changed') {
            simBridge.lastLifecycleStage = eventData.stage;
        }

        // Update F_i rating from SSE (color temperature gradient)
        if (mapped.type === 'fi_rating_updated') {
            fiRating.update(mapped.data);
        }

        // Update CABR score from SSE (3V engine consensus)
        if (mapped.type === 'cabr_score_updated') {
            cabrScore.update(mapped.data);
        }

        // Handle state_sync for DRIVEN_MODE
        if (mapped.type === 'state_sync') {
            handleStateSync(mapped.data);
        }

        // Handle phase_command for direct control
        if (mapped.type === 'phase_command') {
            setPhase(mapped.data.target_phase, { force: mapped.data.force });
        }
    }

    // Pulse a builder's $ to show earning (synced with ticker event)
    function pulseBuilderEarning(targetAgentId) {
        // Find builders to pulse
        const builders = agents.filter(a => a.type === 'builder');
        if (builders.length === 0) return;

        // If specific agent, try to find it; otherwise pick random
        let builder = builders.find(a => a.id === targetAgentId);
        if (!builder) {
            builder = builders[Math.floor(Math.random() * builders.length)];
        }

        // Set earning pulse state (will be picked up by draw loop)
        builder.earningPulse = Date.now();
        builder.earningPulseIntensity = 1.0;
    }

    // Check if event is economic (triggers $ earning pulse)
    function isEconomicEvent(eventType) {
        const economicEvents = [
            'payout_triggered',
            'fi_trade_executed',
            'investor_funding_received',
            'mvp_offering_resolved',
            'mvp_bid_submitted',
            'mvp_subscription_accrued',
            'agent_earned',  // Explicit earning event
            'cabr_pipe_flow_routed',
        ];
        return economicEvents.includes(eventType);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // FEATURE RESTRICTOR — toggle features on/off for debugging
    // ═══════════════════════════════════════════════════════════════════════
    const FEATURES = {
        enableCelebrations: false,   // Agent celebration size pulse (OFF — caused bloating)
        enableSpazzing: false,       // Agent excited jitter (OFF — 0102 agents stay in zen state)
        enableStaker: true,          // Spawn staker agents (CABR/PoB: not investor)
        enablePromoter: true,        // Spawn promoter agents
        enableRecruiting: true,      // Promoters recruit new agents
        enableAgentGlow: true,       // Shadow glow around agents
        enableTicker: true,          // Bottom ticker messages
        enableConfetti: false,       // Celebration confetti (OFF — visual noise)
        enableGoldReturn: true,      // Agents leave with gold, return to earn more
        enableLaunchPan: true,       // Camera pan effect on Public Launch
        maxAgentSize: 6,             // Hard cap on agent visual radius
    };

    // ═══════════════════════════════════════════════════════════════════════
    // CONFIGURATION
    // ═══════════════════════════════════════════════════════════════════════
    const CONFIG = {
        targetSize: 4,          // 4x4x4 cube
        agentSpawnRate: 0.003,  // Slower spawn for 120s loop
        maxAgents: 12,          // Fewer agents to reduce visual clutter
        fiPerBlock: 50,
        loopDuration: 120000,   // 120s total loop (2 minutes - contemplative pace)
    };

    // ═══════════════════════════════════════════════════════════════════════
    // PHASE DEFINITIONS (~120s deterministic loop — deliberate pacing)
    // ═══════════════════════════════════════════════════════════════════════
    // Story Arc: IDEA → SCAFFOLD → BUILD → PROMOTE → STAKING → CUSTOMERS → LAUNCH
    // Slower IDEA phase (spark of inspiration takes time)
    // Total: 15+12+48+0+12+12+10+6+5+0 = 120s
    const PHASES = {
        IDEA: { duration: 15000, next: 'SCAFFOLD' },       // 15s - slow, deliberate ideation
        SCAFFOLD: { duration: 12000, next: 'BUILDING' },   // 12s - planning architecture
        BUILDING: { duration: 48000, next: 'COMPLETE' },   // 48s - main building phase
        COMPLETE: { duration: 0, next: 'PROMOTING' },
        PROMOTING: { duration: 12000, next: 'STAKING' },   // 12s - spreading the word
        STAKING: { duration: 12000, next: 'CUSTOMERS' },   // 12s - BTC stakers arrive (CABR/PoB)
        CUSTOMERS: { duration: 10000, next: 'LAUNCH' },    // 10s - first paying users
        LAUNCH: { duration: 6000, next: 'CELEBRATE' },     // 6s - MVP launch moment
        CELEBRATE: { duration: 5000, next: 'RESET' },      // 5s - celebration
        RESET: { duration: 0, next: 'IDEA' },
    };

    // ═══════════════════════════════════════════════════════════════════════
    // PRE-OPO / POST-OPO LIFECYCLE (pAVS invite gate model)
    // ═══════════════════════════════════════════════════════════════════════
    // Pre-OPO (60%): Invite-only, Angels stake for OPO access
    // Post-OPO (40%): Public access, full fee revenue enabled
    const PRE_OPO_PHASES = Object.freeze(new Set([
        'IDEA', 'SCAFFOLD', 'BUILDING', 'COMPLETE', 'PROMOTING', 'STAKING'
    ]));
    const POST_OPO_PHASES = Object.freeze(new Set([
        'CUSTOMERS', 'LAUNCH', 'CELEBRATE'
    ]));

    // Check if current phase is Pre-OPO (behind invite gate)
    function isPreOPO() {
        return PRE_OPO_PHASES.has(currentPhase);
    }

    // OPO event triggers when transitioning from STAKING → CUSTOMERS
    let opoTriggered = false;
    let opoTransitionTime = 0;

    // ═══════════════════════════════════════════════════════════════════════
    // VISION STATEMENTS (rotate per loop - each FoundUp starts with a dream)
    // Keywords: peer-to-peer, decentralized, community, owned by stakeholders
    // Not just code - ANY community-beneficial venture
    // ═══════════════════════════════════════════════════════════════════════
    const VISION_STATEMENTS = Object.freeze([
        // Tech platforms (decentralized)
        'A decentralized YouTube owned by its stakeholders',
        'A peer-to-peer Twitter with no corporate overlord',
        'An open-source Uber where drivers own the platform',
        'A community-owned Airbnb with no middleman',
        'A decentralized GitHub built by its contributors',
        'A peer-to-peer Spotify where artists earn directly',
        // AI & Knowledge
        'An AI marketplace owned by its creators',
        'A community knowledge base that pays contributors',
        'Decentralized tutoring owned by teachers & students',
        // Real-world community services
        'Community egg distribution managed by neighbors',
        'A peer-to-peer tool library for the neighborhood',
        'Decentralized childcare co-op owned by parents',
        'Community garden coordination with shared harvests',
        'Peer-to-peer meal sharing for elderly neighbors',
        // Finance & Commerce
        'A community banking platform with zero fees',
        'Peer-to-peer lending circles for small businesses',
        'Decentralized farmers market with direct sales',
        'Community investment club owned by members',
        // Creative & Cultural
        'A decentralized film studio owned by creators',
        'Peer-to-peer music venue booking for indie bands',
        'Community art gallery with artist-owned curation',
        'Decentralized podcast network owned by listeners',
        // Local Services
        'Peer-to-peer home repair coordination',
        'Community rideshare owned by the neighborhood',
        'Decentralized pet-sitting network for pet lovers',
        'Peer-to-peer language exchange owned by learners',
    ]);

    // ═══════════════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════════════
    let canvas, ctx, w, h;
    let animationFrameId = null;
    let initializedCanvasId = null;
    let resizeHandler = null;
    let apiHandle = null;
    let currentPhase = 'IDEA';
    let phaseStartTime = 0;
    let loopStartTime = 0;
    let time = 0;
    let fiEarned = 0;
    let loopCount = 0;
    let speedMultiplier = 1.0;  // Speed slider: 0.25x to 5x

    const agents = [];
    const filledBlocks = new Set();
    const confetti = [];
    const particles = [];
    const earningPulses = [];  // Pulsing $ indicators around cube during economic events
    // (Construction beams removed - agents now move TO blocks physically)

    // Event subscribers (Phase 5)
    const eventSubscribers = [];

    // Camera state (Phase 2/3)
    const camera = {
        x: 0,
        y: 0,
        scale: STYLE.camera.defaultScale,
        targetX: 0,
        targetY: 0,
        targetScale: STYLE.camera.defaultScale,
    };

    // Camera handoff state (Phase 2: camera pans between cubes)
    const cameraHandoff = {
        enabled: false,          // Activate after FLAGS.MULTI_CUBE or 3rd loop
        cubeCount: 0,            // Number of completed cubes
        maxCubesBeforeZoom: 3,   // After 3 cubes, zoom out to reveal all
        isTransitioning: false,  // True during pan animation
        transitionProgress: 0,   // 0-1 pan progress
        transitionDuration: 2000, // ms for pan animation
        cubePositions: [],       // [{x, y, scale, loopCount, phase}]
        zoomedOut: false,        // True when showing all cubes
    };

    // Launch pan state - fake camera drift on "Public Launch Party!!"
    const launchPan = {
        active: false,
        startTime: 0,
        duration: 8000,          // Pan duration in ms
        startX: 0,
        startY: 0,
        targetX: -200,           // Drift left (simulate pan right)
        targetY: -50,            // Drift up slightly
    };

    // ═══════════════════════════════════════════════════════════════════════
    // MOUSE INTERACTION STATE
    // ═══════════════════════════════════════════════════════════════════════
    const mouse = {
        x: 0,
        y: 0,
        isDown: false,
        isDragging: false,
        startX: 0,
        startY: 0,
        isOverCanvas: false,
        hoveredAgent: null,     // Agent currently under cursor
    };

    // Selected agent tooltip state
    let selectedAgent = null;
    let selectedAgentTime = 0;

    // Cube rotation from mouse drag
    const cubeRotation = {
        x: 0,
        y: 0,
        targetX: 0,
        targetY: 0,
    };

    // Easter egg: click promoters to create staker (BTC liquidity provider)
    const easterEgg = {
        promoterClicks: 0,
        lastClickTime: 0,
        clickTimeout: 2000,  // Reset after 2 seconds
    };

    // ═══════════════════════════════════════════════════════════════════════
    // SIMULATED TIME (S-curve mapping)
    // ~86s loop = ~3 years (1095 days) compressed
    // Time compression: 1 real second = ~12.7 simulated days
    // ═══════════════════════════════════════════════════════════════════════
    const simTime = {
        daysPerLoop: 1095,              // 3 years in days
        loopDuration: CONFIG.loopDuration,  // 86000ms
        startTimestamp: 0,
    };

    function getSimulatedTime() {
        const elapsed = getScaledElapsed(loopStartTime);
        const progress = elapsed / simTime.loopDuration;
        const totalDays = progress * simTime.daysPerLoop;

        const years = Math.floor(totalDays / 365);
        const days = Math.floor(totalDays % 365);
        const hours = Math.floor((totalDays % 1) * 24);

        if (years > 0) {
            return `Y${years + 1} D${days}`;
        } else if (days > 0) {
            return `D${days} H${hours}`;
        } else {
            return `H${Math.max(1, hours)}`;
        }
    }

    // Live chat state (left side - stream chat style)
    const liveChat = {
        messages: [],
        maxMessages: 14,       // FAM DAEmon event stream depth
        lineHeight: 16,        // Tighter for more events
        animDuration: 300,     // Pop-up animation duration (ms)
        slideDistance: 24,     // How far messages slide up (px)
        panelWidth: 220,       // Wider for full FAM event messages
        panelPadding: 8,
    };

    // Subscript helper for F₁, F₂, etc.
    function toSubscript(num) {
        const subscripts = '₀₁₂₃₄₅₆₇₈₉';
        return String(num).split('').map(d => subscripts[parseInt(d)] || d).join('');
    }

    // Ticker message templates by activity
    const TICKER_MESSAGES = {
        agent_spawned: (d) => `${d.type} joins the build...`,
        agent_recruited: (d) => `new ${d.type} recruited!`,
        block_filled: (d) => `block ${d.x},${d.y},${d.z} built (${d.total}/64)`,
        phase_changed: (d) => `phase: ${d.phase}`,
        promoter_recruited: (d) => `promoter brought ${d.count} agents!`,
        staker_arrived: () => `BTC staker enters with liquidity`,
        customers_arrived: (d) => `${d.count} customers arrived!`,
        opo_gate_opens: (d) => `OPO GATE OPENS - F${toSubscript(d.foundupIndex || 1)} is PUBLIC!`,
        dao_launched: () => `Foundup_i MVP is Live!`,
        cube_complete: () => `cube complete - all 64 blocks built`,
        loop_started: (d) => `new foundup #${d.loopCount} starting...`,

        // Agent handshake & earning events (FAM DAEmon integration)
        agent_earned: (d) => `Agent EARNs F${toSubscript(d.foundupIndex || 1)}`,
        work_approved: (d) => `ORCH approves ${d.agentId || '0102'} → F${toSubscript(d.foundupIndex || 1)}`,
        work_rejected: (d) => `ORCH rejects ${d.agentId || '0102'}: ${d.reason || 'MPS too low'}`,
        promoter_assigned: (d) => `${d.agentId || '0102'} → promoter track (MPS P${d.priority || 4})`,
        handshake_complete: (d) => `handshake: ${d.agentId || '0102'} ↔ F${toSubscript(d.foundupIndex || 1)}`,

        // Agent lifecycle events (01(02) → 0102 → 01/02 state machine)
        agent_joins: (d) => `01(02) ${(d.public_key || '').slice(0, 10)}... enters${d.agent_type ? ` (${d.agent_type})` : ''}`,
        agent_awakened: (d) => `0102 ${d.actor_id || 'agent'} ZEN (${(d.coherence || 0.72).toFixed(2)})`,
        agent_idle: (d) => `01/02 ${d.actor_id || 'agent'} IDLE (${d.inactive_ticks || 0} ticks)`,
        agent_ranked: (d) => `${d.actor_id || 'agent'} rank UP: ${d.old_rank || 1}→${d.new_rank || 2} (${d.new_title || 'Builder'})`,
        agent_earned: (d) => `${d.actor_id || 'agent'} earned ${d.amount || 0} F${toSubscript(d.foundup_idx || 1)}`,
        agent_leaves: (d) => `${(d.public_key || '').slice(0, 10)}... logs off (${d.wallet_balance || 0} Fᵢ)`,
        orch_handoff: (d) => `ORCH → ${d.actor_id || '0102'}: build ${d.module || 'module'}`,

        // SmartDAO escalation events (WSP 100: F₀ DAE → F₁+ SmartDAO)
        smartdao_emergence: (d) => `F${toSubscript(d.foundup_idx || 0)} → SmartDAO F${toSubscript(d.new_tier || 1)} EMERGENCE`,
        tier_escalation: (d) => `F${toSubscript(d.old_tier || 0)} → F${toSubscript(d.new_tier || 1)} TIER UP`,
        treasury_autonomy: (d) => `F${toSubscript(d.foundup_idx || 1)} TREASURY AUTONOMOUS`,
        cross_dao_funding: (d) => `F${toSubscript(d.source_tier || 2)} funds F${toSubscript(d.target_tier || 0)}: ${d.amount || 0} UPS`,

        // FAM module building events (what agents build)
        build_registry: (d) => `0102 builds REGISTRY module`,
        build_task_pipeline: (d) => `0102 builds TASK_PIPELINE module`,
        build_token_econ: (d) => `0102 builds TOKEN_ECON module`,
        build_persistence: (d) => `0102 builds PERSISTENCE module`,
        build_events: (d) => `0102 builds EVENTS module`,
        build_governance: (d) => `0102 builds GOVERNANCE module`,
        build_api: (d) => `0102 builds API module`,

        // Simulated activity messages
        sim_holo_indexing: () => `0102 holo indexing...`,
        sim_planning: () => `0102 planning architecture...`,
        sim_researching: () => `0102 researching solutions...`,
        sim_creating_collaterals: () => `0102 creating collaterals...`,
        sim_security_audit: () => `0102 performing security audit...`,
        sim_promoting: () => `0102 promoting foundup...`,
        sim_dex_trade: (d) => `DEX: ${d.quantity || '100'} F${toSubscript(d.foundupIndex || 1)} traded (UPS: ${d.ups_total || 0})`,
        sim_staker_funding: (d) => `BTC stake (F${toSubscript(d.sourceIndex || 0)}): ${d.btcAmount || 0} BTC`,
        sim_mvp_subscription: (d) => `subscription accrued: +${d.addedUps || 0} UPS`,
        sim_mvp_bid: (d) => `MVP bid submitted: ${d.bidUps || 0} UPS`,
        sim_mvp_resolved: (d) => `MVP offering resolved: +${d.injectedUps || 0} UPS treasury`,
        fi_ups_exchange: (d) => `Stake ${d.upsAmount || 50} UPS @ ${d.bondingPrice || '0.01'} → ${d.fiAmount || 100} F${toSubscript(d.foundupIndex || 1)}`,
        sim_connected: () => `simulator connected - live events active`,

        // FAM DAEmon event mappings (from SSE stream)
        task_state_changed: (d) => `task ${d.task_id || '?'}: ${d.new_status || 'updated'}`,
        proof_submitted: (d) => `proof submitted: ${d.proof_type || 'work'}`,
        payout_triggered: (d) => `payout: ${d.amount || 0} UPS`,
        foundup_created: (d) => `F${toSubscript(d.foundupIndex || 1)} created: ${d.name || 'new foundup'}`,
    };

    // ═══════════════════════════════════════════════════════════════════════
    // AGENT BEHAVIORS (WSP 54 roles)
    // ═══════════════════════════════════════════════════════════════════════
    const BEHAVIORS = {
        normal: { weight: 0.7, speedMod: 1.0 },
        eager: { weight: 0.15, speedMod: 1.5 },
        methodical: { weight: 0.1, speedMod: 0.6 },
        chaotic: { weight: 0.05, speedMod: 1.2 },
    };

    const QUIRKS = {
        spazOut: 0.02,
        wander: 0.03,
        celebrate: 0.01,
        recruit: 0.5,  // 50% chance promoter returns with agents after spazzing
    };

    // ═══════════════════════════════════════════════════════════════════════
    // UTILITY FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════
    function isoProject(x, y, z, ox, oy, s) {
        // Apply rotation from mouse/touch drag (rotate around cube center)
        const rotX = cubeRotation.x;  // Pitch (vertical drag)
        const rotY = cubeRotation.y;  // Yaw (horizontal drag)

        // Rotate around Y axis (horizontal drag = spin left/right)
        const cosY = Math.cos(rotY);
        const sinY = Math.sin(rotY);
        let rx = x * cosY - z * sinY;
        let rz = x * sinY + z * cosY;

        // Rotate around X axis (vertical drag = tilt forward/back)
        const cosX = Math.cos(rotX);
        const sinX = Math.sin(rotX);
        let ry = y * cosX - rz * sinX;
        rz = y * sinX + rz * cosX;

        // Standard isometric projection
        const ix = (rx - ry) * s * 0.866;
        const iy = (rx + ry) * s * 0.5 - rz * s;
        return { x: ox + ix, y: oy + iy };
    }

    function shadeColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.min(255, Math.max(0, (num >> 16) + amt));
        const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt));
        const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt));
        return `rgb(${R},${G},${B})`;
    }

    function pickBehavior() {
        const roll = Math.random();
        let cumulative = 0;
        for (const [name, data] of Object.entries(BEHAVIORS)) {
            cumulative += data.weight;
            if (roll < cumulative) return name;
        }
        return 'normal';
    }

    function emitEvent(type, data) {
        const event = { type, data, timestamp: Date.now(), phase: currentPhase };
        eventSubscribers.forEach(fn => {
            try { fn(event); } catch (e) { console.error('Event subscriber error:', e); }
        });
        // Auto-add to ticker if template exists
        addTickerMessage(type, data);
        // Phase 6: Write to Firestore
        firestoreBridge.writeEvent(type, data);
        // Track loop starts and Fi earned
        if (type === 'loop_started') firestoreBridge.onLoopStart();
        if (type === 'fi_ups_exchange' && data?.fiAmount) firestoreBridge.onFiEarned(data.fiAmount);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // LIVE CHAT FUNCTIONS (Stream chat style - left side)
    // ═══════════════════════════════════════════════════════════════════════
    function addTickerMessage(type, data) {
        const template = TICKER_MESSAGES[type];
        if (!template) return;

        const text = template(data || {});
        const simTimeStr = getSimulatedTime();

        // Bump existing messages up (reset their slide animation for cascade effect)
        liveChat.messages.forEach(m => {
            if (m.animProgress > 0.7) {
                m.bumpProgress = 0;  // Reset bump animation for cascade
            }
        });

        liveChat.messages.push({
            text,
            timestamp: Date.now(),
            simTime: simTimeStr,
            alpha: 1,
            type: type,           // Store type for color coding
            animProgress: 0,      // 0 = just appeared, 1 = fully in place
            bumpProgress: 1,      // For cascade bump when new messages arrive
        });

        // Limit messages
        while (liveChat.messages.length > liveChat.maxMessages) {
            liveChat.messages.shift();
        }
    }

    function updateTicker() {
        const dt = 16;  // Approximate frame time (60fps)

        // Animate messages and fade over time
        liveChat.messages.forEach(m => {
            const age = Date.now() - m.timestamp;
            m.alpha = Math.max(0.3, 1 - age / 20000);  // Min 0.3 alpha for readability

            // Pop-up animation (new messages slide up from bottom)
            if (m.animProgress < 1) {
                m.animProgress = Math.min(1, m.animProgress + dt / liveChat.animDuration);
            }

            // Bump animation (existing messages nudge up when new one arrives)
            if (m.bumpProgress < 1) {
                m.bumpProgress = Math.min(1, m.bumpProgress + dt / (liveChat.animDuration * 0.5));
            }
        });

        // Remove very old messages
        liveChat.messages = liveChat.messages.filter(m => m.alpha > 0.2);

        // Add simulated activity messages during BUILD phase
        if (currentPhase === 'BUILDING' && Math.random() < 0.004) {
            const simTypes = [
                'sim_holo_indexing', 'sim_planning', 'sim_researching',
                'sim_creating_collaterals', 'sim_security_audit'
            ];
            const simType = simTypes[Math.floor(Math.random() * simTypes.length)];
            addTickerMessage(simType, {});
        }

        // Add promoting messages during PROMOTING phase
        if (currentPhase === 'PROMOTING' && Math.random() < 0.01) {
            addTickerMessage('sim_promoting', {});
        }

        // Add F_i staking events during BUILD/PROMOTING (S-curve economics per WSP 26)
        // CABR/PoB: Stakers provide BTC liquidity → receive F_i distributions
        if ((currentPhase === 'BUILDING' || currentPhase === 'PROMOTING') && Math.random() < 0.006) {
            const fi = loopCount;  // Current FoundUp (F_1, F_2, etc)
            // S-curve adoption: progress determines token release rate
            const totalBlocks = Math.pow(CONFIG.targetSize, 3);
            const progress = filledBlocks.size / totalBlocks;  // 0-1 adoption proxy
            // Bonding curve: price = k × supply² (Bitclout model, k=0.0001)
            // More tokens released = higher price per F_i
            const supplyReleased = Math.floor(progress * 21000);  // 21K token pool proxy
            const bondingPrice = 0.0001 * Math.pow(supplyReleased / 1000, 2) + 0.001;  // UPS/F_i
            const upsStaked = Math.floor(Math.random() * 200) + 50;  // Staker provides 50-250 UPS
            const fiReceived = Math.floor(upsStaked / bondingPrice);  // F_i received at curve price
            addTickerMessage('fi_ups_exchange', { foundupIndex: fi, upsAmount: upsStaked, fiAmount: fiReceived, bondingPrice: bondingPrice.toFixed(4) });
        }
    }

    function drawLiveChat() {
        if (liveChat.messages.length === 0) return;

        const panelW = Math.min(320, w - 20);  // Responsive width
        const lineH = liveChat.lineHeight;
        const padding = liveChat.panelPadding;
        const visible = liveChat.messages.slice(-liveChat.maxMessages);
        const panelH = visible.length * lineH + 28;  // Dynamic height based on messages

        // Position at BOTTOM - messages pop UP like TikTok LiveChat
        const panelX = 15;  // Left margin
        const panelY = h - panelH - 60;  // Bottom, above status bar

        // No background, no border - blend with scene, ticker runs behind cube
        // Just draw messages directly on canvas

        // Draw messages - newest at BOTTOM (pop up from bottom with animation)
        ctx.font = '9px monospace';
        ctx.textAlign = 'left';

        visible.forEach((m, i) => {
            // Easing function for smooth pop-up (ease-out quad)
            const easeOut = t => 1 - (1 - t) * (1 - t);
            // Elastic bounce for scale (overshoot then settle)
            const elasticOut = t => {
                if (t >= 1) return 1;
                return 1 + Math.pow(2, -10 * t) * Math.sin((t - 0.1) * 5 * Math.PI);
            };

            const animEased = easeOut(m.animProgress || 1);
            const bumpEased = easeOut(m.bumpProgress || 1);
            const scaleEased = elasticOut(m.animProgress || 1);

            // Y offset: new messages pop up from below, bump offset for cascade
            const slideOffset = (1 - animEased) * liveChat.slideDistance;
            const bumpOffset = (1 - bumpEased) * (liveChat.slideDistance * 0.4);
            const alpha = m.alpha * animEased;  // Fade in with animation
            const scale = 0.85 + 0.15 * Math.min(1, scaleEased);  // Scale from 85% to 100%

            const lineY = panelY + 24 + (i * lineH) + slideOffset + bumpOffset;
            const textX = panelX + padding + 32;

            // Apply scale transform for newest message pop effect
            if (m.animProgress < 1) {
                ctx.save();
                ctx.translate(textX, lineY);
                ctx.scale(scale, scale);
                ctx.translate(-textX, -lineY);
            }

            // Timestamp (left, dim purple)
            ctx.fillStyle = `rgba(124, 92, 252, ${alpha * 0.6})`;
            ctx.fillText(m.simTime, panelX + padding, lineY);

            // Message color by type
            let color = `rgba(228, 226, 236, ${alpha * 0.85})`;

            if (m.type === 'agent_earned' || m.type === 'payout_triggered') {
                color = `rgba(0, 255, 136, ${alpha})`;  // Bright green for earning
            } else if (m.type === 'fi_ups_exchange') {
                color = `rgba(255, 215, 0, ${alpha})`;  // GOLD for F_i ↔ UPS exchange
            } else if (m.type === 'dao_launched' || m.text.includes('MVP') || m.text.includes('Live')) {
                color = `rgba(255, 215, 0, ${alpha})`;  // Gold for MVP
            } else if (m.type === 'staker_arrived' || m.text.includes('staker') || m.text.includes('BTC stake')) {
                color = `rgba(255, 215, 0, ${alpha * 0.9})`;  // Gold for staker
            } else if (m.type === 'customers_arrived' || m.text.includes('customer')) {
                color = `rgba(0, 229, 208, ${alpha})`;  // Cyan for customers
            } else if (m.type === 'agent_spawned' || m.type === 'agent_recruited') {
                color = `rgba(0, 229, 208, ${alpha * 0.8})`;  // Cyan for agents
            } else if (m.type === 'block_filled') {
                color = `rgba(255, 141, 0, ${alpha * 0.8})`;  // Orange for blocks
            } else if (m.type === 'work_approved' || m.type === 'handshake_complete') {
                color = `rgba(124, 92, 252, ${alpha})`;  // Purple for handshake
            } else if (m.type === 'work_rejected' || m.type === 'promoter_assigned') {
                color = `rgba(255, 100, 100, ${alpha * 0.8})`;  // Red for rejected/demoted
            } else if (m.type && m.type.startsWith('sim_')) {
                color = `rgba(180, 180, 200, ${alpha * 0.6})`;  // Dim for sim messages
            }

            ctx.fillStyle = color;
            // Full message text
            ctx.fillText(m.text, textX, lineY);

            // Restore transform if we applied scale
            if (m.animProgress < 1) {
                ctx.restore();
            }
        });

        ctx.textAlign = 'center'; // Restore default
    }

    // Legacy alias for compatibility
    function drawTicker() {
        drawLiveChat();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // CAMERA HANDOFF (Phase 2)
    // After cube completes, pan camera to next spawn position
    // Repeat 3 times, then zoom out to reveal all cubes
    // ═══════════════════════════════════════════════════════════════════════
    function updateCamera() {
        // Handle launch pan effect (fake camera drift on "Public Launch")
        if (FEATURES.enableLaunchPan && launchPan.active) {
            const elapsed = Date.now() - launchPan.startTime;
            const progress = Math.min(1, elapsed / launchPan.duration);
            const eased = STYLE.easing.quadInOut(progress);

            camera.targetX = launchPan.startX + (launchPan.targetX - launchPan.startX) * eased;
            camera.targetY = launchPan.startY + (launchPan.targetY - launchPan.startY) * eased;

            if (progress >= 1) {
                launchPan.active = false;
            }
        }

        // Smooth camera movement toward target
        const lerpSpeed = 0.05;
        camera.x += (camera.targetX - camera.x) * lerpSpeed;
        camera.y += (camera.targetY - camera.y) * lerpSpeed;
        camera.scale += (camera.targetScale - camera.scale) * lerpSpeed;

        // Auto-speed: zoom in → slow down (see detail), zoom out → speed up (ecosystem)
        // Scale 25 (close) → 0.25x, Scale 15 (default) → 1x, Scale 3 (far) → 5x
        const defaultScale = STYLE.camera.defaultScale;
        if (camera.scale >= defaultScale) {
            // Zoomed in: slow down (25→0.25x, 15→1x)
            speedMultiplier = 1 - (camera.scale - defaultScale) / (STYLE.camera.maxScale - defaultScale) * 0.75;
        } else {
            // Zoomed out: speed up (15→1x, 3→5x)
            speedMultiplier = 1 + (defaultScale - camera.scale) / (defaultScale - STYLE.camera.minScale) * 4;
        }
        speedMultiplier = Math.max(0.25, Math.min(5, speedMultiplier));
        // Update slider to reflect auto-speed
        const slider = document.getElementById('speedSlider');
        const label = document.getElementById('speedValue');
        if (slider) slider.value = speedMultiplier;
        if (label) label.textContent = speedMultiplier.toFixed(1) + 'x';

        // Smooth cube rotation from mouse drag
        cubeRotation.x += (cubeRotation.targetX - cubeRotation.x) * lerpSpeed;
        cubeRotation.y += (cubeRotation.targetY - cubeRotation.y) * lerpSpeed;

        // Update handoff transition
        if (cameraHandoff.isTransitioning) {
            cameraHandoff.transitionProgress += 16 / cameraHandoff.transitionDuration;
            if (cameraHandoff.transitionProgress >= 1) {
                cameraHandoff.transitionProgress = 1;
                cameraHandoff.isTransitioning = false;
            }
        }
    }

    function startLaunchPan() {
        if (!FEATURES.enableLaunchPan) return;

        launchPan.active = true;
        launchPan.startTime = Date.now();
        launchPan.startX = camera.x;
        launchPan.startY = camera.y;
        // Pan direction: drift content left (camera moves right relative)
        launchPan.targetX = -150 + Math.random() * 50;
        launchPan.targetY = -30 + Math.random() * 20;
    }

    function resetCameraPan() {
        launchPan.active = false;
        camera.targetX = 0;
        camera.targetY = 0;
    }

    function triggerCameraHandoff() {
        if (!FLAGS.MULTI_CUBE) return;

        // Save current cube position
        cameraHandoff.cubePositions.push({
            x: camera.x,
            y: camera.y,
            scale: camera.scale,
            loopCount: loopCount,
            phase: 'COMPLETE',
        });

        cameraHandoff.cubeCount++;

        // After maxCubesBeforeZoom, zoom out to show all
        if (cameraHandoff.cubeCount >= cameraHandoff.maxCubesBeforeZoom && !cameraHandoff.zoomedOut) {
            triggerZoomOut();
            return;
        }

        // Pan camera to new position for next cube
        cameraHandoff.isTransitioning = true;
        cameraHandoff.transitionProgress = 0;

        // New cube spawns offset from previous
        const offsetX = (cameraHandoff.cubeCount % 2 === 0) ? -200 : 200;
        const offsetY = 50 * cameraHandoff.cubeCount;
        camera.targetX = offsetX;
        camera.targetY = offsetY;

        emitEvent('camera_handoff', { cubeCount: cameraHandoff.cubeCount });
    }

    function triggerZoomOut() {
        cameraHandoff.zoomedOut = true;
        cameraHandoff.isTransitioning = true;
        cameraHandoff.transitionProgress = 0;

        // Zoom out to show all cubes
        camera.targetScale = STYLE.camera.minScale;
        camera.targetX = 0;
        camera.targetY = 0;

        emitEvent('zoom_out', { cubeCount: cameraHandoff.cubeCount });
        addTickerMessage('phase_changed', { phase: 'ECOSYSTEM VIEW' });
    }

    function getCameraOffset() {
        // Returns camera offset for drawing
        return {
            x: camera.x,
            y: camera.y,
            scale: camera.scale,
        };
    }

    // ═══════════════════════════════════════════════════════════════════════
    // LIFECYCLE STAGE TRACKING (WSP modular approach)
    // PoC (IDEA) -> Proto (SCAFFOLD + BUILDING) -> MVP (near complete)
    // ═══════════════════════════════════════════════════════════════════════
    function getLifecycleStage() {
        const totalBlocks = Math.pow(CONFIG.targetSize, 3);
        const filled = filledBlocks.size;
        const pct = filled / totalBlocks;

        // PoC = founder alone with idea (IDEA phase)
        if (currentPhase === 'IDEA') return 'PoC';
        // Proto = scaffolding starts, agents building (SCAFFOLD + most of BUILDING)
        if (currentPhase === 'SCAFFOLD') return 'Proto';
        if (pct < 0.85) return 'Proto';  // Still building prototype
        // MVP = near completion (85%+)
        if (pct < 1.0) return 'MVP';
        return 'Complete';
    }

    // Calculate how many scaffold layers to show based on elapsed time in SCAFFOLD phase
    function getScaffoldLayersToShow() {
        if (currentPhase === 'IDEA') return 0;
        if (currentPhase !== 'SCAFFOLD') return CONFIG.targetSize;  // All layers after SCAFFOLD

        const elapsed = getScaledElapsed(phaseStartTime);
        const phaseDuration = PHASES.SCAFFOLD.duration;
        const progress = Math.min(1, elapsed / phaseDuration);

        // Progressive reveal: 0 -> 4 layers over SCAFFOLD duration
        return Math.floor(progress * CONFIG.targetSize) + 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // DRAWING FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════
    // Sub-block color palette for internal block detail
    // Each filled block shows a 2x2 grid of colored sub-blocks on each face
    const SUB_COLORS = Object.freeze([
        '#ff2d2d', '#ff8c00', '#ffd700', '#00b341', '#0066ff',
        '#9b59b6', '#00e5d0', '#ff6b9d', '#a855f7', '#22c55e',
    ]);

    // Deterministic sub-color based on block position (stable across frames)
    function getSubColor(bx, by, bz, subIdx) {
        const hash = (bx * 73 + by * 137 + bz * 211 + subIdx * 53) & 0xFFFF;
        return SUB_COLORS[hash % SUB_COLORS.length];
    }

    // Interpolate between two 2D points at fraction t
    function lerpPt(a, b, t) {
        return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
    }

    // Draw a sub-quad (one quarter of a face) given 4 corner points
    function drawSubQuad(corners, fillColor, strokeColor, lineW) {
        ctx.beginPath();
        ctx.moveTo(corners[0].x, corners[0].y);
        ctx.lineTo(corners[1].x, corners[1].y);
        ctx.lineTo(corners[2].x, corners[2].y);
        ctx.lineTo(corners[3].x, corners[3].y);
        ctx.closePath();
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineW;
        ctx.stroke();
    }

    function drawCubelet(x, y, z, ox, oy, s, color, alpha = 1) {
        const p1 = isoProject(x, y, z, ox, oy, s);
        const p2 = isoProject(x + 1, y, z, ox, oy, s);
        const p3 = isoProject(x + 1, y + 1, z, ox, oy, s);
        const p4 = isoProject(x, y + 1, z, ox, oy, s);
        const p5 = isoProject(x, y, z + 1, ox, oy, s);
        const p6 = isoProject(x + 1, y, z + 1, ox, oy, s);
        const p7 = isoProject(x + 1, y + 1, z + 1, ox, oy, s);
        const p8 = isoProject(x, y + 1, z + 1, ox, oy, s);

        ctx.globalAlpha = alpha;

        // For ghost/scaffold blocks (low alpha), draw simple solid faces
        if (alpha < 0.3) {
            // Simple 3-face draw for ghosts (no sub-blocks)
            ctx.beginPath();
            ctx.moveTo(p5.x, p5.y); ctx.lineTo(p6.x, p6.y);
            ctx.lineTo(p7.x, p7.y); ctx.lineTo(p8.x, p8.y);
            ctx.closePath();
            ctx.fillStyle = color; ctx.fill();

            ctx.beginPath();
            ctx.moveTo(p4.x, p4.y); ctx.lineTo(p8.x, p8.y);
            ctx.lineTo(p7.x, p7.y); ctx.lineTo(p3.x, p3.y);
            ctx.closePath();
            ctx.fillStyle = shadeColor(color, -20); ctx.fill();

            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y); ctx.lineTo(p5.x, p5.y);
            ctx.lineTo(p8.x, p8.y); ctx.lineTo(p4.x, p4.y);
            ctx.closePath();
            ctx.fillStyle = shadeColor(color, -40); ctx.fill();

            ctx.globalAlpha = 1;
            return;
        }

        // === SOLID BLOCKS: 2x2 sub-block grid on each face ===
        // Recover integer block coords from the offset coordinates
        const size = CONFIG.targetSize;
        const offset = size / 2;
        const zOff = size / 2;
        const bx = Math.round(x + offset);
        const by = Math.round(y + offset);
        const bz = Math.round(z + zOff);

        const edgeColor = 'rgba(0, 0, 0, 0.5)';
        const edgeW = 1;

        // --- TOP FACE (2x2 grid): p5, p6, p7, p8 ---
        const t5_6 = lerpPt(p5, p6, 0.5);
        const t8_7 = lerpPt(p8, p7, 0.5);
        const t5_8 = lerpPt(p5, p8, 0.5);
        const t6_7 = lerpPt(p6, p7, 0.5);
        const tCenter = lerpPt(t5_8, t6_7, 0.5);

        drawSubQuad([p5, t5_6, tCenter, t5_8],     getSubColor(bx, by, bz, 0), edgeColor, edgeW);
        drawSubQuad([t5_6, p6, t6_7, tCenter],     getSubColor(bx, by, bz, 1), edgeColor, edgeW);
        drawSubQuad([t5_8, tCenter, t8_7, p8],     getSubColor(bx, by, bz, 2), edgeColor, edgeW);
        drawSubQuad([tCenter, t6_7, p7, t8_7],     getSubColor(bx, by, bz, 3), edgeColor, edgeW);

        // Highlight on top face - subtle white overlay for depth
        ctx.beginPath();
        ctx.moveTo(p5.x, p5.y); ctx.lineTo(p6.x, p6.y);
        ctx.lineTo(p7.x, p7.y); ctx.lineTo(p8.x, p8.y);
        ctx.closePath();
        ctx.fillStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.fill();

        // --- LEFT FACE (2x2 grid): p4, p8, p7, p3 ---
        const l4_8 = lerpPt(p4, p8, 0.5);
        const l3_7 = lerpPt(p3, p7, 0.5);
        const l4_3 = lerpPt(p4, p3, 0.5);
        const l8_7 = lerpPt(p8, p7, 0.5);
        const lCenter = lerpPt(l4_3, l8_7, 0.5);

        drawSubQuad([p4, l4_8, lCenter, l4_3],     shadeColor(getSubColor(bx, by, bz, 4), -15), edgeColor, edgeW);
        drawSubQuad([l4_8, p8, l8_7, lCenter],     shadeColor(getSubColor(bx, by, bz, 5), -15), edgeColor, edgeW);
        drawSubQuad([l4_3, lCenter, l3_7, p3],     shadeColor(getSubColor(bx, by, bz, 6), -15), edgeColor, edgeW);
        drawSubQuad([lCenter, l8_7, p7, l3_7],     shadeColor(getSubColor(bx, by, bz, 7), -15), edgeColor, edgeW);

        // --- RIGHT FACE (2x2 grid): p1, p5, p8, p4 ---
        const r1_5 = lerpPt(p1, p5, 0.5);
        const r4_8 = lerpPt(p4, p8, 0.5);
        const r1_4 = lerpPt(p1, p4, 0.5);
        const r5_8 = lerpPt(p5, p8, 0.5);
        const rCenter = lerpPt(r1_4, r5_8, 0.5);

        drawSubQuad([p1, r1_5, rCenter, r1_4],     shadeColor(getSubColor(bx, by, bz, 8), -30), edgeColor, edgeW);
        drawSubQuad([r1_5, p5, r5_8, rCenter],     shadeColor(getSubColor(bx, by, bz, 9), -30), edgeColor, edgeW);
        drawSubQuad([r1_4, rCenter, r4_8, p4],     shadeColor(getSubColor(bx, by, bz, 10), -30), edgeColor, edgeW);
        drawSubQuad([rCenter, r5_8, p8, r4_8],     shadeColor(getSubColor(bx, by, bz, 11), -30), edgeColor, edgeW);

        // Outer edge highlight (block border)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
        ctx.lineWidth = 1;
        // Top face border
        ctx.beginPath();
        ctx.moveTo(p5.x, p5.y); ctx.lineTo(p6.x, p6.y);
        ctx.lineTo(p7.x, p7.y); ctx.lineTo(p8.x, p8.y);
        ctx.closePath(); ctx.stroke();
        // Left face border
        ctx.beginPath();
        ctx.moveTo(p4.x, p4.y); ctx.lineTo(p8.x, p8.y);
        ctx.lineTo(p7.x, p7.y); ctx.lineTo(p3.x, p3.y);
        ctx.closePath(); ctx.stroke();
        // Right face border
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y); ctx.lineTo(p5.x, p5.y);
        ctx.lineTo(p8.x, p8.y); ctx.lineTo(p4.x, p4.y);
        ctx.closePath(); ctx.stroke();

        ctx.globalAlpha = 1;
    }

    function drawWireframeCube(ox, oy, size, scale, alpha) {
        ctx.strokeStyle = `rgba(124, 92, 252, ${alpha})`;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);

        const offset = size / 2;
        const zOffset = size / 2;  // Center Z for rotation
        const corners = [];

        for (let x = 0; x <= 1; x++) {
            for (let y = 0; y <= 1; y++) {
                for (let z = 0; z <= 1; z++) {
                    corners.push(isoProject(
                        x * size - offset,
                        y * size - offset,
                        z * size - zOffset,
                        ox, oy, scale
                    ));
                }
            }
        }

        const edges = [
            [0, 1], [0, 2], [1, 3], [2, 3],
            [4, 5], [4, 6], [5, 7], [6, 7],
            [0, 4], [1, 5], [2, 6], [3, 7],
        ];

        edges.forEach(([a, b]) => {
            ctx.beginPath();
            ctx.moveTo(corners[a].x, corners[a].y);
            ctx.lineTo(corners[b].x, corners[b].y);
            ctx.stroke();
        });

        ctx.setLineDash([]);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // AGENT MANAGEMENT
    // ═══════════════════════════════════════════════════════════════════════
    function spawnAgent(type = 'builder', status = 'building...') {
        const angle = Math.random() * Math.PI * 2;
        const dist = 150 + Math.random() * 100;
        const sx = w / 2 + Math.cos(angle) * dist;
        const sy = h * 0.45 + Math.sin(angle) * dist * 0.5;
        const behavior = pickBehavior();

        // Founders are 10% bigger - they're the idea origin
        const baseSize = type === 'founder'
            ? FEATURES.maxAgentSize * 1.1
            : FEATURES.maxAgentSize;
        const agent = {
            id: 'agent_' + Math.random().toString(36).substr(2, 6),
            sx, sy,
            x: sx, y: sy,
            tx: w / 2 + (Math.random() - 0.5) * 60,
            ty: h * 0.45 + (Math.random() - 0.5) * 40,
            progress: 0,
            speed: (0.003 + Math.random() * 0.003) * BEHAVIORS[behavior].speedMod,
            size: baseSize,
            startSize: baseSize,       // Immutable — never let size exceed this
            type,
            status,
            color: STYLE.agentColors[type] || STYLE.agentColors.builder,
            baseColor: STYLE.agentColors[type] || STYLE.agentColors.builder,
            trail: [],
            showLabel: true,
            behavior,
            fiEarned: 0,
            level: 'P4',
            isSpazzing: false,
            spazTimer: 0,
            recruitCount: 0,
            celebrateTimer: 0,
            // Gold return cycle: working -> returning -> entering
            state: 'entering',      // entering | working | returning
            goldCarried: 0,         // Tokens being carried off-screen
            tripCount: 0,           // Number of completed return trips
            exitAngle: angle,       // Direction to exit screen
        };

        agents.push(agent);
        emitEvent('agent_spawned', { agent: agent.id, type, status });
        return agent;
    }

    function spawnAgentNear(nearX, nearY, type, status) {
        const angle = Math.random() * Math.PI * 2;
        const dist = 30 + Math.random() * 20;
        const sx = nearX + Math.cos(angle) * dist;
        const sy = nearY + Math.sin(angle) * dist;
        const behavior = pickBehavior();

        const exitAngle = Math.random() * Math.PI * 2;
        const agent = {
            id: 'agent_' + Math.random().toString(36).substr(2, 6),
            sx, sy,
            x: sx, y: sy,
            tx: w / 2 + (Math.random() - 0.5) * 60,
            ty: h * 0.45 + (Math.random() - 0.5) * 40,
            progress: 0,
            speed: (0.003 + Math.random() * 0.003) * BEHAVIORS[behavior].speedMod,
            size: 6,
            startSize: 6,
            type,
            status,
            color: STYLE.agentColors[type] || STYLE.agentColors.builder,
            baseColor: STYLE.agentColors[type] || STYLE.agentColors.builder,
            trail: [],
            showLabel: true,
            behavior,
            fiEarned: 0,
            level: 'P4',
            isSpazzing: false,
            spazTimer: 0,
            recruitCount: 0,
            celebrateTimer: 0,
            // Gold return cycle
            state: 'entering',
            goldCarried: 0,
            tripCount: 0,
            exitAngle,
        };

        agents.push(agent);
        emitEvent('agent_recruited', { agent: agent.id, type });
        return agent;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // MOUSE CLICK ON AGENT - Promote/upgrade with celebration!
    // ═══════════════════════════════════════════════════════════════════════
    function handleAgentClick(mx, my) {
        // Find clicked agent
        // Transform agent positions to screen space for hit detection
        const scaleRatio = camera.scale / STYLE.camera.defaultScale;
        const isPixelMode = scaleRatio < 0.7;
        const cubeCenter = { x: w / 2, y: h * 0.45 };
        // Binary hit radius: 20px in regular mode, 10px in pixel mode
        const hitRadius = isPixelMode ? 10 : 20;

        const clickedAgent = agents.find(a => {
            const relX = a.x - cubeCenter.x;
            const relY = a.y - cubeCenter.y;
            const drawX = cubeCenter.x + relX * scaleRatio;
            const drawY = cubeCenter.y + relY * scaleRatio;
            const dx = drawX - mx;
            const dy = drawY - my;
            return Math.sqrt(dx * dx + dy * dy) < hitRadius;
        });

        if (!clickedAgent) {
            // Clicked empty space — dismiss tooltip
            selectedAgent = null;
            return;
        }

        // Toggle selection: click same agent = deselect, different = select
        if (selectedAgent === clickedAgent) {
            selectedAgent = null;
            return;
        }
        selectedAgent = clickedAgent;
        selectedAgentTime = Date.now();

        const now = Date.now();

        // Reset easter egg counter if timeout
        if (now - easterEgg.lastClickTime > easterEgg.clickTimeout) {
            easterEgg.promoterClicks = 0;
        }
        easterEgg.lastClickTime = now;

        // Different behavior based on agent type
        if (clickedAgent.type === 'builder') {
            // Builder → Promoter with celebration dance!
            clickedAgent.type = 'promoter';
            clickedAgent.color = STYLE.agentColors.promoter;
            clickedAgent.baseColor = STYLE.agentColors.promoter;
            clickedAgent.status = 'promoted!';
            clickedAgent.isSpazzing = true;
            clickedAgent.spazTimer = 120;  // Excited dance!
            clickedAgent.celebrateTimer = 60;
            emitEvent('promoter_assigned', { agent: clickedAgent.id });
            addTickerMessage('promoter_assigned', { actor_id: clickedAgent.id });

        } else if (clickedAgent.type === 'promoter') {
            // Easter egg: Click 3 promoters → staker!
            easterEgg.promoterClicks++;
            clickedAgent.isSpazzing = true;
            clickedAgent.spazTimer = 60;

            if (easterEgg.promoterClicks >= 3) {
                // GOLD RUSH! Promoter → Staker (BTC liquidity provider)
                clickedAgent.type = 'staker';
                clickedAgent.color = STYLE.agentColors.staker;
                clickedAgent.baseColor = STYLE.agentColors.staker;
                clickedAgent.status = 'staking!';
                clickedAgent.celebrateTimer = 120;
                clickedAgent.size = Math.min(clickedAgent.startSize * 1.3, FEATURES.maxAgentSize * 1.5);
                easterEgg.promoterClicks = 0;
                emitEvent('staker_arrived', { agent: clickedAgent.id, source: 'easter_egg' });
                addTickerMessage('staker_arrived', { agent: clickedAgent.id });
                // Spawn confetti for the gold rush!
                spawnConfetti();
            }
        } else if (clickedAgent.type === 'founder') {
            // Founder gets excited but stays founder
            clickedAgent.isSpazzing = true;
            clickedAgent.spazTimer = 90;
            clickedAgent.status = 'visionary!';
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // AGENT INFO TOOLTIP — mini card near selected agent
    // ═══════════════════════════════════════════════════════════════════════
    function drawAgentTooltip() {
        if (!selectedAgent) return;

        // Auto-dismiss after 8 seconds
        if (Date.now() - selectedAgentTime > 8000) {
            selectedAgent = null;
            return;
        }

        // Check agent still exists
        if (!agents.includes(selectedAgent)) {
            selectedAgent = null;
            return;
        }

        const a = selectedAgent;
        const scaleRatio = camera.scale / STYLE.camera.defaultScale;
        const cubeCenter = { x: w / 2, y: h * 0.45 };
        const relX = a.x - cubeCenter.x;
        const relY = a.y - cubeCenter.y;
        const drawX = cubeCenter.x + relX * scaleRatio;
        const drawY = cubeCenter.y + relY * scaleRatio;

        // Tooltip card dimensions
        const cardW = 150;
        const cardH = 80;
        const icons = { founder: '★', builder: '$', promoter: '↗', staker: '₿' };
        const typeNames = { founder: 'Founder', builder: 'Builder', promoter: 'Promoter', staker: 'Staker' };

        // Position: above and to the right of agent, clamped to canvas
        let cardX = drawX + 12;
        let cardY = drawY - cardH - 8;
        if (cardX + cardW > w - 10) cardX = drawX - cardW - 12;
        if (cardY < 10) cardY = drawY + 16;

        ctx.save();

        // Semi-transparent dark background with rounded corners
        ctx.fillStyle = 'rgba(15, 15, 40, 0.92)';
        ctx.strokeStyle = 'rgba(124, 92, 252, 0.6)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        const r = 6;
        ctx.moveTo(cardX + r, cardY);
        ctx.lineTo(cardX + cardW - r, cardY);
        ctx.quadraticCurveTo(cardX + cardW, cardY, cardX + cardW, cardY + r);
        ctx.lineTo(cardX + cardW, cardY + cardH - r);
        ctx.quadraticCurveTo(cardX + cardW, cardY + cardH, cardX + cardW - r, cardY + cardH);
        ctx.lineTo(cardX + r, cardY + cardH);
        ctx.quadraticCurveTo(cardX, cardY + cardH, cardX, cardY + cardH - r);
        ctx.lineTo(cardX, cardY + r);
        ctx.quadraticCurveTo(cardX, cardY, cardX + r, cardY);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Agent type + icon
        const icon = icons[a.type] || '?';
        const typeName = typeNames[a.type] || a.type;
        ctx.font = 'bold 12px monospace';
        ctx.fillStyle = a.color;
        ctx.textAlign = 'left';
        ctx.fillText(`${icon} ${typeName}`, cardX + 10, cardY + 18);

        // Agent ID (short)
        ctx.font = '9px monospace';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.fillText(a.id, cardX + 10, cardY + 30);

        // Status
        ctx.font = '10px monospace';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.fillText(`Status: ${a.status}`, cardX + 10, cardY + 46);

        // F_i earned + trips
        ctx.fillStyle = 'rgba(0, 255, 136, 0.9)';
        ctx.fillText(`Fᵢ: ${a.fiEarned.toLocaleString()}`, cardX + 10, cardY + 60);

        if (a.tripCount > 0) {
            ctx.fillStyle = 'rgba(255, 215, 0, 0.8)';
            ctx.fillText(`Trips: ${a.tripCount}`, cardX + 85, cardY + 60);
        }

        // State indicator (for gold-return cycle)
        if (a.state) {
            const stateColors = { entering: '#00e5d0', working: '#00ff88', returning: '#ffd700' };
            ctx.fillStyle = stateColors[a.state] || '#fff';
            ctx.fillText(`[${a.state}]`, cardX + 85, cardY + 46);
        }

        ctx.textAlign = 'center';  // Restore default
        ctx.restore();
    }

    function updateAgentBehaviors() {
        agents.forEach(a => {
            // Spaz out behavior
            if (!a.isSpazzing && (a.behavior === 'chaotic' || a.type === 'promoter')) {
                if (Math.random() < QUIRKS.spazOut) {
                    if (!FEATURES.enableSpazzing) return;
                    a.isSpazzing = true;
                    a.spazTimer = 60 + Math.random() * 60;
                    a.status = a.type === 'promoter' ? 'promoting...' : 'focused...';  // 0102 zen state
                    a.color = shadeColor(a.baseColor, 40); // Brighten
                    emitEvent('agent_spazzing', { agent: a.id });
                }
            }

            if (a.isSpazzing) {
                a.spazTimer--;
                a.x += (Math.random() - 0.5) * 8;
                a.y += (Math.random() - 0.5) * 8;
                a.x = Math.max(20, Math.min(w - 20, a.x));
                a.y = Math.max(20, Math.min(h - 20, a.y));

                if (a.spazTimer <= 0) {
                    a.isSpazzing = false;
                    a.status = a.type === 'promoter' ? 'promoting...' : 'building...';

                    // Promoter returns with recruits
                    if (a.type === 'promoter' && Math.random() < QUIRKS.recruit) {
                        const recruits = 1 + Math.floor(Math.random() * 3);
                        a.recruitCount += recruits;
                        a.status = `recruited ${recruits}!`;
                        emitEvent('promoter_recruited', { count: recruits });
                        for (let i = 0; i < recruits; i++) {
                            setTimeout(() => spawnAgentNear(a.x, a.y, 'builder', 'joining...'), i * 200);
                        }
                    }
                }
            }

            // Random celebration — color shift only (gated by FEATURES)
            if (FEATURES.enableCelebrations && !a.isSpazzing && Math.random() < QUIRKS.celebrate) {
                a.celebrateTimer = 20;
            }

            // Update celebrate timer and color
            if (a.celebrateTimer > 0) {
                a.celebrateTimer--;
                a.color = '#ffd700'; // Gold tint during celebration
            } else if (!a.isSpazzing) {
                a.color = a.baseColor; // Restore base color
            }

            // HARD SIZE CAP — never exceed maxAgentSize or startSize
            a.size = Math.min(a.size, a.startSize, FEATURES.maxAgentSize);
        });
    }

    function updateAgents() {
        const cubeCenter = { x: w / 2, y: h * 0.45 };

        for (let i = agents.length - 1; i >= 0; i--) {
            const a = agents[i];
            if (a.isSpazzing) continue; // Skip normal movement when spazzing

            a.progress += a.speed;

            // State machine for gold return cycle
            if (FEATURES.enableGoldReturn && a.type === 'builder') {
                switch (a.state) {
                    case 'entering':
                        // Moving toward cube from off-screen
                        if (a.progress >= 1) {
                            a.progress = 0;
                            a.state = 'working';
                            a.sx = a.x;
                            a.sy = a.y;

                            // Claim a block to build - navigate TO the block
                            if (currentPhase === 'BUILDING') {
                                const claimed = claimNextBlock();
                                if (claimed) {
                                    a.targetBlock = claimed;
                                    a.tx = claimed.screenX;
                                    a.ty = claimed.screenY;
                                    a.status = 'coding...';
                                } else {
                                    a.tx = cubeCenter.x + (Math.random() - 0.5) * 60;
                                    a.ty = cubeCenter.y + (Math.random() - 0.5) * 40;
                                    a.status = 'reviewing...';
                                }
                            } else {
                                a.tx = cubeCenter.x + (Math.random() - 0.5) * 60;
                                a.ty = cubeCenter.y + (Math.random() - 0.5) * 40;
                                a.status = 'planning...';
                            }
                        }
                        break;

                    case 'working':
                        // Agent arrives at block position → fills it → claims next
                        if (a.progress >= 1) {
                            a.progress = 0;
                            a.fiEarned += CONFIG.fiPerBlock;

                            // Fill the block the agent just arrived at
                            if (currentPhase === 'BUILDING' && a.targetBlock) {
                                const tb = a.targetBlock;
                                const key = `${tb.x},${tb.y},${tb.z}`;
                                if (!filledBlocks.has(key)) {
                                    filledBlocks.add(key);
                                    fiEarned += CONFIG.fiPerBlock;
                                    spawnBlockParticles(tb.x, tb.y, tb.z);
                                    emitEvent('block_filled', { x: tb.x, y: tb.y, z: tb.z, total: filledBlocks.size });
                                }
                                a.targetBlock = null;
                            }

                            // 15% chance agent leaves to return gold
                            if (Math.random() < 0.15) {
                                a.state = 'returning';
                                a.status = 'delivering...';
                                a.sx = a.x;
                                a.sy = a.y;
                                const exitDist = Math.max(w, h) * 0.7;
                                a.tx = cubeCenter.x + Math.cos(a.exitAngle) * exitDist;
                                a.ty = cubeCenter.y + Math.sin(a.exitAngle) * exitDist * 0.5;
                            } else {
                                // Claim next block and navigate to it
                                a.sx = a.x;
                                a.sy = a.y;
                                if (currentPhase === 'BUILDING') {
                                    const claimed = claimNextBlock();
                                    if (claimed) {
                                        a.targetBlock = claimed;
                                        a.tx = claimed.screenX;
                                        a.ty = claimed.screenY;
                                        a.status = 'coding...';
                                    } else {
                                        // All blocks claimed - wander near cube
                                        const angle = Math.random() * Math.PI * 2;
                                        const dist = 20 + Math.random() * 30;
                                        a.tx = cubeCenter.x + Math.cos(angle) * dist;
                                        a.ty = cubeCenter.y + Math.sin(angle) * dist * 0.5;
                                        a.status = 'reviewing...';
                                    }
                                } else {
                                    const angle = Math.random() * Math.PI * 2;
                                    const dist = 30 + Math.random() * 40;
                                    a.tx = cubeCenter.x + Math.cos(angle) * dist;
                                    a.ty = cubeCenter.y + Math.sin(angle) * dist * 0.5;
                                    a.status = 'planning...';
                                }
                            }
                        }
                        break;

                    case 'returning':
                        // Moving off-screen with gold
                        if (a.progress >= 1) {
                            a.progress = 0;
                            a.tripCount++;
                            a.goldCarried = 0;  // Deposited gold
                            a.state = 'entering';
                            a.status = 'returning...';
                            // New entry angle (opposite side)
                            a.exitAngle = Math.random() * Math.PI * 2;
                            const entryDist = Math.max(w, h) * 0.6;
                            a.sx = cubeCenter.x + Math.cos(a.exitAngle + Math.PI) * entryDist;
                            a.sy = cubeCenter.y + Math.sin(a.exitAngle + Math.PI) * entryDist * 0.5;
                            a.x = a.sx;
                            a.y = a.sy;
                            a.tx = cubeCenter.x + (Math.random() - 0.5) * 80;
                            a.ty = cubeCenter.y + (Math.random() - 0.5) * 60;
                        }
                        break;
                }
            } else {
                // Non-builder or gold return disabled - original behavior
                if (a.progress >= 1) {
                    a.progress = 0;
                    const angle = Math.random() * Math.PI * 2;
                    const dist = 30 + Math.random() * 40;
                    a.sx = a.x;
                    a.sy = a.y;
                    a.tx = cubeCenter.x + Math.cos(angle) * dist;
                    a.ty = cubeCenter.y + Math.sin(angle) * dist * 0.5;

                    if (currentPhase === 'BUILDING' && a.type === 'builder') {
                        fillRandomBlock();
                    }
                }
            }

            const t = STYLE.easing.quadInOut(a.progress);
            a.x = a.sx + (a.tx - a.sx) * t;
            a.y = a.sy + (a.ty - a.sy) * t;

            // Mouse attraction: agents gently orbit toward cursor
            if (mouse.isOverCanvas && !mouse.isDragging) {
                const dx = mouse.x - a.x;
                const dy = mouse.y - a.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 200 && dist > 20) {  // Within attraction range but not too close
                    const strength = 0.02 * (1 - dist / 200);  // Closer = stronger
                    a.x += dx * strength;
                    a.y += dy * strength;
                }
            }

            if (a.type === 'staker') {
                a.trail.push({ x: a.x, y: a.y });
                if (a.trail.length > STYLE.particles.trailLength) a.trail.shift();
            }
        }
    }

    function drawAgents() {
        // Calculate global agent alpha for fade transitions
        // During CELEBRATE: agents fade out first (0-2000ms), then stay hidden
        let agentAlpha = 1;
        if (currentPhase === 'CELEBRATE') {
            const elapsed = getScaledElapsed(phaseStartTime);
            agentAlpha = Math.max(0, 1 - elapsed / 2000);  // Fade over 2 seconds
        } else if (currentPhase === 'RESET') {
            agentAlpha = 0;  // Agents fully hidden during reset
        } else if (currentPhase === 'IDEA') {
            const elapsed = getScaledElapsed(phaseStartTime);
            agentAlpha = Math.min(1, elapsed / 1000);  // Fade in new founder
        }

        // BINARY agent mode: regular OR pixel (no gradual scaling)
        const scaleRatio = camera.scale / STYLE.camera.defaultScale;
        const isPixelMode = scaleRatio < 0.7;  // Below 70% zoom = pixel mode
        const cubeCenter = { x: w / 2, y: h * 0.45 };

        // Track label positions for collision avoidance
        const labelPositions = [];

        agents.forEach(a => {
            ctx.save();
            ctx.globalAlpha = agentAlpha;

            // Transform agent position relative to cube center based on zoom
            const relX = a.x - cubeCenter.x;
            const relY = a.y - cubeCenter.y;
            const drawX = cubeCenter.x + relX * scaleRatio;
            const drawY = cubeCenter.y + relY * scaleRatio;

            // BINARY SIZE: regular (6-8px) or pixel (2px)
            const drawSize = isPixelMode ? 2 : a.size;

            // Draw trail for stakers (skip in pixel mode)
            if (!isPixelMode && a.type === 'staker' && a.trail.length > 0) {
                for (let i = 0; i < a.trail.length; i++) {
                    const t = a.trail[i];
                    const tRelX = t.x - cubeCenter.x;
                    const tRelY = t.y - cubeCenter.y;
                    const tDrawX = cubeCenter.x + tRelX * scaleRatio;
                    const tDrawY = cubeCenter.y + tRelY * scaleRatio;
                    const alpha = (i / a.trail.length) * 0.5 * agentAlpha;
                    ctx.beginPath();
                    ctx.arc(tDrawX, tDrawY, 3, 0, Math.PI * 2);
                    ctx.fillStyle = `rgba(255, 215, 0, ${alpha})`;
                    ctx.fill();
                }
            }

            // PIXEL MODE: just colored dots, no gradients or icons
            if (isPixelMode) {
                // Bitcoin orange for builders, agent color for others
                if (a.type === 'builder') {
                    const blinkCycle = (Date.now() / 800) + (a.x * 0.1);
                    const orangePhase = (Math.sin(blinkCycle) + 1) / 2;
                    const r = 255;
                    const g = Math.floor(45 + orangePhase * 102);
                    ctx.fillStyle = `rgb(${r}, ${g}, 30)`;
                } else {
                    ctx.fillStyle = a.color;
                }
                ctx.beginPath();
                ctx.arc(drawX, drawY, drawSize, 0, Math.PI * 2);
                ctx.fill();
                ctx.restore();
                return;  // Skip rest of agent drawing in pixel mode
            }

            // REGULAR MODE: full agent rendering with gradients and icons
            ctx.beginPath();
            ctx.arc(drawX, drawY, drawSize, 0, Math.PI * 2);
            const grd = ctx.createRadialGradient(drawX, drawY, 0, drawX, drawY, drawSize);
            grd.addColorStop(0, a.color);
            grd.addColorStop(1, shadeColor(a.color, -30));
            ctx.fillStyle = grd;
            ctx.fill();

            // Glow effect — gated by FEATURES restrictor
            if (FEATURES.enableAgentGlow) {
                ctx.shadowColor = a.color;
                ctx.shadowBlur = a.isSpazzing ? 8 : 4;
                ctx.fill();
                ctx.shadowBlur = 0;
            }

            // Icon based on type - builders blink $ to show EARN-ing
            const baseFontSize = 6;  // Fixed size in regular mode
            ctx.font = `bold ${baseFontSize}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const icons = { founder: '★', builder: '$', promoter: '↗', staker: '₿', idle: '○' };

            // IDLE agents: slow pulse with dimmed color, awaiting ORCH handoff
            if (a.status === 'IDLE' || a.status === 'idle') {
                const idleCycle = (Date.now() / 1200) + (a.x * 0.05);  // Slow pulse
                const idleAlpha = 0.3 + 0.4 * Math.sin(idleCycle);  // 0.3 to 0.7 (dimmed)
                const pulseSize = 1 + 0.15 * Math.sin(idleCycle);  // Size pulse

                ctx.fillStyle = `rgba(102, 102, 136, ${idleAlpha})`;  // Dim purple-gray
                ctx.font = `${Math.floor(12 * pulseSize)}px monospace`;
                ctx.fillText('○', drawX, drawY);  // Circle for idle
            }
            // Builders: slow blink $ with Bitcoin orange gradient (red→orange)
            else if (a.type === 'builder') {
                const blinkCycle = (Date.now() / 800) + (a.x * 0.1);  // Offset per agent
                let blinkAlpha = 0.6 + 0.4 * Math.sin(blinkCycle);  // 0.6 to 1.0

                // Check for earning pulse (from SSE event)
                if (a.earningPulse) {
                    const pulseAge = Date.now() - a.earningPulse;
                    if (pulseAge < 2000) {
                        // Intense gold pulse for 2 seconds
                        const intensity = 1 - (pulseAge / 2000);
                        blinkAlpha = 1.0;
                        // Gold flash that fades back to white
                        const gold = Math.floor(215 * intensity);
                        ctx.fillStyle = `rgba(255, ${255 - gold * 0.4}, ${gold * 0.7}, 1)`;
                        // Scale up the $ during pulse
                        ctx.font = `bold ${14 + 4 * intensity}px monospace`;
                    } else {
                        // Clear the pulse after 2s
                        delete a.earningPulse;
                        // Bitcoin orange gradient: red (#ff2d2d) to orange (#f7931a)
                        const orangePhase = (Math.sin(blinkCycle) + 1) / 2;  // 0-1
                        const r = 255;
                        const g = Math.floor(45 + orangePhase * 102);  // 45 to 147
                        const b = Math.floor(45 - orangePhase * 19);   // 45 to 26
                        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${blinkAlpha})`;
                    }
                } else {
                    // Bitcoin orange gradient: red (#ff2d2d) to orange (#f7931a)
                    const orangePhase = (Math.sin(blinkCycle) + 1) / 2;  // 0-1
                    const r = 255;
                    const g = Math.floor(45 + orangePhase * 102);  // 45 to 147
                    const b = Math.floor(45 - orangePhase * 19);   // 45 to 26
                    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${blinkAlpha})`;
                }
                ctx.fillText(icons[a.type] || '$', drawX, drawY);
            } else {
                ctx.fillStyle = '#fff';
                ctx.fillText(icons[a.type] || '$', drawX, drawY);
            }
            // Reset font after potential pulse scaling
            ctx.font = `bold ${baseFontSize}px sans-serif`;

            // Status label - deconflicted to prevent stacking
            if (a.showLabel && labelPositions.length < 4) {
                const labelX = drawX;
                let labelY = drawY + drawSize + 12;

                // Bump label down if colliding with existing labels
                for (const existing of labelPositions) {
                    const dx = Math.abs(labelX - existing.x);
                    const dy = Math.abs(labelY - existing.y);
                    if (dx < 60 && dy < 12) {
                        labelY = existing.y + 14; // Bump below
                    }
                }

                // Only show labels for agents within 100px of cube center
                const distToCenter = Math.sqrt(
                    Math.pow(drawX - cubeCenter.x, 2) +
                    Math.pow(drawY - cubeCenter.y, 2)
                );
                if (distToCenter < 100) {
                    ctx.font = '10px monospace';
                    ctx.fillStyle = `rgba(255,255,255,${0.25 * agentAlpha})`;
                    ctx.fillText(a.status, labelX, labelY);
                    labelPositions.push({ x: labelX, y: labelY });
                }
            }

            // Hover highlight: subtle scale pulse when mouse is near
            if (mouse.hoveredAgent === a) {
                ctx.beginPath();
                ctx.arc(drawX, drawY, drawSize + 4, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(255, 255, 255, ${0.4 * agentAlpha})`;
                ctx.lineWidth = 1.5;
                ctx.stroke();
            }

            // Selected agent: bright ring
            if (selectedAgent === a) {
                ctx.beginPath();
                ctx.arc(drawX, drawY, drawSize + 6, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(0, 229, 208, ${0.8 * agentAlpha})`;
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            ctx.restore();
        });
    }

    // ═══════════════════════════════════════════════════════════════════════
    // JIGSAW FILL SEQUENCE
    // Pre-computed fill order: foundation first, scattered pieces, gaps close
    // ═══════════════════════════════════════════════════════════════════════
    let jigsawSequence = [];
    let jigsawIndex = 0;

    function generateJigsawSequence(size) {
        // Create all block positions with priority scores
        const blocks = [];
        for (let z = 0; z < size; z++) {
            for (let y = 0; y < size; y++) {
                for (let x = 0; x < size; x++) {
                    // Priority: bottom-center blocks first (P0), top-edge last (P4)
                    const centerDist = Math.abs(x - size / 2 + 0.5) + Math.abs(y - size / 2 + 0.5);
                    const layerImportance = z / (size - 1);
                    const centerImportance = 1 - (centerDist / size);
                    const importance = (1 - layerImportance) * 0.6 + centerImportance * 0.4;

                    // Group into "pieces" (2-3 adjacent blocks)
                    // Piece ID based on 2x2 grid sections per layer
                    const pieceX = Math.floor(x / 2);
                    const pieceY = Math.floor(y / 2);
                    const pieceId = z * 4 + pieceY * 2 + pieceX;

                    blocks.push({ x, y, z, importance, pieceId });
                }
            }
        }

        // Sort by piece groups, but scatter pieces across priority tiers
        // This creates the jigsaw effect: pieces from different areas fill simultaneously
        const pieces = {};
        blocks.forEach(b => {
            if (!pieces[b.pieceId]) pieces[b.pieceId] = [];
            pieces[b.pieceId].push(b);
        });

        // Order pieces by average importance (foundation pieces first)
        const pieceOrder = Object.entries(pieces)
            .map(([id, pBlocks]) => ({
                id: parseInt(id),
                blocks: pBlocks,
                avgImportance: pBlocks.reduce((sum, b) => sum + b.importance, 0) / pBlocks.length,
            }))
            .sort((a, b) => b.avgImportance - a.avgImportance);

        // Interleave: take one block from high-priority piece, then one from mid, then low
        // This creates scattered fill with foundation bias
        const sequence = [];
        const pieceQueues = pieceOrder.map(p => [...p.blocks]);

        // Round-robin through pieces, highest priority first
        while (pieceQueues.some(q => q.length > 0)) {
            for (const queue of pieceQueues) {
                if (queue.length > 0) {
                    sequence.push(queue.shift());
                }
            }
        }

        return sequence;
    }

    function resetJigsawSequence() {
        jigsawSequence = generateJigsawSequence(CONFIG.targetSize);
        jigsawIndex = 0;
    }

    // Claim next unfilled block from jigsaw sequence
    // Returns {x, y, z, screenX, screenY} or null if exhausted
    function claimNextBlock() {
        const size = CONFIG.targetSize;
        while (jigsawIndex < jigsawSequence.length) {
            const block = jigsawSequence[jigsawIndex];
            jigsawIndex++;
            const key = `${block.x},${block.y},${block.z}`;
            if (!filledBlocks.has(key)) {
                // Calculate screen position of this block
                const cx = w / 2, cy = h * 0.45;
                const scale = camera.scale;
                const offset = size / 2;
                const zOffset = size / 2;
                const pos = isoProject(
                    block.x - offset + 0.5,
                    block.y - offset + 0.5,
                    block.z + 0.5 - zOffset,
                    cx, cy, scale
                );
                return { x: block.x, y: block.y, z: block.z, screenX: pos.x, screenY: pos.y };
            }
        }
        return null;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // BLOCK FILLING
    // ═══════════════════════════════════════════════════════════════════════
    function fillRandomBlock() {
        const size = CONFIG.targetSize;
        let x, y, z, key;

        // Jigsaw sequence: use pre-computed order when available
        if (jigsawSequence.length > 0 && jigsawIndex < jigsawSequence.length) {
            // Find next unfilled block in jigsaw sequence
            while (jigsawIndex < jigsawSequence.length) {
                const block = jigsawSequence[jigsawIndex];
                jigsawIndex++;
                key = `${block.x},${block.y},${block.z}`;
                if (!filledBlocks.has(key)) {
                    x = block.x;
                    y = block.y;
                    z = block.z;
                    break;
                }
            }
            // If all jigsaw blocks exhausted, fall through to random
            if (x === undefined) return;
        } else {
            // Fallback: random fill (pre-jigsaw or sequence exhausted)
            let attempts = 0;
            while (attempts < 20) {
                x = Math.floor(Math.random() * size);
                y = Math.floor(Math.random() * size);
                z = Math.floor(Math.random() * size);
                key = `${x},${y},${z}`;
                if (!filledBlocks.has(key)) break;
                attempts++;
                if (attempts >= 20) return;
            }
        }

        filledBlocks.add(key);
        fiEarned += CONFIG.fiPerBlock;
        spawnBlockParticles(x, y, z);
        emitEvent('block_filled', { x, y, z, total: filledBlocks.size });
    }

    function spawnBlockParticles(bx, by, bz) {
        const cx = w / 2, cy = h * 0.45;
        const scale = camera.scale;
        const offset = CONFIG.targetSize / 2;
        const zOffset = CONFIG.targetSize / 2;  // Center Z for rotation
        const pos = isoProject(bx - offset, by - offset, bz + 0.5 - zOffset, cx, cy, scale);

        for (let i = 0; i < STYLE.particles.blockBurstCount; i++) {
            particles.push({
                x: pos.x, y: pos.y,
                vx: (Math.random() - 0.5) * 4,
                vy: (Math.random() - 0.5) * 4 - 2,
                life: 1,
                color: STYLE.faceColors[Math.floor(Math.random() * STYLE.faceColors.length)],
            });
        }
    }

    function updateParticles() {
        for (let i = particles.length - 1; i >= 0; i--) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.1;
            p.life -= STYLE.particles.particleDecay;
            if (p.life <= 0) particles.splice(i, 1);
        }
    }

    function drawParticles() {
        particles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, 3 * p.life, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.globalAlpha = p.life;
            ctx.fill();
            ctx.globalAlpha = 1;
        });
    }

    // ═══════════════════════════════════════════════════════════════════════
    // EARNING PULSES - $ indicators that pulse around cube on economic events
    // Spawned by: payout, DEX trade, BTC staking, MVP resolve
    // ═══════════════════════════════════════════════════════════════════════
    function spawnEarningPulse(eventType, eventData) {
        const cx = w / 2;
        const cy = h * 0.45;

        // Determine pulse intensity based on event type
        let pulseCount = 1;
        let pulseColor = '#ffd700';  // Gold default

        if (eventType === 'payout_triggered') {
            pulseCount = 2 + Math.floor(Math.random() * 2);
            pulseColor = '#00e5d0';  // Cyan for payouts
        } else if (eventType === 'fi_trade_executed') {
            pulseCount = 1 + Math.floor(Math.random() * 2);
            pulseColor = '#ffd700';  // Gold for trades
        } else if (eventType === 'investor_funding_received') {
            pulseCount = 3 + Math.floor(Math.random() * 3);  // Burst for staker
            pulseColor = '#ffd700';  // Gold
        } else if (eventType === 'mvp_offering_resolved') {
            pulseCount = 4 + Math.floor(Math.random() * 3);  // Big burst for MVP
            pulseColor = '#ff4ea0';  // Pink for MVP milestone
        } else if (eventType === 'mvp_bid_submitted' || eventType === 'mvp_subscription_accrued') {
            pulseCount = 1;
            pulseColor = '#7c5cfc';  // Purple accent
        }

        // Spawn pulses around cube perimeter
        for (let i = 0; i < pulseCount; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radius = 60 + Math.random() * 40;  // Distance from cube center
            const startX = cx + Math.cos(angle) * radius;
            const startY = cy + Math.sin(angle) * radius * 0.5;  // Flatten for isometric

            // Random drift direction (slight upward bias)
            const driftAngle = angle + (Math.random() - 0.5) * 0.5;
            const driftSpeed = 0.3 + Math.random() * 0.4;

            earningPulses.push({
                x: startX,
                y: startY,
                vx: Math.cos(driftAngle) * driftSpeed,
                vy: Math.sin(driftAngle) * driftSpeed - 0.2,  // Slight upward drift
                life: 1,
                maxLife: 1,
                scale: 0.6 + Math.random() * 0.4,
                color: pulseColor,
                pulsePhase: Math.random() * Math.PI * 2,  // Random start phase for pulse
                pulseSpeed: 3 + Math.random() * 2,  // Pulse frequency
            });
        }
    }

    function updateEarningPulses() {
        for (let i = earningPulses.length - 1; i >= 0; i--) {
            const p = earningPulses[i];
            p.x += p.vx;
            p.y += p.vy;
            p.pulsePhase += 0.15;
            p.life -= 0.012;  // Fade over ~80 frames (~1.3s)

            // Remove when faded or off-screen
            if (p.life <= 0 || p.x < -50 || p.x > w + 50 || p.y < -50 || p.y > h + 50) {
                earningPulses.splice(i, 1);
            }
        }

        // Random spawn during BUILDING phase (simulates ongoing earning)
        if (currentPhase === 'BUILDING' && Math.random() < 0.008) {
            spawnEarningPulse('random_earning', {});
        }
    }

    function drawEarningPulses() {
        earningPulses.forEach(p => {
            ctx.save();

            // Pulsing scale effect
            const pulse = 0.8 + Math.sin(p.pulsePhase * p.pulseSpeed) * 0.2;
            const finalScale = p.scale * pulse;

            ctx.translate(p.x, p.y);
            ctx.globalAlpha = p.life * 0.35;  // Much more translucent to reduce noise

            // Outer glow
            ctx.shadowColor = p.color;
            ctx.shadowBlur = 8 * pulse;

            // $ circle
            ctx.beginPath();
            ctx.arc(0, 0, 10 * finalScale, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();

            // $ symbol (standard glyph - no emoji)
            ctx.shadowBlur = 0;
            ctx.fillStyle = shadeColor(p.color, -40);
            ctx.font = `bold ${12 * finalScale}px monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('$', 0, 1);

            ctx.globalAlpha = 1;
            ctx.restore();
        });
    }

    // ═══════════════════════════════════════════════════════════════════════
    // CONFETTI
    // ═══════════════════════════════════════════════════════════════════════
    function spawnConfetti() {
        const cx = w / 2, cy = h * 0.35;
        for (let i = 0; i < STYLE.particles.confettiCount; i++) {
            confetti.push({
                x: cx, y: cy,
                vx: (Math.random() - 0.5) * 12,
                vy: (Math.random() - 0.5) * 12 - 8,
                color: STYLE.faceColors[Math.floor(Math.random() * STYLE.faceColors.length)],
                life: 1,
                rotation: Math.random() * Math.PI * 2,
                rotationSpeed: (Math.random() - 0.5) * 0.3,
            });
        }
    }

    function updateConfetti() {
        for (let i = confetti.length - 1; i >= 0; i--) {
            const c = confetti[i];
            c.x += c.vx;
            c.y += c.vy;
            c.vy += 0.15;
            c.vx *= 0.99;
            c.rotation += c.rotationSpeed;
            c.life -= STYLE.particles.confettiDecay;
            if (c.life <= 0) confetti.splice(i, 1);
        }
    }

    function drawConfetti() {
        confetti.forEach(c => {
            ctx.save();
            ctx.translate(c.x, c.y);
            ctx.rotate(c.rotation);
            ctx.fillStyle = c.color;
            ctx.globalAlpha = c.life;
            ctx.fillRect(-4, -2, 8, 4);
            ctx.restore();
        });
        ctx.globalAlpha = 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PHASE MANAGEMENT
    // ═══════════════════════════════════════════════════════════════════════
    function getScaledElapsed(startTime) {
        return (Date.now() - startTime) * speedMultiplier;
    }

    function updatePhase() {
        // DRIVEN_MODE: Skip timer-based transitions, wait for state_sync events
        if (FLAGS.DRIVEN_MODE) {
            return;  // Phase controlled by simulator via state_sync
        }

        const elapsed = getScaledElapsed(phaseStartTime);
        const phase = PHASES[currentPhase];

        if (elapsed >= phase.duration) {
            const nextPhase = phase.next;
            if (FLAGS.DEBUG_TIMING) {
                console.log(`[CUBE] Phase transition: ${currentPhase} → ${nextPhase} at ${Date.now() - loopStartTime}ms`);
            }
            currentPhase = nextPhase;
            phaseStartTime = Date.now();
            onPhaseChange(nextPhase);
            emitEvent('phase_changed', { phase: nextPhase, loopTime: Date.now() - loopStartTime });
        }
    }

    // DRIVEN_MODE: Set phase directly from simulator state
    function setPhase(targetPhase, options = {}) {
        if (!PHASES[targetPhase]) {
            console.warn(`[CUBE] Invalid phase: ${targetPhase}`);
            return false;
        }
        if (currentPhase === targetPhase && !options.force) {
            return false;  // Already at target phase
        }
        if (FLAGS.DEBUG_TIMING) {
            console.log(`[CUBE] DRIVEN: ${currentPhase} → ${targetPhase}`);
        }
        currentPhase = targetPhase;
        phaseStartTime = Date.now();
        onPhaseChange(targetPhase);
        emitEvent('phase_changed', { phase: targetPhase, driven: true });
        return true;
    }

    // DRIVEN_MODE: Handle state_sync events from simulator
    function handleStateSync(data) {
        // Update phase if different
        if (data.phase && data.phase !== currentPhase) {
            setPhase(data.phase);
        }
        // Update F_i rating based on lifecycle stage
        if (data.lifecycle_stage) {
            simBridge.lastLifecycleStage = data.lifecycle_stage;
        }
        // Update block fill progress (for visual consistency)
        if (data.filled_blocks !== undefined) {
            const targetFilled = data.filled_blocks;
            const currentFilled = filledBlocks.size;
            // If simulator has more blocks, fill them
            if (targetFilled > currentFilled) {
                const toFill = targetFilled - currentFilled;
                for (let i = 0; i < toFill; i++) {
                    fillRandomBlock();
                }
            }
        }
    }

    function onPhaseChange(phase) {
        const size = CONFIG.targetSize;

        switch (phase) {
            case 'IDEA':
                // New loop begins
                loopCount++;
                loopStartTime = Date.now();
                agents.length = 0;
                filledBlocks.clear();
                confetti.length = 0;
                particles.length = 0;
                earningPulses.length = 0;
                liveChat.messages.length = 0;  // Clear live chat for new cycle
                jigsawSequence = [];
                jigsawIndex = 0;
                fiEarned = 0;
                opoTriggered = false;  // Reset OPO gate for new FoundUp
                opoTransitionTime = 0;
                resetCameraPan();  // Reset camera to center
                // Founder appears center
                const founder = spawnAgent('founder', 'ideating...');
                founder.x = w / 2;
                founder.y = h * 0.45;
                founder.sx = w / 2;
                founder.sy = h * 0.45;
                emitEvent('loop_started', { loopCount });
                break;

            case 'SCAFFOLD':
                // 0102 Agents join and go IDLE, awaiting ORCH handoff
                const planner = spawnAgent('builder', 'IDLE');
                addTickerMessage('agent_joins', { foundupIndex: loopCount });
                setTimeout(() => {
                    planner.status = 'planning...';
                    addTickerMessage('orch_handoff', { agentId: '0102', module: 'REGISTRY' });
                }, 800);
                const researcher = spawnAgent('builder', 'IDLE');
                setTimeout(() => {
                    addTickerMessage('agent_joins', { foundupIndex: loopCount });
                    researcher.status = 'researching...';
                    addTickerMessage('orch_handoff', { agentId: '0102', module: 'TASK_PIPELINE' });
                }, 1600);
                break;

            case 'BUILDING':
                // Initialize jigsaw fill sequence for this build cycle
                resetJigsawSequence();

                // FAM module building sequence - agents start IDLE then get ORCH handoff
                const famModules = ['PERSISTENCE', 'EVENTS', 'TOKEN_ECON', 'GOVERNANCE', 'API'];
                const moduleAgent1 = spawnAgent('builder', 'IDLE');
                setTimeout(() => {
                    moduleAgent1.status = `building ${famModules[0]}`;
                    addTickerMessage('build_persistence', {});
                }, 400);
                const moduleAgent2 = spawnAgent('builder', 'IDLE');
                setTimeout(() => {
                    moduleAgent2.status = `building ${famModules[1]}`;
                    addTickerMessage('build_events', {});
                }, 1000);
                const moduleAgent3 = spawnAgent('builder', 'IDLE');
                setTimeout(() => {
                    moduleAgent3.status = `building ${famModules[2]}`;
                    addTickerMessage('build_token_econ', {});
                }, 1600);

                // Initial fill burst - start with ~10% filled (jigsaw order)
                for (let i = 0; i < 6; i++) {
                    fillRandomBlock();
                }
                break;

            case 'COMPLETE':
                // Fill all remaining blocks instantly
                for (let x = 0; x < size; x++) {
                    for (let y = 0; y < size; y++) {
                        for (let z = 0; z < size; z++) {
                            filledBlocks.add(`${x},${y},${z}`);
                        }
                    }
                }
                agents.forEach(a => a.status = 'done!');
                emitEvent('cube_complete', { blocks: size * size * size, fiEarned });
                break;

            case 'PROMOTING':
                // First builder becomes promoter
                if (agents.length > 1) {
                    const promoter = agents[1]; // Skip founder
                    promoter.type = 'promoter';
                    promoter.color = STYLE.agentColors.promoter;
                    promoter.status = 'promoting...';
                    promoter.tx = w - 80;
                    promoter.ty = h * 0.3;
                }
                break;

            case 'STAKING':
                // BTC staker arrives from right (CABR/PoB: liquidity provider)
                // ANT FARM MOMENT: All agents react - switch to promoting/announcing!
                const staker = spawnAgent('staker', 'staking BTC...');
                staker.sx = w + 50;
                staker.x = w + 50;
                staker.ty = h * 0.4;

                // ALL agents react to the Staker entrance
                const stakingReactions = [
                    'announcing!', 'sharing...', 'promoting!', 'excited!',
                    'spreading word!', 'telling friends!', 'hyping!', 'watching...'
                ];
                agents.forEach((a, i) => {
                    if (a !== staker) {
                        // Stagger reactions for natural feel
                        setTimeout(() => {
                            const reaction = stakingReactions[i % stakingReactions.length];
                            a.status = reaction;
                            // Make agents briefly "spaz out" toward staker (excited reaction)
                            a.tx = w * 0.6 + Math.random() * 80;
                            a.ty = h * 0.4 + Math.random() * 60;
                        }, i * 150);
                    }
                });

                // Add ticker messages showing the buzz
                setTimeout(() => addTickerMessage('agent_earned', { actor_id: '0102', amount: 50, foundup_idx: loopCount }), 500);
                setTimeout(() => addTickerMessage('sim_promoting', {}), 1000);

                emitEvent('staker_arrived', { agent: staker.id, agentsReacted: agents.length - 1 });
                break;

            case 'CUSTOMERS':
                // OPO TRANSITION - Gate opens! Pre-OPO → Post-OPO
                // This is the Open Public Offering moment
                opoTriggered = true;
                opoTransitionTime = Date.now();
                spawnConfetti();  // Celebration burst for OPO
                addTickerMessage('opo_gate_opens', { foundupIndex: loopCount });

                // Customers join - more agents spawn (users/customers)
                spawnAgent('builder', 'customer!');
                setTimeout(() => spawnAgent('builder', 'user joined!'), 600);
                setTimeout(() => spawnAgent('builder', 'trying it...'), 1200);
                setTimeout(() => spawnAgent('builder', 'paying!'), 1800);
                agents.forEach(a => {
                    if (a.type === 'builder' && a.status !== 'customer!' && a.status !== 'user joined!' && a.status !== 'trying it...' && a.status !== 'paying!') {
                        a.status = 'growing...';
                    }
                });
                emitEvent('customers_arrived', { count: 4, opo: true });
                break;

            case 'LAUNCH':
                // Foundup_i MVP Launch - PoC → Proto → MVP complete
                spawnConfetti();
                agents.forEach(a => a.status = 'live!');
                startLaunchPan();  // Start camera pan effect
                emitEvent('dao_launched', { agents: agents.length, fiEarned, milestone: 'MVP' });
                break;

            case 'CELEBRATE':
                // Continue celebration, spawn more confetti
                setTimeout(() => spawnConfetti(), 1000);
                break;

            case 'RESET':
                // Trigger camera handoff if multi-cube mode enabled
                if (FLAGS.MULTI_CUBE) {
                    triggerCameraHandoff();
                }
                // Loops back to IDEA via phase transition
                break;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // WSP IMPORTANCE COLOR MAPPING
    // Maps block position to WSP module importance (P0=critical, P4=low)
    // ═══════════════════════════════════════════════════════════════════════
    function getWSPImportanceColor(x, y, z, size) {
        // Layer-based importance: bottom layers = foundation (P0), top = features (P4)
        // Center blocks more important than edges
        const centerDist = Math.abs(x - size / 2 + 0.5) + Math.abs(y - size / 2 + 0.5);
        const layerImportance = z / (size - 1); // 0 = bottom, 1 = top
        const centerImportance = 1 - (centerDist / size);

        // Combine: bottom-center = P0, top-edge = P4
        const importance = (1 - layerImportance) * 0.6 + centerImportance * 0.4;

        if (importance > 0.8) return STYLE.levelColors.P0;      // Elite - red
        if (importance > 0.6) return STYLE.levelColors.P1;      // Senior - orange
        if (importance > 0.4) return STYLE.levelColors.P2;      // Mid - yellow
        if (importance > 0.2) return STYLE.levelColors.P3;      // Junior - green
        return STYLE.levelColors.P4;                             // Novice - blue
    }

    // ═══════════════════════════════════════════════════════════════════════
    // DRAWING
    // ═══════════════════════════════════════════════════════════════════════
    function drawCube() {
        const cx = w / 2;
        const cy = h * 0.45;
        const size = CONFIG.targetSize;
        const scale = camera.scale;
        const offset = size / 2;

        // Glow behind cube (rotation is now applied in isoProject)
        const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, 100);
        grd.addColorStop(0, 'rgba(124, 92, 252, 0.1)');
        grd.addColorStop(1, 'transparent');
        ctx.fillStyle = grd;
        ctx.fillRect(0, 0, w, h);

        // Calculate global alpha for fade effects
        // Transition order: agents fade (0-2s) → cube fades (2-5s) → reset
        let globalAlpha = 1;
        if (currentPhase === 'IDEA') {
            // Fade in new cube
            const elapsed = getScaledElapsed(phaseStartTime);
            globalAlpha = Math.min(1, elapsed / 1500);  // 1.5s fade in
        } else if (currentPhase === 'CELEBRATE') {
            // Cube starts fading AFTER agents (which fade 0-2000ms)
            const elapsed = getScaledElapsed(phaseStartTime);
            if (elapsed > 2000) {
                // Fade cube over remaining ~3.8s (2000-5800ms)
                globalAlpha = Math.max(0, 1 - (elapsed - 2000) / 3000);
            }
        } else if (currentPhase === 'RESET') {
            globalAlpha = 0;  // Cube fully hidden during reset
        }

        if (currentPhase === 'IDEA' || currentPhase === 'SCAFFOLD') {
            // Translucent planning cube - shows structure before agents fill it
            drawPlanningCube(cx, cy, size, scale, offset, globalAlpha);
        } else {
            // Draw filled blocks with WSP importance colors during BUILD
            drawFilledCube(cx, cy, size, scale, offset, globalAlpha);
        }
    }

    function drawPlanningCube(cx, cy, size, scale, offset, globalAlpha) {
        // Genesis Vision: VISION → DECONSTRUCT → BLUEPRINT → SCAFFOLD
        // The outcome appears first, agents reverse-engineer it into a blueprint

        if (currentPhase === 'IDEA') {
            const elapsed = getScaledElapsed(phaseStartTime);
            const zOffset = size / 2;

            // Sub-phase timing (15s total)
            // First principles: VISION must feel TANGIBLE (alpha > 0.3 = sub-blocks render)
            // DECONSTRUCT needs visual range (0.45→0, not 0.25→0) and dramatic drift
            const VISION_END = 4000;      // 0-4s: full transparent cube materializes
            const DECON_END = 13000;      // 4-13s: blocks dissolve outward (9s for drama)
            // 13-15s: wireframe only (blueprint ready)

            if (elapsed < VISION_END) {
                // === VISION: Abstract white cube - you don't know the modules yet ===
                const fadeIn = Math.min(1, elapsed / 1500);  // 1.5s fade-in
                const visionAlpha = 0.35 + Math.sin(elapsed / 500) * 0.05;  // 0.30-0.40

                // Wireframe outline
                drawWireframeCube(cx, cy, size, scale, 0.3 * globalAlpha * fadeIn);

                // All 64 blocks as WHITE transparent vision (no colors = abstract)
                for (let z = 0; z < size; z++) {
                    for (let y = size - 1; y >= 0; y--) {
                        for (let x = 0; x < size; x++) {
                            drawCubelet(
                                x - offset, y - offset, z - zOffset,
                                cx, cy, scale, '#ffffff',
                                visionAlpha * globalAlpha * fadeIn
                            );
                        }
                    }
                }

                // Vision statement - rotates per loop cycle
                const labelPos = isoProject(0, 0, size - zOffset + 1.5, cx, cy, scale);
                const statement = VISION_STATEMENTS[loopCount % VISION_STATEMENTS.length];
                ctx.textAlign = 'center';
                // "VISION" header
                ctx.font = 'bold 13px monospace';
                ctx.fillStyle = `rgba(255, 215, 0, ${0.9 * globalAlpha * fadeIn})`;
                ctx.fillText('VISION', labelPos.x, labelPos.y - 22);
                // Statement text
                ctx.font = '11px monospace';
                ctx.fillStyle = `rgba(200, 200, 220, ${0.7 * globalAlpha * fadeIn})`;
                ctx.fillText(statement, labelPos.x, labelPos.y - 6);

            } else if (elapsed < DECON_END) {
                // === DECONSTRUCT: Blocks dissolve outward, wireframe stays ===
                const deconProgress = (elapsed - VISION_END) / (DECON_END - VISION_END);  // 0→1

                // Wireframe persists and slightly brightens as blocks leave
                const wireAlpha = 0.25 + deconProgress * 0.15;  // 0.25→0.40
                drawWireframeCube(cx, cy, size, scale, wireAlpha * globalAlpha);

                // Blocks dissolve: outer/top first, inner/bottom last (white = abstract)
                for (let z = 0; z < size; z++) {
                    for (let y = size - 1; y >= 0; y--) {
                        for (let x = 0; x < size; x++) {

                            // Dissolution priority: edges/top dissolve first
                            const centerDist = Math.abs(x - size / 2 + 0.5) + Math.abs(y - size / 2 + 0.5);
                            const edgeness = centerDist / size;  // 0=center, ~1=edge
                            const topness = z / (size - 1);  // 0=bottom, 1=top
                            const dissolveOrder = edgeness * 0.6 + topness * 0.4;  // 0=last, 1=first

                            // Staggered dissolution: each block fades over ~60% of the range
                            const blockStart = dissolveOrder * 0.4;
                            const blockEnd = blockStart + 0.6;
                            const blockAlpha = 1 - Math.min(1, Math.max(0,
                                (deconProgress - blockStart) / (blockEnd - blockStart)
                            ));

                            if (blockAlpha > 0.01) {
                                // Dramatic outward drift as block dissolves
                                const drift = (1 - blockAlpha) * 0.6;
                                const dx = (x - size / 2 + 0.5) * drift;
                                const dy = (y - size / 2 + 0.5) * drift;
                                const dz = (z - size / 2 + 0.5) * drift;

                                // White dissolving: 0.35 → 0
                                drawCubelet(
                                    x - offset + dx, y - offset + dy, z - zOffset + dz,
                                    cx, cy, scale, '#ffffff',
                                    blockAlpha * 0.35 * globalAlpha
                                );
                            }
                        }
                    }
                }

            } else {
                // === BLUEPRINT: Only wireframe remains ===
                drawWireframeCube(cx, cy, size, scale, 0.35 * globalAlpha);

                // "Blueprint ready" label
                const labelPos = isoProject(0, 0, size - zOffset + 1, cx, cy, scale);
                ctx.font = '11px monospace';
                ctx.fillStyle = `rgba(0, 229, 208, ${0.7 * globalAlpha})`;
                ctx.textAlign = 'center';
                ctx.fillText('BLUEPRINT', labelPos.x, labelPos.y - 10);
            }

        } else if (currentPhase === 'SCAFFOLD') {
            // === SCAFFOLD PHASE ===
            // Progressive layer-by-layer scaffolding reveal
            const layersToShow = getScaffoldLayersToShow();
            const elapsed = getScaledElapsed(phaseStartTime);
            const zOffset = size / 2;  // Center Z for rotation

            // Draw wireframe for upcoming layers (faint preview)
            drawWireframeCube(cx, cy, size, scale, 0.3 * globalAlpha);

            // Draw scaffolded layers - bottom up
            for (let z = 0; z < size; z++) {
                const layerVisible = z < layersToShow;
                const isCurrentLayer = z === layersToShow - 1;

                for (let y = size - 1; y >= 0; y--) {
                    for (let x = 0; x < size; x++) {
                        const color = getWSPImportanceColor(x, y, z, size);

                        if (layerVisible) {
                            // Scaffolded layers: solid wireframe appearance
                            let alpha = isCurrentLayer
                                ? 0.4 + Math.sin(elapsed / 200) * 0.1  // Pulsing current layer
                                : 0.35;

                            // Only draw edges/corners to look like scaffolding (not solid blocks)
                            const isEdge = x === 0 || x === size - 1 || y === 0 || y === size - 1;
                            const isCorner = (x === 0 || x === size - 1) && (y === 0 || y === size - 1);

                            if (isCorner || (isEdge && z === 0)) {
                                // Full blocks at corners and bottom edges
                                drawCubelet(
                                    x - offset, y - offset, z - zOffset,
                                    cx, cy, scale,
                                    color,
                                    alpha * globalAlpha
                                );
                            } else if (isEdge) {
                                // Lighter blocks on other edges
                                drawCubelet(
                                    x - offset, y - offset, z - zOffset,
                                    cx, cy, scale,
                                    color,
                                    alpha * 0.5 * globalAlpha
                                );
                            }
                        } else {
                            // Ghost preview for upcoming layers
                            const isCorner = (x === 0 || x === size - 1) && (y === 0 || y === size - 1);
                            if (isCorner) {
                                drawCubelet(
                                    x - offset, y - offset, z - zOffset,
                                    cx, cy, scale,
                                    color,
                                    0.08 * globalAlpha
                                );
                            }
                        }
                    }
                }
            }

            // Layer counter label
            ctx.font = '11px monospace';
            ctx.fillStyle = `rgba(0, 229, 208, ${0.8 * globalAlpha})`;
            ctx.textAlign = 'center';
            ctx.fillText(`Layer ${layersToShow}/${size}`, cx, cy + size * scale + 40);
        }
    }

    function drawFilledCube(cx, cy, size, scale, offset, globalAlpha) {
        const totalBlocks = Math.pow(size, 3);
        const filled = filledBlocks.size;
        const progress = filled / totalBlocks;

        // Ghost block visibility scales with progress
        // PoC (IDEA phase): no ghosts shown (handled by phase check below)
        // Proto (SCAFFOLD + BUILDING <85%): gradual ghost appearance
        // MVP (85%+): full ghost visibility
        let ghostAlpha;
        if (progress < 0.85) {
            // Proto - gradual from 0.02 to 0.08 as cube fills
            ghostAlpha = 0.02 + progress * 0.07;
        } else {
            // MVP - full ghost visibility
            ghostAlpha = 0.08 + (progress - 0.85) * 0.13;  // 0.08 to 0.10
        }

        // Z offset for center rotation (cube rotates around true center)
        const zOffset = size / 2;

        // Draw wireframe scaffolding during BUILDING - persists as blocks fill in
        if (currentPhase === 'BUILDING') {
            // Wireframe fades as cube fills: 0.25 → 0.05 (scaffolding disappears when done)
            const wireAlpha = 0.25 - progress * 0.20;
            drawWireframeCube(cx, cy, size, scale, wireAlpha * globalAlpha);
        }

        for (let z = 0; z < size; z++) {
            for (let y = size - 1; y >= 0; y--) {
                for (let x = 0; x < size; x++) {
                    const key = `${x},${y},${z}`;
                    if (filledBlocks.has(key)) {
                        // Filled blocks use WSP importance colors - SOLID
                        const color = getWSPImportanceColor(x, y, z, size);
                        drawCubelet(
                            x - offset, y - offset, z - zOffset,
                            cx, cy, scale,
                            color,
                            globalAlpha
                        );
                    } else {
                        // Ghost blocks = SCAFFOLDING/PLANNING
                        // Appear during PoC (idea visualization) and SCAFFOLD (architecture)
                        // Then fill in during BUILDING (WSP 15)
                        let showGhost = false;
                        let alpha = ghostAlpha;

                        if (currentPhase === 'IDEA') {
                            // PoC: faint ghost outline - the vision
                            showGhost = true;
                            alpha = 0.03;  // Very faint - just the idea
                        } else if (currentPhase === 'SCAFFOLD') {
                            // SCAFFOLD: clearer ghost - the blueprint
                            showGhost = true;
                            alpha = 0.08;  // Blueprint visibility
                        } else if (currentPhase === 'BUILDING') {
                            // BUILDING: scaffolding persists - blocks fill INTO the scaffolding
                            showGhost = true;
                            alpha = 0.12;  // Scaffolding visible but subtle
                        } else {
                            // After COMPLETE: full ghost visibility
                            showGhost = true;
                            alpha = ghostAlpha;
                        }

                        if (showGhost) {
                            const color = getWSPImportanceColor(x, y, z, size);
                            drawCubelet(
                                x - offset, y - offset, z - zOffset,
                                cx, cy, scale,
                                color,
                                alpha * globalAlpha
                            );
                        }
                    }
                }
            }
        }
    }

    function drawStatusBar() {
        const cx = w / 2;

        const blocksFilled = filledBlocks.size;
        const totalBlocks = Math.pow(CONFIG.targetSize, 3);
        const pct = Math.round((blocksFilled / totalBlocks) * 100);
        const stage = getLifecycleStage();

        // Stage badge colors
        const stageColors = {
            'PoC': STYLE.levelColors.P0,       // Red - foundation
            'Proto': STYLE.levelColors.P1,     // Orange - prototype
            'MVP': STYLE.levelColors.P2,       // Yellow - MVP
            'Complete': '#00e5d0',             // Cyan - launched
        };

        // Phase announcements + progress badge — ONLY in single-cube view
        if (!cameraHandoff.zoomedOut) {
            const announcementY = h * 0.15;
            const badgeY = announcementY + 22;  // Progress badge just below announcement

            // Phase: IDEA (founder with lightbulb)
            if (currentPhase === 'IDEA') {
                const elapsed = getScaledElapsed(phaseStartTime);
                const pulse = 0.7 + Math.sin(elapsed / 200) * 0.3;
                ctx.font = STYLE.fonts.announcement;
                ctx.fillStyle = `rgba(255, 45, 45, ${pulse})`;  // Red for PoC
                ctx.textAlign = 'center';
                ctx.fillText('Fᵢ PoC Stage', cx, announcementY);
            }

            // Phase: SCAFFOLD/BUILDING (prototype phase)
            if (currentPhase === 'SCAFFOLD' || (currentPhase === 'BUILDING' && stage === 'Proto')) {
                const elapsed = getScaledElapsed(phaseStartTime);
                const pulse = 0.6 + Math.sin(elapsed / 180) * 0.2;
                ctx.font = STYLE.fonts.announcement;
                ctx.fillStyle = `rgba(245, 166, 35, ${pulse})`;  // Orange for Proto
                ctx.textAlign = 'center';
                ctx.fillText('Building Prototype', cx, announcementY);
            }

            // Phase: LAUNCH/CELEBRATE (MVP)
            if (currentPhase === 'LAUNCH' || currentPhase === 'CELEBRATE') {
                const elapsed = getScaledElapsed(phaseStartTime);
                const pulse = 0.8 + Math.sin(elapsed / 100) * 0.2;
                ctx.font = STYLE.fonts.announcement;
                ctx.fillStyle = `rgba(255, 215, 0, ${pulse})`;  // Gold for MVP
                ctx.textAlign = 'center';
                ctx.fillText('Fᵢ MVP is Live!', cx, announcementY);
            }

            // Phase: CUSTOMERS
            if (currentPhase === 'CUSTOMERS') {
                const elapsed = getScaledElapsed(phaseStartTime);
                const pulse = 0.7 + Math.sin(elapsed / 150) * 0.3;
                ctx.font = STYLE.fonts.announcement;
                ctx.fillStyle = `rgba(0, 229, 208, ${pulse})`;
                ctx.textAlign = 'center';
                ctx.fillText('First paying customers!', cx, announcementY);
            }

            // Progress badge — below announcement (e.g. [Proto 45%])
            if (currentPhase === 'BUILDING' || currentPhase === 'COMPLETE') {
                const stageColor = stageColors[stage] || '#fff';
                ctx.font = 'bold 10px monospace';
                ctx.fillStyle = stageColor;
                ctx.textAlign = 'center';
                const stageText = currentPhase === 'BUILDING' ? `[${stage} ${pct}%]` : `[${stage}]`;
                ctx.fillText(stageText, cx, badgeY);
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // MULTI-CUBE ZOOM-OUT (Phase 3)
    // Draw mini cubes with agent pixel swarms when zoomed out
    // ═══════════════════════════════════════════════════════════════════════
    function drawMiniCubes() {
        const miniScale = 6;  // Small cubes
        const spacing = 120;  // Space between cubes
        const startX = w / 2 - (cameraHandoff.cubePositions.length - 1) * spacing / 2;
        const startY = h * 0.4;

        cameraHandoff.cubePositions.forEach((cube, i) => {
            const cubeX = startX + i * spacing;
            const cubeY = startY;

            // Draw mini cube (simplified - just faces)
            drawMiniCube(cubeX, cubeY, miniScale, i);

            // Draw agent swarm around cube (pixels colored by role)
            drawAgentSwarm(cubeX, cubeY, i);

            // Label
            ctx.font = '10px monospace';
            ctx.fillStyle = 'rgba(255,255,255,0.6)';
            ctx.textAlign = 'center';
            ctx.fillText(`#${cube.loopCount}`, cubeX, cubeY + 60);
        });
    }

    function drawMiniCube(cx, cy, scale, cubeIndex) {
        // Draw a simplified cube representation
        const size = 2;  // 2x2x2 mini representation
        const offset = size / 2;
        const colors = [
            STYLE.levelColors.P0,
            STYLE.levelColors.P1,
            STYLE.levelColors.P2,
            STYLE.levelColors.P3,
        ];

        // Just draw top visible blocks
        for (let x = 0; x < size; x++) {
            for (let y = 0; y < size; y++) {
                const colorIdx = (x + y + cubeIndex) % colors.length;
                const p = isoProject(x - offset, y - offset, size, cx, cy, scale);

                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p.x + scale * 0.866, p.y - scale * 0.5);
                ctx.lineTo(p.x, p.y - scale);
                ctx.lineTo(p.x - scale * 0.866, p.y - scale * 0.5);
                ctx.closePath();

                ctx.fillStyle = colors[colorIdx];
                ctx.globalAlpha = 0.8;
                ctx.fill();
                ctx.strokeStyle = 'rgba(255,255,255,0.3)';
                ctx.lineWidth = 0.5;
                ctx.stroke();
                ctx.globalAlpha = 1;
            }
        }
    }

    function drawAgentSwarm(cx, cy, cubeIndex) {
        // Draw pixel swarm representing agents around mini cube
        // Colors represent roles (WSP 54)
        const swarmSize = 8 + cubeIndex * 3;  // More agents for older cubes
        const elapsed = Date.now() / 1000;

        for (let i = 0; i < swarmSize; i++) {
            // Orbital motion around cube
            const angle = (i / swarmSize) * Math.PI * 2 + elapsed * 0.5 + cubeIndex;
            const radius = 25 + Math.sin(elapsed * 2 + i) * 8;
            const px = cx + Math.cos(angle) * radius;
            const py = cy + Math.sin(angle) * radius * 0.5 - 20;

            // Role-based color (cycle through agent types)
            const roles = ['builder', 'promoter', 'staker', 'founder'];
            const role = roles[i % roles.length];
            const color = STYLE.agentColors[role];

            // Draw pixel dot
            ctx.beginPath();
            ctx.arc(px, py, 2, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();

            // Subtle glow
            ctx.shadowColor = color;
            ctx.shadowBlur = 4;
            ctx.fill();
            ctx.shadowBlur = 0;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // ECOSYSTEM VIEW (Far zoom - time-offset duplicates of same FoundUp)
    // Each cube shows the same lifecycle at different points in time
    // ═══════════════════════════════════════════════════════════════════════
    // Tile grid configuration for ecosystem zoom levels
    function getTileGrid() {
        const s = camera.scale;
        if (s >= 10) return { cols: 1, rows: 1 };       // Normal view (not used here)
        if (s >= 6)  return { cols: 2, rows: 2 };       // 4 tiles
        if (s >= 4)  return { cols: 3, rows: 3 };       // 9 tiles
        return { cols: 4, rows: 4 };                     // 16 tiles
    }

    // Get ecosystem tagline based on grid size (012's vision)
    function getEcosystemTagline(tileCount) {
        if (tileCount <= 4)  return 'FoundUPS eating the StartUP';
        if (tileCount <= 9)  return 'FoundUPS eating corporations';
        return 'FoundUPS redistributing Bitcoin';
    }

    function drawEcosystemView() {
        const now = Date.now();
        const grid = getTileGrid();
        const tileCount = grid.cols * grid.rows;

        ctx.save();

        // Ecosystem label - tagline changes based on grid size (012's vision)
        const tagline = getEcosystemTagline(tileCount);
        ctx.font = 'bold 14px sans-serif';
        ctx.fillStyle = 'rgba(124, 92, 252, 0.9)';
        ctx.textAlign = 'center';
        ctx.fillText(tagline, w / 2, 22);

        // Grid layout: divide canvas into tiles with padding
        const pad = 20;
        const tileW = (w - pad * (grid.cols + 1)) / grid.cols;
        const tileH = (h - pad * (grid.rows + 1) - 30) / grid.rows;  // 30px for header
        const cubeScale = Math.min(tileW, tileH) / 16;  // Scale cubes to fit tiles
        const cubeSize = 4;  // Same 4x4x4 as main cube
        const offset = cubeSize / 2;
        const zOffset = cubeSize / 2;

        for (let row = 0; row < grid.rows; row++) {
            for (let col = 0; col < grid.cols; col++) {
                const tileIdx = row * grid.cols + col;

                // Tile center
                const cx = pad + col * (tileW + pad) + tileW / 2;
                const cy = 35 + pad + row * (tileH + pad) + tileH / 2;

                // Time-shift: each tile is offset in the lifecycle
                const timeShift = (tileIdx * CONFIG.loopDuration) / tileCount;
                const tileElapsed = ((now - loopStartTime + timeShift) % CONFIG.loopDuration);
                const progress = tileElapsed / CONFIG.loopDuration;

                // Determine phase from progress (simplified lifecycle)
                let stage, stageColor, fillRatio;
                if (progress < 0.125) {
                    stage = 'VISION';
                    stageColor = 'rgba(255, 255, 255, 0.7)';
                    fillRatio = progress / 0.125;
                } else if (progress < 0.25) {
                    stage = 'SCAFFOLD';
                    stageColor = STYLE.levelColors.P0;
                    fillRatio = 0;  // Wireframe only
                } else if (progress < 0.75) {
                    stage = 'BUILDING';
                    stageColor = STYLE.levelColors.P1;
                    fillRatio = (progress - 0.25) / 0.5;
                } else if (progress < 0.92) {
                    stage = 'MVP';
                    stageColor = STYLE.levelColors.P3;
                    fillRatio = 1;
                } else {
                    stage = 'LAUNCH';
                    stageColor = '#ffd700';
                    fillRatio = 1;
                }

                // Tile border (subtle)
                ctx.strokeStyle = 'rgba(124, 92, 252, 0.15)';
                ctx.lineWidth = 0.5;
                ctx.strokeRect(
                    pad + col * (tileW + pad),
                    35 + pad + row * (tileH + pad),
                    tileW, tileH
                );

                // Wireframe cube outline
                drawWireframeCube(cx, cy, cubeSize, cubeScale,
                    stage === 'VISION' ? 0.4 : 0.15);

                // Fill blocks based on progress
                const totalBlocks = cubeSize * cubeSize * cubeSize;
                const blocksToShow = Math.floor(fillRatio * totalBlocks);
                let blockCount = 0;

                if (stage === 'VISION') {
                    // White transparent blocks (abstract vision)
                    const fadeIn = Math.min(1, fillRatio * 8);
                    for (let z = 0; z < cubeSize; z++) {
                        for (let y = cubeSize - 1; y >= 0; y--) {
                            for (let x = 0; x < cubeSize; x++) {
                                drawCubelet(x - offset, y - offset, z - zOffset,
                                    cx, cy, cubeScale, '#ffffff', 0.25 * fadeIn);
                            }
                        }
                    }
                } else if (blocksToShow > 0) {
                    // Colored blocks filling in
                    for (let z = 0; z < cubeSize && blockCount < blocksToShow; z++) {
                        for (let y = cubeSize - 1; y >= 0 && blockCount < blocksToShow; y--) {
                            for (let x = 0; x < cubeSize && blockCount < blocksToShow; x++) {
                                const color = (stage === 'LAUNCH' || stage === 'MVP')
                                    ? getWSPImportanceColor(x, y, z, cubeSize)
                                    : getWSPImportanceColor(x, y, z, cubeSize);
                                drawCubelet(x - offset, y - offset, z - zOffset,
                                    cx, cy, cubeScale, color, 0.75);
                                blockCount++;
                            }
                        }
                    }
                }

                // Orbiting agent dots
                const agentCount = Math.max(1, Math.floor(progress * 4));
                const elapsed = now / 1000;
                for (let j = 0; j < agentCount; j++) {
                    const angle = (j / agentCount) * Math.PI * 2 + elapsed * 0.6 + tileIdx;
                    const radius = cubeScale * 5 + Math.sin(elapsed * 1.5 + j) * 3;
                    const px = cx + Math.cos(angle) * radius;
                    const py = cy + Math.sin(angle) * radius * 0.5 - cubeScale * 2;
                    ctx.fillStyle = j === 0 ? STYLE.agentColors.founder : STYLE.agentColors.builder;
                    ctx.beginPath();
                    ctx.arc(px, py, 1.5, 0, Math.PI * 2);
                    ctx.fill();
                }

                // Label: F₁, F₂, etc. + stage
                ctx.font = '9px monospace';
                ctx.fillStyle = stageColor;
                ctx.textAlign = 'center';
                ctx.fillText(`F${toSubscript(tileIdx + 1)} ${stage}`,
                    cx, cy + cubeScale * 6 + 8);
            }
        }

        ctx.restore();
    }

    // Check if we should show ecosystem view (far zoom)
    function isEcosystemView() {
        return camera.scale <= STYLE.camera.ecosystemThreshold;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // COLOR KEY LEGEND (Bottom-right with professional border)
    // ═══════════════════════════════════════════════════════════════════════
    // Phase-specific activity descriptions for the right panel
    const PHASE_ACTIVITIES = Object.freeze({
        IDEA: [
            'Imagining the outcome...',
            'Defining the vision...',
        ],
        SCAFFOLD: [
            'Planning architecture...',
            'Researching solutions...',
            'Following WSP protocols...',
            'Mapping dependencies...',
            'Building simulator...',
        ],
        BUILDING: [
            'Coding PERSISTENCE module',
            'Building EVENTS pipeline',
            'Testing TOKEN_ECON logic',
            'Following WSP 15 priorities',
            'Running simulator tests',
            'Auditing security (WSP 71)',
        ],
        PROMOTING: [
            'Preparing pitch deck...',
            'Publishing milestones...',
            'Growing community...',
        ],
        STAKING: [
            'BTC liquidity arriving...',
            'Stakers joining pool...',
            'Protocol participation...',
        ],
        CUSTOMERS: [
            'First paying stakeholders!',
            'Subscription tiers live...',
            'Onboarding 012s...',
        ],
    });

    // ═══════════════════════════════════════════════════════════════════════
    // STAGE DEFINITIONS (0-7 based on actual built modules)
    // ═══════════════════════════════════════════════════════════════════════
    // Stages map to actual FAM/Simulator module lifecycle:
    // 0: IDEA - foundup_created event
    // 1: AGENTS JOIN - 0102 agents claim tasks
    // 2: SCAFFOLDING - FAM infrastructure (registry, persistence)
    // 3: SIM/ANIMATION - simulation baseline created
    // 4: PROTO DELIVERY - first paid task (PoC→Proto)
    // 5: TRACTION - multiple milestones, F_i trading
    // 6: STAKING - BTC stakers enter, MVP bidding
    // 7: MVP - paying subscribers arrive
    const STAGE_DEFS = Object.freeze({
        0: { name: 'IDEA', phase: 'IDEA', threshold: 0 },
        1: { name: 'AGENTS', phase: 'SCAFFOLD', threshold: 0.05 },
        2: { name: 'SCAFFOLD', phase: 'SCAFFOLD', threshold: 0.15 },
        3: { name: 'SIM', phase: 'BUILDING', threshold: 0.30 },
        4: { name: 'PROTO', phase: 'BUILDING', threshold: 0.50 },
        5: { name: 'TRACTION', phase: 'PROMOTING', threshold: 0.65 },
        6: { name: 'STAKING', phase: 'STAKING', threshold: 0.80 },
        7: { name: 'MVP', phase: 'LAUNCH', threshold: 0.95 },
    });

    // Get current stage number based on F_i rating
    function getCurrentStage() {
        const composite = fiRating.composite;
        for (let i = 7; i >= 0; i--) {
            if (composite >= STAGE_DEFS[i].threshold) return i;
        }
        return 0;
    }

    // Draw scaffolding text floating to the RIGHT of the CUBE (not the key)
    // This is free-floating text near the cube, no border
    function drawCubeScaffoldingText() {
        // Position aligned with Key panel left edge, sitting just above it
        const keyW = 140;
        const cubeRightEdge = w - keyW - 7;  // Align with key panel left edge
        const keyTopY = h - 150 - 50 - 12;   // Key panel top edge (after shift)
        const cubeTopY = keyTopY - 70;        // Just above key panel

        ctx.save();

        const stage = getCurrentStage();
        const stageDef = STAGE_DEFS[stage];
        const borderColor = fiRating.borderColor;

        // Stage number + name (floating near cube)
        ctx.font = 'bold 14px monospace';
        ctx.fillStyle = borderColor;
        ctx.textAlign = 'left';
        ctx.fillText(`${stage} ${stageDef.name}`, cubeRightEdge, cubeTopY);

        // Phase activity lines (floating, no border)
        const activities = PHASE_ACTIVITIES[currentPhase] || PHASE_ACTIVITIES.BUILDING;
        const elapsed = getScaledElapsed(phaseStartTime);
        const linesVisible = Math.min(activities.length, 1 + Math.floor(elapsed / 2500));

        ctx.font = '9px monospace';
        for (let i = 0; i < linesVisible && i < 4; i++) {
            const lineAlpha = i < linesVisible - 1 ? 0.6 : 0.4 + Math.sin(elapsed / 300) * 0.2;
            ctx.fillStyle = `rgba(200, 200, 220, ${lineAlpha})`;
            ctx.fillText('> ' + activities[i], cubeRightEdge, cubeTopY + 16 + i * 13);
        }

        ctx.restore();
    }

    function drawColorKey() {
        const keyW = 140;
        const keyH = 150;  // Expanded: AGENTS legend + CABR score + OPO gate
        const keyX = w - keyW - 7;   // Shifted right 5px
        const keyY = h - keyH - 50;  // Shifted down 5px

        ctx.save();

        // Background
        const bgGradient = ctx.createLinearGradient(keyX - 8, keyY - 12, keyX - 8, keyY - 12 + keyH);
        bgGradient.addColorStop(0, 'rgba(15, 15, 25, 0.85)');
        bgGradient.addColorStop(1, 'rgba(10, 10, 20, 0.75)');
        ctx.fillStyle = bgGradient;
        ctx.roundRect(keyX - 8, keyY - 12, keyW, keyH, 6);
        ctx.fill();

        // Border - F_i RATING COLOR (color temperature gradient)
        // Simulate rating progress if not connected to SSE
        if (!FLAGS.USE_SIM_EVENTS || !simBridge.connected) {
            const totalBlocks = Math.pow(CONFIG.targetSize, 3);
            const progress = filledBlocks.size / totalBlocks;
            fiRating.simulateProgress(currentPhase, progress);
            cabrScore.simulateProgress(currentPhase, progress);
        }

        const borderColor = fiRating.borderColor;
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = 2;  // F_i rating border color
        ctx.roundRect(keyX - 8, keyY - 12, keyW, keyH, 6);
        ctx.stroke();

        // F_i Rating label (color speaks for itself - no need to state tier name)
        ctx.font = 'bold 8px monospace';
        ctx.fillStyle = borderColor;  // Color shows the tier
        ctx.textAlign = 'right';
        ctx.fillText('Fᵢ Rating', keyX + keyW - 16, keyY - 2);

        // Count agents by type (live)
        const agentCounts = { founder: 0, builder: 0, promoter: 0, staker: 0 };
        agents.forEach(a => { if (agentCounts.hasOwnProperty(a.type)) agentCounts[a.type]++; });
        const totalAgents = agentCounts.founder + agentCounts.builder + agentCounts.promoter + agentCounts.staker;

        // Agent legend header with total count
        const divY = keyY + 8;
        ctx.font = '9px monospace';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.textAlign = 'left';
        ctx.fillText('AGENTS', keyX, divY);
        // Total count — right-aligned
        ctx.font = 'bold 9px monospace';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.textAlign = 'right';
        ctx.fillText(totalAgents, keyX + keyW - 16, divY);

        const legend = [
            { label: 'Founder', color: STYLE.agentColors.founder, key: 'founder' },
            { label: 'Builder', color: STYLE.agentColors.builder, key: 'builder' },
            { label: 'Promoter', color: STYLE.agentColors.promoter, key: 'promoter' },
            { label: 'Staker', color: STYLE.agentColors.staker, key: 'staker' },
        ];

        legend.forEach((item, i) => {
            const ly = divY + 18 + i * 17;
            ctx.beginPath();
            ctx.arc(keyX + 4, ly - 3, 4, 0, Math.PI * 2);
            ctx.fillStyle = item.color;
            ctx.fill();
            ctx.font = '9px monospace';
            ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
            ctx.textAlign = 'left';
            ctx.fillText(item.label, keyX + 14, ly);
            // Dynamic count — right-aligned
            const count = agentCounts[item.key] || 0;
            ctx.font = 'bold 9px monospace';
            ctx.fillStyle = item.color;
            ctx.textAlign = 'right';
            ctx.fillText(count, keyX + keyW - 16, ly);
        });

        // CABR Score display (below agents)
        const cabrY = divY + 18 + legend.length * 17 + 8;
        ctx.font = '8px monospace';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.textAlign = 'left';
        ctx.fillText('CABR', keyX, cabrY);

        // CABR total with threshold indicator
        const cabrColor = cabrScore.getColor();
        const cabrIcon = cabrScore.threshold_met ? '\u2713' : '\u2717';  // checkmark or X
        ctx.font = 'bold 10px monospace';
        ctx.fillStyle = cabrColor;
        ctx.textAlign = 'right';
        ctx.fillText(`${cabrScore.total.toFixed(2)} ${cabrIcon}`, keyX + keyW - 16, cabrY);

        // OPO Gate Status (Pre-OPO = invite only, Post-OPO = public)
        const gateY = cabrY + 18;
        ctx.font = '8px monospace';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.textAlign = 'left';
        ctx.fillText('GATE', keyX, gateY);

        const preOpo = isPreOPO();
        const gateColor = preOpo ? '#ff8c00' : '#22c55e';  // orange = locked, green = open
        const gateText = preOpo ? 'PRE-OPO' : 'POST-OPO';
        const gateIcon = preOpo ? '\u{1F512}' : '\u{1F513}';  // lock emoji / unlock emoji
        ctx.font = 'bold 9px monospace';
        ctx.fillStyle = gateColor;
        ctx.textAlign = 'right';
        ctx.fillText(`${gateText} ${gateIcon}`, keyX + keyW - 16, gateY);

        ctx.restore();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // ANIMATION LOOP
    // ═══════════════════════════════════════════════════════════════════════
    function animate() {
        ctx.clearRect(0, 0, w, h);
        time += 0.016;

        updatePhase();
        updateAgents();
        updateAgentBehaviors();
        updateParticles();
        updateConfetti();
        updateEarningPulses();
        updateTicker();
        updateCamera();

        // Spawn agents during building
        if (currentPhase === 'BUILDING' && Math.random() < CONFIG.agentSpawnRate * speedMultiplier && agents.length < CONFIG.maxAgents) {
            const statuses = ['building...', 'coding...', 'testing...', 'designing...'];
            spawnAgent('builder', statuses[Math.floor(Math.random() * statuses.length)]);
        }

        // Progressive block filling during BUILDING - ensures cube fills up over time
        if (currentPhase === 'BUILDING') {
            const elapsed = getScaledElapsed(phaseStartTime);
            const buildDuration = PHASES.BUILDING.duration;
            const progress = elapsed / buildDuration;  // 0 to 1
            const totalBlocks = Math.pow(CONFIG.targetSize, 3);  // 64 blocks
            const targetFilled = Math.floor(progress * totalBlocks * 0.85);  // 85% filled by end of BUILDING

            // Fill blocks to match target progress (smooth filling)
            while (filledBlocks.size < targetFilled && filledBlocks.size < totalBlocks) {
                fillRandomBlock();
            }
        }

        // Check if in ecosystem view (far zoom)
        if (isEcosystemView()) {
            // Far zoom: show ecosystem with multiple mini-cubes
            // HIDE ticker when zoomed out - let people see all the models
            drawEcosystemView();
            drawStatusBar();  // Keep status bar visible
        } else {
            // Normal view: single cube with agents
            // Draw ticker FIRST - behind cube, blends with background
            drawTicker();

            drawCube();
            drawParticles();
            drawEarningPulses();  // $ earning indicators around cube
            drawAgents();
            drawConfetti();
            drawStatusBar();
            drawCubeScaffoldingText();  // Activity text floats to RIGHT of cube (free space)
            drawColorKey();  // Bottom-right key with F_i rating border color (AGENTS only)

            // Draw mini-cubes in zoomed-out mode (Phase 3 - legacy)
            if (cameraHandoff.zoomedOut && cameraHandoff.cubePositions.length > 0) {
                drawMiniCubes();
            }

            // Agent tooltip on top of everything
            drawAgentTooltip();
        }

        animationFrameId = requestAnimationFrame(animate);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════════════════════
    function init(canvasId, options = {}) {
        if (initializedCanvasId === canvasId && apiHandle) {
            return apiHandle;
        }

        // If previously initialized on a different canvas, tear down cleanly first.
        if (initializedCanvasId && initializedCanvasId !== canvasId) {
            if (animationFrameId !== null) {
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }
            if (resizeHandler) {
                window.removeEventListener('resize', resizeHandler);
                resizeHandler = null;
            }
            if (simBridge.eventSource) {
                simBridge.eventSource.close();
                simBridge.eventSource = null;
                simBridge.connected = false;
            }
        }

        canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`FoundupCube: Canvas #${canvasId} not found`);
            return null;
        }

        canvas.dataset.foundupInit = 'true';
        initializedCanvasId = canvasId;

        // Apply options
        if (options.useSimEvents !== undefined) FLAGS.USE_SIM_EVENTS = options.useSimEvents;
        if (options.debugTiming !== undefined) FLAGS.DEBUG_TIMING = options.debugTiming;
        if (options.multiCube !== undefined) FLAGS.MULTI_CUBE = options.multiCube;
        if (options.simEndpoint) simBridge.endpoint = options.simEndpoint;

        ctx = canvas.getContext('2d');

        resizeHandler = function resize() {
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            w = rect.width;
            h = rect.height;
            canvas.width = w * dpr;
            canvas.height = h * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };

        window.addEventListener('resize', resizeHandler);
        resizeHandler();

        // ═══════════════════════════════════════════════════════════════════
        // MOUSE INTERACTION HANDLERS
        // ═══════════════════════════════════════════════════════════════════
        canvas.addEventListener('mouseenter', () => { mouse.isOverCanvas = true; });
        canvas.addEventListener('mouseleave', () => {
            mouse.isOverCanvas = false;
            mouse.isDown = false;
            mouse.isDragging = false;
        });

        canvas.addEventListener('mousedown', (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.isDown = true;
            mouse.startX = e.clientX - rect.left;
            mouse.startY = e.clientY - rect.top;
            mouse.x = mouse.startX;
            mouse.y = mouse.startY;
        });

        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;

            if (mouse.isDown) {
                const dx = mouse.x - mouse.startX;
                const dy = mouse.y - mouse.startY;
                if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                    mouse.isDragging = true;
                    cubeRotation.targetY = dx * 0.005;
                    cubeRotation.targetX = dy * 0.005;
                }
            }

            // Hover detection for agents
            const scaleRatio = camera.scale / STYLE.camera.defaultScale;
            const cubeCenterH = { x: w / 2, y: h * 0.45 };
            const hitRadius = scaleRatio < 0.7 ? 10 : 20;
            let found = null;
            for (const a of agents) {
                const relX = a.x - cubeCenterH.x;
                const relY = a.y - cubeCenterH.y;
                const drawX = cubeCenterH.x + relX * scaleRatio;
                const drawY = cubeCenterH.y + relY * scaleRatio;
                const dx = drawX - mouse.x;
                const dy = drawY - mouse.y;
                if (Math.sqrt(dx * dx + dy * dy) < hitRadius) {
                    found = a;
                    break;
                }
            }
            mouse.hoveredAgent = found;
            canvas.style.cursor = found ? 'pointer' : 'default';
        });

        canvas.addEventListener('mouseup', (e) => {
            if (!mouse.isDragging) {
                // It was a click, not a drag - check for agent clicks
                handleAgentClick(mouse.x, mouse.y);
            }
            mouse.isDown = false;
            mouse.isDragging = false;
            // Gradually reset rotation
            cubeRotation.targetX = 0;
            cubeRotation.targetY = 0;
        });

        // Scroll wheel: zoom OR speed (shift+wheel)
        // UP (negative deltaY) = zoom IN / speed UP
        // DOWN (positive deltaY) = zoom OUT / speed DOWN
        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();

            if (e.shiftKey) {
                // SHIFT + wheel = adjust simulation speed
                const speedDelta = e.deltaY > 0 ? -0.25 : 0.25;
                speedMultiplier = Math.max(0.25, Math.min(5.0, speedMultiplier + speedDelta));
                // Update slider if exists
                const slider = document.getElementById('speedSlider');
                const valueEl = document.getElementById('speedValue');
                if (slider) slider.value = speedMultiplier;
                if (valueEl) valueEl.textContent = speedMultiplier.toFixed(1) + 'x';
                console.log(`Speed: ${speedMultiplier.toFixed(1)}x (shift+wheel)`);
            } else {
                // Normal wheel = zoom
                const direction = e.deltaY > 0 ? -1 : 1;  // DOWN=out(-1), UP=in(+1)
                const zoomStep = 0.5;  // Fixed step size
                camera.targetScale = Math.max(STYLE.camera.minScale, Math.min(STYLE.camera.maxScale, camera.targetScale + direction * zoomStep));
                console.log(`Zoom: deltaY=${e.deltaY}, dir=${direction}, scale=${camera.targetScale.toFixed(1)}`);
            }
        }, { passive: false });

        // Double-click resets zoom to default
        canvas.addEventListener('dblclick', (e) => {
            e.preventDefault();
            camera.targetScale = STYLE.camera.defaultScale;  // Reset to 15
            console.log('Zoom reset to default:', STYLE.camera.defaultScale);
        });

        // ═══════════════════════════════════════════════════════════════════
        // TOUCH EVENT HANDLERS (iPhone/mobile support)
        // ═══════════════════════════════════════════════════════════════════
        let touchStartDistance = 0;  // For pinch-to-zoom

        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            if (e.touches.length === 1) {
                // Single touch - rotate
                const touch = e.touches[0];
                mouse.isDown = true;
                mouse.startX = touch.clientX - rect.left;
                mouse.startY = touch.clientY - rect.top;
                mouse.x = mouse.startX;
                mouse.y = mouse.startY;
            } else if (e.touches.length === 2) {
                // Two fingers - pinch to zoom
                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                touchStartDistance = Math.sqrt(dx * dx + dy * dy);
            }
        }, { passive: false });

        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            if (e.touches.length === 1 && mouse.isDown) {
                // Single touch drag - rotate cube
                const touch = e.touches[0];
                mouse.x = touch.clientX - rect.left;
                mouse.y = touch.clientY - rect.top;

                const dx = mouse.x - mouse.startX;
                const dy = mouse.y - mouse.startY;
                if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                    mouse.isDragging = true;
                    cubeRotation.targetY = dx * 0.008;  // Slightly more sensitive for touch
                    cubeRotation.targetX = dy * 0.008;
                }
            } else if (e.touches.length === 2) {
                // Pinch to zoom
                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                const distance = Math.sqrt(dx * dx + dy * dy);
                if (touchStartDistance > 0) {
                    const scale = distance / touchStartDistance;
                    camera.targetScale = Math.max(STYLE.camera.minScale, Math.min(STYLE.camera.maxScale, camera.scale * scale));
                    touchStartDistance = distance;  // Update for continuous zoom
                }
            }
        }, { passive: false });

        canvas.addEventListener('touchend', (e) => {
            if (e.touches.length === 0) {
                if (!mouse.isDragging && mouse.isDown) {
                    // It was a tap, not a drag - check for agent taps
                    handleAgentClick(mouse.x, mouse.y);
                }
                mouse.isDown = false;
                mouse.isDragging = false;
                // Gradually reset rotation
                cubeRotation.targetX = 0;
                cubeRotation.targetY = 0;
                touchStartDistance = 0;
            }
        }, { passive: false });

        // ═══════════════════════════════════════════════════════════════════
        // SPEED SLIDER
        // ═══════════════════════════════════════════════════════════════════
        const speedSlider = document.getElementById('speedSlider');
        const speedValueEl = document.getElementById('speedValue');
        if (speedSlider) {
            speedSlider.addEventListener('input', (e) => {
                speedMultiplier = parseFloat(e.target.value);
                if (speedValueEl) speedValueEl.textContent = speedMultiplier + 'x';
            });
        }

        // ═══════════════════════════════════════════════════════════════════
        // ZOOM SLIDER
        // ═══════════════════════════════════════════════════════════════════
        const zoomSlider = document.getElementById('zoomSlider');
        const zoomValueEl = document.getElementById('zoomValue');

        function syncZoomSlider() {
            if (zoomSlider) zoomSlider.value = camera.targetScale;
            if (zoomValueEl) {
                const zoomRatio = (camera.targetScale / STYLE.camera.defaultScale).toFixed(1);
                zoomValueEl.textContent = zoomRatio + 'x';
            }
        }

        if (zoomSlider) {
            zoomSlider.addEventListener('input', (e) => {
                camera.targetScale = parseFloat(e.target.value);
                syncZoomSlider();
            });
        }

        // Patch wheel handler to sync zoom slider
        const origWheelSync = () => syncZoomSlider();
        canvas.addEventListener('wheel', origWheelSync, { passive: true });

        // Start
        loopStartTime = Date.now();
        phaseStartTime = Date.now();
        onPhaseChange('IDEA');

        // Connect simulator bridge if enabled
        if (FLAGS.USE_SIM_EVENTS) {
            connectSimulatorBridge();
        }

        animate();
        console.log('FoundupCube initialized (120s loop, Phase 1)');

        apiHandle = {
            subscribe: (fn) => { eventSubscribers.push(fn); },
            unsubscribe: (fn) => {
                const idx = eventSubscribers.indexOf(fn);
                if (idx !== -1) eventSubscribers.splice(idx, 1);
            },
            getState: () => ({
                phase: currentPhase,
                loopCount,
                agents: agents.length,
                blocks: filledBlocks.size,
                fiEarned,
            }),
            destroy: () => {
                if (animationFrameId !== null) {
                    cancelAnimationFrame(animationFrameId);
                    animationFrameId = null;
                }
                if (resizeHandler) {
                    window.removeEventListener('resize', resizeHandler);
                    resizeHandler = null;
                }
                if (simBridge.eventSource) {
                    simBridge.eventSource.close();
                    simBridge.eventSource = null;
                    simBridge.connected = false;
                }
                initializedCanvasId = null;
                apiHandle = null;
                if (canvas) {
                    delete canvas.dataset.foundupInit;
                }
            },
        };
        return apiHandle;
    }

    // Set Firestore instance (call from index.html after Firebase init)
    function setFirestore(db) {
        firestoreBridge.init(db);
    }

    // Get session stats
    function getSessionStats() {
        return {
            sessionId: firestoreBridge.sessionId,
            loopCount: firestoreBridge.loopCount,
            totalFiEarned: firestoreBridge.totalFiEarned,
            eventsWritten: firestoreBridge.eventsWritten,
        };
    }

    function setSpeed(multiplier) {
        speedMultiplier = Math.max(0.25, Math.min(5, multiplier));
        const slider = document.getElementById('speedSlider');
        const label = document.getElementById('speedValue');
        if (slider) slider.value = speedMultiplier;
        if (label) label.textContent = speedMultiplier + 'x';
    }

    // ═══════════════════════════════════════════════════════════════════════
    // COMMAND API - Direct control interface for simulator integration
    // Usage: FoundupCube.command('setPhase', { phase: 'BUILDING' })
    // ═══════════════════════════════════════════════════════════════════════
    function command(action, params = {}) {
        switch (action) {
            case 'setPhase':
                return setPhase(params.phase, { force: params.force });

            case 'enableDrivenMode':
                FLAGS.DRIVEN_MODE = true;
                console.log('[CUBE] DRIVEN_MODE enabled - animation controlled by simulator');
                return true;

            case 'disableDrivenMode':
                FLAGS.DRIVEN_MODE = false;
                console.log('[CUBE] DRIVEN_MODE disabled - animation uses internal timer');
                return true;

            case 'stateSync':
                handleStateSync(params);
                return true;

            case 'fillBlocks':
                const count = params.count || 1;
                for (let i = 0; i < count; i++) {
                    fillRandomBlock();
                }
                return filledBlocks.size;

            case 'spawnAgent':
                const agent = spawnAgent(params.type || 'builder', params.status || '');
                return agent ? agent.id : null;

            case 'addTickerMessage':
                addTickerMessage(params.type || 'info', params.data || {});
                return true;

            case 'getState':
                return {
                    phase: currentPhase,
                    filledBlocks: filledBlocks.size,
                    totalBlocks: Math.pow(CONFIG.targetSize, 3),
                    agentCount: agents.length,
                    loopCount: loopCount,
                    fiEarned: fiEarned,
                    drivenMode: FLAGS.DRIVEN_MODE,
                    lifecycleStage: getLifecycleStage(),
                };

            case 'reset':
                onPhaseChange('IDEA');
                return true;

            default:
                console.warn(`[CUBE] Unknown command: ${action}`);
                return false;
        }
    }

    return { init, setFirestore, setSpeed, getSessionStats, command, STYLE, FLAGS };
})();

// Auto-init if buildCanvas exists
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        const canvas = document.getElementById('buildCanvas');
        if (canvas && !canvas.dataset.foundupInit) {
            canvas.dataset.foundupInit = 'true';
            FoundupCube.init('buildCanvas');
        }
    });
}
