# AWS A2A Agents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two serverless A2A-compliant agents on AWS — Credit Intelligence and Regulatory Reporting — deployable via SAM, backed by Redshift Serverless with synthetic data.

**Architecture:** Each agent is a single Lambda behind an API Gateway HTTP API. The Lambda handles all three A2A endpoints (agent card, ping, JSON-RPC). For LLM reasoning, the Lambda calls Bedrock `converse` API (`claude-sonnet-4-6`) with tool definitions. When Bedrock requests a tool call, the Lambda executes SQL via the Redshift Data API and returns the result. No Bedrock Agent managed resource needed — one Lambda does everything.

**Tech Stack:** Python 3.12, AWS SAM, API Gateway HTTP API, Lambda, Bedrock `converse` API, Redshift Serverless, Redshift Data API, Secrets Manager

---

## File Structure

```
aws/
  shared/
    python/                       # Lambda Layer — shared code
      a2a_adapter.py              # A2A protocol: JSON-RPC parsing, agent card serving, response building
      redshift_client.py          # Redshift Data API wrapper (execute + poll + parse)
  credit_intelligence/
    app.py                        # Lambda handler — A2A routing + Bedrock converse + tool loop
    agent_card.json               # Static agent card JSON
  regulatory_reporting/
    app.py                        # Lambda handler — same pattern, different tools/system prompt
    agent_card.json               # Static agent card JSON
  seed/
    credit_data.sql               # Synthetic credit_profiles + loan_history data
    regulatory_data.sql           # Synthetic capital_adequacy + liquidity_ratios + npa_summary data
    setup_redshift.py             # One-time script: create tables + seed data via Redshift Data API
  template.yaml                   # SAM template: Redshift Serverless + 2 APIs + 2 Lambdas + Layer
  samconfig.toml                  # SAM deploy config
```

---

### Task 1: SAM Project Scaffolding

**Files:**
- Create: `aws/template.yaml`
- Create: `aws/samconfig.toml`

- [ ] **Step 1: Create the SAM template with all resources**

```yaml
# aws/template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: CymbalWealth A2A Agents — Credit Intelligence + Regulatory Reporting

Globals:
  Function:
    Runtime: python3.12
    Timeout: 90
    MemorySize: 256
    Architectures:
      - arm64
    Environment:
      Variables:
        REDSHIFT_WORKGROUP: cymbal-wealth-wg
        REDSHIFT_DATABASE: cymbalwealth
        REDSHIFT_SECRET_ARN: !Ref RedshiftAdminSecret
        BEDROCK_MODEL_ID: anthropic.claude-sonnet-4-6
        BEDROCK_REGION: us-east-1

Resources:
  # ---- Redshift Serverless ----
  RedshiftAdminSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: cymbal-wealth-redshift-admin
      Description: Redshift Serverless admin credentials for CymbalWealth
      GenerateSecretString:
        SecretStringTemplate: '{"username": "admin"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludeCharacters: '"@/\\'

  RedshiftNamespace:
    Type: AWS::RedshiftServerless::Namespace
    Properties:
      NamespaceName: cymbal-wealth-ns
      AdminUsername: admin
      AdminUserPassword: !Sub '{{resolve:secretsmanager:${RedshiftAdminSecret}:SecretString:password}}'
      DbName: cymbalwealth
      DefaultIamRoleArn: !GetAtt RedshiftRole.Arn
      IamRoles:
        - !GetAtt RedshiftRole.Arn

  RedshiftWorkgroup:
    Type: AWS::RedshiftServerless::Workgroup
    DependsOn: RedshiftNamespace
    Properties:
      WorkgroupName: cymbal-wealth-wg
      NamespaceName: cymbal-wealth-ns
      BaseCapacity: 8
      PubliclyAccessible: false

  RedshiftRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: cymbal-wealth-redshift-role
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: redshift.amazonaws.com
            Action: sts:AssumeRole

  # ---- Shared Lambda Layer ----
  SharedLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: cymbal-wealth-a2a-shared
      Description: Shared A2A adapter + Redshift client
      ContentUri: shared/
      CompatibleRuntimes:
        - python3.12
      CompatibleArchitectures:
        - arm64
    Metadata:
      BuildMethod: python3.12

  # ---- Credit Intelligence Agent ----
  CreditIntelligenceApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: $default
      Description: Credit Intelligence A2A Agent

  CreditIntelligenceFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: cymbal-credit-intelligence
      CodeUri: credit_intelligence/
      Handler: app.lambda_handler
      Layers:
        - !Ref SharedLayer
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource: !Sub 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6'
            - Effect: Allow
              Action:
                - redshift-data:ExecuteStatement
                - redshift-data:DescribeStatement
                - redshift-data:GetStatementResult
              Resource: '*'
            - Effect: Allow
              Action:
                - secretsmanager:GetSecretValue
              Resource: !Ref RedshiftAdminSecret
      Events:
        AgentCard:
          Type: HttpApi
          Properties:
            ApiId: !Ref CreditIntelligenceApi
            Path: /.well-known/agent-card.json
            Method: GET
        Ping:
          Type: HttpApi
          Properties:
            ApiId: !Ref CreditIntelligenceApi
            Path: /ping
            Method: GET
        A2AEndpoint:
          Type: HttpApi
          Properties:
            ApiId: !Ref CreditIntelligenceApi
            Path: /
            Method: POST

  # ---- Regulatory Reporting Agent ----
  RegulatoryReportingApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: $default
      Description: Regulatory Reporting A2A Agent

  RegulatoryReportingFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: cymbal-regulatory-reporting
      CodeUri: regulatory_reporting/
      Handler: app.lambda_handler
      Layers:
        - !Ref SharedLayer
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource: !Sub 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6'
            - Effect: Allow
              Action:
                - redshift-data:ExecuteStatement
                - redshift-data:DescribeStatement
                - redshift-data:GetStatementResult
              Resource: '*'
            - Effect: Allow
              Action:
                - secretsmanager:GetSecretValue
              Resource: !Ref RedshiftAdminSecret
      Events:
        AgentCard:
          Type: HttpApi
          Properties:
            ApiId: !Ref RegulatoryReportingApi
            Path: /.well-known/agent-card.json
            Method: GET
        Ping:
          Type: HttpApi
          Properties:
            ApiId: !Ref RegulatoryReportingApi
            Path: /ping
            Method: GET
        A2AEndpoint:
          Type: HttpApi
          Properties:
            ApiId: !Ref RegulatoryReportingApi
            Path: /
            Method: POST

Outputs:
  CreditIntelligenceUrl:
    Description: Credit Intelligence A2A endpoint
    Value: !Sub 'https://${CreditIntelligenceApi}.execute-api.${AWS::Region}.amazonaws.com'
  RegulatoryReportingUrl:
    Description: Regulatory Reporting A2A endpoint
    Value: !Sub 'https://${RegulatoryReportingApi}.execute-api.${AWS::Region}.amazonaws.com'
  RedshiftWorkgroup:
    Description: Redshift Serverless workgroup name
    Value: cymbal-wealth-wg
  RedshiftSecretArn:
    Description: Redshift admin secret ARN
    Value: !Ref RedshiftAdminSecret
```

