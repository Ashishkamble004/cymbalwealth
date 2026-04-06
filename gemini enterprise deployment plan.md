# Gemini Enterprise — HR & PeopleOps Agent Deployment Plan

> **Scope:** Build and deploy the 82 HR & PeopleOps agents from the Agentic Transformation Field Kit onto the Gemini Enterprise platform.
> **Author reference:** Shanky Ram, Principal Architect, Google Cloud APAC
> **Target:** Banks and FSI organizations deploying Gemini Enterprise Standard/Plus edition

---

## 1. Platform Architecture Overview

Gemini Enterprise is built on these core primitives:

| Concept | What It Is | HR Relevance |
|---|---|---|
| **Data Sources** | Google + third-party connectors | HRIS, ATS, LMS, payroll, SharePoint, Confluence |
| **Data Stores** | Per-entity indexed repositories | HR policies, job descriptions, org charts, handbooks |
| **App** | The Gemini Enterprise deployment unit | One app per BU or one enterprise-wide app |
| **Assistant** | Grounded chat UI with citations | Employee-facing Q&A, manager self-service |
| **Actions** | Write-back to connected systems | Create calendar events, update Jira, ServiceNow tickets |
| **Agents** | Purpose-built automation units | The 82 HR agents from the Field Kit |
| **Analytics** | Looker-powered usage dashboard | Track adoption, query patterns, agent performance |

### Agent Implementation Layers (from Field Kit)

```
┌─────────────────────────────────────────────────────────┐
│              Gemini Enterprise Web App / API            │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Out-of-the-box Gemini Enterprise Features     │  ← No code
│  Layer 2: Agent Designer + Third-Party Connectors       │  ← Low code
│  Layer 3: Custom ADK Agents on Vertex AI Agent Engine   │  ← Code required
│  Layer 4: Data Agents (BigQuery + Vertex AI Analytics)  │  ← Data engineering
├─────────────────────────────────────────────────────────┤
│  Data Stores: HRIS | ATS | LMS | Payroll | Docs | BQ   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites & Platform Setup

### 2.1 Google Cloud Setup

```bash
# Required roles
- Discovery Engine Admin          # Register and manage agents
- Vertex AI User                  # Deploy ADK agents to Agent Engine
- BigQuery Data Viewer            # Data agents
- Secret Manager Secret Accessor  # Store HRIS/ATS credentials

# Enable required APIs
gcloud services enable \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 2.2 Gemini Enterprise Subscription

- Provision **Standard or Plus** edition (Frontline for branch staff)
- Assign licenses to HR personas: CHRO, HRBP, Recruiter, HR Ops, L&D, ER Specialist, Payroll, DEI, People Analytics, HRIS Analyst
- Create the Gemini Enterprise **App** in Google Cloud Console → Gemini Enterprise

### 2.3 Identity & Security

```bash
# Configure identity provider (SSO)
# Map external identities for data access control
# Enable Model Armor via REST API (required for custom ADK agents)
# Set VPC Service Controls if data sovereignty is required (banks)
# Configure custom organization policies for data residency
```

---

## 3. Data Store Setup (Connect HR Systems)

Each HR system must be connected as a data store before agents can query it.

### 3.1 Google-Native Data Sources (built-in connectors)

| Data Source | Data Store Contents | HR Use |
|---|---|---|
| **Google Drive** | HR policy docs, handbooks, SOPs, job descriptions | Policy Q&A, onboarding |
| **Google Calendar** | Interview schedules, review cycles | Interview Scheduling Agent |
| **Gmail** | HR correspondence | Communication analytics |
| **Google Chat** | HR helpdesk threads | Service delivery analytics |
| **BigQuery** | Workforce analytics, attrition data, payroll | Data agents, predictive models |
| **Cloud Storage** | Resume files, org charts, training content | Resume screening, L&D |

Setup via Console: Gemini Enterprise → App → Data → Add Data Source → Select source → Authenticate → Sync

