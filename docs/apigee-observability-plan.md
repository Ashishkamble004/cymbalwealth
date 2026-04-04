# Apigee AI Gateway + Full Observability Plan
## Cymbal Wealth — LLMOps, Model Routing & KYC Observability

**Status:** In Progress — Phase 1 deployment started  
**Last Updated:** 2026-04-04  
**Project:** `general-ak` (GCP)

---

## Model Policy (Non-Negotiable)

| Rule | Detail |
|---|---|
| **Never use** | Any `gemini-2.0-*` model — in code, routing, or fallback |
| **Primary model** | `gemini-2.5-flash` — `us-central1` |
| **Fallback model** | `gemini-3-flash-preview` — `global` region **only** (not available in us-central1 or any other specific region) |
| **Fallback trigger** | HTTP 429 (quota exceeded) or 503 from primary |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CYMBAL WEALTH AI GATEWAY                      │
│                                                                   │
│  Home Loan Agent  ──┐                                            │
│  Investments Chat ──┼──► Apigee AI Gateway ──► gemini-2.5-flash │
│  (Future agents)  ──┘    (ai-gateway.cymbal    (us-central1)    │
│                            wealth.ak-demos.com)      │           │
│                                               429/503 ↓           │
│                                          gemini-3-flash-preview  │
│                                               (global only)       │
│                                                                   │
│  KYC (Gemini Live WebSocket) ── Cannot go through Apigee ──────  │
│       └──► OTel spans ──► Cloud Trace                            │
│       └──► Structured logs ──► Cloud Logging                     │
│       └──► Log-based metrics ──► Cloud Monitoring                │
│                                                                   │
│  All paths ──► Cloud Logging                                      │
│                    └──► [FUTURE] BigQuery ──► Looker Studio      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Apigee Provisioning

### 1.1 Enable APIs

```bash
gcloud services enable \
  apigee.googleapis.com \
  apigeeconnect.googleapis.com \
  apigeeregistry.googleapis.com \
  cloudkms.googleapis.com \
  servicenetworking.googleapis.com \
  --project=general-ak
```

### 1.2 Provision Apigee X Organisation (~40 min)

```bash
gcloud apigee organizations provision \
  --project=general-ak \
  --authorized-network=default \
  --runtime-location=us-central1 \
  --analytics-region=us-central1
```

### 1.3 Create Environment and Environment Group

```bash
# Environment
gcloud apigee environments create cymbal-prod \
  --organization=general-ak

# Environment group (public hostname)
gcloud apigee envgroups create cymbal-ai-gateway \
  --organization=general-ak \
  --hostnames=ai-gateway.cymbalwealth.ak-demos.com

# Attach environment
gcloud apigee envgroups attachments create \
  --organization=general-ak \
  --envgroup=cymbal-ai-gateway \
  --environment=cymbal-prod
```

### 1.4 Service Account

```bash
gcloud iam service-accounts create apigee-llm-proxy-sa \
  --display-name="Apigee LLM Proxy SA"

gcloud projects add-iam-policy-binding general-ak \
  --member="serviceAccount:apigee-llm-proxy-sa@general-ak.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding general-ak \
  --member="serviceAccount:apigee-llm-proxy-sa@general-ak.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

---

## Phase 2 — Apigee AI Gateway Proxy Configuration

### 2.1 Proxy Structure

```
apigee-proxy/
├── apiproxy/
│   ├── cymbal-llm-gateway.xml
│   ├── proxies/default.xml
│   ├── targets/
│   │   ├── vertex-us-central1.xml     # gemini-2.5-flash (primary)
│   │   └── vertex-global.xml          # gemini-3-flash-preview (fallback)
│   └── policies/
│       ├── TokenAuth.xml
│       ├── DenyGemini20.xml           # Hard block on any gemini-2.0-* request
│       ├── ExtractTokenUsage.xml
│       ├── RecordAnalytics.xml
│       ├── AuditLog.xml
│       ├── CircuitBreaker.xml
│       ├── ModelArmor.xml
│       └── SemanticCache.xml
```

### 2.2 Target Endpoints

**Primary** (`vertex-us-central1.xml`):
```
https://us-central1-aiplatform.googleapis.com/v1/projects/general-ak/
  locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