- [ ] **Step 2: Create SAM config**

```toml
# aws/samconfig.toml
version = 0.1

[default.deploy.parameters]
stack_name = "cymbal-wealth-a2a"
resolve_s3 = true
s3_prefix = "cymbal-wealth-a2a"
region = "us-east-1"
capabilities = "CAPABILITY_NAMED_IAM"
confirm_changeset = true
```

- [ ] **Step 3: Validate the template**

Run: `cd /home/admin_kambleashish_altostrat_com/cymbalwealth/aws && sam validate`
Expected: template is valid

- [ ] **Step 4: Commit scaffolding**

```bash
git add aws/template.yaml aws/samconfig.toml
git commit -m "feat(aws): SAM template scaffolding — Redshift Serverless + 2 A2A agents"
```

---

### Task 2: Shared A2A Adapter Layer

**Files:**
- Create: `aws/shared/python/a2a_adapter.py`
- Create: `aws/shared/requirements.txt`

This module handles all A2A protocol concerns: parsing incoming JSON-RPC `message/send` requests, serving agent cards, health checks, and formatting JSON-RPC responses with artifacts.

- [ ] **Step 1: Create the shared A2A adapter**

```python
# aws/shared/python/a2a_adapter.py
"""A2A Protocol adapter for AWS Lambda behind API Gateway HTTP API.

Handles:
- GET /.well-known/agent-card.json → serves static agent card
- GET /ping → health check
- POST / → parses JSON-RPC 2.0 message/send, delegates to handler, returns artifacts
"""

import json
import uuid
from datetime import datetime, timezone


def build_api_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def handle_agent_card(agent_card: dict) -> dict:
    return build_api_response(200, agent_card)


def handle_ping() -> dict:
    return build_api_response(200, {
        "status": "Healthy",
        "time_of_last_update": datetime.now(timezone.utc).isoformat(),
    })


def parse_a2a_request(event: dict) -> dict | None:
    """Parse JSON-RPC 2.0 body from API Gateway HTTP API event.

    Returns the parsed body dict, or None if parsing fails.
    """
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def extract_user_message(rpc_body: dict) -> str | None:
    """Extract the text content from a message/send JSON-RPC request."""
    params = rpc_body.get("params", {})
    message = params.get("message", {})
    parts = message.get("parts", [])
    for part in parts:
        if part.get("kind") == "text" or "text" in part:
            return part.get("text", "")
    return None


def build_a2a_response(rpc_id: str, agent_text: str, task_id: str | None = None) -> dict:
    """Build a JSON-RPC 2.0 response with the agent's text as an artifact."""
    tid = task_id or str(uuid.uuid4())
    result = {
        "id": tid,
        "status": {"state": "completed"},
        "artifacts": [{
            "parts": [{"kind": "text", "text": agent_text}],
            "index": 0,
        }],
    }
    return build_api_response(200, {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": result,
    })


def build_a2a_error(rpc_id: str, code: int, message: str) -> dict:
    return build_api_response(200, {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": code, "message": message},
    })


def route_request(event: dict, agent_card: dict, handle_message_fn) -> dict:
    """Top-level router for Lambda. Dispatches to agent card, ping, or message handler.

    Args:
        event: API Gateway HTTP API event
        agent_card: Static agent card dict (loaded from JSON file)
        handle_message_fn: Callable(user_text: str) -> str that processes the user query
    """
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")

    if method == "GET" and "agent-card" in path:
        return handle_agent_card(agent_card)

    if method == "GET" and path.endswith("/ping"):
        return handle_ping()

    if method == "POST":
        rpc_body = parse_a2a_request(event)
        if not rpc_body:
            return build_a2a_error("unknown", -32700, "Parse error")

        rpc_id = rpc_body.get("id", "unknown")
        rpc_method = rpc_body.get("method", "")

        if rpc_method != "message/send":
            return build_a2a_error(rpc_id, -32601, f"Method not found: {rpc_method}")

        user_text = extract_user_message(rpc_body)
        if not user_text:
            return build_a2a_error(rpc_id, -32602, "No text content in message")

        try:
            agent_response = handle_message_fn(user_text)
            return build_a2a_response(rpc_id, agent_response)
        except Exception as exc:
            return build_a2a_error(rpc_id, -32000, f"Agent error: {str(exc)}")

    return build_api_response(404, {"error": "Not found"})
```

