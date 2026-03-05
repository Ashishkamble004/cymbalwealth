# Wealth Management Platform

AI-powered private banking platform with **Gemini AI** integrated at every layer — from KYC document analysis to portfolio commentary, RM copilot briefings, and voice interaction.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), TailwindCSS, TypeScript |
| **Backend** | FastAPI (Python 3.11), SQLAlchemy ORM |
| **AI** | Gemini 2.0 Flash (text/multimodal), Gemini 2.5 Flash (voice) |
| **Database** | PostgreSQL 15 |
| **Cache** | Redis 7 |
| **Cloud** | Google Cloud Platform (Cloud Run, Cloud SQL, Memorystore, Cloud Storage) |

## Gemini AI Integration — 4 Layers

1. **KYC & Onboarding** — Multimodal document analysis (Aadhaar, PAN, ITR) with risk profiling
2. **Portfolio Commentary** — Streaming AI-generated monthly commentary via SSE
3. **RM Copilot** — Pre-call briefs and follow-up chat for relationship managers
4. **Voice Assistant (Aria)** — Real-time voice interaction via WebSocket

## Quick Start — Local Development

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com)

### Using Docker Compose

```bash
# Clone the repo
git clone <repo-url>
cd wealth-platform

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Start all services
docker-compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis (or use Docker for just databases)
docker run -d --name pg -e POSTGRES_USER=wealthuser -e POSTGRES_PASSWORD=changeme -e POSTGRES_DB=wealthdb -p 5432:5432 postgres:15-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Run the backend
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/onboarding/analyze-docs` | POST | Upload & analyze KYC documents |
| `/onboarding/risk-score` | POST | Score risk profiling answers |
| `/onboarding/clients` | GET | List all clients |
| `/onboarding/clients/{id}` | GET | Get client details |
| `/portfolio/{client_id}` | GET | Full portfolio summary |
| `/portfolio/{client_id}/commentary` | GET | Stream AI commentary (SSE) |
| `/rm/copilot/brief/{client_id}` | GET | Generate RM pre-call brief |
| `/rm/copilot/chat` | POST | Follow-up chat about client |
| `/rm/copilot/clients-summary` | GET | All clients summary for RM |
| `/voice/stream` | WS | Voice interaction WebSocket |

## GCP Deployment

```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy everything to GCP
./deploy.sh
```

The deployment script will:
1. Check prerequisites (gcloud, docker, psql)
2. Enable required GCP APIs
3. Create infrastructure (Cloud SQL, Redis, Storage, VPC)
4. Configure secrets in Secret Manager
5. Set up service accounts and IAM
6. Build and push Docker images
7. Run database migrations and seed data
8. Deploy to Cloud Run
9. Output URLs and cost estimate

## Seed Data

5 realistic Indian wealth management clients are included:

| Client | Segment | AUM | Risk Profile |
|--------|---------|-----|--------------|
| Arjun Mehta | UHNI | ₹62 Cr | Aggressive |
| Priya Nair | HNI | ₹7.4 Cr | Moderate |
| Rajesh Singhania | UHNI | ₹38 Cr | Moderate |
| Kavitha Iyer | HNI | ₹3.1 Cr | Conservative |
| Sameer Kulkarni | Mass Affluent | ₹48 L | Moderate |

Each client has 10–15 holdings, 6 months of transactions, and 2–3 financial goals.

## Project Structure

```
├── deploy.sh                 # GCP deployment script
├── docker-compose.yml        # Local development
├── cloudbuild.yaml           # CI/CD pipeline
├── .env.example              # Environment variables
├── backend/
│   ├── main.py               # FastAPI application
│   ├── config.py             # Configuration
│   ├── models/               # SQLAlchemy models
│   ├── routers/              # API route handlers
│   ├── services/             # Business logic & AI
│   └── db/                   # Database & seed data
└── frontend/
    ├── app/
    │   ├── (rm)/dashboard/   # RM Dashboard
    │   ├── (client)/portfolio/ # Client Portfolio
    │   └── components/       # React components
    ├── package.json
    └── next.config.js
```

## License

Private — All rights reserved.