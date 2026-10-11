## Priority direction — Play FoundUps convergence (2026-10-12)

- [ ] Execute the staged [Mall migration handoff](PFMALL_MIGRATION_HANDOFF.md).
- [ ] Make Mall the canonical internal listing discovery/search surface.
- [ ] Verify shared media, listing and identity owners with Shop/GetK before provider changes.
- [ ] Preserve existing records, offline captures and security controls through audited cutover.

Earlier standalone roadmap items below are historical context and must be reconciled with this direction.

# GotJUNK? FoundUp - Development Roadmap

## Phase 1: PoC (COMPLETE ✅)

**Status**: Deployed to Cloud Run via AI Studio
**Duration**: Initial build
**Goal**: Validate core concept - rapid photo capture with swipe organization

### Features Delivered
- [x] Photo capture with camera API
- [x] Geolocation tagging (GPS coordinates)
- [x] 50km radius geo-filtering
- [x] Swipe interface (keep/delete)
- [x] Local storage (IndexedDB via localforage)
- [x] PWA manifest (installable app)
- [x] Service worker (offline support)
- [x] Video capture with countdown
- [x] Export functionality
- [x] Cloud Run deployment
- [x] AI Studio integration

### Technical Achievements
- React 19 + TypeScript foundation
- Vite build pipeline
- Framer Motion animations
- Gemini AI SDK integration
- Progressive Web App capabilities
- Haversine distance calculations

### Deployment
- ✅ Google AI Studio project created
- ✅ One-click Cloud Run deployment
- ✅ HTTPS endpoint active
- ✅ Auto-scaling configured

---

## Phase 2: Prototype (CURRENT 🚧)

**Status**: In Progress
**Duration**: 2-4 weeks
**Goal**: Add AI-powered organization and enhanced UX

### Priority Features

#### AI Integration (P0)
- [ ] Gemini Vision API for image analysis
- [ ] **AI-Powered Pricing Workflow** (Core Feature)
  - [ ] User snaps photo of item
  - [ ] Gemini Vision analyzes item (brand, condition, market value)
  - [ ] Three pricing options presented:
    - [ ] **FREE** - Give away (charity/friends)
    - [ ] **75% DISCOUNT** (default) - Quick sale price
    - [ ] **AUCTION** (default 75hr countdown) - Maximum value
  - [ ] AI suggests price based on:
    - [ ] Item category and condition
    - [ ] Local market data (if available)
    - [ ] Similar item comparisons
- [ ] **Voice Chat About Items**
  - [ ] User can talk to AI about item history/story
  - [ ] AI asks clarifying questions (age, condition, sentimental value)
  - [ ] Conversation influences pricing suggestion
  - [ ] Uses Gemini multimodal (voice + vision + text)
- [ ] Auto-categorization of captured items
  - [ ] Junk vs. Keep vs. Sell suggestions
  - [ ] Category labels (furniture, electronics, documents, etc.)
  - [ ] Confidence scores
- [ ] Smart batch operations
  - [ ] "Price all items" action
  - [ ] "Export sellable items" action
  - [ ] Category-based pricing profiles

#### Enhanced Export (P0)
- [ ] ZIP export with metadata JSON
- [ ] Include geolocation in export
- [ ] Timestamp and category data
- [ ] Optional image compression
- [ ] Export statistics (kept vs. deleted)

#### UX Improvements (P1)
- [ ] Undo swipe decision
- [ ] Batch selection mode
- [ ] Search/filter captured items
- [ ] Sort by date/location/category
- [ ] Gallery view enhancements
- [ ] Loading states and skeleton screens

#### Performance (P1)
- [ ] Image lazy loading optimization
- [ ] Virtual scrolling for large galleries
- [ ] Web Worker for heavy processing
- [ ] IndexedDB query optimization
- [ ] Reduce bundle size (tree shaking)

#### Testing (P2)
- [ ] E2E tests (Playwright)
- [ ] Unit tests for utilities
- [ ] Geolocation mocking for tests
- [ ] Camera API mocking for tests
- [ ] CI/CD pipeline

### Technical Debt
- [ ] Error boundary implementation
- [ ] Proper loading states
- [ ] Network error handling
- [ ] Storage quota monitoring
- [ ] Type safety improvements

### Deployment Updates
- [ ] Environment variable management
- [ ] Deployment automation script
- [ ] Cloud Run monitoring setup
- [ ] Performance metrics tracking

---

## Phase 3: MVP (PLANNED 📋)

**Status**: Not Started
**Duration**: 4-6 weeks
**Goal**: Production-ready app with cloud sync and monetization

### User Features

#### Authentication & Cloud Sync (P0)
- [ ] User authentication (Firebase Auth or Supabase)
- [ ] Cloud storage integration
- [ ] Multi-device sync
- [ ] Cross-device geofencing
- [ ] Conflict resolution