- [ ] **Step 2: Create requirements.txt for the layer**

```text
# aws/shared/requirements.txt
boto3>=1.35.0
```

- [ ] **Step 3: Test locally — verify parse and response building**

Run:
```bash
cd /home/admin_kambleashish_altostrat_com/cymbalwealth/aws
python3 -c "
import sys; sys.path.insert(0, 'shared/python')
from a2a_adapter import parse_a2a_request, extract_user_message, build_a2a_response, route_request
import json

# Test parse
event = {'body': json.dumps({'jsonrpc': '2.0', 'id': 'r1', 'method': 'message/send', 'params': {'message': {'role': 'user', 'parts': [{'kind': 'text', 'text': 'Hello'}], 'messageId': 'm1'}}})}
parsed = parse_a2a_request(event)
assert parsed['method'] == 'message/send'
assert extract_user_message(parsed) == 'Hello'

# Test response
resp = build_a2a_response('r1', 'Agent says hi')
body = json.loads(resp['body'])
assert body['result']['artifacts'][0]['parts'][0]['text'] == 'Agent says hi'

# Test routing with mock handler
card = {'name': 'test'}
result = route_request({'requestContext': {'http': {'method': 'GET'}}, 'rawPath': '/.well-known/agent-card.json'}, card, lambda x: x)
assert json.loads(result['body'])['name'] == 'test'

print('All A2A adapter tests passed')
"
```
Expected: `All A2A adapter tests passed`

- [ ] **Step 4: Commit**

```bash
git add aws/shared/
git commit -m "feat(aws): shared A2A protocol adapter layer"
```

---

### Task 3: Shared Redshift Client

**Files:**
- Create: `aws/shared/python/redshift_client.py`

Wraps the Redshift Data API (execute → poll → parse) so agent handlers call one function.

- [ ] **Step 1: Create the Redshift client**

```python
# aws/shared/python/redshift_client.py
"""Redshift Data API client for CymbalWealth agents.

Uses Redshift Serverless (WorkgroupName, not ClusterIdentifier).
No VPC needed — Redshift Data API is a service endpoint.
"""

import json
import os
import time

import boto3

_client = boto3.client("redshift-data", region_name=os.environ.get("AWS_REGION", "us-east-1"))

WORKGROUP = os.environ.get("REDSHIFT_WORKGROUP", "cymbal-wealth-wg")
DATABASE = os.environ.get("REDSHIFT_DATABASE", "cymbalwealth")
SECRET_ARN = os.environ.get("REDSHIFT_SECRET_ARN", "")


def execute_query(sql: str, max_wait_seconds: int = 30) -> list[dict]:
    """Execute SQL against Redshift Serverless and return rows as list of dicts.

    Uses the Redshift Data API (async execute → poll → fetch result).
    """
    resp = _client.execute_statement(
        WorkgroupName=WORKGROUP,
        Database=DATABASE,
        SecretArn=SECRET_ARN,
        Sql=sql,
    )
    statement_id = resp["Id"]

    elapsed = 0.0
    while elapsed < max_wait_seconds:
        desc = _client.describe_statement(Id=statement_id)
        status = desc["Status"]
        if status == "FINISHED":
            break
        if status in ("FAILED", "ABORTED"):
            raise RuntimeError(f"Redshift query {status}: {desc.get('Error', 'unknown')}")
        time.sleep(0.5)
        elapsed += 0.5

    if elapsed >= max_wait_seconds:
        raise TimeoutError(f"Redshift query did not finish in {max_wait_seconds}s")

    result = _client.get_statement_result(Id=statement_id)
    columns = [col["name"] for col in result["ColumnMetadata"]]
    rows = []
    for record in result["Records"]:
        row = {}
        for i, field in enumerate(record):
            if "stringValue" in field:
                row[columns[i]] = field["stringValue"]
            elif "longValue" in field:
                row[columns[i]] = field["longValue"]
            elif "doubleValue" in field:
                row[columns[i]] = field["doubleValue"]
            elif "booleanValue" in field:
                row[columns[i]] = field["booleanValue"]
            elif "isNull" in field and field["isNull"]:
                row[columns[i]] = None
            else:
                row[columns[i]] = str(field)
        rows.append(row)
    return rows


def execute_query_json(sql: str, max_wait_seconds: int = 30) -> str:
    """Execute SQL and return result as a JSON string (for Bedrock tool responses)."""
    rows = execute_query(sql, max_wait_seconds)
    return json.dumps(rows, default=str)
```