```

**Fallback** (`vertex-global.xml`):
```
https://aiplatform.googleapis.com/v1/projects/general-ak/
  locations/global/publishers/google/models/gemini-3-flash-preview:generateContent
```

> **Critical:** `gemini-3-flash-preview` is ONLY available via the `global` location endpoint.
> It is NOT available in `us-central1`, `europe-west4`, or any other specific region.

### 2.3 Circuit Breaker — Routing Policy

```xml
<!-- CircuitBreaker.xml -->
<FaultRules>
  <FaultRule name="QuotaExhausted">
    <Condition>response.status.code = 429 or response.status.code = 503</Condition>
    <Step><Name>SetFallbackTarget</Name></Step>
  </FaultRule>
</FaultRules>
```

### 2.4 Model Deny Policy (Hard Block on Gemini 2.0)

```xml
<!-- DenyGemini20.xml — applied before routing -->
<RaiseFault name="DenyGemini20">
  <Condition>request.content ~~ ".*gemini-2.0.*"</Condition>
  <FaultResponse>
    <Set>
      <StatusCode>400</StatusCode>
      <Payload>{"error": "gemini-2.0 models are not permitted"}</Payload>
    </Set>
  </FaultResponse>
</RaiseFault>
```

### 2.5 Token Analytics

```xml
<!-- ExtractTokenUsage.xml -->
<ExtractVariables>
  <JSONPayload>
    <Variable name="prompt_tokens" type="integer">$.usageMetadata.promptTokenCount</Variable>
    <Variable name="completion_tokens" type="integer">$.usageMetadata.candidatesTokenCount</Variable>
    <Variable name="total_tokens" type="integer">$.usageMetadata.totalTokenCount</Variable>
  </JSONPayload>
</ExtractVariables>
```

### 2.6 Audit Logging to Cloud Logging

```xml
<!-- AuditLog.xml -->
<MessageLogging>
  <CloudLogging>
    <LogName>cymbal-llm-audit</LogName>
    <Message>{
      "app": "{request.header.x-cymbal-app}",
      "model_primary": "gemini-2.5-flash",
      "model_used": "{target.name}",
      "fallback_triggered": "{circuit_breaker_fired}",
      "prompt_tokens": {prompt_tokens},
      "completion_tokens": {completion_tokens},
      "total_tokens": {total_tokens},
      "latency_ms": {target.elapsed.time},
      "cache_hit": "{semantic_cache_hit}",
      "status": {response.status.code},
      "timestamp": "{system.timestamp}"
    }</Message>
  </CloudLogging>
</MessageLogging>
```

### 2.7 Semantic Caching (Investments chatbot — first rollout)

1. On request: compute embedding via Vertex AI Embeddings → query Vertex AI Vector Search (cosine similarity > 0.92)
2. Cache hit: return cached response, log `cache_hit: true`, skip LLM call (~50ms latency)
3. Cache miss: forward to Gemini 2.5 Flash → store response + embedding in Vector Search

**Expected cache hit rate for Investments chatbot:** 40–60% (demo queries are highly repetitive — same stocks asked repeatedly)

### 2.8 Model Armor (Public-facing endpoints)

Applied to Investments chatbot and all future customer-facing agents:

```xml
<!-- ModelArmor.xml -->
<ModelArmor>
  <TemplateId>cymbal-wealth-armor</TemplateId>
  <Actions>
    <OnPromptViolation>BLOCK</OnPromptViolation>
    <OnResponseViolation>SANITIZE</OnResponseViolation>
  </Actions>
  <Filters>
    <Filter>PROMPT_INJECTION</Filter>
    <Filter>JAILBREAK</Filter>
    <Filter>SENSITIVE_DATA_PROTECTION</Filter>
  </Filters>
</ModelArmor>
```

---

## Phase 3 — ADK Agent Integration

### 3.1 Home Loan Agent (Agent Engine)

**File:** `backend/home_loan_agents/orchestrator.py`

```python
from google.adk.models.apigee_llm import ApigeeLlm
import os

