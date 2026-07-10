# ArenaPulse — AI Operations & Fan Copilot for FIFA World Cup 2026
### Complete A-Z Build Plan | Challenge 4: Smart Stadiums & Tournament Operations

---

## 0. Positioning Strategy (read this first)

The eval weights tell you exactly where to spend your 2-4 weeks:

| Parameter | Impact | What it actually rewards |
|---|---|---|
| Problem Statement Alignment | **High** | Solving the *real* multi-stakeholder problem, not a narrow slice. Judges will check: does this work for fans AND organizers AND volunteers? Does GenAI actually drive decisions, or is it decoration? |
| Code Quality | **High** | Clean layering, typed code, small functions, no god-files, meaningful commit history, README that lets a stranger run it in 5 min |
| Security | Medium | Auth, secrets handling, input validation, no prompt-injection holes |
| Efficiency | Medium | Caching, async, model-routing (cheap model for easy tasks), no wasteful LLM calls |
| Testing | Medium | Real pytest suite with mocked LLM calls, not just a couple of smoke tests |
| Accessibility | Low-Medium (but needed for a perfect score) | WCAG-compliant UI, multilingual, voice, offline-degradation |

**Strategy: build fewer features, deeper.** A judge scanning 100+ submissions in a hackathon will reward a system that clearly *reasons* (shows its work, has a knowledge graph, has an audit trail) over one that has 8 shallow features. Depth on High-Impact criteria wins; breadth only matters enough to hit every bullet in the problem statement at least once.

---

## 1. The Concept: "ArenaPulse"

**One-liner:** ArenaPulse is a multi-agent GenAI operations layer that sits between a stadium's real-time sensor/ops data and three groups of people — **fans**, **volunteers**, and **organizers/control-room staff** — turning raw signals into multilingual guidance for fans and prioritized, explainable action recommendations for staff, in real time, during FIFA World Cup 2026 matches.

Why this framing wins on "Problem Statement Alignment": the brief lists 8 possible focus areas (navigation, crowd mgmt, accessibility, transport, sustainability, multilingual, ops intelligence, real-time decision support). Instead of picking one, ArenaPulse treats them as **outputs of a single knowledge graph + agent pipeline**, so you genuinely hit all 8 without building 8 separate mini-apps.

**Grounding in reality (cite this in your submission):** WC26 spans 16 stadiums across the US, Mexico and Canada, hosts 48 teams and 104 matches, and is expected to break the all-time cumulative attendance record of 3.5M set in 1994 — meaning multilingual, high-density crowd support isn't a hypothetical, it's the tournament's single biggest operational challenge. Design your demo around a specific real venue, e.g. **AT&T Stadium, Dallas** (~92,967 tournament capacity, hosting a semi-final) — using a real seating/gate layout makes your knowledge graph and demo far more credible than a generic "Stadium A."

---

## 2. Personas (design against these explicitly — mention them in your README)

1. **Fan (Maria, Mexico City, group-stage traveler in Dallas)** — doesn't speak English well, needs wayfinding, nearest accessible restroom, transit info, and reassurance during a crowd surge.
2. **Volunteer (steward at Gate C)** — not a data analyst, needs a single plain-language instruction ("Redirect Gate C queue to Gate D, congestion rising"), not a raw dashboard.
3. **Control-room organizer** — needs an aggregated, explainable view: what's happening, why the system flagged it, what it recommends, and one-click approve/override.
4. **Accessibility-needs fan (wheelchair user, deaf/hard-of-hearing fan)** — needs routing that respects step-free paths, captioned/visual alerts instead of audio-only.

---

## 3. System Architecture