- [ ] **Step 2: Test locally — verify parsing logic**

Run:
```bash
cd /home/admin_kambleashish_altostrat_com/cymbalwealth/aws
python3 -c "
import sys; sys.path.insert(0, 'shared/python')
from redshift_client import execute_query, WORKGROUP, DATABASE
print(f'Configured: workgroup={WORKGROUP}, database={DATABASE}')
print('Redshift client module loads OK (actual queries require deployed Redshift)')
"
```
Expected: `Configured: workgroup=cymbal-wealth-wg, database=cymbalwealth`

- [ ] **Step 3: Commit**

```bash
git add aws/shared/python/redshift_client.py
git commit -m "feat(aws): shared Redshift Data API client"
```

---

### Task 4: Credit Intelligence Agent

**Files:**
- Create: `aws/credit_intelligence/app.py`
- Create: `aws/credit_intelligence/agent_card.json`

- [ ] **Step 1: Create the agent card**

```json
{
  "name": "Cymbal Wealth Credit Intelligence",
  "description": "Provides CIBIL-style credit scoring, debt-to-income analysis, and loan eligibility assessments for Cymbal Wealth customers. Backed by Redshift Serverless.",
  "version": "1.0.0",
  "url": "https://PLACEHOLDER.execute-api.us-east-1.amazonaws.com/",
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "capabilities": {
    "streaming": false
  },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "authentication": {
    "schemes": ["Bearer"]
  },
  "skills": [
    {
      "id": "credit-score-lookup",
      "name": "Credit Score Lookup",
      "description": "Look up CIBIL credit score and grade for a customer reference number",
      "tags": ["credit", "cibil", "score"]
    },
    {
      "id": "debt-to-income",
      "name": "Debt-to-Income Analysis",
      "description": "Calculate DTI ratio from active loan obligations and income",
      "tags": ["dti", "income", "loans"]
    },
    {
      "id": "credit-eligibility",
      "name": "Credit Eligibility Assessment",
      "description": "Determine loan eligibility with max amount recommendation based on credit profile",
      "tags": ["eligibility", "loan", "assessment"]
    }
  ]
}
```

- [ ] **Step 2: Create the Lambda handler**

```python
# aws/credit_intelligence/app.py
"""Credit Intelligence A2A Agent — Lambda handler.

Routes: agent card, ping, and message/send.
Uses Bedrock converse API (claude-sonnet-4-6) with Redshift tool calling.
"""

import json
import os
import logging

import boto3

from a2a_adapter import route_request
from redshift_client import execute_query_json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-6")

AGENT_CARD_PATH = os.path.join(os.path.dirname(__file__), "agent_card.json")
with open(AGENT_CARD_PATH) as f:
    AGENT_CARD = json.load(f)

SYSTEM_PROMPT = """You are the Credit Intelligence Agent for Cymbal Wealth, a banking institution.
You have access to Redshift Serverless containing customer credit profiles and loan history.

When asked about a customer's credit standing, ALWAYS use the query_credit_data tool to fetch real data.
Never fabricate credit scores or financial figures.

Customer reference numbers follow the format CW-YYYY-NNN (e.g., CW-2026-001).

Format responses clearly with:
- Credit score and grade
- Active loans summary
- DTI ratio (total EMI / assumed monthly income of ₹1,50,000)
- Eligibility recommendation with max loan amount

Use Indian Rupee (₹) formatting. Be precise with numbers."""

TOOLS = [
    {
        "toolSpec": {
            "name": "query_credit_data",
            "description": "Query customer credit profiles and loan history from Redshift. Write a SQL SELECT query against tables: credit_profiles (columns: customer_ref, cibil_score, credit_grade, active_loans, total_exposure, dpd_30, dpd_90, updated_at) and loan_history (columns: customer_ref, loan_type, sanctioned_amt, outstanding_amt, emi, status, opened_at, closed_at). Always filter by customer_ref.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL SELECT query to execute against Redshift"
                        }
                    },
                    "required": ["sql"]
                }
            }
        }
    }
]


def _run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "query_credit_data":
        sql = tool_input.get("sql", "")
        if not sql.strip().upper().startswith("SELECT"):
            return json.dumps({"error": "Only SELECT queries are allowed"})
        return execute_query_json(sql)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _converse_with_tools(user_text: str) -> str:
    """Run Bedrock converse loop with tool use until final text response."""
    messages = [{"role": "user", "content": [{"text": user_text}]}]

    for _ in range(5):  # max 5 tool-use rounds
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=messages,
            system=[{"text": SYSTEM_PROMPT}],
            toolConfig={"tools": TOOLS},
        )

        output_message = response["output"]["message"]
        messages.append(output_message)
        stop_reason = response["stopReason"]

        if stop_reason == "end_turn":
            for block in output_message["content"]:
                if "text" in block:
                    return block["text"]
            return "No response generated."

        if stop_reason == "tool_use":
            tool_results = []
            for block in output_message["content"]:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    result_text = _run_tool(tool_use["name"], tool_use["input"])
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"json": json.loads(result_text)}],
                        }
                    })
            messages.append({"role": "user", "content": tool_results})

    return "Max tool-use rounds exceeded."


def handle_message(user_text: str) -> str:
    return _converse_with_tools(user_text)


def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    return route_request(event, AGENT_CARD, handle_message)
```

