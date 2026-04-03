# Perception AI

A multi-provider brand intelligence platform that tracks how AI models perceive brands — helping marketing teams understand and monitor their presence in AI-generated recommendations, search results, and conversations.

## Why AI Brand Perception Matters

As consumers increasingly use ChatGPT, Claude, and Gemini for product research and buying decisions, **how AI perceives your brand is becoming as important as traditional SEO**. If someone asks an AI "what's the best project management tool?" and your product isn't mentioned — or is positioned poorly — that's lost revenue.

Perception AI gives brands visibility into this blind spot. It analyses how multiple AI models perceive a brand across three dimensions — brand identity, news sentiment, and competitive positioning — and tracks how that perception shifts over time as models are retrained. With scheduled recurring analyses, teams can monitor their AI presence the same way they monitor search rankings.

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
                  dispatches task   pub/sub
                             |          |
                         +---v----------v----+
                         |      Redis        |
                         | (broker + pubsub) |
                         +---+-----+--------++
                             |     |         |
                      task queue   |    beat schedule
                             |     |         |
                         +---v-----+--+ +----v---------+
                         |  Celery    | | Celery Beat  |
                         |  Worker    | | (scheduler)  |
                         +------+-----+ +----+---------+
                                |             |
                          decrypts user  checks due
                          API keys,      schedules,
                          fans out       dispatches
                          in parallel    tasks every
                                |        60 seconds
               +----------------+----------------+
               |                |                |
        +------v-----+  +------v-----+  +-------v----+
        | Anthropic  |  |  OpenAI    |  |  Google    |
        | Claude     |  |  GPT-4o    |  |  Gemini    |
        +------+-----+  +------+-----+  +-------+----+
               |                |                |
               +----------------+----------------+
                                |
                         +------v----------+
                         |  Aggregate &    |
                         |  Compare        |
                         +------+----------+
                                |
                         +------v----------+
                         |    MongoDB      |
                         | (users, reports |
                         |  schedules)     |
                         +-----------------+
```

## User Flow

```
  +------------------+     +------------------+     +------------------+
  |   Sign Up /      |     |   Add API Keys   |     |   Click "New     |
  |   Log In         +---->+   (1+ provider)  +---->+   Analysis"      |
  |                  |     |   sidebar icon    |     |   (modal)        |
  +------------------+     +------------------+     +--------+---------+
                                                             |
                                                    Enter brand name,
                                                    competitors,
                                                    select models
                                                    (one per provider),
                                                    optional "Repeat
                                                    monthly" toggle
                                                             |
                                                    +--------v---------+
                                                    |   Submit Form    |
                                                    +---+----------+---+
                                                        |          |
                                              creates report   if repeat on,
                                              + Celery task    creates schedule
                                                        |          |
                           +--------------------+       |          |
                           |  SSE connection    |<------+          |
                           |  opens, shows      |                  |
                           |  per-model progress|    +-------------v---+
                           +--------+-----------+    | Celery Beat     |
                                    |                | auto-dispatches |
                           Worker fans out to        | every 30 days   |
                           selected models in        +-----------------+
                           parallel (ThreadPool)
                                    |
                           +--------v-----------+
                           |  All models done   |
                           |  Modal closes,     |
                           |  navigates to      |
                           |  report page       |
                           +--------+-----------+
                                    |
                           +--------v-----------+
                           |  Interactive       |
                           |  report: scores,   |
                           |  pillars, model    |
                           |  comparison,       |
                           |  competitor map,   |
                           |  per-model trends  |
                           +--------------------+
```

## Features

- **Multi-provider AI comparison** -- Compare how Claude, GPT-4o, and Gemini perceive your brand side by side, with parallel fan-out via ThreadPoolExecutor
- **Structured scoring rubrics** -- Consistent 1-10 scoring across 5 dimensions (recognition, sentiment, innovation, value, positioning) with defined criteria and temperature 0
- **Scheduled recurring analyses** -- Toggle "Repeat monthly" to auto-run analyses via Celery Beat, with a dashboard to view and cancel schedules
- **Bring your own keys** -- Users add API keys per provider (Anthropic, OpenAI, Google), each encrypted at rest with Fernet (AES-128) using a dedicated encryption key
- **Event-driven processing** -- Celery workers consume analysis jobs from a Redis-backed message queue
- **Real-time per-model progress** -- Server-Sent Events deliver live per-model status updates via Redis pub/sub
- **Brand pillar extraction** -- Identifies and scores core brand attributes with confidence levels
- **Competitor positioning** -- Maps brands against competitors on premium and lifestyle axes
- **Per-model trend tracking** -- Colour-coded trend lines per model built from real historical data, showing how each AI's perception shifts over time
- **Input validation & rate limiting** -- Pydantic validation on all inputs, Redis-backed rate limiting (5 analyses/min per user)
- **Security hardening** -- Separate keys for JWT signing and encryption, bcrypt password hashing, provider-level key validation

## Tech Stack

### Frontend

- React 19 + TypeScript
- Vite 6
- Tailwind CSS v4
- Zustand (state management)
- TanStack React Query (server state)
- React Router v7
- Recharts (data visualisation)
- shadcn/ui + Base UI components

### Backend

- FastAPI (Python 3.12)
- Celery (task queue + Beat scheduler)
- Redis (message broker + pub/sub progress)
- MongoDB via Motor (async) + PyMongo (sync)
- Anthropic SDK, OpenAI SDK, Google GenAI SDK
- Fernet encryption (cryptography)
- JWT authentication (python-jose + bcrypt)
- Uvicorn

### Infrastructure

- Docker + Docker Compose (6 services)
- nginx (reverse proxy + SPA routing)
- GitHub Actions CI (tests, type-check, build, Docker)

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/harryndavies/brand-perception-ai.git
   cd brand-perception-ai
   ```