### 3.2 Third-Party HR System Connectors

| System | Connector | Data Entities |
|---|---|---|
| **Workday / SAP SuccessFactors** | Custom connector (REST API) | Employee records, org hierarchy, compensation bands |
| **Greenhouse / Lever** (ATS) | Custom connector | Requisitions, candidate pipeline, interview feedback |
| **ADP / Darwinbox** (Payroll) | Custom connector | Payroll runs, leave balances, compliance data |
| **Cornerstone / Degreed** (LMS) | Custom connector | Training completions, skills, certifications |
| **ServiceNow** | Built-in connector (Private Preview) | HR tickets, case management |
| **Confluence / SharePoint** | Built-in connectors | HR wikis, policy documents |
| **Jira** | Built-in connector | HR project tracking, compliance tickets |

For custom connectors (Workday, ADP, Greenhouse):
```bash
# Create custom connector via REST
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: PROJECT_ID" \
  "https://LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/LOCATION/collections/default_collection/dataConnectors" \
  -d '{
    "dataSource": "CUSTOM",
    "displayName": "Workday HRIS",
    "params": { ... }
  }'
```

---

## 4. Agent Implementation by Layer

### Layer 1 — Out-of-the-Box (No Code)

These agents are enabled purely by connecting the right data stores and configuring the assistant. No development required.

| Agent | Data Store Required | Configuration |
|---|---|---|
| **Policy Q&A Assistant** | Google Drive (HR policy folder) | Connect Drive → enable assistant grounding |
| **New Hire Q&A Assistant** | Drive (onboarding docs) + Confluence | Scoped to onboarding data store |
| **Benefits Q&A & Enrollment Assistant** | Drive (benefits docs) + SharePoint | Connect, restrict access to employees only |
| **Compliance Training Content Generator** | Drive (training materials) | Enable assistant with generative features |
| **Leave & Accommodation Policy Q&A** | Drive (leave policy) | Scoped assistant with policy docs |
| **Employee Communication Drafter** | Gemini in Workspace (Gmail/Docs) | No data store needed — native Gemini feature |

**Setup steps:**
1. Console → Gemini Enterprise → App → Data → Add Google Drive data store
2. Point to the HR policy folder with appropriate access controls
3. Console → App → Assistant → Configure preamble (e.g., "You are an HR policy assistant...")
4. Enable citations so employees see source documents

---

### Layer 2 — Agent Designer with Connectors (Low Code)

Built using Gemini Enterprise's Agent Designer UI with third-party system connectors and actions.

**Key agents in this layer:**

#### A. Employee Query Resolution Agent
- **Connects to:** ServiceNow (HR ticketing) + Google Drive (policy docs)
- **Capability:** Auto-resolves Tier 0/1 HR queries; escalates Tier 2 with full context
- **Action:** Creates/updates ServiceNow tickets on behalf of the employee
- **Setup:** Agent Designer → New Agent → Connect ServiceNow data store → Add action: Create Ticket → Write agent instructions

#### B. Interview Scheduling & Coordination Agent
- **Connects to:** Google Calendar + Greenhouse ATS (custom connector)
- **Action:** Creates calendar events, sends invites, updates ATS candidate stage
- **Setup:** Agent Designer → Connect Calendar + ATS → Enable Calendar write action

#### C. Onboarding Orchestration Agent
- **Connects to:** Google Drive (onboarding docs) + ServiceNow (IT tickets) + Workday (employee record)
- **Capability:** Guides new hire through checklist, triggers IT provisioning tickets, answers questions
- **Action:** Creates ServiceNow tickets, updates Workday onboarding status

#### D. Compliance Tracking & Escalation Agent
- **Connects to:** Cornerstone LMS + HRIS + ServiceNow
- **Capability:** Monitors mandatory training completion; sends reminders; escalates overdue cases
- **Action:** Creates escalation tickets in ServiceNow

---

