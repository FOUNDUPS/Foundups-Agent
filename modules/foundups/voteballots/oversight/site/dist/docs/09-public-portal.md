# Section IX — House-First PWA and Public Portal

## Public information architecture

The portal starts with three clickable institutional steps for a House representative: Prepare the House; Build the central hub; Connect state enforcement. Rules and hiring come first, with clear access to supporting sources and the complete manual. It separates proposed procedures from legal authorities and reviewed research findings. Its primary navigation is the manual's chapters, the typology explorer, model instruments, state-jurisdiction analysis, contribution guide, and implementation roadmap. Search operates on locally generated chapter data; it does not send a visitor's queries to an analytics service.

The typology explorer organizes emoluments-related transactions, corporate ownership, crypto flows and state jurisdiction as methods. Its categories are questions to investigate, not classifications of people as offenders. Each method directs the reader to its source standards, uncertainty controls and applicable legal chapter. The state-hook database is the detailed state matrix in Section III; each entry includes an actual statute, relevant elements, jurisdictional requirements and limitations. Converting that matrix into a filterable database is a later enhancement that must preserve the legal qualifications attached to every entry.

The downloadable instruments include the full proposed House rules resolution, legislative-purpose memorandum, third-party rider and referral dossier. All are marked as models requiring matter-specific adoption or completion by competent officials. The website must not expose a button that appears to issue a subpoena, submit an official state referral, grant immunity, or certify a legal violation.

## Data and graph model

The graph compiles only public packets whose exact bytes match a trusted approval entry after legal and privacy review and after the publication policy is explicitly enabled. Entity IDs are scoped to packets unless a separately reviewed cross-packet resolution establishes identity. Labels distinguish persons, organizations, government bodies, accounts, wallets, property, documents and law. An ownership edge must identify the relevant time and basis for ownership; it must not silently turn a registered-agent relationship into beneficial ownership.

Every edge references claim IDs, and every claim references source IDs with pinpoints. Fact, allegation, inference and unknown remain distinct. A graph visualization is a navigation aid, not a finding of liability. Missing edges do not establish that no relationship exists; dense edges do not establish a conspiracy. The interface must preserve limitations and allow a reader to reach the underlying packet and original source. Negative and disconfirming evidence should be as discoverable as supportive evidence.

The generated findings dataset is intentionally empty: no approved factual investigative packets exist in this release. The current House-first PWA does not render an investigative graph; the reviewed graph and public-referral tracker are later roadmap features. The constitutional-text example is outside the submission folder and is not automatically published as a finding. `data/referrals.json` is empty. A future status tracker may display only an authorized, sourced public event such as a published committee referral and an agency's actual public response. Submission, receipt, acknowledgment, investigative action and adjudication are different statuses. Silence is not confirmation, and this project must not imply that an agency has opened an investigation without a reliable public basis.

## Build and deployment

`python scripts/build_site.py` reads the exact-path-and-digest publication manifest, rejects symlinks and path escapes, verifies source file bytes, converts approved chapters to escaped HTML, copies explicitly approved downloads, and writes the search index and reviewed graph data. A newly added file does not appear simply because it is present somewhere under a public-looking folder. Publication-manifest changes need independent review just like changes to legal text and executable code.

The generated site is a set of static files. It works on GitHub Pages and ordinary static hosting without a server, user accounts, financial integrations, external JavaScript libraries or a graph database. The chapter search uses DOM text operations for retrieved titles and avoids executing source content as HTML. A future graph renderer must preserve this boundary. The content-security policy restricts scripts and styles to same-origin assets. Human review of private information remains necessary: escaping prevents a class of code injection, not unwanted disclosure.

The Pages workflow builds from main and publishes through the github-pages environment. Manual dispatch is also restricted to main. GitHub repository administration must set the Pages source, branch protections, reviewers and deployment rules; these settings are not created by merely including workflow files. The owner-private House-first prototype is deployed at https://oversight-hub-pwa.undaodu.chatgpt.site . This is separate from public distribution, official institutional adoption or a live research API.

## Accessibility and reader trust

Use semantic headings, keyboard-reachable controls, readable contrast, responsive single-column layouts and horizontal scrolling for wide legal tables. Graph nodes must have accessible labels and a text detail view; an accessible tabular packet view is required before substantial live graph publication. Never convey allegation status solely through color. Downloaded legal instruments should retain the version and research cutoff. Show correction notices near affected material and preserve release history.

The current portal supplies the three-step House flow, rules/hiring/readiness checklists, chapter search, responsive documentation, downloadable source assets, prepared-document status and native Google Docs links, an application manifest and a public-method shell cache. It provides no confidential intake, live task API or current graph display. Later milestones add a filterable statute database, individual claim pages, cross-packet entity review, a public corrections interface, and a referral-status tracker based solely on authorized published records. Those features are roadmap items, not functioning services in this release.

## Tips and contributions

The public guide requests primary-source citations and bounded research questions. It expressly forbids uploading confidential tax information, SARs, sealed court records, private account identifiers, credentials, nonpublic witness contacts or materials obtained by unlawful access. GitHub and social channels are not confidential tip channels and do not offer source-protection guarantees. A dedicated sensitive-tip system would require separate legal design, threat modeling, secure operations, retention decisions and a real responsible organization before being advertised.

Journalists, researchers, legal scholars and watchdogs may identify a methodological error, propose a verified statutory correction, submit an appropriately redacted public record, or review a research claim. The project does not assign surveillance, pressure campaigns, harassment or autonomous contact with people named in a task. A contributor's local agent has only the authority the contributor actually possesses and has lawfully delegated.

## Acceptance criteria

The portal build must fail on a publication-manifest mismatch or symlink; unapproved or changed packet bytes must remain absent from findings; search must navigate to the correct chapter; downloaded templates must match their source digests; arbitrary source text must be escaped; no site script should request a credential; graph labels must remain text; and an empty approved-packet set must show a truthful empty state. Production deployment additionally requires independent review of permissions, actual source checks, correction procedures and the ability to suspend publication quickly.