def _apigee_model(app_label: str) -> ApigeeLlm:
    return ApigeeLlm(
        model="apigee/vertex_ai/gemini-2.5-flash",
        proxy_url=os.environ["APIGEE_PROXY_URL"],
        custom_headers={"x-cymbal-app": app_label}
    )

doc_quality_agent         = Agent(model=_apigee_model("home-loan-doc-quality"), ...)
identity_income_agent     = Agent(model=_apigee_model("home-loan-identity"), ...)
property_eligibility_agent = Agent(model=_apigee_model("home-loan-eligibility"), ...)
```

**Agent Engine env vars** (`backend/home_loan_agents/.agent_engine_config.json`):
```json
{
  "env_vars": {
    "APIGEE_PROXY_URL": "https://ai-gateway.cymbalwealth.ak-demos.com/llm",
    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
    "HOME_LOAN_MODEL": "gemini-2.5-flash"
  }
}
```

### 3.2 Investments MCP Server (Cloud Run)

**File:** `backend/mcp_server/sse_wrapper.py`

Replace `_run_gemini_chat` — swap direct `google-genai` client with `ApigeeLlm`-backed ADK runner.

**Cloud Run env vars** added to `deploy/cloudbuild-mcp.yaml`:
```yaml
"APIGEE_PROXY_URL=https://ai-gateway.cymbalwealth.ak-demos.com/llm"
```

---

## Phase 4 — KYC Observability (Gemini Live — No Apigee)

Gemini Live uses bidirectional WebSocket. Apigee is an HTTP/REST proxy — it **cannot** intercept WebSocket traffic. KYC observability is handled entirely in the application layer.

### 4.1 OpenTelemetry to Cloud Trace

```python
# backend/main.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(
    CloudTraceSpanExporter(project_id="general-ak")
))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("cymbal-kyc")
```

### 4.2 Session Spans at Each Verification Step

```python
# Wraps each KYC milestone in a child span
with tracer.start_as_current_span("kyc_session") as session_span:
    session_span.set_attribute("kyc.reference_number", ref)
    session_span.set_attribute("kyc.model", "gemini-live-2.5-flash-native-audio")

    with tracer.start_as_current_span("kyc.verify_pan") as pan_span:
        result = verify_pan(ref, pan_number)
        pan_span.set_attribute("kyc.pan_verified", result.verified)

    # Same pattern for: verify_aadhaar, verify_dob, capture_photo, verify_face,
    #                   capture_signature, complete_kyc
