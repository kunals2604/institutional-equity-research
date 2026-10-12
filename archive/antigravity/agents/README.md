# Multi-Agent Equity Research System

This directory houses the orchestration structure and agent configurations for the institutional-level fundamental equity research platform.

## Architecture & Operating Principles

1. **Canonical Research Specification**: [`MASTER_RESEARCH_FRAMEWORK.md`](../MASTER_RESEARCH_FRAMEWORK.md) is the governing research specification and source of truth for all research methodology, analytical depth, and evaluation criteria.
2. **Global Operating Rules**: [`PROJECT_INSTRUCTIONS.md`](../PROJECT_INSTRUCTIONS.md) contains non-negotiable global operating rules, evidence standards, fact-versus-inference boundaries, and continuous execution requirements.
3. **Specialist Agents as Independent Research Departments**: Specialist agents located in `specialists/` function as independent research departments (e.g., forensic accounting, business model/moat, industry/competitive dynamics, management/governance, valuation). Each specialist focuses deeply within its assigned mandate.
4. **CIO Agent Responsibilities**: The Chief Investment Officer (`cio/`) agent is responsible for cross-departmental synthesis, reconciling contradictions across specialist reports, rigorous thesis attack / bear-case disproof, and issuing the final investment verdict.
5. **Dynamic Company-Specific Folders**: Company-specific research folders under `research/companies/` are created automatically by the agents when a company is assigned. No pre-emptive or placeholder company folders should be created manually.
6. **No Master Framework Duplication**: Do not duplicate the master research framework inside individual agent definitions or prompt files. Agents reference the master framework directly.
7. **Artifact Isolation & Integrity**: Each specialist writes only to its designated research artifact within the assigned company directory. Never overwrite or mutate another specialist's research artifact.
8. **Specialist Outputs are Evidence Inputs**: Specialist outputs are structured evidence inputs, not unquestionable conclusions. The CIO must independently evaluate source quality, factual accuracy, management claims, and valuation assumptions rather than simply averaging departmental scores.
9. **Continuous Execution Requirement**: Research workflows are continuous pipelines. Internal phases (source discovery, extraction, data validation, historical analysis, business/industry analysis, management analysis, layer analysis, valuation, scenarios, verdict) must proceed automatically without halting or waiting for confirmation after source extraction.
10. **Support for Four Investment Layers**: The system strictly supports and independently analyzes companies across all four investment layers before determining the dominant framework:
    - **Layer 1**: Bedrock Compounder
    - **Layer 2**: High-Growth Business
    - **Layer 3**: Cyclical / Event-Driven / Special Situation / Deep Value
    - **Layer 4**: Venture-Style / Optionality (primary lens in SME Research Mode)
