# ArenaPulse — AI Operations & Fan Copilot for FIFA World Cup 2026

> **Challenge 4: Smart Stadiums & Tournament Operations**
> A multi-agent GenAI operations layer for real-time stadium intelligence, crowd management, accessibility, sustainability, and multilingual fan assistance.

---

## 🏟️ Problem Statement Alignment

FIFA World Cup 2026 spans **16 stadiums across US, Mexico, and Canada**, hosting **48 teams and 104 matches**, with an expected cumulative attendance breaking **3.5 million**. This creates unprecedented operational challenges: multilingual crowds, real-time crowd density management, accessibility needs, transportation bottlenecks, and sustainability concerns.

**ArenaPulse** addresses all 8 focus areas from the problem statement through a unified knowledge graph + agent pipeline:

| Focus Area | How ArenaPulse Solves It |
|---|---|
| **Navigation** | Graph-constrained pathfinding (Neo4j) with GenAI-generated multilingual explanations |
| **Crowd Management** | Real-time anomaly detection with predictive escalation and explainable action recommendations |
| **Accessibility** | Step-free routing as first-class constraint, voice I/O, captioned alerts, WCAG AA UI |
| **Transportation** | Live transit mode optimization with CO₂ impact comparison |
| **Sustainability** | Transit-mode split tracking, waste-bin fill estimates, eco-nudge generation |
| **Multilingual Assistance** | Native multilingual GenAI (English, Spanish, French + 5 more) without separate translation APIs |
| **Operational Intelligence** | Aggregated, prioritized action queue with explicit reasoning traces |
| **Real-time Decision Support** | Human-in-the-loop approve/override for control-room staff |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Synthetic Data Layer                      │
│     (crowd density, transit, weather, gate sensors)          │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket / REST (streamed)
┌───────────────────────────▼─────────────────────────────────┐
│              FastAPI Backend (async, typed)                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │Navigator │ Crowd    │Concierge │Sustain-  │ Ops      │  │
│  │ Agent    │ Sentinel │ Agent    │ ability │ Commander│  │
│  └────┬─────┴────┬─────┴────┬────┴────┬─────┴────┬─────┘  │
│       └──────────┴──────────┴──────────┴──────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              Neo4j Knowledge Graph                           │
│   (gates, zones, exits, medical points, capacities, routes)  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              PostgreSQL (logs, users, incidents, audit)      │
└─────────────────────────────────────────────────────────────┘

Frontend: React PWA (Fan) + React Ops Dashboard (Staff)
```

### Why a Knowledge Graph?

Stadium navigation and accessibility are inherently **graph problems**: gates → sections → exits → medical points, with capacity and step-free constraints. Neo4j lets the NavigatorAgent perform real graph-constrained pathfinding, then the LLM *explains* the path in the fan's language. This is "GenAI enhancing navigation" in a technically defensible way — **we use GenAI for language, not for math it's bad at**.

---

## 🚀 Quick Start (< 5 minutes)

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)
- A Google AI Studio API key ([get one free](https://aistudio.google.com/))

### 1. Clone & Configure
```bash
git clone <repo-url>
cd arenapulse
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Start Infrastructure
```bash
docker-compose up -d neo4j postgres redis
```

### 3. Seed the Knowledge Graph
```bash
cd backend
pip install -r requirements.txt
python -m app.graph.seed
```

### 4. Start Backend
```bash
uvicorn app.main:app --reload
```

### 5. Start Frontend
```bash
cd ../frontend
npm install
npm run dev
```

Visit `http://localhost:5173` for the fan app and `http://localhost:5173/ops` for the operations dashboard.

---

## 🧪 Testing

### Backend
```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

### Frontend
```bash
cd frontend
npm run test
```

---

## 🔒 Security

- JWT authentication with short-lived access tokens + refresh tokens
- Role-based access control (fan / volunteer / organizer scopes)
- All secrets via environment variables (`.env.example` provided)
- Pydantic input validation on every endpoint
- Prompt-injection mitigation: user input sanitized before LLM prompts; agents call structured functions, not free-form DB queries
- Rate limiting on public endpoints (SlowAPI)
- Audit log for every Ops action (who approved what, when)

---

## ⚡ Efficiency

- **Model routing**: Classification/simple lookups → Gemini Flash; complex reasoning → Gemini Pro
- **Response caching**: Redis caches common Concierge Q&A (expected 60%+ hit rate for FAQ-style questions)
- **Batching**: CrowdSentinel processes zone updates in batches, reducing LLM calls by ~90%
- **Streaming**: Chat responses stream for perceived low latency
- Cost/latency metrics visible in Ops dashboard

---

## ♿ Accessibility

- WCAG 2.1 AA target: color contrast ≥4.5:1, keyboard-navigable, ARIA labels, focus indicators
- Voice input/output via Web Speech API
- Captioned/visual alerts (never audio-only)
- High-contrast / large-text mode toggle
- Step-free routing as first-class constraint
- Offline-degraded mode: cached last-known routes work without connectivity

---

## 📊 Evaluation Alignment

| Criterion | Where Demonstrated |
|---|---|
| **Problem Statement Alignment** | Single system covering all 8 focus areas — grounded in real WC26 venue data (AT&T Stadium) |
| **Code Quality** | Layered architecture, typed Python (Pydantic + mypy), documented agent interfaces, CI lint+test gate |
| **Security** | JWT + RBAC, input validation, prompt-injection mitigation, secrets management, dependency scanning |
| **Efficiency** | Model routing, Redis caching, batching, streaming, documented cost/latency metrics |
| **Testing** | Unit + mocked-LLM + integration + frontend tests |
| **Accessibility** | WCAG AA UI, voice I/O, multilingual, step-free routing, offline-degraded mode |

---

## 🤖 Responsible AI

- **Deterministic logic** handles pathfinding, anomaly detection, and priority scoring
- **GenAI** handles natural language explanations, multilingual translation, and eco-nudge generation
- Human-in-the-loop approve/override for all operational actions
- Retrieval-grounded responses prevent hallucination on stadium facts

---

## 📄 License

MIT