### Layer 3 — Custom ADK Agents on Vertex AI Agent Engine (Full Code)

These are the most powerful agents, built using Google's Agent Development Kit (ADK), deployed to Vertex AI Agent Engine, then registered with Gemini Enterprise.

#### End-to-End Build & Deploy Flow

```
1. Build agent with ADK (Python)
        ↓
2. Deploy to Vertex AI Agent Engine
        ↓
3. Register agent with Gemini Enterprise app via Console or REST API
        ↓
4. Configure permissions and Model Armor
        ↓
5. Expose to HR personas via Gemini Enterprise web app
```

#### Step 1 — Build an ADK Agent (Example: 1:1 Meeting Prep Agent)

```python
# agent.py
from google.adk.agents import Agent
from google.adk.tools import google_search, function_tool
import vertexai
from google.cloud import bigquery

# Tool: Pull employee performance data from BigQuery
@function_tool
def get_employee_performance_data(employee_id: str) -> dict:
    """Retrieves recent performance data, OKR progress, and feedback for an employee."""
    client = bigquery.Client()
    query = f"""
        SELECT
            e.name, e.role, e.team,
            o.okr_title, o.progress_pct, o.status,
            f.feedback_text, f.submitted_by, f.submitted_date
        FROM `project.hr_data.employees` e
        LEFT JOIN `project.hr_data.okrs` o ON e.id = o.employee_id
        LEFT JOIN `project.hr_data.feedback` f ON e.id = f.employee_id
        WHERE e.id = '{employee_id}'
          AND f.submitted_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        ORDER BY f.submitted_date DESC
    """
    results = client.query(query).result()
    return [dict(row) for row in results]

# Tool: Pull attrition risk score from ML model
@function_tool
def get_flight_risk_score(employee_id: str) -> dict:
    """Returns current attrition risk score and key drivers for an employee."""
    client = bigquery.Client()
    query = f"""
        SELECT risk_score, risk_level, top_drivers
        FROM `project.hr_data.attrition_predictions`
        WHERE employee_id = '{employee_id}'
        ORDER BY prediction_date DESC LIMIT 1
    """
    results = client.query(query).result()
    return [dict(row) for row in results]

# Define the agent
meeting_prep_agent = Agent(
    name="1_1_meeting_prep_agent",
    model="gemini-2.0-flash",
    description="Prepares personalized 1:1 meeting agendas for managers by pulling employee OKR progress, recent feedback, and flight-risk signals.",
    instruction="""
        You are a 1:1 Meeting Prep Agent for HR Business Partners and managers.
        When given an employee ID:
        1. Pull their performance data, OKR progress, and recent feedback
        2. Check their flight risk score and key attrition drivers
        3. Generate a structured meeting agenda with:
           - OKR progress summary
           - Feedback themes to discuss
           - Retention risk flags (if applicable)
           - Suggested coaching questions
        Keep the output concise and actionable. Do not expose raw risk scores to the manager.
    """,
    tools=[get_employee_performance_data, get_flight_risk_score]
)
```

```python
# deploy.py — Deploy to Vertex AI Agent Engine
import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="PROJECT_ID", location="us-central1")

# Deploy the agent
remote_agent = reasoning_engines.ReasoningEngine.create(
    meeting_prep_agent,
    requirements=["google-cloud-bigquery", "google-adk"],
    display_name="1:1 Meeting Prep Agent",
    description="Prepares 1:1 meeting agendas with OKR, feedback, and flight-risk context"
)

print(f"Agent deployed: {remote_agent.resource_name}")
# Output: projects/PROJECT_ID/locations/us-central1/reasoningEngines/AGENT_ENGINE_ID
```

#### Step 2 — Register with Gemini Enterprise

