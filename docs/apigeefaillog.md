# Apigee AI Gateway — Deployment Failure Log & Lessons Learned

**Date:** 2026-04-04  
**Final status:** Proxy revision 8 — READY and deployed in `cymbal-prod`  
**Gateway hostname:** `ai-gateway.cymbalwealth.ak-demos.com/llm`

---

## Timeline of Failures

### Failure 1 — Wrong zip root path

**What happened:** First `zip` ran from the project root, producing paths like `apigee-proxy/apiproxy/policies/...` instead of the required `apiproxy/policies/...`. Apigee requires `apiproxy/` at the root of the zip.

**Error:** `zip entry in bundle has invalid path`

**Fix:** Re-ran `zip` from inside `apigee-proxy/` directory so the zip root is `apiproxy/`.

---

### Failure 2 — `StatisticsCollector` not supported in Apigee X

**What happened:** Added `StatisticsCollector` policy to record custom analytics dimensions. Apigee X PAYG does not support this policy type (it's available in Apigee Edge only).

**Error:** `"StatisticsCollector" is not a supported policy`

**Fix:** Replaced with `AssignMessage` (SC-RecordAnalytics) that wrote token counts to response headers instead.

---

### Failure 3 — Wrong `LogName` format in `MessageLogging`

**What happened:** Used `<LogName>cymbal-llm-audit</LogName>` — Apigee X requires the full Cloud Logging resource path.

**Error:** `LogName should be in the format "projects/<PROJECT>/logs/<LOG>"`

**Fix:** Changed to `<LogName>projects/general-ak/logs/cymbal-llm-audit</LogName>`

---

### Failure 4 — `hasExtensiblePolicy: true` → cannot deploy to BASE environment

**What happened:** Proxy flagged as extensible (due to `MessageLogging` with `CloudLogging`, and earlier JS policy). Base environments in Apigee X PAYG do not support extensible policies.

**Error:** `Extensible proxy can not be deployed to a base environment`

**Fix:**
1. Deleted the base `cymbal-prod` environment
2. Recreated it as `type: COMPREHENSIVE` (supports extensible policies including MessageLogging → CloudLogging)

> **Cost note:** COMPREHENSIVE environments cost more than BASE in Apigee X PAYG (~$225/month vs ~$75/month). For a demo this is acceptable.

---

### Failure 5 — JavaScript policy blocked on BASE environment (pre-fix-4)

**What happened:** Initially used a JavaScript policy (`JS-RewriteFallbackPath`) to rewrite the fallback target URL. JS policies are extensible and blocked on BASE environments.

**Error:** Same as Failure 4

**Fix:** Replaced JS with a simple `AssignMessage` policy that hardcodes the fallback URL (`gemini-3-flash-preview` at `global`). No JS needed.

---

### Failure 6 — RANGES_EXHAUSTED — no IP space for Apigee runtime instance

**What happened:** Attempted to create an Apigee runtime instance but the VPC had no reserved IP ranges large enough for a `/22` block.

**Error:** `RANGES_EXHAUSTED: reserve additional IP ranges in service networking as there is insufficient IP space`

**Fix:**
1. Found the correct VPC name: `project-general-ak` (not `default`)
2. Reserved `10.100.0.0/22` as a VPC peering range: `gcloud compute addresses create apigee-runtime-range --prefix-length=22 --network=project-general-ak`
3. Updated service networking VPC peering to include the new range alongside existing `database` and `private` ranges

---

### Failure 7 — Missing service account on deployment

**What happened:** First deploy attempt sent no service account identity with the request.

**Error:** `MISSING_SERVICE_ACCOUNT: Deployment requires a service account identity, but one was not provided`

**Fix:** Added `-d '{"serviceAccount": "apigee-llm-proxy-sa@general-ak.iam.gserviceaccount.com"}'` to the deployment API call.

---

### Failure 8 — `beans.MarshalFailure: argument type mismatch` (persistent, multi-iteration)

**What happened:** This was the hardest failure — it appeared on every revision from r2 through r7 regardless of policy changes, making it very hard to bisect.

**Error:** `instance "cymbal-runtime-us-central1" reported error beans.MarshalFailure: "java.lang.IllegalArgumentException: argument type mismatch"`

**Suspected causes investigated (all wrong):**
- `type="integer"` in `ExtractVariables` → changed to `type="string"` — did NOT fix
- Unquoted integer variables in JSON `MessageLogging` template → quoted them — did NOT fix
- `RaiseFault` with `StatusCode: 200` in FaultResponse (unusual) → removed — did NOT fix
- Regex condition `~~ ".*gemini-2\.0.*"` → changed to `Contains "gemini-2.0"` — did NOT fix
- `SC-RecordAnalytics` policy (AssignMessage writing integer variables as headers) → removed — did NOT fix
- All policies removed (bare proxy) → STILL failed

**Actual root cause found:** `<RetryOptions>` block in `vertex-us-central1.xml` target endpoint, specifically the `<RetryCondition>` containing flow variable expressions (`response.status.code = 500 or ...`). The Apigee X runtime could not marshal the condition expression into a Java bean at deployment time.

```xml
<!-- This caused the error: -->
<RetryOptions>
  <RetryCondition>response.status.code = 500 or response.status.code = 502</RetryCondition>
</RetryOptions>
```

**Fix:** Removed `RetryOptions` entirely from the target endpoint. Revision 7 (bare proxy, no RetryOptions) deployed successfully. Revision 8 (full policy set, no RetryOptions) deployed READY.

---

## What Was Removed vs. Original Plan

| Feature | Status | Reason |
|---|---|---|
| `StatisticsCollector` custom analytics | ❌ Removed | Not supported in Apigee X |
| JavaScript path rewriting for fallback | ❌ Removed | Replaced with hardcoded `AssignMessage` |
| `RetryOptions` on target endpoint | ❌ Removed | Caused beans.MarshalFailure at runtime |
| Circuit breaker (429 → fallback routing) | ❌ Left off | Requires complex RouteRule + variable tracking; ADK `ApigeeLlm` has built-in retry with exponential backoff — sufficient for demo |
| `AM-InjectServiceAccountToken` | ❌ Left off | Auth is handled by `ApigeeLlm` SDK natively |
| `AM-RewriteFallbackPath` | ❌ Left off | No active fallback routing without circuit breaker |
| `vertex-global` target endpoint | ❌ Left off | No active fallback routing |
| `SC-RecordAnalytics` (header-based) | ❌ Left off | Token data is in the AuditLog already |

## What IS Deployed (Revision 8 — READY)

| Feature | Status |
|---|---|
| `RF-DenyGemini20` — hard block on `gemini-2.0` in request path | ✅ Active |
| `EV-ExtractTokenUsage` — token counts from Vertex AI response | ✅ Active |
| `ML-AuditLog` — structured log to `projects/general-ak/logs/cymbal-llm-audit` | ✅ Active |
| Route to `gemini-2.5-flash` via `us-central1-aiplatform.googleapis.com` | ✅ Active |
| COMPREHENSIVE environment (`cymbal-prod`) | ✅ Active |
| Runtime instance `cymbal-runtime-us-central1` at `10.100.0.2` | ✅ Active |
| Environment group hostname `ai-gateway.cymbalwealth.ak-demos.com` | ✅ Configured |

---

## What's Left to Complete

### 1. Load Balancer + DNS — COMPLETED ✅

The Apigee runtime instance is at internal VPC IP `10.100.0.2`. Cloud Run services and Agent Engine cannot reach it directly. A Google Cloud Load Balancer is needed to expose it:

```bash
# Steps needed:
# 1. Create a global external HTTPS load balancer
# 2. Create a PSC NEG pointing to the Apigee service attachment
# 3. Create a managed SSL certificate for ai-gateway.cymbalwealth.ak-demos.com
# 4. Add an A record in DNS pointing the hostname to the LB IP

gcloud compute addresses create apigee-gateway-ip --global
gcloud compute ssl-certificates create apigee-ssl-cert \
  --domains=ai-gateway.cymbalwealth.ak-demos.com --global
# ... (backend service, URL map, forwarding rule)
```

Until LB + DNS is configured, `APIGEE_PROXY_URL=https://ai-gateway.cymbalwealth.ak-demos.com/llm` will not resolve.

**Alternative for internal testing:** Configure Cloud Run with Serverless VPC Access connector to reach `10.100.0.2` directly (requires the Apigee runtime's internal SSL cert to be trusted, which is complex).

### 2. Circuit Breaker / Fallback Routing

The plan called for automatic fallback to `gemini-3-flash-preview` (global) on 429/503. This was left off because:
- `RetryOptions` in target endpoints is broken (see Failure 8)
- Proper circuit breaker needs RouteRules with conditions, which requires runtime variable tracking across proxy flows
- The ADK `ApigeeLlm` SDK already has built-in retry (exponential backoff, 5 attempts, jitter) which covers most transient failures

**To implement later:** Use Apigee's `Raise Fault` → `Assign Message` (set routing variable) → second `Route Rule` with condition pattern, with a `Service Callout` to the fallback endpoint.

### 3. Model Armor

Not yet configured. Requires:
- Model Armor API enabled in the project
- A template created with prompt injection / jailbreak / sensitive data filters
- `ModelArmor` policy added to the proxy PreFlow

### 3. BigQuery + Looker Studio — COMPLETED ✅

**Dataset:** `general-ak.cymbal_ai_observability`

**Tables (auto-populated via Cloud Logging sinks):**
- `llm_calls` ← `cymbal-llm-audit` log (Apigee audit — every LLM call, token counts, latency)
- `kyc_sessions` ← `cymbal-kyc-sessions` log (KYC backend — per session outcome, audio duration)
- `loan_applications` ← `cymbal-homeloan-verification` log (home loan — per application outcome)

**Views (pre-built SQL for Looker Studio):**
- `workflow_cost_summary` — unified daily cost across all modules
- `kyc_cost_per_session` — per-session Gemini Live + verification token cost
- `investment_chat_cost` — per-query token cost and latency for Investments chatbot

**Key metrics available in Looker Studio:**
| Metric | Source view |
|---|---|
| Cost per completed KYC session | `kyc_cost_per_session` |
| Cost per home loan verification | `workflow_cost_summary` |
| Cost per investment chat query | `investment_chat_cost` |
| Daily token burn by module (`cymbal_app`) | `workflow_cost_summary` |
| KYC completion rate % | `workflow_cost_summary` |
| Avg verification latency | `workflow_cost_summary` |
| Error rate by service | `workflow_cost_summary` |

**To open Looker Studio:** Go to `lookerstudio.google.com` → Create → Report → BigQuery → dataset `cymbal_ai_observability`

### 4. Semantic Caching

Not yet configured. Requires:
- Vertex AI Vector Search index for embedding cache
- Vertex AI Embeddings API calls integrated into the proxy flow
- Custom Service Callout policies for cache lookup and write

---

## Key Lessons Learned

1. **Always validate the zip root.** Run `zip` from inside the proxy directory, not the parent.
2. **`StatisticsCollector` is Apigee Edge only** — not supported in Apigee X. Use `MessageLogging` or custom analytics via API instead.
3. **`RetryOptions` with `RetryCondition` causes runtime marshaling errors** in Apigee X. Use the ADK SDK's built-in retry instead.
4. **BASE vs COMPREHENSIVE environments:** If your proxy uses `MessageLogging → CloudLogging` or any Google Cloud integration policy, you need a COMPREHENSIVE environment.
5. **Bisect deployment errors methodically** — start with a bare proxy (no policies, minimal target), then add features one at a time. The marshaling error was in the target endpoint XML, not the policies.
6. **`ApigeeLlm` handles auth automatically** — no need for a custom token injection policy; the SDK passes Vertex AI credentials natively.
