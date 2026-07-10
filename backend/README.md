# ArenaPulse — Smart Stadium Operations for FIFA World Cup 2026

## Quick Start

```bash
# 1. Start infrastructure
docker-compose up -d neo4j postgres redis

# 2. Seed stadium data
cd backend
pip install -r requirements.txt
python -m app.graph.seed

# 3. Start backend
uvicorn app.main:app --reload

# 4. Start frontend (new terminal)
cd ../frontend
npm install
npm run dev
```

Visit `http://localhost:5173` for the fan app.

## Demo Mode

If Neo4j/LLM are unavailable, the backend auto-falls back to demo mode — all endpoints still return realistic AT&T Stadium data.

## Testing

```bash
cd backend
pytest -v
```