```bash
# Via REST API
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: PROJECT_ID" \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/assistants/default_assistant/agents" \
  -d '{
    "displayName": "1:1 Meeting Prep Agent",
    "description": "Prepares personalized 1:1 meeting agendas for managers using OKR progress, feedback, and flight-risk signals. Trigger by asking: Prepare my 1:1 with [employee name].",
    "icon": {
      "uri": "https://fonts.gstatic.com/s/i/googlematerialicons/people/v15/24px.svg"
    },
    "adkAgentDefinition": {
      "provisionedReasoningEngine": {
        "reasoningEngine": "projects/PROJECT_ID/locations/us-central1/reasoningEngines/AGENT_ENGINE_ID"
      }
    }
  }'
```

> **Note:** The `description` field is used by the LLM to decide when to invoke this agent. Write it as a clear trigger description — include example user queries.

#### Step 3 — Configure Model Armor (required for banks/FSI)

```python
# Model Armor must be configured in agent code — NOT in the console
# Add to agent initialization

from google.adk.agents import Agent
from google.adk.safety import ModelArmorConfig

meeting_prep_agent = Agent(
    name="1_1_meeting_prep_agent",
    model="gemini-2.0-flash",
    safety_config=ModelArmorConfig(
        block_sensitive_pii=True,       # Block SSN, account numbers
        block_harmful_content=True,
        audit_logging=True              # Required for FSI compliance
    ),
    # ... rest of config
)
```

#### Key ADK Agents to Build — Priority List

| Agent | Data Sources | Key Tools | Complexity |
|---|---|---|---|
| **Workforce Scenario Modeling Agent** | BigQuery (headcount, attrition) | BQ query, Vertex AI forecasting | High |
| **Resume Screening & Shortlisting Agent** | Greenhouse ATS + Drive (JDs) | ATS API, semantic similarity scoring | High |
| **Offer Package Modeler Agent** | Workday (comp bands) + BQ (benchmarks) | BQ query, comp band lookup | Medium |
| **1:1 Meeting Prep Agent** | BigQuery (OKR, feedback, risk scores) | BQ query, risk score API | Medium |
| **Requisition Intake & Validation Agent** | Workday (headcount plan) + ATS | Workday API, ATS API | Medium |
| **Payroll Reconciliation & Compliance Agent** | ADP + HRIS | ADP API, diff engine | High |
| **Calibration Analytics Agent** | BigQuery (performance ratings) | BQ query, bias detection | High |
| **Attrition Prediction & Intervention Agent** | BigQuery (ML predictions) | BQ query, intervention lookup | Medium |
| **Successor Readiness Assessment Agent** | HRIS + BQ (9-box data) | HRIS API, BQ query | Medium |
| **Pay Equity Audit Agent** | BQ (comp data) + Workday | Regression model, BQ query | High |

---

### Layer 4 — Data Agents (BigQuery + Vertex AI)

These agents run against the HR data lake in BigQuery, enabling natural language querying of workforce data.

#### HR Data Lake Schema (BigQuery)

```sql
-- Core tables required for data agents
hr_data.employees          -- Employee master: id, name, role, level, team, location, start_date
hr_data.org_hierarchy      -- Manager-report relationships, org tree
hr_data.compensation       -- Salary, band, equity, bonus, last_review_date
hr_data.performance        -- Review cycles, ratings, calibration outcomes
hr_data.okrs               -- Goals, OKR progress, alignment
hr_data.feedback           -- 360 feedback, check-in notes
hr_data.attrition_history  -- Exits, reasons, regrettable/non-regrettable
hr_data.attrition_predictions  -- ML model outputs: risk score, drivers
hr_data.learning           -- Training completions, certifications, skills
hr_data.payroll            -- Pay runs, deductions, compliance flags
hr_data.leave              -- Leave balances, utilization, patterns
hr_data.requisitions       -- Open roles, time-to-fill, source of hire
hr_data.candidates         -- Pipeline, stage, offer status, diversity funnel
```

#### HR Data Lake Query Agent