```
                         ┌───────────────────────────┐
                         │   Synthetic Data Layer     │
                         │ (crowd density, transit,   │
                         │  weather, gate sensors)     │
                         └─────────────┬─────────────┘
                                       │ WebSocket / REST (streamed)
                         ┌─────────────▼─────────────┐
                         │      FastAPI Backend        │
                         │  (async, typed, layered)     │
                         └─────────────┬─────────────┘
              ┌────────────┬───────────┼───────────┬────────────┐
              ▼            ▼           ▼           ▼            ▼
     ┌────────────┐ ┌────────────┐ ┌─────────┐ ┌─────────┐ ┌────────────┐
     │ Navigator  │ │  Crowd     │ │Concierge│ │Sustain- │ │ Ops        │
     │ Agent      │ │  Sentinel  │ │ Agent   │ │ ability │ │ Commander  │
     │(routing +  │ │  Agent     │ │(multi-  │ │ Agent   │ │ Agent      │
     │ GenAI      │ │(anomaly +  │ │ lingual │ │(transit/│ │(aggregates │
     │ explain)   │ │ forecast)  │ │ chat/   │ │ waste   │ │ all agents,│
     │            │ │            │ │ voice)  │ │ tips)   │ │ prioritizes│
     └─────┬──────┘ └─────┬──────┘ └────┬────┘ └────┬────┘ │ actions)   │
           │              │             │           │      └─────┬──────┘
           └──────────────┴─────────────┴───────────┴────────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │   Neo4j Knowledge Graph     │
                         │ (gates, zones, exits, medical│
                         │  points, capacities, routes) │
                         └─────────────┬─────────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │  PostgreSQL (logs, users,   │
                         │  incidents, audit trail)     │
                         └───────────────────────────┘

        Frontend: React PWA (Fan app) + React Ops Dashboard (staff)
```

Why a knowledge graph (not just RAG over documents) is your standout move: stadium navigation and accessibility are inherently **graph problems** (gates→sections→exits→medical points, with capacity and step-free constraints). Neo4j lets your NavigatorAgent do real graph-constrained pathfinding, then have the LLM *explain* the path in the fan's language — this is "GenAI enhancing navigation" in a technically defensible way, not just "ask Gemini for directions."

---

## 4. Tech Stack (matches your existing skill set — free choice, so lean into it)

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI** (Python 3.11+, async) | You already know it deeply (Trading Engine, NovaMentor) |
| Agent orchestration | Lightweight custom orchestrator (NOT LangChain/CrewAI) | Judges reward code quality/readability; hand-rolled agent classes with clear interfaces score better than a black-box framework and are easier for you to defend in Q&A |
| LLM | **Gemini 2.0 Flash** (fast/cheap path) + **Gemini 1.5 Pro** (complex reasoning path) via Vertex AI or Google AI Studio | Free tier, multilingual, multimodal, matches your Google Cloud certs |
| Knowledge Graph | **Neo4j AuraDB (free tier)** | Stadium topology, routing queries |
| Relational DB | **PostgreSQL** (Supabase free tier) | Users, incidents, audit logs |
| Cache/pub-sub | **Redis** (Upstash free tier) | LLM response caching, WebSocket fan-out |
| Frontend (fan) | **React + Vite**, installable PWA | Works offline-degraded, no app-store friction (important for a global tourist audience) |
| Frontend (ops) | **React + Recharts + Mapbox GL** (free tier) | Crowd heatmaps, live gate status |
| Speech | **Web Speech API** (browser-native, free) or Google Cloud Speech-to-Text/TTS free tier | Voice-first for accessibility & multilingual |
| Translation | **Gemini native multilingual** (skip a separate translation API — fewer moving parts, more "GenAI-native") |
| Auth | **JWT + role-based access** (fan / volunteer / organizer) |
| Deployment | **Render** (backend), **Vercel** (frontend) — your usual stack |
| CI | **GitHub Actions** — lint, type-check, pytest on every push |

---

## 5. Neo4j Knowledge Graph Schema

Nodes: `Stadium`, `Gate`, `Section`, `Zone`, `Exit`, `MedicalPoint`, `AccessiblePath`, `TransitStop`, `ConcessionStand`, `RestRoom`