- [ ] **Step 3: Test locally — verify module loads and agent card parses**

Run:
```bash
cd /home/admin_kambleashish_altostrat_com/cymbalwealth/aws
python3 -c "
import json
with open('credit_intelligence/agent_card.json') as f:
    card = json.load(f)
assert card['name'] == 'Cymbal Wealth Credit Intelligence'
assert card['protocolVersion'] == '0.3.0'
assert len(card['skills']) == 3
print(f'Agent card OK: {card[\"name\"]} with {len(card[\"skills\"])} skills')
"
```
Expected: `Agent card OK: Cymbal Wealth Credit Intelligence with 3 skills`

- [ ] **Step 4: Commit**

```bash
git add aws/credit_intelligence/
git commit -m "feat(aws): Credit Intelligence A2A agent — handler + agent card"
```

---

### Task 5: Regulatory Reporting Agent

**Files:**
- Create: `aws/regulatory_reporting/app.py`
- Create: `aws/regulatory_reporting/agent_card.json`

- [ ] **Step 1: Create the agent card**

```json
{
  "name": "Cymbal Wealth Regulatory Reporting",
  "description": "Provides Basel III capital adequacy (CRAR), liquidity coverage (LCR/NSFR), and NPA analysis for Cymbal Wealth's regulatory compliance. Backed by Redshift Serverless.",
  "version": "1.0.0",
  "url": "https://PLACEHOLDER.execute-api.us-east-1.amazonaws.com/",
  "protocolVersion": "0.3.0",
  "preferredTransport": "JSONRPC",
  "capabilities": {
    "streaming": false
  },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "authentication": {
    "schemes": ["Bearer"]
  },
  "skills": [
    {
      "id": "capital-adequacy",
      "name": "Capital Adequacy (CRAR)",
      "description": "Report CRAR (Capital to Risk-weighted Assets Ratio) vs RBI minimum of 9%",
      "tags": ["crar", "basel3", "capital", "rbi"]
    },
    {
      "id": "liquidity-ratios",
      "name": "Liquidity Coverage Ratios",
      "description": "Report LCR and NSFR liquidity metrics",
      "tags": ["lcr", "nsfr", "liquidity"]
    },
    {
      "id": "npa-summary",
      "name": "NPA Summary",
      "description": "Report Gross NPA %, Net NPA %, and provision coverage",
      "tags": ["npa", "asset-quality", "provisions"]
    },
    {
      "id": "basel3-summary",
      "name": "Basel III Summary",
      "description": "Comprehensive Basel III report with Tier 1, Tier 2 capital breakdown and risk-weighted assets",
      "tags": ["basel3", "tier1", "tier2", "rwa"]
    }
  ]
}
```

- [ ] **Step 2: Create the Lambda handler**

```python
# aws/regulatory_reporting/app.py
"""Regulatory Reporting A2A Agent — Lambda handler.

Routes: agent card, ping, and message/send.
Uses Bedrock converse API (claude-sonnet-4-6) with Redshift tool calling.
"""

import json
import os
import logging

import boto3

from a2a_adapter import route_request
from redshift_client import execute_query_json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "us-east-1"))
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-6")

AGENT_CARD_PATH = os.path.join(os.path.dirname(__file__), "agent_card.json")
with open(AGENT_CARD_PATH) as f:
    AGENT_CARD = json.load(f)

SYSTEM_PROMPT = """You are the Regulatory Reporting Agent for Cymbal Wealth, a banking institution.
You have access to Redshift Serverless containing regulatory and compliance data.

When asked about capital adequacy, liquidity, or asset quality, ALWAYS use the query_regulatory_data tool.
Never fabricate regulatory figures.

Key regulatory benchmarks:
- CRAR (Capital to Risk-weighted Assets Ratio): RBI minimum is 9.0%
- LCR (Liquidity Coverage Ratio): minimum 100%
- NSFR (Net Stable Funding Ratio): minimum 100%

Format responses clearly with:
- Current metric value vs regulatory minimum
- Buffer above/below minimum
- Tier 1 and Tier 2 capital breakdown where relevant
- Quarter-over-quarter trend if multiple periods available

Use Indian Rupee (₹) and Crore (Cr) formatting. Be precise with numbers and percentages."""

TOOLS = [
    {
        "toolSpec": {
            "name": "query_regulatory_data",
            "description": "Query regulatory compliance data from Redshift. Write a SQL SELECT query against tables: capital_adequacy (columns: report_date, tier1_capital, tier2_capital, total_rwa, crar_pct, min_required), liquidity_ratios (columns: report_date, hqla, net_cash_30d, lcr_pct, nsfr_pct), npa_summary (columns: report_date, gross_npa_pct, net_npa_pct, provision_cov, total_advances). Order by report_date DESC for latest data.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL SELECT query to execute against Redshift"
                        }
                    },
                    "required": ["sql"]
                }
            }
        }
    }
]


def _run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "query_regulatory_data":
        sql = tool_input.get("sql", "")
        if not sql.strip().upper().startswith("SELECT"):
            return json.dumps({"error": "Only SELECT queries are allowed"})
        return execute_query_json(sql)
    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _converse_with_tools(user_text: str) -> str:
    """Run Bedrock converse loop with tool use until final text response."""
    messages = [{"role": "user", "content": [{"text": user_text}]}]

    for _ in range(5):
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=messages,
            system=[{"text": SYSTEM_PROMPT}],
            toolConfig={"tools": TOOLS},
        )

        output_message = response["output"]["message"]
        messages.append(output_message)
        stop_reason = response["stopReason"]

        if stop_reason == "end_turn":
            for block in output_message["content"]:
                if "text" in block:
                    return block["text"]
            return "No response generated."

        if stop_reason == "tool_use":
            tool_results = []
            for block in output_message["content"]:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    result_text = _run_tool(tool_use["name"], tool_use["input"])
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"json": json.loads(result_text)}],
                        }
                    })
            messages.append({"role": "user", "content": tool_results})

    return "Max tool-use rounds exceeded."


def handle_message(user_text: str) -> str:
    return _converse_with_tools(user_text)


def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    return route_request(event, AGENT_CARD, handle_message)
```