```python
# data_agent.py — Natural language to BigQuery
from google.adk.agents import Agent
from google.adk.tools import function_tool
from google.cloud import bigquery
import json

@function_tool
def query_hr_data_lake(sql_query: str) -> list:
    """Executes a SQL query against the HR BigQuery data lake and returns results."""
    client = bigquery.Client()
    # Safety: restrict to read-only, HR dataset only
    if any(kw in sql_query.upper() for kw in ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE']):
        return [{"error": "Only SELECT queries are permitted"}]
    results = client.query(sql_query).result()
    return [dict(row) for row in results]

hr_data_agent = Agent(
    name="hr_data_lake_query_agent",
    model="gemini-2.0-flash",
    description="Answers workforce analytics questions by querying the HR data lake. Use for headcount, attrition, compensation, performance, and diversity metrics.",
    instruction="""
        You are the HR Data Lake Query Agent. You translate natural language workforce 
        questions into BigQuery SQL and return structured insights.
        
        Available tables: hr_data.employees, hr_data.compensation, hr_data.performance,
        hr_data.attrition_history, hr_data.attrition_predictions, hr_data.leave,
        hr_data.requisitions, hr_data.candidates, hr_data.okrs, hr_data.learning
        
        Always:
        - Add appropriate WHERE clauses to scope data to the requesting user's org (if HRBP)
        - Format numbers clearly (percentages, currency)
        - Provide trend context where possible (vs last quarter/year)
        - Flag data quality issues if row counts seem anomalous
        
        Never expose: Individual compensation without appropriate access level.
        Never run: Any DML queries (INSERT/UPDATE/DELETE).
    """,
    tools=[query_hr_data_lake]
)
```

---

## 5. Phased Rollout Plan

### Phase 1 — Foundation (Months 1-3)
**Goal:** Establish the platform, connect data, deliver quick wins for the broadest user base.

| Week | Action |
|---|---|
| 1-2 | Provision Gemini Enterprise app, assign licenses, configure SSO/IdP |
| 2-3 | Connect Google Drive data stores (HR policies, handbooks, onboarding docs) |
| 3-4 | Configure assistant with HR preamble, enable Policy Q&A and New Hire Q&A |
| 4-6 | Connect ServiceNow (HR ticketing); build Employee Query Resolution Agent via Agent Designer |
| 6-8 | Connect Confluence/SharePoint for additional knowledge sources |
| 8-12 | Deploy Layer 1 agents to all HR staff; collect usage analytics |

**Agents delivered:** Policy Q&A, New Hire Q&A, Benefits Q&A, Employee Query Resolution
**Users impacted:** All employees (self-service), HR Ops team

---

### Phase 2 — Expansion (Months 3-6)
**Goal:** Connect core HR systems, deploy recruiting and performance agents.

| Action | Agents Delivered |
|---|---|
| Connect Greenhouse/ATS (custom connector) | Requisition Intake Agent, Resume Screening Agent, Sourcing Channel Analytics Agent |
| Connect Google Calendar + enable actions | Interview Scheduling & Coordination Agent |
| Build and deploy 1:1 Meeting Prep Agent (ADK) | 1:1 Meeting Prep Agent, Feedback Trend Analyzer |
| Build Offer Package Modeler Agent (ADK) | Offer Package Modeler Agent |
| Connect Workday/HRIS (custom connector) | Job Description Generator, Org Structure Analyzer |
| Deploy Onboarding Orchestration Agent | Onboarding Orchestration Agent, Pre-boarding Orchestration Agent |

**Users impacted:** Recruiters, HRBPs, Hiring Managers

---

### Phase 3 — Intelligence (Months 6-9)
**Goal:** Activate the BigQuery data lake, deploy predictive and analytics agents.

