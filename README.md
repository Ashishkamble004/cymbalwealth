# Cymbal Wealth — Video KYC

AI-powered Video KYC (Know Your Customer) application for Cymbal Wealth. Uses Google ADK with Gemini Live for real-time voice and video interaction during customer onboarding.

## Architecture

- **Backend**: FastAPI + WebSocket server with Google ADK bidirectional streaming
- **Frontend**: React + Vite + Tailwind CSS
- **Agent**: Gemini Live (`gemini-live-2.5-flash-preview-native-audio-09-2025`) for voice/video KYC
- **Sub-agent**: Gemini 2.5 Flash for document verification via tools

## Project Structure

```
backend/
  main.py                  # FastAPI + WebSocket endpoint
  storage_utils.py         # Cloud Storage utilities
  Dockerfile
  requirements.txt
  kyc_agent/
    agent.py               # Root KYC agent (Gemini Live)
    sub_agents/
      verification_agent.py # Document verification sub-agent with tools

frontend/
  App.tsx                  # Main app (Login → KYC Session)
  index.html               # Entry HTML with Tailwind CDN
  components/
    LoginPage.tsx           # Customer reference number login
    KYCSession.tsx          # Video KYC session (video + chat)
    VerificationStatus.tsx  # Verification progress overlay
  hooks/
    useLiveSessionWebSocket.ts  # WebSocket + audio/video handler
  utils/
    audioUtils.ts           # PCM encoding utilities

cloudbuild.yaml            # Cloud Build for Cloud Run deployment
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Google Cloud ADC: `gcloud auth application-default login`

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Runs on `http://localhost:8080`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:3000` with WebSocket proxy to backend.

## Demo Reference Numbers

| Reference | Customer |
|-----------|----------|
| CW-2026-001 | Ashish Kamble |
| CW-2026-002 | Priya Sharma |

## Deploy to Cloud Run

```bash
gcloud builds submit --config=cloudbuild.yaml
```

Ensure the Artifact Registry repository `cymbal-wealth` exists in `us-central1`.