- [ ] **Step 3: Commit**

```bash
git add aws/regulatory_reporting/
git commit -m "feat(aws): Regulatory Reporting A2A agent — handler + agent card"
```

---

### Task 6: Synthetic Seed Data

**Files:**
- Create: `aws/seed/credit_data.sql`
- Create: `aws/seed/regulatory_data.sql`

- [ ] **Step 1: Create credit data seed SQL**

```sql
-- aws/seed/credit_data.sql
-- Synthetic credit data for CymbalWealth demo customers

CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS credit_profiles (
    customer_ref    VARCHAR(20) PRIMARY KEY,
    cibil_score     INT NOT NULL,
    credit_grade    VARCHAR(3) NOT NULL,
    active_loans    INT DEFAULT 0,
    total_exposure  DECIMAL(15,2) DEFAULT 0,
    dpd_30          INT DEFAULT 0,
    dpd_90          INT DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT GETDATE()
);

CREATE TABLE IF NOT EXISTS loan_history (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    customer_ref    VARCHAR(20) NOT NULL,
    loan_type       VARCHAR(30) NOT NULL,
    sanctioned_amt  DECIMAL(15,2) NOT NULL,
    outstanding_amt DECIMAL(15,2) NOT NULL,
    emi             DECIMAL(10,2) NOT NULL,
    status          VARCHAR(15) NOT NULL,
    opened_at       DATE NOT NULL,
    closed_at       DATE
);

-- Customer CW-2026-001: Ashish Kamble — strong credit profile
INSERT INTO credit_profiles VALUES
('CW-2026-001', 742, 'AA', 2, 3250000.00, 0, 0, '2026-04-15 10:00:00');

INSERT INTO loan_history VALUES
(DEFAULT, 'CW-2026-001', 'AUTO', 800000.00, 320000.00, 15800.00, 'ACTIVE', '2023-06-15', NULL),
(DEFAULT, 'CW-2026-001', 'CREDIT_CARD', 500000.00, 45000.00, 4500.00, 'ACTIVE', '2021-01-10', NULL),
(DEFAULT, 'CW-2026-001', 'PERSONAL', 300000.00, 0.00, 0.00, 'CLOSED', '2020-03-01', '2022-03-01');

-- Customer CW-2026-002: Priya Sharma — moderate credit profile
INSERT INTO credit_profiles VALUES
('CW-2026-002', 678, 'BBB', 3, 5800000.00, 1, 0, '2026-04-15 10:00:00');

INSERT INTO loan_history VALUES
(DEFAULT, 'CW-2026-002', 'HOME', 4500000.00, 3900000.00, 42000.00, 'ACTIVE', '2022-09-01', NULL),
(DEFAULT, 'CW-2026-002', 'AUTO', 600000.00, 180000.00, 12500.00, 'ACTIVE', '2024-01-15', NULL),
(DEFAULT, 'CW-2026-002', 'CREDIT_CARD', 200000.00, 165000.00, 8250.00, 'ACTIVE', '2023-05-01', NULL),
(DEFAULT, 'CW-2026-002', 'PERSONAL', 500000.00, 0.00, 0.00, 'CLOSED', '2019-06-01', '2021-06-01');

-- Customer CW-2026-003: Raj Patel — weak credit profile (for demo edge case)
INSERT INTO credit_profiles VALUES
('CW-2026-003', 520, 'C', 4, 8200000.00, 3, 1, '2026-04-15 10:00:00');

INSERT INTO loan_history VALUES
(DEFAULT, 'CW-2026-003', 'HOME', 5000000.00, 4800000.00, 48000.00, 'ACTIVE', '2024-01-01', NULL),
(DEFAULT, 'CW-2026-003', 'PERSONAL', 1500000.00, 1400000.00, 35000.00, 'ACTIVE', '2024-06-01', NULL),
(DEFAULT, 'CW-2026-003', 'CREDIT_CARD', 300000.00, 290000.00, 14500.00, 'ACTIVE', '2023-01-01', NULL),
(DEFAULT, 'CW-2026-003', 'AUTO', 700000.00, 650000.00, 18000.00, 'ACTIVE', '2025-01-01', NULL);
```