2. **Configure environment variables**

   Create a `.env` file in the project root:

   ```
   SECRET_KEY=your-jwt-signing-secret
   ENCRYPTION_KEY=your-fernet-encryption-key
   ```

   Generate a secure encryption key:

   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   > **Note:** No server-side API keys are needed. Each user provides their own keys for the providers they want to use, stored encrypted in the database.

3. **Start all services**

   ```bash
   docker compose up --build
   ```

   This starts:
   - **Frontend** (nginx) -- [http://localhost:3000](http://localhost:3000)
   - **Backend** (FastAPI) -- [http://localhost:8000](http://localhost:8000)
   - **Worker** (Celery) -- processes analysis jobs
   - **Beat** (Celery Beat) -- dispatches scheduled analyses every 60s
   - **MongoDB** -- document database
   - **Redis** -- message broker and pub/sub progress

4. **Create an account and add API keys**

   Sign up at [http://localhost:3000](http://localhost:3000), then click the key icon in the sidebar to add your API keys. You need at least one provider:
   - [Anthropic](https://console.anthropic.com/) -- Claude Sonnet, Haiku, Opus
   - [OpenAI](https://platform.openai.com/) -- GPT-4o, GPT-4o Mini
   - [Google](https://aistudio.google.com/) -- Gemini 2.0 Flash, Gemini 2.5 Pro

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
│       ├── components/         # UI components (dialogs, report charts, layout)
│       ├── pages/              # Route pages (dashboard, reports, login, signup)
│       ├── stores/             # Zustand stores (auth)
│       ├── lib/                # API client and utilities
│       └── types/              # TypeScript type definitions
├── backend/
│   ├── Dockerfile
│   └── app/
│       ├── worker.py           # Celery app + Beat schedule configuration
│       ├── tasks.py            # Analysis task + parallel fan-out + scheduler
│       ├── models/             # Pydantic models (user, report, schedule)
│       ├── routes/             # API endpoints (auth, reports, schedules)
│       ├── services/           # SSE streaming + provider abstraction
│       ├── middleware.py        # Correlation ID + request logging
│       └── core/               # Config, database, auth, encryption, logging, progress
├── docker-compose.yml          # Full stack orchestration (6 services)
├── .github/workflows/ci.yml   # CI pipeline
└── package.json                # Workspace root with dev scripts
```

## How It Works

1. User signs up and adds API keys for one or more providers (each encrypted with Fernet, stored in MongoDB)
2. User opens the "New Analysis" modal, enters a brand name, optional competitors, and selects one model per provider to compare
3. The API server validates input, checks the user has keys for all selected providers, checks rate limits, creates a report record, and dispatches a Celery task
4. Redis progress state is seeded with one entry per model so the SSE stream has data immediately
5. The Celery worker decrypts the user's API keys and fans out API calls to all selected models in parallel via ThreadPoolExecutor
6. Each model emits its own progress updates via Redis pub/sub -- the frontend shows per-model status in real time
7. Results are aggregated: scores averaged across models, pillars deduplicated, competitor positions merged. Historical trend data is built from past analyses with per-model colour-coded lines
8. The completed report is persisted to MongoDB and the frontend navigates to the interactive report page
9. For scheduled analyses, Celery Beat checks every 60 seconds for due schedules, creates reports, and dispatches multi-model analysis tasks automatically

## Available Models

| Provider | Model | Key |
|---|---|---|
| Anthropic | Claude Sonnet | `claude-sonnet` |
| Anthropic | Claude Haiku | `claude-haiku` |
| Anthropic | Claude Opus | `claude-opus` |
| OpenAI | GPT-4o | `gpt-4o` |
| OpenAI | GPT-4o Mini | `gpt-4o-mini` |
| Google | Gemini 2.0 Flash | `gemini-2.0-flash` |
| Google | Gemini 2.5 Pro | `gemini-2.5-pro` |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/signup` | Register a new user |
| `POST` | `/api/auth/login` | Log in |
| `GET` | `/api/auth/me` | Get current user (includes `api_keys` providers) |
| `PUT` | `/api/auth/api-key` | Save encrypted API key for a provider |
| `DELETE` | `/api/auth/api-key/:provider` | Remove stored key for a provider |
| `GET` | `/api/reports` | List reports for current user |
| `GET` | `/api/reports/models` | List available models |
| `POST` | `/api/reports` | Create multi-model analysis (rate limited) |
| `GET` | `/api/reports/:id` | Get report details |
| `GET` | `/api/reports/:id/stream` | SSE stream for per-model progress |
| `GET` | `/api/schedules` | List active schedules |
| `POST` | `/api/schedules` | Create a recurring schedule |
| `DELETE` | `/api/schedules/:id` | Cancel a schedule |
| `GET` | `/api/health` | Health check |

## Security

- **API keys** are encrypted at rest using Fernet (AES-128-CBC) with a dedicated `ENCRYPTION_KEY`, separate from the JWT `SECRET_KEY`
- **Per-provider key storage** -- each provider's key is encrypted independently; users only need keys for the providers they use
- **Provider validation** -- analyses are blocked if the user lacks keys for any selected provider
- **Passwords** are hashed with bcrypt
- **JWT tokens** expire after 7 days
- **Input validation** enforced via Pydantic (brand length, competitor count, password complexity)
- **Rate limiting** at 5 analyses per 60 seconds per user via Redis
- **CORS origins** configurable via `CORS_ORIGINS` env var
- **Production guards** -- `SECRET_KEY` and `ENCRYPTION_KEY` must be explicitly set when `ENV=production`
