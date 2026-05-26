# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

CymbalWealth is an AI-powered banking demo platform built on Google ADK + Gemini. It showcases multiple AI use cases across a fictional wealth management bank, all deployed on Google Cloud.

GCP config (hardcoded across the codebase):
- **Project**: `general-ak` (ID: `769002985772`)
- **Region**: `us-central1`
- **GCS bucket**: `cymbal-wealth` (session recordings, documents)
- **Artifact Registry repo**: `cymbal-wealth`
- **ADC required**: `gcloud auth application-default login`

---

## Services & Architecture

The repo has five independently deployable services plus a sub-project:

### 1. KYC Backend (`backend/main.py`)
FastAPI + WebSocket server. The root agent (`kyc_agent/agent.py`) uses Gemini Live (`gemini-live-2.5-flash-native-audio`) for real-time bidirectional voice/video. It delegates document verification to a sub-agent via `AgentTool`. Sessions are `InMemorySessionService` (intentional — Cloud Run is configured with `min-instances=1` + session affinity).

WebSocket protocol (`/ws/{user_id}/{session_id}`): client sends JSON messages typed as `audio`, `video`, `text`, `context`, `end_session`, `ping`. Server streams back `audio`, `transcript`, `input_transcription`, `output_transcription`, `turn_complete`, `interrupted`.

After session end, transcripts + audio (PCM WAV) + video (AVI) are saved to GCS.

### 2. Home Loan Backend (`backend/homeloan_main.py`)
Separate FastAPI app (same Docker image, different entrypoint). Uploads go to GCS; verification is routed to a **Vertex AI Agent Engine** multi-agent pipeline. Uses an `_AgentSessionPool` (size 3) pre-warmed at startup to absorb the ~6s session creation latency.

Pipeline: `SequentialAgent` → `ParallelAgent(doc_quality, identity_income)` → `property_eligibility_agent`.

Agent Engine resource: `projects/769002985772/locations/us-central1/reasoningEngines/5332737497585680384`

### 3. HR Agents (`backend/hr_agents/`)
Six agents deployed to Vertex AI Agent Engine and registered with Gemini Enterprise (Discovery Engine). Manage with:
- `python -m hr_agents.deploy` — deploys all 6 agents, writes `.agent_engine_config.json`
- `python -m hr_agents.register` — registers them with Gemini Enterprise, writes `.agent_registration_config.json`

### 4. Customer Support (`backend/customer_support/`)
Not a standalone service — mounted into the KYC backend as a router at `/customer-support`. Uses Google Cloud Speech-to-Text v2 (Chirp 3, streaming) + RAG Corpus on Vertex AI for grounded LLM suggestions.

RAG Corpus: `projects/general-ak/locations/us-central1/ragCorpora/2305843009213693952`

### 5. MCP Server (`backend/mcp_server/`)
Standalone stdio MCP server exposing NSE/BSE stock data via yfinance. Runs separately from the FastAPI app.

### 6. Frontend (`frontend/`)
React 19 + Vite + TypeScript + Tailwind CSS. Dev server proxies `/ws` WebSocket to `localhost:8080`.

### 7. Demo Portal (`demo-portal/`)
Static HTML with Tailwind CDN. No build step. Brand colors: primary `#791652`, accent `#C5A55A`.

### 8. GenFlow Ad Studio (`genflow-ad-studio/`)
Separate sub-project with its own `CLAUDE.md`, `Makefile`, and `AGENTS.md`. See that directory for its own guidance.

---

## Local Development

### Prerequisites
```bash
gcloud auth application-default login
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=general-ak
export GOOGLE_CLOUD_LOCATION=us-central1
```

### KYC Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py          # runs on :8080
```

### Home Loan Backend
```bash
cd backend
source venv/bin/activate
python homeloan_main.py  # same venv, different entry point
```

### MCP Server
```bash
cd backend/mcp_server
pip install -r requirements.txt
python server.py        # stdio, connect via MCP client
```

### Frontend (KYC UI)
```bash
cd frontend
npm install
npm run dev             # runs on :3000, proxies /ws → :8080
npm run build           # production build
```

### Demo Portal
Open `demo-portal/index.html` directly in a browser — no build step.

---

## Deployment

All services deploy via Cloud Build to Cloud Run. From the repo root:

```bash
# KYC backend
gcloud builds submit --config=deploy/cloudbuild-backend.yaml

# Home loan backend
gcloud builds submit --config=deploy/cloudbuild-homeloan.yaml

# KYC frontend
gcloud builds submit --config=deploy/cloudbuild-frontend.yaml

# Demo portal
gcloud builds submit --config=deploy/cloudbuild-portal.yaml

# MCP server
gcloud builds submit --config=deploy/cloudbuild-mcp.yaml

# GenFlow Ad Studio
gcloud builds submit --config=deploy/cloudbuild-adstudio.yaml
```

Key Cloud Run settings for the KYC backend: `--session-affinity --min-instances=1 --timeout=3600` (required for WebSocket + in-memory sessions).

---

## Key Environment Variables

The backend reads these (with defaults shown):

| Variable | Default | Used by |
|---|---|---|
| `GCP_PROJECT` / `GOOGLE_CLOUD_PROJECT` | `general-ak` | All |
| `GCP_REGION` / `GOOGLE_CLOUD_LOCATION` | `us-central1` | All |
| `GCS_BUCKET` | `cymbal-wealth` | KYC, home loan |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | All agents |
| `DEMO_AGENT_MODEL` | `gemini-live-2.5-flash-native-audio` | KYC agent |
| `CORS_ORIGINS` | `https://cymbalwealth.ak-demos.com,...` | KYC backend |
| `AGENT_ENGINE_ID` | `projects/769002985772/...` | Home loan |
| `RAG_CORPUS_RESOURCE_NAME` | `projects/general-ak/.../ragCorpora/...` | Customer support |

Create `backend/.env` for local overrides (loaded via `python-dotenv`).

---

## Demo Reference Numbers

| Reference | Customer |
|---|---|
| CW-2026-001 | Ashish Kamble |
| CW-2026-002 | Priya Sharma |

---

## ADK Patterns Used

- **`Agent` + `AgentTool`**: KYC root delegates to verification sub-agent
- **`SequentialAgent` + `ParallelAgent`**: Home loan pipeline runs doc quality and identity/income checks in parallel, then property/eligibility sequentially
- **`Runner` + `InMemorySessionService`**: KYC live sessions
- **`reasoning_engines.AdkApp`**: HR agents deployed to Vertex AI Agent Engine
- **`LiveRequestQueue` + `StreamingMode.BIDI`**: KYC real-time audio/video streaming