- [ ] **Step 2: Create regulatory data seed SQL**

```sql
-- aws/seed/regulatory_data.sql
-- Synthetic regulatory compliance data for CymbalWealth

CREATE TABLE IF NOT EXISTS capital_adequacy (
    report_date     DATE PRIMARY KEY,
    tier1_capital   DECIMAL(18,2) NOT NULL,
    tier2_capital   DECIMAL(18,2) NOT NULL,
    total_rwa       DECIMAL(18,2) NOT NULL,
    crar_pct        DECIMAL(5,2) NOT NULL,
    min_required    DECIMAL(5,2) DEFAULT 9.00
);

CREATE TABLE IF NOT EXISTS liquidity_ratios (
    report_date     DATE PRIMARY KEY,
    hqla            DECIMAL(18,2) NOT NULL,
    net_cash_30d    DECIMAL(18,2) NOT NULL,
    lcr_pct         DECIMAL(5,2) NOT NULL,
    nsfr_pct        DECIMAL(5,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS npa_summary (
    report_date     DATE PRIMARY KEY,
    gross_npa_pct   DECIMAL(5,2) NOT NULL,
    net_npa_pct     DECIMAL(5,2) NOT NULL,
    provision_cov   DECIMAL(5,2) NOT NULL,
    total_advances  DECIMAL(18,2) NOT NULL
);

-- Capital Adequacy — quarterly data (amounts in Crores)
INSERT INTO capital_adequacy VALUES
('2025-06-30', 3980.00, 1050.00, 42500.00, 11.84, 9.00),
('2025-09-30', 4120.00, 1100.00, 43800.00, 11.92, 9.00),
('2025-12-31', 4450.00, 1180.00, 44200.00, 12.74, 9.00),
('2026-03-31', 4820.00, 1240.00, 45900.00, 13.20, 9.00);

-- Liquidity Ratios — quarterly
INSERT INTO liquidity_ratios VALUES
('2025-06-30', 12500.00, 9200.00, 135.87, 112.40),
('2025-09-30', 13100.00, 9500.00, 137.89, 115.20),
('2025-12-31', 13800.00, 9800.00, 140.82, 118.50),
('2026-03-31', 14200.00, 10000.00, 142.00, 121.30);

-- NPA Summary — quarterly (advances in Crores)
INSERT INTO npa_summary VALUES
('2025-06-30', 3.20, 1.10, 72.50, 38500.00),
('2025-09-30', 2.90, 0.95, 75.20, 39200.00),
('2025-12-31', 2.60, 0.82, 78.40, 40100.00),
('2026-03-31', 2.35, 0.71, 81.20, 41500.00);
```

- [ ] **Step 3: Commit**

```bash
git add aws/seed/
git commit -m "feat(aws): synthetic seed data — credit profiles + regulatory reporting"
```

---

### Task 7: Redshift Setup Script

**Files:**
- Create: `aws/seed/setup_redshift.py`

One-time script to create tables and seed data into Redshift Serverless. Requires the stack to be deployed first (needs workgroup + secret ARN).

- [ ] **Step 1: Create the setup script**

```python
#!/usr/bin/env python3
"""One-time Redshift Serverless setup: create tables + seed data.

Usage:
    # After SAM deploy, get outputs:
    export REDSHIFT_SECRET_ARN=$(aws cloudformation describe-stacks \
        --stack-name cymbal-wealth-a2a \
        --query 'Stacks[0].Outputs[?OutputKey==`RedshiftSecretArn`].OutputValue' \
        --output text)

    python setup_redshift.py
"""

import os
import sys
import time
from pathlib import Path

import boto3

WORKGROUP = os.environ.get("REDSHIFT_WORKGROUP", "cymbal-wealth-wg")
DATABASE = os.environ.get("REDSHIFT_DATABASE", "cymbalwealth")
SECRET_ARN = os.environ.get("REDSHIFT_SECRET_ARN")
REGION = os.environ.get("AWS_REGION", "us-east-1")

if not SECRET_ARN:
    print("ERROR: REDSHIFT_SECRET_ARN environment variable is required")
    print("Run: export REDSHIFT_SECRET_ARN=$(aws cloudformation describe-stacks \\")
    print("    --stack-name cymbal-wealth-a2a \\")
    print("    --query 'Stacks[0].Outputs[?OutputKey==`RedshiftSecretArn`].OutputValue' \\")
    print("    --output text)")
    sys.exit(1)

client = boto3.client("redshift-data", region_name=REGION)


def run_sql(sql: str, description: str) -> None:
    print(f"  Running: {description}...")
    resp = client.execute_statement(
        WorkgroupName=WORKGROUP,
        Database=DATABASE,
        SecretArn=SECRET_ARN,
        Sql=sql,
    )
    statement_id = resp["Id"]

    while True:
        desc = client.describe_statement(Id=statement_id)
        status = desc["Status"]
        if status == "FINISHED":
            print(f"  ✓ {description}")
            return
        if status in ("FAILED", "ABORTED"):
            print(f"  ✗ {description}: {desc.get('Error', 'unknown')}")
            raise RuntimeError(desc.get("Error", "SQL execution failed"))
        time.sleep(1)


def run_sql_file(filepath: Path) -> None:
    sql_text = filepath.read_text()
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    for i, stmt in enumerate(statements):
        run_sql(stmt, f"{filepath.name} statement {i+1}/{len(statements)}")


def main():
    seed_dir = Path(__file__).parent
    print(f"Setting up Redshift Serverless ({WORKGROUP}/{DATABASE})")
    print(f"Secret ARN: {SECRET_ARN[:40]}...")
    print()

    print("[1/2] Credit data...")
    run_sql_file(seed_dir / "credit_data.sql")
    print()

    print("[2/2] Regulatory data...")
    run_sql_file(seed_dir / "regulatory_data.sql")
    print()

    print("✓ Redshift setup complete")

    # Quick verification
    print("\nVerification:")
    resp = client.execute_statement(
        WorkgroupName=WORKGROUP, Database=DATABASE, SecretArn=SECRET_ARN,
        Sql="SELECT customer_ref, cibil_score, credit_grade FROM credit_profiles ORDER BY customer_ref",
    )
    time.sleep(3)
    result = client.get_statement_result(Id=resp["Id"])
    for row in result["Records"]:
        ref = row[0]["stringValue"]
        score = row[1]["longValue"]
        grade = row[2]["stringValue"]
        print(f"  {ref}: CIBIL {score} ({grade})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add aws/seed/setup_redshift.py
git commit -m "feat(aws): Redshift Serverless setup + seed script"
```