| Action | Agents Delivered |
|---|---|
| Set up HR BigQuery data lake (ETL from HRIS/ATS/LMS) | HR Data Lake Query Agent |
| Build and deploy Attrition Prediction Agent | Attrition Prediction & Intervention Agent, Workforce Cost Modeling Agent |
| Build Pay Equity Audit Agent | Pay Equity Audit Agent, Market Benchmarking Analysis Agent |
| Deploy Performance & Succession agents | Calibration Analytics Agent, Successor Readiness Assessment Agent, HiPo Identification Agent |
| Build Payroll Reconciliation Agent (ADP integration) | Payroll Reconciliation & Compliance Agent, Payroll Input Validation Agent |
| Deploy DEI agents | DEI Dashboard & Reporting Agent, Inclusive Hiring Audit Agent |

**Users impacted:** People Analytics, CHROs, Compensation, Compliance

---

### Phase 4 — Optimization (Months 9-12)
**Goal:** Close remaining agent gaps, optimize performance, measure ROI.

| Action | Agents Delivered |
|---|---|
| Deploy remaining L&D agents | Skills Gap Analyzer, Learning Path Recommendation Agent, Leadership Program Design Assistant |
| Deploy engagement agents | Survey Design Agent, Engagement Insight Synthesizer, ERG Engagement Agent |
| Deploy all ER & compliance agents | ER Case Intelligence Agent, Progressive Discipline Advisor, PIP Documentation Assistant |
| Full workforce planning suite | Workforce Scenario Modeling Agent, Labor Market Intelligence Agent |
| Performance tuning and bias audits | Review all 82 agents for accuracy and fairness |
| ROI measurement | Track coordination tax reduction, time savings, adoption metrics |

---

## 6. Security & Governance (Critical for FSI/Banks)

### 6.1 Model Armor (Mandatory for FSI)

Model Armor must be configured **in agent code** — the console settings do NOT cover ADK agents.

```python
# Every custom ADK agent must include Model Armor config
safety_config=ModelArmorConfig(
    block_sensitive_pii=True,       # Block SSN, account numbers, salary leak
    block_harmful_content=True,
    detect_prompt_injection=True,   # Critical for agents with data access
    audit_logging=True,             # Required: every interaction logged to Cloud Audit Logs
    data_residency_region="IN"      # For Indian banks — keep data in India region
)
```

### 6.2 Access Control per Agent

| Agent | Who Can Access | Data Restriction |
|---|---|---|
| Policy Q&A | All employees | Read-only, no PII |
| Attrition Prediction | CHRO, HRBPs only | Aggregated view for HRBPs; individual for CHRO |
| Pay Equity Audit | CHRO, Comp & Ben Mgr | Anonymized below director level |
| Payroll Reconciliation | Payroll Specialist only | Restricted to own team's data |
| Calibration Analytics | HRBP, Calibration committee | Dept-scoped |

```bash
# Add permissioned users to a specific agent via REST
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/assistants/default_assistant/agents/AGENT_ID:addPermissionedUsers" \
  -d '{
    "users": ["user@bank.com"],
    "role": "VIEWER"
  }'
```

### 6.3 Audit & Compliance

```bash
# Access Cloud Audit Logs — every agent interaction logged
gcloud logging read \
  'resource.type="discoveryengine.googleapis.com/Engine"' \
  --project=PROJECT_ID \
  --format=json

# Set up log sink to BigQuery for compliance reporting
gcloud logging sinks create hr-agent-audit-sink \
  bigquery.googleapis.com/projects/PROJECT_ID/datasets/audit_logs \
  --log-filter='resource.type="discoveryengine.googleapis.com/Engine"'
```

### 6.4 VPC Service Controls (for Indian Banks with RBI data residency)

```bash
# Create VPC perimeter around Gemini Enterprise resources
gcloud access-context-manager perimeters create hr-agent-perimeter \
  --title="HR Agent VPC Perimeter" \
  --resources=projects/PROJECT_NUMBER \
  --restricted-services=discoveryengine.googleapis.com,aiplatform.googleapis.com \
  --policy=POLICY_ID
```

---

## 7. OAuth Setup for Agents Accessing Google Resources

