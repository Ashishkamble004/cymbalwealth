# CLAUDE.md — Project Memory & Agent Configuration

This file is read by Claude Code at the start of every session. Keep it updated.

## Project overview
<!-- TODO: Fill in -->
- **Project name**: 
- **What it does**: 
- **Tech stack**: 
- **Primary GCP region**: asia-south1
- **GitHub repo**: 

## Repository structure
```
/
├── src/                    # Application source code
├── tests/                  # Test files
├── infra/
│   ├── terraform/          # GCP infrastructure
│   └── helm/               # Kubernetes manifests
├── docs/
│   ├── adr/                # Architecture Decision Records
│   ├── specs/              # Product specs
│   ├── diagrams/           # Architecture diagrams
│   └── runbooks/           # Operational runbooks
└── .claude/
    ├── agents/             # Agent definitions (this directory)
    ├── memory/             # Per-agent memory files
    ├── reviews/            # Code review outputs
    └── security/           # Security audit outputs
```

## Active agents
| Agent | Role | When to invoke |
|-------|------|----------------|
| product-spec | PM requirements | New feature start |
| software-architect | System design + ADR | Before any implementation |
| diagram-agent | Mermaid / C4 diagrams | After architecture decisions |
| code-developer | Feature implementation | After ADR exists |
| code-reviewer | Code quality + security | Before any commit |
| debugger | Root cause analysis | When code breaks |
| security-auditor | OWASP + CVE scan | Before every deployment |
| performance-analyst | Profiling + benchmarks | Before production release |
| test-engineer | Unit + integration + E2E | After implementation |
| cloud-architect | GCP + Terraform | Infra changes |
| devops-engineer | CI/CD + Docker + K8s | Pipeline changes |
| docs-writer | README + API docs | After feature complete |
| github-publisher | Git + PR + releases | When ready to commit |
| changelog-agent | Semver + CHANGELOG | At release time |

## Coding conventions
<!-- TODO: Fill in your project's conventions -->
- Language: 
- Formatter: 
- Linter: 
- Test framework: 
- Package manager: 

## Environment variables
<!-- List all required env vars here so agents know what's available -->
- `NODE_ENV` / `ENVIRONMENT`: dev | staging | prod
- Add others as your project grows

## Key decisions already made
<!-- Log architectural decisions here so agents don't re-litigate them -->
- See /docs/adr/ for all formal ADRs

## Known constraints
<!-- Things agents must NOT do -->
- Do not provision outside asia-south1 / asia-south2 without explicit approval
- Do not commit directly to main — always use PRs
- Do not use npm packages with known HIGH/CRITICAL CVEs