Relationships:
- `(:Gate)-[:LEADS_TO]->(:Zone)`
- `(:Zone)-[:CONTAINS]->(:Section)`
- `(:Zone)-[:CONNECTS_TO {distance_m, step_free: bool, avg_walk_time_s}]->(:Zone)`
- `(:Section)-[:NEAREST_EXIT]->(:Exit)`
- `(:Section)-[:NEAREST_MEDICAL]->(:MedicalPoint)`
- `(:Gate)-[:NEAREST_TRANSIT]->(:TransitStop)`
- `(:Zone {current_density: float, capacity: int})` — updated in real time by the synthetic feed

This lets the NavigatorAgent run a genuine Cypher query like: *"shortest step-free path from Section 214 to nearest exit, avoiding zones with density > 0.85"* — a real constraint-satisfaction problem, GenAI-explained in the fan's language afterward.

---

## 6. Agent Design (the heart of your submission — document these clearly in code + README)

### 6.1 NavigatorAgent
- **Input:** fan location (section/gate), destination intent ("nearest accessible restroom," "Gate C exit," "metro station")
- **Logic:** Cypher query on graph (constraint-aware: step-free if flagged, avoid high-density zones) → shortest path
- **GenAI role:** turns the raw path into a natural-language, multilingual instruction ("Head down the east concourse, take the ramp near Section 210 — it's step-free and less crowded right now.")
- **Not GenAI's job:** the actual pathfinding (that's deterministic graph traversal — cite this distinction in your README, it shows engineering maturity: *use GenAI for language, not for math it's bad at*)

### 6.2 CrowdSentinelAgent
- **Input:** streamed synthetic density readings per zone (Poisson-process simulator, see §8)
- **Logic:** rolling window anomaly detection (z-score or EWMA) — classical stats, not LLM — flags zones trending toward capacity
- **GenAI role:** generates a plain-language incident summary + severity classification + suggested mitigation for the Ops dashboard
- **Escalation:** pushes to OpsCommanderAgent when density > threshold or predicted to cross threshold within N minutes

### 6.3 ConciergeAgent (fan-facing chat/voice)
- Multilingual Q&A: transit times, gate info, weather, match schedule, prohibited items, sustainability tips
- Retrieval-grounded (pull facts from your Postgres/graph — never let the LLM invent stadium facts, this matters for a hackathon judge checking for hallucination risk)
- Voice input/output via Web Speech API for accessibility

### 6.4 SustainabilityAgent
- Tracks estimated crowd transit-mode split (bus/metro/rideshare/walk) from synthetic data
- GenAI generates fan-facing nudges ("Metro Blue Line is 8 min faster than rideshare right now and cuts your trip's CO₂ by ~70%")
- Feeds a sustainability KPI card to the Ops dashboard (waste-bin fill estimates, water refill station usage)

### 6.5 OpsCommanderAgent (the differentiator)
- Aggregates outputs from all four agents
- Prioritizes by severity × affected population × time-to-impact
- Produces a ranked action list for control-room staff with **explicit reasoning trace** shown in the UI ("Recommended: open overflow Gate D — Reason: Zone 4 density 91%, trending +6%/min, 3,200 fans affected, nearest alternate gate has capacity")
- Staff can **approve/override with one click** — this human-in-the-loop design is a strong "responsible AI" talking point for judges

---

## 7. API Design (representative endpoints)

```
POST   /api/v1/navigate                 -> NavigatorAgent route + explanation
POST   /api/v1/concierge/chat           -> ConciergeAgent (streamed response)
WS     /api/v1/ws/crowd-feed            -> live zone density stream
GET    /api/v1/ops/actions              -> OpsCommanderAgent ranked recommendations
POST   /api/v1/ops/actions/{id}/approve -> staff approves/overrides an action
GET    /api/v1/sustainability/summary   -> current transit split + eco tips
POST   /api/v1/auth/login               -> JWT issuance (role: fan/volunteer/organizer)
GET    /api/v1/healthz                  -> liveness/readiness probe
```

---

## 8. Synthetic Data Strategy (critical — you won't have real stadium feeds)

