# Perception AI

A brand intelligence platform that analyses how brands are perceived across multiple dimensions using AI. It aggregates insights from multiple AI models to generate comprehensive brand reports covering sentiment analysis, brand pillar identification, and competitive positioning.

## Features

- **Multi-model AI analysis** — Runs brand queries through Claude, GPT-4, and Gemini to triangulate perception data
- **Real-time progress streaming** — Server-Sent Events deliver live analysis updates to the UI
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
- SQLModel (SQLAlchemy + Pydantic)
- SQLite (default, configurable)
- Anthropic SDK
- JWT authentication (python-jose + bcrypt)
- Uvicorn

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/harryndavies/ai-brand-perception.git
   cd ai-brand-perception
   ```

2. **Install frontend dependencies**

   ```bash
   npm install
   ```

3. **Configure environment variables**

   Create a `.env` file in the project root:

   ```
   ANTHROPIC_API_KEY=your-api-key-here
   SECRET_KEY=your-jwt-secret        # optional, defaults to dev secret
   DATABASE_URL=sqlite:///./perception.db  # optional
   ```

4. **Start the development servers**

   ```bash
   npm run dev
   ```

   This runs both servers concurrently:
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend: [http://localhost:8000](http://localhost:8000)

   The Vite dev server proxies `/api` requests to the backend automatically.

### Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start frontend + backend concurrently |
| `npm run dev:frontend` | Start Vite dev server only |
| `npm run dev:backend` | Start FastAPI with uvicorn only |
| `npm run build` | Build frontend for production |

## Project Structure

```
├── frontend/
│   └── src/
│       ├── components/    # Layout and UI components
│       ├── pages/         # Route pages (dashboard, reports, analysis, settings)
│       ├── stores/        # Zustand stores (auth, reports)
│       ├── lib/           # API client and utilities
│       └── types/         # TypeScript type definitions
├── backend/
│   └── app/
│       ├── models/        # SQLModel database models (user, report)
│       ├── routes/        # API endpoints (auth, reports, usage)
│       ├── services/      # AI analysis orchestration
│       └── core/          # Config, database, and auth utilities
└── package.json           # Workspace root with dev scripts
```

## How It Works

1. A user creates a new analysis by entering a brand name and up to three competitors
2. The backend fans out parallel AI queries to Claude, GPT-4, and Gemini
3. Progress streams to the frontend in real time via SSE
4. Results are aggregated — pillars merged, sentiment averaged, competitor positions collected
5. The completed report is persisted and displayed with interactive charts and tabbed views

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/signup` | Register a new user |
| `POST` | `/api/auth/login` | Log in |
| `GET` | `/api/auth/me` | Get current user |
| `GET` | `/api/reports` | List reports |
| `POST` | `/api/reports` | Create a new analysis |
| `GET` | `/api/reports/:id` | Get report details |
| `GET` | `/api/reports/:id/stream` | SSE stream for analysis progress |
| `GET` | `/api/usage` | Get usage stats |