For agents that need to read/write Google Workspace data on behalf of users (e.g., Calendar actions, Gmail):

```bash
# Step 1: Create OAuth credentials in Google Cloud Console
# APIs & Services → Credentials → Create OAuth Client ID → Web Application
# Add redirect URIs:
# https://vertexaisearch.cloud.google.com/oauth-redirect
# https://vertexaisearch.cloud.google.com/static/oauth/oauth.html

# Step 2: Register authorization resource with Gemini Enterprise
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/authorizations?authorizationId=hr-workspace-auth" \
  -d '{
    "name": "projects/PROJECT_ID/locations/global/authorizations/hr-workspace-auth",
    "serverSideOauth2": {
      "clientId": "OAUTH_CLIENT_ID",
      "clientSecret": "OAUTH_CLIENT_SECRET",
      "authorizationUri": "https://accounts.google.com/o/oauth2/v2/auth?client_id=CLIENT_ID&redirect_uri=https%3A%2F%2Fvertexaisearch.cloud.google.com%2Fstatic%2Foauth%2Foauth.html&scope=https://www.googleapis.com/auth/calendar%20https://www.googleapis.com/auth/gmail.readonly&include_granted_scopes=true&response_type=code&access_type=offline&prompt=consent",
      "tokenUri": "https://oauth2.googleapis.com/token"
    }
  }'

# Step 3: Reference AUTH_ID when registering the agent
# Add "authorizationConfig": { "toolAuthorizations": ["projects/PROJECT_NUMBER/locations/global/authorizations/hr-workspace-auth"] }
```

---

## 8. Monitoring & Analytics

### 8.1 Platform Analytics (built-in)

Console → Gemini Enterprise → App → Analytics

- Query volume by agent
- Resolution rate (queries answered vs. escalated)
- User satisfaction (thumbs up/down)
- Most common queries per persona
- Agent invocation frequency

### 8.2 Custom KPI Dashboard (BigQuery + Looker)

```sql
-- Log agent interactions to BigQuery for ROI measurement
-- Coordination Tax reduction metric
SELECT
  agent_name,
  DATE_TRUNC(interaction_date, WEEK) as week,
  COUNT(*) as total_interactions,
  AVG(resolution_time_seconds) as avg_resolution_time,
  SUM(CASE WHEN resolved = TRUE THEN 1 ELSE 0 END) / COUNT(*) as resolution_rate,
  SUM(estimated_manual_time_saved_minutes) as total_time_saved_minutes
FROM `project.audit_logs.agent_interactions`
GROUP BY 1, 2
ORDER BY 2 DESC
```

### 8.3 ROI Measurement Framework

| Metric | Before | Target (12 months) | How to Measure |
|---|---|---|---|
| HR query resolution time | Multi-day | < 2 minutes | Audit logs |
| HRBP time on admin tasks | ~75% of day | < 40% | Time tracking survey |
| Requisition validation time | 1-3 days | < 1 hour | ATS timestamps |
| Payroll reconciliation errors | Baseline | -80% | ADP error logs |
| Compliance training completion | Baseline | +30% | LMS data |
| Employee satisfaction (eNPS) | Baseline | +10 points | Quarterly survey |

---

## 9. Agent Registration Reference (Summary)

```bash
# List all registered agents in a Gemini Enterprise app
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/assistants/default_assistant/agents"

# List all agents deployed on Vertex AI Agent Engine
gcloud ai reasoning-engines list --project=PROJECT_ID --location=us-central1

# Get specific agent resource path (needed for registration)
gcloud ai reasoning-engines describe AGENT_ENGINE_ID \
  --project=PROJECT_ID --location=us-central1

# Delete a registered agent from Gemini Enterprise
curl -X DELETE \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/assistants/default_assistant/agents/AGENT_ID"
```

---

## 10. Agent Catalogue — All 82 Agents by Phase