Build a `simulator/` module that generates believable data so your demo doesn't look empty:
- **Crowd density:** Poisson arrivals per gate, modulated by a "match event" timeline (kickoff surge, halftime surge, final-whistle surge) — this alone is a great talking point ("I modeled realistic crowd dynamics around match events, not random noise")
- **Transit feed:** randomized but bounded arrival times per transit mode
- **Weather:** pull *real* current weather for your chosen city via a free API (adds authenticity cheaply)
- Make the simulator swappable behind an interface (`DataSource` ABC) so a judge/future team could plug in real IoT feeds — this is a code-quality point: show you designed for real-world extension, not a hardcoded demo.

---

## 9. Security Checklist (Medium impact, but easy points — do all of these)

- [ ] JWT auth, short-lived access tokens + refresh tokens
- [ ] Role-based access control (fan vs volunteer vs organizer scopes)
- [ ] All secrets (API keys, DB creds) via environment variables / `.env` (never committed) — add `.env.example`
- [ ] Input validation via Pydantic models on every endpoint
- [ ] Prompt-injection mitigation: sanitize/strip user input before it's interpolated into system prompts; keep tool/graph access out of reach of raw user text (agents call structured functions, not free-form DB queries built from user text)
- [ ] Rate limiting on public endpoints (e.g., `slowapi`)
- [ ] HTTPS-only in deployment config
- [ ] Dependency scanning: `pip-audit` / `npm audit` in CI
- [ ] No PII stored beyond session (fan chat doesn't need persistent identity)
- [ ] Audit log table for every Ops action (who approved what, when) — also doubles as an accessibility/accountability feature

---

## 10. Testing Plan

- **Unit tests (pytest):** each agent's non-LLM logic (graph queries, anomaly detection thresholds, priority scoring) tested with fixed inputs/outputs — no live LLM calls in these tests
- **LLM call tests:** mock the Gemini client (fixture returning canned responses) to test agent orchestration logic deterministically
- **Integration tests:** FastAPI `TestClient` hitting real endpoints against a test DB
- **Frontend tests:** Vitest + React Testing Library for key components (chat widget, ops action card, accessibility toggles)
- **Load/efficiency note:** include one Locust script simulating 500 concurrent fan chat sessions, and report cache hit-rate — a concrete efficiency metric in your README is worth more than a claim
- Aim for meaningful coverage on business logic (60-80%), not 100% vanity coverage on trivial code

---

## 11. Efficiency / Cost-Optimization (a genuine differentiator)

- **Model routing:** classification/simple lookups → Gemini Flash; complex multi-constraint reasoning (OpsCommander prioritization) → Gemini Pro. Document the cost delta.
- **Response caching:** Redis-cache common Concierge Q&A (FAQ-style questions repeat heavily in a stadium context) — cite expected cache hit rate
- **Streaming responses** for chat (perceived latency, not just actual)
- **Batching:** CrowdSentinelAgent processes zone updates in batches every N seconds rather than per-event, reducing LLM calls by orders of magnitude
- Show a small "token/cost dashboard" panel in the Ops UI — cheap to build, very persuasive to judges evaluating "efficiency" and "responsible AI use"

---

## 12. Accessibility Plan

- WCAG 2.1 AA target: color contrast ≥4.5:1, all interactive elements keyboard-navigable, ARIA labels, focus indicators
- Voice input/output for low-literacy or visually impaired fans
- Captions/visual alerts for deaf/hard-of-hearing fans (never audio-only alerts)
- High-contrast / large-text mode toggle
- Step-free routing as a first-class NavigatorAgent constraint, not an afterthought
- Multilingual: at minimum English, Spanish, French (the three WC26 host-nation languages), plus 2-3 more via Gemini's native multilingual capability to show global scalability
- Offline-degraded mode: cache last-known gate/route info client-side so the fan app still shows *something* useful if connectivity drops in a packed stadium (a very real, very credible problem — great alignment point)

---

## 13. 2-4 Week Day-by-Day Roadmap (solo)

**Week 1 — Foundations**
- Day 1-2: Repo scaffold, CI pipeline, Neo4j schema + seed data for one real stadium (AT&T Stadium layout), Postgres schema
- Day 3-4: Synthetic data simulator (crowd, transit, weather) + WebSocket streaming
- Day 5-7: NavigatorAgent (graph queries + LLM explanation layer) + basic FastAPI endpoints + first pytest suite

**Week 2 — Core Agents**
- Day 8-9: CrowdSentinelAgent (anomaly detection + LLM summarization)
- Day 10-11: ConciergeAgent (multilingual chat + voice, retrieval-grounded)
- Day 12-14: OpsCommanderAgent (aggregation, prioritization, human-in-the-loop approve/override) + audit log

**Week 3 — Frontend + Polish**
- Day 15-17: Fan PWA (chat, voice, map/route view, accessibility toggles)
- Day 18-20: Ops Dashboard (live heatmap, action queue, cost/efficiency panel)
- Day 21: SustainabilityAgent + eco-tips card

**Week 4 — Hardening + Submission**
- Day 22-23: Security checklist pass, rate limiting, dependency audit
- Day 24-25: Full test suite pass, load test, README + architecture diagram + demo script
- Day 26-27: Record demo video (see §15), deploy to Render/Vercel, final polish
- Day 28: Buffer day for bugs found in final run-through

---

## 14. Evaluation-Parameter Alignment Table (put this directly in your README — judges love an explicit self-assessment)

| Criterion | Where it's demonstrated |
|---|---|
| Problem Statement Alignment | Single system covering navigation, crowd mgmt, accessibility, transport, sustainability, multilingual assistance, ops intelligence, and real-time decision support — grounded in real WC26 venue data |
| Code Quality | Layered architecture (agents / graph / API / frontend separated), typed Python (Pydantic + mypy-clean), documented agent interfaces, CI lint+test gate |
| Security | JWT + RBAC, input validation, prompt-injection mitigation, secrets management, dependency scanning |
| Efficiency | Model routing, Redis caching, batching, streaming, documented cost/latency numbers |
| Testing | Unit + mocked-LLM + integration + frontend tests, load test with reported metrics |
| Accessibility | WCAG AA UI, voice I/O, multilingual, step-free routing constraint, offline-degraded mode |

---

## 15. Submission Package Checklist

- [ ] Public GitHub repo, clean commit history (no "fix" x40 — squash into meaningful commits)
- [ ] README: problem framing, architecture diagram, setup instructions (should run in <5 min), the alignment table above
- [ ] `.env.example` with all required keys documented (no real secrets)
- [ ] Deployed live demo link (Render + Vercel)
- [ ] 3-5 min demo video: (1) fan journey — arrive, ask Concierge a question in Spanish, get routed around a congested zone; (2) ops journey — CrowdSentinel flags a surge, OpsCommander recommends opening an overflow gate, staff approves; (3) 30 seconds on architecture/tech choices
- [ ] Architecture diagram (draw.io/Excalidraw export) — use the one from §3 as a base
- [ ] Short "responsible AI" note: where GenAI is used vs. where deterministic logic is used, and why (this single paragraph does a lot of work for both Problem Alignment and Security scores)

---

## 16. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Solo build, 2-4 weeks, scope creep | Follow the roadmap strictly; cut SustainabilityAgent depth first if behind schedule (it's the least central agent) |
| Judges can't tell GenAI reasoning from hardcoded logic | Show explicit reasoning traces in the UI (OpsCommander "Reason:" field) and log LLM prompts/responses visibly in a debug panel |
| Free-tier limits (Neo4j Aura, Render, Vertex AI quotas) | Keep the demo dataset small (one stadium, ~15-20 zones) — plenty for a compelling demo, well within free tiers |
| LLM hallucinating stadium facts | Retrieval-grounding: Concierge only answers from graph/DB-sourced facts, refuses/deflects otherwise — mention this explicitly as a safety design choice |

---

*This plan is designed to be modified as you build — treat the roadmap as a living checklist, not a rigid schedule.*