#### Wave-Style Messaging (P0) ✅
Internal messaging module: `frontend/src/message/`
- [x] **M1**: IndexedDB persistence (localforage)
- [x] **M2**: Firestore cloud sync (cross-device)
- [x] **M3**: Real-time updates (onSnapshot)
- [x] **M4**: Liberty Alert integration
- [x] **M5**: Thread auto-close on purchase/skip
- [x] **M6**: Unread badge on PhotoGrid cards

#### Collaboration (P1)
- [ ] Share captures with others
- [ ] Collaborative organization
- [ ] Public/private captures
- [x] Comments on items (via Wave messaging)
- [ ] Activity feed

#### Advanced AI (P1)
- [ ] Natural language search
  - "Show me all furniture from last week"
  - "Find items near my home"
- [ ] Duplicate detection
- [ ] Similar item clustering
- [ ] Smart albums (AI-generated)

#### Monetization (P2)
- [ ] Free tier (100 items/month)
- [ ] Premium tier (unlimited + cloud sync)
- [ ] Storage quota management
- [ ] Billing integration
- [ ] Usage analytics dashboard

### Platform Features

#### Admin & Analytics (P1)
- [ ] User dashboard
- [ ] Usage statistics
- [ ] Error tracking (Sentry)
- [ ] A/B testing framework
- [ ] Feature flags

#### Infrastructure (P1)
- [ ] Database migration (PostgreSQL)
- [ ] Redis caching
- [ ] CDN for static assets
- [ ] Rate limiting
- [ ] API versioning

#### Integrations (P2)
- [ ] Google Photos export
- [ ] Dropbox integration
- [ ] Calendar integration (location history)
- [ ] Social sharing (Twitter, Facebook)

### Quality Assurance
- [ ] Comprehensive test coverage (>90%)
- [ ] Load testing (1000+ concurrent users)
- [ ] Security audit
- [ ] WCAG 2.1 AA accessibility compliance
- [ ] GDPR compliance
- [ ] Privacy policy & terms of service

### Deployment
- [ ] Production-grade Cloud Run config
- [ ] Multi-region deployment
- [ ] Disaster recovery plan
- [ ] Automated backups
- [ ] Blue-green deployments

---

## Future Enhancements (Backlog)

### Advanced Features
- [ ] AR preview mode (place furniture in room)
- [ ] ML model fine-tuning on user data
- [ ] Voice commands
- [ ] OCR for text extraction
- [ ] Barcode/QR code scanning
- [ ] Integration with donation platforms

### Platform Expansion
- [ ] Native mobile apps (React Native)
- [ ] Browser extension
- [ ] Desktop app (Electron)
- [ ] API for third-party integrations
- [ ] Webhook support

### AI Enhancements
- [ ] Custom AI models per user
- [ ] Sentiment analysis
- [ ] Predictive organization
- [ ] Automated workflows
- [ ] Smart reminders

---

## WSP Compliance Roadmap

### PoC → Prototype
- [x] WSP 3: Domain organization
- [x] WSP 49: Module structure
- [x] WSP 22: Documentation
- [ ] WSP 5: Test coverage ≥90%
- [ ] WSP 6: Test audit reports

### Prototype → MVP
- [ ] WSP 11: Interface protocol
- [ ] WSP 71: Secrets management
- [ ] WSP 89: Production deployment
- [ ] WSP 60: Module memory
- [ ] WSP 91: Observability

### MVP → Production
- [ ] WSP 78: Database scaling
- [ ] WSP 68: Build scalability
- [ ] WSP 59: Distributed development
- [ ] WSP 42: Universal platform protocol

---

## Metrics & Success Criteria

### PoC Success (ACHIEVED ✅)
- ✅ App deployable to Cloud Run
- ✅ Core swipe interface functional
- ✅ Geo-filtering accurate
- ✅ PWA installable on mobile
- ✅ <2s page load time

### Prototype Success (In Progress)
- [ ] AI categorization >85% accuracy
- [ ] Export with metadata functional
- [ ] Test coverage >70%
- [ ] <1.5s page load time
- [ ] 10+ beta users with positive feedback

### MVP Success (Planned)
- [ ] 100+ active users
- [ ] Cloud sync 99.9% uptime
- [ ] Test coverage >90%
- [ ] <1s page load time
- [ ] <1% error rate
- [ ] Positive revenue from premium tier

---

**Current Phase**: Prototype 🚧
**Next Milestone**: AI Integration + Enhanced Export
**Estimated Completion**: [TBD based on resource availability]

For detailed implementation, see [README.md](README.md) and [INTERFACE.md](INTERFACE.md).