---

### Task 8: Deploy + End-to-End Test

**Prerequisite:** AWS MFA session active (the user ran `aws sts get-session-token` earlier).

- [ ] **Step 1: Deploy the SAM stack**

Run:
```bash
cd /home/admin_kambleashish_altostrat_com/cymbalwealth/aws
sam build
sam deploy
```

Expected: CloudFormation creates Redshift Serverless namespace/workgroup, 2 API Gateways, 2 Lambdas, 1 Layer, IAM roles, Secrets Manager secret. Takes ~5-8 minutes.

- [ ] **Step 2: Get stack outputs**

Run:
```bash
aws cloudformation describe-stacks \
    --stack-name cymbal-wealth-a2a \
    --query 'Stacks[0].Outputs' \
    --output table
```

Expected: Table showing CreditIntelligenceUrl, RegulatoryReportingUrl, RedshiftWorkgroup, RedshiftSecretArn

- [ ] **Step 3: Seed Redshift**

Run:
```bash
export REDSHIFT_SECRET_ARN=$(aws cloudformation describe-stacks \
    --stack-name cymbal-wealth-a2a \
    --query 'Stacks[0].Outputs[?OutputKey==`RedshiftSecretArn`].OutputValue' \
    --output text)

cd /home/admin_kambleashish_altostrat_com/cymbalwealth/aws/seed
python3 setup_redshift.py
```

Expected: All statements succeed, verification shows 3 credit profiles.

- [ ] **Step 4: Test Credit Intelligence — agent card**

Run:
```bash
CREDIT_URL=$(aws cloudformation describe-stacks \
    --stack-name cymbal-wealth-a2a \
    --query 'Stacks[0].Outputs[?OutputKey==`CreditIntelligenceUrl`].OutputValue' \
    --output text)

curl -s "$CREDIT_URL/.well-known/agent-card.json" | python3 -m json.tool
```

Expected: Returns the agent card JSON with name "Cymbal Wealth Credit Intelligence"

- [ ] **Step 5: Test Credit Intelligence — ping**

Run:
```bash
curl -s "$CREDIT_URL/ping" | python3 -m json.tool
```

Expected: `{"status": "Healthy", "time_of_last_update": "..."}`

- [ ] **Step 6: Test Credit Intelligence — message/send**

Run:
```bash
curl -s -X POST "$CREDIT_URL/" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-001",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "What is the credit score and loan eligibility for customer CW-2026-001?"}],
                "messageId": "msg-001"
            }
        }
    }' | python3 -m json.tool
```

Expected: JSON-RPC response with `result.artifacts[0].parts[0].text` containing CIBIL score 742 (AA), DTI ratio, and eligibility recommendation.

- [ ] **Step 7: Test Regulatory Reporting — message/send**

Run:
```bash
REG_URL=$(aws cloudformation describe-stacks \
    --stack-name cymbal-wealth-a2a \
    --query 'Stacks[0].Outputs[?OutputKey==`RegulatoryReportingUrl`].OutputValue' \
    --output text)

curl -s -X POST "$REG_URL/" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-002",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "What is our current CRAR vs RBI minimum?"}],
                "messageId": "msg-002"
            }
        }
    }' | python3 -m json.tool
```

Expected: JSON-RPC response mentioning CRAR 13.20%, RBI minimum 9.0%, buffer 4.20%.

- [ ] **Step 8: Commit final state**

```bash
git add -A aws/
git commit -m "feat(aws): deploy AWS A2A agents — Credit Intelligence + Regulatory Reporting"
```
