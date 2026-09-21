# TheraScout — AI-Powered Therapeutic Opportunity Intelligence

This repository is the Build-phase implementation of TheraScout, structured to match the
architecture and agent-pipeline diagrams from the Solution Proposal.

## How this maps to the diagrams

- **Layered architecture diagram** (Client / Application & Orchestration / AI Services / Data)
  → `frontend/`, `backend/`, `agents/` + `orchestration/`, `infra/stacks/data_stack.py`
- **Agent pipeline diagram** (ingest → decision → analyze → gap_score → report)
  → `orchestration/statemachine.asl.json` — every box in that diagram is a state in this file
- **Tool boxes above each agent** → `tools/*/handler.py` — one Lambda per tool
- **Broadcast / gather pattern** (6 agents in parallel) → the `Parallel` state in the state
  machine, calling the 6 agents in `agents/`

## Folder structure

```
therascout/
├── infra/                     AWS CDK app — deploys everything below
│   ├── app.py                 CDK entry point
│   └── stacks/
│       ├── data_stack.py      S3, OpenSearch Serverless, RDS PostgreSQL
│       ├── agent_stack.py     Lambda tools + IAM roles
│       └── orchestration_stack.py   Step Functions state machine + API Gateway
│
├── tools/                     One Lambda per "tool box" in the pipeline diagram
│   ├── query_globocan_data/   Disease Agent's tool (reads a cached S3 export — GLOBOCAN has no live API)
│   ├── query_pubmed/          Research Agent's tool
│   ├── query_clinicaltrials/  Clinical Trial Agent's tool
│   ├── query_openfda/         Treatment Agent's tool
│   ├── check_data_scope/      Ingest step's decision logic
│   ├── enrich_enterprise_data/  Mocked enterprise data source (the "no" branch)
│   └── compose_pdf_report/    Report Composer (ReportLab)
│
├── agents/                     AgentCore harness configs — one per specialist agent
│   ├── disease_agent/
│   ├── treatment_agent/
│   ├── research_agent/
│   ├── clinical_trial_agent/
│   ├── competition_agent/
│   ├── trend_agent/
│   ├── gap_scoring_agent/      Combines all 6 outputs, ranks Top 5–6
│   └── orchestrator/           Top-level agent that the state machine invokes first
│
├── orchestration/
│   └── statemachine.asl.json  The full pipeline as Amazon States Language
│
├── backend/                    FastAPI — the Application layer
│   ├── main.py
│   └── routers/scan.py         POST /scan, GET /scan/{id}
│
├── frontend/                   React — the Client layer
│   └── src/App.jsx
│
├── data/
│   └── scoring_weights.json   The Opportunity Score weighting formula
│
└── tests/
    └── test_query_globocan_data.py
```

## MVP scope: Colorectal Cancer, not "Oncology" broadly

"Oncology" spans dozens of distinct diseases with very different data
volumes. This MVP is scoped to **Colorectal Cancer** specifically — large
enough dataset across all four sources to produce a real demo, without
being so broad the agents return an unfocused result set. Extending to
additional cancer types is a matter of (a) uploading their GLOBOCAN
export and (b) adding them to `check_data_scope`'s known-areas set — not
a redesign.

## A correction worth knowing about

An earlier version of this project called the general **WHO GHO OData
API** for disease burden data. That API is real, but it does not carry
cancer-specific incidence/mortality by cancer type — that data lives in
**IARC's GLOBOCAN**, published through the Global Cancer Observatory
("Cancer Today"). GLOBOCAN has no public REST API, so
`tools/query_globocan_data/` reads from a periodically-refreshed export
cached in S3 instead of a live call — see that file's docstring for the
full explanation and the manual export step required.



This matches the milestone plan from the Solution Proposal:

1. `tools/query_pubmed/handler.py` — get one live-API tool working standalone first (simplest to test — no S3 caching step). `tools/query_globocan_data/handler.py` has a different pattern: it reads a cached S3 export since GLOBOCAN has no public API — upload one export manually before testing it.
2. `agents/disease_agent/` — wire that tool into one real AgentCore agent, test with `agentcore dev`
3. `orchestration/statemachine.asl.json` — wire ingest → decision → Disease Agent only → stop
4. Duplicate the pattern for the other five agents
5. `agents/gap_scoring_agent/` and `tools/compose_pdf_report/`
6. `backend/` then `frontend/` — build the UI last, once the pipeline works headlessly

## Deploying

```bash
cd infra
pip install -r requirements.txt
cdk bootstrap aws://<ACCOUNT_ID>/us-east-1
cdk deploy --all
```

## What is mocked in this MVP

- `tools/enrich_enterprise_data/` is a stub — real enterprise data integration is a Phase 2 item,
  not part of this public-data MVP.
- Model access assumes Anthropic Claude Sonnet 5 is enabled in Bedrock model access for your account.