### Phase 1 (Foundation) — Layer 1 & 2
`Policy Q&A Assistant` · `New Hire Q&A Assistant` · `Benefits Q&A & Enrollment Assistant` · `Employee Query Resolution Agent` · `Service Delivery Analytics Agent` · `Employee Communication Drafter` · `Compliance Training Content Generator`

### Phase 2 (Expansion) — Layer 2 & 3
`Requisition Intake & Validation Agent` · `Requisition Prioritization Agent` · `Candidate Sourcing & Outreach Agent` · `Resume Screening & Shortlisting Agent` · `Sourcing Channel Analytics Agent` · `Interview Question & Scorecard Builder` · `Interview Scheduling & Coordination Agent` · `Selection Debrief Summarizer` · `Offer Package Modeler Agent` · `Pre-boarding Orchestration Agent` · `Onboarding Orchestration Agent` · `Onboarding Effectiveness Analyzer` · `Job Description Generator & Optimizer` · `Job Architecture Sync Agent` · `Org Structure Analyzer Agent` · `Change Communication Drafter` · `1:1 Meeting Prep Agent` · `Goal Drafting & Alignment Assistant` · `OKR Progress Tracker Agent` · `Feedback Trend Analyzer`

### Phase 3 (Intelligence) — Layer 3 & 4
`Performance Review Narrative Assistant` · `Calibration Analytics Agent` · `Review Cycle Orchestration Agent` · `Successor Readiness Assessment Agent` · `Succession Pipeline Dashboard Agent` · `HiPo Identification & Nomination Agent` · `HiPo Development Journey Agent` · `Market Benchmarking Analysis Agent` · `Compensation Philosophy Communicator` · `Merit & Promotion Budget Modeler Agent` · `Pay Equity Audit Agent` · `Compensation Letter Generator` · `Benefits Utilization & Cost Analyzer` · `Total Rewards Optimizer Agent` · `Equity Participant Communicator` · `Payroll Input Validation Agent` · `Payroll Reconciliation & Compliance Agent` · `HRIS Data Quality Monitor Agent` · `Employee Data Change Orchestrator` · `Attrition Analytics Agent` · `DEI Dashboard & Reporting Agent` · `Inclusive Hiring Audit Agent` · `DEI Communication & Programming Assistant` · `HR Data Lake Query Agent` · `Attrition Prediction & Intervention Agent` · `Workforce Cost Modeling Agent`

### Phase 4 (Optimization) — Layer 3 & 4
`Workforce Scenario Modeling Agent` · `Labor Market Intelligence Agent` · `Workforce Plan Document Drafter` · `Restructuring Impact Assessment Agent` · `Skills Gap Analyzer Agent` · `L&D Plan Narrative Drafter` · `Learning Content Summarizer & Quiz Generator` · `Learning Path Recommendation Agent` · `Compliance Tracking & Escalation Agent` · `Leadership Program Design Assistant` · `Program Impact Evaluation Agent` · `ER Case Intelligence Agent` · `ER Case Analytics Agent` · `PIP Documentation Assistant` · `Progressive Discipline Advisor Agent` · `Policy Drafting & Review Assistant` · `Leave & Accommodation Intake Agent` · `Leave Utilization & Compliance Analyzer` · `Survey Design & Communication Agent` · `Engagement Insight Synthesizer` · `Engagement-to-Outcome Correlation Agent` · `Recognition Program Analytics Agent` · `Recognition Nudge & Celebration Agent` · `Communication Reach & Sentiment Analyzer` · `ERG Engagement & Impact Agent` · `Offboarding Orchestration Agent` · `Exit Interview Insight Synthesizer` · `HR Tech Stack Intelligence Agent` · `Vendor Evaluation Assistant`

---

*Sources: Gemini Enterprise Documentation (docs.cloud.google.com/gemini/enterprise), ADK Agent Registration Guide, HR & PeopleOps Agentic Transformation Field Kit (Shanky Ram, Google Cloud APAC, March 2026)*
