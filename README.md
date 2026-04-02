# Perception AI

A brand intelligence platform that analyses how brands are perceived across multiple dimensions using AI. It aggregates insights from multiple AI models to generate comprehensive brand reports covering sentiment analysis, brand pillar identification, and competitive positioning.

## Architecture

```
                         +-------------------+
                         |    Browser/UI     |
                         |  React + Vite     |
                         +--------+----------+
                                  |
                             HTTP / SSE
                                  |
                         +--------v----------+
                         |      nginx        |
                         |  (reverse proxy)  |
                         +--------+----------+
                                  |
                           /api/* |
                                  |
                         +--------v----------+
                         |  FastAPI Server   |
                         |  (API + Auth)     |
                         +---+----------+----+
                             |          |
                  POST /reports    SSE /stream
                  dispatches task   polls progress
                             |          |
                         +---v----------v----+
                         |      Redis        |
                         | (broker + state)  |
                         +---+----------+----+
                             |          ^
                      task queue     progress
                             |      updates
                         +---v----------+----+
                         |  Celery Worker    |
                         +---+---------+-----+
                             |         |
               +-------------+---------+-------------+
               |             |                        |
        +------v---+  +------v------+  +--------------v--+
        | Claude   |  | GPT-4      |  | Gemini          |
        | (brand   |  | (news      |  | (competitor     |
        | analysis)|  | sentiment) |  | positioning)    |
        +----------+  +------------+  +-----------------+
               |             |                        |
               +-------------+------------------------+
                             |
                    +--------v---------+
                    |  Aggregate &     |
                    |  Persist         |
                    +--------+---------+
                             |
                    +--------v---------+
                    |    MongoDB       |
                    | (users, reports) |
                    +------------------+
```

## Features

- **Multi-model AI analysis** — Runs brand queries through Claude, GPT-4, and Gemini to triangulate perception data
- **Event-driven task processing** — Celery workers consume analysis jobs from a Redis-backed message queue
- **Real-time progress streaming** — Server-Sent Events deliver live analysis updates to the UI via Redis-backed state
- **Brand pillar extraction** — Identifies and scores core brand attributes with confidence levels
- **Sentiment scoring** — Quantifies brand sentiment on a -1.0 to 1.0 scale across news and social dimensions
- **Competitor positioning** — Maps brands against competitors on premium and lifestyle axes
- **Trend visualisation** — Charts historical sentiment and volume data with Recharts
- **Auth & team management** — JWT-based authentication with multi-user workspace support

## Tech Stack

### Frontend

- React 19 + TypeScript
- Vite 6
- Tailwind CSS v4
- Zustand (state management)
- TanStack React Query (server state)
- React Router v7
- Recharts (data visualisation)
- shadcn/ui components

### Backend

- FastAPI (Python 3.12)
- Celery (task queue)
- Redis (message broker + progress state)
- MongoDB via Motor (async) + PyMongo (sync)
- Anthropic SDK
- JWT authentication (python-jose + bcrypt)
- Uvicorn

### Infrastructure

- Docker + Docker Compose
- nginx (reverse proxy + SPA routing)
- GitHub Actions CI (tests, type-check, build, Docker)

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/harryndavies/ai-brand-perception.git
   cd ai-brand-perception
   ```

2. **Configure environment variables**

   Create a `.env` file in the project root:

   ```
   ANTHROPIC_API_KEY=your-api-key-here
   SECRET_KEY=your-jwt-secret        # optional, defaults to dev secret
   ```

3. **Start all services**

   ```bash
   docker compose up --build
   ```

   This starts:
   - **Frontend** (nginx) — [http://localhost:3000](http://localhost:3000)
   - **Backend** (FastAPI) — [http://localhost:8000](http://localhost:8000)
   - **Worker** (Celery) — processes analysis jobs
   - **MongoDB** — document database
   - **Redis** — message broker and progress state

### Local Development (without Docker)

For frontend-only work, you can run Vite directly:

```bash
npm install
npm run dev:frontend
```

The full analysis pipeline requires Redis and the Celery worker. Use Docker Compose for the complete stack.

### Running Tests

```bash
# Frontend (Vitest)
npm run test:frontend

# Backend (pytest)
npm run test:backend

# Both
npm run test
```

## Project Structure

```
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf              # Reverse proxy + SPA config
│   └── src/
│       ├── components/         # Layout and UI components
│       ├── pages/              # Route pages (dashboard, reports, analysis, settings)
│       ├── stores/             # Zustand stores (auth, reports)
│       ├── lib/                # API client and utilities
│       ├── types/              # TypeScript type definitions
│       └── test/               # Test setup and utilities
├── backend/
│   ├── Dockerfile
│   └── app/
│       ├── worker.py           # Celery app configuration
│       ├── tasks.py            # Analysis Celery tasks
│       ├── models/             # SQLModel database models (user, report)
│       ├── routes/             # API endpoints (auth, reports, usage)
│       ├── services/           # SSE streaming interface
│       └── core/               # Config, database, auth, Redis progress
├── docker-compose.yml          # Full stack orchestration
├── .github/workflows/ci.yml   # CI pipeline
└── package.json                # Workspace root with dev scripts
```

## How It Works

1. A user creates a new analysis by entering a brand name and up to three competitors
2. The API server creates a report record and dispatches a Celery task via Redis
3. The Celery worker picks up the job and fans out queries to Claude, GPT-4, and Gemini
4. Progress updates are written to Redis as each model completes
5. The frontend streams progress in real time via SSE, polling Redis-backed state
6. Results are aggregated — pillars merged, sentiment averaged, competitor positions collected
7. The completed report is persisted to the database and an `analysis.complete` event is published
8. The frontend displays the report with interactive charts and tabbed views

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/signup` | Register a new user |
| `POST` | `/api/auth/login` | Log in |
| `GET` | `/api/auth/me` | Get current user |
| `GET` | `/api/reports` | List reports |
| `POST` | `/api/reports` | Create a new analysis (dispatches Celery task) |
| `GET` | `/api/reports/:id` | Get report details |
| `GET` | `/api/reports/:id/stream` | SSE stream for analysis progress |
| `GET` | `/api/usage` | Get usage stats |
| `GET` | `/api/health` | Health check |