```

### 4.3 Structured Session Summary Log

```python
# Logged to Cloud Logging at session end
logger.log_struct({
    "reference_number": ref,
    "session_duration_seconds": duration,
    "model": "gemini-live-2.5-flash-native-audio",
    "language_detected": "hindi",
    "steps": {
        "pan_verified": True,
        "aadhaar_verified": True,
        "face_verified": True,
        "signature_verified": True,
        "kyc_complete": True
    },
    "audio_duration_seconds": audio_seconds,
    "completion_status": "success"   # or "abandoned" / "failed"
})
```

### 4.4 Cloud Monitoring Dashboard (KYC)

Log-based metrics derived automatically from structured logs:

| Metric | Source field | Use |
|---|---|---|
| `kyc/completion_rate` | `completion_status == "success"` | Primary KPI |
| `kyc/session_duration_p50` | `session_duration_seconds` | Experience quality |
| `kyc/step_failure_rate` | each `steps.*` field | Identify friction points |
| `kyc/active_sessions` | WebSocket connection count | Capacity planning |
| `kyc/audio_minutes_total` | `audio_duration_seconds` | Cost proxy for Gemini Live |

---

## Phase 5 — Observability Stack

### What Apigee Native Provides (Included, No Extra Setup)

| Capability | Retention |
|---|---|
| Request volume by app / model | 90 days |
| Token usage (prompt + completion + thoughts) | 90 days |
| Latency percentiles p50/p95/p99 | 90 days |
| Error rate by model + HTTP status | 90 days |
| Circuit breaker firing events | 90 days |
| Semantic cache hit rate | 90 days |
| Per-developer / per-app breakdown | 90 days |

### KYC via Cloud Monitoring (Included, No Extra Setup)

- Custom dashboards on log-based metrics
- Alert policies: completion rate < 80%, session duration > 10 min, step failure spike
- Uptime checks on KYC backend endpoint

---

## [FUTURE] BigQuery + Looker Studio

> **Current status:** Not implemented. Apigee Analytics + Cloud Monitoring is sufficient for the demo.
> Add BigQuery when moving toward production or when Apigee 90-day retention is insufficient.

### Why BigQuery Is Needed

1. **Cross-source correlation** — Apigee stores LLM call data, Cloud Logging stores KYC session data, Agent Engine emits traces. There is no native way to join these in a single query without BigQuery. Example: "What is the total token cost per completed home loan application end-to-end?" requires joining Apigee token counts with Agent Engine session IDs — only possible in BigQuery.

2. **Retention > 90 days** — Apigee Analytics has a 90-day retention cap. For financial services audit requirements (RBI, SEBI), LLM interaction logs may need to be kept 1–7 years. BigQuery supports indefinite retention at low cost.

3. **Business-level metrics** — Apigee measures "API calls and tokens." BigQuery lets you compute "cost per KYC session completed," "cost per home loan approved," "ROI per AI module" by joining LLM costs with business outcomes.

4. **Ad-hoc SQL analysis** — When debugging a model quality issue or cost spike, SQL queries on BigQuery are far more flexible than Apigee's fixed dashboard dimensions.

### Where Looker Studio Helps

Looker Studio (free, connects directly to BigQuery) provides:

| Dashboard | Contents |
|---|---|
| **Executive** | Total AI cost by day/module, token burn rate trend, model routing ratio |
| **KYC Operations** | Completion funnel, avg duration, step-by-step drop-off, language breakdown |
| **Model Health** | Primary vs fallback routing ratio, cache hit rate, latency by model, quality flags from Model Armor |
| **Home Loan Pipeline** | Cost per verification run, sub-agent timing, approval rate |

### Implementation (when ready)

```bash
# Cloud Logging sink → BigQuery
gcloud logging sinks create cymbal-ai-bigquery \
  bigquery.googleapis.com/projects/general-ak/datasets/cymbal_observability \
  --log-filter='logName=("cymbal-llm-audit" OR "cymbal-kyc-sessions")'
```

BigQuery tables auto-created: `apigee_llm_calls`, `kyc_sessions`  
Looker Studio: connect to `general-ak.cymbal_observability` dataset.

---

## Implementation Sequence

| Week | Phase | Work |
|---|---|---|
| 1 | Phase 1 | Apigee provisioning + environment setup |
| 1 | Phase 2 | Deploy proxy + routing + token analytics + deny policy |
| 2 | Phase 3 | Swap Home Loan + Investments to `ApigeeLlm`, redeploy |
| 3 | Phase 4 | KYC OpenTelemetry instrumentation + Cloud Monitoring dashboard |
| 3 | Phase 2 | Model Armor + Semantic Cache (add-ons) |
| Future | Phase 5 | BigQuery sink + Looker Studio dashboards |

---

## Services Affected

| Service | Cloud Run URL | Change |
|---|---|---|
| `homeloan-backend` | `homeloan-backend-mcj3w7ujpq-uc.a.run.app` | Model → ApigeeLlm, redeploy Agent Engine |
| `nse-bse-mcp-server` | `nse-bse-mcp-server-mcj3w7ujpq-uc.a.run.app` | `_run_gemini_chat` → ApigeeLlm, redeploy |
| `kyc-backend` | `kyc-backend-mcj3w7ujpq-uc.a.run.app` | Add OTel instrumentation, structured logging |
| `kyc-frontend` | `kyc-frontend-mcj3w7ujpq-uc.a.run.app` | No change |
| `demo-portal` | `demo-portal-mcj3w7ujpq-uc.a.run.app` | No change |
